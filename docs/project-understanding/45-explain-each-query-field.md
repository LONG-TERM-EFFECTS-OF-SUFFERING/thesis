# 45 - Explain each query field

Story: US-047, Explain each query field.

Status note: this page describes US-047 after its two reviews of 2026-11-09 and the fixes that followed (`src/ui` PR #25 and the follow-up PR #26). The story came from the thesis review; see `docs/thesis-review-code-changes.md`.

## What this story added

Every field of the saved-query form now explains itself. That is 22 fields: the 12 main ones and the 10 advanced filters. Hover a field, Tab into it or tap it, and a short hint appears **above** it. The hint says what the field does and names the YouTube parameter it fills, for example "(q)" or "(videoDuration)". Screen readers read the hint as the field's description.

The `order` select and the advanced selects now show readable names, such as "With captions" instead of `closedCaption` and "Most viewed" instead of `viewCount`. What is sent and saved is still the API's own value. Saved-query cards show the same readable names.

Two rules decide what you see:

- **Focus wins.** While a field has focus, only its hint shows. Hovering other fields shows nothing until you leave that field. This is the author's decision, taken after review.
- **Escape hides the hints.** They stay hidden until a field (not a button) gets focus again.

## Files

- `src/ui/src/savedQueryForm.ts`:
  - `HintedField` lists the form fields a person fills in. It leaves out the three draft-provenance fields, which code sets.
  - `FIELD_HINTS` holds one hint per field. Its type is `Record<HintedField, MessageKey>`, so a field without a hint fails `npm run build`.
  - `OPTION_LABELS` holds readable names keyed by parameter and then by value. The same value needs different names under different parameters: `none` is "No filtering" under `safeSearch` but "Without captions" under `videoCaption`.
- `src/ui/src/i18n.ts`: the Spanish entry for every hint and option name.
- `src/ui/src/QueriesSection.tsx`:
  - `hintId(field)` is the single source of a hint's `id` and of its field's `aria-describedby`.
  - `fieldHint(field)` renders the hint.
  - A `window` listener handles Escape, and the form's `onFocus` brings hints back when a field is focused.
- `src/ui/src/App.css`: `.field-hint` is an overlay above its field, shown by CSS on `label:hover` and `label:focus-within`. A `:has()` rule makes focus win, and `[data-hints-hidden]` hides every hint after Escape.

## Key concept: a tooltip with no JavaScript library

The hint lives inside the field's `<label>`, hidden by default. CSS shows it when the label is hovered (`:hover`) or anything inside it has focus (`:focus-within`). Tapping a field on a phone focuses it, so touch works too. A `title` attribute was rejected because it never shows on touch screens or to keyboard users.

Each hint has `aria-hidden="true"`. Because it sits inside the label, it would otherwise become part of the field's *name* once shown, and screen readers would read it twice. The field's `aria-describedby` points at the hint, so screen readers still read it as the *description*.

## Limits

- A shown hint covers whatever sits above its field. For example, a focused date field hides *Draft parameters*. Clicks pass through the hint (`pointer-events: none`), and Escape hides it. The upgrade is a "?" button per field (a toggletip), noted in a `ponytail:` comment.
- The hint cannot itself be pointed at. Moving the mouse onto it hides it, which falls short of WCAG 1.4.13's "hoverable" rule. The same upgrade fixes this.
- No automated test checks hover, focus or screen readers, because the project has no browser test setup (US-037). Those checks are manual.

## Commands

From `src/ui`:

```bash
npm test        # 126 tests, including "every user-entered form field has a translated hint"
npm run build   # fails if a field has no hint or a hint has no Spanish entry
```

## How to test manually

1. `npm run dev`, then open Queries. Hover "Duración": a Spanish hint explains short, medium and long.
2. Tab into a field: its hint shows. Hover another field: nothing changes, because focus wins.
3. Press Escape: the hint disappears. Tab into the next field: hints are back.
4. Open the Order select: the options are readable names. Save a query with "Con subtítulos": in DevTools, the request body holds `closedCaption`.

## Common errors

- **`npm run build` fails with "Property 'X' is missing in type".** You added a field to `SavedQueryFormState` without a hint in `FIELD_HINTS`.
- **The test fails with "no label for videoX=Y".** You added a select value to `ADVANCED_SEARCH_PARAMS` or `SEARCH_ORDER_VALUES` without an `OPTION_LABELS` entry.
