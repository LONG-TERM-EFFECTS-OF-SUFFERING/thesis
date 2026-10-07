---
title: 'Show request logs for each collection run'
type: 'feature'
ticket: '5'
created: '2026-10-07'
status: 'done'
baseline_revision: 'a43b9a3bb87eec66a7c9d701c27d959bfeb96725'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Request logs are only visible in the Django admin. A researcher cannot see in the app which runs a project has, or the requests behind a run (US-014).

**Approach:**
- **API:** two read-only endpoints, a project's runs list and one run's detail with its request logs nested in it.
- **UI:** a "Collection runs" panel for the active project lists runs with status and totals, has a Refresh button, and shows the selected run's request logs in a readable table.

## Boundaries & Constraints

**Always:**
- Both endpoints are scoped through `ProjectOwnerMixin.get_project()`. A run of another owner's project, or of another project, is a 404.
- The list is newest first, with no logs. The detail adds `request_logs` ordered by `request_sequence`.
- Both add `saved_query_name` (null once the query is deleted).
- Serializers are read-only. Only GET is allowed (405 otherwise).
- The log rows show what the log stores and nothing else: no response bodies, no API key, ID params already redacted at write time (US-013).
- UI fetches follow the AGENTS.md pitfall: one `AbortController` per fetch held in a ref, an identity check before writing state, and the project id checked so a late response for a previous project is dropped.
- A run started from a query card appears in the list without a refresh.
- No `any`.
- JSDoc on exported TypeScript functions.

**Never:**
- No pagination (a run has tens of logs at most).
- No polling or auto-refresh.
- No discovery summary or video list (US-016).
- No editing, cancelling or re-running runs.
- No separate router or page library: a panel in `App.tsx`.
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| List | project with 2 runs | 200 with both runs newest first, totals and `saved_query_name`, no `request_logs` key | No error expected |
| Detail | run with 2 logs | 200 with the run plus `request_logs` in sequence order, each with sequence, endpoint, params, page tokens, HTTP status, quota, items, timestamps and error | No error expected |
| Deleted query | run whose saved query was deleted | `saved_query` and `saved_query_name` both null | No error expected |
| Foreign run | run of another project or owner, or an unknown id | no data | 404 |
| Write attempt | POST, PATCH or DELETE on either endpoint | nothing changes | 405 |
| UI list | the active project changes while a list request is in flight | the stale response is dropped; the panel shows the new project's runs | abort + identity check |
| UI start | "Start run" succeeds on a query card | the new run appears at the top of the runs list | No error expected |
| UI detail | user selects a run | its logs table renders: #, endpoint, page token sent, HTTP status, items, quota, started, error; a failed log row is visually marked | `readJson` error detail shown in the panel |
| UI empty | run with no logs (still `pending`) | "No requests yet" instead of an empty table | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/views.py` -- the new views use `ProjectOwnerMixin`. Use `generics.ListAPIView` and `generics.RetrieveAPIView`: their `get_queryset()` returns `CollectionRun.objects.filter(project=self.get_project())`, and the detail adds `.prefetch_related("request_logs")`. `http_method_names` falls out of the generic views, which gives 405.
- `src/api/core/serializers.py` -- `CollectionRunSerializer` gains `saved_query_name` (`source="saved_query.name"`, `default=None`, read-only). Add a new `ApiRequestLogSerializer` with every `ApiRequestLog` field except `collection_run`, and a new `CollectionRunDetailSerializer(CollectionRunSerializer)` that adds a nested `request_logs`.
- `src/api/core/urls.py` -- add `projects/<uuid:project_id>/runs/` (`project-run-list`) and `projects/<uuid:project_id>/runs/<uuid:pk>/` (`project-run-detail`).
- `src/api/core/tests.py` -- add `CollectionRunReadApiTests`, copying `CollectionRunStartApiTests.setUp`.
- `src/ui/src/apiClient.ts` -- add `saved_query_name` to `CollectionRun` and to `isCollectionRun`. Add an `ApiRequestLog` type with an `isApiRequestLog` guard, a `CollectionRunDetail` type with an `isCollectionRunDetail` guard, `listCollectionRuns(projectId, signal?)` and `getCollectionRun(projectId, runId, signal?)`, following `listSavedQueries`.
- `src/ui/src/collectionRunState.ts` (new) -- `CollectionRunListState` (same shape as `SavedQueryListState`), `mergeLoadedRuns`, and `prependRun(state, projectId, run)`. These are pure functions, so `node --test` can cover them.
- `src/ui/src/App.tsx` -- a third panel, `<section className="panel" aria-labelledby="run-heading">`. Load the list in a `useEffect` on `activeProjectId`, in the same way as the saved queries. Refresh and detail fetches each get an `AbortController` ref. `handleStartRun` calls `prependRun` on success.
- `src/ui/src/App.css` -- table styling only; reuse the existing panel and `form-error` classes.
- `src/ui/tests/collectionRunApi.test.ts` -- extend it with the new guards and fetchers, stubbing `fetch`. Add a new `tests/collectionRunState.test.ts`.
- `App.tsx` has no render harness (see the deferred-work entry). The panel is checked by `npm run build` and by hand.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/serializers.py`, `views.py`, `urls.py` -- the two read endpoints.
- [x] `src/api/core/tests.py` -- one test per API matrix row.
- [x] `src/ui/src/apiClient.ts`, `tests/collectionRunApi.test.ts` -- types, guards, fetchers, tests.
- [x] `src/ui/src/collectionRunState.ts`, `tests/collectionRunState.test.ts` -- list state helpers and tests (stale project dropped, prepend dedupes by id).
- [x] `src/ui/src/App.tsx`, `App.css` -- the runs panel and the logs table.

