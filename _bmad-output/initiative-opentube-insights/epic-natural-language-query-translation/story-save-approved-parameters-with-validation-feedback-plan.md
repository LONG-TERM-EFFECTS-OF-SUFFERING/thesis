---
title: 'Save approved parameters with validation feedback'
type: 'feature'
ticket: 4
created: '2026-10-03'
status: 'built'
baseline_revision: '871625353a7cd2a2ca07d13e78232129378998ff'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The saved-query endpoint accepts any JSON object as `structured_query_params`, so a parameter set that `validate_search_parameters` flags can still be saved. An omitted one is saved as `{}`. Draft provenance is also lost: `llm_model_name`, `llm_prompt_version`, `translation_confidence` and `query_source` are read-only, so a query built from a draft is stored as `manual` with no model, prompt version or confidence.

**Approach:** Saving runs the existing validator, and any finding is a `400` that lists every message. The form shows that message, and nothing is saved. "Use these parameters" also carries the draft's model, prompt version and confidence into the form. Saving sends them back, and the server validates them and marks the query `llm_generated`. A save with no draft metadata stays `manual`.

**Decisions (human, 2026-10-03):** Validation feedback is the rejected save: the backend validator is the only rule check, and there is no separate "check" step or route. Editing the prompt after applying a draft clears the draft metadata, so that save is `manual`. Editing parameter values keeps the metadata.

## Boundaries & Constraints

**Always:** Reuse `validate_search_parameters` unchanged as the only rule source. Do not port it to TypeScript. `query_source` stays read-only and is derived on the server. Provenance is all or nothing: the model name, prompt version and confidence come together, and they need a natural-language prompt. Confidence must be in [0, 1]. Pure, React-free form mapping is unit-tested with `node --test`. Keep the `AbortController` and controller-identity guard in `handleDraftParameters` untouched. Backend tests use no network.

**Never:** No new model, migration, route or dependency, and no server-side draft store. No collection run (EPIC-004). No re-validation of `GET` results or of already-saved rows. No change to `validate_search_parameters` or `query_translation.py`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Approved draft saved | form filled by "Use these parameters", valid values | `201`, `query_source: llm_generated`, model/version/confidence stored | — |
| Manual save | no draft applied, valid values | `201`, `query_source: manual`, metadata null | — |
| Invalid params | e.g. `regionCode: "col"` or `publishedAfter > publishedBefore` | `400 {"structured_query_params": [every finding message]}`, no row | form shows the message, form values kept |
| Params omitted | POST without `structured_query_params` | `400` required | — |
| Partial provenance | `llm_model_name` without version/confidence, or metadata without prompt | `400` | — |
| Bad confidence | `translation_confidence: 1.5` or `-0.1` | `400` | — |
| Prompt edited after apply | apply draft, then edit prompt | metadata cleared from form; save is `manual` | — |

</frozen-after-approval>

## Code Map

Baselines: thesis `871625353a7cd2a2ca07d13e78232129378998ff`, `src/api` `153986516745091dcfe7a71714f6556c3a7badc9` (`develop`), `src/ui` `00e7397c0e1f06aedd39362a4630a9514e663475` (`develop`). Commit app code inside each nested repo on `feature/US-009`, cut from `develop`.

- `src/api/core/serializers.py` -- `SavedQuerySerializer`: `Meta.read_only_fields` (drop the three `llm_*`/`translation_confidence` names, keep `query_source`); `validate_structured_query_params` (call the validator, raise its messages); `validate` (provenance all-or-nothing, set `attrs["query_source"]`). Use `extra_kwargs` for `structured_query_params` `required: True` and the confidence `min_value`/`max_value`.
- `src/api/core/parameter_validation.py` -- `validate_search_parameters`. Read-only, reuse.
- `src/api/core/models.py` -- `SavedQuery.QuerySource`, field types. Read-only; no migration.
- `src/api/core/tests.py` -- `SavedQueryApiTests.valid_payload` has no `maxResults` and would now fail, so add `"maxResults": 50`. Put new tests in this class.
- `src/api/README.md` -- the paragraphs near "Persisting an approved draft" and "Saving does not check them yet" now describe what is built. Update both.
- `src/ui/src/savedQueryForm.ts` -- `SavedQueryFormState`, `emptySavedQueryForm`, `applyDraftToForm`, `buildSavedQueryInput`. Add metadata and emit it.
- `src/ui/src/apiClient.ts` -- `SavedQueryInput`: add the optional `llm_model_name`, `llm_prompt_version` and `translation_confidence` (string, as the draft returns it). `errorDetail` already flattens the 400, so leave it.
- `src/ui/src/App.tsx` -- `updateSavedQueryForm`: on a `naturalLanguagePrompt` edit, also clear the metadata. `savedQueryError` already renders the 400. Optionally show the model on the saved `.query-card`.
- `src/ui/tests/savedQueryForm.test.ts` -- reuse its `draft` fixture.

