# Commands

This page lists reusable commands for the thesis app and explains what each one does.

Run commands from the folder shown in each section. The main thesis repo tracks shared root Compose files in `src/`, while active API/UI development commands happen inside the nested repositories `src/api` and `src/ui`.

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

## Docker compose (reproducible local stack)

```bash
cd src
docker compose config
```

Checks whether `src/docker-compose.yml` is valid after environment variables and defaults are resolved.

```bash
docker compose up --build
```

Builds the backend and frontend images, then starts the database, API and UI containers in the foreground. The terminal shows logs while the services run.

```bash
docker compose up --build -d
```

Builds and starts the containers in the background. The `-d` means detached mode.

```bash
API_HOST_PORT=8001 docker compose up --build
```

Starts the stack with the API exposed on host port `8001` for this one command. Use this when something else is already using port `8000`.

```bash
UI_HOST_PORT=5174 docker compose up --build
```

Starts the stack with the frontend exposed on host port `5174` for this one command. Use this when something else is already using port `5173`.

```bash
POSTGRES_HOST_PORT=5433 docker compose up --build
```

Starts the stack with PostgreSQL exposed on host port `5433` for this one command. Use this when something else is already using port `5432`.

```bash
docker compose ps
```

Shows whether the `api`, `db` and `ui` services are running and which ports are exposed.

```bash
docker compose logs ui
docker compose logs api
docker compose logs db
```

Shows logs for the frontend, backend or database container.

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
docker compose --env-file .env up --build
```

Starts the stack while reading Compose override values from `src/.env`.

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
curl "http://127.0.0.1:${API_HOST_PORT:-8000}/api/health/"
```

Asks the backend health endpoint if the API is running.

Expected response:

```json
{ "status": "ok" }
```

```bash
curl "http://127.0.0.1:${UI_HOST_PORT:-5173}/api/health/"
```

Asks the backend health endpoint through the Vite frontend proxy.

## Frontend Commands

Run these from `src/ui`.

```bash
npm test
```

Runs the small frontend helper tests.

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
