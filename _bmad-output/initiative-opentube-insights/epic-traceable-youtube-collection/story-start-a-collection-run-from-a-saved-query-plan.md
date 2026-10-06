---
title: 'Start a collection run from a saved query'
type: 'feature'
ticket: '2'
created: '2026-10-05'
status: 'done'
baseline_revision: '873f9a874278c5a0a5dd7c4d7b9fe20d1117d15a'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context:
  - '{project-root}/docs/database_schema.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A researcher cannot start a collection run, and nothing records the parameters a run used. A saved query alone cannot hold them: it can be deleted, which sets the run's `saved_query` to null (US-011).

**Approach:** Add `POST /api/projects/<project_id>/queries/<query_id>/runs/`. It re-validates the saved query, creates a `CollectionRun` that copies the query's parameters into a new `effective_params` JSON column, and returns the run. On the UI side, each saved query card gets a "Start run" button that shows the created run's status.

## Boundaries & Constraints

**Always:** `project` comes from the saved query, and both are scoped to the effective owner exactly as `SavedQueryListCreateView.get_queryset` does. `initiated_by_user` is the effective owner. `effective_params` is a copy taken at start: editing or deleting the query afterwards never changes it. Re-run `validate_search_parameters` on the stored `structured_query_params` before creating the run. The UI fetch is guarded by an `AbortController` in a ref plus an identity check, and the button is disabled while its request is in flight. Constraints are validated against Compose PostgreSQL.

**Decisions:** A started run is created in `pending`; US-015's collector moves it to `running`. `effective_params` is `{"search_list": <copy of structured_query_params>, "max_videos_to_discover": <int|null>}`. The workflow implements the code (not guide mode).

