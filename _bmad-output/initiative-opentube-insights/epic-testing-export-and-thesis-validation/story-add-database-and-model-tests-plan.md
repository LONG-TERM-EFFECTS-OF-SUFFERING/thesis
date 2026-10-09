---
title: 'Add database and model tests'
type: 'chore'
ticket: '3'
created: '2026-10-08'
status: 'done'
baseline_revision: '224b6ac2caa8e71ea7f19f2731b1c878fb7a48f2'
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

**Problem:** US-033 asks for database and model tests on controlled data, including the 30-day purge and its cascade to derived records. Each model story left its own model tests, and US-040 left 14 purge tests. Three gaps remain:
- **The purge's cascade to derived records is untested.** The purge tests predate US-024 and US-025, so they never check `text_normalized`, `CommentSentiment` rows or processing runs. The later "purged comment" tests delete the comment directly instead of running the purge.
- **The delete rules are not pinned.** The 20 foreign keys have deliberate `on_delete` rules that no single test fixes in place.
- **Only one table's constraints are checked in the database.** Only `collection_runs` has a test confirming that its declared constraints exist in PostgreSQL.

**Approach:** Add tests only:
- one full-dataset purge test, run through `purge_youtube_data`, that checks every derived record goes and every methodological record stays;
- a table-driven test pinning every foreign key's `on_delete`;
- a test that every model's declared check and unique constraint exists, by name, in the database.

## Boundaries & Constraints

**Always:**
- **Full-dataset purge** (`PurgeCascadeTests`). Build one controlled project:
  - a saved query and two collection runs;
  - an old video and a fresh video (on either side of `RETENTION_DAYS`), with a channel, statistics snapshots, run-video links, top-level comments with replies, run-comment links, `text_normalized`, a normalization `ProcessingRun`, and a sentiment `ProcessingRun` with `CommentSentiment` rows (created directly, no classifier) and a request log.

  Run `purge_youtube_data(now=...)` and assert, with exact counts:
  - **Gone:** the old video, its links, snapshots, comments, replies, and those comments' `text_normalized` and `CommentSentiment` rows.
  - **Kept and unchanged:**
    - the fresh video with everything attached;
    - every `ResearchProject`, `SavedQuery`, `CollectionRun` (all counters and `effective_params`), `ApiRequestLog` and `ProcessingRun`;
    - each `ProcessingRun`'s `summary_payload` (reports outlive the purge).
  - The deleted kinds and counts in the returned `PurgeResult` equal the rows that disappeared, including cascades.
- **Delete-rule table** (`DeleteRuleTests`): a module-level `EXPECTED_DELETE_RULES` maps every `(model, field)` foreign key in the `core` app to `CASCADE` or `SET_NULL`, matching `docs/database_schema.md`. The test fails if:
  - a foreign key is missing from the table;
  - the table lists a foreign key that no longer exists;
  - any rule differs.
- **Behavior samples:** for the `SET_NULL` keys (`CollectionRun.saved_query`, `CollectionRun.initiated_by_user`, `YouTubeVideo.channel`, `VideoStatisticsSnapshot.collection_run`, `ProcessingRun.collection_run`), one test each deletes the target and checks that the row survives with the link null. Behavior already covered elsewhere is not duplicated: only these five, and only where no existing test asserts it (record which ones in Implementation Notes).
- **Constraint existence** (`DatabaseConstraintTests`): for every `core` model, every `CheckConstraint` and `UniqueConstraint` name declared in `Meta.constraints` exists in `connection.introspection.get_constraints` for its table. It runs on both SQLite and Compose PostgreSQL, with no skip (amended with human approval on 2026-10-08, after the review showed SQLite introspection reports every declared name).
- Each new assertion is mutation-checked once (Implementation Notes).
- No network. Validated on Compose PostgreSQL.

