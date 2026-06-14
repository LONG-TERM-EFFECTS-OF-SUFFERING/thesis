# 02 - Docker frontend service

Story: US-002, Docker frontend service.

Status note: this document explains the final reviewed US-002 implementation.

## What this story added

This story connected the React/Vite frontend to the local Docker Compose stack. The app can now run as three local services:

- `db`: PostgreSQL.

- `api`: Django REST Framework.

- `ui`: React/Vite.

The frontend starts from Docker Compose, listens on a localhost port, reads its backend API base URL from Vite environment configuration and calls the existing backend health endpoint.

## Why this matters

Later stories will add research-project screens, saved queries and YouTube collection workflows. Those features need the frontend and backend to run together in a repeatable way. US-002 answers this question:

```text
Can a developer start the full local app without manually setting up the frontend each time?
```

The answer is now yes.

## File-by-file explanation

### `src/docker-compose.yml`

The Compose file now has a `ui` service in addition to `db` and `api`.

The `ui` service builds from:

```yaml
context: ./ui
```

Because Compose runs from `src/`, this points Docker to `src/ui`.

The frontend listens inside the container on port `5173`:

```yaml
ports:
    - '${UI_HOST_BIND:-127.0.0.1}:${UI_HOST_PORT:-5173}:5173'
```

The left side is the host address and host port. The right side is the container port.

The `api` service has a healthcheck that calls:

```text
http://127.0.0.1:8000/api/health/
```

The `ui` service waits for that healthcheck before starting. This avoids the frontend showing a failed backend check just because Django was still migrating or starting.

The `ui` command runs:

```bash
npm ci && npm run dev -- --host 0.0.0.0
```

`npm ci` refreshes the container's `node_modules` volume from `package-lock.json`. The `--host 0.0.0.0` part lets Vite accept browser traffic through Docker's port mapping.

### `src/.env.example`

This is the Compose-level environment template. Copy it to `src/.env` when you need to change Docker host ports or the frontend proxy target.

Important variables:

```text
UI_HOST_BIND=127.0.0.1
UI_HOST_PORT=5173
VITE_API_BASE_URL=/api
VITE_API_PROXY_TARGET=http://api:8000
API_HOST_PORT=8000
POSTGRES_HOST_PORT=5432
```

The real `src/.env` file is local and ignored by Git.

### `src/ui/Dockerfile`

The frontend Dockerfile uses `node:24-alpine`, installs dependencies with `npm ci`, copies the frontend source and switches to the non-root `node` user.

Running as `node` matters because the container bind-mounts `src/ui`. If the container created build output as root, the host could end up with root-owned frontend files.

### `src/ui/vite.config.ts`

The Vite config sets up the dev-server proxy. By default, browser requests to:

```text
/api/health/
```

are proxied to:

```text
http://api:8000/api/health/
```

Inside Docker Compose, `api` is the backend service name. For local npm runs outside Docker, `src/ui/.env.example` points the proxy target to `http://127.0.0.1:8000`.

The config trims blank proxy values and derives the proxy path from `VITE_API_BASE_URL`, so a changed API base path does not silently bypass the proxy.

### `src/ui/src/apiConfig.ts`

This helper normalizes the frontend API base URL.

Examples:

```text
empty value -> /api
api -> /api
/api/ -> /api
http://127.0.0.1:8000/api/ -> http://127.0.0.1:8000/api
```

This keeps URL joining out of React components.

### `src/ui/src/apiClient.ts`

This module calls the backend health endpoint and checks that the JSON response includes:

```json
{ "status": "ok" }
```

If the response is missing, invalid or not `ok`, the frontend reports the backend as unavailable.

### `src/ui/src/App.tsx`

The app screen shows the local stack status, the backend health result and the configured API base URL.

It retries the initial health check a few times with a timeout. That gives the backend time to finish startup and prevents the UI from staying in a permanent checking state if a request hangs.

### `src/ui/tests/apiConfig.test.ts`

These tests cover the API base URL normalization and URL joining helper. They use Node's built-in test runner, so the story did not add a separate test framework.

## How the services connect

```text
Browser
  -> http://127.0.0.1:5173
  -> ui container
  -> Vite proxy for /api
  -> api container at http://api:8000
  -> db container at PostgreSQL port 5432
```

The browser never connects directly to `http://api:8000`; that service name only exists inside Docker Compose. The browser talks to Vite on localhost, and Vite proxies `/api` requests to the backend container.

## Commands

Run the full stack from `src`:

```bash
docker compose up --build
```

Run it in the background:

```bash
docker compose up --build -d
```

Check the frontend through the host port:

```bash
curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/"
```

Check the backend through the frontend proxy:

```bash
curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/api/health/"
```

Check the backend directly:

```bash
curl "http://127.0.0.1:${API_HOST_PORT:-8000}/api/health/"
```

Run frontend checks from `src/ui`:

```bash
npm test
npm run lint
npm run build
```

Run frontend checks inside the container from `src`:

```bash
docker compose exec ui npm test
docker compose exec ui npm run lint
docker compose exec ui npm run build
```

## Manual checks

After `docker compose up --build -d`, run:

```bash
docker compose ps
```

Expected state:

- `db` is healthy.

- `api` is healthy.

- `ui` is running.

Then open:

```text
http://127.0.0.1:5173
```

The page should show the backend health result as `ok`.

## Common errors

## Concepts to understand next

- Vite exposes browser environment variables only when they start with `VITE_`.

- Docker Compose service names, such as `api`, are available to other containers but not to the host browser.

- A bind mount lets the container see local source files.

- A named volume can preserve container-only dependencies such as `node_modules`.

- A healthcheck lets Compose wait for a service to be ready, not merely started.
