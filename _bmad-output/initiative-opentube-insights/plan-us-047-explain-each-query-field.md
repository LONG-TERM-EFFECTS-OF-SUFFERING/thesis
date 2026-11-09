---
title: 'US-047 Explain each query field'
type: 'feature'
ticket: ''
created: '2026-11-09'
status: 'done'
baseline_revision: 'ui=200ce9b21a38adbbcdacc2b4158748a5637e6046'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 1
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The saved-query form gives no explanation of its fields. A researcher cannot tell what "Max videos to discover", `order` or `closedCaption` do without reading the YouTube API documentation. The thesis review asked for a message on hover that says what each field means.

**Approach:** Every field of the saved-query form gets a one- or two-sentence hint. The hint appears when the field is hovered, focused or tapped, and screen readers announce it through `aria-describedby`. This is native HTML plus CSS: no tooltip library and no JavaScript state. The options of the `order` select and the advanced selects show readable, translated names, while the same API value is still sent.

**Decision (human, 2026-11-09, after review pass 1):** focus wins. While a field has focus, only its hint shows; hovering other fields shows no hint until focus leaves that field.

## Boundaries & Constraints

**Always:**
- All 22 user-entered fields get a hint: the 12 main fields (name, search term, prompt, both dates, the three limits, region, language, order, notes) plus the 10 `ADVANCED_SEARCH_PARAMS`. The draft-provenance fields are not user-entered and get none.
- A field with no hint must fail `npm run build`. A select value with no readable label must fail a test.
- Hints and option labels go through `t()` and have Spanish entries in `i18n.ts`.
- Each hint names the YouTube parameter it fills, for example "(q)", so the form matches the parameter table of the thesis (Activity A1.2).
- What is sent and saved is unchanged: `buildSavedQueryInput` output and the saved-query card values stay byte-identical.
- Hints state only facts listed in Design Notes.

**Never:**
- No new dependency and no `title` tooltips, since `title` never shows on touch screens or to keyboard users.
- No backend change, and no change to the project form or the existing `draft-hint` texts.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Hover | mouse over a field's label or input | its hint shows next to the field, other hints stay hidden | — |
| Keyboard or touch | the field receives focus, by Tab or by tapping it | its hint shows while the field has focus | — |
| Screen reader | focus on an input | the hint is read as the field's description | — |
| Advanced select | the user picks "With captions" | the form state and the saved params hold `closedCaption` | — |
| English | the language toggle is on English | hints and option names are in English | — |

</frozen-after-approval>

## Code Map

- `src/ui/src/savedQueryForm.ts`:
  - `ADVANCED_SEARCH_PARAMS` (`name`, `label`, `values` or `placeholder`) and `SEARCH_ORDER_VALUES`. Keep both shapes: the API mirror comments and `buildSavedQueryInput` depend on them.
  - `SavedQueryFormState`. The fields to hint are its keys minus `llmModelName`, `llmPromptVersion` and `translationConfidence`, which are also in `noDraftProvenance`.
  - Add `FIELD_HINTS: Record<HintedField, MessageKey>` here, with `import type { MessageKey } from './i18n'`. `i18n.ts` has no JSX, so node tests can import it.
  - Add `OPTION_LABELS: Record<string, Record<string, MessageKey>>`, keyed by `order` and by each advanced select's `name`.
- `src/ui/src/QueriesSection.tsx`:
  - The form fields are at ~lines 245–275 (name, search term, prompt), ~359–457 (dates, limits, region, language, order) and ~467–493 (the advanced `map`). Notes is at ~497.
  - The option text `{order}` (~452) and `{value}` (~482) become the readable labels.
  - The saved-query card (~568) shows raw advanced values. Show the readable label there too when one exists, and fall back to the raw value.
  - Give the hint element `id="query-hint-<field>"` and point the control's `aria-describedby` at it. One `hintId(field: HintedField)` helper produces the id for both, so a misspelled field fails `tsc -b`.
  - Escape dismisses a shown hint (WCAG 1.4.13). On the form, an Escape keydown sets a hidden-hints state, and the next `focus` event on a field clears it. CSS hides `.field-hint` while the form carries that state.
  - In the card lookup, check own properties: `Object.hasOwn(OPTION_LABELS[name] ?? {}, value)`. Django admin can save any value, so the comment must not claim otherwise.
- `src/ui/src/App.css`: `.draft-hint` (~440) is the color and size to reuse.
  - `.field-hint` is an absolutely positioned overlay **above** its field (`bottom: 100%`), never below, so it never covers the next control (*Draft parameters*, *Save query*, the next field). Make sure no parent's `overflow: hidden` clips a hint above the first fields.
  - It shows on `label:hover` and `label:focus-within`.
  - Focus wins: `.query-form:has(label:focus-within) label:not(:focus-within) > .field-hint { display: none; }`.
  - Keep `pointer-events: none`. Add a `ponytail:` comment: the hint is not hoverable in the WCAG 1.4.13 sense, and a toggletip is the upgrade.
