<!-- bmad:context -->
<!-- Verified 2026-10-02 against df91dcf. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## thesis — OpenTube Insights

Undergraduate thesis: a web application that collects, processes and visualizes YouTube data for reproducible academic research, plus the LaTeX document reporting it. Django REST Framework and PostgreSQL in `src/api`, React and Vite in `src/ui`, LaTeX at the repo root. Planning is a BMad ticket tree under `_bmad-output/initiative-opentube-insights/`; the numbered requirement source is `docs/product_backlog.md`, and `docs/project-understanding/` explains each shipped story in beginner-facing terms.

## Policy

- `src/api` and `src/ui` are nested git repositories, not submodules — commit app code from inside those folders, never from the thesis repo.
- Never add API, UI, virtualenv or node files to the thesis repo; it tracks `content/`, `docs/`, `_bmad-output/`, LaTeX tooling, `src/docker-compose.yml` and `src/.env.example` only.
- Never hardcode secrets, database credentials, backend URLs or API keys — read them through the env helpers in `src/api/opentube_insights_api/settings.py`.
- A production-required secret has no default and must fail loudly; safe defaults are for non-secret local values only.
- Keep thesis prose commits separate from app code commits.
- Branch `feature/US-XXX` using the backlog id. Conventional Commits. Add `TG-<ref> #done` in the main repository when a commit completes a user story.
- Taiga is used at user-story level only — never create Taiga tasks under a story.

## Where things are

- Next story to build: `uv run _bmad/method/scripts/tickets.py --project-root . next`; a ticket resolves with `tickets.py find _bmad-output/initiative-opentube-insights <ref>`.
- Requirement ids are the `US-0NN` rows in `docs/product_backlog.md`; epics and entries cite them in `covers`.
- Thesis brief, stack rationale, docstring templates and Taiga operating detail: `_bmad-output/project-context.md`.
- After a story is implemented and reviewed, add or update its page in `docs/project-understanding/` and link it from that folder's `index.md` — after review fixes land, not before.

## Running and verifying

- Backend tests: `cd src/api && venv/bin/python manage.py test`. A bare `python manage.py test` misses the virtualenv and its dependencies.
- Before a story is done, `venv/bin/python manage.py makemigrations --check --dry-run` must report no changes.
- Frontend: `cd src/ui && npm test` runs `node --test`. `npm run build` also typechecks with `tsc -b`, which `npm test` does not.
- Validate models, migrations and constraints against Compose PostgreSQL (`cd src && docker compose up -d db`), never SQLite — SQLite is for fast local iteration only and its constraint behavior differs.
- No test may reach `api.openai.com` or `googleapis.com`; inject a transport in backend tests and stub `fetch` in frontend tests. A test needing a live API key is a broken test.
- Thesis document: `make check` runs format-check, chktex and the build; output goes to `build/`. `pdflatex` needs `-shell-escape` for minted, already set in `.latexmkrc`.
- Declared versions, read from the files that declare them: Python 3.14 (`src/api/Dockerfile`), Django 6.0.5 / DRF 3.17.1 / psycopg[binary] 3.3.4 (`src/api/requirements.txt`), React 19.2.6 / Vite 8.0.12 / TypeScript 6.0.2 (`src/ui/package.json`). Never upgrade or substitute without an explicit migration task.

## Conventions that differ from defaults

- New Python modules start with `from __future__ import annotations` and stay import-safe: no env reads, database queries, network calls or file writes at import time.
- `verbatimModuleSyntax` is on — use `import type` for type-only TypeScript imports.
- Avoid `Any` and `any`. Type an external payload at the boundary and narrow from there; where one is unavoidable, justify it in a comment.
- JSDoc on exported TypeScript functions, with descriptions starting lowercase unless the first word is a proper noun, acronym or identifier. The Python docstring convention is in the user's global agent config; templates for both are in `_bmad-output/project-context.md`.
- Reach for existing project code, then a platform feature, then an installed dependency, before adding a library; state what a new dependency solves and why local code would be worse.
- In `src/api/README.md` and `src/ui/README.md`, write paths as if that folder were the repository root — `manage.py`, not `src/api/manage.py`.
- Do not change Python or TypeScript compiler or linter strictness as part of feature work.

## Known pitfalls

- A late or superseded async response overwrites newer React state. Patched in the US-005 review and again in US-006. Guard every fetch in `src/ui/src/App.tsx` with an `AbortController` held in a ref plus a controller-identity check before writing state.
- Tests that pass for the wrong reason have shipped twice: an assertion on a substring the prompt already contained, and a transport faked in every test so the real HTTP path never ran. Delete the behavior and confirm the test fails before trusting it.
- `isinstance(True, int)` is `True` in Python, so a bool slips through integer range checks on untrusted model or API output. Reject `bool` explicitly.

<!-- /bmad:context -->
