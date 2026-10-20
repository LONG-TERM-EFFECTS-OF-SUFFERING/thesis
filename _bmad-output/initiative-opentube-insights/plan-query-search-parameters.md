---
title: 'Let researchers set more YouTube search filters on a saved query'
type: 'feature'
ticket: ''
created: '2026-10-19'
status: 'built'
baseline_revision: 'api e0efb54a567b6e46481d19413c382c1baaccd8c7 (feature/US-041 from develop); ui 428d1cfd42eb997e02a58835aa9d516f6b15a1bb (feature/US-041 from develop); thesis 159ea879e56e251eba42651202dbc6cf926cefb3 (main)'
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

**Problem:** A saved query can only set the nine `search.list` parameters that the natural-language draft fills: `q`, the date bounds, region, language, order and `maxResults`. The thesis advisor wants more detailed queries. YouTube supports more filters, such as duration, captions, license, channel, category, location and live events, but the API validator rejects them as `not_allowed`.

**Approach:** Add a manual "Advanced search parameters" group to the Queries form whose values go into `structured_query_params`, and extend the API allowlist and validation rules to cover them. What the model drafts stays unchanged, and applying a draft leaves the advanced fields alone.

## Boundaries & Constraints

**Always:**
- New parameters live only in `structured_query_params`, and so in each run's `effective_params` snapshot. No model columns, no migration.
- Each new parameter is validated on save and on run start, using the existing `{parameter, code, message}` findings. An invalid value never reaches YouTube.
- A blank advanced field omits the parameter. With every advanced field blank, the saved params are exactly what they are today.
- "Use these parameters" never changes an advanced field. Editing an advanced field keeps the draft provenance, as editing the region does today.
- Values follow the `search.list` reference: enums verbatim, `location` and `locationRadius` together, `locationRadius` at most 1000 km.
- Every query card shows the advanced parameters it holds.

**Decisions** (made by the human on 2026-10-19):
- **Filters:** the research set, 10 parameters: `channelId`, `eventType`, `location` + `locationRadius`, `safeSearch`, `videoCaption`, `videoCategoryId`, `videoDefinition`, `videoDuration` and `videoLicense`. Not included: `channelType`, `videoDimension`, `videoEmbeddable`, `videoPaidProductPlacement`, `videoSyndicated` and `videoType`.
- **Tracking:** this is backlog story US-041 under EPIC-002. Branch `feature/US-041` in api and ui. A project-understanding page is added after review. The user creates the Taiga card.

**Never:**
- Changes to `DRAFT_SCHEMA`, the translation prompt or what the model fills.
- OAuth-only parameters (`forMine`, `forContentOwner`, `forDeveloper`, `onBehalfOfContentOwner`), the removed `relatedToVideoId`, or `topicId` (deprecated after Feb 2017).
- Collection code changes, a `videoCategories.list` lookup, new dependencies, or tests that reach `googleapis.com`.
- Commits or pushes without the user asking.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Enum filter | `videoDuration: long` | saved; a run's `search.list` request carries it | No error expected |
| Bad enum | `videoDuration: forever` | 400 | `invalid_value` finding listing the allowed values |
| Half a location | `location` without `locationRadius`, or the reverse | 400 | `missing` finding naming the absent one |
| Location bounds | `location: "95,0"` or `locationRadius: "1500km"` | 400 | `out_of_range` finding |
| Bad formats | `channelId: "abc"`, `videoCategoryId: "news"`, `location: "north"` | 400 | `invalid_format` findings |
| Non-string | `videoDuration: 5` | 400 | `invalid_type` finding |
| Draft applied | advanced fields set, then "Use these parameters" | advanced fields unchanged | No error expected |
| All blank | no advanced field set | params identical to today's | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/parameter_validation.py`:
  - `ALLOWED_SEARCH_PARAMS` holds the nine names. Its comment ties it to `draft_from_response`.
  - In `validate_search_parameters`, the string-type loop covers every allowed key except `maxResults`.
  - Findings sort by allowlist index, so new names are appended after the nine.
  - Pattern constants follow `REGION_CODE_PATTERN` / `RELEVANCE_LANGUAGE_PATTERN`.
- Callers that need no change: `SavedQuerySerializer.validate_structured_query_params` (`serializers.py`) and `CollectionRunStartView` (`views.py`), both through `validate_search_parameters`. `draft_from_response` (`query_translation.py`) also validates drafts with it, and drafts never carry the new keys.
- `src/api/core/collection.py` `_search_params` -- already passes every string or int `search_list` key to `search.list`. Unchanged.
- `src/api/core/tests/test_parameter_validation.py` (`ValidateSearchParametersTests`) and `tests/test_views.py` (save and run-start API) -- where the new cases go.
- `src/api/README.md` -- the `validation` paragraph near line 179.
- `src/ui/src/savedQueryForm.ts`:
  - `SavedQueryFormState` and `emptySavedQueryForm`.
  - `SEARCH_ORDER_VALUES` shows how a UI copy of an API enum is commented.
  - `buildSavedQueryInput` filters undefined entries out of `optionalParams`.
  - `applyDraftToForm` spreads `...form`, so new fields survive a draft apply.