**Acceptance Criteria:**
- Given the foreign-run test, when `get_queryset` stops filtering by `get_project()`, then the test fails.
- Given `collectionRunState.test.ts`, when `mergeLoadedRuns` stops checking the project id, then a test fails.
- Given the running app with a collected run, when the user opens the Collection runs panel and selects the run, then each request appears as one table row matching `/admin/` Api request logs.

## Implementation Notes

- The TS `CollectionRun` type also gained `total_api_requests`, `total_quota_units`, `total_videos_discovered` and `error_message`: the API already sent them and the panel shows them. The other three totals stay untyped until a story displays them.
- Both views `select_related("saved_query", "initiated_by_user")`; log order comes from `ApiRequestLog.Meta.ordering`, and the detail test creates logs out of order to prove it.
- `loadRuns` in `App.tsx` is module-level so the `activeProjectId` effect and the Refresh button share one ref-held controller without a hook dependency. Refresh sets the list to `loading` first and also refetches an open run detail; selecting a run always refetches its detail. `prependRun` leaves an `error` state untouched, and `isFailedLog` lives in `collectionRunState.ts` so it is tested.
- Acceptance mutations run: dropping the `get_project()` filter fails `test_foreign_or_unknown_run_is_not_found` and `test_list_excludes_runs_of_other_projects`; dropping the project check in `mergeLoadedRuns` fails `mergeLoadedRuns drops a late response for a previous project`.
- Matrix audit (orchestrator): API rows covered by `CollectionRunReadApiTests` (6 tests, 153 OK on PostgreSQL); UI list and start rows by `collectionRunState.test.ts`; UI detail and empty rows have no render harness and rest on the manual check. `npm test` 54 pass, build and lint clean. UI baseline `e35bff0adf49d18b33918046dc41354d08d2b981`; thesis baseline `3a1ce4fe7435693b8b304471cba9681ad1266a65`.
- Review patches (pass 1) applied: `prependRun` keeps an error state; Refresh re-fetches an open run detail; lowercase JSDoc on the four new exports; `isFailedLog` moved to `collectionRunState.ts` and tested. Backend 153 OK on PostgreSQL; UI 59 pass, build and lint clean.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 2, low 4, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `prependRun` turns an `error` list into a one-row `ready` list, hiding the error and older runs | medium | patch | Confirmed: only the project id is guarded. Direct fix: return `current` for `error`; test it. |
| Refresh leaves an open run detail stale (status and logs) | medium | patch | Confirmed: `handleRefreshRuns` reloads only the list; hits the plan's own manual flow. Fix: also re-fetch the open detail. |
| New JSDoc in `apiClient.ts` starts uppercase | low | patch | Confirmed against the AGENTS.md rule; direct correction for the four new functions. |
| `isFailedLog` is untested pure logic | low | patch | Confirmed; move to `collectionRunState.ts` and test with `node --test`. |
| First load shows "Choose a project" while the runs request is in flight | low | reject | Confirmed, but it copies the saved-queries panel's existing pattern; a brief cosmetic flash, and the fix (setState in an effect) conflicts with the react-hooks lint rule the implementer hit. |
| Refresh request not aborted on unmount | low | reject | `App` never unmounts and React 19 ignores the late update; the identity check still guards state. Not worth the lint workaround. |

## Design Notes

The detail nests the logs instead of offering a separate logs endpoint. A run makes one `search.list` call per 50 videos, so even a 500-video cap means 10 rows, and one request per selection keeps the UI to a single fetch.

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all pass.

**Manual checks:**
- Start a run, run `manage.py collect_runs` (real key, or a fake via the shell recipe in project-understanding page 12), click Refresh, select the run, and compare the logs table with `/admin/`.
