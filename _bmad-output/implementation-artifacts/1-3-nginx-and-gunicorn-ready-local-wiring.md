---
baseline_commit: 6764bd4c047329756dbd42efa78a4dc7ce34085b
---

# Story 1.3: Nginx and Gunicorn-ready Local Wiring

Status: done

<!-- Ultimate context engine analysis completed - comprehensive developer guide created. -->

## Story

As a researcher-developer,
I want local production-style service wiring,
so that the thesis app is closer to a reproducible deployment.

## Acceptance Criteria

1. The backend container can start Django through Gunicorn using the existing `opentube_insights_api.wsgi:application` entry point.
2. `src/docker-compose.yml` wires the local stack through an Nginx reverse proxy service without breaking the existing `db`, `api` and `ui` services.
3. Nginx routes `/api/` requests to the Django/Gunicorn API service and routes browser UI requests to the existing React/Vite UI service.
4. The production-style local stack is environment-driven and keeps localhost-only host bindings by default.
5. Minimal setup and validation steps are documented for the Gunicorn backend and Nginx front door.
6. Existing API, UI, database, project and saved-query behavior remains working through the direct service ports and through the Nginx front door.
7. US-003 does not add TLS, a deployment platform, auth, YouTube collection behavior, natural-language query translation, or a production static-asset pipeline beyond the minimal local Nginx proxy wiring.

## BDD Acceptance Criteria

### AC1: Backend starts with Gunicorn

Given Docker Compose is run from `src/`,
When the API service starts,
Then migrations run against PostgreSQL,
And Django is served by Gunicorn on container port `8000`,
And `GET /api/health/` returns `{"status":"ok"}`.

### AC2: Nginx is the local front door

Given the Compose stack is running,
When the developer opens the documented Nginx host URL,
Then Nginx serves the React/Vite app,
And requests to `/api/health/` through the same host URL are proxied to the API service.

### AC3: Existing development paths still work

Given the production-style local wiring has been added,
When the developer uses the direct UI and API host ports,
Then the existing Vite frontend, API health endpoint, project API and saved-query API still work.

### AC4: Documentation is enough for reproducible validation

Given a developer has a fresh checkout with Docker installed,
When they follow the documented setup and smoke-check commands,
Then they can validate Gunicorn, Nginx proxying, backend tests and frontend checks without guessing required ports or environment variables.

## Tasks / Subtasks

- [x] Add Gunicorn backend runtime wiring (AC: 1, 4, 6)
  - [x] Add `gunicorn==26.0.0` to `src/api/requirements.txt` unless implementation finds a documented incompatibility with the current Python/Django stack.
  - [x] Add a small `src/api/gunicorn.conf.py` or equivalent explicit command configuration for bind address, workers, timeout and stdout/stderr logging.
  - [x] Use `opentube_insights_api.wsgi:application`; do not create a second Django entry point.
  - [x] Keep quick local `python manage.py runserver` docs available for SQLite development.
  - [x] Add or update a backend validation command that checks the Gunicorn configuration before startup.

- [x] Wire Gunicorn into Compose without losing the existing stack (AC: 1, 2, 4, 6)
  - [x] Update the `api` service command in `src/docker-compose.yml` to run migrations and start Gunicorn instead of Django's development server.
  - [x] Preserve the current PostgreSQL environment values, `OPENTUBE_DEFAULT_OWNER_USERNAME`, API healthcheck and localhost-only `API_HOST_BIND`/`API_HOST_PORT` behavior.
  - [x] Do not change database selection rules, model definitions, migrations, project APIs or saved-query APIs as part of this story.

- [x] Add Nginx reverse proxy wiring (AC: 2, 3, 4, 6)
  - [x] Add an Nginx config under a clear root-owned path such as `src/nginx/default.conf`.
  - [x] Add a Compose service named `web` or `nginx` using an official Nginx image, preferably a pinned stable Alpine tag such as `nginx:1.30.3-alpine`.
  - [x] Proxy `/api/` to `http://api:8000` and preserve `Host`, `X-Forwarded-For` and `X-Forwarded-Proto` headers.
  - [x] Proxy `/` to the existing Vite UI service at `http://ui:5173`; keep `VITE_API_BASE_URL=/api` so browser API calls stay same-origin through Nginx.
  - [x] Add `WEB_HOST_BIND` and `WEB_HOST_PORT` to `src/.env.example` with localhost-only defaults, for example `127.0.0.1` and `8080`.
  - [x] Keep the direct `UI_HOST_PORT` and `API_HOST_PORT` mappings unless there is a clear reason to remove them and docs are updated.

