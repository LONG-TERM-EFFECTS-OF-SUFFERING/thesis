---
title: 'Validate generated YouTube API parameters'
type: 'feature'
ticket: 2
created: '2026-10-02'
status: 'built'
baseline_revision: 'a26dc44e5434c973c0d3f8c1b7dad4ed1b04b9c5'
route: 'full'
route_source: 'auto'
review: 'thorough'
review_source: 'pinned'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/initiative-opentube-insights/archive-v6/3-2-validate-generated-youtube-api-parameters.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing checks the shape of a drafted `structured_query_params` object: unknown keys, non-RFC 3339 dates, inverted date ranges and malformed region/language codes all reach the researcher unflagged, and later (US-008 edits, US-009 saves) nothing will stop them reaching a collection run.

**Approach:** One pure, stdlib-only backend function reports findings for a parameter object without mutating it; the draft endpoint returns them as a `validation` array and the read-only draft panel lists them. US-008 and US-009 reuse the same function.

## Boundaries & Constraints

**Always:** Report, never mutate. Untrusted input typed as `object` and narrowed. Reject `bool` for `maxResults`. Import `SEARCH_ORDER_VALUES` and `YOUTUBE_MAX_RESULTS_PER_REQUEST` from `core.query_translation`, never restate them. Each finding is `{parameter, code, message}` with `code` from the closed set `not_allowed, missing, invalid_type, invalid_value, invalid_format, out_of_range, invalid_range`. Findings in deterministic order (allowlist order; `not_allowed` keys sorted, first). Cross-field date finding is reported on `publishedBefore` with the message "Published before must be after published after.", matching `SavedQuerySerializer.validate`.

**Never:** No new dependency, route, serializer, model, or migration. Findings never turn a 200 draft into an error. No edit inputs, no save blocking (US-008/US-009). No change to `query_translation.py` behaviour or the App.tsx abort/race logic. No YouTube or OpenAI network call in any test. Do not add `videoDuration`/`safeSearch`/etc. to the allowlist.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean draft | object `draft_from_response(OPENAI_DRAFT_RESPONSE)` builds | `[]`; endpoint 200 with `validation: []` | — |
| Non-dict | `None`, list, string | one finding, parameter `structured_query_params`, code `invalid_type` | never raises |
| Empty / partial | `{}` | one `missing` per absent required key (`part, type, q, maxResults`) | — |
| Unknown key | `{..., "videoDuration": "long"}` | `not_allowed` on that key | — |
| Wrong type | `maxResults: "50"` or `True`; `q: 5`; optional key `None` | `invalid_type` | — |
| Out of range | `maxResults: 51` or `-1` | `out_of_range` | — |
| Wrong value | `part: "id"`, `type: "channel"`, blank `q`, unknown `order` | `invalid_value` | — |
| Bad format | naive or date-only `publishedAfter`, `regionCode: "colombia"`, `relevanceLanguage: "spanish"` | `invalid_format` | — |
| Inverted range | `publishedAfter` later than `publishedBefore`, both valid | `invalid_range` on `publishedBefore` | only when both parse |
| Draft with findings | model returns `relevance_language: "spanish"` | 200, one finding in `validation` | — |

</frozen-after-approval>

## Code Map

Baselines: thesis `a26dc44e5434c973c0d3f8c1b7dad4ed1b04b9c5`, `src/api` `57d4bf5930af8185dfcc86947978d857ce566dab`, `src/ui` `d47ab9f8b1364294b6805c4e6e5618771026ab95`. App code is committed inside the nested repos on a `feature/US-007` branch cut from `develop`.

