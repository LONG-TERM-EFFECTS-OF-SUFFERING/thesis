---
title: 'US-045 Switch the interface language'
type: 'feature'
ticket: ''
created: '2026-11-08'
status: 'done'
baseline_revision: 'ui=b1c3ed75856ef6cb75c6249a6fc1b7e02c99d8a2'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The interface is English only. The thesis review asked for a Spanish/English language toggle, with Spanish as the default.

**Approach:** No i18n library. Add one typed Spanish dictionary keyed by the existing English text, a `translate` function, and a React context that holds the active language. A header button switches the language, and the login screen has the same button. The choice is stored in `localStorage` exactly like the theme (`theme.ts`), and it sets `<html lang>`. Every text the UI itself writes is translated. Text the server writes (DRF and validation messages, API values such as `relevance`, YouTube data) stays as the server sends it.

## Boundaries & Constraints

**Always:**
- Spanish is the default: no stored choice, an invalid stored value, or blocked storage all mean `es`. `index.html` says `lang="es"`.
- Keys are typed (`keyof typeof es`), so an English string without a Spanish entry fails `tsc -b`.
- Visible text, `placeholder`, `aria-label`, `title`, `alt` and button text are all translated. API enum values in selects (`order`, the advanced filter values, sentiment label codes) stay as they are, because they are the API's vocabulary. An unlisted language code in `languageChoices` stays the raw code.
- Each toggle button names the *other* language in that language ("English" while Spanish is active, "Español" while English is active) and carries a matching `lang` attribute.
- `verbatimModuleSyntax`: use `import type` for type-only imports. Exported functions get JSDoc with a lowercase description. No `any`.

**Never:**
- No new dependency (no i18next or react-intl), and no backend change (Django `LocaleMiddleware` and gettext are out of scope).
- Do not translate server-written messages, YouTube data or API parameter values.
- Do not remount the app on a switch: half-typed forms, drafts and the selected run must survive a language change.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First visit | no stored language | UI in Spanish, `<html lang="es">` | — |
| Toggle | click "English" | every UI text switches to English without a reload; forms keep their values; choice stored | storage blocked → switch still applies for this visit |
| Reload | stored `en` | UI in English | invalid stored value → Spanish |
| Interpolation | key with `{name}` placeholders | values substituted in both languages | — |
| Non-React message | `apiClient` error prefix, `errorMessage` fallback | translated with the language on `<html lang>`; without a `document` (node tests) English | — |

</frozen-after-approval>

## Code Map

- `src/ui/src/theme.ts` -- the pattern to mirror: `parseTheme`, `pickTheme(readSaved)`, `initialTheme`, `applyTheme(theme, save)`. It is called before the first render in `main.tsx`, and `tests/theme.test.ts` tests it.
- `src/ui/src/main.tsx` -- call `applyLanguage(initialLanguage(), false)` here, beside `applyTheme`.
- `src/ui/src/App.tsx` -- holds `language` state (initial: `initialLanguage()`) and wraps every return path in the context provider: the error screen, `LoginScreen` and the shell. It passes the switch handler to `AppHeader` and `LoginScreen`.
- Components with strings: `AppHeader.tsx`, `LoginScreen.tsx`, `ProjectsSection.tsx`, `QueriesSection.tsx` (most), `ResultsSection.tsx`, `RunDetail.tsx`, `RunsSection.tsx`, `Sidebar.tsx`. App's error screen has a "Retry" button.
- Label data in `.ts` modules, translated where it is rendered:
  - `navigation.ts` `SECTIONS[].label`
  - `savedQueryForm.ts` `ADVANCED_SEARCH_PARAMS[].label/placeholder` and `LANGUAGE_OPTIONS[].label`
  - `sentimentFormat.ts` / `resultsFilters.ts`, for any user-facing text they return; read them and translate each at its render site.
- `src/ui/src/apiClient.ts` -- about 34 `httpErrorMessage`/`shapeErrorMessage` strings, passed into `request()`. Translate the prefix inside `request()` (and in the other throw sites) with the `<html lang>` language. Node tests have no `document`, so they keep getting English, and the existing message assertions in `tests/*Api.test.ts` stay valid.
- `src/ui/src/latestRequest.ts` `errorMessage` -- the `'Unexpected error.'` fallback, translated the same way.
- `src/ui/src/collectionRunState.ts` `formatTimestamp` -- uses the browser locale, so it stays as it is.
- `src/ui/index.html` -- `lang="en"` becomes `lang="es"`.

## Tasks & Acceptance

**Execution:**
- [ ] `src/ui/src/i18n.ts` -- add:
  - `Language`, `parseLanguage`, `pickLanguage(readSaved)` (default `es`), `initialLanguage`, `applyLanguage(language, save)` (sets `document.documentElement.lang`, stores under `opentube-language`, and survives blocked storage)
  - the `es` dictionary and `MessageKey`
  - `translate(language, key, vars?)`, where English returns the key and `{name}` placeholders are replaced
  - `documentLanguage()`: the `<html lang>` language, or `en` when there is no `document`
  - `LanguageContext` and `useT()`

  Keep it free of JSX, so `node --test` can import it.