- [x] Document the production-style local path (AC: 4, 5)
  - [x] Update `src/README.md` with the Nginx front-door URL, direct service URLs, and validation commands.
  - [x] Update `src/api/README.md` with the Gunicorn local container behavior and how it differs from `runserver`.
  - [x] Update `docs/project-understanding/commands.md` with `web`/Nginx smoke checks after implementation and review.
  - [x] After the implementation is reviewed, add `docs/project-understanding/05-nginx-and-gunicorn-ready-local-wiring.md` and update the project-understanding index.

- [x] Verify the story outcome (AC: 1-7)
  - [x] Run backend checks from `src/api`: `python manage.py check` and `python manage.py test core`.
  - [x] Run frontend checks from `src/ui`: `npm test`, `npm run lint` and `npm run build`.
  - [x] Run `docker compose config` from `src/`.
  - [x] Run `docker compose up --build -d` from `src/`.
  - [x] Confirm direct backend health: `curl "http://127.0.0.1:${API_HOST_PORT:-8000}/api/health/"`.
  - [x] Confirm direct frontend page and proxy path: `curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/"` and `curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/api/health/"`.
  - [x] Confirm Nginx front-door page and API path: `curl "http://127.0.0.1:${WEB_HOST_PORT:-8080}/"` and `curl "http://127.0.0.1:${WEB_HOST_PORT:-8080}/api/health/"`.
  - [x] Confirm the project and saved-query APIs still work through either direct API or Nginx proxy paths using the existing documented sample curls.

### Review Findings

- [x] [Review][Patch] Track the Nginx config in the root repo so fresh checkouts can start the `web` service [.gitignore:37]
- [x] [Review][Patch] Keep `GUNICORN_BIND` from breaking the Compose healthcheck and Nginx upstream routing [src/.env.example:14]
- [x] [Review][Patch] Validate Gunicorn numeric environment overrides with clear positive-integer errors [src/api/gunicorn.conf.py:10]
- [x] [Review][Patch] Isolate the Gunicorn default-config test from shell environment overrides [src/api/core/tests.py:87]
- [x] [Review][Patch] Stop orchestration tests from silently skipping missing root wiring files by default [src/api/core/tests.py:98]
- [x] [Review][Patch] Document port-override smoke checks using the same overridden `WEB_HOST_PORT` value [docs/project-understanding/commands.md:56]

## Dev Notes

### Story Context

US-003 completes EPIC-001, "reproducible local foundation." US-001 created the Django/DRF backend plus PostgreSQL Compose foundation. US-002 added the Dockerized React/Vite frontend and Vite proxy. US-003 should add the production-style local service boundary: Gunicorn runs Django, and Nginx becomes the local reverse proxy front door.

Sources:

- `docs/product_backlog.md`, EPIC-001 and US-003.
- `docs/sprint_planning.md`, Sprint 2.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, `story_catalog.1-3-nginx-and-gunicorn-ready-local-wiring`.
- `_bmad-output/project-context.md`, thesis stack and repository layout rules.

### Current Repository State

- Active shared Compose file: `src/docker-compose.yml`.
- Active backend path: `src/api`.
- Active frontend path: `src/ui`.
- `src/docker-compose.yml` currently defines `db`, `api` and `ui`.
- The `api` Compose command currently runs migrations and starts `python manage.py runserver 0.0.0.0:8000`.
- `src/api/requirements.txt` currently pins Django `6.0.5`, DRF `3.17.1`, `psycopg[binary]` `3.3.4`, `python-dotenv` `1.2.1`, and does not include Gunicorn.
- `src/api/opentube_insights_api/wsgi.py` already exposes `application`; reuse it for Gunicorn.
- `src/api/opentube_insights_api/settings.py` already defines `STATIC_ROOT = BASE_DIR / "staticfiles"`, but no production static-file serving path is wired yet.
- `src/ui` already uses `VITE_API_BASE_URL=/api`, and Vite proxies `/api` to the backend during direct UI development.
- No active `src/nginx/` config exists.

### Previous Story Intelligence

Preserve these US-001 and US-002 decisions:

