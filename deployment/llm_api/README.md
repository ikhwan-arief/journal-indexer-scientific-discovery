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
