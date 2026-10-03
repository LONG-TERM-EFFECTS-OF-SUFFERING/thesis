# 08 - Build editable query parameter review screen

Story: US-008, Build editable query parameter review screen.

Status note: this document describes the US-008 implementation **after** the code review of 2026-10-02 and the fixes that followed it. US-009 later added draft provenance to the same form; that part is explained in [09 - Save approved parameters with validation feedback](09-save-approved-parameters-with-validation-feedback.md).

## What this story added

US-006 drafts YouTube search parameters from a sentence, and US-007 lists what is wrong with them. Both showed the draft **read-only**. This story lets the researcher change the values before saving.

A researcher can now:

- press **Draft parameters** as before.

- press **Use these parameters** in the draft panel. Every drafted value (search term, prompt, dates, max videos, region, language, order) is copied into the saved-query form below.

- edit any of those fields, including a new **Order** dropdown.

- press **Save query**. What is saved is what the form shows.

The draft panel stays on screen as the model's original proposal, so the researcher can compare it with their edits.

## Why this matters

Before this story there were two problems.

First, the researcher could not correct the model. If it picked the wrong region, the only option was to retype the whole query by hand.

Second, the save form ignored most of the parameters. `buildSavedQueryInput` always sent `structured_query_params` as a fixed `{part, type, q}`, so `order`, `maxResults`, dates, region and language never reached the saved parameters, even when the researcher typed them into the form. The columns were saved, but the parameter set a collection run would use was not.

US-008 answers this question:

```text
Can the researcher see, change and save every parameter the collection will use?
```

## Key concept: one form, not two

The draft panel was **not** made editable. Instead, "Use these parameters" copies the draft into the form that already existed for manual queries.

That means one set of inputs, one state object and one save path. A second editable panel would have needed its own state, its own save button and its own rules for which copy wins. The panel becomes a reference ("this is what the model said"), and the form is the review screen ("this is what I will save").

For the same reason, the panel's findings are now labelled **Validation findings (as drafted)**. They describe the model's draft, not the researcher's edits. Checking the edited values happens on save, in US-009.

## Key concept: dates and time zones

YouTube wants dates as RFC 3339 UTC instants, for example `2026-01-01T00:00:00Z`. The browser's `<input type="datetime-local">` shows and returns **local** time with no zone, for example `2025-12-31T19:00:00` in Bogotá.

Two small functions convert between them:

- `toDateTimeLocal` turns the drafted UTC instant into local `YYYY-MM-DDTHH:mm:ss` for the input.

- `optionalDateTime` (already present) turns the input's local value back into a UTC instant on save.

A round trip must give back the **same instant**. The code review found that the first version dropped seconds, so an end-of-day bound of `23:59:59Z` was saved as `23:59:00Z` without the researcher touching it. The fix keeps seconds and sets `step="1"` on both inputs. Without `step="1"`, the browser blocks submitting a value whose seconds are not zero.

## File-by-file explanation

### `src/ui/src/savedQueryForm.ts` (new)

The form's pure logic moved out of `App.tsx` into this module, so it can be tested with `node --test` without React:

- `SavedQueryFormState` and `emptySavedQueryForm`, now with an `order` field.

- `SEARCH_ORDER_VALUES`, the orders YouTube accepts. A comment points at the backend copy in `core/query_translation.py`.

- `toDateTimeLocal`, described above.

- `applyDraftToForm(form, draft)`, which copies the draft into the form and leaves name and notes untouched. It reads `order` from `draft.structured_query_params.order`, because the draft has no top-level `order`.

- `buildSavedQueryInput(form)`, which now builds the full `structured_query_params` from the edited fields, leaves out empty ones, and caps `maxResults` at 50, the same way the backend does.

### `src/ui/src/App.tsx`

- imports the form logic from the new module.

- adds the **Use these parameters** button to the draft panel. It calls `applyDraftToForm` and does **not** discard the draft.

- adds the **Order** `<select>`, whose empty option means "not set".

- adds `step="1"` to both date inputs.

The `AbortController` guard in `handleDraftParameters` is unchanged.

### `src/ui/tests/savedQueryForm.test.ts` (new)

One test per case in the plan: a full draft, a sparse draft, an unparseable drafted date, edited values on save, the `maxResults` cap and default, and missing name or search term. The file pins `process.env.TZ = 'America/Bogota'`, so a bug that mixes up UTC and local time cannot pass on a machine set to UTC, which is what containers usually are.

### `src/ui/README.md`

One paragraph on the flow: draft, apply, edit, save.

## How the pieces connect

```text
App.tsx  "Draft parameters"
   |
   v
draft panel (read-only, "as drafted" findings)
   |
   |  "Use these parameters"
   v
savedQueryForm.ts  applyDraftToForm()    UTC dates -> local input values
   |
   v
saved-query form   (researcher edits any field)
   |
   |  "Save query"
   v
savedQueryForm.ts  buildSavedQueryInput()   local -> UTC, full structured_query_params
   |
   v
POST /api/projects/<id>/queries/
```

No backend file changed in this story.

## Concepts worth understanding

### Why an unparseable date is kept as text

If the model returns `published_after: "not-a-date"`, `toDateTimeLocal` returns the raw text instead of dropping it, so the value is not silently lost. A `datetime-local` input cannot show such text, so the field looks empty while the raw string stays in form state. The draft panel's findings already flag it. This is rare model output, and the review accepted it as is.

### Why `maxResults` is capped at 50

`max_videos_to_discover` is the researcher's intent and can be large, for example 250. `maxResults` is what one YouTube request may ask for, and YouTube allows at most 50. Collection code will paginate to close the gap. The frontend applies the same cap as `draft_from_response` in the backend, so a draft and a hand-edited form produce the same parameters.

## Commands

```bash
cd src/ui
npm test
npm run lint
npm run build
```

Passing looks like `fail 0` from `npm test` and a finished Vite build. `npm run build` also runs `tsc -b`, which `npm test` does not.

## How to test manually

1. Set `LLM_API_KEY` in `src/api/.env`, start the app and select a project.

2. Draft "Most viewed videos about mobility debates in Cali this year", then press **Use these parameters**. The form fills in, and the draft panel stays visible.

3. Change Order to `date` and Region to `CO`, give the query a name and save.

4. Check what was stored:

    ```bash
    curl -sS http://127.0.0.1:8000/api/projects/<project-uuid>/queries/
    ```

    The new query's `structured_query_params` should include `"order": "date"` and `"regionCode": "CO"`.

## Known gap

No test renders `App.tsx`, so the button and the Order dropdown are untested; the functions they call are tested. The project has no React rendering test setup, and the gap is recorded in `_bmad-output/initiative-opentube-insights/deferred-work.md`.