- `src/ui/src/i18n.ts`: the `es` dictionary, keyed by the English text. `MessageKey` makes missing entries a `tsc -b` error. Add a "Query form hints" group.
- `src/ui/tests/savedQueryForm.test.ts`: add tests. `tests/i18n.test.ts` already checks every Spanish entry for placeholders and blanks.

## Tasks & Acceptance

**Execution:**
- [x] `src/ui/src/savedQueryForm.ts` -- `FIELD_HINTS` and `OPTION_LABELS`, with JSDoc -- the field names and texts live in one list.
- [x] `src/ui/src/i18n.ts` -- Spanish entries for every hint and option label -- the build enforces translation.
- [x] `src/ui/src/QueriesSection.tsx` -- a hint element plus `aria-describedby` on every field, readable option labels and card labels.
- [x] `src/ui/src/App.css` -- `.field-hint`, shown on hover and focus, with no layout shift.
- [x] `src/ui/tests/savedQueryForm.test.ts` -- every hinted field has a non-empty hint, and every value of `SEARCH_ORDER_VALUES` and of every advanced select has a label. Delete one entry and confirm the test fails.

**Acceptance Criteria:**
- Given the Queries section in Spanish, when a researcher hovers "Duración", then a Spanish hint explains short, medium and long, and the options read as readable names.
- Given `npm run build`, when a hinted field lacks a `FIELD_HINTS` entry, then `tsc -b` fails.

## Implementation Notes

- Implemented on `src/ui` `feature/US-047`. `npm test` passes 126 of 126; build and lint are clean.
- Matrix audit: the rows Advanced select and English are covered by node tests. Every select value has a label keyed by its API value, and the i18n tests check that English returns the key. The rows Hover, Keyboard or touch, and Screen reader are CSS and accessibility behavior, and the project has no DOM test environment (US-037 is pending). They stay as the plan's manual checks, because a DOM test runner would be a new dependency, which this plan forbids.
- Hints carry `aria-hidden="true"`. Each sits inside its `<label>`, so without it a shown hint would join the field's accessible name. `aria-describedby` still reads a hidden element it references directly.
- Loop 1 rework on `src/ui` `feature/US-047-review` (uncommitted): the hint sits above its field, focus wins through `:has()`, Escape (a `window` keydown listener, so it also works with focus outside the form) sets `data-hints-hidden` on the form until the next focus on an `input`, `select` or `textarea`, `hintId` feeds every id and `aria-describedby`, and the card lookup uses `Object.hasOwn`. No ancestor of the form sets `overflow`, so nothing clips the first hint; the sticky header can still paint over it when the form is scrolled under the header. `npm test` 126 of 126, build and lint clean. A throwaway Playwright run against the real component in Chromium confirmed hover, focus wins, Escape, placement clear of *Draft parameters* and *Save query*, accessible name and description, readable options in both languages, `closedCaption` in the POST body, and a raw `toString` on the card; it failed on the pre-rework code.

## Plan Change Log

- **Loop 1 (2026-11-09), from review pass 1.** Triggers: the bad_plan finding (a hint below its field covers the next control) and the intent_gap finding (focus and hover show two hints), which the human resolved as focus wins.
  - **Amended:** the Code Map now places the hint above its field, adds the focus-wins rule, Escape to dismiss, the `hintId` helper and the own-property card lookup.
  - **Known-bad state avoided:** a focused prompt or Notes field hiding *Draft parameters* or *Save query*, and two hints overlapping.
  - **No revert:** the code was already merged (`32d7a30`), so re-derivation happens on `feature/US-047-review` from `develop`.
  - **KEEP everything else in `32d7a30` as it is:**
    - `FIELD_HINTS` and every hint text, `OPTION_LABELS`, the `HintedField` type and all `i18n.ts` entries;
    - both new tests;
    - the `aria-describedby` wiring and `aria-hidden="true"` on hints;
    - readable option text with unchanged `value` attributes;
    - card labels with a fallback to the raw value.

## Review Triage Log

Pass 1 (quick), 6 findings: 1 medium, 3 low, 2 false.

The human merged `src/ui` PR #25 (`32d7a30` on `develop`) while this review was running. Any rework therefore lands on a new branch from `develop`; nothing is reverted.

