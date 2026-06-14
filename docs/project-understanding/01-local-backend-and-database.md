# 01 - Local backend and database

Story: US-001, Docker backend and database services.

Status note: this document explains the final reviewed US-001 implementation.

## What this story added

This story created the first active backend foundation for the thesis app. Before this, `src/api` only had a dependency file. Now it has a small Django project that can:

- run locally with SQLite for quick development.

- run through Docker Compose with PostgreSQL for reproducible validation.

- apply Django migrations.

- expose a health endpoint at `/api/health/`.

- run a small backend test suite.

- read local overrides from an API-local `.env` file.

- bind Docker ports to localhost by default.

- keep backend and frontend implementation files in nested repositories while the main repo owns shared Compose files.

The goal is not to build the research features yet. The goal is to prove that the backend and database environment works.

## Why this matters

Later stories will add research projects, saved queries, collection runs, YouTube API logging and stored YouTube data. All of that needs a working backend and database first.

US-001 answers the basic question:

```text
Can this project run a Django backend and a database in a reproducible way?
```

The answer is now yes.

## The Big Picture

There are two ways to run the backend:

```text
Quick development:
    Your machine -> Python virtual environment -> Django -> SQLite file

Reproducible validation:
    Your machine -> Docker Compose -> api container -> db container -> PostgreSQL
```

SQLite is faster and easier for quick experiments. PostgreSQL is the database that matters for story validation and thesis reproducibility.

## Repository layout decision

After the review fixes, the app development layout changed:

```text
thesis repo
    -> tracks thesis docs, BMAD artifacts and project-understanding docs
    -> tracks src/docker-compose.yml and src/.env.example
    -> ignores nested app implementation files

src/
    -> contains development projects and local orchestration
    -> contains src/docker-compose.yml
    -> contains src/.env.example

src/api/
    -> backend Django project
    -> has its own Git repository

src/ui/
    -> frontend project
    -> has its own Git repository
```

The API and UI are not Git submodules. A submodule is a formal pointer from the parent repo to a specific commit in another repo. This project is not using that mechanism.

Instead, `src/api` and `src/ui` are nested development repositories that live inside the working tree. The main thesis repo tracks only the shared root orchestration files in `src/`, especially `src/docker-compose.yml` and `src/.env.example`, while ignoring API and UI implementation files. That keeps the thesis/documentation history separate from app-development history while still letting Compose stay reproducible from the main repo.

## File-by-file explanation

### `src/api/.env.example`

This file lists environment variables a developer can use.

Important examples:

```text
DATABASE_ENGINE=sqlite
SQLITE_DATABASE_PATH=src/api/db.sqlite3
POSTGRES_DB=opentube_insights
POSTGRES_USER=opentube_insights
POSTGRES_PASSWORD=opentube_insights
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_HOST_BIND=127.0.0.1
POSTGRES_HOST_PORT=5432
API_HOST_BIND=127.0.0.1
API_HOST_PORT=8000
```

Think of this file as a template. It shows the names and default values, but it is not the secret production configuration.

If you copy this file to `src/api/.env`, Django reads that API-local `.env` file for local settings. Your shell environment still wins if both places define the same variable.

Django reads `src/api/.env` for local backend runs. Docker Compose uses `src/.env` for Compose-level port and frontend proxy overrides.

### `src/docker-compose.yml`

This file tells Docker Compose how to run the backend and database together. US-002 later adds the frontend service to the same file.

It defines two services:

```text
db
api
```

The `db` service uses PostgreSQL:

```yaml
image: postgres:18-alpine
```

The `api` service builds from:

```yaml
context: ./api
```

Because the Compose file lives in `src/`, this means Docker looks inside `src/api` for the backend Dockerfile and source code.

The API container sets:

```yaml
DATABASE_ENGINE: postgresql
POSTGRES_HOST: db
```

This is important. Inside Docker Compose, the backend does not connect to `localhost` for PostgreSQL. It connects to the service name `db`.

The host port mappings bind to localhost:

```yaml
127.0.0.1:8000
127.0.0.1:5432
```

