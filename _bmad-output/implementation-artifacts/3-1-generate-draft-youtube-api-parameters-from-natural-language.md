---
baseline_commit: bfc37c82841658a19d0cf57182fe337079112738
---

# Story 3.1: Generate Draft YouTube API Parameters from Natural Language

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a researcher,
I want the app to draft YouTube API parameters from my natural-language request,
so that I do not need to know the YouTube Data API syntax.

## Acceptance Criteria

1. The backend exposes an owner-scoped, project-scoped endpoint that accepts a natural-language prompt and returns a **draft** parameter set for YouTube `search.list`. The draft is **not persisted** by this story.
2. The draft response fields map 1:1 onto existing `SavedQuery` fields (`natural_language_prompt`, `search_term`, `published_after`, `published_before`, `max_videos_to_discover`, `region_code`, `relevance_language`, `structured_query_params`, `llm_model_name`, `llm_prompt_version`, `translation_confidence`) so US-009 can save the draft without reshaping it.
3. Translation calls OpenAI's Responses API with **Structured Outputs** (`text.format.type = "json_schema"`, `strict: true`), so the model cannot return unknown keys or invalid enum values.
4. `structured_query_params` is assembled **in Python from the model's typed fields**, never copied verbatim from model output. The LLM cannot invent YouTube parameter names.
5. `structured_query_params.maxResults` is clamped to YouTube's per-request limit of `50`, while `max_videos_to_discover` keeps the researcher's full intent.
6. Every call records reproducibility metadata on the response: resolved model id (`llm_model_name`), prompt template version (`llm_prompt_version`) and model-reported `translation_confidence`.
7. Failure modes return distinct, actionable statuses instead of a 500: blank prompt → 400, missing `LLM_API_KEY` → 503, model refusal → 422, upstream timeout/HTTP/parse failure → 502.
8. The frontend adds a "Draft parameters" action beside the existing natural-language prompt field that calls the endpoint and shows the returned draft **read-only**. Editing and saving the draft belong to US-008 and US-009.
9. Automated backend and frontend tests cover payload construction, response parsing, `maxResults` clamping, each failure mode, owner isolation and the client call — **with zero live OpenAI or YouTube network calls**.

## Tasks / Subtasks

- [x] Task 1: Add LLM configuration to the environment surface (AC: 3, 6, 7)
  - [x] Add `LLM_MODEL` next to the existing `LLM_API_KEY` in `src/api/.env.example`, default `gpt-5.6-luna`.
  - [x] Pass `LLM_MODEL` through the `api` service in `src/docker-compose.yml` (`LLM_API_KEY` is already wired).
  - [x] Read both through the existing `settings_environ` pattern in `src/api/opentube_insights_api/settings.py`; do **not** invent a parallel env-reading path.
  - [x] `LLM_API_KEY` has **no** default and must not be logged.
  - [x] Endpoint URL and request timeout are module constants in `query_translation.py`, **not** env vars — nothing in this project points them anywhere else, and tests inject `transport` instead.
- [x] Task 2: Add the query-translation service module (AC: 3, 4, 5, 6, 7)
  - [x] Create `src/api/core/query_translation.py` with `from __future__ import annotations`.
  - [x] Module constants: `QUERY_TRANSLATION_PROMPT_VERSION = "v1"`, the system prompt, `DRAFT_SCHEMA`, `RESPONSES_URL`, `TIMEOUT_SECONDS = 30`.
  - [x] `translate_prompt(prompt, *, model, api_key, default_language=None, transport=None)` → draft dict: builds the request body inline from the constants, calls `transport`, returns the parsed draft. `transport` is the injectable seam tests use — default it to the module's stdlib POST helper.
  - [x] `draft_from_response(payload)` → draft dict: pure function that maps model output to the draft fields **and** assembles `structured_query_params` (`part`, `type`, `q`, `maxResults`, `publishedAfter`, `publishedBefore`, `regionCode`, `relevanceLanguage`, `order`), omitting `None` values. Raises a module-local error for refusals and malformed output.
  - [x] Two public functions is the whole module. Do not split payload building or param assembly into their own functions — `draft_from_response` is already the pure, directly testable half.
  - [x] Keep the module import-safe: no env reads, no network, no key resolution at import time.
- [x] Task 3: Add the draft endpoint (AC: 1, 2, 7)
  - [x] Add `SavedQueryDraftView` to `src/api/core/views.py`, reusing `ProjectOwnerMixin` and the `get_project()` 404 behavior already used by `SavedQueryListCreateView`. Do **not** write a second owner-resolution path.
  - [x] Route `POST /api/projects/<uuid:project_id>/queries/draft/` in `src/api/core/urls.py`, placed **before** `projects/<uuid:pk>/` like the existing query route.
  - [x] Pass the project's `default_language` into `translate_prompt` as a hint for `relevance_language`.
  - [x] Map service errors to 400 / 503 / 422 / 502 per AC 7; never leak the API key or raw upstream body in the error message.