**Never:**
- No product code changes. If a test exposes a defect, stop and report it.
- No migrations.
- No moving or splitting existing tests.
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Purge cascade | the controlled project above, `now` such that one video is past the cutoff | derived records of the old video gone (incl. `text_normalized` and sentiment rows), everything else and all methodological rows unchanged, reports intact | No error expected |
| Purge result | same | `PurgeResult.deleted` equals the rows that disappeared per model | No error expected |
| Delete rules | the `core` models | every FK's `on_delete` equals `EXPECTED_DELETE_RULES`; none missing, none extra | No error expected |
| SET_NULL samples | delete each `SET_NULL` target | the row survives with a null link | No error expected |
| Constraints in DB | every declared constraint | present by name on its table, on SQLite and PostgreSQL | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/tests.py`:
  - `PurgeYouTubeDataTests` (US-040) and its helpers show how to age rows with `update()`;
  - `ProcessCollectionRunTests` and `AnalyzeCommentsTests` show how to build processing runs and sentiment rows directly;
  - the existing `test_check_constraints_exist_on_table` (around line 498) is the pattern for introspection.
- `src/api/core/purge.py` (`purge_youtube_data`, `RETENTION_DAYS`, `PurgeResult`) and `src/api/core/models.py` -- read-only references. The current delete rules are listed in this plan's investigation (20 FKs: 15 `CASCADE`, 5 `SET_NULL`).
- Add `PurgeCascadeTests(APITestCase)`, `DeleteRuleTests(SimpleTestCase)` and `DatabaseConstraintTests(TransactionTestCase or APITestCase)`.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/tests.py` -- `PurgeCascadeTests`.
- [x] `src/api/core/tests.py` -- `EXPECTED_DELETE_RULES`, `DeleteRuleTests` and the `SET_NULL` samples.
- [x] `src/api/core/tests.py` -- `DatabaseConstraintTests`.

**Acceptance Criteria:**
- Given the purge cascade test, when `CommentSentiment.comment` is changed to `SET_NULL` (in a scratch edit), then the test fails.
- Given the delete-rule test, when any FK's `on_delete` changes or a new FK is added without a table entry, then it fails.
- `git diff --stat 224b6ac -- core/ ':!core/tests.py'` is empty.

## Implementation Notes

- Only `src/api/core/tests.py` changed (imports `django.apps.apps` and `django.db.models`); suite 325 -> 329 tests.
- `PurgeCascadeTests` (after `PurgeYouTubeDataTests`): two runs, two request logs, a normalization and a sentiment `ProcessingRun`, one fresh channel, and per video 2 run links, 2 snapshots, 2 threads (top-level + reply) with `text_normalized`, 2 run-comment links and 1 `CommentSentiment` each. Only the old video is aged, so its snapshots and comments can only leave by cascade. The test snapshots every `core` table with `values()` before and after the purge and requires each table after to equal before minus exactly the old video's rows: kept rows match in every column (counters, `effective_params`, `data_purged_at`, `text_normalized`, `summary_payload`). The per-table drop is pinned (video 1, run-video 2, snapshot 2, comment 4, run-comment 8, sentiment 4) and must equal the non-zero entries of `PurgeResult.deleted`; `runs_stamped` is 0 because both runs keep the fresh video. Zero-count labels are filtered because which zero labels Django's collector reports is an internal detail.
- `EXPECTED_DELETE_RULES` + `DeleteRuleTests` and `DatabaseConstraintTests` sit after `YouTubeCommentModelTests`. The delete-rule test collects every concrete relation field (`_meta.fields` with `remote_field`, so a future `OneToOneField` is caught too) and compares one dict, which reports missing, extra and changed keys; `maxDiff = None` so the diff names the key. The constraint test also checks the kind (`check` / `unique`; the partial unique snapshot constraint is a unique index in PostgreSQL and reports `unique`) and fails if it checked nothing. It has no vendor skip: it passes on SQLite too (review patch).
- `SET_NULL` samples: four of five were already asserted, so only `CollectionRun.initiated_by_user` was added, as `CollectionRunModelTests.test_deleting_the_initiating_user_keeps_run` beside its `saved_query` sibling (it needs the DB, so it cannot live in the `SimpleTestCase`). The initiator is a second user because deleting the owner cascades to the project. Existing coverage:
  - `CollectionRun.saved_query`: `CollectionRunModelTests.test_deleting_saved_query_keeps_run`.
  - `YouTubeVideo.channel`: `PurgeYouTubeDataTests.test_old_channel_is_deleted_and_its_fresh_video_loses_the_channel`.
  - `VideoStatisticsSnapshot.collection_run`: `VideoStatisticsSnapshotModelTests.test_deleting_the_run_keeps_the_snapshot`.
  - `ProcessingRun.collection_run`: `ProcessingRunModelTests.test_deleting_the_collection_run_keeps_the_processing_run`.
