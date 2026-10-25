---
title: 'Let researchers log in with a local account'
type: 'feature'
ticket: ''
created: '2026-10-24'
status: 'built'
baseline_revision: 'api a26ed40a759614b61114581616c682938f5e58f2 (feature/US-042 from develop); ui 0f5a87a38bbd683097ca00c71664fe051e3452ba (feature/US-042 from develop); thesis 4fcece07cdc2003bd78f47e316890e09a3095d1e (main)'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** US-042. The app has owner-scoped projects but no login: every unauthenticated request is attributed to one fallback user, so researchers sharing a deployment are the same user. The advisor ruled the tool's own account system is enough; no Polarizómetro account sharing.

**Approach:** Django's built-in auth with DRF session authentication. An administrator creates accounts; the UI logs in and out through three small API endpoints; project endpoints reject anonymous requests unless a local-owner fallback setting is on.

## Boundaries & Constraints

**Always:** session auth only (`SessionAuthentication`, no Basic: its `WWW-Authenticate` 401 opens the browser's own login dialog); the anonymous gate lives in `resolve_project_owner`, the one function every project view routes through; login POST is CSRF-protected even though the caller is anonymous; unsafe UI requests send `X-CSRFToken` read from the cookie at request time (Django rotates it on login); error text never says which of username or password was wrong.

**Decisions:** the local-owner fallback is off by default in code and in Compose (human, 2026-10-24); a researcher runs `createsuperuser` once, or sets `OPENTUBE_LOCAL_OWNER_FALLBACK=true` to keep the old behavior. The plan is kept whole at about 2,200 tokens (human, 2026-10-24).

**Never:** self-registration, password reset, roles or sharing between users, login rate limiting, re-login prompt on mid-session expiry (a reload shows the login), Polarizómetro/SSO, CORS or cross-origin cookies, a new dependency, thesis prose edits.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Session, anonymous, fallback off | `GET /api/auth/session/` | 200 `{"username": null, "authenticated": false}`, `csrftoken` cookie set | — |
| Session, anonymous, fallback on | same | 200 `{"username": "<fallback>", "authenticated": false}` | — |
| Login ok | `POST /api/auth/login/` valid credentials + CSRF | 200 `{"username", "authenticated": true}`, session cookie | — |
| Login bad | wrong password, unknown user, inactive user, blank fields | 400 `{"detail": "Invalid username or password."}` | no session created |
| Login without CSRF token | `enforce_csrf_checks` client | 403 | — |
| Logout | authenticated POST + CSRF | 204, session ended | anonymous logout → 204 too |
| Project API, anonymous, fallback off | `GET /api/projects/` | 403 | UI shows login screen on load |
| Project API, logged in | user A | only A's projects; B's project → 404 | — |
| Health | anonymous | 200 regardless of fallback | — |

</frozen-after-approval>

## Code Map

- `src/api/opentube_insights_api/settings.py` -- `REST_FRAMEWORK` has only renderers/parsers (DRF default auth = Session+Basic, `AllowAny`); add `DEFAULT_AUTHENTICATION_CLASSES`; read the fallback flag with `env_bool`. `CsrfViewMiddleware`, sessions, admin already installed.
- `src/api/core/views.py` -- `default_owner_username` (reads `os.environ`, keep), `resolve_project_owner` (only caller: `ProjectOwnerMixin.get_owner`; 12 project views use it), `health` (`@api_view`, must stay open). Add the three auth views here.
- `src/api/core/urls.py` -- routes under `api/`; add `auth/session/`, `auth/login/`, `auth/logout/`. `admin/` is already mounted at the root URLconf.
- `src/api/core/tests/test_views.py` -- `ResearchProjectApiTests`: the only 2 tests relying on the fallback (`test_create_project_uses_default_owner_for_local_development`, `test_duplicate_project_name_returns_validation_error`). Every other API test uses `force_authenticate`, which skips CSRF.
- `src/api/README.md` -- line ~125 ("Until an authentication story adds sign-in…") and the `OPENTUBE_DEFAULT_OWNER_USERNAME` entry under Environment variables.
- `src/ui/src/apiClient.ts` -- private `request()` is the only `fetch`; wrappers set their own POST headers; errors are plain `Error` with status in the message. Add CSRF header here, once.
- `src/ui/src/App.tsx` -- owns top-level state and the mount-time project-list effect; render a login screen instead of the layout until a session exists.
- `src/ui/src/AppHeader.tsx` -- `.header-actions` holds the status pill and theme toggle; put "signed in as" and Log out there.
- `src/ui/tests/*.test.ts` -- pure `.ts` only, `globalThis.fetch` swapped by hand per file (see `projectApi.test.ts`); no component rendering.
- Same-origin already: nginx proxies `/api/`, Vite proxies `VITE_API_BASE_URL`; no CORS work.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/opentube_insights_api/settings.py` -- add `DEFAULT_AUTHENTICATION_CLASSES: [SessionAuthentication]` and `LOCAL_OWNER_FALLBACK = env_bool("OPENTUBE_LOCAL_OWNER_FALLBACK", False)` with a comment -- one switch, read once.
- [x] `src/api/core/views.py` -- `resolve_project_owner` raises `NotAuthenticated` when anonymous and the fallback is off; add `session` (GET, `ensure_csrf_cookie`), `log_in` (POST, `csrf_protect`, `authenticate` + `login`), `log_out` (POST, `logout`, 204) -- single gate, Django's own auth functions.
- [x] `src/api/core/urls.py` -- the three routes, named `auth-session`, `auth-login`, `auth-logout`.
- [x] `src/api/core/tests/test_auth.py` -- new; every I/O matrix row, login CSRF with `APIClient(enforce_csrf_checks=True)`; update the 2 fallback tests in `test_views.py` with `override_settings(LOCAL_OWNER_FALLBACK=True)`.
- [x] `src/api/README.md` -- replace the "until an authentication story" sentence; document the flag, `python manage.py createsuperuser`, and that existing projects stay with the fallback user unless an account is created with that username.
- [x] `src/ui/src/apiClient.ts` -- exported `csrfToken(cookie: string): string | null`; `request()` adds `X-CSRFToken` for non-GET when `document` exists; add `getSession`, `logIn`, `logOut` wrappers and a `SessionState` type, JSDoc lowercase.
- [x] `src/ui/src/LoginScreen.tsx` -- new; username/password form, pending state, `form-error` message on failure.
- [x] `src/ui/src/App.tsx` -- load the session on mount; while `username` is null render `LoginScreen`, else the layout; start the project-list effect only with a session.
- [x] `src/ui/src/AppHeader.tsx` -- when `authenticated`, show the username and a Log out button that calls `logOut` then reloads the page.
- [x] `src/ui/tests/authApi.test.ts` -- new; `csrfToken` parsing, the three wrappers' requests, CSRF header present on POST and absent on GET.
- [x] `src/docker-compose.yml`, `src/.env.example`, `src/api/.env.example` -- pass `OPENTUBE_LOCAL_OWNER_FALLBACK` with a blank default (blank reads as off) and document it (thesis-repo commit for the first two).

**Acceptance Criteria:**
- Given fallback off and no account, when the UI loads, then only the login screen shows and no project request is sent.
- Given an admin-created account, when the researcher logs in, creates a project and logs out, then the project survives, is owned by that account and the login screen returns.
- Given two accounts, when each logs in, then neither sees the other's projects in the UI.

## Implementation Notes

- 2026-10-24: the human approved this plan for implementation by an agent ("Approve and continue"); write the code, do not stop at guidance.

## Plan Change Log

## Review Triage Log

### Pass 1 (quick, 2026-10-24): high 1, medium 3, low 1, false 0, maybe-false 0

| # | Verdict | Route | Finding and evidence |
|---|---------|-------|----------------------|
| 1 | high | patch | CSRF origin check rejects login and every logged-in write behind both proxies: nginx `/api/` sends `Host $host` (port dropped) and Vite `changeOrigin: true` rewrites Host, so `Origin` never equals `scheme://get_host()` (`django/middleware/csrf.py` `_origin_verified`). Reproduced with the test client: Host `localhost` + Origin `http://localhost:8080` → 403; Host `127.0.0.1:8000` + Origin `http://localhost:5173` → 403; matching Host → 400. Fix: forward the browser's host (`$http_host`, `changeOrigin: false`). |
| 2 | medium | patch | `App.tsx` renders `LoginScreen` when `getSession` failed; no `csrftoken` cookie was set, so every submit is a 403 until a reload, and with the fallback on there is nothing to log in to. Fix: on a session error show the message and a retry, not the form. |
| 3 | medium | patch | `src/api/README.md` and both `.env.example` comments say to create every researcher with `createsuperuser`; `core/admin.py` registers projects, runs and comments, so a superuser researcher browses others' data at `/admin/`. Fix: one superuser for the administrator, researchers as plain users from the admin's Add user page. |
| 4 | low | patch | `src/api/README.md` says all three endpoints are CSRF-protected for unsafe methods; anonymous `log_out` is not (`test_anonymous_logout_is_a_no_op`). Direct text correction. |
| 5 | medium | patch | `src/README.md` (thesis repo) still calls `OPENTUBE_DEFAULT_OWNER_USERNAME` the fallback for unauthenticated requests and omits `OPENTUBE_LOCAL_OWNER_FALLBACK` and account creation under Compose. Fix: document both and `docker compose exec api python manage.py createsuperuser`. |

## Design Notes

`session` returns the effective owner so the UI makes one decision: `username` null → login screen. With the fallback on it returns the fallback name and `authenticated: false`, so no Log out button shows. Logout reloads the page instead of resetting every section's state by hand.

Login uses `csrf_protect` because DRF only enforces CSRF for already-authenticated sessions; without it a third-party page could log a browser into the attacker's account.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test` against Compose PostgreSQL -- expected: OK
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: No changes detected
- `cd src/ui && npm test && npm run build` -- expected: tests pass, `tsc -b` clean
- `curl -i http://127.0.0.1:8000/api/projects/` with fallback off -- expected: 403

**Manual checks:**
- In the browser via Compose (port 8080): login screen, log in, create a project, log out, log in as a second account, project not visible.
