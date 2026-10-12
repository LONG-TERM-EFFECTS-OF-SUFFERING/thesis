---
title: 'Apply the Polarizometro visual style to the OpenTube UI'
type: 'refactor'
ticket: ''
created: '2026-10-12'
status: 'built'
baseline_revision: '3a0601ddbc8390bb84bdf1a8dec76b16c0270348'
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

**Problem:** The OpenTube UI (`src/ui`) has its own ad-hoc look: system font, slate/teal colors hardcoded across `App.css`. The user wants it to share the visual identity of the Polarizometro app (`src/polarizometro-ui`). Because `App.css` hardcodes light colors, dark mode also only changes the page background today; panels stay white.

**Approach:** Port Polarizometro's MUI theme values (palette, Public Sans, radii, shadows, component styling) into plain CSS custom properties in `index.css`, and make every color in `App.css` use them, for light and dark.

## Boundaries & Constraints

**Always:**
- **Tokens from the source theme:** values come from `polarizometro-ui/src/theme/colors.js`, `shadows.js` and `components/*.jsx`, under the same names where natural (`--primary`, `--grey-200`, …).
  - **Light:** background `#F4F4F4`, surfaces `#FFFFFF`, text `#002459` (logo navy), secondary text `#4B5563`, dividers `#E5E7EB`, primary `#002459` (hover `#003E9E`).
  - **Dark:** background `#121212`, surfaces `#232323`, text `#E0E0E0`, secondary text `#B0B0B0`, dividers `#444444`, primary `#42A5F5`.
  - **Status colors:** success, warning and error from its scales.
- **Shapes:**
  - cards and panels: radius 12px with shadow level 1 from `shadows.js`, light grey border only where a card sits on a card;
  - buttons: radius 10px, weight 500, no text transform, no shadow;
  - inputs: radius 8px, border `grey-200`, focus ring in primary;
  - pill-like elements: radius 16px.
- **Type:** Public Sans 400/500/600/700 via `@fontsource/public-sans` (OFL-1.1, the package Polarizometro uses), imported in `main.tsx`. No weight outside 400–700.
- **Contrast:** text meets WCAG AA (4.5:1). Polarizometro's own `accessibleText` variants are used for text on light surfaces (link `#0B62B8`, success `#0A6E52`, warning `#8A6100`, muted `#6B7280`), and brand colors only for fills, borders and bars. In dark mode the primary button uses dark navy text (`#001936`) on `#42A5F5`.
- Dark mode still follows `prefers-color-scheme`, and every `App.css` rule renders correctly in it.
- Every element keeps a visible keyboard focus indicator.

**Decisions** (made by the human on 2026-10-12):
- Tokens and component styling only, on the current single-page layout. CSS only; `App.tsx` markup unchanged.
- Font: `@fontsource/public-sans`, a new dependency.
- Keep dark mode, mapped to Polarizometro's dark palette.
- Branch `feature/ui-polarizometro-style` (no backlog id).

**Never:**
- No MUI, Emotion or any other dependency besides the font.
- No layout, markup, text or behavior changes in `.tsx` files, other than the font import.
- No copying of Polarizometro logos, names or other assets.
- Do not edit `src/polarizometro-ui`.
- No compiler or lint strictness changes.

</frozen-after-approval>

## Code Map

- `src/polarizometro-ui/src/theme/colors.js`: the palettes (`primary`, `secondary`, `grey`, `darkGrey`, `success`, `warning`, `error`, `lightPalette`, `darkPalette`, `accessibleText`). Read only.
- `src/polarizometro-ui/src/theme/shadows.js`: level 1 is `0px 2px 1px -1px α.03, 0px 1px 1px 0px α.04, 0px 1px 3px 0px α.08` of `grey[500]` in light and `#000` in dark.
- `src/polarizometro-ui/src/theme/components/`: `button.jsx` (radius 10, weight 500, contained hover `primary[600]`), `card.jsx` (radius 12, elevation 1), `input.jsx` (outlined radius 8, border `grey[200]`), `chip.jsx` (radius 16), `tableCell.jsx` (no borders, `grey[500]` text). Typography is in `theme/index.js` (Public Sans; h6 18/500, body 16/14).
- `src/ui/src/index.css`: the current `:root` variables (`--text`, `--muted`, `--bg`, `--surface`, `--border`, `--accent`, `--success*`, `--warning*`, `--danger*`), the `prefers-color-scheme: dark` block, base `h1`/`h2`/`code` rules (`font-weight: 750` must become ≤ 700). Replace the values; keep or rename variables freely, since only CSS uses them.
- `src/ui/src/App.css` (~490 lines): every hex literal moves to a variable. The classes:
  - `.top-bar`, `.panel`, `.query-card`, `.draft-preview`: cards;
  - `button`, `.link-button`, `input`/`select`/`textarea`: controls;
  - `.status-dot` and `.service-state--*`: status colors;
  - `.data-table` with `.row--selected` and `.row--failed`;
  - `.sentiment-chart-track span`: bar fill, brand blue: `#0057C2` light, `#42A5F5` dark;
  - `.draft-preview pre`: dark code block; keep it dark in both modes;
  - `.form-error`, `.draft-findings*`: error text.
- `src/ui/src/main.tsx`: add the four `@fontsource/public-sans/{400,500,600,700}.css` imports before `./index.css`.
- `src/ui/package.json` and `package-lock.json`: `npm install @fontsource/public-sans@^5`.
- `src/ui/README.md`: one line naming the font package and why (self-hosted, no third-party request).

## Tasks & Acceptance

