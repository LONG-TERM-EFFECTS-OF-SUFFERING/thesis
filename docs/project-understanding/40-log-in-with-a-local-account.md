# 40 - Log in with a local account

Story: US-042, Log in with a local account.

Status note: this document describes the US-042 implementation **after** the code review of 2026-10-24 and the fixes that followed it.

## What this story added

Researchers now log in. Before, every request without a session was attributed to one fallback user (`local-researcher`), so everyone using the app was the same person. Now:

- the UI opens on a **login screen** until there is a session;
- the header shows **Signed in as …** and a **Log out** button;
- every project endpoint answers `403` to an anonymous request;
- an administrator creates the accounts. There is no sign-up page.

The advisor ruled that the tool's own account system is enough for the thesis: no shared accounts with the Polarizómetro.

## Why this matters

Owner isolation already existed in the data: every project has an owner, and a project of another owner answers `404` (page 03). Without a login, that isolation had no one to isolate. With accounts, two researchers on one deployment see only their own projects, queries, runs and results.

## Key concept: session authentication

Django already ships everything a login needs: the `auth_user` table, password hashing, `authenticate` (check a username and password), `login` (start a session) and `logout`. Nothing new was installed.

After `login`, Django sets a `sessionid` cookie. The browser sends it on every request, and Django turns it back into `request.user`. DRF reads that through `SessionAuthentication`, now the only authentication class in `REST_FRAMEWORK`.

DRF's default also included **Basic** authentication. It was removed on purpose: Basic answers an anonymous request with `401` plus a `WWW-Authenticate` header, which makes the browser pop up its own grey login dialog over the app. With session only, the answer is a plain `403`.

## Key concept: one gate

Every project view gets its owner from `resolve_project_owner` in `core/views.py` (through `ProjectOwnerMixin`). That function is the single place the rule lives:

- logged in → that user;
- anonymous and `OPENTUBE_LOCAL_OWNER_FALLBACK` on → the fallback user, as before US-042;
- anonymous and the fallback off (the default) → `NotAuthenticated`, which DRF turns into `403`.

`/api/health/` does not go through it, so it stays open.

## Key concept: CSRF

A logged-in browser sends its `sessionid` cookie to the API automatically, even when some other website triggers the request. CSRF protection stops that: an unsafe request (POST, PATCH, DELETE) must also carry a token that only pages of the app itself can read.

How it works here:

1. `GET /api/auth/session/` sets a `csrftoken` cookie (`ensure_csrf_cookie`).
2. The UI's shared `request()` helper in `apiClient.ts` copies that cookie into an `X-CSRFToken` header on every request that is not a GET.
3. Django compares the two.

Three details matter:

- **Login is checked too.** DRF only checks CSRF for a session that is already logged in. The login view adds `csrf_protect` itself; otherwise another site could log your browser into *its* account and watch what you collect.
- **Decorator order.** `csrf_protect` sits *under* `@api_view`. DRF marks its views as CSRF-exempt, so a decorator above it would never run its check. A test fails if the order is swapped.
- **The token changes on login.** Django rotates it, so the UI reads the cookie at request time instead of keeping a copy.

## Key concept: the origin check behind a proxy

Django also compares the browser's `Origin` header (`http://localhost:8080`) with the host the request arrived at. Both proxies used to change that host:

- nginx sent `Host $host`, which drops the port (`localhost`);
- Vite's `changeOrigin: true` replaced it with the API's own address.

So every login through port 8080 or 5173 was rejected with `403` before the password was even checked. The tests did not catch it, because Django's test client sends no `Origin`. The review found it. The fix forwards the browser's host: `$http_host` in `src/nginx/default.conf`, `changeOrigin: false` in `src/ui/vite.config.ts`.

## File-by-file explanation

### `src/api/opentube_insights_api/settings.py`

`DEFAULT_AUTHENTICATION_CLASSES` is session only, and `LOCAL_OWNER_FALLBACK` is read once from `OPENTUBE_LOCAL_OWNER_FALLBACK` (blank or missing means off).

