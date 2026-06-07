# Story 1.1: Docker Backend and Database Services

Status: done

<!-- Ultimate context engine analysis completed - comprehensive developer guide created. -->

## Story

As a researcher-developer,
I want the backend and database to run locally with Docker,
so that the data environment is reproducible on my machine.

## Acceptance Criteria

1. Docker Compose can start a PostgreSQL database service and a Django REST Framework backend service from the project root or a clearly documented compose path.
2. The backend supports environment-driven database selection: SQLite is allowed for quick local development, while the Docker Compose backend uses PostgreSQL for reproducible thesis validation.
3. The backend dependency file includes Django, Django REST Framework, PostgreSQL driver support and the minimal runtime packages needed by the container.
4. Backend environment variables are documented in an example environment file and do not require real secrets for local development.
5. Migrations can run locally through Docker, and the command is documented.
6. The backend exposes at least one lightweight health endpoint or equivalent smoke-check URL so the developer can confirm the service is running.
7. Docker Compose waits for PostgreSQL readiness before running migrations or starting the backend process.

## BDD Acceptance Criteria

### AC1: Compose starts backend and database

Given Docker is installed on the developer machine,
When the developer runs the documented Docker Compose startup command,
Then PostgreSQL starts successfully,
And the Django/DRF backend starts successfully,
And the backend listens on a documented local port.

### AC2: Backend supports local SQLite and reproducible PostgreSQL configuration

Given the backend is running outside Docker for quick local development,
When Django loads its settings,
Then SQLite can be selected through documented environment configuration,
And the SQLite database file location is documented.

Given the backend is running in Docker Compose,
When Django loads its settings,
Then PostgreSQL is selected through documented environment configuration,
And database connection values come from environment variables,
And the backend connects to the Compose database service by service name.

### AC3: Local migrations run through Docker

Given the Compose database service is healthy,
When the developer runs the documented migration command,
Then Django applies migrations without requiring manual local PostgreSQL setup.

### AC4: Environment variables are reproducible and documented

Given a new developer checks out the repository,
When they inspect the documented environment file,
Then they can identify every required backend/database variable,
And local defaults are safe for development,
And secret placeholders are not committed as real production secrets.

## Tasks / Subtasks

- [x] Establish active backend scaffold in `src/api` (AC: 1, 2, 3, 6)
  - [x] Create or complete the Django project under `src/api` if it does not already exist (`manage.py`, project package, settings module, URL config, WSGI/ASGI entry points).
  - [x] Add `rest_framework` to `INSTALLED_APPS`.
  - [x] Add a minimal health endpoint such as `GET /api/health/` returning JSON.
  - [x] Keep the backend simple; do not implement research-project, saved-query or YouTube collection models in this story.

- [x] Align backend dependencies (AC: 3)
  - [x] Update `src/api/requirements.txt` to include Django, Django REST Framework, `psycopg` or another PostgreSQL driver, and any minimal settings/runtime helpers used by the backend.
  - [x] Resolve the current mismatch: active `src/api/requirements.txt` only lists Django/asgiref/sqlparse, while `src/vault/api/requirements.txt` includes DRF, CORS, Gunicorn, psycopg, python-dotenv and requests.
  - [x] Prefer a stable, documented dependency set over broad unpinned upgrades. If using Django 5.2 LTS for thesis stability, document the choice; if keeping Django 6.0.x, verify DRF compatibility and document the choice.

