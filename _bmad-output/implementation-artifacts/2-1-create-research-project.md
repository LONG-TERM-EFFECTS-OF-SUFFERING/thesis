# Story 2.1: Create Research Project

Status: done

<!-- Ultimate context engine analysis completed - comprehensive developer guide created. -->

## Story

As a researcher,
I want to create a research project,
so that I can organize a YouTube study by topic.

## Acceptance Criteria

1. A `ResearchProject` Django model exists in the active backend and stores `id`, `owner`, `name`, `description`, `status`, `default_language`, `created_at` and `updated_at`.
2. The database schema matches `docs/database_schema.md`: UUID primary key, owner foreign key to `settings.AUTH_USER_MODEL`, nullable/blank description, `active` or `archived` status with default `active`, optional default language, automatic timestamps, unique project name per owner, and database-level status enforcement.
3. Migrations are created for the `core` app and apply cleanly through Docker Compose PostgreSQL. SQLite may still work for quick local iteration, but PostgreSQL is the validation target.
4. The backend exposes a JSON API for creating and reading research projects without requiring YouTube or LLM credentials.
5. The API never accepts `id`, `owner`, `created_at` or `updated_at` as client-controlled fields during create. Ownership is assigned by backend logic.
6. The frontend first screen becomes a usable research-project workspace where the researcher can create a project and see saved projects.
7. Existing health endpoint behavior and Compose service wiring from US-001 and US-002 remain working.
8. Backend and frontend tests cover project creation, validation, API response shape and frontend API helper behavior.

## BDD Acceptance Criteria

### AC1: Research project is persisted with required schema

Given the backend database is running on PostgreSQL,
When a researcher creates a project with a name, optional description and optional default language,
Then a `research_projects` row is stored with a generated UUID,
And the row has an owner,
And `status` defaults to `active`,
And `created_at` and `updated_at` are set by Django.

### AC2: Owner and project name are protected

Given a project owner already has a project named `Polarization Study`,
When another create request for that same owner uses the same name,
Then the backend rejects the request with a validation error,
And no duplicate project row is created.

Given a different owner creates a project with the same name,
When the request is valid,
Then the backend can store that second project because uniqueness is scoped to the owner.

### AC3: API create and list contract is stable

Given the API is available,
When the frontend sends `POST /api/projects/` with valid project input,
Then the backend returns HTTP 201 and the created project JSON,
And the response includes `id`, owner identity, `name`, `description`, `status`, `default_language`, `created_at` and `updated_at`.

Given projects exist for the current effective owner,
When the frontend sends `GET /api/projects/`,
Then the backend returns those projects in a predictable order.

### AC4: Frontend supports project creation

Given the frontend is running,
When the researcher fills in the project form and submits it,
Then the frontend calls the project API through the centralized API client,
And the created project appears in the project list without a page reload,
And validation or network errors are displayed near the form.

### AC5: Existing stack checks still pass

Given the implementation is complete,
When the standard backend, frontend and Docker validation commands run,
Then health checks still return `{"status":"ok"}`,
And the frontend build, lint and tests pass,
And backend model/API tests pass in Docker Compose PostgreSQL.

## Tasks / Subtasks

- [x] Add the research project persistence model (AC: 1, 2, 3)
  - [x] Create `src/api/core/models.py` if missing.
  - [x] Define `ResearchProject` with `from __future__ import annotations`.
  - [x] Use `models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`.
  - [x] Use `owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="research_projects")`.
  - [x] Use `name = models.CharField(max_length=200)`.
  - [x] Use `description = models.TextField(null=True, blank=True)`.
  - [x] Use a `models.TextChoices` status enum with `active` and `archived`; default to `active`.
  - [x] Use `default_language = models.CharField(max_length=20, null=True, blank=True)`.
  - [x] Use `created_at = models.DateTimeField(auto_now_add=True)` and `updated_at = models.DateTimeField(auto_now=True)`.
  - [x] Set `db_table = "research_projects"` to match the schema dictionary.
  - [x] Add `models.UniqueConstraint(fields=["owner", "name"], name="unique_research_project_name_per_owner")`.
  - [x] Add a `models.CheckConstraint` that restricts `status` to the allowed enum values.
  - [x] Create `src/api/core/migrations/__init__.py` and the initial migration if migrations do not exist.