### `src/api/core/views.py` and `core/urls.py`

The gate in `resolve_project_owner`, and three views:

| endpoint | method | answer |
| :------- | :----- | :----- |
| `/api/auth/session/` | GET | `{"username", "authenticated"}`, plus the `csrftoken` cookie |
| `/api/auth/login/` | POST | the session, or `400 {"detail": "Invalid username or password."}` |
| `/api/auth/logout/` | POST | `204` |

`username` is `null` when nobody is logged in. With the fallback on, it names the fallback user and `authenticated` stays `false`, so the UI shows no Log out button. A wrong password, an unknown user, an inactive user and blank fields all get the same message, so the answer never says which part was wrong.

### `src/api/core/tests/test_auth.py`

One test per row of the plan's input/output table, with `APIClient(enforce_csrf_checks=True)` so CSRF is really checked. Most other API tests use `force_authenticate`, which skips CSRF.

### `src/ui/src/apiClient.ts`

`csrfToken` (reads the cookie), the header added inside `request()`, and `getSession`, `logIn`, `logOut`.

### `src/ui/src/App.tsx`, `LoginScreen.tsx`, `AppHeader.tsx`

`App` loads the session on start. Loading shows nothing, no username shows `LoginScreen`, and a session that failed to load shows the error with a **Retry** button (without a session answer there is no CSRF cookie to log in with). The project list loads only once there is a username. Log out reloads the page, which clears every section's state at once.

### `src/nginx/default.conf`, `src/ui/vite.config.ts`, `src/docker-compose.yml`

The host forwarding above, and the flag passed to the `api` container.

## How the pieces connect

```text
open the app -> GET /api/auth/session/ -> csrftoken cookie
  username null -> LoginScreen -> POST /api/auth/login/ (X-CSRFToken) -> sessionid cookie
  -> GET /api/projects/ -> resolve_project_owner -> request.user -> only their projects
Log out -> POST /api/auth/logout/ -> reload -> LoginScreen
```

## Commands

```bash
cd src/api
venv/bin/python manage.py test core.tests.test_auth
venv/bin/python manage.py createsuperuser
cd ../ui
npm test
npm run build
```

Under Compose: `cd src && docker compose exec api python manage.py createsuperuser`.

Passing looks like `OK` for the auth tests, and `pass 111` and `✓ built` for the UI.

## How to test manually

1. `cd src && docker compose up -d --build`, then create the administrator with `docker compose exec api python manage.py createsuperuser`.

2. Open `http://127.0.0.1:8000/admin/`, log in, and use **Users → Add user** to create two researchers, `ana` and `beto`. Leave **Staff** and **Superuser** unticked.

3. Open `http://localhost:8080`. Only the login screen shows. Log in as `ana`, create a project, and check the header says **Signed in as ana**.

4. Click **Log out**, then log in as `beto`. Ana's project is not listed.

5. In a terminal, `curl -i http://localhost:8080/api/projects/` answers `403`.

## Common errors

- **Every project request is `403` after updating.** Login is now required. Create an account, or set `OPENTUBE_LOCAL_OWNER_FALLBACK=true` in `src/.env` for a single-user machine.

- **My old projects disappeared.** They belong to the fallback user, `local-researcher`. Create an account with exactly that username to log in as it, or turn the fallback on.

- **"Login failed. 403."** The CSRF check failed. Reload the page so the session request sets a fresh cookie. If it persists behind your own proxy, the proxy is changing the `Host` header (see the origin check above).

- **"Invalid username or password."** One of the two is wrong, or the account is inactive. The message deliberately does not say which.

- **A researcher can see everyone's data in `/admin/`.** That account is a superuser. Researchers must be plain users; only the administrator needs `createsuperuser`.

## Known gaps

- No sign-up page, no password reset and no roles or sharing between users.
- No limit on login attempts.
- A session that expires mid-use shows errors in each section until a reload brings the login screen back.
- The admin site is reachable only on the API port (8000), because nginx forwards just `/api/` to the API.
