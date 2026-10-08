# 28 - Store comment sentiment results (part A)

Story: US-025, Run one pre-trained sentiment model and store results, **part A**.

Status note: this document describes US-025 part A **after** the code review of 2026-10-08 and the fixes that followed it. The researcher chose to keep the sentiment method open, so the story was split:

- **part A (this page):** everything that does not depend on the method: the table, the contract every model must follow, the sentiment step and its report.
- **part B (later, in `deferred-work.md`):** plugging in a real pre-trained model. The likely candidate is `pysentimiento/robertuito-sentiment-analysis`, from the AVISPA `youtube-data-extraction` notebooks.

## What this story added

- **`comment_sentiments`** (model `CommentSentiment`): one sentiment result per comment, per processing run, per model.
- **A classifier contract** in `src/api/core/sentiment.py`: the shape every model adapter must have.
- **The sentiment step:** after a collection run's comments are cleaned (US-024), it classifies their `text_normalized` and stores the results in **its own** processing run, with a report.
- **An off switch:** the `SENTIMENT_MODEL` setting. It is empty for now, so the step does nothing.

## Why this matters

Audience opinion is the thesis's central reading of a dataset. For a reader to trust a sentiment chart, every label must say which model, and which version of it, produced it, and from which text. Building the storage, checks and reporting now, against a contract, means part B only has to add the model itself.

## Key concept: a contract instead of a model

The step never imports a specific model. It talks to anything that looks like this:

```python
class Classifier(Protocol):
    name: str      # e.g. "pysentimiento/robertuito-sentiment-analysis"
    version: str   # e.g. a model revision
    def classify(self, texts: list[str]) -> list[SentimentResult]: ...
```

`SentimentResult` carries a `label`, a `score` (−1 to 1), a `confidence` (0 to 1), a `language_code` and the model's `raw` output. `classify` takes a **list** of texts, because real models are much faster in batches.

Every result is **checked before it is saved**. Any of these fails the processing run, and no bad row is stored:
- a label outside `positive / negative / neutral / mixed / unknown`;
- a score or confidence out of range, `NaN`, or `true`/`false` (the AGENTS.md `bool` pitfall);
- a different number of results than texts.

The database enforces the same rules again with check constraints, a second safety net.

## Key concept: off until a real model exists

```text
SENTIMENT_MODEL=""            -> the step does nothing (today's state)
SENTIMENT_MODEL="<a name>"    -> the name must be in CLASSIFIERS, or startup fails
```

`CLASSIFIERS` is a registry (a dictionary from name to a function that builds the classifier). It is **empty** in part A. Setting `SENTIMENT_MODEL` to any name now makes Django's system check report:

```text
core.E001 SENTIMENT_MODEL ... is not a registered sentiment model.
```

So `runserver`, `migrate`, `collect_runs` and the tests refuse to start, instead of quietly skipping sentiment because of a typo. Tests use a **fake** classifier registered only inside the test. No fake or placeholder result can ever reach your real data.

## Key concept: its own processing run, after a completed clean

For each successful collection run:

```text
collect_run
   -> process_collection_run   (US-024)  -> ProcessingRun #1: cleaning report
   -> analyze_comments         (US-025)  -> ProcessingRun #2: sentiment report
```

- Sentiment gets **its own** processing run, so changing the model later creates a new, separately reported pass, without touching cleaning.
- Sentiment runs **only if cleaning completed**. Comments are shared across runs, so after a failed clean some comments would still hold text cleaned in an earlier run, possibly under older rules. Classifying that mix would be misleading. The code review caught this.
- A sentiment failure is recorded on its own processing run and never changes the collection run or the cleaning run.

A comment without `text_normalized` (it failed cleaning) is not classified. It is counted as `skipped_no_text`.

## Key concept: the report

```json
{
  "model_name": "...", "model_version": "...",
  "inputs": 42,
  "labels": {"positive": 10, "negative": 8, "neutral": 20, "mixed": 0, "unknown": 1},
  "skipped_no_text": 3
}
```

Counts only, never text or YouTube IDs: processing runs are kept after the 30-day purge. The sentiment rows themselves are deleted with their comment by the purge (page 26), through `CASCADE`.

## File-by-file explanation

### `src/api/core/models.py` and `src/api/core/migrations/0016_commentsentiment.py`

`CommentSentiment`. It adds a `model_version` column, which the schema doc did not have. The unique key is (processing run, comment, model name, model version).

### `src/api/core/sentiment.py`

`SentimentResult`, `Classifier`, `CLASSIFIERS`, `validate_result` and `analyze_comments(run)`. The classifier is built on first use, never at import, so the module stays import-safe.

### `src/api/core/checks.py` and `src/api/core/apps.py`

The `core.E001` system check, registered when the app starts.

### `src/api/opentube_insights_api/settings.py` and `src/api/.env.example`

`SENTIMENT_MODEL`, empty by default (meaning off).

### `src/api/core/collection.py`

Calls the sentiment step after a completed cleaning run.

### `src/api/core/admin.py`

Read-only Comment sentiments pages.

### `src/api/core/tests.py`

`AnalyzeCommentsTests` and new collection tests, all with a fake classifier:
- results stored
- comments without text skipped
- the off switch
- every bad result case
- the purge removes sentiment
- the database checks
- the unknown-model startup error
- the separate processing run
- isolation from the collection run
- no sentiment after a failed clean

### `docs/database_schema.md`, `docs/ER_diagram.mmd` and `docs/ER_diagram.svg`

The schema doc gains `model_version` and the wider unique key. The ER diagram was brought up to date in the same round: it was also missing US-016, US-021, US-022 and US-024's columns.

## How the pieces connect

```text
collect_run(run) -> completed
   '-- process_collection_run(run) -> ProcessingRun (cleaning)
          completed? no  -> stop (no sentiment)
          completed? yes -> analyze_comments(run)
                               SENTIMENT_MODEL empty -> nothing
                               else: CLASSIFIERS[name]() -> classifier
                                     ProcessingRun (sentiment)
                                     batches of text_normalized -> classify -> validate
                                     -> CommentSentiment rows + counts-only report
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
SENTIMENT_MODEL=nope venv/bin/python manage.py check
```

Passing looks like `OK` (275 tests). The second command shows the intended `core.E001` error, because no model is registered yet. It is how you can see the off switch protecting you.

## How to test manually

1. With `SENTIMENT_MODEL` empty (the default), collect a run with comments. `/admin/` → Processing runs shows only the cleaning run, and Comment sentiments is empty.

2. Run `SENTIMENT_MODEL=anything venv/bin/python manage.py check`. It reports `core.E001`.

Real sentiment results appear once part B registers a model.

## Common errors

- **`core.E001 ... is not a registered sentiment model`.** `SENTIMENT_MODEL` is set but no such model is registered. Leave it empty until part B, or check the spelling.

- **No sentiment processing run after a collection.** Either `SENTIMENT_MODEL` is empty, or the cleaning run did not complete, which skips sentiment on purpose.

## Known gaps

- Part B: the real model, its dependencies (`torch`/`transformers` versions that support Python 3.14), its label and score mapping, keeping its download out of tests, and its licence. All of this is listed in `deferred-work.md`.

- The classifier is rebuilt for each collection run. A real model would reload its weights each time. A `ponytail:` comment marks this for part B.

- Compose does not pass `SENTIMENT_MODEL` to the API container yet. Part B adds it with the model.
