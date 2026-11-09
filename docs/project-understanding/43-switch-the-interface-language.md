# 43 - Switch the interface language

Story: US-045, Switch the interface language.

Status note: this page describes US-045 after its review of 2026-11-08 and the fixes that followed. The story came from the thesis review; see `docs/thesis-review-app-changes.md`.

## What this story added

A button in the header, also on the login screen, switches every text the interface writes between **Spanish** (the default) and **English**. The button names the other language in that language: "English" while Spanish is active, "Español" while English is active.

The choice is saved in `localStorage` under `opentube-language` and sets `<html lang>`, the same way the theme is saved. If nothing is saved, the value is unknown, or storage is blocked, the interface is in Spanish.

Switching only re-renders. Half-typed forms, drafts and the selected run stay.

## What is not translated

- Messages the **server** writes (DRF errors, validation findings). Translating those would need Django `LocaleMiddleware` and gettext.
- **API values** such as `relevance`, `moderate` or `negative`, and **YouTube data**. They are the API's vocabulary, so Spanish shows mixed text such as "Mostrando comentarios negative".
- A message already on screen keeps its language until the next action replaces it.

## Files

- `src/ui/src/i18n.ts`:
  - `es`: the Spanish dictionary, keyed by the English text. `MessageKey` is `keyof typeof es`, so a wrapped string with no Spanish entry fails `npm run build`.
  - `translate(language, key, vars)`, with `{name}` placeholders.
  - The storage helpers, which mirror `theme.ts`.
  - `documentLanguage()`, for code outside React.
  - `LanguageContext` and `useT()`.
- `src/ui/src/LanguageToggle.tsx`: the button.
- `src/ui/src/App.tsx`: holds the language and provides it to every screen. `main.tsx` applies it before the first render, and `index.html` starts with `lang="es"`.
- `src/ui/src/apiClient.ts` and `latestRequest.ts`: translate their own error prefixes with the `<html lang>` language. Node tests have no `document`, so they get English.
- Every component calls `const t = useT();` and wraps its text, placeholders and aria-labels.

## Why English text as the key, and no library

The source stays readable: a diff is just `'Runs'` → `t('Runs')`. English needs no second dictionary, and the typed keys give a completeness check at build time that JSON files in an i18n library would not. One cost: one English string can only have one Spanish translation. That is why the draft panel heading became "Drafted parameters" while the button stays "Draft parameters" ("Generar parámetros").

## Commands

From `src/ui`:

```bash
npm test        # 124 tests, including tests/i18n.test.ts
npm run build   # fails if any wrapped string has no Spanish entry
```

## How to test manually

1. `npm run dev`, then open the app. Everything, including the login screen, is in Spanish.
2. Type half a query, then click **English**. The text switches and the form keeps its values.
3. Reload. It is still English. Clear `localStorage` and reload: it is Spanish again.

## Common errors

- **`npm run build` fails with "Argument of type '…' is not assignable to parameter of type MessageKey".** You wrapped a new string in `t()` without adding it to `es` in `i18n.ts`.
- **An error appears in the other language after a switch.** It was produced before the switch. The next action produces it in the new language.
