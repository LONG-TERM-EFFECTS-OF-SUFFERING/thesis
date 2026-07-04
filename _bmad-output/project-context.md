---
project_name: 'thesis'
user_name: 'Brandon'
date: '2026-06-05'
sections_completed:
    [
        'discovery',
        'technology_stack',
        'repository_layout',
        'thesis_brief',
        'language_specific_rules',
    ]
existing_patterns_found: 10
---

# Project context for AI agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology stack and versions

- Backend lives in `src/api` and uses Python 3.14 with Django `6.0.5`.

- Backend API framework is Django REST framework `3.17.1`.

- PostgreSQL access uses `psycopg[binary]` `3.3.4`.

- Local backend environment-file support uses `python-dotenv` `1.2.1`.

- Backend dependency versions come from `src/api/requirements.txt`; do not guess or normalize them from memory.

- Docker Compose lives at `src/docker-compose.yml` and uses PostgreSQL `18-alpine` as the reproducible validation database.

- SQLite is allowed only for fast local backend iteration; all thesis validation, acceptance testing, migration checks and reported database behavior must use PostgreSQL via Docker Compose.

- Frontend lives in `src/ui` and uses React `19.2.6`, Vite `8.0.12` and TypeScript `6.0.2`.

- Frontend dependency versions come from `src/ui/package.json` and `src/ui/package-lock.json`; use npm unless the project explicitly changes package manager.

- Frontend linting uses ESLint `10.3.0`; plugin versions are governed by the frontend package manifest.

- Active implementation happens in `src/api` and `src/ui`, and those folders are nested repositories ignored by the main thesis repo. The main repo owns only shared root orchestration files such as `src/docker-compose.yml` and `src/.env.example`.

- Do not downgrade, substitute or opportunistically upgrade Python, Django, DRF, React, Vite, TypeScript, ESLint, PostgreSQL or psycopg without an explicit migration task and validation plan.

## Library and dependency policy

- Libraries are welcome when they clearly accelerate a real current feature, reduce implementation risk, or provide well-tested behavior that would be wasteful to rebuild.

- Do not add a library just because it is popular, familiar, or might be useful later. Speculative dependencies should wait until the app has the repeated need.

- Prefer this order: existing project code, platform/browser features, React/Vite/TypeScript basics, already-installed dependencies, then a new library.

- Before adding a new dependency, document the concrete problem it solves, why local code would be worse, any trade-offs such as bundle size, licensing, maintenance, styling constraints, or API lock-in.

- For UI work, keep plain React and CSS until component repetition or accessibility complexity makes a library cheaper. Add UI libraries component-by-component when possible instead of adopting a large design system by default.

- For domain-heavy features such as charts, tables, server-state caching, validation, dates, or accessible primitives, prefer proven libraries over custom implementations when the feature is non-trivial.

## Subrepo documentation independence

- Documentation inside `src/api` and `src/ui` must treat that folder as the repository root.

- Do not write subrepo README paths from the main thesis repository perspective. For example, in `src/api/README.md`, use `.env`, `.env.example`, `manage.py` and `db.sqlite3`, not `src/api/.env` or `src/api/manage.py`.

- Main-repo paths such as `src/api`, `src/ui` and `src/docker-compose.yml` belong in thesis-level docs, BMAD artifacts and `docs/project-understanding/`, not inside subrepo-local setup instructions.

## Repository layout and Git rules

- The main thesis repository tracks thesis prose, planning artifacts, BMAD artifacts, learning documentation and shared root Compose artifacts under `src/`. It intentionally ignores nested app repositories such as `src/api` and `src/ui`.

- `src/api` and `src/ui` are nested Git repositories, not Git submodules. `git submodule status` should be empty. Do not convert them to submodules unless Brandon explicitly asks for that migration.

- Do not add API, UI, virtualenv, node or app runtime files to the main thesis repo. Shared root Compose files belong to the main repo; API and UI implementation files are committed from the relevant nested repository when needed.

- Use the main repo for `content/`, `docs/`, `_bmad-output/`, LaTeX tooling and project-understanding docs.

- Use `src/api` for backend code and backend Git history. Use `src/ui` for frontend code and frontend Git history.

- Use `src/docker-compose.yml` for local multi-service orchestration. Run Compose commands from `src/`, for example `cd src && docker compose config`.