- [ ] `src/ui/src/LanguageToggle.tsx` -- one button used by `AppHeader` and `LoginScreen`, styled like the theme toggle (`className="theme-toggle"`).
- [ ] `src/ui/src/main.tsx`, `App.tsx`, `index.html` -- the initial apply, the state, the provider and the default `lang`.
- [ ] Every component listed in the Code Map -- add `const t = useT();` and wrap each UI string. Use `t('…{name}…', { name })` for interpolated text instead of concatenating translated fragments.
- [ ] `src/ui/src/apiClient.ts`, `latestRequest.ts` -- translate the fixed message prefixes with `translate(documentLanguage(), …)`.
- [ ] `src/ui/tests/i18n.test.ts` -- test `pickLanguage` (default `es`; invalid value → `es`; throwing storage → `es`), `translate` (English returns the key; Spanish returns the entry; vars are substituted), and that every Spanish value has exactly the same `{placeholders}` as its key and is not blank.

**Acceptance Criteria:**
- Given a first visit, when the app loads, then every UI text is Spanish, including the login screen.
- Given a half-filled query form, when the toggle is clicked, then the text changes language and the form keeps every value.
- Given `npm run build`, when a wrapped string has no Spanish entry, then `tsc -b` fails.

## Implementation Notes

- Implemented and committed locally as `src/ui` 28cf0a2 on `feature/US-045`. `npm test` passes 122/122, and `npm run build` and `npm run lint` are clean.
- The review ran in the same session after the pause (Review Triage Log). Its three patches are in `src/ui` 01adff2, and `npm test` now passes 124/124.
- Still to do after review:
  - the browser check (form values survive a switch; reload keeps the language)
  - the project-understanding page 43 and its `index.md` link
  - the US-045 section of `docs/thesis-review-app-changes.md`
- Implementer notes worth checking in review:
  - API values stay raw, so Spanish shows mixed text such as "Mostrando comentarios negative".
  - The example placeholders `movilidad Cali` and `CO` are not translated.
  - The button and the heading "Borrador de parámetros" share one key.
  - `request()` in `apiClient.ts` now takes `MessageKey`.
  - Three label helpers take a `t` argument.

## Design Notes

Why English text as the key: the source stays readable, a component diff is just `'Runs'` → `t('Runs')`, and English needs no second dictionary. The typed key gives the compile-time completeness check that a library's JSON files would not.

Glossary, kept consistent across the dictionary:

| English | Spanish |
| :-- | :-- |
| run / runs | ejecución / ejecuciones |
| query / saved query | consulta / consulta guardada |
| project | proyecto |
| results | resultados |
| draft | borrador |
| sentiment | sentimiento |
| Refresh / Apply / Clear | Actualizar / Aplicar / Limpiar |
| Not set | Sin definir |
| request log | registro de solicitudes |
| quota | cuota |

Keep "API", "YouTube", "LLM", "CSV", "JSON" and identifiers such as `YOUTUBE_API_KEY` as they are.

Ceiling: a message already stored in React state, such as a form error, stays in the language it was produced in until the next action produces a new one. That is acceptable for transient messages.

## Review Triage Log

Pass 1 (quick), 3 findings: 1 medium, 2 low, 0 false. All route to patch.

- **low, patch.** `es['Draft parameters']` is shared by the draft button and the panel heading. "Borrador de parámetros" is a noun, so the main action button does not name its action in the default language. Fix: give the heading its own English text and key.
- **medium, patch.** No test covers the matrix row "Non-React message". Removing `translate(documentLanguage(), …)` from `request()` or `errorMessage` keeps every test green. `documentLanguage` also reuses `pickLanguage`'s storage `catch`, so a stubbed `document` without `documentElement` (`tests/authApi.test.ts` `stubCookie`) throws and silently becomes `es`; the reviewer reproduced a Spanish `logIn` error under node. Fix: treat a missing `document` or `documentElement` as `en` without a catch-all, and add tests that `errorMessage` and one `request()` path translate when `<html lang>` is `es`.
- **low, patch.** `src/ui/README.md` does not document the language toggle (`opentube-language`, Spanish default, blocked storage) the way it documents the theme, and it quotes buttons only by their English names. Fix: add a paragraph next to the theme one.

## Verification

**Commands:**
- `cd src/ui && npm test` -- expected: all pass, including `tests/i18n.test.ts`. The existing English assertions in the API tests are unchanged.
- `cd src/ui && npm run build` -- expected: `tsc -b` and Vite succeed, which proves every wrapped key has a Spanish entry.
- `cd src/ui && npm run lint` -- expected: clean.
- `cd src/ui && grep -nE ">[^<>{}]*[A-Za-z]{3,}[^<>{}]*<" src/*.tsx` -- expected: no hits that are untranslated JSX text (only `{t(...)}` expressions or brand names such as "OpenTube Insights").

**Manual checks (if no CLI):**
- `npm run dev`: the first load is in Spanish. Fill half a query, toggle to English, and check that the form keeps its values and every section is English. Reload: it is still English. Clear `localStorage`, then reload: it is Spanish again.