- [x] Add backend project API support (AC: 4, 5, 7)
  - [x] Create `src/api/core/serializers.py` with a `ResearchProjectSerializer`.
  - [x] Make `id`, owner identity fields, `created_at` and `updated_at` read-only.
  - [x] Validate duplicate project names per owner at the serializer/API layer so clients receive a clear 400 response before relying only on database errors.
  - [x] Create isolated owner-resolution logic. Use `request.user` when authenticated. Because this project has no authentication UI story yet, support unauthenticated local development through an explicit default owner helper that uses `OPENTUBE_DEFAULT_OWNER_USERNAME` with a safe default such as `local-researcher`. Do not make `owner` nullable.
  - [x] Keep owner fallback logic out of model import time; no database queries at module import.
  - [x] Add list/create and retrieve/update API views in `src/api/core/views.py`, or split project views into a small module if `views.py` becomes crowded.
  - [x] Route `GET /api/projects/`, `POST /api/projects/`, `GET /api/projects/<uuid:pk>/` and `PATCH /api/projects/<uuid:pk>/` from `src/api/core/urls.py`.
  - [x] Preserve `GET /api/health/` exactly as a smoke endpoint.
  - [x] Do not add saved queries, YouTube collection, LLM translation, comments, sentiment or result dashboards in this story.

- [x] Add backend tests (AC: 1, 2, 3, 4, 5, 7, 8)
  - [x] Cover model defaults, UUID generation, optional description/default language and timestamp population.
  - [x] Cover unique `(owner, name)` behavior.
  - [x] Cover status validation and database constraint behavior.
  - [x] Cover API create success, duplicate-name validation, list response and retrieve/update response.
  - [x] Cover authenticated-owner behavior and unauthenticated default-owner behavior if both paths are implemented.
  - [x] Keep existing health endpoint tests passing.

- [x] Add frontend project API helpers (AC: 4, 6, 8)
  - [x] Extend `src/ui/src/apiClient.ts` or create a nearby project API module that reuses `buildApiUrl` and `apiBaseUrl`.
  - [x] Define explicit TypeScript types for project request and response payloads. Do not use `any`.
  - [x] Add `listResearchProjects`, `createResearchProject` and, if used by the UI, `updateResearchProject`.
  - [x] Validate unknown JSON response shapes at the API boundary before the React component consumes them.
  - [x] Add no-new-dependency Node tests for URL construction and project payload guards where practical.

- [x] Replace the starter frontend screen with a project workspace (AC: 4, 6, 7)
  - [x] Update `src/ui/src/App.tsx` so the first screen supports the actual create-project workflow, not only the local-stack health display.
  - [x] Include fields for project name, description and default language. Status can default to active and remain visible in the project list.
  - [x] Keep backend health visible as a compact service state, but do not let health status dominate the page.
  - [x] Show loading, empty, success and error states for project list/create.
  - [x] Add responsive CSS in `src/ui/src/App.css` and reuse the existing color tokens from `src/ui/src/index.css`.
  - [x] Do not introduce a new UI framework or icon package unless the implementation explicitly documents why it is necessary.

- [x] Update implementation documentation after code review fixes (AC: 6, 7)
  - [x] Update `src/api/README.md` and `src/ui/README.md` only where new project API/UI commands or behavior need to be documented.
  - [x] After implementation and review fixes, add `docs/project-understanding/03-create-research-project.md`.
  - [x] Update `docs/project-understanding/index.md`, `docs/project-understanding/commands.md` and `docs/project-understanding/glossary.md` if new commands or concepts are introduced.

- [x] Verify the story outcome (AC: 1-8)
  - [x] From `src/api`, run `python manage.py makemigrations --check --dry-run` after committing the migration file to confirm no model changes are missing.
  - [x] From `src/api`, run `python manage.py test core`.
  - [x] From `src/ui`, run `npm test`, `npm run lint` and `npm run build`.
  - [x] From `src`, run `docker compose config`.
  - [x] From `src`, run `docker compose up --build -d`.
  - [x] From `src`, run `docker compose exec -T api python manage.py migrate`.
  - [x] From `src`, run `docker compose exec -T api python manage.py test core`.
  - [x] Confirm `curl "http://127.0.0.1:${API_HOST_PORT:-8000}/api/health/"` returns `{"status":"ok"}`.
  - [x] Confirm project create/list through the frontend or with `curl` against `/api/projects/`.