- [x] Configure environment-driven Django database settings (AC: 2, 4)
  - [x] Read `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, database selection and PostgreSQL connection values from environment variables.
  - [x] Support a documented SQLite option for quick local development outside Docker.
  - [x] Use PostgreSQL as the Docker Compose and reproducibility-validation database.
  - [x] Use `django.db.backends.postgresql` for the PostgreSQL path and `django.db.backends.sqlite3` for the SQLite fallback path.
  - [x] Keep local defaults developer-friendly, but make the committed example file clearly non-production.
  - [x] Use `settings.AUTH_USER_MODEL` patterns later for app models; do not define a custom user model in this story.

- [x] Add Docker files for backend and database service wiring (AC: 1, 2, 5, 7)
  - [x] Add a backend Dockerfile in the active backend area, expected location `src/api/Dockerfile`.
  - [x] Add a Compose file in a clear location, preferably `docker-compose.yml` at the project root for beginner-friendly `docker compose up --build`.
  - [x] Define a `db` service using an official PostgreSQL image and a named volume for persistent local database data.
  - [x] Define an `api` service built from `src/api`, using environment variables that select PostgreSQL and set `POSTGRES_HOST=db`.
  - [x] Add a database healthcheck using `pg_isready`.
  - [x] Configure the backend service to wait for database health before running migrations or starting the server.

- [x] Document local run, migration and troubleshooting commands (AC: 4, 5, 6)
  - [x] Add or update a beginner-friendly local development document, such as `src/api/README.md` or a root-level app setup section.
  - [x] Include commands for SQLite quick development, PostgreSQL Docker startup, shutdown, logs, shell access and migrations.
  - [x] Clearly label SQLite as a convenience path and PostgreSQL as the required reproducibility/validation path.
  - [x] Include expected local URLs, especially the health endpoint.
  - [x] Explain how to reset the local database volume only as an intentional troubleshooting step.

- [x] Verify the story outcome (AC: 1-7)
  - [x] Run `docker compose config` to validate Compose syntax.
  - [x] Run `docker compose up --build` and confirm both `db` and `api` start.
  - [x] Run the documented migration command in Docker.
  - [x] If SQLite support is implemented, run the documented local SQLite migration/check command.
  - [x] Confirm the health endpoint responds.
  - [x] Capture any command failures and fix the underlying configuration rather than marking the story complete.

### Review Findings

- [x] [Review][Patch] Local `.env` overrides are documented but not loaded [src/api/README.md:73]
- [x] [Review][Patch] Relative SQLite database paths depend on the current working directory [src/api/.env.example:8]
- [x] [Review][Patch] Docker build context can include API-local `.env` or `.venv` files [src/api/.dockerignore:1]
- [x] [Review][Patch] Environment helper tests cannot isolate an explicitly empty environment [src/api/opentube_insights_api/settings.py:19]
- [x] [Review][Patch] Host port bindings are fixed and exposed on all interfaces [src/docker-compose.yml:8]
- [x] [Review][Patch] PostgreSQL credential changes can conflict with the existing named volume [src/api/README.md:63]
- [x] [Review][Patch] Docker shell access command is missing from the backend README [src/api/README.md:52]
- [x] [Review][Patch] Django 6.0.x dependency choice is not documented [src/api/requirements.txt:2]

## Dev Notes

### Story Context

This is the first story in EPIC-001, "reproducible local foundation." The epic goal is to make the app run locally in a reproducible environment so the thesis project can be installed and evaluated consistently. In Sprint 1, this story is grouped with the Docker frontend story and the first research-record stories, so this backend/database foundation must be simple and stable enough for later stories to build on.

Sources:

- `docs/product_backlog.md`, EPIC-001 and US-001.
- `docs/sprint_planning.md`, Sprint 1.

### Current Repository State

- The active backend path is `src/api`, but it currently contains only `requirements.txt`.
- The active frontend path is `src/ui`; that folder is for US-002 and should not be changed for this backend/database story unless a small documentation reference is unavoidable.
- `src/vault/` contains an earlier generated scaffold with a Django API, Docker Compose, frontend Dockerfile and Nginx config. Treat it as reference material only. Do not move the entire vault into active code without review because `.codex/AGENTS.md` says the vault was generated before proper documentation.
- `_bmad-output/implementation-artifacts/` had no previous story files at story creation time, so there is no previous-story intelligence to preserve.
- No `sprint-status.yaml` exists in `_bmad-output/implementation-artifacts/`; this story file was created directly from the requested `US-001`.

### Architecture and Stack Guardrails

- Thesis stack selection requires Django REST Framework for the backend, PostgreSQL for the reproducible database target, React/Vite for frontend, Nginx for web server/reverse proxy, Gunicorn for production-style backend serving, and Docker for containerization. For US-001, implement only the Django/DRF backend, PostgreSQL Docker service and optional SQLite quick-dev settings path; US-002 covers frontend Docker, and US-003 covers Nginx/Gunicorn-ready local wiring.
- The project scope requires all services to be containerized for consistent and reproducible deployment.
- Database design is Django ORM on PostgreSQL. SQLite is allowed as a quick development convenience, but PostgreSQL remains the database of record for thesis reproducibility and story validation. Future app tables should use Django-managed UUID primary keys, `settings.AUTH_USER_MODEL` for user references, `models.JSONField` for PostgreSQL JSONB, Django timestamp fields, choices and `CheckConstraint` where applicable. US-001 does not need to create those domain models, but the settings and database foundation must support them.
- The ORM reduces the burden of supporting both SQLite and PostgreSQL, but it does not erase all behavioral differences. Any story touching models, migrations, constraints, JSON fields or query behavior must be verified with PostgreSQL before completion.
- Keep the implementation beginner-friendly. Prefer explicit files, clear environment variables and documented commands over clever abstractions.

Sources:

- `content/06-project_scope.tex`, Technology.
- `content/09_1_1-stack_evaluation_and_selection.tex`, Selected technology stack.
- `content/09_1_3-database_design.tex`, Implementation model.
- `docs/database_schema.md`, Django ORM implementation notes.

### Active vs Vault Reference

Useful vault patterns:

- `src/vault/docker-compose.yml` demonstrates `db`, `api`, `frontend` and `nginx` services, database healthcheck, environment variable names and `POSTGRES_HOST=db`.
- `src/vault/api/Dockerfile` demonstrates a simple Python image, `/app` workdir, requirements installation and app copy.
- `src/vault/api/thesis_api/settings.py` demonstrates environment-driven settings, PostgreSQL database config, CORS settings and DRF installation.
- `src/vault/.env.example` lists practical local development variables.
- `src/vault/DEVELOPMENT.md` shows useful local URLs and developer commands.

Boundaries:

- Do not implement the vault frontend, Nginx service or production Gunicorn story scope as part of US-001 unless needed for a minimal backend smoke test.
- Do not copy vault domain models into active code for this story. Project and saved-query models belong to later stories US-004 and US-005.
- If reusing vault snippets, adapt paths from `src/vault/api` to the active `src/api` structure.

### File Structure Requirements

Expected files to create or update:

- `docker-compose.yml`: root-level Compose file for `db` and `api`.
- `.env.example` or a clearly named local env example file: documented development defaults.
- `src/api/Dockerfile`: backend container image.
- `src/api/requirements.txt`: backend dependencies.
- `src/api/manage.py`: Django management entry point, if missing.
- `src/api/<project_package>/settings.py`: environment-driven Django settings with SQLite and PostgreSQL branches.
- `src/api/<project_package>/urls.py`: route health endpoint.
- `src/api/<project_package>/wsgi.py` and `asgi.py`: standard Django entry points.
- `src/api/README.md` or equivalent setup docs: local run, migrations and troubleshooting.

Use a clear Django project package name such as `thesis_api` unless the implementation discovers a stronger existing naming convention.

### Environment Variables

Minimum documented local variables:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_ENGINE` or an equivalent documented database selector, with allowed values for SQLite and PostgreSQL
- `SQLITE_DATABASE_PATH` or an equivalent documented SQLite file path, if SQLite is supported
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