- Compose commands run from `src/`.
- Host port bindings default to `127.0.0.1`.
- PostgreSQL is the Docker validation database; SQLite remains only the quick backend local path.
- Main thesis repo owns shared root Compose files under `src/`; `src/api` and `src/ui` are nested repos.
- Direct health checks already used by validation:
  - `http://127.0.0.1:${API_HOST_PORT:-8000}/api/health/`
  - `http://127.0.0.1:${UI_HOST_PORT:-5173}/api/health/`
- The UI container currently uses a bind mount plus `ui-node-modules` volume and runs Vite with `--host 0.0.0.0`.
- Previous review fixes hardened API readiness, frontend proxy URL parsing, and root-owned Compose tracking. Do not undo those fixes.

Sources:

- `_bmad-output/implementation-artifacts/1-1-docker-backend-and-database-services.md`.
- `_bmad-output/implementation-artifacts/1-2-docker-frontend-service.md`.
- `docs/project-understanding/01-local-backend-and-database.md`.
- `docs/project-understanding/02-docker-frontend-service.md`.

### Architecture and Stack Guardrails

- Use the existing Django project package `opentube_insights_api`; do not recreate `thesis_api`.
- Keep backend configuration helpers small, typed and import-safe.
- Do not hardcode secrets, API keys, database credentials or backend URLs.
- Do not downgrade or opportunistically upgrade Django, DRF, React, Vite, TypeScript, PostgreSQL or psycopg.
- Add only the dependency required for the current story: Gunicorn. Do not add Supervisord, uWSGI, Traefik, Caddy, WhiteNoise, Celery, Redis, TLS tooling, or cloud deployment files unless a validation failure proves they are needed.
- Nginx should proxy to existing services by Compose service name (`api`, `ui`), not by host-only `127.0.0.1` ports from inside the container.
- Keep `DEBUG=true` acceptable for this local reproducibility story unless the implementation explicitly documents a separate production-like override. Do not force secret production settings into local defaults.
- If serving Django static files is included, use Django's existing `collectstatic`/`STATIC_ROOT` model; do not invent a custom static pipeline.

### Expected File Changes

Likely files to update:

- `src/docker-compose.yml`: API Gunicorn command and Nginx service.
- `src/.env.example`: `WEB_HOST_BIND`, `WEB_HOST_PORT`, and any Gunicorn tuning variables exposed for local development.
- `src/api/requirements.txt`: Gunicorn dependency.
- `src/api/Dockerfile`: default command or related runtime expectation, if needed.
- `src/api/gunicorn.conf.py`: small environment-driven Gunicorn config, if chosen.
- `src/nginx/default.conf`: Nginx reverse proxy config.
- `src/README.md`: Compose front-door workflow and validation.
- `src/api/README.md`: Gunicorn notes.
- `docs/project-understanding/commands.md`: reusable Nginx/Gunicorn commands after implementation.

Likely files to leave alone:

- `src/api/core/models.py`, serializers, views and migrations.
- `src/ui/src/*`, unless a validation failure shows the frontend needs a small same-origin proxy adjustment.
- `docs/database_schema.md`, because US-003 does not change data models.

### Existing File Notes For Updates

- `src/docker-compose.yml`: Preserve `db` healthcheck, `api` healthcheck, `ui-node-modules` volume and service dependencies. Add Nginx as an additional front door rather than deleting direct service validation paths.
- `src/api/Dockerfile`: Current default is `runserver`. If the default command changes to Gunicorn, keep Compose explicit enough that startup remains obvious.
- `src/api/opentube_insights_api/settings.py`: Already has environment helpers, `ALLOWED_HOSTS`, `STATIC_URL` and `STATIC_ROOT`. Add proxy-related settings only if required by Django behavior and keep them environment-driven.
- `src/ui/vite.config.ts`: Existing proxy is for direct Vite development. Nginx can proxy `/api/` directly to `api:8000`; do not route Nginx API traffic through Vite.
- `src/README.md`: Existing commands describe the dev Compose stack. Add the Nginx URL without removing direct UI/API health checks.

### Latest Technical Notes

