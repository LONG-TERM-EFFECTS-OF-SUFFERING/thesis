---
title: 'Add LLM query translation tests'
type: 'chore'
ticket: '5'
created: '2026-10-08'
status: 'built'
baseline_revision: '90aa923754496dbd616611624229fec940857dda'
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

**Problem:** US-035 asks for query-translation tests that cover natural-language translation, allowed parameters, invalid inputs and deterministic fixture examples. US-006, US-007 and US-009 already left 55 such tests. Two gaps remain:
- **No end-to-end run.** Every draft-endpoint test patches `core.query_translation._post_json`, so the chain from the view through `translate_prompt`, `_post_json` and `urllib.request.urlopen`, and back through `draft_from_response` and the validator, never runs together. This is the AGENTS.md "transport faked in every test" pitfall that US-034 fixed for collection.
- **One example only.** There is a single success fixture (`OPENAI_DRAFT_RESPONSE`) and a refusal, not a set of deterministic examples.

**Approach:** Add tests only:
- a small table of documented-shape example cases, each with a prompt, the model's JSON output and the **exact** expected draft and validation findings;
- end-to-end tests that POST to the draft endpoint with only `urllib.request.urlopen` stubbed;
- an end-to-end draft-then-save round trip.

## Boundaries & Constraints

**Always:**
- **Example table:** a module-level `TRANSLATION_EXAMPLES` in `src/api/core/tests.py`, beside `OPENAI_DRAFT_RESPONSE`. A comment says the Responses API payloads are shaped after the documentation and the existing fixture, not captured from a live call. At least five cases:
  1. a Spanish prompt with a date window and a video cap;
  2. an English prompt with a region and a relevance language;
  3. a prompt with no dates and no cap (nulls omitted from `structured_query_params`);
  4. `order` set to `viewCount`;
  5. a model output that yields a validation finding, e.g. `published_after` later than `published_before`, which must give the inverted-range finding while the draft is still returned (US-007's "findings inform, never error").

  Each case asserts the full `structured_query_params` dict and the full `validation` list with `assertEqual`, never substrings (AGENTS.md: assertions on substrings the prompt already contained have shipped before).
- **Determinism:** translating the same prompt and project twice through `translate_prompt` builds byte-identical request bodies (`json.dumps(..., sort_keys=True)`), and the same model output gives an equal draft.
- **End-to-end tests** run with `override_settings(LLM_API_KEY="test-key", LLM_MODEL=...)` and `patch("urllib.request.urlopen", ...)` only. They assert:
  - a POST to `https://api.openai.com/v1/responses` with `Authorization: Bearer test-key`;
  - `text.format` strict with `DRAFT_SCHEMA`;
  - the prompt in the user message and the project's language hint in the system message;
  - the 200 response body equal to the expected draft (including `llm_model_name`, `llm_prompt_version` and `validation`);
  - a refusal body giving 422, and an upstream `HTTPError` 500 giving 502 with the key absent from the response.
- **Round trip:** the draft response is POSTed to the saved-query endpoint unchanged, apart from `name`, and stored with `query_source` `llm_generated` and the same provenance and `structured_query_params`.
- Each new assertion is mutation-checked once (Implementation Notes).
- No test reaches `api.openai.com`. Validated on Compose PostgreSQL.

**Never:**
- No product code changes. If a test exposes a defect, stop and report it.
- No live API key or recorded secrets.
- No moving or splitting existing tests.
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Example table | each of the ≥5 cases through `draft_from_response` and `validate_search_parameters` | exact draft fields, exact `structured_query_params`, exact findings | No error expected |
| Deterministic request | same prompt and project language twice | identical serialized request bodies | No error expected |
| End-to-end success | POST draft endpoint, `urlopen` returns an example's payload | 200 with the exact expected draft; request URL, method, auth header and strict schema as above | No error expected |
| End-to-end refusal | `urlopen` returns `OPENAI_REFUSAL_RESPONSE` | 422 | refused |
| End-to-end upstream failure | `urlopen` raises `HTTPError` 500 | 502 with a generic detail; the key absent from the body | logged |
| Round trip | draft response then save | saved query with `llm_generated`, provenance and identical params | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/tests.py` -- `OPENAI_DRAFT_RESPONSE` and `OPENAI_REFUSAL_RESPONSE` (around line 1624) sit beside the new `TRANSLATION_EXAMPLES`.
  - `DraftFromResponseTests`, `TranslatePromptTests` and `SavedQueryDraftApiTests` show the setup and assertions to copy.
  - `PostJsonTransportTests` shows how to stub `urlopen` with `_FakeHttpResponse` and build an `HTTPError`.
  - Add `QueryTranslationExampleTests(SimpleTestCase)` for the table and determinism, and `QueryTranslationEndToEndTests(APITestCase)` for the endpoint and round trip.
- `src/api/core/query_translation.py` (`translate_prompt`, `draft_from_response`, `_post_json`, `DRAFT_SCHEMA`, `QUERY_TRANSLATION_PROMPT_VERSION`) and `src/api/core/views.py` (`SavedQueryDraftView`) -- read-only references.
- `src/api/core/parameter_validation.py` -- `validate_search_parameters`, for the expected findings.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/tests.py` -- `TRANSLATION_EXAMPLES` and `QueryTranslationExampleTests`.
- [x] `src/api/core/tests.py` -- `QueryTranslationEndToEndTests`, including the round trip.

**Acceptance Criteria:**
- Given the end-to-end success test, when `_post_json` stops sending the `Authorization` header or the strict schema, then the test fails. This proves the real path runs.
- Given the example table, when `draft_from_response` stops omitting null values or stops clamping `maxResults`, then a case fails.
- `git diff --stat 90aa923 -- core/ ':!core/tests.py'` is empty.

## Implementation Notes

- Tests only: 417 added lines in `src/api/core/tests.py`, nothing removed or moved. `TRANSLATION_EXAMPLES` is a list of `TranslationExample` NamedTuples (prompt, project `default_language`, Responses payload, exact draft, exact findings), built with a small `_openai_response` wrapper. The five cases follow the plan, and the "no dates, no cap" case also has no project language, so the end-to-end test checks both sides of the language hint: present, and absent.
- `QueryTranslationEndToEndTests` runs every example through the draft endpoint with only `urllib.request.urlopen` patched, then covers the refusal (422, exact detail), the upstream `HTTPError` 500 (502, exact generic body, both log records, and no `test-key` in the bytes even though the fake error echoes it) and the draft-then-save round trip (example 1, the draft JSON posted unchanged apart from `name`).
- Mutation check: a scratch script applied each mutation to product code, ran the new tests on Compose PostgreSQL, then restored the files with `git checkout`. All 24 mutations failed with assertion failures, not errors. To isolate the key-leak check, the exact-body assertion was disabled for that one mutation.
  - Mutations to `query_translation.py`:
    - request: `Authorization` header dropped, `strict` set to False, schema loosened, wrong URL, GET instead of POST, user message altered, model replaced;
    - language hint: always dropped, or always added;
    - drafting: nulls kept in `structured_query_params`, `maxResults` clamp removed, a random nonce in the request body, a random nonce in the draft;
    - upstream: the HTTP status no longer logged (corrected in review: originally not caught, because the test only checked that a warning existed; it now asserts `HTTP 500` and no key in the captured log, and this mutation fails it).
  - Mutation to `parameter_validation.py`: inverted-range check removed.
  - Mutations to `views.py`: findings dropped, refusal sent to the 502 branch, refusal detail replaced, `logger.exception` replaced with `logger.debug`, 502 changed to 503, upstream cause put in the 502 detail.
  - Mutations to `serializers.py`: saved as `manual`, saved params altered, provenance stripped.
- No product defect found. `ruff check core/tests.py` reports one E731 in `SavedQueryDraftApiTests.post_draft`. That error was already there at baseline, so it was left alone because the plan forbids touching existing tests.

- Orchestrator check: 281 OK on PostgreSQL; product diff empty. Thesis baseline `49c71978478aa9e5b28ade0e0c98ced665d70404`.

- Review patch (pass 1) applied by the orchestrator. Full suite 281 OK on PostgreSQL; product diff empty.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 1, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `test_upstream_http_error_returns_a_generic_bad_gateway` uses `assertLogs` without checking the content, so the "status no longer logged" mutation recorded as caught was not | low | patch | Reviewer reproduced it. Orchestrator added assertions that the captured `core.query_translation` output contains `HTTP 500` and not the key; re-ran the mutation and the test fails; corrected the Implementation Notes. |

## Verification

Ran on 2026-10-08: full suite on Compose PostgreSQL 281 tests OK; `makemigrations --check --dry-run` no changes; `git diff --stat 90aa923 -- core/ ':!core/tests.py'` empty.

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && git diff --stat 90aa923 -- core/ ':!core/tests.py'` -- expected: empty.
