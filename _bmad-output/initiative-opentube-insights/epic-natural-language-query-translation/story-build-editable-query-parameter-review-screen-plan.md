---
title: 'Build editable query parameter review screen'
type: 'feature'
ticket: 3
created: '2026-10-02'
status: 'built'
baseline_revision: '4353a5d160ed68ff09d01d674c50eb5f42e391b2'
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

**Problem:** A drafted parameter set (US-006/US-007) is shown read-only; the researcher cannot change any value, and the saved-query form ignores the draft entirely: `buildSavedQueryInput` hardcodes `structured_query_params` to `{part, type, q}`, so `order`, `maxResults`, dates, region and language never reach the saved parameters even when typed by hand.

**Approach:** A "Use these parameters" action on the draft panel copies every drafted value into the existing saved-query form, which becomes the editable review screen; the draft panel stays visible as the model's original proposal. Saving builds `structured_query_params` from the (edited) form fields, so what the researcher sees and edits is what is saved.

## Boundaries & Constraints

**Always:** Pure, React-free functions for draft→form and form→input mapping, unit-tested with `node --test`. Dates round-trip RFC 3339 UTC ↔ `datetime-local` (local time) without shifting the instant (minute precision). The draft's prompt fills the prompt field without discarding the draft. Keep the existing `AbortController` + controller-identity guard in `handleDraftParameters` untouched. JSDoc on exported functions.

**Never:** No backend change, no new route, dependency, or React test harness. No save blocking or re-validation of edited values, and no persisting `llm_model_name`/`query_source` (US-009). No collection run (EPIC-004).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Apply full draft | draft with every field set, `order: "viewCount"` | form: search term, prompt, dates (local), max videos, region, language, order filled; name and notes untouched | — |
| Apply sparse draft | nulls for optional fields, no `order` key | those form fields become empty strings | — |
| Bad drafted date | `published_after: "not-a-date"` | field filled with the raw string, not dropped | existing `optionalDateTime` passes it through; backend 400 surfaces |
| Edited save | form with order `date`, max videos `20`, region `CO` | `structured_query_params` = `{part, type, q, maxResults: 20, order, publishedAfter?, publishedBefore?, regionCode, relevanceLanguage?}` with empty fields omitted | — |
| Max videos > 50 | `"120"` | `max_videos_to_discover: 120`, `maxResults: 50` (same clamp as backend) | — |
| No max videos | empty | `maxResults: 50` | — |
| Required missing | blank name or search term | `null`, form shows existing error | unchanged |

</frozen-after-approval>

## Code Map

Baselines: thesis `4353a5d160ed68ff09d01d674c50eb5f42e391b2`, `src/ui` `570a2a8bfe39d32b66fa78dba15b15881808307c`. App code is committed inside `src/ui` on `feature/US-008` (cut from `develop`).

- `src/ui/src/App.tsx` -- `SavedQueryFormState`, `emptySavedQueryForm`, `optionalText`, `optionalDateTime`, `buildSavedQueryInput` (move out), `updateSavedQueryForm` (prompt edit discards draft — keep), `.draft-preview` block and `.field-grid` inputs. Do not touch the health, project-list or abort logic.
- `src/ui/src/apiClient.ts` -- `QueryParameterDraft`, `SavedQueryInput`. Read-only.
- `src/ui/src/savedQueryState.ts` -- existing pure-state module; pattern to copy.
- `src/ui/tests/queryDraftApi.test.ts` -- `draft` fixture to reuse; `tests/savedQueryState.test.ts` shows test style.
- `src/api/core/query_translation.py` -- `SEARCH_ORDER_VALUES` (`date, rating, relevance, title, videoCount, viewCount`) and the `min(max_videos or 50, 50)` clamp to mirror. Read-only.
- `src/ui/src/App.css` -- `.draft-actions`, `.field-grid`.

## Tasks & Acceptance

