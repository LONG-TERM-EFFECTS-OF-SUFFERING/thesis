# Story 1.2: Docker Frontend Service

Status: done

<!-- Ultimate context engine analysis completed - comprehensive developer guide created. -->

## Story

As a researcher-developer,
I want the frontend to run locally with Docker,
so that I can use the app without manual frontend setup.

## Acceptance Criteria

1. Docker Compose can start a React/Vite frontend service from `src/docker-compose.yml` alongside the existing `db` and `api` services.
2. The frontend service listens on a documented local host port and runs Vite inside the container on `0.0.0.0` so the host browser can reach it.
3. The frontend can call the backend health endpoint through environment-driven configuration, without hardcoding the backend URL in React components.
4. Frontend Docker environment variables are documented with safe local defaults and do not require real secrets.
5. Frontend build, lint and Docker/Compose smoke validation commands are documented.
6. US-002 does not implement Nginx, Gunicorn production serving, research-project models, saved queries or YouTube collection behavior.

## BDD Acceptance Criteria

### AC1: Compose starts frontend with backend stack

Given Docker is installed on the developer machine,
When the developer runs the documented Docker Compose startup command from `src/`,
Then PostgreSQL starts successfully,
And the Django/DRF backend starts successfully,
And the React/Vite frontend starts successfully,
And the frontend listens on a documented local port.

### AC2: Frontend uses environment-driven backend configuration

Given the frontend is running locally or in Docker,
When the frontend loads its API configuration,
Then it derives the API base URL from a documented Vite environment variable,
And the application can request the backend `GET /api/health/` endpoint.

### AC3: Frontend validation is reproducible

Given a developer checks out the repository,
When they run the documented frontend build, lint and Docker Compose validation commands,
Then the commands pass without requiring manual frontend setup outside npm or Docker.

## Tasks / Subtasks

- [x] Add frontend container support in `src/ui` (AC: 1, 2, 4)
  - [x] Add `src/ui/Dockerfile` for the Vite development server.
  - [x] Add `src/ui/.dockerignore` so local env files, dependencies and build output are not copied into the image.
  - [x] Ensure the container command runs Vite with `--host 0.0.0.0`.

- [x] Wire the frontend into Compose (AC: 1, 2, 3, 4)
  - [x] Add a `ui` service to `src/docker-compose.yml` built from `./ui`.
  - [x] Document and wire `UI_HOST_BIND`, `UI_HOST_PORT`, `VITE_API_BASE_URL` and any Vite proxy target variable needed for local Docker development.
  - [x] Keep the existing `db` and `api` services working.
  - [x] Do not add Nginx or production frontend serving in this story.

- [x] Add environment-driven frontend backend-call support (AC: 3)
  - [x] Add a small typed frontend API configuration/helper module instead of hardcoding URLs in components.
  - [x] Update the starter React screen to show the configured API base URL and backend health result.
  - [x] Use the existing backend `GET /api/health/` endpoint for the smoke check.

- [x] Document frontend Docker workflow (AC: 2, 4, 5)
  - [x] Expand `src/ui/README.md` with local npm commands, Docker Compose commands, expected URLs, environment variables and troubleshooting.
  - [x] Update `src/api/README.md` only where needed so the shared Compose workflow mentions the frontend service.
  - [x] Keep docs beginner-friendly and explicit about running Compose from `src/`.

- [x] Verify the story outcome (AC: 1-6)
  - [x] Add focused tests for frontend API URL helper behavior without introducing unnecessary dependencies.
  - [x] Run frontend tests, lint and build.
  - [x] Run `docker compose config` from `src/`.
  - [x] Run Docker Compose build/start validation and confirm the frontend and backend health paths respond.
  - [x] Capture any command failures and fix configuration before marking the story complete.

### Review Findings

- [x] [Review][Decision] Decide repository ownership for root Compose artifacts — resolved by unignoring only `src/docker-compose.yml` and `src/.env.example` in the main repo while continuing to ignore nested `src/api` and `src/ui` repository contents.
- [x] [Review][Patch] Add API readiness handling before one-shot frontend health checks [`src/docker-compose.yml:58`]
- [x] [Review][Patch] Prevent stale UI dependency volume after package changes [`src/docker-compose.yml:55`]
- [x] [Review][Patch] Trim and validate blank Vite proxy target values [`src/ui/vite.config.ts:9`]
- [x] [Review][Patch] Normalize bare relative API base URLs before joining health paths [`src/ui/src/apiConfig.ts:3`]
- [x] [Review][Patch] Make the frontend health check resilient to initial hangs or transient startup failure [`src/ui/src/App.tsx:18`]
- [x] [Review][Patch] Remove default-only port text from the app surface [`src/ui/src/App.tsx:60`]
- [x] [Review][Patch] Use documented host-port variables and `127.0.0.1` in Docker smoke commands [`src/ui/README.md:90`]
- [x] [Review][Patch] Clarify the backend env-copy command working directory [`src/api/README.md:103`]