## Tasks & Acceptance

**Execution:**
- [ ] `src/api/core/serializers.py` -- enforce the validator on save, require the params, make provenance writable but validated, derive `query_source` -- this is the save gate and the traceability.
- [ ] `src/api/core/tests.py` -- fix `valid_payload`; cover every backend matrix row. Assert the 400 body contains each finding's message and that no row exists. -- proves the gate
- [ ] `src/ui/src/apiClient.ts`, `src/ui/src/savedQueryForm.ts` -- form metadata, filled by `applyDraftToForm`, emitted by `buildSavedQueryInput` only when all three are set -- carries provenance
- [ ] `src/ui/src/App.tsx` -- clear the metadata on a prompt edit -- the "prompt edited" row
- [ ] `src/ui/tests/savedQueryForm.test.ts` -- apply → build includes metadata; empty form → no metadata keys; a cleared form → no metadata
- [ ] `src/api/README.md`, `src/ui/README.md` -- one or two sentences each: save-time validation and provenance

**Acceptance Criteria:**
- Given a draft with a finding (e.g. bad region), when the researcher applies it and clicks Save without fixing it, then the form shows the finding's message and the saved list is unchanged. After fixing it, the save succeeds.
- Given the save gate in `validate_structured_query_params` is removed, when the backend tests run, then a test fails.
- Given `query_source` derivation is removed, when the backend tests run, then a test fails.

## Implementation Notes

- App code is on `feature/US-009` in `src/api` and `src/ui`, both cut from `develop`. Nothing is committed yet.
- `validate_structured_query_params` raises the validator's messages as a list. The old "must be a JSON object" message is replaced by the validator's own `invalid_type` message.
- UI: three string form fields plus an exported `noDraftProvenance` reset, which `emptySavedQueryForm` spreads and `updateSavedQueryForm` applies on a prompt edit.
- Mutation checks: disabling the save gate fails `test_invalid_structured_params_are_rejected_with_every_finding`. Dropping the `query_source` derivation fails `test_approved_draft_is_saved_as_llm_generated_with_provenance`. Suppressing provenance emission in `buildSavedQueryInput` fails the new UI test.
- Matrix row "prompt edited after apply": the pure reset is unit-tested. The App wiring is not, because the plan rules out a React test harness.
- No model change, so the run did not include a Compose PostgreSQL check.

## Plan Change Log

## Review Triage Log

Pass 1 (quick; lens `quick`). Counts: high 0, medium 1, low 1, false 0, maybe-false 0. Routes: 2 patch.

| # | Lens | Finding | Verdict | Route | Evidence |
|---|------|---------|---------|-------|----------|
| 1 | quick | `curl` save examples in `docs/project-understanding/commands.md` and `04-save-youtube-search-query.md` omit `maxResults`, so they now get a 400 | medium | patch | Confirmed: `maxResults` is in `REQUIRED_SEARCH_PARAMS`. Added `"maxResults":50` to both. |
| 2 | quick | A manual save with `"llm_model_name": ""` stores `""` instead of null | low | patch | Reproduced in `manage.py shell`. `validate` now pops the provenance keys when none is provided, and the manual-save test sends `""` and asserts null; disabling the pop fails that test. |

## Design Notes

The README promised that the draft maps onto the save payload without reshaping, so the client sends the metadata back. A server-side draft store would prove that the model actually produced the values, but it costs a model, a migration and expiry handling. In a single-user research tool, the metadata records where the parameters came from; it is not an authorization claim. Validate its shape and range, and trust the rest.

"Approved" means the researcher pressed Save on a form whose parameters pass the validator. The validation feedback is the rejected save: the server is the only rule source, so the UI cannot drift from it.

Editing the prompt clears the metadata because the stored triple (prompt, model, prompt version) must be the one that produced the parameters. Edited parameter *values* keep it: the researcher reviewing and adjusting the draft is the point of US-008.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test` -- expected: all pass
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: "No changes detected"
- `cd src/ui && npm test && npm run lint && npm run build` -- expected: all pass, `tsc -b` clean

**Manual checks:**
- With the API and `npm run dev` up: draft, apply, set region `col`, save → error shown, nothing saved; fix it to `CO`, save → card appears; `GET /api/projects/<id>/queries/` shows `query_source: "llm_generated"` and the model, version and confidence.
