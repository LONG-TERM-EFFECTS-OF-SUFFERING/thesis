# 27 - Add basic cleaning, normalization and validation report

Story: US-024, Add basic cleaning, normalization and validation report.

Status note: this document describes the US-024 implementation **after** the code review of 2026-10-07 and the fixes that followed it. With it, every story of the YouTube data storage and processing epic is built.

## What this story added

Comments are stored exactly as YouTube sends them. That is right for auditing, but messy for analysis: invisible characters, HTML entities, links and odd spacing. This story adds the first step of the processing pipeline the thesis promises:

- **`text_normalized`**, a new column on `youtube_comments`: a cleaned copy of `text_original`, for top-level comments and replies. The original columns and `raw_payload` are never changed.

- **`ProcessingRun`**, a new table (`processing_runs`): one record per processing pass, with its status, rows read and written, and a **validation report**.

- **Automatic processing.** When a collection run completes successfully, `collect_run` immediately processes that run's comments. There is no extra command to remember.

## Why this matters

Sentiment analysis (US-025) needs clean, consistent text. And the thesis needs to say exactly **how** text was cleaned and how many comments were usable. The report records that for every processing run, together with the version of the rules that produced it.

## Key concept: six rules, in order

`core/normalization.py` holds pure functions: the same input always gives the same output, with no clock, randomness or database. The rules run in this order:

| # | rule | example |
| :-- | :-- | :-- |
| 1 | Unicode NFC normalization | combine a letter and a separate accent into one character |
| 2 | decode HTML entities | `isn&#39;t` → `isn't` |
| 3 | remove invisible and control characters; tabs and line breaks become spaces | `a​b` → `ab` |
| 4 | replace a URL with `<URL>`, only at the start of a word, in any case | `see https://x.co` → `see <URL>`; `awww.so` unchanged |
| 5 | collapse runs of whitespace and trim | `"  a   b "` → `"a b"` |
| 6 | Unicode NFC again | `e&#769;` → `é` (the accent only appears after rule 2) |

**Case and emoji are kept on purpose.** Modern sentiment models read "GREAT!!! 😍" differently from "great", so removing them would throw away signal.

Two review fixes shaped this list:
- Rule 4 first turned "awww.so cute" into "a<URL> cute" and missed `HTTPS://`. It now matches only at the start of a word, in any case.
- Rule 6 was added because an entity decoded in rule 2 can produce a separate accent that rule 1 never saw.

The rules carry a version, `comment-text-v2`. Change a rule and the version must change, so every report says which rules produced its numbers.

## Key concept: the validation report

A comment that cannot be cleaned is **counted, not fatal**:

- `missing_text`: the comment has no text at all;
- `empty_text`: nothing is left after the rules (for example, a comment that was only invisible characters).

Its `text_normalized` stays empty, and processing continues with the next comment.

Each `ProcessingRun` stores `rows_read`, `rows_written` and a `summary_payload` like:

```json
{
  "normalization_version": "comment-text-v2",
  "inputs":  {"top_level": 3, "reply": 1},
  "written": {"top_level": 2, "reply": 1},
  "errors":  {"missing_text": 0, "empty_text": 1},
  "rules":   {"nfc": 1, "html_unescape": 2, "chars_removed": 3,
              "urls_replaced": 2, "whitespace": 2, "nfc_final": 1}
}
```

`rules` counts, for each rule, how many comments it actually changed.

The report holds **only counts**, never text or YouTube IDs. Processing runs are kept after the 30-day purge, like request logs (pages 12 and 24), so they must contain no YouTube data. A test checks this.

## Key concept: processing never breaks collection

Processing runs after the collection run is already `completed`:

