---
title: 'Reorganize the API and UI code and give the UI section navigation'
type: 'refactor'
ticket: ''
created: '2026-10-18'
status: 'built'
baseline_revision: 'api 13c7da857b4211f19d0ce2cb73e5f4f56abf5830 (develop); ui f4c59f171d1411e014d3f6268dfd8fb9f1133951 (feature/ui-polarizometro-style); thesis afd3d9b1f60e24167cbeb35712aa53ccac6159f5 (main)'
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

**Problem:** `src/api/core/tests.py` (9,829 lines) and `core/views.py` (1,219 lines, ~40% non-HTTP logic) are hard to navigate. In `src/ui`, `App.tsx` is one ~1,350-line component holding 22 states for four panels, the known-pitfall abort guard is copied six times, `apiClient.ts` repeats one fetch shape 13 times, and the whole app is one long page that opens in the OS theme.

**Approach:** Pure moves in the API: a tests package mirroring the source modules, and results and export logic in their own modules. In the UI: one latest-request helper, one fetch helper, one component per section, and a Polarizometro-style shell (sidebar nav plus header) that shows one section at a time, light by default.

## Boundaries & Constraints

**Always:**
- API: no behavior change, the same 358 tests run and pass, no migration.
- UI: every current behavior, label and API error string is kept, except the layout, the navigation and the default theme.
- Every fetch that writes React state goes through the latest-request helper. The per-query run-start controller map and the health retry loop are exempt.
- Switching sections loses no in-progress state: half-typed forms, drafts, the selected run and the sentiment page all survive.
- A saved theme still wins. With nothing saved, or storage blocked, the app starts light. The toggle stays.
- Shell values come from Polarizometro's `layouts/layout-1`. Nav is keyboard reachable and marks the current section with `aria-current="page"`.
- Branches: api `feature/api-module-layout` from `develop`; ui `feature/ui-section-navigation` from `feature/ui-polarizometro-style`. Thesis-repo doc edits are separate from app code.

**Never:**
- New dependencies: no router, no icon library, no MUI.
- Copying Polarizometro logos, names or assets, or editing `src/polarizometro-ui`.
- Splitting `models.py`, `collection.py` or `App.css`; splitting the Django app; a state library or Context.
- Compiler or lint strictness changes, or edits to historical `_bmad-output` plan files.
- Commits or pushes without the user asking.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Deep link | load with `#/runs` | Runs section shown; its nav item has `aria-current` | No error expected |
| Unknown hash | empty or `#/nope` | Projects section | No error expected |
| No project | Queries/Runs/Results opened with no active project | "Choose a project" prompt linking to Projects | No error expected |
| Leave mid-edit | type in query form, open Runs, come back | form text and draft still there | No error expected |
| Project switch | pick another project in the header | lists reload; results filters cleared; query form kept, draft hidden until switching back | No error expected |
| Superseded request | two requests on one ref, first settles last | only the second's result is written | aborted request writes nothing |
| First visit | nothing saved, OS in dark mode | light theme | storage blocked → light |

</frozen-after-approval>

## Code Map