- Gunicorn `26.0.0` is the latest PyPI release as of the 2026-07-09 story creation pass, released 2026-05-05, and the project declares Python `3.9+` compatibility. Source: https://pypi.org/project/gunicorn/
- Gunicorn deployment docs recommend running Gunicorn behind a proxy server and include Nginx proxy headers such as `X-Forwarded-For`, `X-Forwarded-Proto` and `Host`. Source: https://gunicorn.org/deploy/
- The official Nginx Docker image supports serving static content and exposing port 80; Docker Hub currently lists stable Alpine tags including `nginx:1.30.3-alpine`. Sources: https://hub.docker.com/_/nginx and https://hub.docker.com/_/nginx/tags?name=-alpine&page=1
- Docker Compose supports `depends_on` with `condition: service_healthy`; keep this pattern where healthchecks exist. Source: https://docs.docker.com/compose/how-tos/startup-order/
- Django 6.0 static-file deployment guidance uses `collectstatic` into `STATIC_ROOT`, then serves those collected files from a web/static server. US-003 may document this boundary without needing to build the full production static pipeline. Source: https://docs.djangoproject.com/en/6.0/howto/static-files/deployment/

### Testing Requirements

Required validation commands:

- `python manage.py check` from `src/api`.
- `python manage.py test core` from `src/api`.
- `npm test` from `src/ui`.
- `npm run lint` from `src/ui`.
- `npm run build` from `src/ui`.
- `docker compose config` from `src/`.
- `docker compose up --build -d` from `src/`.
- `curl "http://127.0.0.1:${API_HOST_PORT:-8000}/api/health/"`.
- `curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/"`.
- `curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/api/health/"`.
- `curl "http://127.0.0.1:${WEB_HOST_PORT:-8080}/"`.
- `curl "http://127.0.0.1:${WEB_HOST_PORT:-8080}/api/health/"`.
- Existing project and saved-query sample curls from `docs/project-understanding/commands.md`, through at least one working path.

If Docker is unavailable or host ports conflict, fix configurable port defaults when possible. If the environment blocks validation, record the exact failed command and reason in the completion notes.

### Project Structure Notes

- Keep shared orchestration in `src/`, not inside only `src/api` or `src/ui`.
- Keep API-local documentation paths relative to `src/api`.
- Keep UI-local documentation paths relative to `src/ui`.
- Keep beginner-facing implementation docs in `docs/project-understanding/`.
- After implementation and review, update nested repository histories from `src/api` and/or `src/ui` if Brandon asks for commits; main thesis repo should track only the BMAD artifact, shared Compose files and docs it owns.

### References

