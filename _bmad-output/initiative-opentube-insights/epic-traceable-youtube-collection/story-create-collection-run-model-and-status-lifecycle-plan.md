---
title: 'Create collection run model and status lifecycle'
type: 'feature'
ticket: '1'
created: '2026-10-05'
status: 'built'
baseline_revision: 'e15325c9929f13d0d1369d83cc5b34a9673ab1cc'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context:
  - '{project-root}/docs/database_schema.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing records a collection attempt, so a dataset cannot be traced to whether, when and from which saved query it was collected (US-010).

**Approach:** Add a `CollectionRun` model in `core` holding project, saved query, initiating user, status and started/finished timestamps, with a five-state lifecycle enforced by a single transition method that stamps the timestamps, plus database checks for the allowed statuses and time order.

## Boundaries & Constraints

**Always:** Column names, types, nullability and `on_delete` match the `collection_runs` table in `docs/database_schema.md` for the columns this story adds. Table name `collection_runs`. Statuses `pending`, `running`, `completed`, `failed`, `cancelled`, default `pending`. Allowed transitions: `pending → running | cancelled`; `running → completed | failed | cancelled`; the three terminal states allow none. Entering `running` sets `started_at`; entering a terminal state sets `finished_at`. Constraints validated against Compose PostgreSQL.

**Never:** No count, quota, error-message, `requested_comment_limit` or `data_purged_at` columns (US-012, US-040). No effective-parameters storage, endpoint, serializer or UI (US-011). No YouTube calls or request logs (US-013). No check that `project` equals `saved_query.project` in the model — US-011 derives the project from the query. No state-machine library.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New run | create with project and saved query only | `status=pending`, `started_at`/`finished_at` null, UUID id, `created_at` set | No error expected |
| Start | `pending` run, transition to `running` | status saved, `started_at` set, `finished_at` null | No error expected |
| Finish | `running` run, transition to `completed`/`failed`/`cancelled` | status saved, `finished_at` set, ≥ `started_at` | No error expected |
| Cancel before start | `pending` run, transition to `cancelled` | status saved, `finished_at` set, `started_at` stays null | No error expected |
| Illegal transition | `pending → completed`, or any move out of a terminal state | row unchanged in the database | `ValueError` naming both statuses |
| Bad status in DB | create with `status="paused"` | not saved | `IntegrityError` from check constraint |
| Time inversion | `finished_at` earlier than `started_at` | not saved | `IntegrityError` from check constraint |
| Query deleted | saved query deleted after a run used it | run kept, `saved_query` null | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py` -- add `CollectionRun` after `ResearchProject`; copy `ResearchProject`'s idioms: UUID pk, nested `TextChoices`, `db_table`, `CheckConstraint(condition=…)` (Django 6 keyword, not `check=`), `__str__` with docstring.
- `src/api/core/migrations/` -- latest is `0003_rename_savedquery_max_results.py`; generate `0004` with `makemigrations`, do not hand-write.
- `src/api/core/admin.py` -- register like `ResearchProjectAdmin`: list display, status filter, readonly id/timestamps.
- `src/api/core/tests.py` -- add `CollectionRunModelTests(APITestCase)` beside `ResearchProjectModelTests`; reuse its `IntegrityError` + `transaction.atomic()` pattern and `get_user_model().objects.create_user` setup.
- `docs/database_schema.md` `collection_runs` -- source of truth for columns; do not edit (other columns land in later stories).
- Do not touch `serializers.py`, `views.py`, `urls.py` or `src/ui`.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/models.py` -- add `CollectionRun` with `RunStatus` choices, FKs (`project` CASCADE; `saved_query` and `initiated_by_user` SET_NULL, null, `related_name="collection_runs"`), nullable `started_at`/`finished_at`, `created_at` auto_now_add, ordering `-created_at`, two check constraints (allowed status; `finished_at >= started_at` when both present), and a `transition_to(new_status)` method that validates against a class-level allowed-transitions map, stamps the timestamp with `django.utils.timezone.now()`, and saves only the changed fields -- one place owns the lifecycle so US-011/US-012 cannot skip it.
- [x] `src/api/core/migrations/0004_*.py` -- generate with `venv/bin/python manage.py makemigrations core` -- schema for the new table.
- [x] `src/api/core/admin.py` -- register `CollectionRun` -- local inspection, same as the other models.
- [x] `src/api/core/tests.py` -- tests for every I/O matrix row -- the lifecycle and constraints are the story.

**Acceptance Criteria:**
- Given the migrations applied to Compose PostgreSQL, when the test suite runs, then every `CollectionRunModelTests` case passes and both check constraints exist on `collection_runs`.
- Given the illegal-transition test, when the transition-map check in `transition_to` is removed, then that test fails.

## Implementation Notes

- `docs/database_schema.md` lists `saved_query_id` and `initiated_by_user_id` as `null: NO` while their Django field is `SET_NULL, null=True`; implemented as nullable per this plan and the field column. The schema doc's null column should be corrected in a docs commit.
- Verified on Compose PostgreSQL: `DATABASE_ENGINE=postgresql venv/bin/python manage.py test` ran 99 tests OK; removing the transition-map guard fails 18 subtests of the illegal-transition test.
- Human addition after review: `data_purged_at` (nullable `DateTimeField`, named as in `docs/database_schema.md`) added to `CollectionRun` now rather than in US-040, overriding the Never line; folded into migration `0004_collectionrun` and the story commit. Default asserted in the new-run test.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 2, low 2, false 0, maybe-false 0, defer 1.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `transition_to` checks in-memory `self.status`; a stale instance can overwrite a terminal row | medium | patch | Confirmed: `save(update_fields=…)` is unconditional. Fix: conditional `filter(pk, status=old).update(...)`, raise `ValueError` when 0 rows match; test with two instances. |
| Admin `status` editable, bypassing `transition_to` | medium | patch | Confirmed: `status` absent from `readonly_fields`. Fix: add it. |
| `saved_query`/`initiated_by_user` `null=True` without `blank=True`; admin cannot save a run whose query was deleted | low | patch | Confirmed in model. Direct correction: add `blank=True`, regenerate uncommitted `0004`. |
| `ValueError` text uses `!r`, so enum members render as `CollectionRun.RunStatus.X` vs `'x'` for DB-loaded strings | low | patch | Confirmed: `TextChoices` repr differs from `str`. Direct correction: format plain values. |
| `docs/database_schema.md` says `null: NO` for two nullable FKs | low | defer | Pre-existing contradiction inside the doc (its own Django column says `null=True`); thesis-repo docs fix, out of this api diff. |

## Design Notes

A plain `dict[str, frozenset[str]]` on the model is the whole state machine; `transition_to` raises before mutating, so a rejected call leaves the instance and row untouched. Reject the call when `new_status` equals the current status (no self-loops) — the map already does this since no state lists itself.

## Verification

**Commands:**
- `cd src && docker compose up -d db` then `cd src/api && venv/bin/python manage.py test core` against PostgreSQL env -- expected: OK, no failures.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.