- **medium, bad_plan.** The hint is placed below the field, so a focused field's hint covers the next control. The prompt's hint covers *Draft parameters*, and the Notes hint covers *Save query*. The Code Map asked only for "no layout shift" and never said where the hint goes. Under WCAG 1.4.13 the hint obscures content and cannot be dismissed without moving focus.
- **low, intent_gap.** With one field focused and another hovered, both hints show. The frozen Hover row says "other hints stay hidden" but does not say which hint wins when focus and hover disagree. Hover-wins and focus-wins are both possible readings, so this goes to the human.
- **low, patch (carry).** In the card, `OPTION_LABELS[name]?.[value]` has no own-property check. `SavedQueryAdmin` (`core/admin.py`) has no read-only fields, so an admin can save `videoCaption: "toString"`. `translate` then gets a function: Spanish shows nothing, and English hands React a function. The code comment claiming "the API saves only listed select values" is false. Fix: `Object.hasOwn` and a corrected comment.
- **low, patch (carry).** The 12 hand-written fields type their `aria-describedby="query-hint-…"` ids as string literals, apart from the id that `fieldHint` generates, so a typo builds and tests clean. Fix: one `hintId(field: HintedField)` helper used by both the attribute and `fieldHint`.
- **false.** The finding said the card's readable names break "card values stay byte-identical". The human approved "the saved-query cards show the same names" at the checkpoint, and "values" in that line means the stored values, which are unchanged. Resolving it would only mean editing this plan.
- **false.** The finding said hints state facts not listed in Design Notes: the `location` format, what `safeSearch` filters, and the caption, definition and license hints. Each matches YouTube's `search.list` documentation and the existing placeholder (`3.4516,-76.532`), so no wrong fact reaches the user.

Pass 2 (quick), 4 findings: 3 low patch, 1 low reject. No pass-1 row repeats. Every pass-1 patch and the loop-1 amendments are present.

- **low, patch.** Escape listens only on the `<form>`, so a hint opened by hover while focus is outside the form (on first load, or after clicking the sidebar or a card) cannot be dismissed. The comment claims WCAG 1.4.13 dismissal. Fix: listen for Escape on `window` in an effect.
- **low, patch.** The form's `onFocus` clears the hidden state on focus to any control (*Draft parameters*, the Advanced `<summary>`, *Save query*), but the Code Map says "the next focus on a field". Fix: clear it only when the focus target is an `input`, `select` or `textarea`.
- **low, patch.** `src/ui/README.md` "Interface language" says API values such as `relevance` stay as the server sends them. Order options and the card's advanced values are now translated names. Fix: correct that sentence and add one sentence on the field hints.
- **low, reject (noted).** A hint above its field still covers what sits above it, so a focused Published after hides *Draft parameters* and a focused Notes or Channel ID hides the Advanced `<summary>`; the reviewer measured both. That is the overlay the human approved: Escape dismisses it, clicks pass through, and the user is in another field at the time. The real fix is the toggletip that the `ponytail:` comment already names, which is more than a direct correction. The comment now names this case so the ceiling is recorded where the code is.

## Design Notes

Facts the hints may use. All of them are verified in the code or the YouTube documentation; do not add others.
- **Name:** unique per researcher within a project.
- **Search term:** `q`, required.
- **Prompt:** at most 2,000 characters, used only by *Draft parameters*.
- **Dates:** `publishedAfter` and `publishedBefore`, inclusive bounds, entered in local time and sent in UTC.
- **Max videos:** the run's total cap. The page size `maxResults` is the smaller of this value and 50; each extra `search.list` page costs 100 quota units; empty means one page of 50.
- **Comments and replies:** empty collects none; each page of up to 100 costs 1 unit.
- **Region:** `regionCode`, a two-letter country code; videos viewable in that country.
- **Language:** `relevanceLanguage`; prefers relevant results in that language, others can still appear.
- **Order:** empty means YouTube's default, relevance. `videoCount` only sorts channels.
- **Notes:** never sent to YouTube.
- **Advanced filters:**
  - `channelId`: `UC` plus 22 characters.
  - `eventType`: completed, live or upcoming broadcasts.
  - `location` and `locationRadius`: go together; the radius is at most 1000 km.
  - `safeSearch`: YouTube's default is moderate.
  - `videoDuration`: short is under 4 minutes, medium 4–20 minutes, long over 20.
  - `videoCategoryId`: a number, for example 25 for News & Politics.

Option-label examples: `closedCaption` → "With captions"; `creativeCommon` → "Creative Commons"; `viewCount` → "Most viewed"; `none` under `safeSearch` → "No filtering". The same value under different parameters can need different labels, which is why `OPTION_LABELS` is keyed by parameter.

## Verification

**Commands:**
- `cd src/ui && npm test` -- expected: all pass, including the new hint and label tests.
- `cd src/ui && npm run build && npm run lint` -- expected: clean.

**Manual checks:**
- In `npm run dev`:
  - Hover, Tab into and tap three fields: each shows its hint, and the grid does not jump.
  - Toggle to English: the hints change language.
  - Save a query with "With captions": the card shows the readable name, and the API request body (DevTools) holds `closedCaption`.