- [x] Task 4: Add backend tests with a fake transport (AC: 9)
  - [x] Test `translate_prompt` sends `text.format.type == "json_schema"` with `strict is True` and the prompt (assert on the body the fake `transport` receives).
  - [x] Test `draft_from_response` maps a captured success payload to the draft fields, clamps `maxResults` to 50 when `max_videos_to_discover` is 250, and omits `None` keys.
  - [x] Test refusal payload, malformed-JSON payload and transport timeout each raise the expected error.
  - [x] Test the endpoint: 200 happy path with fake transport, 400 blank prompt, 503 missing key, 404 for another owner's project.
  - [x] Store the captured OpenAI success payload as a fixture; US-035 will reuse it.
- [x] Task 5: Extend the frontend API boundary (AC: 8, 9)
  - [x] Add `QueryParameterDraft` type, `isQueryParameterDraft` runtime guard and `draftQueryParameters(projectId, prompt, signal?)` to `src/ui/src/apiClient.ts`, using `buildApiUrl` and the existing `readJson` error flattening.
  - [x] Add `src/ui/tests/queryDraftApi.test.ts` covering request routing, shape validation and error-message propagation.
- [x] Task 6: Add the read-only draft UI (AC: 8)
  - [x] In `src/ui/src/App.tsx`, add a "Draft parameters" button next to the existing `naturalLanguagePrompt` textarea in the saved-query form.
  - [x] Show pending/error state and render the returned draft as a read-only summary plus a formatted `structured_query_params` block.
  - [x] Do **not** auto-fill the saved-query form fields and do **not** add routing — editing is US-008.
  - [x] Preserve existing health-check, project and saved-query behavior; keep styling in `src/ui/src/App.css`.
- [x] Task 7: Docs and validation (AC: 1-9)
  - [x] Update `src/api/README.md` with the draft endpoint example and the new env variables.
  - [x] Add `docs/project-understanding/06-generate-draft-youtube-api-parameters.md` and link it from `docs/project-understanding/index.md` **after** code review fixes land.
  - [x] Run backend and frontend validation commands listed under Testing Requirements.

### Review Findings

Code review 2026-08-05. Layers: Blind Hunter, Edge Case Hunter, Acceptance Auditor. All three completed.

Decisions resolved (Brandon, 2026-08-05):

- [x] [Review][Decision] Model-output validation scope vs US-007 → **length guards only**. Truncate or null `region_code` above `max_length=10` and `relevance_language` above `max_length=20` so every draft is always savable by US-009. No ISO format checks, no RFC 3339 parsing and no `published_after <= published_before` check — those stay with US-007. Tracked as a patch below.
- [x] [Review][Decision] `maxResults` with no discovery intent → **keep 50**. It is the useful default for a bulk-discovery research tool and is what the README and understanding doc already document. Fix the prose to describe 50 as the default rather than implying the value was clamped from an intent that does not exist. Tracked as a patch below.
- [x] [Review][Decision] Auth and throttling on the first metered endpoint → **prompt length cap now, auth deferred**. The cap is input validation at a trust boundary and is tracked as a patch below. The authentication/permission/throttle posture is left unchanged and moved to deferred work.

Patches:

- [x] [Review][Patch] Malformed model output escapes as an uncaught 500 instead of the documented 502 [src/api/core/query_translation.py:911, :857-864] — `json.loads` accepts bare `NaN`, and `min(max(Decimal('NaN'), …))` raises `decimal.InvalidOperation`; `{"output": 5}` or `{"content": 7}` raises `TypeError` from `for item in output or []`. Neither is a `QueryTranslationError`, so `SavedQueryDraftView` does not catch it. Both reproduced against the real endpoint.
- [x] [Review][Patch] Non-object JSON request body returns an uncaught 500 instead of 400 [src/api/core/views.py:200] — `request.data.get(...)` raises `AttributeError` for a body of `[1,2,3]` or `"hello"`, both of which `JSONParser` accepts. Reproduced against the real endpoint.
- [x] [Review][Patch] Transport error mapping misses `http.client.HTTPException` and is never executed by any test [src/api/core/query_translation.py:940, src/api/core/tests.py:340-345, :427] — `except (OSError, ValueError)` does not catch `IncompleteRead`/`BadStatusLine`, so a truncated upstream response 500s. Every test either injects `transport=` or patches `_post_json` wholesale, so `send` — the URL, the `Bearer` header, the timeout and the error mapping — never runs. The two "failure" tests raise `QueryTranslationError` from the fake and assert it was raised. AC 9 claims coverage of each failure mode; the 502 path's real code is untested, which is precisely what hid this bug.
- [x] [Review][Patch] `_confidence` fabricates reproducibility metadata instead of failing [src/api/core/query_translation.py:909] — a missing key or `"confidence": "high"` returns `"0.0000"`, indistinguishable from a model genuinely reporting zero confidence. `confidence` is in `DRAFT_SCHEMA["required"]`, so its absence is malformed output and should raise. AC 6 requires the *model-reported* confidence.
- [x] [Review][Patch] Integral-float `max_videos_to_discover` is silently discarded [src/api/core/query_translation.py:810] — `isinstance(250.0, int)` is `False`, and `250.0` is a legal JSON encoding of a schema `integer`. The researcher's stated limit vanishes with no error and `maxResults` quietly falls back.
- [x] [Review][Patch] Both `default_language` hint tests are vacuous [src/api/core/tests.py:326, :458] — they assert `"es"` appears in the prompt, but `SYSTEM_PROMPT` already contains `"es"` inside "researcher". Deleting the entire `if default_language:` block leaves both tests green. Verified.
- [x] [Review][Patch] No upper bound on prompt length [src/api/core/views.py:200, src/ui/src/App.tsx:513] — only emptiness is checked, so anything up to `DATA_UPLOAD_MAX_MEMORY_SIZE` (2.5 MB) is forwarded verbatim to a metered API. The textarea has no `maxLength` either.
- [x] [Review][Patch] `default_language` is interpolated into the system prompt unvalidated [src/api/core/query_translation.py:88-92] — `ResearchProject.default_language` is free text (`CharField(max_length=20)`, no choices, no validator) concatenated straight into `SYSTEM_PROMPT` on every draft for that project.
- [x] [Review][Patch] Upstream failures are never logged server-side [src/api/core/query_translation.py:942, src/api/core/views.py:226] — the real exception is replaced with a generic message and `HTTPError.code` is never read or logged. An invalid API key, a 429 and a network blip are indistinguishable in the response *and* in the logs. Keeping the response generic is right; discarding the status code server-side is not.
- [x] [Review][Patch] Draft request has no cancellation and no sequence guard [src/ui/src/App.tsx:326-349, src/ui/src/apiClient.ts:285] — `draftQueryParameters` accepts a `signal` the only caller never passes, unlike every other call in `App.tsx`. `handleDraftParameters` writes `setQueryDraft` unconditionally, so a late response for project A overwrites an in-flight draft for project B: B's spinner disappears mid-request, and if B resolves first its result is destroyed. The `projectId` tag guards display but not writes. US-005's review flagged exactly this class of bug.
- [x] [Review][Patch] Stale draft survives prompt edits and form reset [src/ui/src/App.tsx:380, :514-522] — `updateSavedQueryForm` does not touch `queryDraft`, and `handleSavedQuerySubmit` clears the form without clearing the draft. After saving, an empty prompt box sits above a populated draft panel from the previous prompt. The panel never renders `draft.natural_language_prompt`, so the mismatch is invisible.
- [x] [Review][Patch] Draft result and error are not announced to screen readers [src/ui/src/App.tsx:540-557] — the equivalent existing panel uses `aria-live="polite"` (`App.tsx:645`); the draft panel and its `form-error` sibling announce nothing, on an async action that can take 30 s.
- [x] [Review][Patch] `src/api/README.md` documents a round-trip that always 400s [src/api/README.md:36] — "an approved draft can be posted to `/api/projects/<uuid>/queries/` unchanged" is false: `name` is required and absent from the draft, and `llm_model_name`, `llm_prompt_version` and `translation_confidence` are `read_only_fields` so the provenance is dropped and `query_source` stays `"manual"`.
- [x] [Review][Patch] The understanding doc's route-ordering explanation is wrong [docs/project-understanding/06-generate-draft-youtube-api-parameters.md] — "the `draft/` route is listed before the `queries/` route so Django matches it correctly". `path()` patterns are fully anchored, so `projects/<uuid>/queries/` can never shadow `projects/<uuid>/queries/draft/` in either order. A beginner-facing learning doc teaching a wrong invariant is a defect.
- [x] [Review][Patch] `.draft-preview dl` is not collapsed on mobile [src/ui/src/App.css:241, :280] — `.query-card dl` is overridden to `grid-template-columns: 1fr` in the 860 px media query; `.draft-preview dl`, copied from it with four equal columns, is not, so eight dt/dd pairs squash into four columns.
- [x] [Review][Patch] `Any` in nine signatures with no justification [src/api/core/query_translation.py] — project-context.md:251 allows it at an untrusted boundary with a short justification. `DRAFT_SCHEMA`, `translate_prompt`'s return and the draft dict are not that boundary; their shape is fixed and already spelled out by the frontend `QueryParameterDraft` type.
- [x] [Review][Patch] Wrong and unused type annotation on the view handler [src/api/core/views.py:188] — `project_id: str` with a matching docstring, but `<uuid:project_id>` passes a `uuid.UUID`. The parameter is also unused, since the view reads `self.kwargs["project_id"]` via `get_project()`.
- [x] [Review][Patch] `src/.env.example` missing `LLM_MODEL` [src/.env.example] — `src/docker-compose.yml` now consumes `${LLM_MODEL:-gpt-5.6-luna}` but the Compose override example was not updated. `LLM_MODEL` is not a secret, so unlike `LLM_API_KEY` it belongs there.
- [x] [Review][Patch] Default model id duplicated in five places [src/docker-compose.yml:40, src/api/opentube_insights_api/settings.py:240, src/api/.env.example:14, src/api/README.md:24, docs/project-understanding/06-…md] — and Compose's `:-gpt-5.6-luna` means the app can never observe an unset `LLM_MODEL`, so `settings.py`'s default is unreachable under Docker. Changing models is five edits and guaranteed drift.
- [x] [Review][Patch] Over-long `region_code` / `relevance_language` produce an unsavable draft [src/api/core/query_translation.py:803-804] — from decision 1. Guard length only: values above `SavedQuery.region_code` `max_length=10` and `relevance_language` `max_length=20` become `None` rather than being passed through. Format and date-range validation remain US-007's.
- [x] [Review][Patch] Docs describe `maxResults: 50` as a clamp when there is no intent to clamp [src/api/README.md:63, docs/project-understanding/06-…md] — from decision 2. The value stays 50; the prose should say 50 is the default per request and is also the ceiling that a larger `max_videos_to_discover` is clamped to.
- [x] [Review][Patch] Understanding doc and its index link shipped before code review [docs/project-understanding/06-…md, docs/project-understanding/index.md] — Task 7 says to add them "after code review fixes land" and project-context.md:272 repeats it. The doc admits the ordering was skipped in its own status note. Regenerate once the patches above are applied.