### Review Findings

- [x] [Review][Patch] Make project API response validation endpoint-specific [src/ui/src/apiClient.ts:105]
- [x] [Review][Patch] Convert duplicate-name database races into validation responses [src/api/core/views.py:102]
- [x] [Review][Patch] Preserve backend validation details in frontend create errors [src/ui/src/apiClient.ts:110]
- [x] [Review][Patch] Prevent stale initial list responses from hiding newly created projects [src/ui/src/App.tsx:213]
- [x] [Review][Patch] Update project-understanding documentation only after review fixes are final [docs/project-understanding/03-create-research-project.md:5]

## Dev Notes

### Story Context

US-004 is the first story in EPIC-002, "research project and query setup." The epic goal is to let researchers organize studies and save collection criteria so each YouTube dataset has clear research context. Sprint 1 groups US-004 with US-005, so this story must create a stable project foundation that saved queries can reference next.

Sources:

- `docs/product_backlog.md:12`, EPIC-002.
- `docs/product_backlog.md:27`, US-004.
- `docs/product_backlog.md:28`, US-005 dependency context.
- `docs/sprint_planning.md:9`, Sprint 1 goal.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`, `story_catalog.2-1-create-research-project`.

### Current Repository State

- Active backend path: `src/api`.
- Active frontend path: `src/ui`.
- Compose path: `src/docker-compose.yml`.
- The backend currently exposes only `GET /api/health/` from `src/api/core/views.py` and `src/api/core/urls.py`.
- The backend `core` app currently has no `models.py`, `serializers.py`, `admin.py` or migrations folder.
- The frontend currently renders a local-stack health/status screen from `src/ui/src/App.tsx`.
- Frontend API base URL parsing is centralized in `src/ui/src/apiConfig.ts` and consumed by `src/ui/src/apiClient.ts`; preserve that pattern.
- `src/api` has uncommitted README changes at story-creation time. Do not overwrite unrelated README edits when implementing.

### Data Model Requirements

The required table is `research_projects`.

Required fields:

- `id`: UUID primary key generated by Django with `uuid.uuid4`.
- `owner`: foreign key to `settings.AUTH_USER_MODEL`, cascade delete, required.
- `name`: `CharField(max_length=200)`, required.
- `description`: optional text.
- `status`: `active` or `archived`, default `active`.
- `default_language`: optional `CharField(max_length=20)`.
- `created_at`: `auto_now_add=True`.
- `updated_at`: `auto_now=True`.

Required constraints:

- Unique project name per owner.
- Database-level check that status is one of the allowed values.

Sources:

- `docs/database_schema.md:39`, `research_projects` model.
- `docs/database_schema.md:45`, owner/name uniqueness and status constraint.
- `docs/database_schema.md:50-56`, field definitions.
- `_bmad-output/project-context.md:148`, research projects are core persisted data.

### Ownership Decision

The schema requires an owner, but the backlog does not include a login/authentication UI story before US-004. Do not solve this by making owner nullable or by letting the browser submit arbitrary owner IDs.

Use this transitional rule:

- If `request.user.is_authenticated`, assign the project to `request.user`.
- If the request is unauthenticated, resolve a documented local default owner inside request handling. A small helper can read `OPENTUBE_DEFAULT_OWNER_USERNAME` and `get_or_create` a Django user with a safe default username such as `local-researcher`.
- Keep this isolated and documented so a future authentication story can replace it cleanly.

This preserves the data model while keeping the Sprint 1 local workflow usable.

### API Contract Guidance

Recommended endpoints:

- `GET /api/projects/`: list projects for the effective owner.
- `POST /api/projects/`: create a project for the effective owner.
- `GET /api/projects/<uuid:pk>/`: retrieve a project for the effective owner.
- `PATCH /api/projects/<uuid:pk>/`: update editable fields for the effective owner.

Recommended create request:

```json
{
  "name": "Cali polarization study",
  "description": "Videos and comments about civic debate in Cali.",
  "default_language": "es"
}
```

Recommended response:

```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "owner_id": 1,
  "owner_username": "local-researcher",
  "name": "Cali polarization study",
  "description": "Videos and comments about civic debate in Cali.",
  "status": "active",
  "default_language": "es",
  "created_at": "2026-06-17T00:00:00Z",
  "updated_at": "2026-06-17T00:00:00Z"
}
```

Guardrails:

- Do not expose delete as the primary workflow. If the UI needs removal semantics later, prefer `status = archived`.
- Do not show projects across owners.
- Do not accept `owner_id` from the browser during create.
- Do not use live YouTube API or LLM credentials in this story.

### Frontend UX Requirements

The first viewport should become the working project setup interface. Keep it quiet and operational:

- A compact heading for OpenTube Insights and project setup.
- A create form with name, description and default language.
- A visible list/table of projects with name, status, default language and updated timestamp.
- Inline validation and request error messaging.
- Loading and empty states.
- A compact backend health indicator so US-002 smoke behavior remains visible.

Avoid turning this into a marketing page or a decorative dashboard. The researcher should be able to create the first project immediately.

### Project Structure Notes

Expected backend files to create or update:

- `src/api/core/models.py`
- `src/api/core/migrations/__init__.py`
- `src/api/core/migrations/0001_initial.py` or the next correct migration number if migrations already exist.
- `src/api/core/serializers.py`
- `src/api/core/views.py`
- `src/api/core/urls.py`
- `src/api/core/admin.py` if useful for local inspection.
- `src/api/core/tests.py`
- `src/api/README.md` only if new behavior must be documented.

Expected frontend files to create or update:

- `src/ui/src/apiClient.ts`
- `src/ui/src/App.tsx`
- `src/ui/src/App.css`
- `src/ui/tests/apiConfig.test.ts` or a new nearby project API test file.
- `src/ui/README.md` only if new behavior must be documented.

Expected docs after implementation and review:

- `docs/project-understanding/03-create-research-project.md`
- `docs/project-understanding/index.md`
- `docs/project-understanding/commands.md` if new reusable commands are added.
- `docs/project-understanding/glossary.md` if new concepts such as UUID, constraint, serializer or owner fallback need beginner explanation.

Repository ownership:

- `src/api` and `src/ui` are nested Git repositories. Do not add their implementation files to the main thesis repo.
- The main thesis repo owns `_bmad-output/`, `docs/`, `content/`, `src/docker-compose.yml` and `src/.env.example`.

Sources:

- `_bmad-output/project-context.md:44-64`, active code paths and nested repository rules.
- `_bmad-output/project-context.md:237-248`, project-understanding documentation rules.

### Architecture and Stack Guardrails

- Backend versions come from `src/api/requirements.txt`: Django `6.0.5`, Django REST Framework `3.17.1`, `psycopg[binary]` `3.3.4`, `python-dotenv` `1.2.1`.
- Frontend versions come from `src/ui/package.json` and `package-lock.json`: React `19.2.6`, Vite `8.0.12`, TypeScript `6.0.2`.
- PostgreSQL `18-alpine` from `src/docker-compose.yml` is the reproducibility database.
- Use Django ORM models and migrations. Do not handwrite SQL for this story unless a migration operation truly requires it.
- Add `from __future__ import annotations` to new Python modules.
- Keep Django settings free of business logic.
- Avoid `Any` in Python and `any` in TypeScript unless there is a short written justification.
- Keep code beginner-readable and typed rather than clever.

Sources:

- `_bmad-output/project-context.md:24-46`, stack versions and dependency source of truth.
- `_bmad-output/project-context.md:197-233`, Python and TypeScript implementation rules.
- `src/api/requirements.txt`.
- `src/ui/package.json`.

### Previous Story Intelligence

US-001 established:

- Compose commands run from `src/`.
- SQLite is allowed for quick local backend iteration only.
- PostgreSQL through Docker Compose is required for validation.
- Existing health endpoint is `GET /api/health/`.
- Backend environment values may come from `src/api/.env`, but shell values win.

US-002 established:

- The UI service waits for API health in Compose.
- Frontend API URL handling belongs in `src/ui/src/apiConfig.ts` and `src/ui/src/apiClient.ts`.
- Vite proxy defaults to `/api` -> `http://api:8000` in Compose.
- Required frontend checks are `npm test`, `npm run lint` and `npm run build`.
- Root Compose artifacts are tracked by the main repo; API/UI app files are owned by nested repos.