**Execution:**
- [x] `src/ui/package.json`, `package-lock.json`, `src/ui/src/main.tsx` -- install `@fontsource/public-sans` and import weights 400–700 -- the source theme's font, served locally.
- [x] `src/ui/src/index.css` -- light and dark token sets from the source theme, the font stack `'Public Sans', system-ui, sans-serif`, heading weights ≤ 700 -- one source of truth.
- [x] `src/ui/src/App.css` -- replace every color literal with a token; apply the radii, shadow, button, input, table and focus styles -- the visible restyle, and dark mode fixed.
- [x] `src/ui/README.md` -- note the font dependency.

**Acceptance Criteria:**
- Given `App.css`, when searched with `grep -nE '#[0-9a-fA-F]{3,8}\b|rgba?\(' src/App.css`, then no match remains: colors live only in `index.css`.
- Given the app opened with the OS in dark mode, when the page renders, then panels, cards, inputs and tables use the dark surfaces and light text. No white panel remains.
- Given each text/background token pair used for text in either mode, when its contrast is computed, then it is at least 4.5:1. A small `node` check over the token pairs, listed in the Implementation Notes, shows this.
- Given keyboard navigation, when tabbing through buttons, inputs and links, then each focused control shows a visible outline.

## Implementation Notes

- Tokens (`src/ui/src/index.css`): `--bg`, `--surface`, `--surface-sunken`, `--text`, `--text-secondary`, `--muted`, `--divider`, `--input-border`, `--primary`, `--primary-hover`, `--on-primary`, `--link`, `--selected`, `--success`, `--warning`, `--error`, `--error-text`, `--error-bg`, `--chart-fill`, `--code-bg`, `--code-text`, `--shadow-1`. Dark overrides everything except the status fills and the code block, which stay the same in both modes.
- Deviations from the source theme, for contrast: dark `--muted` is `#B0B0B0` because `darkGrey[400]` `#888888` gives 4.43:1 on `#232323`; light `--error-text` is `error[700]` `#C0113C` because `accessibleText` has no error variant and `error.main` fails 4.5:1; dark `--error-text` is `error[300]` `#F7A6BA`. Dark `--selected` (`#283845`) and `--error-bg` (`#301E22`) are Polarizometro's alpha overlays flattened onto `#232323`, so they can be checked as plain hex. Dark hover is `secondaryDark[400]` `#2196F3`, from `getButtonStyles`.
- Kept deliberately: disabled buttons still use `opacity: 0.55` instead of Polarizometro's grey fill (its dark disabled fill is a bright `#E0E0E0`); table rows keep a `--divider` bottom border, where Polarizometro's `TableCell` has none, because the run and log tables are dense.
- Cards: `.top-bar` and `.panel` get radius 12 and `--shadow-1`; `.query-card` and `.draft-preview` sit on a panel, so they get a `--divider` border and no shadow. `.service-state` and the sentiment bar track are the 16px pills. `color-scheme: light dark` on `:root` makes native controls (select popups, date pickers, scrollbars) follow the mode. Placeholders use `--muted`.
- Inputs use `--input-border`, from Polarizometro's `OutlinedInput.notchedOutline` (`theme/components/input.jsx`): `grey[200]` `#E5E7EB` in light, `grey[700]` in dark, which is `darkGrey[700]` `#E0E0E0`. The input focus rule sets `outline: 2px solid transparent` instead of `outline: none`, so forced-colors mode, which drops `box-shadow`, still paints a focus outline.
- Contrast pairs checked, each in light and dark (all at least 4.5:1, lowest is dark `--link` on `--selected` at 4.55): text on bg, surface, surface-sunken, selected; text-secondary on surface, surface-sunken, selected; muted on surface, surface-sunken; link on surface, surface-sunken, selected; on-primary on primary, primary-hover; error-text on surface, surface-sunken, error-bg; code-text on code-bg. The check is a throwaway `node` script that parses both token blocks out of `index.css` and computes the WCAG relative-luminance ratio; it was not committed.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 2, low 0, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `input:focus` sets `outline: none` and draws the ring with `box-shadow`, which forced-colors mode drops, so inputs show no focus indicator there | medium | patch | Confirmed: before the diff the browser default outline applied. Now `outline: 2px solid transparent`, which forced-colors mode paints. Normal mode unchanged. |
| Dark input border uses `--divider` `#444` (1.61:1 on `#232323`), so fields barely show; the source theme uses `grey[700]` (`#E0E0E0`) in dark | medium | patch | Confirmed in `theme/components/input.jsx`. New `--input-border` token: `#e5e7eb` light, `#e0e0e0` dark. Light stays at the planned `grey-200` (about 1.2:1, below WCAG 1.4.11's 3:1; it is what the source does, reported to the human). |

Re-verified after patches: `npm test` 89 pass, build and lint clean, `App.css` color grep empty.

## Verification

Ran 2026-10-12: `npm test` 89/89 pass, `npm run build` passes and emits the Public Sans `.woff2`/`.woff` files, `npm run lint` clean, the `App.css` color grep prints nothing. Headless Chromium screenshots of `vite preview` (API down) in light and `--force-dark-mode` matched the manual-check description. Keyboard tabbing was not exercised in a real browser.

**Commands:**
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all pass (89 tests). The build bundles the `.woff2` files.
- `cd src/ui && grep -nE '#[0-9a-fA-F]{3,8}\b|rgba?\(' src/App.css` -- expected: no output.

**Manual checks:**
- `cd src && ./run-local.sh`, then open `http://localhost:5173/` in light and in dark OS mode. The text uses Public Sans, the cards are white and rounded on a light grey page, and the primary buttons are navy. In dark mode the surfaces are `#232323` with light-blue buttons. Compare side by side with a Polarizometro dashboard page.
