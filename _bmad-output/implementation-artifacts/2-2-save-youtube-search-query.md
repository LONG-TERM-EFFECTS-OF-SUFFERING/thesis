---
baseline_commit: b8afe4db5e99d4be99d5057d432f6b51a4224139
---

# Story 2.2: Save YouTube Search Query

Status: done

## Story

As a researcher,
I want to save a YouTube search query inside a research project,
so that collection criteria can be reused and audited with clear project context.

## Acceptance Criteria

1. A `SavedQuery` record can be created for an existing `ResearchProject` with a name, search term, optional natural-language prompt, optional date bounds, optional video discovery limit, optional region/language filters, optional notes and structured YouTube query parameters.
2. `SavedQuery` records persist in PostgreSQL with UUID primary keys, project ownership links, creator links, timestamps and JSONB structured parameters matching `docs/database_schema.md`.
3. The backend exposes owner-scoped API endpoints to list and create saved queries for a project without exposing another owner user's project or query data.
4. Backend validation rejects missing query names, missing search terms, invalid date ranges, invalid `max_videos_to_discover` values below `1` and duplicate query names within the same project for the same creator.
5. The frontend lets the user save a manual YouTube search query from the existing project workflow and shows saved queries after creation and page reload.
6. The frontend uses the existing centralized API client/base URL behavior and does not hardcode backend URLs in React components.
7. Automated backend and frontend tests cover saved-query model defaults, API validation/scoping, client payload validation and the UI-facing save/list behavior.

## Tasks / Subtasks

- [x] Task 1: Add the saved-query persistence model and migration (AC: 1, 2, 4)
  - [x] Add `SavedQuery` to `src/api/core/models.py` with the fields described in `docs/database_schema.md`.
  - [x] Link each query to `ResearchProject` and `settings.AUTH_USER_MODEL`.
  - [x] Add model choices for `manual` and `llm_generated`, defaulting to `manual`.
  - [x] Add a database constraint that keeps query names unique per `project`, `created_by` and `name`.
  - [x] Generate `src/api/core/migrations/0002_savedquery.py`.
  - [x] Register `SavedQuery` in `src/api/core/admin.py`.
- [x] Task 2: Add owner-scoped backend serializers and endpoints (AC: 1, 3, 4)
  - [x] Add `SavedQuerySerializer` in `src/api/core/serializers.py`.
  - [x] Reuse the current owner resolution behavior from `src/api/core/views.py`; do not create a parallel authentication path.
  - [x] Add `GET /api/projects/<uuid:project_id>/queries/` for project-scoped query listing.
  - [x] Add `POST /api/projects/<uuid:project_id>/queries/` for project-scoped query creation.
  - [x] Derive `project` from the URL and `created_by` from the resolved owner; do not accept either field from request JSON.
  - [x] Validate duplicate names, date order and `max_videos_to_discover` in the serializer or view layer before saving.
- [x] Task 3: Add backend tests for saved-query behavior (AC: 2, 3, 4, 7)
  - [x] Test model defaults and `structured_query_params` persistence.
  - [x] Test successful create and list through the project-scoped API.
  - [x] Test duplicate query names are rejected only inside the same project/creator scope.
  - [x] Test another authenticated user cannot list or create queries under someone else's project.
  - [x] Test invalid date range and invalid `max_videos_to_discover` responses.
- [x] Task 4: Extend the frontend API boundary (AC: 5, 6, 7)
  - [x] Add `SavedQuery`, `SavedQueryInput` and runtime shape validation in `src/ui/src/apiClient.ts`.
  - [x] Add `listSavedQueries(projectId)` and `createSavedQuery(projectId, input)` using `buildApiUrl`.
  - [x] Add or update Node tests in `src/ui/tests/` for saved-query shape validation, list routing, create routing and error messages.
