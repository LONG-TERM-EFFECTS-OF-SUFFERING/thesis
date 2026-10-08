# Deferred work

Items raised during review that are real but not actionable in the story that surfaced them.

## Deferred from: code review of 3-1-generate-draft-youtube-api-parameters-from-natural-language (2026-08-05)

- **30 s synchronous upstream call blocks sync Gunicorn workers** (`src/api/core/query_translation.py:15`). `TIMEOUT_SECONDS = 30` on a sync worker class with `GUNICORN_WORKERS` defaulting to 3 means three concurrent draft requests stall health checks, project listing and query saving. `urlopen(timeout=…)` also bounds each individual socket operation rather than total elapsed time, so a trickling upstream outlives the 30 s budget and is killed by the 60 s worker timeout — the client gets a dropped connection instead of the documented 502. Architectural; revisit when collection runs (EPIC-004) introduce their own long-running calls.

- **`get_project()` is inherited by views whose URLs have no `project_id`** (`src/api/core/views.py:83`). Moving the lookup from `SavedQueryListCreateView` into `ProjectOwnerMixin` is correct for the two project-scoped views, but `ResearchProjectListCreateView` and `ResearchProjectDetailView` now inherit a method that would raise `KeyError` instead of `Http404` if called. Not reachable today; worth a guard if a third project-scoped view lands.

- **No authentication, permission or throttle classes on the API** (`src/api/opentube_insights_api/settings.py:242`). `REST_FRAMEWORK` declares no `DEFAULT_AUTHENTICATION_CLASSES`, `DEFAULT_PERMISSION_CLASSES` or `DEFAULT_THROTTLE_*`, and `resolve_project_owner` creates a fallback `local-researcher` user for unauthenticated callers, so anyone who can reach the port can spend the operator's OpenAI key. Deferred by decision during the US-006 review: the app binds to `127.0.0.1` and auth is a cross-cutting concern no story owns yet. A prompt length cap was applied in US-006; rate limiting was not. Revisit before any non-local deployment, and note that every endpoint added after US-006 that calls a metered API inherits this gap.

- **Unrelated main-repo edits ride along in the US-006 diff** (`.gitignore`, `docs/project-understanding/index.md`). `.gitignore` gains `.claude` and loses its trailing newline; `index.md` flips US-003 from `Review` to `Done` (correct per `sprint-status.yaml`, but another story's bookkeeping) and reflows the entire table's whitespace, which obscures the single row this story added. No fix needed — noted so a future reviewer does not re-flag it.
- source_plan: `_bmad-output/initiative-opentube-insights/epic-natural-language-query-translation/story-validate-generated-youtube-api-parameters-plan.md`
  summary: The draft panel's validation findings list in src/ui/src/App.tsx has no rendering test; inverting its condition or deleting the list ships green.
  evidence: No file under src/ui/tests imports App and no React render harness (jsdom/testing-library) is installed; US-007 forbade new dependencies. Cover it when a UI test harness is introduced, likely with US-008's editable screen.
- source_plan: `_bmad-output/initiative-opentube-insights/epic-traceable-youtube-collection/story-create-collection-run-model-and-status-lifecycle-plan.md`
  summary: `docs/database_schema.md` `collection_runs` lists `saved_query_id` and `initiated_by_user_id` as `null: NO` though their Django field is `SET_NULL, null=True`.
  evidence: The doc contradicts itself in the same rows; migration `0004_collectionrun` creates both columns nullable. Fix the null column in a thesis docs commit.
- source_plan: `_bmad-output/initiative-opentube-insights/epic-traceable-youtube-collection/story-start-a-collection-run-from-a-saved-query-plan.md`
  summary: A Django admin session cookie on the same host makes every UI POST fail with a DRF CSRF 403 and switches the effective owner to the admin user.
  evidence: `REST_FRAMEWORK` sets no `DEFAULT_AUTHENTICATION_CLASSES`, so DRF's default `SessionAuthentication` runs; cookies ignore ports, so the admin `sessionid` reaches `/api` through the Vite proxy and `startCollectionRun`/`createSavedQuery` send no CSRF token. Settle together with the auth deferral above.
- source_plan: none
  summary: Plug a real pre-trained sentiment model (e.g. pysentimiento/robertuito-sentiment-analysis from the AVISPA youtube-data-extraction notebooks) into the US-025 classifier slot, with its dependencies, label/score mapping, licence check and model version.
  evidence: Split from US-025 by the human on 2026-10-08 to keep the method open; part A builds the table, the sentiment step and the report against a classifier interface tested with a fake. Open items: torch/transformers versions for Python 3.14, Docker image size, weights download kept out of tests, and the model card's research-use terms.