Deferred:

- [x] [Review][Defer] 30 s synchronous upstream call blocks sync Gunicorn workers [src/api/core/query_translation.py:15] — deferred, architectural and outside story scope. Three concurrent drafts stall every worker; `urlopen(timeout=)` bounds each socket operation, not total elapsed time, so a trickling upstream outlives the 30 s budget and hits the 60 s worker timeout instead of returning 502.
- [x] [Review][Defer] `get_project()` is now inherited by views whose URLs have no `project_id` [src/api/core/views.py:83] — deferred, not reachable today. Moving it into `ProjectOwnerMixin` was correct for the two project-scoped views, but `ResearchProjectListCreateView` and `ResearchProjectDetailView` would raise `KeyError` rather than `Http404` if it were ever called there.
- [x] [Review][Defer] No authentication, permission or throttle classes on the API [src/api/opentube_insights_api/settings.py:242] — deferred per decision 3: the app binds to `127.0.0.1` and auth is a cross-cutting concern no story owns yet. `REST_FRAMEWORK` sets no `DEFAULT_AUTHENTICATION_CLASSES`, `DEFAULT_PERMISSION_CLASSES` or `DEFAULT_THROTTLE_*`, and `resolve_project_owner` creates a fallback `local-researcher` user, so any caller that can reach the port can spend the operator's OpenAI key. The prompt length cap is being applied now; rate limiting is not.
- [x] [Review][Defer] Unrelated main-repo edits ride along in this diff [.gitignore, docs/project-understanding/index.md] — deferred, pre-existing bookkeeping. `.gitignore` gains `.claude` and loses its trailing newline; `index.md` flips US-003 from `Review` to `Done` (correct per sprint-status, but another story's bookkeeping) and reflows the whole table's whitespace, obscuring the one row actually added.

Dismissed as noise: the US-035 fixture comment in `core/tests.py` (Task 4 explicitly required storing the captured payload for reuse) and the claim that re-validating `order` against `SEARCH_ORDER_VALUES` trespasses on US-007 (defensively re-checking untrusted output is correct; strict mode is a provider promise, not a guarantee).

## Dev Notes

### Sprint and Dependency Context

US-006 is the first story in EPIC-003, "natural language query translation," and the first story of the epic — epic status moves to `in-progress`. Sprint 2 goal: production wiring and parameter drafting.

Epic 3 division of labour — **stay inside your lane**:

| Story  | Owns                                                        | Not this story                     |
| ------ | ----------------------------------------------------------- | ---------------------------------- |
| US-006 | Draft generation from natural language (**this story**)     | —                                  |
| US-007 | Allowlist + YouTube-rule validation of generated parameters | Do not build a validation layer    |
| US-008 | Editable parameter review screen                            | Do not make the draft editable     |
| US-009 | Saving approved parameters                                  | Do not persist the draft           |

US-005 built `SavedQuery` with LLM metadata fields already reserved (`llm_model_name`, `llm_prompt_version`, `translation_confidence`, `query_source='llm_generated'`). This story fills those values in a **transient** response; US-009 writes them to the database.

### Current Code State

Backend (`src/api/core/`):

- `models.py` — `ResearchProject` and `SavedQuery` exist. **No model change is needed in this story.** The LLM metadata columns already exist (migrations `0002_savedquery`, `0003_rename_savedquery_max_results`).
- `views.py` — `default_owner_username`, `resolve_project_owner`, `ProjectOwnerMixin`, `ResearchProjectListCreateView`, `ResearchProjectDetailView`, `SavedQueryListCreateView` (has the `get_project()` / `Http404` pattern to reuse), `health`.
- `urls.py` — `/api/health/`, `/api/projects/`, `/api/projects/<uuid:project_id>/queries/`, `/api/projects/<uuid:pk>/`. Route ordering matters: the queries route sits **before** the detail route.
- `serializers.py` — `SavedQuerySerializer` marks `query_source`, `llm_model_name`, `llm_prompt_version`, `translation_confidence` as read-only. Leave that alone; the draft endpoint does not go through this serializer.
- `settings.py` — `load_local_env`, `settings_environ`, `env_bool`, `env_list`, `resolve_sqlite_path`. Reuse `settings_environ`; add a small typed helper if you need an int/str read.
- `tests.py` — single test module, Django `TestCase` style. Append there.

Frontend (`src/ui/src/`):

- `apiConfig.ts` — `normalizeApiBaseUrl`, `buildApiUrl`. All URL construction goes through here.
- `apiClient.ts` — `isRecord`, `isNullableString`, `errorDetail`, `readJson` and per-resource guards. **Reuse `readJson` and `errorDetail`**; do not write new error flattening.
- `App.tsx` (612 lines) — single-screen workflow with `SavedQueryFormState` that already has a `naturalLanguagePrompt` field. Extend in place.
- `projectState.ts` / `savedQueryState.ts` — list-merge helpers that protect against stale/late responses. Follow the same pattern if you add list state (you probably do not need to for a single transient draft).
- Tests are plain `node --test` files in `src/ui/tests/`. **No React component test framework is installed** — test the API boundary, not the component.

### LLM Provider Decision

**OpenAI API** is the selected provider (Brandon's decision, 2026-08-05). It matches the reference framework already cited in `content/07-reference_framework.tex:28` (GPT-4 / Spider text-to-structured precedent).

**Do not add the `openai` Python SDK.** This story makes exactly one POST to one endpoint with a JSON body. `urllib.request` from the standard library covers it in ~15 lines, keeps the API container lean, and makes the `transport` seam trivial to fake in tests — which is a hard requirement of AC 9 and of US-035. This follows the dependency order in `_bmad-output/project-context.md`: existing code → platform features → installed dependencies → new library.

Mark the ceiling in code so the upgrade path is explicit:

```python
# ponytail: single stdlib POST, no retry/backoff. Switch to the `openai` SDK (2.52.0+)
# if retries, streaming or multi-endpoint use land.
```

### Request Contract

```
POST /api/projects/<uuid:project_id>/queries/draft/
```

Request:

```json
{ "natural_language_prompt": "Videos about mobility debates in Cali published this year, Spanish, about 250 videos" }
```

Success response (`200`):

```json
{
  "natural_language_prompt": "Videos about mobility debates in Cali published this year, Spanish, about 250 videos",
  "search_term": "movilidad Cali debate",
  "published_after": "2026-01-01T00:00:00Z",
  "published_before": null,
  "max_videos_to_discover": 250,
  "region_code": "CO",
  "relevance_language": "es",
  "structured_query_params": {
    "part": "snippet",
    "type": "video",
    "q": "movilidad Cali debate",
    "maxResults": 50,
    "publishedAfter": "2026-01-01T00:00:00Z",
    "regionCode": "CO",
    "relevanceLanguage": "es",
    "order": "relevance"
  },
  "llm_model_name": "gpt-5.6-luna",
  "llm_prompt_version": "v1",
  "translation_confidence": "0.8200"
}
```

Note `max_videos_to_discover: 250` alongside `maxResults: 50` — researcher intent vs. YouTube's per-request cap. Later collection code (US-015) paginates to reach the intent.

`translation_confidence` is serialized as a **string with 4 decimal places** to match the existing `DecimalField(max_digits=5, decimal_places=4)` rendering that `SavedQuerySerializer` already produces. Keeping the same representation is what makes AC 2's 1:1 mapping real.

Error responses:

| Condition                                  | Status | Body                                                                         |
| ------------------------------------------ | ------ | ---------------------------------------------------------------------------- |
| Blank or missing `natural_language_prompt` | 400    | `{"natural_language_prompt": ["A natural language prompt is required."]}`     |
| `LLM_API_KEY` not configured               | 503    | `{"detail": "LLM API key is not configured."}`                                |
| Model refused the request                  | 422    | `{"detail": "<refusal text from the model>"}`                                 |
| Timeout / upstream HTTP error / bad JSON   | 502    | `{"detail": "Query translation failed."}`                                     |
| Project not owned by the effective owner   | 404    | DRF default                                                                   |

Never include the API key, request headers or the raw upstream body in an error response or log line.

### OpenAI Responses API Details

Endpoint: `POST https://api.openai.com/v1/responses`
Headers: `Authorization: Bearer $LLM_API_KEY`, `Content-Type: application/json`

Request body shape:

```json
{
  "model": "gpt-5.6-luna",
  "input": [
    { "role": "system", "content": "<translation system prompt>" },
    { "role": "user", "content": "<natural language prompt>" }
  ],
  "text": {
    "format": {
      "type": "json_schema",
      "name": "youtube_search_draft",
      "strict": true,
      "schema": { "...": "see below" }
    }
  }
}
```

Strict-mode schema rules (these are enforced by the API — violating them is a 400 from OpenAI):

- Root must be an object; `anyOf` is not allowed at the root.
- `additionalProperties: false` on every object.
- **Every** property must be listed in `required`. Optional values are expressed as `"type": ["string", "null"]`, and nullable enums must include `null` in the enum list.

Schema to use:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "search_term", "published_after", "published_before", "max_videos_to_discover",
    "region_code", "relevance_language", "order", "confidence"
  ],
  "properties": {
    "search_term": { "type": "string" },
    "published_after": { "type": ["string", "null"] },
    "published_before": { "type": ["string", "null"] },
    "max_videos_to_discover": { "type": ["integer", "null"] },
    "region_code": { "type": ["string", "null"] },
    "relevance_language": { "type": ["string", "null"] },
    "order": { "type": ["string", "null"], "enum": ["date", "rating", "relevance", "title", "videoCount", "viewCount", null] },
    "confidence": { "type": "number" }
  }
}
```

`videoDuration`, `safeSearch`, `videoCaption` and `videoDefinition` are deliberately **not** in v1. They map to no `SavedQuery` column, a natural-language prompt rarely signals them, and US-008 gives the researcher a screen to set them by hand. Add them to the schema when a real prompt needs one.

Success payload structure to parse — the JSON string lives in the first `output_text` content part:

```json
{ "output": [ { "type": "message", "content": [ { "type": "output_text", "text": "{\"search_term\": ...}" } ] } ] }
```

Refusal payload — detect `type == "refusal"` and surface `refusal` as the 422 detail:

```json
{ "output": [ { "type": "message", "content": [ { "type": "refusal", "refusal": "I'm sorry, I cannot assist with that request." } ] } ] }
```

The system prompt must instruct the model to: extract a concise `search_term`, emit RFC 3339 UTC timestamps (`1970-01-01T00:00:00Z`) for date bounds, use ISO 3166-1 alpha-2 for `region_code` and ISO 639-1 for `relevance_language`, return `null` rather than guessing when the prompt gives no signal, and report `confidence` between 0 and 1.

### YouTube `search.list` Parameter Rules

Verified against the official reference on 2026-08-05:

- `maxResults`: integer 0–50, default 5. **Per request**, not per collection.
- `publishedAfter` / `publishedBefore`: RFC 3339, e.g. `1970-01-01T00:00:00Z`.
- `order`: `date`, `rating`, `relevance` (default), `title`, `videoCount`, `viewCount`.
- `part` must be `"snippet"` and `type` must be `"video"` for this workflow — both are constants, not model output.
- For US-008 later: `videoDuration` (`any`/`short`/`medium`/`long`), `safeSearch` (`moderate`/`none`/`strict`), `videoCaption` and `videoDefinition` exist and are only valid when `type=video`.

**Do not call the YouTube API in this story.** Discovery is US-015.

### Architecture and File Structure Requirements

Expected backend files:

- `src/api/core/query_translation.py` (new)
- `src/api/core/views.py`
- `src/api/core/urls.py`
- `src/api/core/tests.py`
- `src/api/opentube_insights_api/settings.py`
- `src/api/.env.example`
- `src/api/README.md`

Expected frontend files:

- `src/ui/src/apiClient.ts`
- `src/ui/src/App.tsx`
- `src/ui/src/App.css`
- `src/ui/tests/queryDraftApi.test.ts` (new)

Expected main-repo files:

- `src/docker-compose.yml` (new LLM env passthrough)
- `docs/project-understanding/06-generate-draft-youtube-api-parameters.md` and `index.md` (after review)

**No migration and no model change in this story.** `venv/bin/python manage.py makemigrations --check --dry-run` must stay clean.

### Testing Requirements

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

Docker/PostgreSQL when available:

```bash
cd src
docker compose up -d db
docker compose run --rm api python manage.py migrate
```

**Hard rule:** no test may reach `api.openai.com` or `googleapis.com`. Every backend test injects `transport`; every frontend test stubs `fetch`. A test that needs `LLM_API_KEY` to pass is a broken test.

### Previous Story Intelligence

Review findings from US-005 that apply directly here:

- **Concurrent-write and late-response handling was the top source of review patches.** A single transient draft has no list state, so keep it that way — do not introduce a draft list or cache.
- **URL normalization must stay in `apiConfig.ts`.** US-005 shipped a patch because `apiClient.ts` bypassed it. Use `buildApiUrl` for the draft URL.
- **Frontend coverage of the UI-facing behavior was a review finding, not an optional extra.** Ship `queryDraftApi.test.ts` in the same pass, not afterwards.
- **US-005 skipped `README` / project-understanding updates and that was accepted** because no new setup step existed. This story **does** add env variables, so `src/api/README.md` and the env examples must be updated.

Git patterns from the last five commits (`bfc37c8` … `e51b7c6`): each story ships an implementation-context artifact in `_bmad-output/implementation-artifacts/`, and thesis prose commits stay separate from code commits. Branch name for this work: `feature/US-006`. Commit messages follow Conventional Commits; when the story completes, include the Taiga reference `TG-<ref> #done`.