## Dev Notes

### Story Context

US-002 is part of EPIC-001, "reproducible local foundation." US-001 already established the active Django/DRF backend, PostgreSQL database and `src/docker-compose.yml`. US-002 should extend that foundation by adding the React/Vite frontend service only.

Sources:

- `docs/product_backlog.md`, EPIC-001 and US-002.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, `story_catalog.1-2-docker-frontend-service`.
- `_bmad-output/implementation-artifacts/1-1-docker-backend-and-database-services.md`, previous story file list and completion notes.

### Current Repository State

- Active frontend path: `src/ui`.
- Active backend path: `src/api`.
- Compose path: `src/docker-compose.yml`.
- The frontend currently has React/Vite dependencies, a stock Vite starter screen and no Dockerfile.
- `src/ui` is a nested Git repository with no commits yet; the main thesis repo intentionally ignores nested `src/api` and `src/ui` contents while tracking shared root Compose artifacts.
- Brandon deleted the old `src/vault` directory. Do not depend on it, reference it as a required source, or attempt to recreate it.

### Architecture and Stack Guardrails

- Use React `19.2.6`, Vite `8.0.12`, TypeScript `6.0.2`, npm and ESLint `10.3.0` from `src/ui/package.json`.
- Use Django/DRF backend health endpoint `GET /api/health/` already implemented in US-001.
- Keep API URL parsing centralized in a frontend helper module. React components may consume the helper, but should not construct backend URLs directly.
- Vite only exposes client environment variables prefixed with `VITE_`; use `import.meta.env` in frontend runtime code.
- Vite must listen on `0.0.0.0` inside Docker so the host can access the dev server.
- Prefer a Vite dev-server proxy for same-origin local development if needed; avoid adding backend CORS dependencies unless implementation proves it is necessary.
- Do not introduce a production web server in US-002. Nginx and Gunicorn-ready wiring belongs to US-003.

Sources:

- `_bmad-output/project-context.md`, technology stack and critical implementation rules.
- `src/ui/package.json`, frontend dependency versions and npm scripts.
- `src/docker-compose.yml`, existing `db` and `api` services.
- Vite docs: `https://vite.dev/guide/env-and-mode.html` and `https://vite.dev/config/server-options`.
- Docker Compose services docs: `https://docs.docker.com/reference/compose-file/services/`.

### Previous Story Intelligence

US-001 established these patterns to preserve:

- Compose commands run from `src/`.
- Docker services bind host ports to `127.0.0.1` by default.
- Backend health is verified with `curl http://127.0.0.1:8000/api/health/`.
- Environment examples live in service-specific files such as `src/api/.env.example`.
- Runtime files belong under nested repos in `src/`, not in the main thesis repo.
- Keep SQLite as quick local backend convenience and PostgreSQL as Docker validation target. US-002 should not change database behavior.

### Expected File Changes

- `src/docker-compose.yml`: add `ui` service and frontend environment/port wiring.
- `src/ui/Dockerfile`: Vite development container.
- `src/ui/.dockerignore`: exclude local-only frontend files from Docker build context.
- `src/ui/README.md`: frontend local and Docker workflow.
- `src/ui/src/*`: small API helper, tests and a minimal app screen that checks backend health.
- `src/api/README.md`: shared Compose documentation update if needed.

### Testing Requirements

Required validation commands:

- `npm test` from `src/ui`, if a no-new-dependency helper test is added.
- `npm run lint` from `src/ui`.
- `npm run build` from `src/ui`.
- `docker compose config` from `src/`.
- `docker compose build ui` from `src/`.
- `docker compose up --build -d` from `src/`.
- `curl http://127.0.0.1:${UI_HOST_PORT:-5173}/` or equivalent frontend smoke check.
- `curl http://127.0.0.1:${UI_HOST_PORT:-5173}/api/health/` to confirm frontend-to-backend proxying works, if proxying is used.
- `curl http://127.0.0.1:${API_HOST_PORT:-8000}/api/health/` to confirm the backend remains healthy.

