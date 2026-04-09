from __future__ import annotations

from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from .config import ApiSettings, get_settings
from .provider import ProviderRequestError, ProviderTimeoutError, build_provider, truncate_text
from .rate_limit import InMemoryRateLimiter
from .schemas import AbstractCandidate, AbstractMatchRequest, AbstractMatchResponse, ProviderScoredCandidate, RankedCandidate


def sort_scored_candidates(candidates: list[ProviderScoredCandidate]) -> list[ProviderScoredCandidate]:
    return sorted(
        candidates,
        key=lambda item: (
            -int(item.llm_score),
            -float(item.lexical_score),
            item.title.lower(),
            item.sourceid,
        ),
    )


def slice_candidates(candidates: list[AbstractCandidate], size: int) -> list[list[AbstractCandidate]]:
    return [candidates[index:index + size] for index in range(0, len(candidates), size)]


def root_page_html(settings: ApiSettings) -> str:
    docs_line = '<li><a href="/docs">GET /docs</a> for interactive API docs.</li>' if settings.enable_docs else ""
    provider_status = "configured" if settings.provider_configured else "not configured"
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Journal Discovery LLM API</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f7f8fc;
        color: #182033;
      }}
      body {{
        margin: 0;
        padding: 2.5rem 1.25rem;
      }}
      main {{
        max-width: 42rem;
        margin: 0 auto;
        padding: 1.5rem;
        background: #ffffff;
        border: 1px solid #dde3f0;
        border-radius: 1rem;
        box-shadow: 0 16px 48px rgba(24, 32, 51, 0.08);
      }}
      h1 {{
        margin: 0 0 0.75rem;
        font-size: 1.8rem;
      }}
      p, li {{
        line-height: 1.6;
      }}
      code {{
        background: #eef2fb;
        padding: 0.15rem 0.35rem;
        border-radius: 0.35rem;
      }}
      .status {{
        display: inline-block;
        margin-top: 0.5rem;
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        background: #edf7ed;
        color: #1f6a2a;
        font-weight: 600;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>Journal Discovery LLM API</h1>
      <p>This is the backend reranking service used by the GitHub Pages frontend. It is not the main user interface.</p>
      <p class="status">Provider is {provider_status}.</p>
      <ul>
        <li><a href="/healthz">GET /healthz</a> for a lightweight health check.</li>
        <li><code>POST /v1/abstract-match</code> to rerank shortlisted journals from an abstract.</li>
        {docs_line}
      </ul>
      <p>If this service is hosted on Render free, the first request after idle time can take longer because the service may need to wake up.</p>
    </main>
  </body>
</html>"""


def create_app(
    *,
    settings: ApiSettings | None = None,
    provider=None,
    rate_limiter: InMemoryRateLimiter | None = None,
) -> FastAPI:
    api_settings = settings or get_settings()
    api_provider = provider or build_provider(api_settings)
    limiter = rate_limiter or InMemoryRateLimiter(
        max_requests=api_settings.rate_limit_max_requests,
        window_seconds=api_settings.rate_limit_window_seconds,
    )

    app = FastAPI(
        title="Journal Discovery LLM API",
        docs_url="/docs" if api_settings.enable_docs else None,
        redoc_url="/redoc" if api_settings.enable_docs else None,
        openapi_url="/openapi.json" if api_settings.enable_docs else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(api_settings.allow_origins),
        allow_origin_regex=api_settings.allow_origin_regex,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.middleware("http")
    async def enforce_body_size(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH"}:
            body = await request.body()
            if len(body) > api_settings.body_limit_bytes:
                return JSONResponse(status_code=413, content={"detail": "Request body too large."})
        return await call_next(request)

    @app.middleware("http")
    async def enforce_rate_limit(request: Request, call_next):
        client_host = request.client.host if request.client else "unknown"
        if request.url.path != "/healthz" and not limiter.allow(client_host):
            return JSONResponse(status_code=429, content={"detail": "Too many requests."})
        return await call_next(request)

    @app.get("/", response_class=HTMLResponse)
    async def root() -> HTMLResponse:
        return HTMLResponse(root_page_html(api_settings))

    @app.get("/healthz")
    async def healthz() -> dict[str, object]:
        return {"status": "ok", "provider_configured": api_settings.provider_configured}

    @app.post("/v1/abstract-match", response_model=AbstractMatchResponse)
    async def abstract_match(payload: AbstractMatchRequest) -> AbstractMatchResponse:
        if not api_settings.provider_configured:
            raise HTTPException(status_code=503, detail="LLM provider is not configured.")

        if payload.top_n > len(payload.candidates):
            raise HTTPException(status_code=422, detail="top_n cannot exceed the number of candidates.")

        start_time = perf_counter()
        truncated_query = truncate_text(payload.query_text, api_settings.query_char_limit)
        try:
            batch_results: list[ProviderScoredCandidate] = []
            for batch in slice_candidates(payload.candidates, api_settings.batch_size):
                batch_results.extend(api_provider.rerank_batch(truncated_query, batch))
        except ProviderTimeoutError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ProviderRequestError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

        ranked = []
        for index, item in enumerate(sort_scored_candidates(batch_results)[: payload.top_n], start=1):
            ranked.append(
                RankedCandidate(
                    sourceid=item.sourceid,
                    rank=index,
                    llm_score=item.llm_score,
                    rationale=item.rationale,
                    matched_fields=item.matched_fields,
                    confidence=item.confidence,
                )
            )

        latency_ms = max(0, int((perf_counter() - start_time) * 1000))
        return AbstractMatchResponse(
            mode="llm_assisted",
            model=api_provider.model_name,
            latency_ms=latency_ms,
            ranked=ranked,
        )

    return app


app = create_app()
