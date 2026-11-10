# 48 - Edit a saved query until its first run

Story: US-050, Edit a saved query until its first run.

Status note: this page describes US-050 after its review of 2026-11-09 and the fixes that followed (`src/api` PR #47, `src/ui` PR #29). The advisor asked for query editing, "at least while the search has not run", in his review of thesis commit `753a97d`; see `docs/thesis-review-code-changes.md` item 10.

## What this story added

A saved-query card shows **Edit** while the query has never started a run. Edit loads the query into the form, which becomes *Edit query*, with *Save changes* and *Cancel*. Saving goes through exactly the same checks as saving a new query: the parameter validator, the unique name, and the LLM provenance rules.

Once the query has a run, it is frozen:

- the API answers `409` ("This query already started a run; save a new query instead.");
- the card no longer shows Edit;
- if you are editing a query and start its run, the form returns to create mode.

## Why freeze after the first run

Each run already keeps its own copy of the parameters (`effective_params`), so editing later would not lose history. But "the query that started this run" would then point at criteria the run never used. Freezing keeps that link honest, and a new criterion is simply a new query.

## Key concept: PATCH that replaces

The endpoint is `PATCH /api/projects/<id>/queries/<query_id>/`, but it replaces the whole query: a field the body leaves out is cleared. That is deliberate. The form sends the whole query, the same way it does when creating one, and the date-range and provenance checks need all the fields to be meaningful.

## Key concept: the provenance follows the prompt

A query drafted by the LLM stores the model, the prompt version and the confidence (8.5). If the prompt is edited, the provenance no longer describes it, so the query becomes `manual`. The UI drops the provenance when you type in the prompt, and since this story the server does too, when the stored provenance is sent back with a different prompt.

## Files

- `src/api/core/views.py`:
  - `SavedQueryScopeMixin` holds the scoping shared by listing and editing.
  - `SavedQueryDetailView` handles the `PATCH`, the `409` and the duplicate-name mapping.
- `src/api/core/serializers.py`: `has_runs`, and the provenance rule on update.
- `src/api/core/urls.py`: the `project-query-detail` route.
- `src/ui/src/apiClient.ts`:
  - `updateSavedQuery`, and `has_runs` on `SavedQuery`.
  - `ApiError`, which carries the HTTP status so the UI can recognize a `409`.
- `src/ui/src/savedQueryForm.ts`: `savedQueryToForm`, the inverse of `buildSavedQueryInput`.
- `src/ui/src/savedQueryState.ts`: `replaceSavedQuery`.
- `src/ui/src/QueriesSection.tsx`: the edit mode.

## Commands

```bash
cd src/api && venv/bin/python manage.py test   # 408 tests
cd src/ui && npm test                          # 132 tests, including the savedQueryToForm round trip
```

## How to test manually

1. `npm run dev` → Queries. Save a query, then click Edit on its card, change the search term and Save changes. The card shows the new term.
2. Start a run from the card. The Edit button disappears.
3. Edit a query and start its run while the form is in edit mode. The form returns to create mode.

## Limit

A run that starts at the very moment a save arrives can slip between the "has it run?" check and the save; a `ponytail:` comment marks this. The run still records its own parameter snapshot.
