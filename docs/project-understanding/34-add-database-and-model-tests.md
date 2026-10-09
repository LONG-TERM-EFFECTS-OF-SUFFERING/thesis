# 34 - Add database and model tests

Story: US-033, Add database and model tests.

Status note: this document describes the US-033 implementation **after** the code review of 2026-10-08 and the fixes that followed it. Like pages 15, 24, 29 and 30, this story added **tests only**: no product file and no migration changed.

## What this story added

Each model story already left tests for its own model, and US-040 left 14 purge tests. An audit found three gaps, and this story fills them:

1. **The purge's cascade to derived records.** The purge tests were written before cleaned text (US-024) and sentiment rows (US-025) existed, so nothing checked that the purge also removes them.
2. **The delete rules.** Each of the 20 foreign keys has a deliberate rule for what happens when the row it points to is deleted, but no test pinned them all in one place.
3. **Constraints in the database.** Only `collection_runs` had a test confirming that its declared constraints really exist in the database.

## Why this matters

The thesis promises two things about stored data:

- YouTube data is removed after 30 days (page 26), and nothing derived from it, such as cleaned text or a sentiment label, outlives it;
- the research record stays: projects, saved queries, runs with their counters, request logs and processing reports.

These tests are the evidence for both, on controlled data that anyone can rerun.

## Key concept: a before-and-after snapshot of every table

`PurgeCascadeTests` builds one complete project:

- a saved query and two collection runs, with request logs;
- an **old** video and a **fresh** video, both found by both runs, each with:
  - two statistics snapshots;
  - two comment threads (a top-level comment and a reply) with `text_normalized`;
  - run-comment links;
  - a sentiment row per comment;
- a cleaning `ProcessingRun` and a sentiment `ProcessingRun`.

Only the old video is aged past the 30-day cutoff. Its snapshots and comments are fresh, so they can only disappear **by cascade** from the video.

The test then reads every `core` table with `values()` (every column of every row), runs `purge_youtube_data`, and reads them again. It requires:

| table | rows gone |
| :-- | :-: |
| `YouTubeVideo` | 1 |
| `CollectionRunVideo` | 2 |
| `VideoStatisticsSnapshot` | 2 |
| `YouTubeComment` | 4 |
| `CollectionRunComment` | 8 |
| `CommentSentiment` | 4 |
| every other table | 0 |

Every row that stays must be **identical** in every column, so a purge that wiped a run's `effective_params`, a comment's `text_normalized` or a report's `summary_payload` would fail. The counts the purge returns in `PurgeResult.deleted` must equal the rows that really disappeared, cascades included. No run is marked purged (`runs_stamped` is 0), because both runs still have the fresh video.

## Key concept: a table of delete rules

`EXPECTED_DELETE_RULES` lists every foreign key in the `core` app with its rule, 15 `CASCADE` and 5 `SET_NULL`:

| key | rule | meaning |
| :-- | :-- | :-- |
| `CollectionRun.saved_query` | `SET_NULL` | deleting a saved query keeps its runs (they hold their own `effective_params`) |
| `CollectionRun.initiated_by_user` | `SET_NULL` | deleting a user keeps the runs they started |
| `YouTubeVideo.channel` | `SET_NULL` | a purged channel leaves its fresh videos in place |
| `VideoStatisticsSnapshot.collection_run` | `SET_NULL` | a snapshot outlives its run |
| `ProcessingRun.collection_run` | `SET_NULL` | a processing report outlives its run |
| the other 15 | `CASCADE` | the child row means nothing without its parent |

`DeleteRuleTests` reads every relation field from the models and compares the result with this table as one dictionary. It fails if:

- a foreign key is missing from the table, for example a new one added without a decision;
- the table names a key that no longer exists;
- any rule differs.

Comparing one dictionary means the failure message names the exact key.

Rules on paper are not enough, so each `SET_NULL` key also has a test that deletes the target and checks that the row survives with an empty link. Four already existed. This story added the fifth, `CollectionRunModelTests.test_deleting_the_initiating_user_keeps_run`. It uses a second user as the initiator, because deleting the project's owner would delete the whole project.

## Key concept: constraints exist in the database, not only in Python

A constraint declared in `Meta.constraints` protects data only if a migration actually created it. `DatabaseConstraintTests` goes through every `core` model and asks the database itself, via `connection.introspection.get_constraints`, whether each declared check and unique constraint exists under its name and is the right kind.

The plan first skipped this test on SQLite. The review found that SQLite reports every declared name too, so the skip was removed (a change you approved). The test now also runs in a plain `manage.py test`.

## Found while testing: the schema document drifts

`docs/database_schema.md` describes `saved_queries` in two ways the model does not match:

- it says the pair (`project_id`, `name`) is unique, but the model's constraint is on (`project`, `created_by`, `name`);
- it describes a database check on the date range, but that rule lives only in `SavedQuerySerializer.validate`.

The constraint test compares the models with the database, not with the document, so it cannot catch this. It is logged in `deferred-work.md`, next to the earlier `collection_runs` null-column mismatch.

## File-by-file explanation

### `src/api/core/tests.py`

- `EXPECTED_DELETE_RULES`, `DeleteRuleTests` and `DatabaseConstraintTests`, after `YouTubeCommentModelTests`.
- `PurgeCascadeTests`, after `PurgeYouTubeDataTests`.
- `CollectionRunModelTests.test_deleting_the_initiating_user_keeps_run`.

No product file changed.

## How the pieces connect

```text
controlled project (old video + fresh video, all derived rows)
   values() of every core table -> before
   purge_youtube_data(now)
   values() of every core table -> after
      before - after   = exactly the old video's rows = PurgeResult.deleted
      kept rows        = identical in every column

core models -> every relation field's on_delete == EXPECTED_DELETE_RULES
core models -> every Meta.constraints name -> present in the database, right kind
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py test core.tests.PurgeCascadeTests core.tests.DeleteRuleTests core.tests.DatabaseConstraintTests
```

Passing looks like `OK` (329 tests). The second command runs the three new classes on SQLite.

## How to test manually

This story adds no screen. To see what the tests guard, break a rule on purpose:

1. In `src/api/core/models.py`, change `YouTubeVideo.channel` to `on_delete=models.CASCADE`.
2. Run `DeleteRuleTests`. It fails and names `('YouTubeVideo', 'channel')`.
3. Restore the file with `git checkout core/models.py`.

## Common errors

- **`DeleteRuleTests` fails after you add a foreign key.** That is intended. Decide its rule, add it to `EXPECTED_DELETE_RULES`, and update `docs/database_schema.md`.

- **`DatabaseConstraintTests` fails naming a constraint.** The model declares a constraint that no migration created, usually because `makemigrations` was not run after renaming it.

- **The cascade test fails on one table after a purge change.** Read the diff: a missing row means the purge removed something it should keep; an extra row means a derived record outlived its video.

## Known gaps

- The schema document mismatches above (in `deferred-work.md`).

- The tests check that each constraint exists by name and kind, not its exact condition. The behavior tests of each model story cover the conditions.