### Project Context Reference

Follow `_bmad-output/project-context.md`:

- Backend Python 3.14 / Django 6.0.5 / DRF 3.17.1; frontend React 19.2.6 / Vite 8.0.12 / TypeScript 6.0.2. Do not upgrade or substitute.
- `src/api` and `src/ui` are **nested repos** — app files are committed from there, not from the main thesis repo. `src/docker-compose.yml` belongs to the main repo.
- New Python modules start with `from __future__ import annotations`; helpers get explicit return types; modules stay import-safe.
- Google-style docstrings on public functions; JSDoc on exported TS functions. Descriptions start lowercase unless the first word is a proper noun or identifier.
- `verbatimModuleSyntax` is on — use `import type` for type-only imports.
- Avoid `Any` / `any`; type the OpenAI payload at the boundary and narrow from there.
- No secrets in code. `LLM_API_KEY` has no safe default and must fail loudly (503), not silently.

### Story Completion Status

This story is ready for `bmad-dev-story`. Implement only draft generation, the draft endpoint, the read-only draft UI, env wiring, docs and tests. Parameter validation (US-007), the editable review screen (US-008), persistence of approved parameters (US-009) and any YouTube API call (US-015) are out of scope.

## Dev Agent Record

### Agent Model Used

Claude Opus 5

