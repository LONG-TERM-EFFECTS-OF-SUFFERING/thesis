---
baseline_commit: 9650fe3eb4551ca7c32fc592c86e7eda83aa9709
---

# Story 3.2: Validate Generated YouTube API Parameters

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a researcher,
I want generated YouTube API parameters to be validated,
so that invalid requests are caught before collection starts.

## Acceptance Criteria

1. A single pure backend function validates a `structured_query_params` object against an **allowlist of parameter names**. Any key outside the allowlist is reported, so an edited or hand-written parameter set cannot smuggle an unsupported YouTube parameter into a collection run.
2. The validator checks the basic `search.list` rules: `part == "snippet"`, `type == "video"`, non-empty `q`, `maxResults` an integer in `0..50`, `order` within the allowed enum, `publishedAfter` / `publishedBefore` RFC 3339 with an explicit offset, `regionCode` ISO 3166-1 alpha-2 shape, `relevanceLanguage` ISO 639-1 shape.
3. `publishedAfter` must not be later than `publishedBefore`. This is the one cross-field rule and must be reported against `publishedBefore`, matching the existing `SavedQuerySerializer.validate` message.
4. The validator **reports, never mutates**. It returns a list of findings and leaves the parameter set untouched; correcting values is the researcher's job in US-008.
5. Required parameters absent from the set (`part`, `type`, `q`, `maxResults`) are reported as missing, so an empty or partial object never validates clean.
6. Each finding carries a machine-readable `parameter` and `code` plus a human-readable `message`, so US-008 can attach a finding to the field it belongs to instead of parsing prose.
7. The draft response from `POST /api/projects/<uuid>/queries/draft/` gains a `validation` array carrying the findings for the draft it just produced. A clean draft returns `[]`. No new endpoint, and the draft is still not persisted.
8. The frontend read-only draft panel shows the findings when there are any, inside the existing `aria-live` region. The panel stays read-only — editing is US-008.
9. Controlled tests cover a fully valid parameter set and one invalid example per rule in AC 1-5, plus an endpoint test proving the `validation` array reaches the client, with **zero live OpenAI or YouTube network calls**.

## Tasks / Subtasks

- [ ] Task 1: Add the parameter-validation module (AC: 1, 2, 3, 4, 5, 6)
    - [ ] Create `src/api/core/parameter_validation.py` with `from __future__ import annotations`.
    - [ ] Import `SEARCH_ORDER_VALUES` and `YOUTUBE_MAX_RESULTS_PER_REQUEST` from `core.query_translation` — do **not** restate either list. The enum and the 50 ceiling already live there and must not drift.
    - [ ] Module constants: `ALLOWED_SEARCH_PARAMS` (the nine names `query_translation` emits), `REQUIRED_SEARCH_PARAMS` (`part`, `type`, `q`, `maxResults`), `REGION_CODE_PATTERN`, `RELEVANCE_LANGUAGE_PATTERN`.
    - [ ] One public function: `validate_search_parameters(params: object) -> list[dict[str, str]]`. A non-dict argument returns a single finding rather than raising — it is called on untrusted input.
    - [ ] Private helpers only for what is genuinely reused: an RFC 3339 parser returning `datetime | None`. Do **not** split one checker per parameter; a flat sequence of checks in one function is readable and is what the tests assert against.
    - [ ] Keep the module import-safe: no env reads, no database, no network.
- [ ] Task 2: Parse date bounds with the standard library (AC: 2, 3)
    - [ ] Use `datetime.datetime.fromisoformat`. It accepts the `Z` suffix on Python 3.11+, so no `dateutil` and no new dependency.
    - [ ] Reject a parsed value whose `tzinfo` is `None`: `fromisoformat` happily accepts `2026-01-01` and `2026-01-01T00:00:00`, neither of which is RFC 3339, and YouTube rejects both.
    - [ ] Compare the two bounds only when both parsed successfully. A malformed `publishedAfter` must produce one format finding, not a format finding plus a bogus ordering finding.
    - [ ] Mark the ceiling in code:
          `# ponytail: shape checks only (regex + fromisoformat). Add pycountry/langcodes if a real ISO 3166-1 / 639-1 registry lookup is ever needed.`
