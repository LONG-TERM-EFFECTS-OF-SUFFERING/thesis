---
title: 'Store collection run counts, quota, timestamps and errors'
type: 'feature'
ticket: '3'
created: '2026-10-05'
status: 'built'
baseline_revision: 'fb1296703deab8c69b2d8a263ff81e2d06cf5caf'
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

**Problem:** A run records only its status and start and finish times. It cannot say how many requests it made, how much quota it spent, how many items it gathered, or why it failed (US-012).

**Approach:** Add the counter columns and `error_message` to `CollectionRun`, as `docs/database_schema.md` defines them. `call_youtube` keeps the request and quota totals current. `transition_to` records the error message when a run fails. The run's API response exposes the new fields.

## Boundaries & Constraints

**Always:** Columns match `collection_runs` in `docs/database_schema.md`: `total_api_requests`, `total_quota_units`, `total_videos_discovered`, `total_videos_collected`, `total_comments_collected` and `total_replies_collected`, each `PositiveIntegerField(default=0)`, plus `error_message` as `TextField(null=True, blank=True)`.
- The totals are updated with `F()` expressions in a single `UPDATE`, never with read-modify-write in Python.
- `transition_to` stays the only way to change status. The existing timestamps already meet "timestamps".
- The new fields are read-only in `CollectionRunSerializer` and in the admin.
- Validated on Compose PostgreSQL.

**Decisions:** `total_api_requests` and `total_quota_units` are stored columns, as in the schema doc, kept current only by `call_youtube`. Entering `failed` requires a non-empty `error_message` (else `ValueError`), and passing `error_message` with any other target status raises `ValueError`.

**Never:** No writer for the video and comment counters: US-015 and the comment stories increment them. No `requested_comment_limit` (comment stories). No UI change: the existing `isCollectionRun` ignores extra fields. No run detail page (US-014). No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New run | created by the start endpoint | every total 0, `error_message` null; all appear in the 201 body | No error expected |
| Successful call | `call_youtube` `search.list` then `videos.list` | `total_api_requests` 2, `total_quota_units` 101; the caller's `run` instance reflects them | No error expected |
| Failed call | `call_youtube` gets HTTP 403 | request and quota totals still incremented (YouTube charges failed calls) | `YouTubeApiError` as before |
| Rejected call | unknown endpoint, `key` param, `bool` value | totals unchanged | `ValueError` as before |
| Fail with message | `running` run, `transition_to("failed", error_message="quotaExceeded on search.list")` | status `failed`, `finished_at` set, message stored | No error expected |
| Fail without message | `transition_to("failed")` or `error_message=""` | row unchanged | `ValueError` |
| Message on another status | `transition_to("completed", error_message="x")` | row unchanged | `ValueError` |
| Illegal move | any existing illegal transition, with or without a message | row unchanged; message names both statuses, as today | `ValueError` |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py` `CollectionRun`: add the seven fields after `finished_at`. Extend `transition_to(new_status, *, error_message=None)` so the message joins the existing `changes` dict, which keeps the compare-and-set `UPDATE` atomic. Check legality first, so illegal-move messages stay as they are. Generate `0007` with `makemigrations core`.
- `src/api/core/youtube_client.py` `call_youtube`: right after `ApiRequestLog.objects.create`, run `CollectionRun.objects.filter(pk=run.pk).update(total_api_requests=F(...) + 1, total_quota_units=F(...) + cost)`, then `run.refresh_from_db(fields=[...])`. Nothing changes before the validation `ValueError`s.
- `src/api/core/serializers.py` `CollectionRunSerializer`: add the seven fields to `fields` (already read-only via `read_only_fields = fields`).
- `src/api/core/admin.py` `CollectionRunAdmin`: add the seven fields to `readonly_fields`.
- `src/api/core/tests.py`: extend `CollectionRunModelTests` (defaults, fail with message, message rejected elsewhere), `CallYouTubeTests` (totals on success, failure and rejection) and `CollectionRunStartApiTests` (fields in the 201 body). The existing terminal-transition loop around line 321 moves to `failed` without a message; pass one for `failed` there.
- `docs/database_schema.md`: no change. The columns are already documented.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/models.py` + migration `0007`: fields and the `transition_to` error message.
- [x] `src/api/core/youtube_client.py`: atomic total increments.
- [x] `src/api/core/serializers.py`, `admin.py`: expose the fields read-only.
- [x] `src/api/core/tests.py`: one test per matrix row.

**Acceptance Criteria:**
- Given the totals test, when the increment is changed to read-modify-write in Python (`run.total_api_requests += 1; run.save()`) with a stale `run` instance, then a test fails.
- Given the failed-call test, when the increment moves after the transport call's success path, then that test fails.

## Implementation Notes

- Migration renamed to `0007_collectionrun_totals_and_error_message.py`. Totals are incremented right after the log row is created with one `filter(pk).update(F()+…)`, then `run.refresh_from_db(fields=[…])`.
- Matrix audit: every row has a test in `CollectionRunModelTests`, `CallYouTubeTests` or `CollectionRunStartApiTests`; full suite 128 OK on PostgreSQL. Both acceptance mutations (read-modify-write on a stale instance; increment after the success path) fail a test. Thesis baseline: `6e68310745fa91ed29a6a8cd211045f33a61a638`.
- Review patches (pass 1) applied: log create + totals update in one `transaction.atomic()` (request outside it); whitespace-only failure message rejected. Full suite 128 OK on PostgreSQL.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 3, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Log `create` and run-totals `update` are separate autocommit statements; a failure between them leaves an uncounted log row | low | patch | Confirmed: no `atomic` anywhere in `core/`. Direct fix: wrap both statements (not the request) in `transaction.atomic()`. |
| Network failures (no HTTP response) still add the full quota cost | low | reject | Confirmed, but consistent by design: US-013 keeps the assigned `quota_cost` on every failed log row, so totals equal the logs' sum; over-counting is the conservative error for a quota budget, a timeout may have reached YouTube anyway, and a refund adds a branch for a rare case. |
| `transition_to("failed", error_message="   ")` stores a blank message | low | patch | Confirmed: guard is `if not error_message`. Direct fix: check `.strip()`; add the case to the test. |

## Design Notes

The totals are incremented when the log row is created, not when the response arrives. A crash mid-call is then still counted, which matches the log row that stays behind.

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.

**Manual checks:**
- Start a run from the UI, call `call_youtube` on it in `manage.py shell` with a fake transport, then open the run in `/admin/`: the totals are 1 and 100, and every new field is read-only.
