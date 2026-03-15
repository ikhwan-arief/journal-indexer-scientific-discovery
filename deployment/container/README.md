# Container Deployment Guide

This repository is best deployed to a server as a static site build served by a small web server container.

This guide lives under `deployment/container/` on purpose:

- `docs/` is generated output and can be replaced during each build.
- the container files and server deployment notes are operational assets, not public site content.

## Deployment model

The application does **not** need Python or SQLite at runtime.

- Python and SQLite are used only while running `scripts/build_site.py`
- the final runtime is plain static HTML, CSS, and JSON served from `docs/`
- the production container can therefore be a small Nginx image

Recommended production flow:

1. prepare or update the CSV source files in `data/raw/`
1. build a container image that runs the static-site build
1. serve the generated `docs/` output from Nginx
1. verify the live site after each rollout

## Files included in this folder

- `Dockerfile`: multi-stage image that builds the site and serves it with Nginx
- `nginx.conf`: minimal static-site Nginx config with a health endpoint
- `docker-compose.yml.example`: ready-to-edit Compose example for a single-server deployment

## Prerequisites

Before building the container on the server, make sure:

1. Docker Engine is installed.
1. Docker Compose is available via `docker compose`.
1. The required CSV files already exist in `data/raw/`:
   - `scimagojr 2024.csv`
   - `scimagojr 2024_WoS.csv`
1. The optional DOAJ file exists if you want DOAJ enrichment:
   - `doaj.csv`

If `doaj.csv` is missing, the site still builds, but DOAJ-derived website, APC, and license enrichment will be reduced.

## Option A: Build and run with Docker

This is the simplest path when you manage a single server manually.

### 1. Build the image

Run this from the repository root:

```bash
docker build \
  -f deployment/container/Dockerfile \
  --build-arg SITE_URL=https://journals.example.com \
  -t journal-discovery:latest \
  .
```

Notes:

- Replace `https://journals.example.com` with the real public URL.
- `SITE_URL` is optional, but recommended because the generator uses it for canonical tags and `sitemap.xml`.
- The build uses the current CSV files from `data/raw/` inside the repository.

### 2. Run the container

```bash
docker run -d \
  --name journal-discovery \
  --restart unless-stopped \
  -p 8080:80 \
  journal-discovery:latest
```

This publishes the site on port `8080` of the server.

If you already have a reverse proxy on the server, point it to `http://127.0.0.1:8080`.

### 3. Verify the container

```bash
docker ps
docker logs --tail=100 journal-discovery
curl -I http://127.0.0.1:8080/
curl http://127.0.0.1:8080/healthz
```

### 4. Verify the generated site content

```bash
curl -L --silent http://127.0.0.1:8080/ | grep -n "Search journal profiles"
curl -L --silent http://127.0.0.1:8080/search/ | grep -n "Search journal profiles"
```

## Option B: Build and run with Docker Compose

This is the better option if you want a repeatable single-server deployment file.

### 1. Copy the example file

```bash
cp deployment/container/docker-compose.yml.example deployment/container/docker-compose.yml
```

### 2. Edit the Compose file

Update at least these values:

- `SITE_URL`
- published port if you do not want `8080`
- image tag or container name if needed

### 3. Start the service

```bash
docker compose -f deployment/container/docker-compose.yml up -d --build
```

### 4. Check service status

```bash
docker compose -f deployment/container/docker-compose.yml ps
docker compose -f deployment/container/docker-compose.yml logs --tail=100
```

## Reverse proxy and TLS

For production, the clean setup is usually:

1. keep this container bound to `127.0.0.1:8080` or to a private Docker network
1. terminate HTTPS in a reverse proxy such as Nginx, Caddy, or Traefik
1. forward the domain to this container

Example public flow:

- browser -> `https://journals.example.com`
- reverse proxy -> `http://journal-discovery:80`

If your reverse proxy is on the same host and not inside Docker, forwarding to `http://127.0.0.1:8080` is enough.

## Updating the deployment

When source data changes, the recommended rollout is:

1. replace the CSV files in `data/raw/`
1. rebuild the image
1. restart the container with the new image
1. verify the live site

Example with plain Docker:

```bash
docker build \
  -f deployment/container/Dockerfile \
  --build-arg SITE_URL=https://journals.example.com \
  -t journal-discovery:latest \
  .

docker stop journal-discovery
docker rm journal-discovery

docker run -d \
  --name journal-discovery \
  --restart unless-stopped \
  -p 8080:80 \
  journal-discovery:latest
```

Example with Compose:

```bash
docker compose -f deployment/container/docker-compose.yml up -d --build
```

## Rollback strategy

For safer operations, tag each image with a release identifier instead of using only `latest`.

Example:

```bash
docker build \
  -f deployment/container/Dockerfile \
  --build-arg SITE_URL=https://journals.example.com \
  -t journal-discovery:2026-03-15 \
  .
```

If a deployment is bad, restart the server with the previous working tag.

## Storage and persistence

This deployment is immutable and does not require a database volume.

- no runtime SQLite file is needed
- no application upload directory is needed
- persistence is only needed if you separately store logs or backups on the host

## Recommended post-deploy checks

After every rollout, run these checks:

```bash
curl -L --silent https://journals.example.com/ | grep -n "Search journal profiles"
curl -L --silent https://journals.example.com/search/ | grep -n "Search journal profiles"
curl -L --silent https://journals.example.com/ | grep -n "ikhwan\[at\]eng\.unand\.ac\.id"
```

This follows the same verification pattern already used after GitHub Pages deployments:

1. verify the built content
1. verify the deployed service is healthy
1. verify the public site shows the expected text

## Operational notes

- Because this is a static site, horizontal scaling is trivial: multiple containers can serve the same built output.
- If you later want the server to rebuild automatically from Git commits, the best next step is to build the image in CI and push it to a container registry.
- If you later need true server-side search or database-backed updates at runtime, that is a different architecture from the current static-site model.