**Execution:**
- [x] `src/ui/src/savedQueryForm.ts` -- new module: move `SavedQueryFormState`, `emptySavedQueryForm`, `optionalText`, `optionalDateTime`, `buildSavedQueryInput` here; add `order` to the form; add `SEARCH_ORDER_VALUES` (comment pointing at the backend source), `toDateTimeLocal(iso: string | null): string`, and `applyDraftToForm(form, draft): SavedQueryFormState`; `buildSavedQueryInput` emits the full structured params per the matrix -- testable without React.
- [x] `src/ui/tests/savedQueryForm.test.ts` -- cover every matrix row, including a date round-trip (`toDateTimeLocal` → `optionalDateTime` returns the same instant) -- proves mapping.
- [x] `src/ui/src/App.tsx` -- import from the new module; add an Order `<select>` (empty option = not set) to `.field-grid`; add a "Use these parameters" button in `.draft-preview` that sets the form via `applyDraftToForm` without calling `discardQueryDraft` -- the review screen.
- [x] `src/ui/README.md` -- one paragraph: draft, apply, edit, save.

**Acceptance Criteria:**
- Given a ready draft, when the researcher clicks "Use these parameters", then every drafted value appears in an editable form field and the draft panel stays visible.
- Given applied values are edited, when the query is saved, then the POST body's `structured_query_params` reflects the edited values.
- Given `buildSavedQueryInput`'s structured-params mapping is reverted to `{part, type, q}`, when `npm test` runs, then a test fails.

## Implementation Notes

- `applyDraftToForm` reads `order` from `draft.structured_query_params.order` (the draft has no top-level `order`); any non-string becomes `''`.
- The draft panel's findings label now reads "Validation findings (as drafted)".
- A `datetime-local` input cannot display an unparseable value: the raw string stays in form state and is sent on save (backend 400 surfaces), but the browser shows the field empty.
- Mutation check done: removing `maxResults` and the optional keys from `structured_query_params` fails two `savedQueryForm` tests. Round-trip tests also pass under `TZ=America/Bogota` and `TZ=Asia/Kolkata`.

## Plan Change Log

## Review Triage Log

Pass 1 (quick; lens `quick`). Counts: high 0, medium 1, low 3, false 1, maybe-false 0. Routes: 2 patch, 3 reject.

| # | Lens | Finding | Verdict | Route | Evidence |
|---|------|---------|---------|-------|----------|
| 1 | quick | Unparseable drafted date is hidden by `datetime-local` and "cannot be cleared" | low | reject | Hidden is real, but the draft panel already lists the `invalid_format` finding and the field clears by typing any date then deleting it; rare model output, fix adds UI. |
| 2 | quick | `toDateTimeLocal` drops seconds, so `23:59:59Z` saves as `23:59:00Z` unedited | medium | patch | Reproduced from the code; end-of-day bounds are a normal model output. Keep seconds and add `step="1"` (otherwise the browser blocks submit on step mismatch). |
| 3 | quick | Date expectations are computed with `toDateTimeLocal`; UTC/local swap passes under `TZ=UTC` | low | patch | Containers run UTC; pin a non-UTC zone in the test and assert literals. |
| 4 | quick | Saved card does not show `order`, so the plan's manual check cannot pass for it | low | reject | Fix is editing this plan's manual-check wording; `order` is verifiable via `GET /projects/<id>/queries/`. |
| 5 | quick | `maxResults` takes negative/fractional/0 values unchecked | false | reject | Backend `validate_max_videos_to_discover` and `PositiveIntegerField` reject every such value before save; nothing invalid persists. Save blocking is US-009. |

## Design Notes

Reusing the save form instead of making the draft panel editable means one set of inputs, one state object and no second save path; the panel becomes the "as generated" reference beside the edited values. Its validation findings describe the draft, not the edits — label them "as drafted"; live re-validation is US-009.

`toDateTimeLocal` formats the instant's local `YYYY-MM-DDTHH:mm`; an unparseable string is returned unchanged so the researcher sees and fixes it.

## Verification

**Commands:**
- `cd src/ui && npm test && npm run lint && npm run build` -- expected: all pass, `tsc -b` clean
- `git -C src/ui diff --stat develop -- package.json` -- expected: empty

**Manual checks:**
- `npm run dev` with the API up: draft a prompt, click "Use these parameters", change order and region, save; the saved card and `GET /projects/<id>/queries/` show the edited values.