If Docker is unavailable or a Compose command fails because of a pre-existing local volume or host port conflict, fix configuration when feasible. If the environment itself blocks validation, document the exact limitation in completion notes.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `test -f src/ui/Dockerfile && test -f src/ui/.dockerignore && (cd src && docker compose config --services | grep -qx ui)` failed before implementation, confirming the missing frontend container artifacts and Compose service.
- `npm test` passed with 3 API URL helper tests.
- `npm run lint` passed.
- `npm run build` initially failed because the checking health state had no `message`; fixed by rendering a separate fallback health message, then passed.
- `docker compose config` passed and showed `ui` bound to `127.0.0.1:5173` with `VITE_API_BASE_URL=/api`.
- `docker compose build ui` passed. Docker emitted a non-blocking warning that the buildx plugin is not installed, then used the classic builder successfully.
- `docker compose up --build -d` initially failed because `postgres:18-alpine` rejects a volume mounted at `/var/lib/postgresql/data`; fixed the Compose volume target to `/var/lib/postgresql` to match PostgreSQL 18 image expectations.
- `docker compose down --volumes` removed the just-created failed validation volumes before retrying.
- Final `docker compose up --build -d` passed with `db`, `api` and `ui` running.
- `curl http://127.0.0.1:5173/` returned the Vite-served frontend HTML.
- `curl http://127.0.0.1:5173/api/health/` returned `{"status":"ok"}` through the Vite proxy.
- `curl http://127.0.0.1:8000/api/health/` returned `{"status":"ok"}` directly from Django.
- `docker compose exec -T ui npm test`, `docker compose exec -T ui npm run lint` and `docker compose exec -T ui npm run build` passed.
- `docker compose exec -T api python manage.py check`, `docker compose exec -T api python manage.py test core` and `docker compose exec -T api python manage.py showmigrations` passed.
- Final host `npm run build` exposed that the earlier root-running UI container had created a root-owned `dist/`; fixed `src/ui/Dockerfile` to run as the non-root `node` user.
- Recreated the `ui` container and `ui-node-modules` volume, then reran `docker compose exec -T ui npm run build`, `docker compose exec -T ui npm test`, `docker compose exec -T ui npm run lint`, host `npm run build`, and both health curls successfully.
- Code review applied all patch findings: main repo now owns root Compose artifacts, `api` has a Compose healthcheck, `ui` waits for API health, the UI dependency volume refreshes with `npm ci`, frontend API URL/proxy handling is hardened, and Docker smoke docs use documented host-port variables.
- Post-review validation passed: `npm test`, `npm run lint`, `npm run build`, `docker compose config`, `docker compose build ui`, `docker compose up --build -d`, frontend/API health curls, and container-side UI test/lint/build.

### Completion Notes List

- Recreated the missing US-002 story artifact because only the backlog/catalog entry existed and the old vault directory had been deleted.
- Added a Dockerized Vite frontend service using `node:24-alpine`, `npm ci` and `npm run dev -- --host 0.0.0.0`.
- The frontend container now runs as the non-root `node` user so bind-mounted build output is not owned by root on the host.
- Added the `ui` service to `src/docker-compose.yml` with localhost-only host binding, configurable `UI_HOST_PORT`, frontend source bind mount and a persistent `ui-node-modules` volume.
- Added environment-driven frontend API configuration with `VITE_API_BASE_URL` and a Vite proxy target defaulting to `http://api:8000` in Compose.
- Replaced the starter Vite screen with an OpenTube local stack status view that calls the backend health endpoint through the configured API path.
- Added no-new-dependency Node tests for URL normalization and endpoint joining.
- Documented local npm workflow, Docker Compose workflow, expected URLs, environment variables and validation commands.
- Fixed the PostgreSQL 18 Compose volume target from `/var/lib/postgresql/data` to `/var/lib/postgresql` so the existing `db` service remains startable with the project-context database version.
- Final validation passed locally and in Docker. The Compose stack is intentionally left running for Brandon to try at `http://127.0.0.1:5173`.
- Code review findings resolved and US-002 marked done.

### File List

- `.gitignore`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/1-2-docker-frontend-service.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/project-understanding/01-local-backend-and-database.md`
- `docs/project-understanding/02-docker-frontend-service.md`
- `docs/project-understanding/commands.md`
- `docs/project-understanding/glossary.md`
- `docs/project-understanding/index.md`
- `src/.env.example`
- `src/docker-compose.yml`
- `src/api/README.md`
- `src/ui/.dockerignore`
- `src/ui/.env.example`
- `src/ui/Dockerfile`
- `src/ui/README.md`
- `src/ui/package-lock.json`
- `src/ui/package.json`
- `src/ui/src/App.css`
- `src/ui/src/App.tsx`
- `src/ui/src/apiClient.ts`
- `src/ui/src/apiConfig.ts`
- `src/ui/src/index.css`
- `src/ui/tests/apiConfig.test.ts`
- `src/ui/vite.config.ts`

### Change Log

- 2026-06-07: Recreated US-002 story artifact after the missing story/vault context; set story ready for development.
- 2026-06-07: Implemented US-002 Docker frontend service, frontend API health smoke check, documentation and validation.
- 2026-06-07: Resolved US-002 code review findings and updated story status to done.
