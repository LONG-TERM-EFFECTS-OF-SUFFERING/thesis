---
type: migration
title: Move v6 planning and implementation artifacts into the v7 initiative layout
status: done
created: 2026-10-02
module: method
from: '6'
to: '7'
---

# Migration v6 → v7

Driven by `.agents/skills/bmod-method/migration-1.toml`. Nothing moves until this plan is approved.

## Prerequisites already done (2026-10-02)

- The 31 installed skills were linked into `.claude/skills/` so Claude Code can discover them. Before this, none were invokable.
- `bmad setup` ran: `shared_scripts` repaired, both modules' scripts created (`_bmad/method/scripts/tickets.py` now exists — the migration's own verification command needs it). Install reports `current: true`.
- Installed version: `6.13.0-next` for `core-tools` and `method`, both already at the latest published version. **No version change is part of this migration.**

## Detect signals

| Signal | Present |
| --- | :-: |
| `sprint-status.yaml` under `implementation_artifacts` | **yes** (v6 for certain) |
| `epics.md` under `planning_artifacts` | no |
| Story files `<epic>-<story>-<slug>.md` in the implementation folder | yes (7; frontmatter carries `baseline_commit`, not the v6 `route:`/`status:` pair) |
| Dated artifact folders (`prds/`, `briefs/`, `ux-designs/`, `architecture/`) | no |
| `specs/spec-<slug>/SPEC.md` | no |
| No `active_initiative`, no `initiative-*/` folder | confirmed — migration applies |

## Inventory

Source folders from `_bmad/config.toml` (no `_bmad/custom/` overrides exist for them):

- `core.output_folder` = `_bmad-output`
- `modules.bmm.planning_artifacts` = `_bmad-output/planning-artifacts` — **empty**
- `modules.bmm.implementation_artifacts` = `_bmad-output/implementation-artifacts`

All 11 files under the output folder:

| File | Classification |
| --- | --- |
| `implementation-artifacts/1-1-docker-backend-and-database-services.md` | build record |
| `implementation-artifacts/1-2-docker-frontend-service.md` | build record |
| `implementation-artifacts/1-3-nginx-and-gunicorn-ready-local-wiring.md` | build record |
| `implementation-artifacts/2-1-create-research-project.md` | build record |
| `implementation-artifacts/2-2-save-youtube-search-query.md` | build record |
| `implementation-artifacts/3-1-generate-draft-youtube-api-parameters-from-natural-language.md` | build record |
| `implementation-artifacts/3-2-validate-generated-youtube-api-parameters.md` | build record (not started) |
| `implementation-artifacts/deferred-work.md` | moves to the initiative folder unchanged (explicit rule) |
| `implementation-artifacts/sprint-status.yaml` | tracking source → `archive-v6/` |
| `party-mode/memories/installed/.memlog.md` | stray memlog, nothing beside it → `inbox/archive-v6/` |
| `project-context.md` | left in place (see below) |

## Deviation from the migration's assumptions — read this

The migration's ticket-tree rules read `epics.md` and a PRD coverage map to produce epic `Requirements` and `covers` ids. **This project has neither.** Your epics and stories live in `docs/product_backlog.md` and `docs/sprint_planning.md`, which are thesis documents under `project_knowledge`, not BMad artifacts, and are **not** source folders for this migration.

Consequences, all recorded rather than papered over:

1. Epic `Requirements` are transcribed from the `docs/product_backlog.md` user-story rows, each keeping its **`US-0NN` id** as the stable requirement id. Entry `covers` cites those same ids. This keeps your existing traceability spine (`US-0NN` across the backlog, the sprint plan, `docs/project-understanding/` and the LaTeX chapters) alive inside v7 instead of inventing `FR-N` ids.
2. The initiative envelope has no PRD to draw Description, Outcome and Done-when from. They are written from the `docs/product_backlog.md` epic table and the thesis brief in `_bmad-output/project-context.md`, and must be confirmed.
3. Checklist item 7 ("every requirement in the PRD's coverage map has at least one entry") will be recorded as **adapted**: checked against `docs/product_backlog.md` instead of a PRD.
4. `docs/product_backlog.md`, `docs/sprint_planning.md` and `docs/project-understanding/` **do not move**. They are referenced from the initiative's References.

