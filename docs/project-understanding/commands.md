# Commands

This page lists reusable commands for the thesis app and explains what each one does.

Run commands from the folder shown in each section. The main thesis repo ignores `src/`, so active API/UI development commands happen inside `src/api`, `src/ui`, or `src`.

## Backend (quick SQLite development)

```bash
cd src/api
python manage.py migrate
```

Runs Django migrations. With the default settings, this uses SQLite and creates or updates `src/api/db.sqlite3`.

```bash
python manage.py runserver 8000
```

Starts the Django development server on port `8000`.

```bash
python manage.py test core
```

Runs the tests in the `core` Django app.

```bash
python manage.py check
```

Runs Django's system checks. This catches common configuration problems.

## Docker compose (reproducible PostgreSQL path)

```bash
cd src
docker compose config
```

Checks whether `src/docker-compose.yml` is valid after environment variables and defaults are resolved.

```bash
docker compose up --build
```

Builds the backend image and starts the database and API containers in the foreground. The terminal shows logs while the services run.

```bash
docker compose up --build -d
```

Builds and starts the containers in the background. The `-d` means detached mode.

```bash
API_HOST_PORT=8001 docker compose up --build
```

Starts the stack with the API exposed on host port `8001` for this one command. Use this when something else is already using port `8000`.

```bash
POSTGRES_HOST_PORT=5433 docker compose up --build
```

Starts the stack with PostgreSQL exposed on host port `5433` for this one command. Use this when something else is already using port `5432`.

```bash
docker compose ps
```

Shows whether the `api` and `db` services are running and which ports are exposed.

```bash
docker compose logs api
docker compose logs db
```

Shows logs for the backend or database container.

```bash
docker compose exec api python manage.py migrate
```

Runs Django migrations inside the API container. This validates the PostgreSQL path because the container uses `DATABASE_ENGINE=postgresql`.

```bash
docker compose exec api python manage.py check
```

Runs Django's system checks inside the API container.

```bash
docker compose exec api python manage.py test core
```

Runs the backend tests inside the API container.

```bash
docker compose exec api python manage.py showmigrations
```

Shows which migrations Django sees and whether they have been applied.

```bash
docker compose exec api python manage.py shell
```

Opens Django's interactive Python shell inside the API container.

```bash
docker compose exec api sh
```

Opens a shell inside the API container. This is useful when you need to inspect files or run several Django commands manually.

```bash
docker compose exec db psql -U opentube_insights -d opentube_insights
```

Opens a PostgreSQL shell inside the database container using the default local development database and user.

```bash
docker compose --env-file api/.env up --build
```

Starts the stack while reading Compose override values from `src/api/.env`.

```bash
docker compose down
```

Stops and removes the running containers. The PostgreSQL data volume remains.

```bash
docker compose down --volumes
```

Stops containers and deletes the PostgreSQL data volume. Use this only when you intentionally want to erase the local Docker database.

## Health check

```bash
curl http://localhost:8000/api/health/
```

Asks the backend health endpoint if the API is running.

Expected response:

```json
{ "status": "ok" }
```

## Frontend Commands

Run these from `src/ui`.

```bash
npm run dev
```

Starts the Vite frontend development server.

```bash
npm run build
```

Runs TypeScript build checks and creates production frontend assets.

```bash
npm run lint
```

Runs ESLint on the frontend source code.