Optional variables may be included if the implementation uses them:

- `CORS_ALLOWED_ORIGINS`
- `YOUTUBE_API_KEY`
- `LLM_API_KEY`

Do not require live YouTube or LLM credentials for this story.

### Testing Requirements

Required command checks:

- `docker compose config`
- `docker compose up --build`
- `docker compose exec api python manage.py migrate`
- Health endpoint check, for example `curl http://localhost:8000/api/health/`

Recommended Django checks:

- SQLite quick-dev check, if documented: `python src/api/manage.py migrate` or equivalent from the backend working directory
- `docker compose exec api python manage.py check`
- `docker compose exec api python manage.py showmigrations`

If Docker is unavailable in the implementation environment, document that limitation in the completion notes and provide the exact commands for Brandon to run locally.

### Latest Technical Notes

- Django 5.2 is an LTS release and supports Python 3.10 through 3.14 in current official docs; this makes it a good thesis-stability choice if the project does not need Django 6-only features. Source: https://docs.djangoproject.com/en/dev/releases/5.2/
- Django REST Framework official requirements currently include Django 4.2, 5.0, 5.1, 5.2 and 6.0, plus Python 3.10 through 3.14. Source: https://www.django-rest-framework.org/
- Docker Compose discovers `compose.yaml` or `docker-compose.yaml` when no `-f` flag is provided, which supports a beginner-friendly root-level Compose file. Source: https://docs.docker.com/reference/cli/docker/compose/
- Compose `healthcheck` supports `CMD` and `CMD-SHELL`, and can be used with `pg_isready` for database readiness. Source: https://docs.docker.com/reference/compose-file/services/
- The official PostgreSQL Docker image supports Alpine variants, but extra PostgreSQL extensions can be simpler on the default Debian-based image. Since this project has no PostGIS requirement yet, either a versioned default image or a versioned Alpine image is acceptable if documented. Source: https://hub.docker.com/_/postgres

### Git Intelligence

