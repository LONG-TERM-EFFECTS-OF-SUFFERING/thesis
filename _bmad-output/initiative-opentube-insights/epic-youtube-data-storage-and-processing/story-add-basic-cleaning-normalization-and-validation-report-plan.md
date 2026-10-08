---
title: 'Add basic cleaning, normalization and validation report'
type: 'feature'
ticket: '5'
created: '2026-10-07'
status: 'built'
baseline_revision: '556aa3b85188832a913ef3075b3c5a7b806766c8'
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

**Problem:** Collected data is stored as YouTube sends it. Nothing cleans it into a consistent form for analysis, and nothing reports how many records are usable or why the rest are not (US-024). Sentiment (US-025) needs clean comment text as its input.

**Approach:** Add the `ProcessingRun` model from `docs/database_schema.md` and a processing step that applies a small, deterministic, versioned set of normalization rules to a collection run's data. Each processing run records `rows_read`, `rows_written`, a validation report (counts per rule and per error kind) in `summary_payload`, and its status. Normalized output is stored so that the 30-day purge removes it together with the YouTube data it came from.

## Boundaries & Constraints

**Always:**
- **`ProcessingRun`** (`processing_runs`) matches the schema doc. `project` is a `CASCADE` FK. `collection_run` is a `SET_NULL`, `null=True` FK: the doc's `null: NO` contradicts its own Django column again, so follow the Django column and fix the doc.
  - Its five statuses and allowed transitions are the same as `CollectionRun`'s. Reuse the same pattern (a transition map and a compare-and-set `transition_to`), not a library.
  - Two checks: an allowed-status check and `finished_at >= started_at`.
- **Rules are pure functions**, in a new import-safe module, with a `NORMALIZATION_VERSION` string. The version is stored in every processing run's `summary_payload`, so a report always names the rules that produced it.
- **Deterministic:** processing the same collection run twice gives the same normalized output and the same report.
- **The report** (`summary_payload`): `{"normalization_version", "inputs": {kind: count}, "written": {kind: count}, "errors": {error_code: count}, "rules": {rule: count}}`, plus `rows_read` and `rows_written` totals. `rules` counts, for each rule, the comments whose text that rule changed: `nfc`, `html_unescape`, `chars_removed`, `urls_replaced`, `whitespace`, `nfc_final`, all always present (added by the human on 2026-10-07). No YouTube text or IDs go in the report: processing runs are kept after the purge, like request logs.
- **Validation errors are counted, not fatal.** A record that fails validation is skipped and counted, and the run still completes. An unexpected exception fails the run with its class name, as the collector does.
- **Tests:** no network. Validated on Compose PostgreSQL.