- Mutation checks, all on Compose PostgreSQL, each reverted (product files by `git checkout`, the scratch migration deleted):
  - `CommentSentiment.comment` -> `SET_NULL, null=True` with a scratch migration: the cascade test fails on `core.CommentSentiment` and the counts, and `DeleteRuleTests` fails.
  - purge counts only `PURGED_MODELS` labels: the `PurgeResult` assertion fails.
  - purge also wipes `CollectionRun.effective_params` / `YouTubeComment.text_normalized` / `ProcessingRun.summary_payload` (three runs): the kept-row comparison fails on that table each time.
  - purge skips the video queryset: the gone-row comparison fails on 7 tables.
  - `YouTubeVideo.channel` -> `CASCADE`; table entry removed; extra `("YouTubeVideo", "playlist")` entry: `DeleteRuleTests` fails each time.
  - `CollectionRun.initiated_by_user` -> `CASCADE`: the new sample errors (`DoesNotExist`).
  - a `Meta.constraints` name changed without a migration: `DatabaseConstraintTests` fails naming it; `check`/`unique` swapped in the test: fails; no constraints iterated: fails on the emptiness guard.
- Not a defect found by the tests, but noted: `docs/database_schema.md` says `saved_queries` is unique on (`project_id`, `name`); the model's `unique_saved_query_name_per_project_creator` is on (`project`, `created_by`, `name`). The constraint test checks declared names, so it does not catch doc drift.

- Review patches (pass 1) applied: SQLite skip removed from `DatabaseConstraintTests` (it runs and passes on SQLite); `Args` added to `PurgeCascadeTests.make_video`. Re-verified: 329 OK on PostgreSQL, constraint test `ok` on SQLite, product diff empty.

- Orchestrator check: 329 OK on PostgreSQL with `DatabaseConstraintTests` run (not skipped); no stray migration (latest is 0016); product diff empty. Thesis baseline `618dbe94e0cd99c85ca21f3ad7940694793ee8c5`.

## Plan Change Log

- 2026-10-08, human-approved: the constraint-existence test runs on SQLite as well; the frozen "skipped on SQLite" line and its matrix row were amended.

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 2, false 0, maybe-false 0, defer 1.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `DatabaseConstraintTests` skips on SQLite although SQLite introspection reports every declared check and unique name, so the default `manage.py test` never runs it | low | intent_gap -> patch | Human chose "Remove the skip". Skip removed; the test passes on SQLite and PostgreSQL. Frozen line amended (Plan Change Log). |
| `PurgeCascadeTests.make_video` docstring has no `Args` section, and `fetched_at` is what decides the purge side | low | patch | Args added for `youtube_id` and `fetched_at`. |
| `docs/database_schema.md` `saved_queries` says unique on (`project_id`, `name`) and names a date-range check constraint; the model is unique on (`project`, `created_by`, `name`) and the date order is checked only in `SavedQuerySerializer.validate` | low | defer | Doc drift, not a test or product defect; logged in deferred-work. The `collection_runs` null mismatch is already deferred (US-010). |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK, with the constraint test run, not skipped.
- `cd src/api && venv/bin/python manage.py test --noinput core.tests.DatabaseConstraintTests` -- expected: OK on SQLite as well.
- `cd src/api && git diff --stat 224b6ac -- core/ ':!core/tests.py'` -- expected: empty.