Sources:

- `_bmad-output/implementation-artifacts/1-1-docker-backend-and-database-services.md`.
- `_bmad-output/implementation-artifacts/1-2-docker-frontend-service.md:127-156`.

### Git Intelligence

Recent main thesis commits:

- `2a0edfd docs(thesis): add US-002 implementation context`
- `e51b7c6 docs(thesis): add Taiga usage to 'Project development and implementation' chapter`
- `cd3cf84 docs(thesis): add US-001 implementation context`

Recent nested app commits:

- API: `0f7a69a feat(api): add backend Docker foundation`
- UI: `a6aefd2 feat(frontend): add Docker frontend service`

Implication: there is little mature app-domain code yet. Build the project model/API/UI as the first domain slice and preserve the simple patterns already in place.

### Latest Technical Notes

- Django 6.0 officially supports Python 3.12, 3.13 and 3.14, which matches the project-context Python 3.14 target. Source: https://docs.djangoproject.com/en/6.0/releases/6.0/
- Django constraints belong in `Meta.constraints`, and the standard convention is to refer to imported constraint classes as `models.<Foo>Constraint`. Source: https://docs.djangoproject.com/en/6.0/ref/models/constraints/
- Django model `Meta.unique_together` should not be used for new work; Django docs recommend `UniqueConstraint` through `Meta.constraints`. Source: https://docs.djangoproject.com/en/6.0/ref/models/options/#unique-together
- DRF `ModelSerializer` is the appropriate serializer shortcut when API fields map closely to a Django model. Source: https://www.django-rest-framework.org/api-guide/serializers/#modelserializer
- DRF API test case classes use `APIClient`-style behavior and are appropriate for endpoint tests. Source: https://www.django-rest-framework.org/api-guide/testing/#api-test-cases
- React's built-in `<form>` component is the standard way to build interactive form controls; keep form state explicit and typed in this small UI. Source: https://react.dev/reference/react-dom/components/form

