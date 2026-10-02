# 06 - Generate draft YouTube API parameters from natural language

Story: US-006, Generate draft YouTube API parameters from natural language.

Status note: this document describes the US-006 implementation **after** the code review of 2026-08-05 and the fixes that followed it.

## What this story added

This story lets a researcher describe what they want in plain language and get back a draft set of YouTube search parameters.

A researcher can now:

- type a request such as "Videos about mobility debates in Cali published this year, in Spanish".

- press **Draft parameters** in the saved-query panel.

- read back a proposed search term, date bounds, region, language, discovery limit and the exact YouTube parameters the app would send.

- see which language model produced the draft, which prompt version was used and how confident the model was.

Nothing is saved by this story. The draft is shown for reading only. Editing it (US-008) and saving it (US-009) come later.

## Why this matters

The YouTube Data API expects exact parameter names such as `publishedAfter`, `relevanceLanguage` and `maxResults`. A researcher should not have to learn that vocabulary to collect data.

US-006 answers this question:

```text
Can the app turn a sentence into valid YouTube search parameters that a researcher can inspect?
```

The answer is now yes, and every draft carries the model name and prompt version so another reviewer can tell how it was produced.

## Key concept: the model proposes, Python decides

This is the most important idea in this story.

The language model is **not** allowed to write YouTube parameter names. It only fills in a small, fixed list of typed fields:

```text
search_term, published_after, published_before, max_videos_to_discover,
region_code, relevance_language, order, confidence
```

Our Python code then builds the real YouTube parameters from those fields. This means:

- the model cannot invent a parameter that YouTube does not accept.

- the model cannot misspell `relevanceLanguage`.

- if the model returns nonsense such as `order: "banana"`, our code drops it.

This is enforced twice. First by OpenAI **Structured Outputs** with `strict: true`, which makes the model physically unable to produce a value outside the schema. Second by our own checks in `draft_from_response`, because we never fully trust an external service.

Be precise about what that second layer does and does not do, because the code review found it easy to overstate:

- **Shape** is fully checked. Anything that is not the expected type is rejected or dropped, and a response that is malformed in a way we did not anticipate becomes a `502`, never an unhandled `500`.

- **`order`** is checked against the six values YouTube accepts.

- **Length** is checked for `region_code` and `relevance_language`, so a draft always fits the database columns and can be saved later.

- **Value format is not checked.** A model that answers `region_code: "Colombia"` instead of `"CO"`, or `published_after: "this year"` instead of a timestamp, still produces a draft. Validating that those values are real ISO codes and real timestamps is US-007's job, deliberately kept out of this story.

## File-by-file explanation

### `src/api/core/query_translation.py` (new)

This is the whole translation service. It has two public functions.

`translate_prompt(...)` builds the request, sends it and returns the finished draft. It takes a `transport` argument, which is the function that actually makes the network call. Tests pass their own `transport`, which is how the test suite runs without ever contacting OpenAI.

That seam has a trap worth naming, because the review found it: if _every_ test replaces the transport, then the real transport is never run by anything, and a mistake in the URL, the `Authorization` header or the error handling ships unnoticed. `PostJsonTransportTests` closes that hole by exercising the real `_post_json` with a stubbed `urlopen` - still no network, but the actual request-building and error-mapping code runs.

`draft_from_response(payload)` takes the model's answer and turns it into draft fields plus the assembled `structured_query_params`. It is a pure function: give it the same input and it always returns the same output, with no network involved. That makes it easy to test.

Important constants:

- `RESPONSES_URL` and `TIMEOUT_SECONDS`: where the request goes and how long we wait. These are plain constants, not environment variables, because nothing in this project points them anywhere else.

- `QUERY_TRANSLATION_PROMPT_VERSION`: the version of the instruction text. **Bump this whenever you change `SYSTEM_PROMPT`**, because it is stored with each draft as evidence of how the parameters were produced.

- `DRAFT_SCHEMA`: the JSON Schema the model must obey.

Two error types exist so the endpoint can tell the difference between a refusal and a failure:

- `QueryTranslationRefused`: the model declined the request. The researcher sees why.

- `QueryTranslationError`: the call failed, timed out or returned something unusable.

The network helper uses Python's standard-library `urllib.request`. No extra dependency was added because the story only makes one POST request to one URL. Its error message is deliberately vague ("Query translation request failed.") so an upstream error body can never echo the API key back to the browser. The real cause is written to the log instead, including the HTTP status when there is one.

One subtlety the review caught: `except (OSError, ValueError)` looks like it covers every network problem, but it does not. `http.client.HTTPException` - the class behind `IncompleteRead` and `BadStatusLine`, which is what you get when a connection dies partway through a response - inherits from neither, so it has to be named explicitly. Missing it turned a realistic network failure into a `500`.

`translate_prompt` also refuses to pass the project's `default_language` into the prompt unless it looks like a language tag such as `es` or `es-419`. That field is free text a user typed, and it is concatenated into the instructions we send the model, so it is a place where stored text could otherwise smuggle in instructions of its own.

### `src/api/core/views.py`

Adds `SavedQueryDraftView`, the endpoint behind the button.

It reuses `ProjectOwnerMixin`, so the same owner rules that protect projects and saved queries protect drafts too: asking for a draft under someone else's project returns `404`.

`get_project()` moved from `SavedQueryListCreateView` up into `ProjectOwnerMixin`, so both project-scoped views share one implementation instead of two copies.

The view maps problems to distinct HTTP statuses:

| what happened                      | status | why this status                                              |
| :--------------------------------- | :----: | :----------------------------------------------------------- |
| Prompt was blank or missing        |  400   | The researcher can fix it                                    |
| Prompt was longer than 2000 chars  |  400   | The researcher can fix it, and the provider bills per token  |
| Request body was not a JSON object |  400   | The caller sent the wrong shape                              |
| `LLM_API_KEY` is not set           |  503   | The server is not configured yet; not the researcher's fault |
| Model refused the request          |  422   | The request was understood but declined                      |
| Timeout, HTTP error, unusable JSON |  502   | The upstream service failed                                  |

A `500` would tell the researcher nothing. Each of these tells them what to do next.

The code review found four ways an unexpected upstream answer could still escape as a `500`, which is exactly the outcome this table exists to prevent. All four are now covered by tests: a `NaN` confidence (JSON allows it, and comparing a `Decimal("NaN")` raises), a number where a list belongs, a connection that dies mid-read, and a request body that is a JSON list instead of an object.

The `502` response body stays generic on purpose, but the real cause is now written to the server log with its HTTP status. Without that, an expired API key and a brief network failure look identical to whoever is running the app.

### `src/api/core/urls.py`

Adds `POST /api/projects/<uuid:project_id>/queries/draft/`.

Both this route and the existing `queries/` route are listed before the `projects/<uuid:pk>/` detail route, matching the order the project already used.

A note on ordering, because it is easy to assume the wrong thing: Django matches `path()` patterns against the **whole** remaining URL, not a prefix. `projects/<uuid>/queries/` therefore cannot swallow `projects/<uuid>/queries/draft/` no matter which one comes first. Order only decides between patterns that can genuinely match the same URL.

### `src/api/opentube_insights_api/settings.py`

Adds `env_str`, a small helper that reads a trimmed string from the environment, matching the existing `env_bool` and `env_list` helpers.

Adds two settings:

- `LLM_API_KEY`: no default on purpose. A missing key must fail loudly, not translate against nothing.

- `LLM_MODEL`: defaults to `gpt-5.6-luna`. This file is the **only** place that default is written. `docker-compose.yml` passes the variable through as an optional override rather than repeating the value, so changing models is a one-line edit instead of five.

### `src/ui/src/apiClient.ts`

Adds the `QueryParameterDraft` type, the `isQueryParameterDraft` runtime check and the `draftQueryParameters` call.

The runtime check exists because TypeScript types disappear when the code runs. Without it, a backend change could silently feed the wrong shape into the screen.

### `src/ui/src/App.tsx`

Adds the **Draft parameters** button under the natural-language prompt box, plus a read-only summary of the returned draft.

The draft state carries the project id it belongs to:

```ts
type QueryDraftState =
    | { status: 'idle' }
    | { status: 'drafting'; projectId: string }
    | { status: 'ready'; projectId: string; draft: QueryParameterDraft }
    | { status: 'error'; projectId: string; message: string };
```

This solves a real problem. If you ask for a draft, then switch projects before the answer arrives, the answer belongs to the old project. Because the state remembers which project it was for, the screen simply does not show it. This mirrors how `savedQueryState.ts` protects the saved-query list.

The code review showed that tag was not enough on its own. It controlled what was _displayed_, but a late answer still _overwrote_ the state, so a slow draft for one project could wipe out a newer draft for another. Two additions fix that at the source:

- An `AbortController` kept in a `useRef`. Starting a new draft cancels the previous request, and leaving the screen cancels it too, so nothing keeps running for 30 seconds after it stopped mattering.

- An identity check before writing state. A response only updates the screen if its controller is still the current one. A cancelled request is recognized through the existing `isAbortError` helper and stays silent instead of showing an error the researcher did not cause.

The draft is also discarded whenever the prompt is edited or the form is saved. A draft describes the prompt it came from, so leaving it on screen under different text would be misleading. For the same reason the panel now prints the prompt it was drafted from, and the whole result is wrapped in `aria-live="polite"` so a screen reader announces it - the same treatment the saved-query list already had.

## How the pieces connect

```text
App.tsx  "Draft parameters" button
   |
   v
apiClient.ts  draftQueryParameters()
   |  POST /api/projects/<id>/queries/draft/
   v
views.py  SavedQueryDraftView
   |  owner check, blank prompt check, API key check
   v
query_translation.py  translate_prompt()
   |  one POST to OpenAI with a strict JSON schema
   v
query_translation.py  draft_from_response()
   |  builds structured_query_params in Python
   v
back to the screen, read-only
```

## How to test manually

1. Set a real key in `src/api/.env`:

    ```bash
    LLM_API_KEY=sk-...
    ```

2. Start the app and create or select a project.

3. Type a natural-language prompt, for example "Videos about mobility debates in Cali published this year, in Spanish".

4. Press **Draft parameters**.

5. Check the draft: the search term should be short and searchable, the region should be `CO`, the language `es`, and `maxResults` should be at most 50.

Without a key, the same button should show a clear message that the LLM API key is not configured. That is expected behavior, not a bug.

## Common errors and what they mean

|                     message                     | what it means                                                       |
| :---------------------------------------------: | :------------------------------------------------------------------ |
|        `LLM API key is not configured.`         | `LLM_API_KEY` is empty. Set it in `src/api/.env` and restart.       |
|           `Query translation failed.`           | The model call timed out or returned something unusable. Try again. |
|        A refusal message from the model         | The model declined this request. Rewrite the prompt.                |
|   `Write a natural-language prompt first...`    | The prompt box is empty. This check runs in the browser.            |
| `Query draft response had an unexpected shape.` | Backend and frontend disagree about the response. Check both.       |
