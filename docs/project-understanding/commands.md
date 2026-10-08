# Commands

This page lists reusable commands for the thesis app and explains what each one does.

Run commands from the folder shown in each section. The main thesis repo tracks shared root Compose files in `src/`, while active API/UI development commands happen inside the nested repositories `src/api` and `src/ui`.

## Backend (quick SQLite development)

```bash
cd src/api
python manage.py migrate
```

Runs Django migrations. With the default settings, this uses SQLite and creates or updates `src/api/db.sqlite3`.

```bash
python manage.py runserver 8000
```

Starts the Django development server on port `8000`.

```bash
python manage.py test core
```

Runs the tests in the `core` Django app.

```bash
python manage.py check
```

Runs Django's system checks. This catches common configuration problems.

## Docker compose (reproducible local stack)

```bash
cd src
docker compose config
```

Checks whether `src/docker-compose.yml` is valid after environment variables and defaults are resolved.

```bash
docker compose up --build
```

Builds the backend and frontend images, then starts the database, API and UI containers in the foreground. The terminal shows logs while the services run.

```bash
docker compose up --build -d
```

Builds and starts the containers in the background. The `-d` means detached mode.

To override the default ports, you can use the following environment variables:

- `WEB_HOST_PORT`: when something else is already using port `8080`.

- `UI_HOST_PORT`: when something else is already using port `5173`.

- `API_HOST_PORT`: when something else is already using port `8000`.

- `POSTGRES_HOST_PORT`: when something else is already using port `5432`.

```bash
docker compose ps
```

Shows whether the `api`, `db`, `ui` and `web` services are running and which ports are exposed.

```bash
docker compose logs web
docker compose logs ui
docker compose logs api
docker compose logs db
```

Shows logs for the Nginx front door, frontend, backend or database container.

```bash
docker compose exec api gunicorn --check-config -c gunicorn.conf.py opentube_insights_api.wsgi:application
```

Checks the Gunicorn configuration inside the API container.

```bash
docker compose exec api python manage.py migrate
```

Runs Django migrations inside the API container. This validates the PostgreSQL path because the container uses `DATABASE_ENGINE=postgresql`.

```bash
docker compose exec api python manage.py check
```

Runs Django's system checks inside the API container.

```bash
docker compose exec -e OPENTUBE_ALLOW_ORCHESTRATION_TEST_SKIP=1 api python manage.py test core
```

Runs the backend tests inside the API container. The environment flag makes the root-orchestration-file checks skip explicitly because the API image intentionally contains only backend files.

```bash
docker compose exec api python manage.py showmigrations
```

Shows which migrations Django sees and whether they have been applied.

```bash
docker compose exec api python manage.py shell
```

Opens Django's interactive Python shell inside the API container.

```bash
docker compose exec api sh
```

Opens a shell inside the API container. This is useful when you need to inspect files or run several Django commands manually.

```bash
docker compose exec db psql -U opentube_insights -d opentube_insights
```

Opens a PostgreSQL shell inside the database container using the default local development database and user.

```bash
docker compose --env-file .env up --build
```

Starts the stack while reading Compose override values from `src/.env`.

```bash
docker compose down
```

Stops and removes the running containers. The PostgreSQL data volume remains.

```bash
docker compose down --volumes
```

Stops containers and deletes the PostgreSQL data volume. Use this only when you intentionally want to erase the local Docker database.

## Health check

```bash
curl "http://127.0.0.1:${API_HOST_PORT:-8000}/api/health/"
```

Asks the backend health endpoint directly if the API is running.

Expected response:

```json
{ "status": "ok" }
```

```bash
curl "http://127.0.0.1:${WEB_HOST_PORT:-8080}/api/health/"
```

Asks the backend health endpoint through the Nginx front door.

```bash
curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/api/health/"
```

Asks the backend health endpoint through the Vite frontend proxy.

```bash
curl "http://127.0.0.1:${WEB_HOST_PORT:-8080}/"
```

Asks Nginx for the browser-facing frontend page.

## Project API

