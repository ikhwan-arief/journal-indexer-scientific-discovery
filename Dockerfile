# Dikembangkan oleh Ikhwan Arief (ikhwan[at]unand.ac.id)
# Lisensi aplikasi: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)

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

ENV PORT=8080

COPY deployment/container/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=builder /app/docs /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD /bin/sh -c 'wget -qO- "http://127.0.0.1:${PORT}/healthz" >/dev/null || exit 1'