- [ ] Task 3: Expose validation on the draft response (AC: 7)
    - [ ] In `SavedQueryDraftView.post` in `src/api/core/views.py`, call `validate_search_parameters(draft["structured_query_params"])` after `translate_prompt` returns and add the result under `"validation"`.
    - [ ] Do **not** add a route, a serializer or a second view. `urls.py` is unchanged in this story.
    - [ ] Do **not** fail the request when findings exist. A draft with findings is still a 200; it is information for the researcher, not an error. Only US-009 blocks a save.
    - [ ] Update the `post` docstring's `Returns:` line to mention the validation findings.
- [ ] Task 4: Add backend tests (AC: 9)
    - [ ] Add a `ValidateSearchParametersTests` class to `src/api/core/tests.py` (single test module, Django `TestCase` style — append, do not create a second file).
    - [ ] Clean case: the exact `structured_query_params` object `draft_from_response` builds for the US-006 fixture validates to `[]`. This test is what keeps the two modules honest with each other.
    - [ ] One failing case per rule: unknown key, `part != "snippet"`, `type != "video"`, blank `q`, `maxResults` of `51`, `maxResults` of `"50"` (a string, not an int), `maxResults` of `True` (`isinstance(True, int)` is `True` — this is the trap), bad `order`, naive `publishedAfter`, non-RFC-3339 `publishedBefore`, `publishedAfter > publishedBefore`, `regionCode` of `"colombia"`, `relevanceLanguage` of `"spanish"`, each required key missing, `{}`, and a non-dict argument.
    - [ ] Assert on `parameter` and `code`, not on message prose, so wording changes do not break the suite.
    - [ ] Extend the existing draft endpoint happy-path test to assert `response.data["validation"] == []`, and add one test where the faked model output yields a reported draft (for example a `relevanceLanguage` the model returned as `"spanish"`) and the endpoint still returns 200 with one finding.
    - [ ] Reuse the existing `OPENAI_DRAFT_RESPONSE` fixture and the injected `transport`. No test may reach `api.openai.com`.
- [ ] Task 5: Extend the frontend API boundary (AC: 8, 9)
    - [ ] In `src/ui/src/apiClient.ts`, add a `QueryParameterValidationFinding` type (`parameter`, `code`, `message`) and a `validation: QueryParameterValidationFinding[]` field to `QueryParameterDraft`.
    - [ ] Extend `isQueryParameterDraft` to check the array and its elements. The guard is the trust boundary — a missing or malformed `validation` array must fail the guard, not reach React as `undefined`.
    - [ ] `draftQueryParameters` itself needs no change; it already returns through the guard.
    - [ ] Extend `src/ui/tests/queryDraftApi.test.ts` — do **not** add a new test file. Cover: findings pass through, empty array passes through, missing `validation` is rejected by the guard, a non-array `validation` is rejected.
- [ ] Task 6: Show findings in the read-only draft panel (AC: 8)
    - [ ] In `src/ui/src/App.tsx`, inside the existing `.draft-preview` block, render the findings as a list when `activeDraft.draft.validation.length > 0`. The block is already inside the `aria-live` region US-006 added, so no new live region.
    - [ ] Keep it read-only: no inputs, no auto-correction, no blocking of the save button. US-008 owns editing and US-009 owns save-time feedback.
    - [ ] Add the finding styles to `src/ui/src/App.css`. If the list uses a `dl`/multi-column layout, add it to the 860 px media query override — US-006 shipped a review patch for exactly that omission on `.draft-preview dl`.
- [ ] Task 7: Docs and validation (AC: 1-9)
    - [ ] Update `src/api/README.md`: the draft response example gains the `validation` array, and one line explains that findings are informational on a draft and enforced at save time by US-009. Keep subrepo-relative paths.
    - [ ] Add `docs/project-understanding/07-validate-generated-youtube-api-parameters.md` and link it from `docs/project-understanding/index.md` (reading order entry 9 plus a story-notes row) **after** code review fixes land.
    - [ ] Run the backend and frontend validation commands listed under Testing Requirements.

## Dev Notes

### Sprint and Dependency Context

US-007 is the second story in EPIC-003, "natural language query translation", and closes sprint 2 ("production wiring and parameter drafting"). Epic 3 is already `in-progress`; US-006 is `done`.

Epic 3 division of labour — **stay inside your lane**:

| Story  | Owns                                                                | Not this story                                        |
| ------ | ------------------------------------------------------------------- | ----------------------------------------------------- |
| US-006 | Draft generation from natural language (`done`)                      | Do not change the translation prompt or schema        |
| US-007 | Allowlist + YouTube-rule validation of parameters (**this story**)  | —                                                     |
| US-008 | Editable parameter review screen                                    | Do not make the draft editable, do not add inputs     |
| US-009 | Saving approved parameters with validation feedback                 | Do not persist anything, do not block any save path   |

The validator this story writes is the function US-008 and US-009 call. Write it as a pure function over a `structured_query_params` dict so both can reuse it without reshaping anything: US-008 against edited values, US-009 at save time.

### What US-006 Deliberately Left Here

The US-006 code review (2026-08-05) recorded an explicit decision that fixes this story's boundary. From that story's Review Findings:

> Model-output validation scope vs US-007 → **length guards only**. … No ISO format checks, no RFC 3339 parsing and no `published_after <= published_before` check — those stay with US-007.

So `query_translation.py` already does, and this story must **not** redo:

- `order` re-checked against `SEARCH_ORDER_VALUES` (`query_translation.py:177`).
- `max_videos_to_discover` coerced to a positive int, integral floats accepted (`_optional_count`).
- `maxResults` clamped to 50 (`YOUTUBE_MAX_RESULTS_PER_REQUEST`).
- `region_code` / `relevance_language` dropped when longer than their `SavedQuery` columns (`MAX_REGION_CODE_LENGTH = 10`, `MAX_RELEVANCE_LANGUAGE_LENGTH = 20`) — **length only**, the comment at `query_translation.py:29-32` says so.

What is therefore still missing, and is this story's actual content: nothing checks the **shape** of `regionCode` or `relevanceLanguage`, nothing parses the date bounds, nothing compares them, and nothing constrains the **set of keys** in `structured_query_params`.

That last point is the one worth understanding. Today the LLM cannot invent a parameter name, because `draft_from_response` assembles `structured_query_params` in Python from typed fields. But `SavedQuerySerializer.validate_structured_query_params` only checks `isinstance(value, dict)`, and US-008 lets a researcher edit the object before US-009 saves it. The allowlist is what stops an arbitrary key from reaching a collection run. Validating an object the current code cannot produce is not defensive noise — it is the point of the story.

### Current Code State

Backend (`src/api/core/`):

- `query_translation.py` (381 lines) — owns `SEARCH_ORDER_VALUES`, `YOUTUBE_MAX_RESULTS_PER_REQUEST = 50`, the length caps, `translate_prompt`, `draft_from_response`. **Import the constants from here.** Do not add validation to this module: its job is translation, and mixing the two makes the validator untestable without a model payload.
- `views.py` (267 lines) — `SavedQueryDraftView.post` is the only call site you touch. It already resolves the project through `ProjectOwnerMixin.get_project()`, caps the prompt at `MAX_PROMPT_CHARACTERS`, and maps `QueryTranslationRefused` / `QueryTranslationError` to 422 / 502.
- `serializers.py` (158 lines) — `SavedQuerySerializer.validate` already enforces `published_after <= published_before` on the **model fields**, with the message "Published before must be after published after." Your cross-field check covers the **camelCase API parameters** in `structured_query_params`, which that serializer never inspects. Two checks, two different objects; keep the message consistent so the researcher does not see two phrasings of one rule.
- `models.py` (105 lines) — **no model change, no migration in this story.**
- `urls.py` (31 lines) — unchanged.
- `tests.py` (1213 lines) — one module, Django `TestCase`. `OPENAI_DRAFT_RESPONSE` is the captured provider payload. Append your classes.

Frontend (`src/ui/src/`):

- `apiClient.ts` (472 lines) — `QueryParameterDraft` (line 73), `isQueryParameterDraft` (line 294), `draftQueryParameters` (line 453), plus `isRecord` / `isNullableString` / `readJson`. **Reuse the existing guards and `readJson`**; do not write new error flattening.
- `App.tsx` (743 lines) — `QueryDraftState` is a discriminated union carrying `projectId`; `draftController` is an `AbortController` ref; `discardQueryDraft` clears the draft on prompt edit and on save. The `.draft-preview` block already sits in an `aria-live="polite"` region. Extend in place; do not touch the abort/race logic, which was a US-006 review patch.
- `tests/` — plain `node --test` files. **No React component test framework is installed.** Test the API boundary, not the component.