Recent commits are documentation and LaTeX-tooling oriented, not backend implementation commits:

- `90fe2fe chore(config): update the formatting related files with the latest version of the latex stack and edit the selection of Django for the backend`
- `5922389 style(content): update LaTeX files for consistent formatting and clarity`
- `3d17c06 chore(config): update configuration files and enhance documentation`
- `fc64e57 add LaTeX tooling configuration with formatter, linter, build system and editor integration`
- `46ffce5 finish YouTube Data API review subsection`

Implication: this is effectively the first active backend implementation pass. Do not assume mature app conventions beyond the thesis docs and the reference vault.

### Completion Criteria

The dev agent may mark this story complete only when:

- The active backend is runnable in Docker.
- SQLite, if implemented, is documented as a quick local development path rather than the reproducible thesis target.
- PostgreSQL is configured as Django's Docker Compose database.
- Migrations run successfully through Docker.
- Migrations run successfully through SQLite if the SQLite path is documented.
- Environment variables and commands are documented clearly enough for a beginner developer.
- Any unverified Docker command is explicitly listed in completion notes with the reason it could not be run.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `src/api/venv/bin/python -m pip install -r src/api/requirements.txt` (needed network approval; installed DRF and psycopg in the local venv).
- `src/api/venv/bin/python src/api/manage.py test core` initially failed because `api-health` was not routed; passed after adding `core.urls` and `core.views.health`.
- `src/api/venv/bin/python src/api/manage.py migrate` applied default Django SQLite migrations successfully.
- `docker compose config` validated the Compose file.
- `docker compose up --build -d` first failed with `postgres:18-alpine` because an existing PostgreSQL 16 volume used the older data-directory layout; fixed by using `postgres:16-alpine`.
- Final Docker validation passed with `docker compose exec -T api python manage.py migrate`, `docker compose exec -T api python manage.py check`, `docker compose exec -T api python manage.py test core`, `docker compose exec -T api python manage.py showmigrations` and `curl http://127.0.0.1:8000/api/health/`.
- Code review patches passed with `src/api/venv/bin/python src/api/manage.py test core`, `src/api/venv/bin/python src/api/manage.py check`, `docker compose config`, `docker compose build api`, `docker compose exec -T api python manage.py check`, `docker compose exec -T api python manage.py showmigrations` and `curl http://127.0.0.1:8000/api/health/`.

### Completion Notes List

- Implemented a minimal active Django 6.0.5 + DRF backend under `src/api`.
- Added environment-driven database configuration with SQLite for quick local development and PostgreSQL for Docker-based thesis validation.
- Added a lightweight `GET /api/health/` endpoint returning `{"status":"ok"}`.
- Added `src/docker-compose.yml` wiring for `db` and `api`; the API waits for the database healthcheck, runs migrations, then starts Django.
- Pinned backend runtime dependencies: Django 6.0.5, DRF 3.17.1, psycopg 3.3.4, python-dotenv 1.2.1, asgiref 3.11.1 and sqlparse 0.5.5.
- Added beginner-facing backend README commands for SQLite, Docker PostgreSQL, migrations, logs, shell access, checks, port overrides and reset behavior.
- Updated `.gitignore` so the main thesis repo ignores `src/`; API and UI development are managed as nested repositories, not Git submodules.
- Moved Compose orchestration to `src/docker-compose.yml` and moved the local environment template to `src/api/.env.example`.
- Final validation passed locally and in Docker. The Compose stack was stopped after verification.

### File List

- `.gitignore`
- `src/docker-compose.yml`
- `src/api/.dockerignore`
- `src/api/.env.example`
- `src/api/Dockerfile`
- `src/api/README.md`
- `src/api/core/__init__.py`
- `src/api/core/apps.py`
- `src/api/core/tests.py`
- `src/api/core/urls.py`
- `src/api/core/views.py`
- `src/api/manage.py`
- `src/api/requirements.txt`
- `src/api/opentube_insights_api/__init__.py`
- `src/api/opentube_insights_api/asgi.py`
- `src/api/opentube_insights_api/settings.py`
- `src/api/opentube_insights_api/urls.py`
- `src/api/opentube_insights_api/wsgi.py`

### Change Log

- 2026-06-01: Implemented US-001 backend/database Docker foundation and marked story ready for review.
- 2026-06-01: Applied code review patches, revalidated the Docker/backend path and marked US-001 done.
- 2026-06-05: Documented the `src/` development layout: API/UI are nested repositories, not submodules, and development files are ignored by the main thesis repo.
