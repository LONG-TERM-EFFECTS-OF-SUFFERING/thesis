---
title: 'Store comment sentiment results (part A: model-agnostic)'
type: 'feature'
ticket: '4'
created: '2026-10-08'
status: 'done'
baseline_revision: '0ac0359ca6177b1cc685a967f97a5ac46f35f2c6'
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

**Problem:** Comments have clean text (US-024) but no sentiment, so audience opinion cannot be studied (US-025). The researcher has not chosen the sentiment method yet.

**Approach:** Build everything that does not depend on the method, and record plugging in a real model as deferred part B.
- **Table:** `CommentSentiment`, as in `docs/database_schema.md`.
- **Classifier contract:** one function signature that any model adapter implements.
- **Sentiment step:** classifies each comment's `text_normalized` and stores one result per comment, with model name and version, in a processing run whose report counts labels and skips.
- **Off by default:** with no model configured, the step does nothing. No fake or placeholder result is ever stored outside tests.

## Boundaries & Constraints

**Always:**
- **`CommentSentiment`** (`comment_sentiments`) matches the schema doc:
  - `processing_run` and `comment` are `CASCADE` FKs, so the 30-day purge removes sentiment with its comment;
  - unique (`processing_run`, `comment`, `model_name`);
  - `sentiment_label` choices `positive`, `negative`, `neutral`, `mixed`, `unknown`, with a `CheckConstraint`;
  - check constraints `-1 ≤ sentiment_score ≤ 1` and `0 ≤ confidence ≤ 1` when set;
  - `model_name`, `language_code`, `raw_payload` and `created_at`.
- **The classifier contract** lives in a new import-safe module: a frozen dataclass `SentimentResult(label, score, confidence, language_code, raw)` and a `Classifier` protocol with `name: str`, `version: str` and `classify(texts: list[str]) -> list[SentimentResult]` (batch, so a real model can batch). The step validates every result at the boundary: a label outside the choices, a score or confidence out of range, a `bool`, or a result count that differs from the input count each fails the run. It never stores a bad row.
- **Input:** a comment is classified only when its `text_normalized` is set. Comments without it are counted as `skipped_no_text`.
- **Report** (`summary_payload` of the sentiment processing run): `{"model_name", "model_version", "inputs", "labels": {label: count}, "skipped_no_text"}`, all five labels always present. Counts only: no text, no IDs.
- **Failures:** an unexpected exception, or an invalid classifier result, fails the processing run with the exception's class name and keeps the rows already stored. It never changes the collection run.
- **Tests** inject a fake classifier. No test downloads a model or reaches the network. Validated on Compose PostgreSQL.

**Decisions** (approved by the human on 2026-10-08):
- **Own processing run:** the sentiment step creates its own `ProcessingRun` (`project` and `collection_run` set), right after the normalization processing run. `collect_run` calls it only after a successful collection, wrapped and logged so it never affects the collection run or the normalization run.
- **Model version:** `CommentSentiment` gains `model_version = CharField(max_length=120)`. The unique key becomes (`processing_run`, `comment`, `model_name`, `model_version`), and the report holds both.
- **Configuration:**
  - `SENTIMENT_MODEL = env_str("SENTIMENT_MODEL", "")` in `settings.py`; empty means the step is skipped.
  - `sentiment.py` keeps a module-level registry, `CLASSIFIERS: dict[str, Callable[[], Classifier]]`, empty in part A.
  - A non-empty `SENTIMENT_MODEL` that is not a registry key is reported by a Django system check (`django.core.checks.register`, `Error`, id `core.E001`). `runserver`, `migrate`, `collect_runs` and `test` therefore stop loudly instead of skipping sentiment.
  - The step instantiates the classifier lazily (on first use, not at import), so modules stay import-safe.