- [x] Task 5: Add the saved-query UI to the existing project workflow (AC: 5, 6)
  - [x] Extend `src/ui/src/App.tsx` after project creation/selection so the user can enter query name, search term, optional prompt, optional video discovery limit, optional published date bounds, optional region/language filters and notes.
  - [x] Use native form controls; use `datetime-local` or `date` inputs and convert submitted values to API-compatible ISO strings.
  - [x] List saved queries for the active project and refresh the list after a query is created.
  - [x] Preserve the existing health check and project create/list behavior.
  - [x] Keep styling in `src/ui/src/App.css` and `src/ui/src/index.css` consistent with the current dense app screen; no landing page or new design system.
- [x] Task 6: Update docs and run validations (AC: 1-7)
  - [x] Update backend and frontend README usage examples only where saved-query commands or local workflow are now incomplete without them.
  - [x] Add a beginner-facing note under `docs/project-understanding/` only if the implementation introduces non-obvious model/API behavior.
  - [x] Run backend tests in `src/api`.
  - [x] Run frontend `npm test`, `npm run lint` and `npm run build` in `src/ui`.
  - [x] Validate migrations against PostgreSQL through `src/docker-compose.yml` when Docker is available.

### Review Findings

- [x] [Review][Patch] Catch concurrent saved-query duplicate-name `IntegrityError` and return validation 400 [src/api/core/views.py:157]
- [x] [Review][Patch] Restore centralized API URL normalization by using `apiConfig.ts` from the runtime API client [src/ui/src/apiClient.ts:63]
- [x] [Review][Patch] Preserve locally created projects when the initial project list request resolves late [src/ui/src/App.tsx:175]
- [x] [Review][Patch] Restore bounded health retry/timeout behavior while preserving the health check [src/ui/src/App.tsx:163]
- [x] [Review][Patch] Reset or merge saved-query list state so stale queries cannot appear under another project or overwrite a just-created query [src/ui/src/App.tsx:190]
- [x] [Review][Patch] Show saved-query published-after and published-before date bounds in the query summary [src/ui/src/App.tsx:516]
- [x] [Review][Patch] Add frontend coverage for UI-facing saved-query save/list behavior [src/ui/tests/savedQueryApi.test.ts:44]

## Dev Notes

### Sprint and Dependency Context

US-005 is the second story in EPIC-002, "research project and query setup." US-004 created the `ResearchProject` foundation and project API/UI. This story must build on that foundation so saved queries are owned by projects and users, not stored as free-floating search text.

Sprint 1 goal: local app and research records. By the end of this story, the local app should support basic project records and saved-query records. No live YouTube API call is required in this story.

### Current Code State

- Backend app code lives in `src/api/core`.
- `ResearchProject` already exists in `src/api/core/models.py` with UUID primary key, owner FK, name, description, status, default language and timestamps.
- `src/api/core/serializers.py` already has `ResearchProjectSerializer` and owner-aware duplicate-name validation.
- `src/api/core/views.py` already has `resolve_project_owner`, `ProjectOwnerMixin`, `ResearchProjectListCreateView`, `ResearchProjectDetailView` and `health`.
- `src/api/core/urls.py` currently exposes `/api/health/`, `/api/projects/` and `/api/projects/<uuid:pk>/`.
- Frontend API behavior is centralized in `src/ui/src/apiClient.ts`; keep backend URL parsing there.
- `src/ui/src/App.tsx` currently owns the one-screen health/project workflow. Extend it; do not add routing for this story.
- Frontend tests are plain Node test files under `src/ui/tests/`; there is no React component test framework installed.

### Data Model Requirements

Implement `SavedQuery` using the fields from `docs/database_schema.md`:

- `id`: UUID primary key, default `uuid.uuid4`.
- `project`: FK to `ResearchProject`, `on_delete=models.CASCADE`, related name such as `saved_queries`.
- `created_by`: FK to `settings.AUTH_USER_MODEL`, `on_delete=models.CASCADE`.
- `name`: `CharField(max_length=200)`.
- `natural_language_prompt`: optional `TextField`.
- `query_source`: `CharField(max_length=20)` with choices `manual` and `llm_generated`, default `manual`.
- `search_term`: text field required by this story for manual saved searches.
- `published_after` and `published_before`: optional `DateTimeField`.
- `max_videos_to_discover`: optional positive integer; app validation must reject values below `1` when provided.
- `region_code`: optional `CharField(max_length=10)`.
- `relevance_language`: optional `CharField(max_length=20)`.
- `structured_query_params`: `JSONField(default=dict)`.
- `llm_model_name`, `llm_prompt_version`, `translation_confidence`: optional metadata fields reserved for later LLM stories.
- `notes`: optional `TextField`.
- `created_at` and `updated_at`: timestamp fields.