```bash
curl -sS -X POST "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/" \
  -H "Content-Type: application/json" \
  -d '{"name":"Cali polarization study","description":"Local thesis test","default_language":"es"}'
```

Creates a research project for the current effective owner. During local unauthenticated development, that owner defaults to `local-researcher`.

```bash
curl -sS "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/"
```

Lists research projects visible to the current effective owner.

Replace `<project-id>` with an `id` from the project create or list response.

```bash
curl -sS -X POST "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/<project-id>/queries/" \
  -H "Content-Type: application/json" \
  -d '{"name":"Cali mobility videos","search_term":"movilidad Cali","max_videos_to_discover":250,"structured_query_params":{"part":"snippet","type":"video","q":"movilidad Cali","maxResults":50}}'
```

Creates a saved YouTube search query inside one research project.

```bash
curl -sS "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/<project-id>/queries/"
```

Lists saved queries for one research project and effective owner.

```bash
cd src/api
python manage.py makemigrations --check --dry-run
```

Checks whether Django model changes are already represented by migration files.

## Collection runs

Replace `<query-id>` with an `id` from the saved query list response.

```bash
curl -sS -X POST "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/<project-id>/queries/<query-id>/runs/"
```

Starts a collection run from one saved query. The run is created as `pending` with a copy of the query's parameters (US-011).

```bash
cd src/api
venv/bin/python manage.py collect_runs
```

Collects every `pending` run, oldest first: it pages through YouTube `search.list` and stores the discovered videos (US-015). It needs `YOUTUBE_API_KEY` in `src/api/.env` and stops with `YOUTUBE_API_KEY is not configured.` without it. Each search page costs 100 quota units.

```bash
cd src
docker compose exec api python manage.py collect_runs
```

The same command inside the running Compose `api` container.

With `./run-local.sh` running in one terminal, run `collect_runs` from `src/api` in a second terminal, then click **Refresh** in the Collection runs panel. Nothing collects a run automatically: "Start run" only queues it as `pending`.

## 30-day purge

```bash
cd src/api
venv/bin/python manage.py purge_youtube_data --dry-run
venv/bin/python manage.py purge_youtube_data
```

Deletes YouTube data (channels, videos, comments, replies, statistics snapshots) fetched more than 30 days ago, as the YouTube API Services Developer Policies require (US-040). Runs, saved queries and request logs are kept. `--dry-run` prints what would be deleted and changes nothing. Run it at least once a day, and **not while `collect_runs` is running**: a video refreshed during the purge could still be deleted.

## Django admin

```bash
cd src/api
venv/bin/python manage.py createsuperuser
```

Creates an admin login, once per database. `run-local.sh` uses SQLite; with `DATABASE_ENGINE=postgresql`, run it again with that setting.

Then open `http://127.0.0.1:8000/admin/`. Collection runs, request logs and videos are read-only there. Open the UI as `http://localhost:5173/`, not `127.0.0.1`, while logged into the admin: browsers share cookies across ports, and the admin login would make UI saves fail with a CSRF `403`.

```bash
curl -sS "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/<project-id>/runs/"
```

Lists a project's collection runs, newest first, with status and totals (US-014).

Replace `<run-id>` with an `id` from that list.

```bash
curl -sS "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/<project-id>/runs/<run-id>/"
```

Shows one run with its request logs in order (US-014).

```bash
curl -sS "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/<project-id>/results/summary/"
```

Returns the project's results summary: counts of runs, videos, channels, comments, replies and statistics snapshots, and the date range its runs collected data (US-027).

```bash
curl -sS "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/<project-id>/results/summary/?date_from=2026-01-01&date_to=2026-03-31"
curl -sS "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/<project-id>/results/videos/"
```

The same summary narrowed to videos published in that range (both days included, UTC); add `&video=<video-id>` with an `id` from the second command to narrow to one video (US-029).

## Frontend commands

Run these from `src/ui`.

```bash
npm test
```

Runs the small frontend helper tests.

```bash
npm run dev
```

Starts the Vite frontend development server.

```bash
npm run build
```

Runs TypeScript build checks and creates production frontend assets.

```bash
npm run lint
```

Runs ESLint on the frontend source code.