- [Source: docs/product_backlog.md#User-stories]
- [Source: docs/sprint_planning.md#Sprint-planning]
- [Source: _bmad-output/project-context.md#Technology-stack-and-versions]
- [Source: _bmad-output/project-context.md#Repository-layout-and-Git-rules]
- [Source: _bmad-output/implementation-artifacts/1-1-docker-backend-and-database-services.md#Dev-Notes]
- [Source: _bmad-output/implementation-artifacts/1-2-docker-frontend-service.md#Dev-Notes]
- [Source: docs/project-understanding/01-local-backend-and-database.md]
- [Source: docs/project-understanding/02-docker-frontend-service.md]
- [Source: src/docker-compose.yml]
- [Source: src/.env.example]
- [Source: src/api/requirements.txt]
- [Source: src/api/Dockerfile]
- [Source: src/api/opentube_insights_api/settings.py]
- [Source: src/api/opentube_insights_api/wsgi.py]
- [Source: src/ui/vite.config.ts]
- [Source: src/README.md]
- [Source: Gunicorn PyPI, https://pypi.org/project/gunicorn/]
- [Source: Gunicorn deployment docs, https://gunicorn.org/deploy/]
- [Source: Nginx official Docker image, https://hub.docker.com/_/nginx]
- [Source: Docker Compose startup order docs, https://docs.docker.com/compose/how-tos/startup-order/]
- [Source: Django 6.0 static file deployment docs, https://docs.djangoproject.com/en/6.0/howto/static-files/deployment/]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add the smallest Gunicorn config needed for the existing Django WSGI app.
- Keep the current direct API and Vite development paths while adding Nginx as an extra local front door.
- Validate behavior with focused backend config tests, Compose config/build/start checks and direct plus proxied health/API curls.

### Debug Log References

- Red: `venv/bin/python manage.py test core.tests.GunicornConfigTests` failed because `src/api/gunicorn.conf.py` did not exist.
- Green: `venv/bin/python manage.py test core.tests.GunicornConfigTests` passed after adding `src/api/gunicorn.conf.py`.
- `venv/bin/gunicorn --check-config -c gunicorn.conf.py opentube_insights_api.wsgi:application` passed.
- Red: `venv/bin/python manage.py test core.tests.ComposeWiringTests` failed because `src/docker-compose.yml` still used `python manage.py runserver 0.0.0.0:8000`.
- Green: `venv/bin/python manage.py test core.tests.ComposeWiringTests` passed after switching the API service to Gunicorn.
- Red: `venv/bin/python manage.py test core.tests.ComposeWiringTests.test_nginx_front_door_proxies_ui_and_api` failed because `src/nginx/default.conf` did not exist.
- Green: `venv/bin/python manage.py test core.tests.ComposeWiringTests.test_nginx_front_door_proxies_ui_and_api` passed after adding the Nginx config, `web` Compose service and `WEB_*` env defaults.
- `docker compose config` passed with `web` bound to `127.0.0.1:8080` and proxy config mounted read-only.
- Documentation scan with `rg` confirmed the shared README, API README and project-understanding docs now reference Gunicorn/Nginx/`WEB_HOST_PORT`.
- `git diff --check` passed after documentation updates.
- `venv/bin/python manage.py check` passed.
- `venv/bin/python manage.py test core` passed with 23 tests.
- `npm test` passed with 21 tests.
- `npm run lint` passed.
- `npm run build` passed.
- `docker compose config` passed.
- `docker compose up --build -d` passed; `db` and `api` became healthy, `ui` and `web` started.
- Direct API health, Vite page, Vite `/api/health/`, Nginx page and Nginx `/api/health/` curls passed.
- Nginx project and saved-query smoke flow created project `cfe0aef8-a75f-4e68-8bb3-065f4e235aa5` and saved query `99ac1357-a2bd-4de8-801e-0f39f97b4602`.
- Container-side `docker compose exec -T api python manage.py test core` initially failed because API-image tests could not read root Compose files that are intentionally outside `/app`.
- Fixed the orchestration tests to assert root files on the host and skip only when those files are unavailable inside the API-only container image.
- After rebuilding the API image, `docker compose exec -T api python manage.py test core` passed with 23 tests and 2 skips.
- Container-side `gunicorn --check-config`, API `manage.py check`, UI test/lint/build and post-rebuild health/page curls passed.

### Completion Notes List

- Added Gunicorn `26.0.0` as the only new backend runtime dependency.
- Added `src/api/gunicorn.conf.py` for the existing `opentube_insights_api.wsgi:application` entry point with local defaults for bind, workers, timeout and stdout/stderr logs.
- Preserved the backend quick local `runserver` path and documented a Gunicorn config-check command.
- Updated the `api` Compose service to run migrations and then start Gunicorn while preserving direct API port mapping, PostgreSQL environment values and healthcheck behavior.
- Added a `web` Nginx service on `127.0.0.1:${WEB_HOST_PORT:-8080}` with `/api/` proxied to `api:8000` and `/` proxied to `ui:5173`.
- Added Compose-level `WEB_HOST_BIND`, `WEB_HOST_PORT`, `GUNICORN_WORKERS` and `GUNICORN_TIMEOUT` example overrides.
- Updated shared setup docs, API docs, reusable command docs and the US-003 project-understanding page/index for the production-style local path.
- Added focused orchestration tests for Gunicorn, Compose API startup and Nginx routing. Host tests assert root files; container tests skip those two root-file checks because the API image intentionally contains only `src/api`.
- Verified the production-style stack end to end through direct service ports and through Nginx.

### File List

- `_bmad-output/implementation-artifacts/1-3-nginx-and-gunicorn-ready-local-wiring.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/api/core/tests.py`
- `src/api/gunicorn.conf.py`
- `src/api/README.md`
- `src/api/requirements.txt`
- `src/.env.example`
- `src/docker-compose.yml`
- `src/nginx/default.conf`
- `src/README.md`
- `docs/project-understanding/05-nginx-and-gunicorn-ready-local-wiring.md`
- `docs/project-understanding/commands.md`
- `docs/project-understanding/index.md`

### Change Log

- 2026-07-09: Created US-003 story artifact and set status to ready-for-dev.
- 2026-07-09: Implemented US-003 Gunicorn/Nginx local wiring and moved story to review.
