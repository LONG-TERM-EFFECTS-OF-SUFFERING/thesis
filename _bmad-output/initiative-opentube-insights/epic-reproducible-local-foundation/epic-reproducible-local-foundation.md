---
type: epic
title: "The app runs locally in a reproducible environment"
parent: initiative-opentube-insights
covers: [US-001, US-002, US-003]
after: []
assignee: ""
status: in-progress
risk: low
estimate: ""
estimate_basis: entries
created: 2026-10-02
---

# The app runs locally in a reproducible environment

## Description

Docker Compose brings up the backend, database, frontend and a production-style front door on a clean machine, using documented environment variables, so the thesis project can be installed and evaluated consistently by someone who did not build it.

## Outcome

Anyone with Docker can start every service and run migrations from the documented commands alone; the signal is a clean-machine bring-up with no undocumented step.

## Requirements

Transcribed from `docs/product_backlog.md`, each line keeping its `US-0NN` id so entries cite the same ids the thesis uses.

- US-001: Docker backend and database services — Docker Compose starts Django/DRF and PostgreSQL; backend environment variables are documented; migrations can run locally. (docs/product_backlog.md, User stories, priority must)
- US-002: Docker frontend service — Docker Compose starts the React/Vite frontend; frontend can call the backend URL through environment configuration. (docs/product_backlog.md, User stories, priority must)
- US-003: Nginx and Gunicorn-ready local wiring — Gunicorn startup is configured; Nginx reverse proxy configuration exists or is clearly documented; minimal setup steps are written. (docs/product_backlog.md, User stories, priority must)

## Done when

1. Docker Compose starts the API, PostgreSQL, the frontend and the Nginx front door from one command.
2. Every environment variable the services read is listed in an `.env.example` and documented.
3. Migrations run against Compose PostgreSQL, not only SQLite.
4. Gunicorn and the reverse proxy configuration exist and the setup steps are written down.

## Boundaries

Local service orchestration and the environment surface. Not application behaviour, not deployment to a remote host.

## References

- parent — ../initiative-opentube-insights.md, section Requirements
- backlog — ../../../docs/product_backlog.md, row EPIC-001 and its user-story rows
- sprint plan — ../../../docs/sprint_planning.md
- project context — ../../project-context.md

## Notes

- Assumption: Done when was written from the backlog's epic row and its stories' done-when column; v6 had no epics.md stating epic-level checks. Confirm or correct it.