### Allowlist

The nine names `draft_from_response` can emit, and nothing else:

| Parameter           | Required | Rule                                                        |
| ------------------- | :------: | ----------------------------------------------------------- |
| `part`              |   yes    | exactly `"snippet"`                                         |
| `type`              |   yes    | exactly `"video"`                                           |
| `q`                 |   yes    | non-empty string after stripping                            |
| `maxResults`        |   yes    | `int`, `0..50`, and **not** a `bool`                        |
| `publishedAfter`    |    no    | RFC 3339 with an explicit offset                            |
| `publishedBefore`   |    no    | RFC 3339 with an explicit offset, not earlier than `publishedAfter` |
| `regionCode`        |    no    | `^[A-Z]{2}$`                                                |
| `relevanceLanguage` |    no    | `^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$`                          |
| `order`             |    no    | within `SEARCH_ORDER_VALUES`                                |

`videoDuration`, `safeSearch`, `videoCaption` and `videoDefinition` are real `search.list` parameters that are valid only when `type=video`, and US-006 deliberately kept them out of the translation schema. They are **not** on the allowlist yet: a parameter the app cannot produce and the UI cannot set would be dead rules. US-008 adds them to both the screen and this allowlist in the same change.

`isinstance(True, int)` is `True` in Python, so `{"maxResults": True}` passes a naive integer check and `0 <= True <= 50` is also true. Reject `bool` explicitly — `_optional_count` in `query_translation.py:305` already does this, for the same reason.

### Finding Shape

```json
{
    "parameter": "relevanceLanguage",
    "code": "invalid_format",
    "message": "relevanceLanguage must be an ISO 639-1 language code, for example es."
}
```

Suggested `code` values — a small closed set, because US-008 branches on them: `not_allowed`, `missing`, `invalid_type`, `invalid_value`, `invalid_format`, `out_of_range`, `invalid_range`. Use `"structured_query_params"` as the `parameter` for the non-dict and whole-object cases.

Findings are returned in a deterministic order (allowlist order, with `not_allowed` keys sorted) so tests can assert on a list rather than a set.

### Draft Response Contract Change

Same route, same statuses, one added key:

```
POST /api/projects/<uuid:project_id>/queries/draft/
```

```json
{
    "natural_language_prompt": "...",
    "search_term": "movilidad Cali debate",
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
    "translation_confidence": "0.8200",
    "validation": []
}
```

The error table from US-006 is unchanged: 400 blank or over-long prompt, 503 missing `LLM_API_KEY`, 422 refusal, 502 upstream failure, 404 for another owner's project. **A draft with findings is a 200 with a populated `validation` array**, not a 422. Nothing about this story can turn a successful translation into an error response.

### YouTube `search.list` Parameter Rules

Carried over from the US-006 reference check (2026-08-05), which remains the source for this story:

- `maxResults`: integer 0-50, default 5. Per request, not per collection.
- `publishedAfter` / `publishedBefore`: RFC 3339, e.g. `1970-01-01T00:00:00Z`.
- `order`: `date`, `rating`, `relevance` (default), `title`, `videoCount`, `viewCount`.
- `part` must be `"snippet"` and `type` must be `"video"` for this workflow.
- `regionCode` is ISO 3166-1 alpha-2; `relevanceLanguage` is ISO 639-1, and YouTube also accepts `zh-Hans` / `zh-Hant`, which is why the language pattern allows an optional subtag.

**Do not call the YouTube API in this story.** Discovery is US-015. Validation here is offline, by shape and rule only — no live "does this region exist" lookup.

### Architecture and File Structure Requirements

Expected backend files:

- `src/api/core/parameter_validation.py` (new)
- `src/api/core/views.py`
- `src/api/core/tests.py`
- `src/api/README.md`

Expected frontend files:

- `src/ui/src/apiClient.ts`
- `src/ui/src/App.tsx`
- `src/ui/src/App.css`
- `src/ui/tests/queryDraftApi.test.ts`

Expected main-repo files:

- `docs/project-understanding/07-validate-generated-youtube-api-parameters.md` and `index.md` (after review)