This means the services are available from your computer, but not intentionally exposed on every network interface. If port `8000` or `5432` is busy, change `API_HOST_PORT` or `POSTGRES_HOST_PORT` in `src/.env`, or pass those variables directly in your shell.

The API command is:

```bash
python manage.py migrate &&
python manage.py runserver 0.0.0.0:8000
```

That means: run migrations first, and if migrations succeed, start Django.

The `depends_on` health condition tells Compose to wait until PostgreSQL is healthy before starting the API.

### `src/api/Dockerfile`

This file describes how to build the backend container image.

Step by step:

```dockerfile
FROM python:3.14-slim
```

Start with a small Python 3.14 image.

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
```

These settings are common for Python containers:

- `PYTHONDONTWRITEBYTECODE=1` avoids creating `.pyc` files.

- `PYTHONUNBUFFERED=1` makes logs print immediately.

```dockerfile
WORKDIR /app
```

Inside the container, use `/app` as the working folder.

```dockerfile
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
```

Copy and install Python dependencies.

```dockerfile
COPY . .
```

Copy the backend source code into the container.

```dockerfile
EXPOSE 8000
```

Document that the container listens on port `8000`.

### `src/api/.dockerignore`

This file tells Docker what not to copy into the image.

It excludes things like:

- `venv/`.

- `.venv/`.

- `__pycache__/`.

- `.env`.

- `db.sqlite3`.

- `*.sqlite3`.

- test cache.

- static/media output.

This keeps the Docker image cleaner and avoids copying local development artifacts.

### `src/api/requirements.txt`

This file pins backend Python dependencies:

```text
asgiref==3.11.1
Django==6.0.5
djangorestframework==3.17.1
psycopg[binary]==3.3.4
python-dotenv==1.2.1
sqlparse==0.5.5
```

The important ones are:

- `Django`: backend framework.

- `djangorestframework`: API support.

- `psycopg[binary]`: PostgreSQL driver.

- `python-dotenv`: reads `.env` files without requiring you to export every variable manually.

Do not change these versions casually. They are part of the current project stack.

### `src/api/manage.py`

This is Django's command runner.

When you run:

```bash
python manage.py migrate
```

the file sets:

```python
DJANGO_SETTINGS_MODULE=opentube_insights_api.settings
```

Then it asks Django to execute the command.

### `src/api/opentube_insights_api/settings.py`

This is the main backend configuration file.

Important parts:

```python
BASE_DIR = Path(__file__).resolve().parent.parent
```

This finds the API project folder using `pathlib.Path`.

```python
LOCAL_ENV = load_local_env()
```

This reads `src/api/.env` if it exists. The code uses `dotenv_values`, which reads values without changing `os.environ`.

```python
def env_bool(...)
def env_list(...)
```

These helper functions read environment variables and convert them into useful Python types.

```python
def build_database_config(...)
```

This function chooses SQLite or PostgreSQL based on `DATABASE_ENGINE`.

If `DATABASE_ENGINE=sqlite`, Django uses:

```python
django.db.backends.sqlite3
```

If `DATABASE_ENGINE=postgresql`, Django uses:

```python
django.db.backends.postgresql
```

This is the central switch that allows quick local SQLite development and Docker PostgreSQL validation.

Relative SQLite paths are resolved from the API project root. With `SQLITE_DATABASE_PATH=db.sqlite3`, the local SQLite database lives at `src/api/db.sqlite3`.

```python
INSTALLED_APPS = [
    ...
    "rest_framework",
    "core",
]
```

This tells Django to load Django REST Framework and the local `core` app.

```python
ROOT_URLCONF = "opentube_insights_api.urls"
```

This tells Django where the main URL configuration lives.

### `src/api/opentube_insights_api/urls.py`

This file connects top-level URLs.

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
]
```

This means:

- `/admin/` goes to Django admin.

- `/api/...` goes to routes from `core.urls`.

### `src/api/opentube_insights_api/asgi.py` and `src/api/opentube_insights_api/wsgi.py`

These are standard Django entry points.