### v7 has no sprints

`sprint-status.yaml`'s `sprints:` block (13 two-week sprints, 2026-05-25 → 2026-11-20) has no equivalent in the v7 ticket tree — v7 orders work by `tickets.toml` build order and `after` prerequisites, not by sprint. After this migration, `docs/sprint_planning.md` is the **only** sprint record, maintained by hand. Your methodology chapter claims adapted Scrum, so decide deliberately whether that is acceptable before approving.

## The four lists

**Joins the initiative** (evidence: v6 build records and tracking in the implementation folder)

- the 7 story files, as plans or folded entries per the table below
- `deferred-work.md`, unchanged

**Moves to inbox**

- `party-mode/memories/installed/.memlog.md` → `inbox/archive-v6/.memlog.md`, unchanged, with `inbox/space.md` created. **Confirmed by the user.**

**Stays where it is**

- `_bmad-output/project-context.md` — referenced by path from all 7 story files and carrying project-wide rules, not initiative-specific ones. Listed at the store root as left alone, which the checklist permits. v7's replacement is a managed block in a root `AGENTS.md`; run `bmad-project-context` after the migration to create it. **This repo currently has no `AGENTS.md` or `CLAUDE.md`, so nothing auto-loads these rules today.**
- everything under `docs/`

**Archived** → `initiative-<slug>/archive-v6/`

- `sprint-status.yaml`, unchanged
- `3-2-validate-generated-youtube-api-parameters.md`, if question 2 is answered "fold"

## Target: epics and entries

8 epics, 39 entries. Epic `status` is carried from `sprint-status.yaml` exactly as recorded.

> **Flagged inconsistency:** `epic-1` and `epic-2` are recorded `in-progress`, but every story under them is `done`. Carried as `in-progress` per the rules. Their retrospectives are `optional` and not done; `bmad-retrospective` would close them out.


### `epic-reproducible-local-foundation` — status `in-progress`

| entry `id` | US | title | v6 status | v7 disposition |
| :-: | :-: | --- | :-: | --- |
| 1 | US-001 | Docker backend and database services | `done` | plan `story-docker-backend-and-database-services-plan.md`, status `done` |
| 2 | US-002 | Docker frontend service | `done` | plan `story-docker-frontend-service-plan.md`, status `done` |
| 3 | US-003 | Nginx and Gunicorn-ready local wiring | `done` | plan `story-nginx-and-gunicorn-ready-local-wiring-plan.md`, status `done` |

### `epic-research-project-and-query-setup` — status `in-progress`

| entry `id` | US | title | v6 status | v7 disposition |
| :-: | :-: | --- | :-: | --- |
| 1 | US-004 | Create research project | `done` | plan `story-create-research-project-plan.md`, status `done` |
| 2 | US-005 | Save YouTube search query | `done` | plan `story-save-youtube-search-query-plan.md`, status `done` |

### `epic-natural-language-query-translation` — status `in-progress`

| entry `id` | US | title | v6 status | v7 disposition |
| :-: | :-: | --- | :-: | --- |
| 1 | US-006 | Generate draft YouTube API parameters from natural language | `done` | plan `story-generate-draft-youtube-api-parameters-from-natural-language-plan.md`, status `done` |
| 2 | US-007 | Validate generated YouTube API parameters | `ready-for-dev` | **folded** → entry + `archive-v6/3-2-validate-generated-youtube-api-parameters.md` |
| 3 | US-008 | Build editable query parameter review screen | `backlog` | entry only, no plan |
| 4 | US-009 | Save approved parameters with validation feedback | `backlog` | entry only, no plan |