### Testing Requirements

Minimum backend validation:

```bash
cd src/api
python manage.py makemigrations --check --dry-run
python manage.py test core
```

Minimum frontend validation:

```bash
cd src/ui
npm test
npm run lint
npm run build
```

Minimum Docker/PostgreSQL validation:

```bash
cd src
docker compose config
docker compose up --build -d
docker compose exec -T api python manage.py migrate
docker compose exec -T api python manage.py test core
curl "http://127.0.0.1:${API_HOST_PORT:-8000}/api/health/"
curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/api/health/"
```

Manual project API smoke check:

```bash
curl -sS -X POST "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/" \
  -H "Content-Type: application/json" \
  -d '{"name":"Cali polarization study","description":"Local thesis test","default_language":"es"}'

curl -sS "http://127.0.0.1:${API_HOST_PORT:-8000}/api/projects/"
```

If Docker is unavailable or a command fails because of an external host-port conflict, document the exact failed command and the environmental reason in completion notes.

### Completion Criteria

The dev agent may mark this story complete only when:

- The `ResearchProject` model and migration exist in the active backend.
- PostgreSQL migration and backend tests pass in Docker Compose.
- The API supports create/list/retrieve/update for projects scoped to the effective owner.
- The frontend can create a project and show it in the project list.
- Existing health checks still pass.
- US-005 has a stable `ResearchProject` model/API to reference later.
- Any owner fallback is isolated, documented and tested.
- Project-understanding docs are updated after implementation and review fixes.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `python manage.py test core` failed before backend work because the shell Python did not have Django installed.
- `venv/bin/python manage.py test core` failed in the backend red phase because `core.models.ResearchProject` did not exist.
- `venv/bin/python manage.py makemigrations core` initially caught a model `Meta` scoping issue for `ProjectStatus`; fixed the check constraint to use literal allowed status values.
- `venv/bin/python manage.py makemigrations core` generated `core/migrations/0001_initial.py`.
- `venv/bin/python manage.py test core` passed with 13 backend tests after model/API implementation.
- `npm test` failed in the frontend red phase because `apiClient.ts` did not export project API helpers.
- `npm test` passed with 9 frontend helper tests after project API helper implementation.
- `npm run lint` passed after the project workspace UI implementation.
- `npm run build` passed after the project workspace UI implementation.
- `venv/bin/python manage.py makemigrations --check --dry-run` passed with no changes detected.
- `venv/bin/ruff check .` passed.
- `docker compose config` passed and showed `OPENTUBE_DEFAULT_OWNER_USERNAME=local-researcher` on the API service.
- `COMPOSE_PROGRESS=plain docker compose up --build -d` rebuilt the API image and started `db`, `api` and `ui`; Docker warned that the buildx plugin is not installed and used the classic builder successfully.
- `docker compose exec -T api python manage.py migrate` passed with no pending migrations.
- `docker compose exec -T api python manage.py test core` passed with 13 backend tests on PostgreSQL.
- API health returned `{"status":"ok"}` from `http://127.0.0.1:8000/api/health/`.
- Frontend-proxied health returned `{"status":"ok"}` from `http://127.0.0.1:5173/api/health/`.
- Project create/list smoke checks passed against `/api/projects/` and returned `owner_username: "local-researcher"`.
- `docker compose exec -T ui npm test`, `docker compose exec -T ui npm run lint` and `docker compose exec -T ui npm run build` passed.
- Code review red phase: `venv/bin/python manage.py test core` failed with an unhandled duplicate-name `IntegrityError`.
- Code review red phase: `npm test` failed because project list/detail response validation was not endpoint-specific, backend validation details were hidden and `projectState.ts` did not exist yet.
- Code review green phase: `venv/bin/python manage.py test core` passed with 14 backend tests.
- Code review green phase: `npm test` passed with 14 frontend tests.
- Post-review validation: `venv/bin/python manage.py makemigrations --check --dry-run && venv/bin/python manage.py test core` passed.
- Post-review validation: `npm test && npm run lint && npm run build` passed.
- Post-review Docker validation: `docker compose config`, `COMPOSE_PROGRESS=plain docker compose up --build -d`, `docker compose exec -T api python manage.py migrate`, `docker compose exec -T api python manage.py test core`, `docker compose exec -T ui npm test`, `docker compose exec -T ui npm run lint` and `docker compose exec -T ui npm run build` passed.
- Post-review smoke checks returned `{"status":"ok"}` from the API health endpoint and the frontend-proxied health endpoint; project create/list passed against `/api/projects/`.

