# Reproducible local run (PostgreSQL)

Each part of the application can be run separately, but Docker Compose is the reference local environment for thesis validation. It runs the API, frontend, Nginx front door and PostgreSQL database with the same service wiring each time.

From this directory:

```bash
docker compose up --build
```

The `api` service waits for PostgreSQL to become healthy, runs migrations and then starts Django through Gunicorn on port `8000`. The `ui` service starts the Vite frontend on port `5173`. The `web` service starts Nginx on port `8080` and proxies `/api/` to the API service and `/` to the UI service.

The `ui` service bind-mounts `./ui` into the container and keeps container dependencies in the `ui-node-modules` Docker volume. The container runs `npm ci` on startup so the volume matches `package-lock.json`.

By default, Compose binds the Nginx front door, frontend, API and database to localhost only:

- Nginx front door: `127.0.0.1:8080`.

- Frontend: `127.0.0.1:5173`.

- API: `127.0.0.1:8000`.

- PostgreSQL: `127.0.0.1:5432`.

If you want to override the default values, copy `.env.example` to `.env` and change the desired variables.

Useful Compose variables:

- `UI_HOST_BIND`: frontend host bind address. Default: `127.0.0.1`.

- `UI_HOST_PORT`: frontend host port. Default: `5173`.

- `VITE_API_BASE_URL`: browser-facing API base path. Default: `/api`.

- `VITE_API_PROXY_TARGET`: in-Compose Vite proxy target. Default: `http://api:8000`.

- `WEB_HOST_BIND`: Nginx host bind address. Default: `127.0.0.1`.

- `WEB_HOST_PORT`: Nginx host port. Default: `8080`.

- `OPENTUBE_DEFAULT_OWNER_USERNAME`: backend fallback owner for local unauthenticated project requests. Default: `local-researcher`.

- `GUNICORN_WORKERS`: local Gunicorn worker count. Default: `2`.

- `GUNICORN_TIMEOUT`: local Gunicorn request timeout in seconds. Default: `60`.

```bash
WEB_HOST_PORT=8081
UI_HOST_PORT=5174
API_HOST_PORT=8001
POSTGRES_HOST_PORT=5433
```

For a one-command Nginx port override, use the explicit port in follow-up smoke checks:

```bash
WEB_HOST_PORT=8081 docker compose up --build
curl "http://127.0.0.1:8081/"
curl "http://127.0.0.1:8081/api/health/"
```

Health check:

```bash
curl "http://127.0.0.1:${API_HOST_PORT:-8000}/api/health/"
```

Nginx front-door health check:

```bash
curl "http://127.0.0.1:${WEB_HOST_PORT:-8080}/api/health/"
```

Frontend health check through Vite:

```bash
curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/api/health/"
```

Useful Docker commands:

```bash
docker compose config
docker compose logs web
docker compose logs ui
docker compose logs api
docker compose logs db
docker compose exec ui npm test
docker compose exec ui npm run lint
docker compose exec api gunicorn --check-config -c gunicorn.conf.py opentube_insights_api.wsgi:application
docker compose exec api python manage.py migrate
docker compose exec api python manage.py check
docker compose exec -e OPENTUBE_ALLOW_ORCHESTRATION_TEST_SKIP=1 api python manage.py test core
docker compose exec api python manage.py shell
docker compose exec api sh
docker compose exec db psql -U opentube_insights -d opentube_insights
docker compose down
```

PostgreSQL stores local data in the `postgres-data` Docker volume. If you change `POSTGRES_DB`, `POSTGRES_USER` or `POSTGRES_PASSWORD` after the first startup, the existing volume can still contain the old initialized database. To intentionally reset the local PostgreSQL database, remove the Compose volume:

```bash
docker compose down --volumes
```

Only do this when you are comfortable deleting the local development database.

For Docker Compose port and frontend proxy overrides, copy `.env.example` to `.env`.

## Validation

Once the containers are running:

```bash
curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/"
curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/api/health/"
curl "http://127.0.0.1:${API_HOST_PORT:-8000}/api/health/"
curl "http://127.0.0.1:${WEB_HOST_PORT:-8080}/"
curl "http://127.0.0.1:${WEB_HOST_PORT:-8080}/api/health/"
curl -sS -X POST "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/" \
  -H "Content-Type: application/json" \
  -d '{"name":"Cali polarization study","description":"Local thesis test","default_language":"es"}'
curl -sS "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/"
docker compose down
```