- Backend local env template is `src/api/.env.example`; local backend overrides go in `src/api/.env`. Docker Compose override values live in `src/.env.example`; copy it to `src/.env` for local Compose port/proxy overrides.

- The backend Django project package is `opentube_insights_api`. Do not recreate or refer to the old `thesis_api` package name for current implementation work.

- If Brandon asks to create commits, for the commit message follow the "Conventional Commits" convention.

- Brandon is using GitFlow, if he asks to create branches the name of the:
    - feature would be the number of the US (`feature/US-XXX`).

## Taiga workflow

Taiga project:

- Name: `OpenTube Insights`.

- Project ID: `1791562`.

- Slug: `braz-lkdi-opentube-insights`.

- Owner/current user: `braz9LKDI` / user ID `783877`.

Use Taiga at the user story (US) level only. Tasks are not used under user stories; each US is the smallest trackable work item.

When Taiga tools are needed:

1. If Taiga tools are not loaded, search for them with `tool_search` using: `taiga userstories project slug`.

2. Resolve or verify the project with:
    - `taiga_projects_get_by_slug({ "slug": "braz-lkdi-opentube-insights" })`.

    - or use project ID directly: `1791562`.

3. List open user stories with:
    - `taiga_userstories_list({ "project": 1791562, "status__is_closed": false, "order_by": "ref" })`.

4. Get a specific user story by Taiga ref with:
    - `taiga_userstories_get_by_ref({ "project": 1791562, "ref": <ref> })`.

5. If status metadata is needed, query:
    - `taiga_userstory_statuses_list({ "project": 1791562 })`.

Commit integration rule:

- When a commit completes a user story, include the Taiga reference in the commit message: `TG-<ref> #done`.

- Available user-story status slugs for this project:
    - `new` (ID `10869731`, open).

    - `ready` (ID `10869732`, open).

    - `in-progress` (ID `10869733`, open).

    - `ready-for-test` (ID `10869734`, open).

    - `done` (ID `10869735`, closed; use this for completed implementation work).

    - `archived` (ID `10869736`, closed and archived; do not use for normal completion commits).

Do not create or rely on Taiga tasks for implementation tracking unless explicitly instructed.

## Thesis brief for agents

Use this section before reading the full LaTeX thesis. Only open `content/*.tex` when exact wording, citations, tables or traceability are required.

- Working project: a web application for automated collection, processing, analysis and visualization of YouTube data for transparent, reproducible academic research.

- Core problem: YouTube is socially important and widely used for information consumption, but existing commercial/social-listening tools are proprietary black boxes. Academic researchers need an auditable, no-cost, reproducible system that exposes collection parameters, processing steps, schemas and validation evidence.

- Motivating case: PROMUEVA at Universidad del Valle needs transparent social-media data infrastructure to support computational models of polarization in Valle del Cauca and Cali.

- General objective: develop a web application that automates collection, processing, analysis and visualization of data from YouTube videos.

- Specific objectives: design the architecture; implement a YouTube Data API collection module with a natural-language/LLM query interface; implement processing and visualization components; test the system through functional and integration tests from user query to visual output.

- Scope inclusions: YouTube-only data collection; AI query translation using existing pre-trained models; cleaning, normalization, validation and structured storage of raw API responses; charts and summary views; Dockerized services for reproducible deployment.

- Scope exclusions: no other social platforms, no training or fine-tuning NLP models, no real-time streaming analysis and no native mobile application.

- Methodology: adapted Scrum for an individual thesis project. Product backlog and sprint planning are maintained in `docs/product_backlog.md` and `docs/sprint_planning.md`; work is distributed across thirteen two-week sprints from May 25 to November 20, 2026.

- Selected stack from the thesis design: Django REST Framework backend, PostgreSQL database, React + Vite frontend, Nginx/reverse proxy and Gunicorn for later production-style wiring, Docker for containerization.

- YouTube Data API focus: use read-oriented resources including `search.list`, `videos.list`, `commentThreads.list` and `comments.list`. The app should document exact request parameters, timestamps, pagination and quota costs because API results can vary over time.

- Quota principle: `search.list` is expensive at 100 quota units; `videos.list`, `commentThreads.list`, `comments.list`, `channels.list` and `playlistItems.list` are treated as lower-cost one-unit methods in the thesis review. Avoid redundant searches and store discovered IDs for follow-up calls.

