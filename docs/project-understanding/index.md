# Project understanding

This folder is the learning layer for the thesis app. It explains what each implemented story added, how the files connect, what commands to run and what concepts are worth understanding before moving on.

These notes are different from the formal thesis chapters. The thesis explains the academic work. This folder explains the code in beginner-friendly language.

## Reading Order

1. [Glossary](glossary.md).

2. [Commands](commands.md).

3. [01 - Local backend and database](01-local-backend-and-database.md).

4. [02 - Docker frontend service](02-docker-frontend-service.md).

5. [03 - Create research project](03-create-research-project.md).

6. [04 - Save YouTube search query](04-save-youtube-search-query.md).

## Story notes

|                                 file                                 | story  | status |                                                               what it explains                                                                |
| :------------------------------------------------------------------: | :----: | :----: | :-------------------------------------------------------------------------------------------------------------------------------------------: |
| [01-local-backend-and-database.md](01-local-backend-and-database.md) | US-001 |  Done  | Django backend scaffold, SQLite, PostgreSQL, Docker Compose, migrations, environment config, health checks and the `src/` nested-repo layout. |
|       [02-docker-frontend-service.md](02-docker-frontend-service.md)       | US-002 |  Done  | Dockerized React/Vite frontend, Compose `ui` service, Vite proxy, frontend health check, and frontend validation commands. |
|      [03-create-research-project.md](03-create-research-project.md)      | US-004 |  Done  | Research project model, project API, owner fallback, frontend project workspace, and project validation commands.                             |
|      [04-save-youtube-search-query.md](04-save-youtube-search-query.md)      | US-005 |  Done  | Saved-query model, project-scoped query API, owner isolation, manual query form, stale-list protection and saved-query validation commands.                             |

## How to use this folder

- Read the story page after a BMAD story is implemented and reviewed.

- Use [commands.md](commands.md) when you forget what a terminal command does.

- Use [glossary.md](glossary.md) when a repeated term feels fuzzy.

- Update the story page after review fixes so it describes the final reviewed code.

## Documentation rule

After each BMAD story is implemented, reviewed and fixed, add or update one story-specific page in this folder. The page should explain:

- what changed.

- why it was added.

- what each important file does.

- how the files connect.

- what commands to run.

- how to test manually.

- common errors and what they mean.

- beginner concepts to understand before the next story.