### `epic-traceable-youtube-collection` — status `(none — backlog)`

| entry `id` | US | title | v6 status | v7 disposition |
| :-: | :-: | --- | :-: | --- |
| 1 | US-010 | Create collection run model and status lifecycle | `backlog` | entry only, no plan |
| 2 | US-011 | Start a collection run from a saved query | `backlog` | entry only, no plan |
| 3 | US-012 | Store collection run counts, quota, timestamps and errors | `backlog` | entry only, no plan |
| 4 | US-013 | Create API request log model and service wrapper | `backlog` | entry only, no plan |
| 5 | US-014 | Show request logs for each collection run | `backlog` | entry only, no plan |
| 6 | US-015 | Discover videos with YouTube search.list | `backlog` | entry only, no plan |
| 7 | US-016 | Show video discovery summary | `backlog` | entry only, no plan |

### `epic-youtube-data-storage-and-processing` — status `(none — backlog)`

| entry `id` | US | title | v6 status | v7 disposition |
| :-: | :-: | --- | :-: | --- |
| 1 | US-017 | Store video metadata and raw video payload | `backlog` | entry only, no plan |
| 2 | US-018 | Store channel metadata and raw channel payload | `backlog` | entry only, no plan |
| 3 | US-019 | Store video statistics snapshots | `backlog` | entry only, no plan |
| 4 | US-020 | Link collection runs to videos idempotently | `backlog` | entry only, no plan |
| 5 | US-024 | Add basic cleaning, normalization and validation report | `backlog` | entry only, no plan |

### `epic-results-visualization-and-analysis` — status `(none — backlog)`

| entry `id` | US | title | v6 status | v7 disposition |
| :-: | :-: | --- | :-: | --- |
| 1 | US-027 | Show results summary counts and card | `backlog` | entry only, no plan |
| 2 | US-028 | Show sentiment distribution chart | `backlog` | entry only, no plan |
| 3 | US-029 | Filter results by date and video | `backlog` | entry only, no plan |
| 4 | US-030 | Filter results by sentiment | `backlog` | entry only, no plan |

### `epic-comments-and-sentiment-analysis` — status `(none — backlog)`

| entry `id` | US | title | v6 status | v7 disposition |
| :-: | :-: | --- | :-: | --- |
| 1 | US-021 | Collect top-level comments for selected videos | `backlog` | entry only, no plan |
| 2 | US-022 | Collect comment replies with pagination and resume handling | `backlog` | entry only, no plan |
| 3 | US-023 | Store comment raw payloads, quota and errors | `backlog` | entry only, no plan |
| 4 | US-025 | Run one pre-trained sentiment model and store results | `backlog` | entry only, no plan |
| 5 | US-026 | Show sentiment labels, scores and model information | `backlog` | entry only, no plan |

### `epic-testing-export-and-thesis-validation` — status `(none — backlog)`

| entry `id` | US | title | v6 status | v7 disposition |
| :-: | :-: | --- | :-: | --- |
| 1 | US-031 | Export videos, channels and logs as CSV | `backlog` | entry only, no plan |
| 2 | US-032 | Export raw payloads, sentiment and metrics as JSON or CSV | `backlog` | entry only, no plan |
| 3 | US-033 | Add database and model tests | `backlog` | entry only, no plan |
| 4 | US-034 | Add YouTube collection service tests | `backlog` | entry only, no plan |
| 5 | US-035 | Add LLM query translation tests | `backlog` | entry only, no plan |
| 6 | US-036 | Add processing tests | `backlog` | entry only, no plan |
| 7 | US-037 | Add presentation smoke tests | `backlog` | entry only, no plan |
| 8 | US-038 | Validate the workflow with synthetic fixtures | `backlog` | entry only, no plan |
| 9 | US-039 | Validate the workflow with real YouTube topics | `backlog` | entry only, no plan |

## Build records → plans