### Debug Log References

- Created story context from `docs/product_backlog.md`, `docs/sprint_planning.md`, `docs/database_schema.md`, `_bmad-output/project-context.md`, the US-005 story artifact, current `src/api` and `src/ui` code, and official OpenAI / YouTube Data API references checked 2026-08-05.
- Red checks: `core.tests.EnvironmentHelperTests` failed on missing `env_str`; `core.tests.DraftFromResponseTests` failed on missing `core.query_translation`; `core.tests.SavedQueryDraftApiTests` failed 6/9 before the endpoint existed; `npm test` failed on missing `draftQueryParameters`.
- Green checks: `venv/bin/python manage.py test` (45 tests), `venv/bin/python manage.py makemigrations --check --dry-run` ("No changes detected"), `npm test` (25 tests), `npm run lint`, `npm run build`, `docker compose config`, `docker compose run --rm api python manage.py migrate` against PostgreSQL 18 ("No migrations to apply").
- Verified the Compose env passthrough after rebuilding the `api` image: `LLM_MODEL` resolves to `gpt-5.6-luna` by default and to an override when one is exported; `LLM_API_KEY` stays unset. The first attempt read a stale image built before the settings change, which is why the rebuild was needed.
- `npm run lint` rejected the first draft-clearing implementation (`react-hooks/set-state-in-effect`). Replaced with a project-scoped `QueryDraftState`, which also removes the late-response race instead of only clearing on project change.

