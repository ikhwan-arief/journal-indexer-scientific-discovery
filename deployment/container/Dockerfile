FROM python:3.12-slim AS builder

ARG SITE_URL=""
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SITE_URL=${SITE_URL}

WORKDIR /app

COPY data ./data
COPY scripts ./scripts
COPY src ./src

RUN python scripts/build_site.py


FROM nginx:1.27-alpine AS runtime

COPY deployment/container/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/docs /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]