6 `done` story files become plans beside their entry. Frontmatter per the rules: `ticket` (the entry's numeric id), mapped `status`, a build `type` (never `story`), and `baseline_revision` **only** where the record already holds one.

| v6 file | plan `ticket` | `status` | `type` | `baseline_revision` |
| --- | :-: | :-: | :-: | --- |
| `1-1-docker-backend-and-database-services.md` | 1 | `done` | `feature` | **missing** — not inferred |
| `1-2-docker-frontend-service.md` | 2 | `done` | `feature` | **missing** — not inferred |
| `1-3-nginx-and-gunicorn-ready-local-wiring.md` | 3 | `done` | `feature` | `6764bd4c047329756dbd42efa78a4dc7ce34085b` |
| `2-1-create-research-project.md` | 1 | `done` | `feature` | **missing** — not inferred |
| `2-2-save-youtube-search-query.md` | 2 | `done` | `feature` | `b8afe4db5e99d4be99d5057d432f6b51a4224139` |
| `3-1-generate-draft-youtube-api-parameters-from-natural-language.md` | 1 | `done` | `feature` | `bfc37c82841658a19d0cf57182fe337079112738` |

Three baselines are absent from the v6 records. The migration forbids inferring one from today's HEAD, so they are disclosed here and in the final report rather than guessed.

The 32 stories with no build record stay entries with no plan, their full `done when` text from `docs/product_backlog.md` kept in the entry description.

## Questions

| # | Question | Default | Answer |
| :-: | --- | --- | --- |
| 1 | Back up the output folder to `_bmad-output-bak` first? | Yes | **Git is the backup.** Working tree committed at `f1f9055` before any move (`2aa1e18` carries the US-007 artifact and sprint status, `f1f9055` the thesis objective edit). No `-bak` copy. |
| 2 | One initiative or several, and what is each called? | One, named after `core.project_name` → `initiative-thesis` | **One: `initiative-opentube-insights`**, after the product rather than the repo. |
| 3 | Will this work touch other repositories? If yes, `_bmad/` and the planning files move into a workspace folder above them. | No | **No** — `src/api` and `src/ui` are nested repos *inside* this project, not sibling projects. A workspace would move the whole thesis checkout down a level and break every path in the LaTeX build, the Compose files and `docs/`. Not applicable. |
| 4 | Keep the planning files' git history in their own repository, apart from the code? | No | **No** — `_bmad-output/` is tracked in the thesis repo and its history is thesis evidence. Splitting it would require `git rm -r --cached _bmad-output` and gitignoring it, which removes that evidence from the thesis history. |
| 5 | Some stories are in progress or in review. Finish them in v6 first, or migrate now? | Finish first | **Not applicable** — nothing is `in-progress` or `in-review`. 6 `done`, 1 `ready-for-dev`, 32 `backlog`. |
| 6 | Fold unstarted stories that already have v6 files into their entries and archive the files? | Yes | **Yes.** US-007 (`3-2`) folds into its entry; the file moves to `archive-v6/` unchanged. |

## Configuration changes implied

- `_bmad/custom/config.user.toml` gains `active_initiative = "initiative-<slug>"` under `[core]`.
- `_bmad/custom/ticketing-store-config.toml` is created by `bmad-ticket`'s store setup: repo store, rooted at `_bmad-output`.
- `core.output_folder`, `planning_artifacts` and `implementation_artifacts` are **left alone** (no workspace move).
- Empty `_bmad-output/planning-artifacts/` is removed, and `implementation-artifacts/` once emptied.
- `.gitignore` is **not** touched.

## Commit grouping

`_bmad-output/` is tracked in an existing repo, so every move is a `git mv` and each group is committed in order: initiative folder and envelope (with this plan moved into it) → planning documents (none) → epics, entries and plans → loose files and inbox → the archive → path rewrites → configuration. The current working tree is committed first. Nothing is pushed.

## Checklist results

Filled in after the moves; an item that cannot be checked is recorded as such.

| # | Item | Result |
| :-: | --- | --- |
| 1 | Every v6 source file is under an initiative, `backlog/`, `inbox/`, `archive-v6/`, or listed as left in place | **pass** — all 11 accounted for: 6 plans, 1 folded + archived, `deferred-work.md` in the initiative, `sprint-status.yaml` archived, the memlog in `inbox/archive-v6/`, `project-context.md` listed as left in place |
| 2 | Every created folder holds a same-named main file; no name carries a date or a v6 story/epic number | **pass** — 8 epic folders and the initiative each hold their same-named file; `inbox/space.md` is its identity file. `archive-v6/3-2-…md` keeps its v6 number, which the archive rules allow (archived files move unchanged), and `migration-v6-v7/` is a named exception |
| 3 | Every store-root entry is an `initiative-`/`epic-` folder, `backlog/`, a space, a `<type>-<slug>/`, or a listed remnant | **pass** — root holds `initiative-opentube-insights/`, `inbox/` (with `space.md`) and `project-context.md`, the last listed above as left alone |
| 4 | `tickets.py status <initiative>` exits 0; story counts match the archived tracking sources | **pass** — exit 0. 39 tickets: 6 `done`, 33 `planned`. v6 had 39 stories: 6 `done`, 1 `ready-for-dev`, 32 `backlog`. The `ready-for-dev` one is `planned` because folding it leaves it without a plan, which is the agreed behaviour |
| 5 | Every story is one entry; every build record one plan or a folded entry plus an archived file | **pass** — 39 entries across 8 `tickets.toml`, 6 plans, 1 folded entry with its archived file. No epic story files were written |
| 6 | Every plan has a build type and mapped status; `done` stays `done`; baselines kept or disclosed | **pass** — all 6 plans are `type: feature`, `status: done`. Baselines kept for US-003, US-005, US-006; **absent for US-001, US-002, US-004** and recorded as absent rather than inferred from HEAD. The body `Status:` line was removed from each plan so frontmatter is the single source of status |
| 7 | Every epic/entry `covers` id exists in its requirement source; every requirement has an entry | **pass, adapted** — checked against `docs/product_backlog.md` rather than a PRD coverage map, which this project does not have. 39 backlog `US` ids, 39 entry `covers` ids, each covered exactly once, none unmatched in either direction; every entry's `covers` id appears in its own epic's Requirements; the union of epic `covers` equals the backlog exactly |
| 8 | Every live path in References and prose links resolves from its new folder | **pass, 3 listed apart** — 21 references to moved files rewritten across 5 plans. Three remaining mentions of `_bmad-output/implementation-artifacts/` are historical prose inside `done` plans describing the v6 folder itself, not links to a file (`story-docker-backend-and-database-services-plan.md` lines 137–138, `story-generate-draft-…-plan.md` line 364). A `done` plan stays as it was written, so they are left intact. No reference in `docs/` or `content/` pointed at any moved file |
| 9 | `config.user.toml` names the active initiative; `ticketing-store-config.toml` exists | **pass** — `resolve_config.py` returns `core.active_initiative = "initiative-opentube-insights"`; `_bmad/custom/ticketing-store-config.toml` exists as the repo store and `read_toml.py` parses it |
| 10 | The store is under git as answered; no file tracked by two repositories | **pass** — one repository, as answered. No `git init`, no `git rm --cached`, no `.gitignore` change. `_bmad-output/` stays in the thesis repo history and every move was a `git mv` |
| 11 | This plan records every question, its answer, the backup, and each item's result | **pass** — this document |

## Outcome

Migration complete. `tickets.py status` exits 0 and `tickets.py next` puts `3.2` (US-007) first in `ready_to_start`.

**The one real weakness:** no entry declares a prerequisite, so `ready_to_start` lists all 33 unstarted stories. v6 recorded no story-level dependencies and the migration forbids inferring them from list order. Until one `bmad-ticket` pass declares them, treat that list as "not blocked by anything *recorded*", not as "genuinely ready".
