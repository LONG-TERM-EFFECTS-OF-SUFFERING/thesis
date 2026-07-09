# Glossary

This glossary explains recurring terms in the thesis app in plain language.

## API

An API is a set of rules for one program to talk to another. In this project, the frontend will talk to the backend API to ask for data or send user actions.

## Backend

The backend is the server-side part of the app. It handles data, database access, API routes and business logic.

## Django

Django is the Python web framework used for the backend. It provides tools for URL routing, settings, database models, migrations, admin pages and security features.

## Django REST Framework

Django REST Framework, often shortened to DRF, adds API-focused tools on top of Django. It helps return JSON responses and will later help with serializers and API views.

## Serializer

A serializer converts between Django/Python data and JSON. It also validates incoming JSON before the backend saves it.

In US-004, `ResearchProjectSerializer` makes `id`, owner and timestamp fields read-only so the browser cannot choose them.

## Model

A model is a Python class that describes a database table. Django uses models to create queries, validate field types and generate migrations.

In US-004, `ResearchProject` maps to the `research_projects` table.

## Constraint

A constraint is a database-level rule. It protects important conditions even if a bug bypasses higher-level validation.

In US-004, constraints prevent duplicate project names for the same owner and reject unsupported project statuses.

## Docker

Docker runs software inside containers. A container is like a small isolated environment with everything the service needs.

In this project, Docker helps run the frontend, backend and PostgreSQL in a reproducible way.

## Docker Compose

Docker Compose starts several containers together using a compose file. In this project, the local development compose file is `src/docker-compose.yml`.

After US-002, Compose starts:

- `db`: PostgreSQL database.

- `api`: Django backend.

- `ui`: React/Vite frontend.

## Environment variable

An environment variable is a setting passed to a program from outside the code.

Example:

```text
DATABASE_ENGINE=postgresql
```

This lets the same code use SQLite locally or PostgreSQL in Docker.

## `.env` file

A `.env` file is a local text file that stores environment-variable values for development.

In this project, `src/.env.example` is the safe template for Docker Compose port and frontend proxy overrides. `src/api/.env.example` is the safe template for backend-local settings. Real `.env` files are ignored by Git.

## Health endpoint

A health endpoint is a tiny API route used to confirm the app is alive.

In this project:

```text
GET /api/health/
```

returns:

```json
{ "status": "ok" }
```

## Migration

A migration is Django's way of applying database structure changes.

Even before custom models exist, Django has built-in migrations for users, sessions, admin tables and permissions.

## UUID

A UUID is a long unique identifier, such as `00000000-0000-0000-0000-000000000000`.

Research projects use UUIDs as public record identifiers instead of simple increasing numbers.

## Nested repository

A nested repository is a Git repository inside another repository's working folder.

In this project, `src/api` and `src/ui` can have their own Git histories while the main thesis repo tracks only shared root Compose files under `src/`. This lets you keep app-development commits separate from thesis/documentation commits without losing the local orchestration files.

## Git submodule

A Git submodule is a formal link from one Git repository to a specific commit in another Git repository.

This project is not using submodules for `src/api` or `src/ui`. They are nested repositories, not submodule pointers tracked by the main thesis repo.

## PostgreSQL

PostgreSQL is the main relational database used for reproducible thesis validation. It is the database target for Docker Compose.

SQLite can be useful for quick local development, but PostgreSQL is the database that matters for story validation.

## Research project

A research project is the workspace for one study topic. Saved queries, collection runs and later results will belong to a project so data remains organized by research context.

## Saved query

A saved query is reusable YouTube search criteria stored inside a research project. It records the search term, optional filters and structured parameters before any collection run is started.

## Fallback owner

The fallback owner is a local development user used before sign-in exists. Unauthenticated project API requests use `OPENTUBE_DEFAULT_OWNER_USERNAME`, defaulting to `local-researcher`.

## `python-dotenv`

`python-dotenv` is a small Python package that reads `.env` files. In this project, Django uses it to read local development settings from `src/api/.env`.

## SQLite

SQLite is a small database stored in a local file. It is convenient because it does not need a separate database server.

In this project, SQLite is only the quick development path. It should not be used to make final claims about database behavior.

## `manage.py`

`manage.py` is Django's command runner. It lets you run commands such as:

```bash
python manage.py migrate
python manage.py test
python manage.py runserver
```

## `settings.py`

`settings.py` configures the Django backend. It tells Django which apps are installed, how the database is selected, which URL file to use and other project-level settings.

## `urls.py`

`urls.py` maps URLs to Python code.

Example:

```text
/api/health/ -> core.views.health
```

## Virtual environment

A virtual environment, or venv, is an isolated Python package environment. It lets this project install Django without affecting the whole computer.

In this repo, the backend venv is at:

```text
src/api/venv
```