### Completion Notes List

- Story artifact created for US-006.
- Sprint status updated to `ready-for-dev`; epic 3 moved to `in-progress`.
- Added `core/query_translation.py`: two public functions (`translate_prompt`, `draft_from_response`) plus a stdlib `urllib.request` transport. No new dependency; the `openai` SDK was deliberately not added.
- OpenAI Responses API is called with Structured Outputs (`text.format.type = "json_schema"`, `strict: true`). `structured_query_params` is assembled in Python from the model's typed fields, so the model cannot emit YouTube parameter names.
- Model output is re-validated after the schema: `order` is checked against the allowed enum, `max_videos_to_discover` below 1 becomes `null`, and `confidence` is clamped to 0–1 before being rendered as a 4-decimal string.
- Added `POST /api/projects/<uuid:project_id>/queries/draft/` returning a transient draft; a test asserts `SavedQuery.objects.count() == 0` after a draft call.
- Moved `get_project()` from `SavedQueryListCreateView` into `ProjectOwnerMixin` so both project-scoped views share one owner-scoped lookup.
- Failure modes return 400 / 503 / 422 / 502; the upstream error message is generic so a provider response body can never echo the API key back to the client.
- Added `env_str` to settings alongside the existing `env_bool` / `env_list`, plus `LLM_API_KEY` (no default) and `LLM_MODEL` (default `gpt-5.6-luna`).
- Frontend adds `QueryParameterDraft`, `isQueryParameterDraft`, `draftQueryParameters` and a read-only draft panel. The draft is not written back into the saved-query form — editing is US-008.
- No test contacts `api.openai.com`: backend tests inject `transport`, frontend tests stub `fetch`. `OPENAI_DRAFT_RESPONSE` in `core/tests.py` is the captured payload US-035 will reuse.
- No model change and no migration; `makemigrations --check` stays clean.
- `docs/project-understanding/06-generate-draft-youtube-api-parameters.md` was rewritten after the code review to describe the reviewed implementation, per the project documentation rule.