- if collection **failed**, nothing is processed;
- if processing fails, only the **processing run** becomes `failed` (with the error's class name). The collection run stays `completed`, and the `collect_runs` loop continues with the next run;
- comments cleaned before the failure keep their `text_normalized`.

A review fix widened the error handling: a failure while starting or finishing the processing run used to leave it stuck in `pending` or `running`.

Both run types now share one status lifecycle (`pending → running → completed | failed | cancelled`), through a small `RunLifecycle` class in `models.py`. Migration `0015` names that class, so renaming it later means editing the migration too.

## Key concept: purged together

`text_normalized` is a column of the comment row. When the 30-day purge (page 26) deletes a comment, its cleaned text goes with it, so the purge needed no change. Processing runs and their reports are kept.

## File-by-file explanation

### `src/api/core/models.py` and `src/api/core/migrations/0015_processingrun_youtubecomment_text_normalized.py`

- `RunLifecycle`: the shared statuses, the allowed transitions and the compare-and-set `transition_to`.
- `ProcessingRun`: with an allowed-status check and a finished-after-started check.
- `YouTubeComment.text_normalized`.

### `src/api/core/normalization.py`

- `NORMALIZATION_VERSION`, `RULE_NAMES` and the error codes.
- `normalize_comment_text(text)`, which returns the cleaned text (or an error code) plus the names of the rules that changed it.

### `src/api/core/processing.py`

`process_collection_run(run)` creates the processing run, cleans every comment and reply linked to the collection run, and writes the counts and the report.

### `src/api/core/collection.py`

`collect_run` calls `process_collection_run` after a successful collection, and logs, without raising, any processing error.

### `src/api/core/admin.py`

- Read-only Processing runs pages that show the report.
- The comment list shows the original and the cleaned text side by side.

### `src/api/core/tests.py`

- Unit tests for each rule, their order, the URL edge cases, the accent case and the reported rule names.
- Model tests for the lifecycle and both checks.
- Processing tests:
  - the full report on a messy fixture
  - invalid records
  - processing twice gives the same output and report
  - the purge removes cleaned text
  - empty runs
  - failures inside and outside the loop
  - a failed collection is not processed
  - processing failures do not touch the collection run

### `docs/database_schema.md`

Rows for `processing_runs` (including the usual not-null fix for its collection-run column) and for `youtube_comments.text_normalized`.

## How the pieces connect

```text
collect_run(run)
   ... discovery, details, channels, comments, replies
   transition_to("completed")
   '-- process_collection_run(run)                 (errors logged, never raised)
          ProcessingRun: pending -> running
          for each comment and reply linked to the run:
             normalize_comment_text(text_original)
                -> text_normalized, or an error code
          rows_read, rows_written, summary_payload (version, inputs, written, errors, rules)
          ProcessingRun: -> completed   (or failed, with the error class name)
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py test core.tests.NormalizeCommentTextTests
```

Passing looks like `OK` (262 tests). The second command runs only the rule tests, which need no database setup beyond Django's.

## How to test manually

1. Bring your database up to date (`./run-local.sh` migrates SQLite; for Compose PostgreSQL run `DATABASE_ENGINE=postgresql venv/bin/python manage.py migrate` from `src/api`).

2. Collect a run with comments (page 22): save a query with **Comments per video** set, click **Start run**, then run `venv/bin/python manage.py collect_runs`.

3. In `http://127.0.0.1:8000/admin/` → Processing runs: one `completed` run for that collection run, with `rows_read`, `rows_written` and the report.

4. Youtube comments: the original and cleaned text side by side. Links show as `<URL>`, extra spaces are gone, and emoji and capitals are still there.

You can also try the rules directly in `venv/bin/python manage.py shell`:

```python
from core.normalization import normalize_comment_text
normalize_comment_text("  Mira https://x.co  isn&#39;t   GREAT 😍 ")
# ("Mira <URL> isn't GREAT 😍", None, frozenset({...}))
```

## Common errors

- **A comment has no cleaned text.** Check the processing run's report: `missing_text` or `empty_text` counts explain it. A comment made only of invisible characters ends up empty.

- **No processing run for a collection run.** The collection failed, so it was not processed. Or the run was collected before this story, so collect again.

- **A processing run is `failed`.** Its `error_message` names the error class, and the server log has the full trace. The collection run is unaffected.

## Known gaps

- The Results card (page 25) does not show a processed count yet. The US-027 plan expected the processing stories to add one.

- Processing updates comments one by one. That is fine at thesis scale; a `ponytail:` comment in `processing.py` marks where to batch if runs grow large.

- Rule 3 also removes U+200D, the zero-width joiner that builds emoji like 👨‍👩‍👧, so such emoji are split into their parts. Found in US-036 (page 30) and logged in `deferred-work.md` for a decision.

- Only comment text is normalized. Video and channel fields are already typed and checked when they are collected (pages 17 and 18).
