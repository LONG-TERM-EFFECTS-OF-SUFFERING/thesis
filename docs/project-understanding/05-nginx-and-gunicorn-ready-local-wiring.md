# 05 - Nginx and Gunicorn-ready local wiring

Story: US-003, Nginx and Gunicorn-ready local wiring.

Status note: this document explains the US-003 implementation prepared for review.

## What this story added

This story changed the local Docker stack from a pure development-server setup to a production-style local path:

- `api`: Django still runs on port `8000`, but now through Gunicorn.

- `ui`: Vite still runs on port `5173` for the React frontend.

- `web`: Nginx listens on port `8080` and becomes the browser-facing front door.

- `db`: PostgreSQL remains the reproducible validation database.

The direct API and UI ports still exist for debugging. The new recommended browser entry point is:

```text
http://127.0.0.1:8080
```

## Why this matters

`runserver` and the Vite dev server are convenient during development, but they are not the same shape as a deployed application. This story adds the deployment boundary without adding a cloud platform, TLS, auth or a production static pipeline.

The local request path is now:

```text
Browser
    -> Nginx web service on 127.0.0.1:8080
    -> /api/ goes to api:8000
    -> / goes to ui:5173
```

## File-by-file explanation

### `src/api/requirements.txt`

The backend now includes:

```text
gunicorn==26.0.0
```

Gunicorn is the Python WSGI server used by the Docker API service.

### `src/api/gunicorn.conf.py`

This file tells Gunicorn how to start Django:

```python
wsgi_app = "opentube_insights_api.wsgi:application"
bind = "0.0.0.0:8000"
workers = 2
timeout = 60
```

The values can be overridden with environment variables in Docker Compose.

### `src/docker-compose.yml`

The `api` service still waits for PostgreSQL, runs migrations and listens on port `8000`. The startup command now uses Gunicorn:

```bash
python manage.py migrate &&
gunicorn -c gunicorn.conf.py opentube_insights_api.wsgi:application
```

The new `web` service uses the official Nginx image and mounts:

```text
src/nginx/default.conf -> /etc/nginx/conf.d/default.conf
```

The service binds to localhost by default:

```text
127.0.0.1:8080
```

### `src/nginx/default.conf`

Nginx has two routes:

```text
/api/ -> http://api:8000
/     -> http://ui:5173
```

It also forwards standard proxy headers such as `Host`, `X-Forwarded-For` and `X-Forwarded-Proto`.

### `src/.env.example`

The Compose-level environment template now includes:

```text
WEB_HOST_BIND=127.0.0.1
WEB_HOST_PORT=8080
GUNICORN_WORKERS=2
GUNICORN_TIMEOUT=60
```

Copy it to `src/.env` when local ports need to change.

### `src/api/core/tests.py`

The backend test suite now includes small orchestration tests that check:

- the Gunicorn config points at the existing Django WSGI app.

- the Compose API command uses Gunicorn instead of `runserver`.

- the Nginx config proxies UI and API traffic to the right Compose services.

## Commands

Run the local stack:

```bash
cd src
docker compose up --build -d
```

Check the Nginx front door:

```bash
curl "http://127.0.0.1:${WEB_HOST_PORT:-8080}/"
curl "http://127.0.0.1:${WEB_HOST_PORT:-8080}/api/health/"
```

Check direct service paths:

```bash
curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/"
curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/api/health/"
curl "http://127.0.0.1:${API_HOST_PORT:-8000}/api/health/"
```

Check Gunicorn config:

```bash
cd src/api
gunicorn --check-config -c gunicorn.conf.py opentube_insights_api.wsgi:application
```

## Manual checks

After the stack starts, run:

```bash
cd src
docker compose ps
```

Expected state:

- `db` is healthy.

- `api` is healthy.

- `ui` is running.

- `web` is running and exposes `127.0.0.1:8080`.

## Common errors

If port `8080` is busy, start with a temporary override:

```bash
WEB_HOST_PORT=8081 docker compose up --build
curl "http://127.0.0.1:8081/"
curl "http://127.0.0.1:8081/api/health/"
```

If the browser works on `5173` but not `8080`, inspect Nginx logs:

```bash
docker compose logs web
```

If the API container exits, inspect backend logs:

```bash
docker compose logs api
```

## Concepts to understand next

- Gunicorn runs Django through the WSGI application object.

- Nginx is a reverse proxy here: it accepts browser traffic and forwards it to internal Compose services.

- Compose service names such as `api` and `ui` work inside Docker networking, not in the host browser.

- Keeping direct API/UI ports is useful for debugging even when Nginx is the main browser entry point.
