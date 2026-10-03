# 09 - Save approved parameters with validation feedback

Story: US-009, Save approved parameters with validation feedback.

Status note: this document describes the US-009 implementation **after** the code review of 2026-10-03 and the fixes that followed it.

## What this story added

US-007 reports problems with a parameter set. US-008 lets the researcher edit it. This story closes the loop: the app now refuses to **save** a parameter set that still has problems, and remembers which model produced it.

A researcher can now:

- press **Use these parameters**, edit the values and press **Save query** as before.

- see the list of problems under the form when a value is still invalid, for example a region of `col`. Nothing is saved, and the form keeps every value so they can fix it.

- save once the values are valid, and see the query listed as `llm_generated`, with the model name, prompt version and confidence stored beside it.

A query typed by hand, without a draft, is still saved, and is still `manual`.

## Why this matters

Before this story, the saved-query endpoint accepted **any** JSON object as `structured_query_params`. The validator from US-007 ran on drafts only, so an invalid value could still be saved and would only fail later, when a collection run spent YouTube quota.

The second problem was traceability. The draft response already carried `llm_model_name`, `llm_prompt_version` and `translation_confidence`, but the save endpoint marked those fields read-only and ignored them. Every query, even one the model wrote, was saved as `manual`. A thesis that claims reproducible collection needs to say which model and which prompt produced each query.

US-009 answers this question:

```text
Is every saved query valid, and can a reader tell where its parameters came from?
```

## Key concept: the server is the only judge

The validation feedback is the rejected save. When **Save query** is pressed, the backend runs `validate_search_parameters` (the same function US-007 runs on drafts). If it reports anything, the response is a `400` that lists every message, and the form shows that text in its existing error line.

The frontend does **not** have its own copy of the rules. Two copies, one in Python and one in TypeScript, would drift apart the first time someone changed only one. With one copy, the draft panel and the save button can never disagree.

## Key concept: provenance is all or nothing

"Provenance" means where something came from. Here it is three values: the model name, the prompt version and the confidence.

The rules on save are:

- all three arrive together, or none of them do. A model name without a prompt version cannot be reproduced.

- they need a `natural_language_prompt`. A model name without the prompt it answered is not a record of anything.

- confidence must be between 0 and 1.

- `query_source` is never taken from the browser. The server sets it to `llm_generated` when provenance is present and `manual` when it is not.

The frontend keeps the three values in the form after **Use these parameters**. If the researcher then edits the **prompt**, the form drops them, because the saved prompt would no longer be the one the model saw. Editing the parameter **values** keeps them: reviewing and adjusting the model's proposal is the point of US-008.

## File-by-file explanation

### `src/api/core/serializers.py`

`SavedQuerySerializer` does all the backend work:

- `validate_structured_query_params` calls `validate_search_parameters` and raises every finding's message.

- `Meta.extra_kwargs` makes `structured_query_params` required (before, an omitted field was saved as `{}`) and limits `translation_confidence` to 0..1.

- `validate` applies the all-or-nothing rule, removes blank provenance from a manual save so it is stored as null, and sets `query_source`.

The three provenance fields were removed from `read_only_fields`, so the endpoint now accepts them. `query_source` stays read-only.

### `src/api/core/tests.py`

Six new tests in `SavedQueryApiTests`, one per case in the plan: approved draft, manual save, invalid parameters, missing parameters, partial provenance and out-of-range confidence. The shared `valid_payload` gained `"maxResults": 50`, because `maxResults` is a required YouTube parameter and the old fixture would now be rejected.

### `src/ui/src/savedQueryForm.ts`

The form state gained `llmModelName`, `llmPromptVersion` and `translationConfidence`. `applyDraftToForm` fills them from the draft. `buildSavedQueryInput` sends them only when all three are set. `noDraftProvenance` is the "cleared" value of those three fields, used by the empty form and by a prompt edit.

### `src/ui/src/App.tsx`

`updateSavedQueryForm` clears provenance when the prompt changes, in the same place it already discarded the draft panel.

### `src/ui/src/apiClient.ts`

`SavedQueryInput` gained the three optional provenance fields.

## How the pieces connect

```text
App.tsx  "Use these parameters"
   |
   v
savedQueryForm.ts  applyDraftToForm()   values + provenance into the form
   |
   v   (researcher edits; editing the prompt clears provenance)
App.tsx  "Save query"
   |
   v
savedQueryForm.ts  buildSavedQueryInput()
   |
   v
POST /api/projects/<id>/queries/
   |
   v
serializers.py  SavedQuerySerializer
   +--> validate_search_parameters()   any finding -> 400, nothing saved
   +--> provenance rules               -> query_source
   |
   v
201 and the new query card, or the 400 message under the form
```

## Concepts worth understanding

### Why trust the browser with provenance at all

The browser sends the model name back, and the server cannot prove the model really produced those values. Proving it would need the server to store every draft and the browser to refer to it by id: a new table, a migration and a rule for when old drafts expire.

This is a single-user research tool. Provenance here records where the parameters came from; it does not grant any permission. So the server checks that the values are well formed and leaves it at that. `query_source` is the one field it never takes from the browser.

### Why `""` is removed from a manual save

The model columns allow blank strings, so a direct API call with `"llm_model_name": ""` would have been saved as `""` instead of null. The code review found this. A manual query has no provenance, so `validate` removes the three keys and the database stores null.

## Commands

Backend:

```bash
cd src/api
venv/bin/python manage.py test
venv/bin/python manage.py makemigrations --check --dry-run
```

Frontend:

```bash
cd src/ui
npm test
npm run lint
npm run build
```

Passing looks like `OK` from the backend tests, `No changes detected` from the migration check, `fail 0` from `npm test`, and a finished Vite build.

## How to test manually

1. Set `LLM_API_KEY` in `src/api/.env`, start the app and select a project.

2. Draft a prompt, press **Use these parameters**, give the query a name and set Region to `col`. Press **Save query**. You should see the region message under the form, and no new card.

3. Change Region to `CO` and save. A card appears with source `llm_generated`.

4. Without an API key, check the gate with `curl`:

    ```bash
    curl -sS -X POST "http://127.0.0.1:8000/api/projects/<project-uuid>/queries/" \
      -H "Content-Type: application/json" \
      -d '{"name":"Bad region","search_term":"movilidad Cali","structured_query_params":{"part":"snippet","type":"video","q":"movilidad Cali","maxResults":50,"regionCode":"col"}}'
    ```

    You should see a `structured_query_params` error about `regionCode`.

## Common errors

- **`maxResults is required.`** An older request body without `maxResults`. Add `"maxResults": 50`; the UI always sends it.

- **`Model name, prompt version and confidence must be saved together.`** Only some provenance was sent. Send all three or none.

- **`A prompt is required when saving a generated query.`** Provenance was sent without `natural_language_prompt`.

## Known gap

No test renders the form, so the React wiring that clears provenance on a prompt edit is untested. The reset value it uses, `noDraftProvenance`, is tested. Same reason as US-007: the project has no React rendering test setup.
