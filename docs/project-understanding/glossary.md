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

## Docker

Docker runs software inside containers. A container is like a small isolated environment with everything the service needs.

In this project, Docker helps run the backend and PostgreSQL in a reproducible way.

## Docker Compose

Docker Compose starts several containers together using a compose file. In this project, the local development compose file is `src/docker-compose.yml`.

For US-001, Compose starts:

- `db`: PostgreSQL database.

- `api`: Django backend.

## Environment variable

An environment variable is a setting passed to a program from outside the code.

Example:

```text
DATABASE_ENGINE=postgresql
```

This lets the same code use SQLite locally or PostgreSQL in Docker.

## `.env` file

A `.env` file is a local text file that stores environment-variable values for development.

In this project, `src/api/.env.example` is the safe template. You can copy it to `src/api/.env` and edit local values such as ports or database settings. The real `.env` file is ignored by Git.

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

## Nested repository

A nested repository is a Git repository inside another repository's working folder.

In this project, `src/api` and `src/ui` can have their own Git histories while the main thesis repo ignores `src/`. This lets you keep app-development commits separate from thesis/documentation commits.

## Git submodule

A Git submodule is a formal link from one Git repository to a specific commit in another Git repository.

This project is not using submodules for `src/api` or `src/ui`. They are nested repositories, not submodule pointers tracked by the main thesis repo.

## PostgreSQL

PostgreSQL is the main relational database used for reproducible thesis validation. It is the database target for Docker Compose.

SQLite can be useful for quick local development, but PostgreSQL is the database that matters for story validation.

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
