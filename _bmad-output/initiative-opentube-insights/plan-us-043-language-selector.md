---
title: 'US-043 Pick a language from a selector'
type: 'feature'
ticket: ''
created: '2026-11-08'
status: 'done'
baseline_revision: '4a418ec78ad53262748ab311e8ae56cdf70886ec' # src/ui
route: 'oneshot'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The project's default language and the saved query's language are free-text inputs, so a researcher has to know and type an ISO 639 code. The thesis review asked for a selector that offers Spanish and English for now.

**Approach:** Replace both inputs with a native `<select>` fed from one shared list of `{ value, label }` options (`es` Spanish, `en` English) plus a blank "Not set" choice. When an LLM draft applies a language that is not in the list, the query form adds it as an extra option, so the form never shows "Not set" while saving a different code. The API stays unchanged: it still accepts any valid language tag.

</frozen-after-approval>

## Implementation Notes

Oneshot: about 40 lines across three UI files and one test. There is no backend change, because `default_language` stays free text on the model and `relevanceLanguage` keeps its shape check in `core/parameter_validation.py`.

- `src/ui/src/savedQueryForm.ts`: add `LANGUAGE_OPTIONS` beside `SEARCH_ORDER_VALUES`, plus `languageChoices(current)`, which returns the list and appends `current` when it is non-blank and missing from the list.
- `src/ui/src/QueriesSection.tsx` (`Language` field) and `src/ui/src/ProjectsSection.tsx` (`Default language` field): replace `<input>` with `<select>`, using `languageChoices` for both.
- `src/ui/tests/savedQueryForm.test.ts`: test that `languageChoices` keeps a drafted code that is outside the list and does not add blank or listed values.
- Out of scope: translating option labels. US-045 owns that.
- As built, `ProjectsSection` maps `LANGUAGE_OPTIONS` directly instead of calling `languageChoices`: the project form only creates projects and always starts blank, so it can never hold an unlisted code.
- Mutation check: removing the `choices.push` in `languageChoices` fails the new test (111/112), and restoring it passes again (112/112). `npm run build` and `npm run lint` are clean.

## Review Triage Log

- Pass 1 (quick): 0 findings. The reviewer confirmed the AC, the blank-means-no-filter path and the unlisted-draft path, and reran the mutation check (the test fails without `choices.push`). Its one follow-up note was outside the diff: `docs/project-understanding/04-save-youtube-search-query.md` still called language a text input, so that page and page 03 were updated, and page 41 was added.

## Verification

**Commands:**
- `cd src/ui && npm test` -- expected: all tests pass, including the new `languageChoices` cases.
- `cd src/ui && npm run build` -- expected: `tsc -b` and the Vite build succeed.
- `cd src/ui && npm run lint` -- expected: no errors.

**Manual checks (if no CLI):**
- Projects form: "Default language" is a select with Not set / Spanish / English. Queries form: the same select, and applying a draft with `relevance_language: "pt"` shows `pt` as the selected option.