- `src/api/core/query_translation.py` -- source of `SEARCH_ORDER_VALUES`, `YOUTUBE_MAX_RESULTS_PER_REQUEST`; `draft_from_response` emits exactly the nine allowlisted keys. Read-only.
- `src/api/core/views.py` -- `SavedQueryDraftView.post` ends `return Response(draft)`; the only backend call site.
- `src/api/core/serializers.py` -- `SavedQuerySerializer.validate` holds the date-order message to mirror. Read-only.
- `src/api/core/tests.py` -- single test module; reuse `OPENAI_DRAFT_RESPONSE`, `draft_from_response`, and `SavedQueryDraftApiTests.post_draft(response_payload=...)` (patches `_post_json`).
- `src/api/README.md` -- draft section ("Turn a natural-language request…"); subrepo-relative paths.
- `src/ui/src/apiClient.ts` -- `QueryParameterDraft` type, `isQueryParameterDraft` guard, `isRecord` helper.
- `src/ui/src/App.tsx` -- `.draft-preview` block inside the existing `aria-live="polite"` div.
- `src/ui/src/App.css` -- `.draft-preview*` rules and the `@media (max-width: 860px)` block.
- `src/ui/tests/queryDraftApi.test.ts` -- `draft` fixture and guard tests.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/parameter_validation.py` -- new module: `ALLOWED_SEARCH_PARAMS`, `REQUIRED_SEARCH_PARAMS`, two regexes, one `_rfc3339(value) -> datetime | None` helper, and `validate_search_parameters(params: object) -> list[dict[str, str]]` as a flat sequence of checks -- reusable pure rule set for US-007/008/009.
- [x] `src/api/core/views.py` -- add `"validation": validate_search_parameters(draft["structured_query_params"])` to the 200 response; update the `post` docstring `Returns:` -- exposes findings without a new route.
- [x] `src/api/core/tests.py` -- add `ValidateSearchParametersTests` covering every I/O matrix row, asserting on `parameter`/`code` only; extend the happy-path endpoint test with `validation == []` and add the "draft with findings" endpoint test -- proves the rules and the wiring.
- [x] `src/ui/src/apiClient.ts` -- add exported `QueryParameterValidationFinding` type, `validation` field, and extend the guard to require an array of findings -- trust boundary.
- [x] `src/ui/tests/queryDraftApi.test.ts` -- fixture gains `validation: []`; cover findings pass through, missing and non-array `validation` rejected, malformed element rejected.
- [x] `src/ui/src/App.tsx` + `App.css` -- list findings (`parameter`: message) in `.draft-preview` when non-empty; read-only; single-column so no media-query change needed.
- [x] `src/api/README.md` -- add `validation` to the draft description: informational on a draft, enforced at save time by US-009.

**Acceptance Criteria:**
- Given any input, when `validate_search_parameters` runs, then the input object is unchanged (asserted with a deep copy).
- Given a validator rule is deleted, when the backend suite runs, then at least one test fails.
- Given the backend and frontend suites, when they run, then no request reaches `api.openai.com` or `googleapis.com`.

## Implementation Notes

- Findings are collected per check, then stably sorted by allowlist index (`not_allowed` = -1), so order is allowlist order across checks; a test asserts it.
- `QueryParameterValidationFinding.code` is typed `string`, not a union of the seven codes; US-008 can narrow it when it branches on codes.
- Each backend rule and the frontend array guard were deleted one at a time and the suite failed every time.

## Plan Change Log

## Review Triage Log

Pass 1 (thorough; blind-hunter, edge-case-hunter, verification-gap, intent-alignment). Counts: high 0, medium 1, low 8, false 7, maybe-false 0. Routes: 6 patch, 1 defer, rest rejected.

| # | Lens | Finding | Verdict | Route | Evidence |
|---|------|---------|---------|-------|----------|
| 1 | edge | `T24:00:00Z` passes `_rfc3339` | medium | patch | Reproduced: parses to next-day midnight, no finding; RFC 3339 hour is 00-23. Fix: regex hour `([01]\d\|2[0-3])` + test case. |
| 2 | edge (claim) | Intent "non-RFC 3339 dates flagged" not met for hour 24 | medium | patch (grouped with 1) | Same root cause as 1. |
| 3 | edge | >6 fractional digits accepted and truncated | false | reject | RFC 3339 allows any fraction length; truncation affects only sub-microsecond comparison. |
| 4 | edge | Regex `\d` matches non-ASCII digits | false | reject | Reproduced: `fromisoformat` rejects them, `_rfc3339` returns None, finding reported. |
| 5 | edge | `q` of zero-width chars passes | low | reject | Real but rare (model strips, researcher would see it); fix adds a Unicode-category guard. |
| 6 | edge + blind | `relevanceLanguage` accepts 3-letter codes, message says ISO 639-1 | low | patch | Reproduced `spa` clean. Pattern is per plan Design Notes and YouTube i18n tags include 3-letter codes (`fil`); fix the message, not the pattern. |
| 7 | edge + blind | Equal date bounds not flagged | low | reject | Deliberately identical to `SavedQuerySerializer.validate` (`>`); flagging `>=` here alone would create two rules for one constraint. |
| 8 | edge | Non-str key reported stringified | low | reject | JSON object keys are always strings; no caller can produce an int key. |
| 9 | blind | README says findings "are enforced" by unbuilt US-009 | low | patch | Saved-query API still accepts any dict; reword to future tense. |
| 10 | blind | Finding names (camelCase) differ from panel labels | false | reject | The `<pre>` directly below renders `structured_query_params` with the same camelCase keys. |
| 11 | blind | Findings list has no visible label | low | patch | Bare red `<ul>` with no heading; add a text label (accessibility basic). |
| 12 | blind | Producer/allowlist drift untested for `publishedBefore` | low | patch | Fixture has `published_before: None`, so that key never travels producer → validator. Add an all-fields draft test. |
| 13 | blind | Wrong-type coverage misses `part`, `type`, `publishedBefore`, `relevanceLanguage` | low | patch | Behaviour verified correct (single `invalid_type`); add the cases so a double-report regression fails. |
| 14 | verif-gap + intent (e) | Panel rendering of findings has no test | low | defer | Pre-verified; no React render harness in repo and plan forbids new dependency. |
| 15 | intent (a) | Most rules unreachable from draft endpoint | false | reject | By design: intent states US-008/US-009 reuse the function on edited/saved objects. |
| 16 | intent (b) | Endpoint test exercises one rule only | false | reject | View calls the same function regardless of rule; the wiring is proven by one test. |
| 17 | intent (c) | Saved-query API still accepts any dict | false | reject | Out of scope by intent: save-time enforcement is US-009's reuse. |
| 18 | intent (d) | Top-level snake_case fields not validated | false | reject | Intent scopes validation to `structured_query_params`; values identical today. |

## Design Notes

RFC 3339 check uses a regex for shape plus `datetime.fromisoformat` for calendar validity. `fromisoformat` alone accepts non-RFC 3339 forms (`2026-01-01`, `20260101T000000Z`, ISO week dates, hour-only times), which YouTube rejects:

```python
RFC3339_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")
```

Patterns: `regionCode` `^[A-Z]{2}$`; `relevanceLanguage` `^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$` (YouTube accepts `zh-Hans`). Mark the ceiling: `# ponytail: shape checks only. Add pycountry/langcodes if a real ISO 3166-1 / 639-1 registry lookup is ever needed.`

A present optional key must be a string; `None` is `invalid_type`, not "absent", because an edited object with `"regionCode": null` would otherwise reach YouTube.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test` -- expected: all pass
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: "No changes detected"
- `cd src/ui && npm test && npm run lint && npm run build` -- expected: all pass, `tsc -b` clean
- `git -C src/api diff --stat develop -- requirements.txt; git -C src/ui diff --stat develop -- package.json` -- expected: empty