- Database design principle: PostgreSQL + Django ORM. Store not only processed outputs but also research projects, saved queries, collection runs, API request logs, YouTube channels/videos/comments, collection-run links, video statistic snapshots, processing runs, sentiment records, derived metrics, raw JSON payloads, request parameters, quota usage and timestamps.

- Reproducibility rule: API-dependent collection is a constrained observation of YouTube, not a stable complete representation. Preserve raw payloads, original YouTube IDs, effective query parameters, model metadata, processing summaries and collection timestamps so another reviewer can reconstruct what happened.

- Testing/validation intent: prove individual components with controlled tests, prove the end-to-end workflow from natural-language query to visual output and validate with synthetic fixtures before relying on live YouTube topics.

## Critical implementation rules

## Documentation

Whenever new code is generated, it should include documentation when the function, class, module, or component is part of the public interface, contains non-trivial logic, has side effects, or may be reused in other parts of the system.

```py
"""
<description>.

Args:
    <name> (<type>): <description>.
    .
    .
    .
Returns:
    <type>: <description>.
"""
```

> Kind of a Google Style.

For JavaScript functions:

```js
/**
 * <Description>.
 *
 * @param {<type>} <name>: <description>.
 * .
 * .
 * .
 * @returns {<type>}: <description>.
 * @throws {<type>} <description>.
 */
```

Descriptions should start with a lowercase letter unless the first word is a proper noun, acronym, or code identifier.

Documentation should focus on intent, inputs, outputs, side effects, error cases and any behavior that is not immediately obvious from the code.

### Language-specific rules

- Python backend files should use `from __future__ import annotations` when adding new modules, matching the current `src/api` pattern.

- Keep Python modules import-safe: no database queries, network calls, file writes, secret generation or environment mutation at import time.

- Backend helper functions should have explicit return types, especially settings/env helpers, serializers, services and view utilities.

- Keep backend configuration helpers small, typed and testable; environment parsing belongs in explicit helper functions like `env_bool`, `env_list` and `build_database_config`.

- Environment helpers should fail clearly for invalid required values, especially database-related configuration.

- Do not hardcode secrets, database credentials, backend URLs or API keys in code; read them from environment variables or centralized config helpers.

- Safe defaults are allowed only for non-secret local development values. Production-required secrets should fail loudly if missing.

- For Django settings, use `pathlib.Path` for filesystem paths and keep database selection environment-driven.

- Django settings must not contain business logic. Keep views thin and move reusable behavior into named helper/service functions that Brandon can trace.

- Django model changes require migrations and must be validated against Docker Compose PostgreSQL; never rely on SQLite-specific behavior for model, query, transaction or constraint logic.

- TypeScript frontend code uses ES modules, React JSX transform and Vite bundler resolution.

- TypeScript config has `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`, `verbatimModuleSyntax`, `moduleDetection: "force"` and `noEmit`; agents must keep code clean enough for `npm run build`.

- With `verbatimModuleSyntax`, use `import type` and `export type` for type-only imports/exports.

- Preserve existing frontend import style in the local file/module; do not broadly introduce extensioned imports unless the local config and surrounding code already support them.

- Prefer named React components with nearby typed props definitions over clever generic component patterns.

- Frontend API calls should centralize base URL/env parsing; do not hardcode backend URLs inside components.

- Avoid Python `Any` and TypeScript `any` unless there is a short justification. Type external API/backend payloads at the boundary and narrow from there.

- Do not change Python or TypeScript compiler/linter strictness as part of feature work unless the story is specifically about tooling migration.

- Prefer explicit, beginner-readable code over clever abstractions in both Python and TypeScript.

- Do not introduce new framework patterns without documenting why.

- Beginner-facing implementation docs belong in `docs/project-understanding/`. Keep this learning layer separate from formal thesis prose and from terse developer reference docs.

- Use this base structure for `docs/project-understanding/`:
    - `index.md`: navigation, reading order and links to each story explanation.

    - `glossary.md`: beginner-friendly definitions of recurring technical terms.

    - `commands.md`: reusable commands with plain-language explanations of what each command does and when to run it.

    - One story-specific file per completed and reviewed story, named with a two-digit prefix and plain title, for example `01-local-backend-and-database.md`.

- After each implemented and reviewed story, update `docs/project-understanding/` with changed files, why they changed, how they connect, commands, manual checks, common errors and key concepts.

- Story-specific understanding docs should explain the final reviewed implementation, not an earlier draft. Create or update them after code review findings have been fixed.