For now, you do not need to deeply understand them. They are how deployment servers know how to start the Django app.

US-003 will later deal more with production-style server wiring.

### `src/api/core/apps.py`

This defines the Django app named `core`.

The `core` app currently holds shared/simple backend code, including the health endpoint.

### `src/api/core/urls.py`

This file maps URLs inside `/api/`.

```python
urlpatterns = [
    path("health/", health, name="api-health"),
]
```

Because `opentube_insights_api.urls` includes `core.urls` under `api/`, this becomes:

```text
/api/health/
```

### `src/api/core/views.py`

This file contains the health endpoint:

```python
@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})
```

- `@api_view(["GET"])` means the endpoint accepts GET requests.

- `Response({"status": "ok"})` returns JSON.

This endpoint does not touch the database. That is intentional. A health check should stay simple.

### `src/api/core/tests.py`

This file tests three important things:

1. Database configuration selection.

2. Environment helper edge cases.

3. Health endpoint behavior.

The database tests check that `build_database_config` can produce SQLite and PostgreSQL settings from environment-like values. They also check that an explicitly empty environment stays empty instead of accidentally falling back to your real shell environment.

The health test checks that the URL named `api-health` returns:

```json
{ "status": "ok" }
```

### `.gitignore`

This file tells Git what not to track.

Important project-specific choices:

- `src/` is ignored by the thesis repo because active API/UI development is managed inside nested repositories, not as files tracked by the thesis repo.

- `db.sqlite3` is ignored because it is a local database file.

- Python cache folders and frontend build folders are ignored.

## How the files connect

Here is the request path for the health endpoint:

```text
Browser or curl
    -> http://127.0.0.1:8000/api/health/
    -> opentube_insights_api/urls.py sees "api/"
    -> core/urls.py sees "health/"
    -> core/views.py calls health()
    -> DRF returns {"status":"ok"}
```

Here is the Docker startup path:

```text
docker compose up --build
  -> reads src/docker-compose.yml
  -> starts db service
  -> waits for pg_isready healthcheck
  -> builds api image from src/api/Dockerfile
  -> starts api service
  -> api runs python manage.py migrate
  -> api starts Django on 0.0.0.0:8000
```

Here is the database-selection path:

```text
Django starts
  -> loads opentube_insights_api/settings.py
  -> calls build_database_config()
  -> reads DATABASE_ENGINE
  -> chooses sqlite or postgresql
```

## Commands to run

### Quick SQLite path

```bash
cd src/api
python manage.py migrate
python manage.py test core
python manage.py check
```

Use this path when you want quick feedback.

### Docker PostgreSQL path

```bash
cd src
docker compose config
docker compose up --build
docker compose exec api python manage.py migrate
docker compose exec api python manage.py test core
docker compose exec api python manage.py check
docker compose exec api python manage.py shell
docker compose exec api sh
docker compose exec db psql -U opentube_insights -d opentube_insights
```

Use this path when validating story completion.

If you want Compose to use variables from `src/.env`, use:

```bash
cd src
docker compose --env-file .env up --build
```

### Health check

```bash
curl http://127.0.0.1:8000/api/health/
```

Expected:

```json
{ "status": "ok" }
```

## Common errors

### PostgreSQL volume has old data

If the database image or credentials change, the existing Docker volume can conflict with the new configuration.

Only if you are comfortable deleting the local Docker database, run:

```bash
docker compose down --volumes
```

Then start again:

```bash
docker compose up --build
```

Run those Docker Compose commands from `src/`, because that is where `src/docker-compose.yml` lives.

## What you should understand before the next story

Before moving to US-002 or US-004, make sure these ideas feel familiar:

- A Django project has settings, URLs and app modules.

- `manage.py` runs Django commands.

- Environment variables let one codebase run in different modes.

- SQLite is a local file database.

- PostgreSQL is the reproducible database target.

- Docker Compose starts several services together.

- A health endpoint is a simple way to test if the backend is alive.

- Migrations apply database table changes.

You do not need to memorize every file. The important part is understanding how the pieces connect.