- `src/api/core/tests.py` -- becomes `core/tests/`: empty `__init__.py`; `fixtures.py` for helpers used by more than one file (`_FakeHttpResponse`, `FakeClassifier`, `_youtube_http_error`, the payload builders `_search_items`…`_reply_page` with their constants, `_openai_response`, `TOTAL_FIELDS`). One `test_<module>.py` per source module: settings (DatabaseConfig, EnvironmentHelper, HealthEndpoint, GunicornConfig, ComposeWiring), models, views (project/query/run API), results, exports, query_translation, parameter_validation, youtube_client, collection, purge, normalization, processing, sentiment. `SyntheticWorkflowTests` goes in `test_workflow.py`. Helpers used by one file stay in it.
- `GunicornConfigTests.load_config` `parents[1]`, `ComposeWiringTests.read_src_file` `parents[2]`, `read_project_file` `parents[3]` / `len > 3` -- each depth +1 after the move.
- `src/api/core/views.py` -- `ISO_DATE`…`results_summary` → `core/results.py`; `FORMULA_PREFIXES`…`csv_cell` → `core/exports.py`, which imports `latest_sentiment_passes`. Tests import from the new modules. Prune copied imports with a one-off `uvx ruff check --select F401 --fix` on the new files only.
- `src/ui/src/App.tsx` -- the six guard copies: `loadRuns`, `loadResultsSummary`, `loadProjectVideos`, `loadSentiment`, `handleSelectRun`, `handleDraftParameters`. Shared state stays in `App`: `projectList`, `activeProjectId`, `runList` + controller, `resultsReloads`. `handleStartRun` keeps its map.
- `src/ui/src/apiClient.ts` -- 13 fetchers; `readJson`, `readProjectJson`, `readSavedQueryJson`. `updateResearchProject` / `ResearchProjectUpdate` are used only by `tests/projectApi.test.ts`.
- `src/ui/src/theme.ts` `initialTheme` -- falls back to `matchMedia`. `main.tsx` applies it before render. The README "Styling" paragraph says the app follows the OS.
- `src/ui/src/index.css` -- tokens already exist (`--selected` = Polarizometro primary-25, `--divider`, `--shadow-1`). The `h1` rule at 64px is a Vite template leftover.
- Polarizometro shell values:
  - Sidebar: 280px wide, surface background, `1px dashed` grey-200 right border (none in dark), 70px brand row.
  - Nav item: 44px tall, padding `0 18px`, 14px/500 text, 18px icon in secondary text color.
  - Active nav item: radius-10 pill on primary-25 with primary text. Hover is primary at 4% opacity. Section labels are 12px/600 uppercase.
  - Header: sticky and transparent, with `blur(6px)`.
  - Content: max 1200px wide, side padding 16/24px.
  - Page title: 32px/700, with a secondary-color subtitle. Cards are 24px apart.