**Never:** No YouTube calls, no worker and no move past the initial status (US-015 runs it). No count, quota or error columns (US-012). No run list or detail endpoint and no run page (US-014). No editing a run's `effective_params` through the API. No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Start | owner's saved query, valid params | 201; run with query's project, `saved_query`, `initiated_by_user`, status `pending`, `effective_params` equal to the snapshot | No error expected |
| Snapshot holds | query's `structured_query_params` changed or query deleted after start | run's `effective_params` unchanged | No error expected |
| Foreign query | query id in another project, or another owner's | no run created | 404 |
| Unknown project | project id not owned by the effective owner | no run created | 404 |
| Invalid stored params | stored `structured_query_params` fails validation (e.g. edited in admin) | no run created | 400 listing each finding message |
| Two clicks | user clicks "Start run" twice quickly | one request in flight; the button stays disabled until it settles | No error expected |
| UI failure | API returns 4xx/5xx | message shown on that query card; other cards unaffected | `readJson` error detail |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py` `CollectionRun` -- add `effective_params = models.JSONField(default=dict)`; do not touch `transition_to` or the constraints. Run `makemigrations core` to generate `0005`.
- `src/api/core/serializers.py` -- add `CollectionRunSerializer` (all fields read-only; `initiated_by_username` mirrors `SavedQuerySerializer.created_by_username`).
- `src/api/core/views.py` -- new `CollectionRunStartView(ProjectOwnerMixin, APIView)`. Reuse `get_project()`/`get_owner()` and the 400-with-messages shape from `SavedQuerySerializer.validate_structured_query_params`.
- `src/api/core/urls.py` -- route `projects/<uuid:project_id>/queries/<uuid:query_id>/runs/`, name `project-query-run-start`.
- `src/api/core/tests.py` -- `CollectionRunStartApiTests(APITestCase)` beside `SavedQueryApiTests`; copy its `setUp`.
- `src/ui/src/apiClient.ts` -- `CollectionRun` type, `isCollectionRun` guard, `startCollectionRun(projectId, queryId, signal?)`, following `createSavedQuery` and `readSavedQueryJson`.
- `src/ui/tests/collectionRunApi.test.ts` -- stub `fetch` as `savedQueryApi.test.ts` does.
- `src/ui/src/App.tsx` -- query card in the `query-list` map: a button and a per-query status or error line, with state keyed by query id.
- `src/ui` has no React render harness (see the deferred-work entry), so App.tsx is checked by `npm run build` and by hand.
- Thesis repo, separate docs commit: add an `effective_params` row (`JSONB`, `JSONField(default=dict)`, NO) to `collection_runs` in `docs/database_schema.md`.

## Tasks & Acceptance

**Execution:**
- [x] `src/api` -- `git switch` already done: `feature/US-011`. For `src/ui`, create `feature/US-011` from `develop`.
- [x] `src/api/core/models.py` + migration `0005` -- add `effective_params` -- the run's own record of its parameters.
- [x] `src/api/core/serializers.py`, `views.py`, `urls.py` -- the start endpoint -- the story's behavior.
- [x] `src/api/core/tests.py` -- one test per I/O row on the API side -- covers the matrix.
- [x] `src/ui/src/apiClient.ts`, `tests/collectionRunApi.test.ts` -- client, guard and test (201, 404 detail, malformed body) -- typed boundary.
- [x] `src/ui/src/App.tsx` -- button and status line per query card -- the user-facing start.
- [x] `docs/database_schema.md` -- schema row -- the doc is the source of truth for columns.

**Acceptance Criteria:**
- Given a saved query, when the user clicks "Start run", then the card shows the new run's status and `GET /admin` shows the run with its `effective_params`.
- Given the snapshot test, when the view stores a reference instead of a copy (or reads params from `saved_query` at display time), then that test fails.

## Implementation Notes

- No `copy.deepcopy` in the view: saving the run serializes `effective_params` to its own JSONB value, so an in-memory reference cannot leak past the write. Mutation-checked: a serializer that reads `saved_query` at display time fails `test_snapshot_survives_query_edit_and_delete`; skipping validation fails the invalid-params test.
- Admin: `effective_params` added to `CollectionRunAdmin.readonly_fields`, so the snapshot shows in `/admin` but cannot be edited there either.
- UI: besides the disabled button, `handleStartRun` returns early while a controller for that query id is in the ref map, so a double click before re-render cannot send two requests. `.query-card p` became `.query-card p:not(.form-error)` because it overrode the red error colour on the card.
- Matrix audit: rows Start, Snapshot holds, Foreign query, Unknown project and Invalid stored params are covered by `CollectionRunStartApiTests` (5 tests, ran OK on PostgreSQL). Rows Two clicks and UI failure have no automated test (no React render harness; `readJson` 404 detail is covered in `collectionRunApi.test.ts`); they rest on the manual check. UI baseline: `5f99e7f2da9b10b1f35d50d3b51ac94d17e1e9bb`; thesis baseline: `c31f0ae511c185e79e698aeb6bc6904b4afd19c5`.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 1, false 0, maybe-false 0, defer 1.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Logging into `/admin` on the same host sends `sessionid` through the Vite proxy; DRF `SessionAuthentication` then demands CSRF, so "Start run" (and every other UI POST) returns 403, and the effective owner switches to the admin user | medium | defer | Confirmed: `REST_FRAMEWORK` in `settings.py` sets no `DEFAULT_AUTHENTICATION_CLASSES`, so DRF defaults apply. Pre-existing for every POST since US-003; not caused by this diff. Manual check workaround: open admin on `127.0.0.1`, UI on `localhost` (or start the run before logging in). |
| Unmount cleanup aborts an in-flight start; `catch` skips `AbortError`, so a surviving component (Fast Refresh) keeps the card on "Starting…" | low | reject | Confirmed only for dev Fast Refresh during a request's in-flight window; in production the component is gone. Unlikely in everyday use and the fix adds a branch; same pattern as the existing draft handler. |

## Design Notes

The snapshot exists because `saved_query` is `SET_NULL` and the reproducible unit in the thesis (`content/07-reference_framework.tex`) is "saved query, effective parameters and request logs". The parameters therefore have to outlive the query.

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test core` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.
- `cd src/ui && npm test && npm run build` -- expected: all tests pass, build exits 0.

**Manual checks:**
- Run the app, click "Start run" on a saved query: the card shows `pending`, and the admin lists the run with its parameters.
