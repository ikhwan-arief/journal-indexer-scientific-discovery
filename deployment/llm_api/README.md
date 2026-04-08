# LLM API Deployment

This service exposes `POST /v1/abstract-match` for Journal Discovery abstract reranking.

## Required environment variables

- `LLM_PROVIDER_KIND=openai_compatible`
- `LLM_PROVIDER_BASE_URL=https://your-provider.example/v1`
- `LLM_PROVIDER_API_KEY=...`
- `LLM_PROVIDER_MODEL=...`

## Optional environment variables

- `LLM_PROVIDER_TIMEOUT_SECONDS=30`
- `LLM_CORS_ORIGINS=https://your-site.example`
- `LLM_RATE_LIMIT_MAX_REQUESTS=30`
- `LLM_RATE_LIMIT_WINDOW_SECONDS=60`
- `LLM_BODY_LIMIT_BYTES=250000`
- `LLM_API_ENABLE_DOCS=false`

If `LLM_PROVIDER_BASE_URL` points to `localhost` or `127.0.0.1` and `LLM_PROVIDER_TIMEOUT_SECONDS` is not set, the service defaults to `120` seconds to tolerate slower local Ollama inference.

## Build and run

```bash
docker build -f deployment/llm_api/Dockerfile -t journal-discovery-llm-api .

docker run -d \
  --name journal-discovery-llm-api \
  --restart unless-stopped \
  -p 8000:8000 \
  -e LLM_PROVIDER_KIND=openai_compatible \
  -e LLM_PROVIDER_BASE_URL=https://your-provider.example/v1 \
  -e LLM_PROVIDER_API_KEY=replace-me \
  -e LLM_PROVIDER_MODEL=replace-me \
  journal-discovery-llm-api
```

Point the frontend build variable `LLM_API_BASE_URL` to this service root, for example `https://api.example.com`.

For local Ollama testing, `qwen2.5:1.5b` is a good starting point for the full 50-candidate rerank workload.

## Render deployment

This repository now includes a root-level `render.yaml` for a Docker-based Render Web Service.

Service settings:

- Dockerfile: `deployment/llm_api/Dockerfile`
- Health check: `/healthz`
- Runtime port: `PORT` from Render, defaulting to `10000`

Set these environment variables in Render:

- `LLM_PROVIDER_KIND=openai_compatible`
- `LLM_PROVIDER_BASE_URL=https://your-provider.example/v1`
- `LLM_PROVIDER_API_KEY=...`
- `LLM_PROVIDER_MODEL=...`

The blueprint also sets:

- `LLM_CORS_ORIGINS=https://ikhwan-arief.github.io`
- `LLM_API_ENABLE_DOCS=false`

After Render gives you a public URL such as `https://journal-discovery-llm-api.onrender.com`, point the GitHub Pages build to that URL through:

- `LLM_API_BASE_URL=https://your-render-service.onrender.com`
- `LLM_ABSTRACT_MATCH_ENABLED=true`
