---
title: 'US-050 Edit a saved query until its first run'
type: 'feature'
ticket: ''
created: '2026-11-09'
status: 'ready-for-dev'
baseline_revision: ''
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Saved queries can only be created, so a typo means making a new query. The advisor asked for editing, at least while the search has not run.

**Approach:** Add `PATCH` on a saved query. It is accepted while the query has no collection runs and answered with `409` once one exists. The same `SavedQuerySerializer` validation applies, including `validate_search_parameters` and the provenance rules. In the UI, each saved-query card with no runs shows *Edit*. It loads the query into the form, which switches to *Save changes* / *Cancel*.

## Boundaries & Constraints

**Always:**
- Owner and project scoping as for listing: someone else's query, or a query of another project, returns 404.
- After the first run the query is frozen (409), so "the query that started this run" stays unambiguous. Each run keeps its own `effective_params` snapshot anyway.
- The server sets `query_source` again from the submitted provenance. The existing rule holds: editing the prompt drops the LLM provenance, and editing parameter values keeps it.
- The saved-query response gains a read-only `has_runs`, so the UI knows when to offer Edit.
- Fetches that write React state go through `latestRequest`, and new text has Spanish entries.

**Never:**
- No migration, and no edit after a run.
- No delete of saved queries.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Edit before run | query without runs, change the search term | 200; the card shows the new term | — |
| Edit after run | query with one run | 409 `{"detail": "This query already started a run; save a new query instead."}`; the UI shows no Edit button | 409 |
| Invalid edit | `order=bogus` | 400 with the validator's findings; the form keeps its values | 400 |
| Duplicate name | rename to another query of yours in the project | 400 name error | 400 |
| LLM query, prompt edited | `llm_generated` query, the prompt changes | saved as `manual`, provenance cleared | — |
| Cancel | Edit, then Cancel | the form returns to empty create mode | — |

</frozen-after-approval>

## Code Map

- `src/api/core/views.py` `SavedQueryListCreateView` (~202): its queryset scoping (`project=self.get_project(), created_by=self.get_owner()`) and serializer context (`project`, `created_by`) are the pattern. Add `SavedQueryDetailView(ProjectOwnerMixin, generics.UpdateAPIView)`, `patch` only. Its `perform_update` returns 409 when `instance.collection_runs.exists()`, and it maps `IntegrityError` to the same name error as create.
- `src/api/core/urls.py`: add `projects/<uuid:project_id>/queries/<uuid:query_id>/` before the `runs/` route.
- `src/api/core/serializers.py` `SavedQuerySerializer` (~22). `validate_name` already excludes `self.instance`. Add `has_runs` (read-only; annotate `Exists` in querysets, or a `SerializerMethodField`). Check that `validate()` and the provenance logic behave on update with a full body.
- Tests in `src/api/core/tests/test_views.py`: one per matrix row, plus owner scoping (404).
- `src/ui/src/apiClient.ts`:
  - Add `updateSavedQuery(projectId, queryId, input: SavedQueryInput)` next to `createSavedQuery` (~930).
  - Add `has_runs` to the `SavedQuery` type and to `isSavedQuery`.
  - Test both with a stubbed `fetch`.
- `src/ui/src/savedQueryForm.ts`:
  - Add `savedQueryToForm(query: SavedQuery): SavedQueryFormState`, the inverse of `buildSavedQueryInput`. Dates go through `toDateTimeLocal`, and the advanced params come from `structured_query_params`; keep the provenance fields.
  - Test the round trip in `tests/savedQueryForm.test.ts`: `buildSavedQueryInput(savedQueryToForm(q))` reproduces the saved input.
- `src/ui/src/QueriesSection.tsx`:
  - The form (`handleSavedQuerySubmit`, `savedQueryForm` state) gains an `editingQueryId` mode.
  - The card actions (~620, `draft-actions`) get *Edit* when `!query.has_runs`.
  - `savedQueryState.ts` merges the updated query into the list by id; add a helper with a test.
- `src/ui/src/i18n.ts`: Spanish entries for Edit, Save changes, Cancel and the editing heading.

## Tasks & Acceptance

**Execution:**
- [ ] Backend: the view, the URL, `has_runs` and the tests.
- [ ] `apiClient.ts`: `updateSavedQuery`, the type and tests.
- [ ] `savedQueryForm.ts`: `savedQueryToForm`, with the round-trip test.
- [ ] `savedQueryState.ts`: replace-by-id helper, with a test.
- [ ] `QueriesSection.tsx` and `i18n.ts`: edit mode and the Edit button.

**Acceptance Criteria:**
- Given a query edited before its first run, when a run then starts, then the run's `effective_params` hold the edited values.
- Given a query with a run, when the UI loads it, then no Edit button is shown and the API refuses a `PATCH`.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: pass, `No changes detected`.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: clean.