- `src/ui/tests/savedQueryForm.test.ts` -- form builder tests.
- `src/ui/src/QueriesSection.tsx` -- the form's `field-grid` (ends with Order), the Notes field, and each query card's `dl`.
- `src/ui/src/App.css` -- form, `field-grid` and `query-card` styles.
- `docs/project-understanding/07-validate-generated-youtube-api-parameters.md` -- says "the nine allowed names" in three places.
- `search.list` values, checked against the reference on 2026-10-19:
  - `channelId`: a string.
  - `eventType`: `completed`, `live`, `upcoming`.
  - `location`: `lat,long`.
  - `locationRadius`: a number plus `m`, `km`, `ft` or `mi`, at most 1000 km.
  - `safeSearch`: `moderate`, `none`, `strict`.
  - `videoCaption`: `any`, `closedCaption`, `none`.
  - `videoCategoryId`: a string id.
  - `videoDefinition`: `any`, `high`, `standard`.
  - `videoDuration`: `any`, `long`, `medium`, `short`.
  - `videoLicense`: `any`, `creativeCommon`, `youtube`.
  - The `video*`, `eventType` and `location*` filters need `type=video`, which is always sent.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/parameter_validation.py` -- append the 10 decided names to the allowlist. Add one enum table, plus format and range checks: `channelId` `^UC[0-9A-Za-z_-]{22}$`, `videoCategoryId` digits, `location` latitude -90..90 and longitude -180..180, `locationRadius` unit and ≤ 1000 km, and the pairing rule. Update the allowlist comment -- one validator for save, run start and drafts.
- [x] `src/api/core/tests/` -- every matrix row at the validator, plus one save and one run-start API case showing an advanced filter in `effective_params.search_list`.
- [x] `src/ui/src/savedQueryForm.ts`, `tests/savedQueryForm.test.ts` -- an advanced-parameter table (name, label, allowed values or free text) mirroring the API, form state, and the build step. Tests cover the matrix's UI rows.
- [x] `src/ui/src/QueriesSection.tsx`, `App.css` -- a collapsed native `<details>` "Advanced search parameters" under the field grid, rendered from the table (selects for enums with "Not set" first, text inputs otherwise). Cards list the advanced parameters that are set.
- [x] `src/api/README.md`, `docs/project-understanding/07-…md` -- describe the advanced parameters and stop calling the allowlist "nine".
- [x] `docs/product_backlog.md` -- add a US-041 row after US-040 with every column filled: EPIC-002, `should`, subject "Set advanced YouTube search filters", a user story, points, and "done when". Add US-041 to EPIC-002's story list.
- [x] Branches -- rename `feature/query-search-parameters` to `feature/US-041` in `src/api` and `src/ui`.
- [x] After review, by the orchestrator, not the implementer -- `docs/project-understanding/41-set-advanced-youtube-search-filters.md`, linked from that folder's `index.md`.

**Acceptance Criteria:**
- Given an advanced filter set in the form, when the query is saved and a run starts, then the run's `effective_params.search_list` holds it and the card shows it.
- Given `npm test`, `npm run lint`, `npm run build` and `venv/bin/python manage.py test`, when run, then all pass and `makemigrations --check --dry-run` reports no changes.

## Implementation Notes

- `order` moved into the new `SEARCH_ENUM_VALUES` table (built from `SEARCH_ORDER_VALUES`), so one loop checks every enum; its finding text is unchanged.
- Patterns use `[0-9]`, not `\d`, which matches non-ASCII digits. `location` takes no spaces; `locationRadius` must be `<number><unit>` with no space and a lowercase unit.
- Existing validator tests used `videoDuration` and `safeSearch` as unknown keys; they now use `videoType` and `channelType`, which stay out of scope. The "every allowed key" draft test now pins the nine draft names.
- Added one collection test showing the filters reach the `search.list` request (matrix row 1); collection code is unchanged.
- UI form state holds the advanced fields flat, keyed by their `search.list` name, so `updateSavedQueryForm` and the draft-provenance rule need no change. `src/ui/README.md` gained one sentence on the advanced group.

- Orchestrator: the understanding page is `39-set-advanced-youtube-search-filters.md`, not `41-…`, because pages are numbered in shipping order (the last was 38) rather than by story id. It is linked from `index.md` in the list and in the story table. A headless Chromium check on a scratch database saved Duration = long, Captions = closedCaption and a location pair. The card showed them, the run's `effective_params.search_list` held all four, and a half location pair was refused with the `locationRadius` message.

## Plan Change Log

- 2026-10-19: the user decided US-041 gets no Taiga card. It stays a backlog story only, so its commits carry no `TG-<ref>`.

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 1, false 0, maybe-false 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Page 07's "rules, in the order they are checked" table ends at `order` and omits every US-041 check, though its first row now covers all allowed names | low | patch | Confirmed: rows 87–98 of the page stop at `order`. Append the enum, `channelId`, `videoCategoryId`, location pairing, location and radius rows in check order. |

## Design Notes

- **JSON only:** these filters describe the YouTube request, not the study, so they belong in `structured_query_params`. The model columns mirror only what the draft and the run limits need. The run snapshot already makes them reproducible.
- **One table per side:** the API keeps a name → allowed-values map; free-text names get explicit checks. The UI mirrors it in one table that drives both rendering and `buildSavedQueryInput`, the same mirroring `SEARCH_ORDER_VALUES` uses.
- **Collapsed by default:** the form stays as it is for the drafted fields. `<details>` is native, keyboard accessible and needs no state.
- **Category id:** a free-text numeric id with a hint, e.g. 25 = News & Politics. Listing categories would cost a `videoCategories.list` call per region.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test 2>&1 | grep -E '^(Ran|OK|FAILED)'` -- expected: `OK`.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.
- `cd src/ui && npm test && npm run lint && npm run build` -- expected: `ℹ fail 0`, no lint output, `✓ built`.

**Manual checks:**
- `npm run dev` with the API up: set Duration = long and a location pair, save, start a run, and check the card and the run's request log parameters.
