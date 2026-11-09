# 41 - Pick a language from a selector

Story: US-043, Pick a language from a selector.

Status note: this page describes US-043 after its review of 2026-11-08, which found nothing to fix. The story came from the thesis review; see `docs/thesis-review-app-changes.md`.

## What this story changed

Two free-text inputs became native `<select>` menus:

| form | field | stored as |
| :--- | :---- | :-------- |
| Projects → New project | Default language | `default_language` on the project |
| Queries → saved-query form | Language | `relevance_language` and `relevanceLanguage` in `structured_query_params` |

Both offer **Not set**, **Spanish** (`es`) and **English** (`en`). Not set sends nothing, just like the old blank input did.

## Why

Researchers had to know and type ISO 639 codes. A typo like `sp` or `Spanish` was rejected only on save (for a query) or was accepted silently (for a project, where the field is free text and is only used as an LLM hint).

## Files

- `src/ui/src/savedQueryForm.ts`:
  - `LANGUAGE_OPTIONS` is the one list both menus use. To offer another language, add it here.
  - `languageChoices(current)` returns that list. If the form holds a code that is not in the list, it adds the code as an extra option.
- `src/ui/src/QueriesSection.tsx`: the Language menu, built with `languageChoices`.
- `src/ui/src/ProjectsSection.tsx`: the Default language menu, built with `LANGUAGE_OPTIONS` directly. The form only creates projects and always starts blank, so it can never hold an unlisted code.
- `src/ui/tests/savedQueryForm.test.ts`: the `languageChoices` test.

The API did not change. It still accepts any well-formed language tag (`core/parameter_validation.py`), so old projects and queries keep their values.

## The one subtle part

The natural-language draft (page 06) can return a language outside the list, such as `pt`. **Use these parameters** copies it into the form.

A React `<select>` whose value matches no `<option>` shows its first option ("Not set") while its state still holds `pt`. The form would then save a language the screen says is not set. `languageChoices` adds `pt` as its own option, so the screen and the saved value always agree.

## Commands

From `src/ui`:

```bash
npm test        # 112 tests, including "languageChoices keeps a drafted language that is not offered"
npm run build   # typecheck + bundle
```

## How to test manually

1. Open **Projects**. Default language is a menu with Not set, Spanish and English. Create a project with Spanish, and its card shows `· es`.
2. Open **Queries**. Language is the same menu. Save a query with English, and its card shows `en`.
3. Draft from a prompt like "videos in Portuguese about Cali" and click **Use these parameters**. If the draft says `pt`, the menu shows `pt` selected instead of Not set.
