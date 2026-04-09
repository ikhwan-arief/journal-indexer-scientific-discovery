from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from journal_discovery_llm_api.app import create_app
from journal_discovery_llm_api.config import ApiSettings
from journal_discovery_llm_api.provider import ProviderTimeoutError
from journal_discovery_llm_api.rate_limit import InMemoryRateLimiter
from journal_discovery_llm_api.schemas import ProviderScoredCandidate


def make_settings(**overrides) -> ApiSettings:
    base = ApiSettings(
        provider_kind="openai_compatible",
        provider_base_url="https://provider.example/v1",
        provider_api_key="secret",
        provider_model="mock-model",
        provider_timeout_seconds=30.0,
        batch_size=10,
        max_candidates=50,
        default_top_n=50,
        query_char_limit=3000,
        title_char_limit=240,
        category_char_limit=480,
        area_char_limit=420,
        subject_area_char_limit=240,
        lexical_score_limit=1_000_000.0,
        body_limit_bytes=250000,
        rate_limit_window_seconds=60,
        rate_limit_max_requests=30,
        allow_origins=("https://example.github.io",),
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        enable_docs=False,
    )
    return replace(base, **overrides)


class FakeProvider:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, object]] = []
        self.model_name = "mock-model"

    def rerank_batch(self, query_text, candidates):
        self.calls.append(
            {
                "query_text": query_text,
                "sourceids": [candidate.sourceid for candidate in candidates],
            }
        )
        if self.error:
            raise self.error

        scored = []
        for index, candidate in enumerate(candidates):
            boost = 100 if candidate.sourceid == "c12" else 80 if candidate.sourceid == "c11" else 20 - index
            scored.append(
                ProviderScoredCandidate(
                    sourceid=candidate.sourceid,
                    title=candidate.title,
                    lexical_score=float(candidate.lexical_score),
                    llm_score=max(0, boost),
                    rationale=f"{candidate.title} aligns with the submitted scope.",
                    matched_fields=["title", "areas"],
                    confidence=0.75,
                )
            )
        return scored


def build_payload(total: int = 12) -> dict[str, object]:
    return {
        "query_text": "machine learning " * 400,
        "top_n": total,
        "candidates": [
            {
                "sourceid": f"c{index}",
                "title": f"Journal {index}",
                "categories": "Machine Learning; Data Science",
                "areas": "Computer Science",
                "subject_area": "Artificial Intelligence",
                "publisher": "Example Publisher",
                "country": "Indonesia",
                "lexical_score": float(index),
            }
            for index in range(1, total + 1)
        ],
    }


def test_abstract_match_batches_candidates_and_sorts_results() -> None:
    provider = FakeProvider()
    settings = make_settings(query_char_limit=120, batch_size=10)
    client = TestClient(create_app(settings=settings, provider=provider))

    response = client.post("/v1/abstract-match", json=build_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "llm_assisted"
    assert payload["model"] == "mock-model"
    assert [item["sourceid"] for item in payload["ranked"][:2]] == ["c12", "c11"]
    assert len(provider.calls) == 2
    assert [len(call["sourceids"]) for call in provider.calls] == [10, 2]
    assert len(str(provider.calls[0]["query_text"])) <= settings.query_char_limit


def test_abstract_match_returns_timeout_as_service_unavailable() -> None:
    provider = FakeProvider(error=ProviderTimeoutError("Upstream LLM provider timed out."))
    client = TestClient(create_app(settings=make_settings(), provider=provider))

    response = client.post("/v1/abstract-match", json=build_payload(total=2))

    assert response.status_code == 503
    assert "timed out" in response.json()["detail"].lower()


def test_abstract_match_rate_limits_requests() -> None:
    provider = FakeProvider()
    settings = make_settings(rate_limit_max_requests=1, rate_limit_window_seconds=60)
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    client = TestClient(create_app(settings=settings, provider=provider, rate_limiter=limiter))

    first = client.post("/v1/abstract-match", json=build_payload(total=1))
    second = client.post("/v1/abstract-match", json=build_payload(total=1))

    assert first.status_code == 200
    assert second.status_code == 429


def test_abstract_match_rejects_large_body() -> None:
    provider = FakeProvider()
    settings = make_settings(body_limit_bytes=512)
    client = TestClient(create_app(settings=settings, provider=provider))

    response = client.post("/v1/abstract-match", json=build_payload(total=8))

    assert response.status_code == 413


def test_cors_allows_configured_origin() -> None:
    provider = FakeProvider()
    client = TestClient(create_app(settings=make_settings(), provider=provider))

    response = client.options(
        "/v1/abstract-match",
        headers={
            "Origin": "https://example.github.io",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://example.github.io"


def test_root_page_exposes_browser_friendly_service_summary() -> None:
    provider = FakeProvider()
    client = TestClient(create_app(settings=make_settings(), provider=provider))

    response = client.get("/")

    assert response.status_code == 200
    assert "Journal Discovery LLM API" in response.text
    assert "/healthz" in response.text
    assert "/v1/abstract-match" in response.text