**No model change, no migration, no new dependency, no new route.** `venv/bin/python manage.py makemigrations --check --dry-run` must stay clean. `requirements.txt` and `package.json` must be untouched — `re` and `datetime` cover every rule here.

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

**Hard rule:** no test may reach `api.openai.com` or `googleapis.com`. Backend tests inject `transport`; frontend tests stub `fetch`. The validator tests need no network at all — they are pure function calls, which is the main reason the validator is a separate module.

### Previous Story Intelligence

Review findings from US-006 that apply directly here:

- **The worst bug in US-006 was a code path with no real coverage.** Every test replaced the transport, so `_post_json` — URL, bearer header, timeout, error mapping — ran in no test, and that is what hid the `http.client.HTTPException` gap. Apply the lesson: unit-testing `validate_search_parameters` is not enough. At least one test must reach it **through the endpoint**, and one must feed it the object `draft_from_response` actually builds.
- **Do not fabricate data to avoid an error.** `_confidence` was patched to raise instead of returning a plausible `"0.0000"`. Here: never "fix" a value to make a finding disappear, and never return `[]` for input you could not inspect. A non-dict gets a finding.
- **Tests that pass for the wrong reason were a review patch.** Two US-006 tests asserted `"es"` appeared in the prompt, but `"es"` already occurs inside "researcher". Check that each invalid-example test fails when the corresponding rule is deleted.
- **Guards are the trust boundary on the frontend.** `isQueryParameterDraft` must reject a malformed `validation` array; do not let `undefined` reach the panel.
- **Mobile layout on `.draft-preview` was a review patch.** Any multi-column CSS you add needs the 860 px override.
- **Understanding docs ship after review, not with the implementation.** US-006 shipped them early and had to regenerate them.

Git patterns: each story ships an implementation-context artifact in `_bmad-output/implementation-artifacts/`; thesis prose commits stay separate from code commits; app code is committed from the nested `src/api` and `src/ui` repos, never from the main thesis repo. Branch for this work: `feature/US-007`. Conventional Commits; on completion include the Taiga reference `TG-<ref> #done`.

### Project Context Reference

Follow `_bmad-output/project-context.md`:

- Backend Python 3.14 / Django 6.0.5 / DRF 3.17.1; frontend React 19.2.6 / Vite 8.0.12 / TypeScript 6.0.2. Do not upgrade or substitute.
- `src/api` and `src/ui` are **nested repos**; `docs/`, `_bmad-output/` and `content/` belong to the main thesis repo.
- New Python modules start with `from __future__ import annotations`; helpers get explicit return types; modules stay import-safe.
- Google-style docstrings on public functions; JSDoc on exported TS functions. Descriptions start lowercase unless the first word is a proper noun or identifier.
- `verbatimModuleSyntax` is on — use `import type` for type-only imports.
- Avoid `Any` / `any`. The validator's input is untrusted, so `object` plus explicit `isinstance` narrowing is the right typing, not `Any`.
- Dependency order is existing code → platform features → installed dependencies → new library. `re` and `datetime.fromisoformat` are the existing-platform answer here; `pycountry` / `langcodes` are the documented upgrade path if registry-accurate validation is ever required.
- Keep views thin: the view adds one key, the module holds the rules.

### Story Completion Status

This story is ready for `bmad-dev-story`. Implement only the validation module, its exposure on the existing draft response, the read-only display of findings, tests and docs. Editing parameters (US-008), persisting approved parameters (US-009), any YouTube API call (US-015) and the deferred auth/throttle posture are out of scope.

## Dev Agent Record

### Agent Model Used

Claude Opus 5

### Debug Log References

- Created story context from `docs/product_backlog.md` (US-007 row), `docs/sprint_planning.md` (sprint 2), `_bmad-output/project-context.md`, the US-006 story artifact and its review decisions, `_bmad-output/implementation-artifacts/deferred-work.md`, and the current `src/api/core/` and `src/ui/src/` code at `9650fe3`.

### Completion Notes List

- Story artifact created for US-007.
- Sprint status set to `ready-for-dev`.

### File List

- `_bmad-output/implementation-artifacts/3-2-validate-generated-youtube-api-parameters.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-10-02: Created US-007 story context artifact and set status to ready-for-dev.