**Never:**
- No real model, no `torch`/`transformers`/`pysentimiento`/`openai` dependency, and no label mapping for a specific model: that is part B, in `deferred-work.md`.
- No fake or default classifier used outside tests.
- No API endpoint or UI (US-026).
- No change to normalization (US-024).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Classified | completed collection run, 3 comments with `text_normalized`, a fake classifier returning positive / negative / neutral | 3 `CommentSentiment` rows with label, score, confidence, model name/version and processing run; report `labels` counts 1/1/1, the others 0 | No error expected |
| No text | a comment with `text_normalized` null | no row for it; `skipped_no_text` 1 | No error expected |
| Off | `SENTIMENT_MODEL` empty | no sentiment processing run created, no rows | No error expected |
| Unknown model | `SENTIMENT_MODEL="nope"` with an empty registry | the system check returns `core.E001` | check error |
| Own run | model configured (a test registry entry), collection completes | two processing runs for the collection run: normalization, then sentiment, each with its own report | No error expected |
| Bad result | the classifier returns a label `"great"`, a score 1.5, a `bool` confidence, or 2 results for 3 texts | run `failed` with the class name; no invalid row stored | logged |
| Purge | the purge deletes a comment | its sentiment rows go with it | No error expected |
| DB checks | insert a label outside the choices, score 2, confidence -0.1, or a duplicate (run, comment, model name, model version) | rejected | `IntegrityError` |
| Isolation | the sentiment step raises | the collection run stays `completed`; the normalization processing run is unaffected | logged |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py` -- `CommentSentiment` after `ProcessingRun`. Generate `0016`. It includes `model_version`, and the unique key covers name and version.
- `src/api/core/sentiment.py` (new) -- `SentimentResult`, the `Classifier` protocol, `validate_result`, and `analyze_comments(...)`. It mirrors `processing.py`: the lifecycle covered by `try`, a `finally`-written report and a class-name error.
- `src/api/opentube_insights_api/settings.py` -- `SENTIMENT_MODEL` beside `YOUTUBE_API_KEY`, using `env_str`.
- `src/api/core/checks.py` (new) -- the `core.E001` system check, registered in `CoreConfig.ready()` (`core/apps.py`).
- `src/api/core/collection.py` -- after `process_collection_run(run)`, call the sentiment step when `SENTIMENT_MODEL` is set, wrapped and logged like processing. Tests use `override_settings` plus a patched `CLASSIFIERS` entry holding the fake.
- `src/api/core/purge.py` -- no change: the `CASCADE` from the comment covers it. Add a purge test.
- `src/api/core/admin.py` -- `CommentSentiment` read-only.
- `src/api/core/tests.py` -- a fake classifier class, and one test per matrix row.
- `docs/database_schema.md` (thesis repo, separate docs commit) -- a `model_version` row and the widened unique key.
- `src/api/.env.example` -- `SENTIMENT_MODEL=` with a comment that empty means off.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/models.py` + migration -- `CommentSentiment`.
- [x] `src/api/core/sentiment.py` -- the contract, validation and step.
- [x] `settings.py`, `.env.example`, `core/checks.py`, `core/apps.py`, `core/collection.py` -- the setting, the check and the wiring, off by default.
- [x] `src/api/core/admin.py`, `src/api/core/tests.py` -- admin and tests.
- [x] `docs/database_schema.md` -- schema updates.

**Acceptance Criteria:**
- Given the bad-result test, when result validation is removed, then an invalid row is stored or the database rejects it and the test fails.
- Given the "off" test, when the step runs without a configured model, then no `CommentSentiment` or sentiment `ProcessingRun` exists.
- Given the report test, when any comment text or ID appears in `summary_payload`, then the test fails.

## Implementation Notes

- `analyze_comments(run)` owns the off switch: it returns None before creating anything when `SENTIMENT_MODEL` is empty, so `collect_run` needs no setting check of its own. Review fix: `collect_run` calls it only when the normalization processing run returned `completed`; a failed or raising normalization skips sentiment, so stale or partial `text_normalized` is never classified.
- Report `inputs` counts every comment linked to the run (as normalization does), so `inputs = sum(labels) + skipped_no_text` on success; `rows_read`/`rows_written` mirror `inputs` and the stored rows.
- Comments are classified in batches of `BATCH_SIZE = 64`; a batch is validated in full before `bulk_create`, so a bad result stores nothing from its batch and keeps earlier batches.
- The classifier is built inside the run's `try`, so a factory failure (e.g. missing weights) fails the sentiment run with its class name; the report then holds the registry key as `model_name` and `model_version: null`.
- `validate_result` also rejects a `language_code` that is not a string of at most 20 characters (the column width), and NaN through the range check.
- `docker-compose.yml` does not pass `SENTIMENT_MODEL` to the api container; left for part B, since any non-empty value fails `core.E001` while the registry is empty.
- `docs/ER_diagram.mmd`/`.svg` not updated (they also lack US-024's `text_normalized`).

- Orchestrator check: 274 OK on PostgreSQL, migrations clean, `SENTIMENT_MODEL=nope manage.py check` reports `core.E001`. Thesis baseline `a565896588942a7e6fc7e31ab0b5f427558e1170`.

- Review patches (pass 1) applied: sentiment runs only after a completed normalization run; bad-result subtests scoped to their own processing run. Full suite 275 OK on PostgreSQL. Part B (the real model) is in `deferred-work.md`.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 1, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Sentiment runs even when the normalization run failed, classifying stale or partial `text_normalized` (shared comment rows) and reporting `completed` | medium | patch | Confirmed: `collect_run` discards the returned processing run. Within intent ("right after the normalization processing run"): gate sentiment on that run being `completed`; test the failed-normalization path. |
| The bad-result subtests share database state, so a broken case makes later cases fail for the wrong reason | low | patch | Confirmed (AGENTS.md pitfall). Scope each subtest's assertion to its own processing run. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.

**Manual checks:**
- With `SENTIMENT_MODEL` empty, collect a run: no Comment sentiments rows appear in `/admin/`, and no sentiment processing run either.