### Completion Notes List

- Implemented the `ResearchProject` Django model with UUID primary key, owner foreign key, status choices, optional language/description, timestamps, owner/name uniqueness and status check constraint.
- Added project list/create and detail/update API endpoints scoped to the authenticated user or an isolated local default owner.
- Added backend tests for model defaults, uniqueness, status constraint, health endpoint preservation, project create/list/retrieve/update, duplicate-name validation and owner scoping.
- Added typed frontend project API helpers with response-shape validation and fetch tests.
- Replaced the starter local-stack screen with a project workspace that creates projects, lists saved projects and keeps backend health visible as a compact state.
- Documented the project API, local owner fallback and project workspace in service READMEs and project-understanding docs.
- Final validation passed locally and through Docker Compose PostgreSQL. The Compose stack is intentionally left running for review at `http://127.0.0.1:5173`.
- Code review fixes made project response validation endpoint-specific, preserved backend field errors in the frontend, converted duplicate-name database races into validation responses and protected the project list from stale initial-load responses.

### File List

- `src/api/core/admin.py`
- `src/api/core/migrations/0001_initial.py`
- `src/api/core/migrations/__init__.py`
- `src/api/core/models.py`
- `src/api/core/serializers.py`
- `src/api/core/tests.py`
- `src/api/core/urls.py`
- `src/api/core/views.py`
- `src/api/.env.example`
- `src/api/README.md`
- `src/.env.example`
- `src/docker-compose.yml`
- `src/ui/src/App.css`
- `src/ui/src/App.tsx`
- `src/ui/src/apiClient.ts`
- `src/ui/src/projectState.ts`
- `src/ui/tests/projectApi.test.ts`
- `src/ui/tests/projectState.test.ts`
- `src/ui/README.md`
- `docs/project-understanding/03-create-research-project.md`
- `docs/project-understanding/commands.md`
- `docs/project-understanding/glossary.md`
- `docs/project-understanding/index.md`
- `_bmad-output/implementation-artifacts/2-1-create-research-project.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-06-17: Created US-004 story context artifact and set status to ready-for-dev.
- 2026-06-17: Implemented US-004 research project model, API, frontend workspace, documentation and validation; set story ready for review.
- 2026-06-29: Applied code review fixes for US-004 and set story done.