Use a database uniqueness constraint for `project`, `created_by` and `name`. This mirrors the existing project-name uniqueness pattern and prevents ambiguous query selection inside a project.

### API Requirements

Add only project-scoped list/create endpoints:

- `GET /api/projects/<uuid:project_id>/queries/`
- `POST /api/projects/<uuid:project_id>/queries/`

Request JSON for create should accept user-editable fields only:

```json
{
  "name": "Cali mobility videos",
  "natural_language_prompt": "Videos about mobility debates in Cali",
  "search_term": "movilidad Cali",
  "published_after": "2026-01-01T00:00:00Z",
  "published_before": "2026-06-01T00:00:00Z",
  "max_videos_to_discover": 250,
  "region_code": "CO",
  "relevance_language": "es",
  "structured_query_params": {
    "part": "snippet",
    "type": "video",
    "q": "movilidad Cali"
  },
  "notes": "Manual seed query for sprint testing."
}
```

Recommended successful response fields:

```json
{
  "id": "uuid",
  "project": "project-uuid",
  "created_by_username": "local-researcher",
  "name": "Cali mobility videos",
  "query_source": "manual",
  "search_term": "movilidad Cali",
  "published_after": "2026-01-01T00:00:00Z",
  "published_before": "2026-06-01T00:00:00Z",
  "max_videos_to_discover": 250,
  "region_code": "CO",
  "relevance_language": "es",
  "structured_query_params": {
    "part": "snippet",
    "type": "video",
    "q": "movilidad Cali"
  },
  "notes": "Manual seed query for sprint testing.",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

Validation guardrails:

- Missing or blank `name` returns 400.
- Missing or blank `search_term` returns 400 for this story.
- `max_videos_to_discover`, when present, must be at least 1.
- `published_after` must not be later than `published_before`.
- `structured_query_params` must be a JSON object, not a string or array.
- Duplicate `name` inside the same project/creator scope returns 400.
- A project outside the resolved owner scope returns 404.

### Frontend Requirements

Keep the UI boring and usable:

- The app should remain a single working tool screen.
- Add saved-query controls below or beside the active project area, not as a landing page.
- Use existing API helpers and error-message handling.
- Use native controls for optional dates and numbers.
- Keep labels visible and errors close to the form.
- Show enough query summary fields for review: name, search term, date bounds, video discovery limit, region, language and source.

No new frontend dependency is needed for this story.

### Architecture and File Structure Requirements

Expected backend files:

- `src/api/core/models.py`
- `src/api/core/migrations/0002_savedquery.py`
- `src/api/core/serializers.py`
- `src/api/core/views.py`
- `src/api/core/urls.py`
- `src/api/core/admin.py`
- `src/api/core/tests.py`
- `src/api/README.md` if manual API examples need updating

Expected frontend files:

- `src/ui/src/apiClient.ts`
- `src/ui/src/App.tsx`
- `src/ui/src/App.css`
- `src/ui/src/index.css` only if global layout needs a small adjustment
- `src/ui/tests/projectApi.test.ts` or a focused new saved-query API test file
- `src/ui/README.md` if local usage examples need updating

Expected docs files:

- `docs/project-understanding/04-save-youtube-search-query.md` only if the implementation needs beginner-facing explanation.
- `docs/project-understanding/index.md` only if a new learning doc is added.

### Testing Requirements

Minimum backend validation:

```bash
cd src/api
venv/bin/python manage.py test
venv/bin/python manage.py makemigrations --check --dry-run
```

Minimum frontend validation:

```bash
cd src/ui
npm test
npm run lint
npm run build
```

Minimum Docker/PostgreSQL validation when Docker is available:

```bash
cd src
docker compose up -d db
docker compose run --rm api python manage.py migrate
```

Do not rely on SQLite-only behavior for the migration or JSON field behavior.

### Latest Technical Information

- Django 6.0 model constraints are declared through `Meta.constraints`; use `models.UniqueConstraint` for the saved-query name scope. Official reference checked 2026-07-06: https://docs.djangoproject.com/en/6.0/ref/models/constraints/
- DRF generic views already fit this story; `ListCreateAPIView` is enough for the project-scoped list/create endpoint. Official reference checked 2026-07-06: https://www.django-rest-framework.org/api-guide/generic-views/
- DRF `ModelSerializer` remains the local pattern for model-backed request/response validation. Official reference checked 2026-07-06: https://www.django-rest-framework.org/api-guide/serializers/
- React controlled inputs and native input types are sufficient for this form. Official reference checked 2026-07-06: https://react.dev/reference/react-dom/components/input
- YouTube `search.list` supports `part=snippet`, `q`, `maxResults`, `publishedAfter`, `publishedBefore`, `regionCode`, `relevanceLanguage` and `type`; do not call the YouTube API in this story. The saved-query field `max_videos_to_discover` stores researcher intent, and later collection code should map it to one or more requests with YouTube's per-request `maxResults` limit. Official reference checked 2026-07-06: https://developers.google.com/youtube/v3/docs/search/list

### Project Context Reference

Follow `_bmad-output/project-context.md`:

- Active code lives in nested repos `src/api` and `src/ui`; do not add app files to the main thesis repo.
- Backend uses Django 6.0.5 and DRF 3.17.1.
- Frontend uses React 19.2.6, Vite 8.0.12 and TypeScript 6.0.2.
- Use PostgreSQL via Docker Compose for migration/database acceptance when available.
- Keep frontend API base URL parsing centralized.
- Do not add new dependencies unless a story requirement cannot be met with existing code.

### Story Completion Status

This story is ready for `bmad-dev-story`. The developer should implement only saved-query persistence, API, UI, docs and tests described above. Collection runs, YouTube API execution, natural-language translation and query approval workflows belong to later stories.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Created story context from `docs/product_backlog.md`, `docs/sprint_planning.md`, `docs/database_schema.md`, `_bmad-output/project-context.md`, existing US-004 story context and current `src/api`/`src/ui` code structure.
- Red check: `venv/bin/python manage.py test core.tests.SavedQueryModelTests core.tests.SavedQueryApiTests` failed before `SavedQuery` existed.
- Green checks: `venv/bin/python manage.py test`, `venv/bin/python manage.py makemigrations --check --dry-run`, `npm test`, `npm run lint`, `npm run build`, `docker compose run --rm api python manage.py migrate`.

### Completion Notes List

- Story artifact created for US-005.
- Sprint status updated to `ready-for-dev`.
- Implemented `SavedQuery` persistence, migration, admin registration, serializer validation and owner-scoped project query endpoints.
- Added backend coverage for saved-query defaults, create/list, duplicate scoping, owner isolation, date validation and `max_videos_to_discover` validation.
- Extended the frontend API client with saved-query types, runtime validation, list/create calls and Node tests.
- Reworked the single-screen app to create/select projects and save/list manual YouTube queries with native form controls.
- README/project-understanding docs were not changed because this story did not require new setup steps; pre-existing README edits in nested repos were left untouched.

### File List

- `_bmad-output/implementation-artifacts/2-2-save-youtube-search-query.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/api/core/admin.py`
- `src/api/core/models.py`
- `src/api/core/migrations/0002_savedquery.py`
- `src/api/core/serializers.py`
- `src/api/core/tests.py`
- `src/api/core/urls.py`
- `src/api/core/views.py`
- `src/ui/src/App.css`
- `src/ui/src/App.tsx`
- `src/ui/src/apiClient.ts`
- `src/ui/tests/savedQueryApi.test.ts`

### Change Log

- 2026-07-06: Created US-005 story context artifact and set status to ready-for-dev.
- 2026-07-06: Implemented US-005 saved-query backend, frontend and tests; set status to review.