**Decisions** (approved by the human on 2026-10-07):
- **Output:** comment text only, in a new nullable `YouTubeComment.text_normalized` (`TextField(null=True, blank=True)`), computed from `text_original`. It covers top-level comments and replies. Being on the comment row, it is purged with the comment. Re-processing overwrites it deterministically.
- **Rules,** in order:
  1. `unicodedata.normalize("NFC", text)`;
  2. `html.unescape`;
  3. remove zero-width characters (U+200B–U+200D, U+2060, U+FEFF) and control characters (Unicode category `Cc`), except that `\n` and `\t` become a space;
  4. replace URLs (`https?://` or `www.` up to the next whitespace) with `<URL>`;
  5. collapse runs of whitespace to one space and trim;
  6. `unicodedata.normalize("NFC", text)` again, so entities that decode to combining characters are composed (added by the human on 2026-10-07; `NORMALIZATION_VERSION = "comment-text-v2"`).

  Rule 4 matches a URL only at the start of a token (start of text or after whitespace), case-insensitively (review fix within the rule's intent).

  Case and emoji are kept. Validation errors: `missing_text` (no `text_original`) and `empty_text` (nothing left after the rules). On either error, `text_normalized` stays null.
- **Trigger:** automatic. `collect_run`, after it moves a run to `completed`, calls `process_collection_run(run)`, which creates one `ProcessingRun` (`project` and `collection_run` set). A failed collection run is never processed.
  - A processing failure is recorded on the `ProcessingRun` only. It never changes the collection run's status, which is already terminal.
  - Each later collection run gets its own processing run. There is no separate command.

**Never:**
- No sentiment (US-025).
- No `derived_metrics` (they belong to the analysis stories).
- No changes to how raw data is collected or stored: `raw_payload` and the original columns stay untouched.
- No new dependencies (stdlib `unicodedata`, `html` and `re` are enough).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Normalize | a completed collection run with comments whose text has extra spaces, HTML entities, a URL and zero-width characters | normalized text written per the rules; report counts inputs and written records; status `completed` | No error expected |
| Invalid record | a comment whose text is empty after normalization | not written; `errors.empty_text` 1; run still `completed` | counted |
| Idempotent | the same collection run processed twice | identical normalized output; second report equal to the first | No error expected |
| Purge | normalized record's source comment purged (US-040) | normalized record gone with it | No error expected |
| No data | collection run with no comments | `rows_read` 0, `rows_written` 0, `completed` | No error expected |
| Unexpected failure | a rule raises an unexpected exception | run `failed`, `error_message` = exception class name, records written before it kept | logged |
| Failed collection | the collection run ends `failed` | no processing run created | No error expected |
| Processing failure isolated | processing raises after the collection run completed | processing run `failed`; collection run stays `completed` | logged |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py` -- `ProcessingRun` after `CollectionRunComment`, copying `CollectionRun`'s `RunStatus` / `ALLOWED_TRANSITIONS` / `transition_to` idiom. Add `YouTubeComment.text_normalized`. Generate `0015`.
- `src/api/core/normalization.py` (new) -- `NORMALIZATION_VERSION` and the pure rule functions, each returning a normalized value or an error code. Unit-tested without the database.
- `src/api/core/processing.py` (new) -- `process_collection_run(run) -> ProcessingRun`, which applies the rules, writes the output and fills the report. Same pattern as `collection.py` (status lifecycle, a `finally`-written count, a class-name error).
- `src/api/core/collection.py` `collect_run` -- after the final `transition_to(COMPLETED)`, call `process_collection_run(run)`, wrapped so that an exception is logged and recorded on the processing run, never raised to the collector or the `collect_runs` loop.
- `src/api/core/purge.py` -- no change: `text_normalized` is a column of the comment row. Processing runs are kept, like collection runs.
- `src/api/core/admin.py` -- `ProcessingRun` read-only, showing the report. Add `text_normalized` to the comment admin.
- `docs/database_schema.md` (thesis repo, separate docs commit) -- the `processing_runs.collection_run_id` null fix and a `youtube_comments.text_normalized` row.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/models.py` + migration -- `ProcessingRun` and the normalized output.
- [x] `src/api/core/normalization.py` -- rules and version.
- [x] `src/api/core/processing.py` + the call in `collect_run` -- the processing step, the report and the trigger.
- [x] `src/api/core/admin.py`, `src/api/core/tests.py` -- registration, rule unit tests and one test per matrix row.
- [x] `docs/database_schema.md` -- schema updates.

**Acceptance Criteria:**
- Given the idempotent test, when a rule depends on time or randomness, then the test fails.
- Given the purge test, when the normalized output does not cascade with its source, then the test fails.
- Given the report test, when any comment text or YouTube ID appears in `summary_payload`, then the test fails.

## Implementation Notes

- The lifecycle is shared, not copied: `RunStatus`, `ALLOWED_TRANSITIONS`, `TERMINAL_STATUSES` and `transition_to` moved into a plain `RunLifecycle` mixin that `CollectionRun` and `ProcessingRun` both inherit. Error messages name the model through `_meta.verbose_name`, so `CollectionRun`'s messages are unchanged.
- Rules are an ordered `(name, function)` table in `normalization.py`; the pure `normalize_comment_text(text) -> (value, error, changed_rule_names)` runs them and `process_collection_run` aggregates the names into the report's `rules` block. Report kinds are the comment levels (`top_level`, `reply`); every kind, error code and rule is always present, with zeros.
- Processing writes with one `UPDATE` per comment (no `save()`), so `updated_at` and `last_fetched_at` are untouched and a failure keeps earlier rows. Marked `ponytail:` for a batched upgrade.
- The URL rule takes trailing punctuation with it (`http://y.org,` becomes `<URL>`), as the "up to the next whitespace" rule says.
- `process_collection_run` wraps the whole lifecycle after creation: any exception moves the run to `failed` (through `running` when it never started, since `pending -> failed` is not allowed), and the counts so far are saved in a `finally`.
- PostgreSQL rejects NUL in text, so `\x00` can never reach `text_original`; the DB tests use another control character.

- Orchestrator check: 259 OK on PostgreSQL, migrations clean. Thesis baseline `41c6b204ffb0c26ada9d77e164f64bfad7255276`.

- Review patches (pass 1) applied: URL rule anchored and case-insensitive; final NFC (`comment-text-v2`); per-rule counts in the report; whole processing lifecycle covered by the failure handler; idempotent test pins expected strings; schema doc corrected. Full suite 262 OK on PostgreSQL.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 3, low 3, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| URL rule matches mid-word ("awww." → "a<URL>") and misses upper-case URLs | medium | patch | Confirmed by running the pattern. Anchor at a token start and match case-insensitively; tests for both. |
| A failure outside the per-comment loop (create, transition, final save) leaves the `ProcessingRun` `pending`/`running` | medium | patch | Confirmed: only the loop is inside `try`. Cover the whole lifecycle; on any exception, move the run to `failed` with the class name. Test a failure after creation. |
| NFC runs before unescape, so the output is not guaranteed NFC | medium | intent_gap → patch | Confirmed (`e&#769;`). The human added a final NFC rule (version `comment-text-v2`). |
| Report lacks the per-rule counts the Approach promises | low | intent_gap → patch | The frozen section contradicted itself; the human chose per-rule counts. |
| Idempotent test cannot catch a date-dependent rule | low | patch | Compare both runs against fixed expected values. |
| Schema doc `processing_runs` paragraph mentions a user reference and omits the status check | low | patch | Direct doc correction. |
| Migration `0015` imports `core.models.RunLifecycle` in `bases` | low | reject | Standard Django behavior for a plain mixin; documented on the story page as a rename constraint. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.

**Manual checks:**
- After a collection with comments, `/admin/` → Processing runs shows a completed run whose report counts match the comments, and Youtube comments show the normalized text beside the original.