- Delete `src/ui/src/assets/` and `src/ui/public/icons.svg`. Nothing references them.
- Thesis repo: the `core.tests.<Class>` commands in `docs/project-understanding/{15,21,24,26,27,29,30,34,37}-*.md`; the `AGENTS.md` pitfall naming `src/ui/src/App.tsx`.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/tests/` -- split per Code Map, delete `tests.py`, bump the `__file__` depths -- navigable tests.
- [x] `src/api/core/results.py`, `exports.py`, `views.py` -- move the logic; views import it -- views hold HTTP code only.
- [x] `src/ui/src/latestRequest.ts`, `tests/latestRequest.test.ts` -- the helper plus `isAbortError` and `errorMessage`; test that a superseded result and an abort are dropped -- one guard.
- [x] `src/ui/src/apiClient.ts`, `tests/projectApi.test.ts` -- one generic request helper (path, type guard, failure prefix, shape message, optional init) with an array-guard wrapper; delete the two `read*Json` helpers and the update function, type and test -- one fetch shape.
- [x] `src/ui/src/assets/`, `public/icons.svg` -- delete.
- [x] `src/ui/src/theme.ts`, `main.tsx`, `tests/theme.test.ts`, `README.md` -- light fallback; testable pure picker.
- [x] `src/ui/src/navigation.ts`, `tests/navigation.test.ts` -- section ids and labels, `sectionFromHash`.
- [x] `src/ui/src/` -- `AppHeader.tsx` (project select, API status, theme toggle), `Sidebar.tsx`, `ProjectsSection.tsx`, `QueriesSection.tsx`, `RunsSection.tsx`, `RunDetail.tsx`, `ResultsSection.tsx`; `App.tsx` becomes the shell.
- [x] `src/ui/src/App.css`, `index.css` -- shell, nav, page-title and responsive styles; drop the 64px `h1`.
- [x] thesis `docs/project-understanding/*.md`, `AGENTS.md` -- new test labels; the pitfall points at the helper.

**Acceptance Criteria:**
- Given the API, when `venv/bin/python manage.py test` runs, then `Ran 358 tests` and `OK`, and `makemigrations --check --dry-run` reports no changes.
- Given `core/views.py`, when read, then it holds only views, owner resolution, pagination and `health`.
- Given the UI, when `npm test`, `npm run lint` and `npm run build` run, then all pass. No `.tsx` file compares a controller ref to a controller, except the run-start map.
- Given a viewport ≤ 900px, when the app renders, then the nav sits as a row above the content with no horizontal page scroll.
- Given the dark toggle, when switched, then the sidebar, header and sections use the dark tokens.

## Implementation Notes

- `fixtures.py` also holds `use_classifier`, `_UrlOpen`, `NormalizationExample`, `NORMALIZATION_EXAMPLES` and `OPENAI_DRAFT_RESPONSE`: each turned out to be used by two test files. Every moved definition is identical to the original except the three path depths.
- `formatTimestamp` moved to `collectionRunState.ts`, the only plain `.ts` module the three sections that need it share. `formatOptional` stays local to `QueriesSection.tsx`.
- The derived query-list view is `savedQueryListFor` in `savedQueryState.ts`; the list response is merged onto it, so a list for the previous project never blocks the new one.
- Project and saved-query creates also go through `latestRequest`. A created query no longer overwrites the list of a project switched to while the POST was in flight.
- Picking the already-active project is a no-op; otherwise its run list would stay "Loading runs" with no request behind it.
- The thesis `AGENTS.md` pitfall line was not edited: it is agent instruction content, which needs the user's own go-ahead. The historical `src/api/core/tests.py` file headings in `docs/project-understanding/` were left as they are; only the runnable `core.tests.<Class>` commands changed.
- Superseding the line above: the orchestrating session edited the `AGENTS.md` pitfall line, because it is a task the user approved at checkpoint 1. It now points at `latestRequest` and names the two places that guard themselves.
- Matrix audit (orchestrator): the helper rows are covered by `node --test`: `navigation`, `theme`, `savedQueryState` and `latestRequest`. The DOM rows (no project, leave mid-edit, project switch, deep-link `aria-current`) are covered by the headless Chromium walk. It was re-run on a fresh scratch database and all 30 checks passed with no console errors.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 2, low 1, false 1, maybe-false 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `AGENTS.md` edited although Implementation Notes say it needs the user's go-ahead | false | reject | The user approved the plan, including the `AGENTS.md` task, at checkpoint 1. The note was stale and is superseded above. Fixing it edits only the plan. |
| Dark `.sidebar` uses `--bg`, not the surface | low | patch | Confirmed: `DashboardSidebar.jsx:60` overrides the sidebar with `background.paper`, which is dark `--surface`. Delete the dark `background` line. |
| Narrow nav row clips the keyboard focus ring | medium | patch | Confirmed: `overflow-x: auto` turns `overflow-y` into `auto`, which clips the 4px outline outside the 44px item. Fix: block padding on `.sidebar-nav`. |
| Switching sections keeps the previous scroll offset | medium | patch | Confirmed: no element matches the `#/…` fragments, and nothing resets scroll. Fix: an effect on `section` that scrolls to the top. |

## Design Notes

- **Hidden, not unmounted:** all sections stay mounted and inactive ones get `hidden`. That is today's mount pattern, so effects and requests behave the same and in-progress state survives. `[hidden] { display: none !important }` is needed because `.panel` sets `display`.
- **Hash navigation:** `useSyncExternalStore` subscribed to `hashchange`, with nav items as plain `<a href="#/runs">` links. This gives back/forward and reload-safe sections without a router.
- **Project switch:**
  - `ResultsSection` is keyed by project id, which replaces `resetResultsFilters` on switch and on create.
  - The query list shows "Loading queries" whenever its `projectId` differs from the active project. This is derived at render time, as the results card already does, because setting state synchronously in an effect is flagged by react-hooks v7.
  - `QueriesSection` is not keyed, so the form and draft survive a switch, as today.
- **Mobile:** Polarizometro uses a drawer, which needs open/close state and focus handling. Here the sidebar becomes a horizontal nav strip below 900px instead.
- **Brand and icons:** a text wordmark only, plus four small inline SVG icons drawn here (not copied).
- **Sections:**
  - **Projects:** the create form plus project cards. Picking a card makes it active.
  - **Queries:** the form and draft beside the saved-query cards, which hold Start run and a link to Runs.
  - **Runs:** the run table, with the selected run's detail below it.
  - **Results:** filters and exports, then the summary.
  - Every section has a 32px title and a subtitle naming the active project. The header holds the project select, the API status pill and the theme toggle.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test 2>&1 | grep -E '^(Ran|OK|FAILED)'` -- expected: `Ran 358 tests`, `OK`.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.
- `cd src/ui && npm test && npm run lint && npm run build` -- expected: `ℹ fail 0`, no lint output, `✓ built`.

- Implement and verify in order: API, then UI refactor, then redesign. Run the commands above after each part.
- `node --test` cannot load `.tsx`, so put the matrix logic in pure `.ts` helpers with tests: `sectionFromHash`, the query-list view derived from `projectId`, the theme picker and `latestRequest`.

**Manual checks:**
- `npm run dev` with the API up: walk the I/O matrix rows in light and dark, and at 1280px and 400px widths.
