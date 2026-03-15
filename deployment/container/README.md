# Container Deployment Guide

This repository is best deployed to a server as a static site build served by a small web server container.

This guide lives under `deployment/container/` on purpose:

- `docs/` is generated output and can be replaced during each build.
- the container files and server deployment notes are operational assets, not public site content.

## Deployment model

The application does **not** need Python at runtime.

- Python is used only while running `scripts/build_site.py`
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
- `.env.example`: template for the deployment-specific values used by Docker Compose

## Prerequisites

Before building the container on the server, make sure:

1. Docker Engine is installed.
1. Docker Compose is available via `docker compose`.
1. The required CSV files already exist in `data/raw/`: `scimagojr.csv` and `scimagojr_wos.csv`.
1. The optional DOAJ file exists if you want DOAJ enrichment: `doaj.csv`.

If `doaj.csv` is missing, the site still builds, but DOAJ-derived website, APC, and license enrichment will be reduced.

## Recommended server layout

For a clean single-server deployment, keep the clone and the compose files in a dedicated application directory.

Example:

```bash
sudo mkdir -p /opt/journal-discovery
sudo chown "$USER":"$USER" /opt/journal-discovery
cd /opt/journal-discovery
git clone https://github.com/ikhwan-arief/journal-indexer-scientific-discovery.git .
```

After cloning:

1. place the required CSV files in `data/raw/`
1. copy `deployment/container/.env.example` to `deployment/container/.env`
1. update the values in `.env` for the real domain, image name, and published port

Example:

```bash
cp deployment/container/.env.example deployment/container/.env
```

The `.env` file is meant to hold deployment-specific values only. Source data still lives in `data/raw/`.

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

If you are deploying on a small VM and want to confirm the build output before starting the runtime container, inspect the image metadata and recent build logs:

```bash
docker image ls journal-discovery
docker history journal-discovery:latest
```

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

If you do not use a reverse proxy yet, you can temporarily expose the site directly on a public port like `80:80`, but that is not recommended for long-term production use because TLS termination and routing are harder to manage.

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
cp deployment/container/.env.example deployment/container/.env
```

### 2. Edit the Compose file

The Compose file now reads deployment values from `deployment/container/.env`.

Update at least these values in `.env`:

- `SITE_URL`
- `HOST_PORT` if you do not want `8080`
- `IMAGE_NAME` if you want versioned tags
- `CONTAINER_NAME` if needed

Example `.env`:

```dotenv
SITE_URL=https://journals.example.com
IMAGE_NAME=journal-discovery:2026-03-15
CONTAINER_NAME=journal-discovery
HOST_PORT=8080
```

### 3. Start the service

```bash
docker compose -f deployment/container/docker-compose.yml up -d --build
```

### 4. Check service status

```bash
docker compose -f deployment/container/docker-compose.yml ps
docker compose -f deployment/container/docker-compose.yml logs --tail=100
curl -I http://127.0.0.1:8080/
curl http://127.0.0.1:8080/healthz
```

### 5. Make Compose start on boot

If Docker is already enabled on the server, `restart: unless-stopped` is usually enough. To be explicit on Debian/Ubuntu systems:

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

If you later want Compose itself wrapped in a systemd service, add that as a host-level operational step, not inside the container.

## Reverse proxy and TLS

For production, the clean setup is usually:

1. keep this container bound to `127.0.0.1:8080` or to a private Docker network
1. terminate HTTPS in a reverse proxy such as Nginx, Caddy, or Traefik
1. forward the domain to this container

Example public flow:

- browser -> `https://journals.example.com`
- reverse proxy -> `http://journal-discovery:80`

If your reverse proxy is on the same host and not inside Docker, forwarding to `http://127.0.0.1:8080` is enough.

Minimal Nginx reverse proxy example on the host:

```nginx
server {
  listen 80;
  server_name journals.example.com;

  location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

After this works, add TLS with your normal certificate flow, for example Let's Encrypt.

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

If you use versioned image tags in `.env`, update `IMAGE_NAME` first, then run the same Compose command.

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

A practical pattern is:

1. keep yesterday's known-good image tag available locally
1. assign each rollout a dated tag
1. only remove older tags after the new deployment passes verification

## Storage and persistence

This deployment is immutable and does not require a database volume.

- no runtime database file is needed
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

## Suggested deployment checklist

Use this sequence for routine updates on a server:

1. `git pull origin main`
1. refresh `data/raw/` if source files changed
1. review `deployment/container/.env`
1. run `docker compose -f deployment/container/docker-compose.yml up -d --build`
1. run the local container checks on `127.0.0.1`
1. run the public URL checks on the real domain
1. keep the previous image tag until the rollout is confirmed healthy

## Operational notes

- Because this is a static site, horizontal scaling is trivial: multiple containers can serve the same built output.
- If you later want the server to rebuild automatically from Git commits, the best next step is to build the image in CI and push it to a container registry.
- If you later need true server-side search or database-backed updates at runtime, that is a different architecture from the current static-site model.
