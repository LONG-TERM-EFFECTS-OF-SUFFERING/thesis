# App changes from the thesis review (2026-11)

App fixes made while the thesis document was under review. The LaTeX in `content/` was **not** edited; each entry lists what the document must say once these changes are accepted.

| id | change | status |
| :-: | :-- | :-- |
| US-043 | Language fields become an ES/EN selector | built, reviewed, committed locally (`src/ui` e162b3a on `feature/US-043`) |
| US-044 | Collection runs execute from the app | built, reviewed twice, committed locally (`src/api` f86841d, `src/ui` b1c3ed7 on `feature/US-044`) |
| US-045 | Interface language toggle, Spanish default | built, reviewed, committed locally (`src/ui` 28cf0a2 + 01adff2 on `feature/US-045`) |
| US-046 | 30-day purge runs automatically | planned, ready for development (`_bmad-output/initiative-opentube-insights/plan-us-046-purge-youtube-data-automatically.md`) |

## US-043 — language selector

**What changed.** The project's *Default language* and the saved query's *Language* are now a `<select>` with Not set, Spanish (`es`) and English (`en`), fed from one list (`LANGUAGE_OPTIONS` in `src/ui/src/savedQueryForm.ts`). When an LLM draft applies a code that is not in the list (for example `pt`), the menu adds it as an extra option, so the screen never says "Not set" while saving another code. The API did not change and still accepts any well-formed language tag. Explainer: `docs/project-understanding/41-pick-a-language-from-a-selector.md`.

**Document follow-ups:**
- `content/09_3_5-user_project_management.tex`: the Projects and Queries paragraphs can say the language is chosen from a Spanish/English menu.
- `content/09_2_2-LLM_integration_component.tex`, line 31 ("free text typed by a user"): the interface now offers a menu, but the API still stores free text, so the tag-shape guard on the hint still matters. Reword it rather than delete it.
- `content/09_3_4-data_visualization_components.tex` ("native HTML elements"): still true, since the menu is a native `<select>`.

## US-044 — runs execute from the app

Reviewer note: the document argues against executing runs from the web client; given the tool's target users (researchers, not operators) that is necessary.

**What changed.**
- Start run still returns `201` with a `pending` run at once. After the row is committed, the API collects the run in a background thread of its own process (`collect_run_in_background`), so no command is needed and the Gunicorn timeout is not involved.
- With no `YOUTUBE_API_KEY`, the start returns `503` and creates no run.
- The UI polls the run list every 3 s while a run is `pending` or `running`, and reloads Results when a run finishes.
- SQLite now uses `transaction_mode: IMMEDIATE` so concurrent run threads wait for each other.
- `collect_runs` remains as a recovery tool for runs left `pending`.
- Explainer: `docs/project-understanding/42-execute-collection-runs-from-the-app.md`.

Decision taken in review: a run counts as finished when *collection* ends. Normalization and sentiment then continue in the same thread, so the Results sentiment area may be empty for a while. It says so, and Apply checks again. `status` and `finished_at` keep their current meaning.

**Document follow-ups:**
- `content/09_2_1-backend_data_collection_component.tex`, line 11: rewrite the paragraph.
  - Runs are now collected by a background thread started after the run's row is committed.
  - Collecting *inside the request* is still rejected, for the same Gunicorn-timeout reason.
  - A job queue is still rejected (broker).
  - `collect_runs` is a recovery command for runs left `pending`.
  - The compare-and-set claim is unchanged: two threads, or a thread plus the command, never collect the same run.
- `content/09_1_1-stack_evaluation_and_selection.tex`:
  - Line 61 ("Collection runs and the 30-day purge are executed by Django management commands"): only the purge is a command now.
  - The diagram note at line 86 lists `collect_runs` as a management command. Mark it as recovery, or move collection into the `api` box.
- `content/10-conclusions.tex`:
  - Line 28, Limitations, "Operator duties": collection is no longer an operator duty.
  - New limitations to state:
    - a run whose API process stops mid-run stays `running`, with no automatic recovery;
    - a researcher can now start a run while a scheduled purge runs, and the old operating rule cannot prevent that.
  - Future work: "Schedule collection runs ... within the application" is half done; only the purge schedule and the lock remain.
- `content/09_4_3-validation.tex`, line 7 ("through the user interface and the two management commands"): only the purge command is needed now.
- `content/09_3_4-data_visualization_components.tex`, if it describes the Runs section: the table updates itself while a run is active, an open run offers *Reload details*, and the sentiment area explains an empty state.
- Test counts in `content/10-conclusions.tex` (365 backend / 104 frontend) are already stale. The current counts are 395 backend / 124 frontend after US-045.

## US-045 — interface language toggle

**What changed.**
- A header button, also on the login screen, switches the interface between Spanish and English. Spanish is the default.
- The choice is stored in the browser like the theme, and it sets `<html lang>`.
- There is no library: there is one typed Spanish dictionary keyed by the English text (`src/ui/src/i18n.ts`), so a missing translation fails the build.
- Server-written messages, YouTube data and API values (e.g. `relevance`, `negative`) are not translated.

Reviewed: 3 findings fixed in 01adff2. Explainer: `docs/project-understanding/43-switch-the-interface-language.md`. The browser check (form values survive a switch; reload keeps the choice) is still for you to do by hand.

**Document follow-ups:**
- `content/09_3_4-data_visualization_components.tex` (interface paragraph): add the Spanish/English toggle, its Spanish default and its stored choice, next to the theme sentence. "No component library was added" still holds, because no i18n library was added either.
- Say that server messages and API vocabulary remain in English. Translating them would need Django `LocaleMiddleware` and gettext.


## US-046 — automatic 30-day purge (planned, not built)

**Plan:**
- A Compose `purge` service and a `run-local.sh` background job run `purge_youtube_data` every hour.
- The command skips while a collection run is `running`.

**Document follow-ups, once built:**
- `content/09_3_2-database_layer.tex` line 17: the purge is no longer only an operator command.
- `content/09_1_1-stack_evaluation_and_selection.tex`: line 61 and the diagram add a fifth Compose service, `purge`.
- `content/10-conclusions.tex`: remove "Operator duties" from Limitations, and drop the scheduling item from Future work.