Post-review (2026-08-05), after applying all 22 patches:

- Closed four paths that returned an unhandled `500` instead of the status AC 7 promises: `NaN`/non-finite confidence, a non-iterable `output` or `content`, `http.client.HTTPException` from a connection that dies mid-read, and a JSON request body that is not an object.
- `_post_json` is now exercised directly by `PostJsonTransportTests` with a stubbed `urlopen`. Previously every test replaced the transport, so the URL, bearer header, timeout and error mapping had zero coverage — which is what hid the `HTTPException` gap.
- `_confidence` raises instead of returning a fabricated `"0.0000"` when the model reports no usable confidence. Inventing provenance is worse than failing in a reproducibility tool.
- Model output re-validation: integral floats (`250.0`) are accepted as a discovery intent, fractional values are dropped, and `region_code` / `relevance_language` longer than their `SavedQuery` columns are dropped so a draft is always savable. Value-format validation stays with US-007 per the review decision.
- `default_language` only reaches the system prompt when it matches an ISO-639-shaped tag; it is unvalidated free text and was being concatenated into the instructions.
- Prompt capped at `MAX_PROMPT_CHARACTERS` (2000) at the endpoint and via `maxLength` on the textarea. The auth/throttle posture was deliberately left unchanged and moved to deferred work.
- Upstream failures are logged server-side with their HTTP status; the response body stays generic. Expected-failure tests use `assertLogs`, so this is asserted rather than printed as noise.
- Frontend: the draft request now uses an `AbortController` held in a ref plus a controller-identity check, so a superseded response can neither clobber a newer draft nor resolve after unmount. The draft is discarded when the prompt is edited or the form is saved, the panel prints the prompt it was drafted from, and the result is wrapped in `aria-live="polite"`.
- Fixed two tests that passed for the wrong reason: `"es"` already occurs inside "researcher" in `SYSTEM_PROMPT`, so both project-language assertions would have survived deleting the feature.
- `src/api/README.md` no longer claims a draft can be POSTed to the saved-query endpoint unchanged; `name` is required and three metadata fields are read-only.
- The default model id now lives only in `settings.py`; Compose passes `LLM_MODEL` through as an optional override, and `src/.env.example` documents it.
- Validation after the fixes: backend 63 tests (was 45), `makemigrations --check` clean, frontend 26 tests (was 25), `npm run lint`, `npm run build`, `docker compose config`, and the Compose passthrough re-verified for unset / empty / overridden `LLM_MODEL`.
- Not done (deliberately, out of story scope): no branch was created and nothing was committed; the thesis `% TODO: Add exact LLM model` in `content/09_1_1-stack_evaluation_and_selection.tex:51` and the empty `content/09_2_2-LLM_integration_component.tex` are still open, and are thesis prose rather than dev work.

### File List

- `_bmad-output/implementation-artifacts/3-1-generate-draft-youtube-api-parameters-from-natural-language.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/deferred-work.md`
- `src/.env.example`
- `docs/project-understanding/06-generate-draft-youtube-api-parameters.md`
- `docs/project-understanding/index.md`
- `src/docker-compose.yml`
- `src/api/.env.example`
- `src/api/README.md`
- `src/api/core/query_translation.py`
- `src/api/core/tests.py`
- `src/api/core/urls.py`
- `src/api/core/views.py`
- `src/api/opentube_insights_api/settings.py`
- `src/ui/src/App.css`
- `src/ui/src/App.tsx`
- `src/ui/src/apiClient.ts`
- `src/ui/tests/queryDraftApi.test.ts`

### Change Log

- 2026-08-05: Created US-006 story context artifact and set status to ready-for-dev.
- 2026-08-05: Implemented US-006 query translation service, draft endpoint, read-only draft UI, env wiring, docs and tests; set status to review.
- 2026-08-05: Code review (Blind Hunter, Edge Case Hunter, Acceptance Auditor). 3 decisions resolved, 22 patches applied, 4 items deferred, 2 dismissed; set status to done.
