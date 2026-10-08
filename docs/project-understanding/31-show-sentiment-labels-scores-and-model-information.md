# 31 - Show sentiment labels, scores and model information

Story: US-026, Show sentiment labels, scores and model information.

Status note: this document describes the US-026 implementation **after** the code review of 2026-10-08 and the fixes that followed it. It builds on US-025 part A (page 28). Until a real model is plugged in (part B), the section only shows data you seed by hand (see "How to test manually").

## What this story added

- **An endpoint:** `GET /api/projects/<project_id>/runs/<run_id>/sentiment/`. It returns the run's most recent sentiment pass and its results, 50 per page.
- **A Sentiment section** in the run detail of the Collection runs panel, between Discovery and Requests. It shows:
  1. the **model name and version**, the pass's status and when it finished, always above the results;
  2. the count for each of the five labels, written as text;
  3. a table with each comment's level, text, label, score, confidence and language, with Previous and Next buttons when there are more than 50.

## Why this matters

A sentiment label means little without knowing which model produced it. "Positive" from one model is not the same claim as "positive" from another, or from a newer version of the same one. The thesis needs every result shown with its model context, so a reader can interpret, compare and reproduce it. That is why the model name and version sit **above** the results, never in a tooltip.

## Key concept: what the endpoint returns

```json
{
  "sentiment": {
    "status": "completed", "error_message": null,
    "model_name": "...", "model_version": "...",
    "started_at": "...", "finished_at": "...",
    "labels": {"positive": 1, "negative": 1, "neutral": 1, "mixed": 0, "unknown": 0}
  },
  "model_configured": false,
  "count": 3, "next": null, "previous": null,
  "results": [
    {"comment_level": "top_level", "text_display": "...",
     "sentiment_label": "positive", "sentiment_score": 0.8, "confidence": 0.9,
     "language_code": "es", "model_name": "...", "model_version": "..."}
  ]
}
```

- **`sentiment`** describes the **most recent** sentiment pass of the run, or is `null` if there is none. Older passes (for example after a model change) stay visible in `/admin/`.
- **`model_configured`** says only **whether** a sentiment model is set (`SENTIMENT_MODEL`), never which one. The UI uses it to explain an empty section.
- **`results`** holds only rows of the stated model and version, so a row can never disagree with the heading. Rows are ordered top-level comments first, then by publish time, then by ID, so pages don't shuffle.
- No YouTube IDs are included.

## Key concept: numbers shown honestly

| value | shown as |
| :-- | :-- |
| score 0.8 / −0.75 / 0 | `+0.80` / `-0.75` / `0.00` |
| confidence 0.9 | `90%` |
| missing score or confidence | `—`, **never** `0` or `0%` |

A missing value is not zero. Showing `0%` would invent a fact. The small helpers in `src/ui/src/sentimentFormat.ts` do this formatting and are tested.

## Key concept: counts that survive the purge

The label counts come from the sentiment pass's **report**, not from counting result rows. The 30-day purge (page 26) deletes comments, and their sentiment rows go with them, but processing runs and their reports are kept. Counting rows would have shown all zeros after a purge. The code review caught this.

After a purge, the section keeps the model and the counts and says **"Data purged on <date>"** in place of the table, the same way the Discovery section does (page 19).

## Key concept: every state has a message

| situation | the section shows |
| :-- | :-- |
| no sentiment pass yet | "No sentiment results yet", plus a hint while no model is configured |
| pass running | the model, version and status `running` (a review fix: a pass now records its model when it **starts**) |
| pass failed | the failure and its error class name, not an empty table |
| data purged | the model, the counts and "Data purged on <date>" |
| results | the model, the counts and the table |

## File-by-file explanation

### `src/api/core/views.py`, `serializers.py` and `urls.py`

- `CollectionRunSentimentView` finds the run through `get_project()`, so another owner's or another project's run is a `404`. It is read-only, so writes get a `405`.
- `CommentSentimentSerializer` shapes each row, with score and confidence as JSON numbers, not strings.
- The route is named `project-run-sentiment`.

### `src/api/core/sentiment.py`

`analyze_comments` (from US-025) now builds the classifier first and creates the pass with its model name and version already in the report, so a running pass is visible. Its existing tests still pass.

### `src/api/core/tests.py`

`SentimentResultsApiTests` covers:

- the results, with every row's model checked against the heading
- no pass yet
- a failed pass
- missing numbers
- foreign and unknown runs (`404`) and writes (`405`)
- paging over 120 rows
- the latest pass winning
- rows of another model version left out
- counts kept after the comments are deleted
- a running pass showing its model

### `src/ui/src/apiClient.ts`, `src/ui/src/sentimentFormat.ts` and their tests

The types, a guard that checks the JSON shape (all five labels, numbers that are numbers), the fetcher, and the formatting helpers.

### `src/ui/src/App.tsx` and `src/ui/src/App.css`

The Sentiment section and its pager. Loading follows the same late-response guards as the rest of the panel (page 16).

## How the pieces connect

```text
run detail (project P, run R)
   '-- getRunSentiment(P, R, page)
          GET /api/projects/P/runs/R/sentiment/?page=N
             get_project() + run of P      -> 404 otherwise
             latest pass with a model_name -> summary (labels from its report)
             rows of that pass and model   -> 50 per page
   <- Sentiment section: model + version, label counts, table | state message
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
cd ../ui
npm test
npm run build
npm run lint
```

Passing looks like `OK` (299 tests), `pass 73`, a finished build and no lint output.

## How to test manually

No real sentiment model exists yet (part B), so seed a fake pass by hand in your **development** database. You need a collected run that has comments (page 22).

1. `cd src/api && venv/bin/python manage.py shell`, then paste:

   ```python
   from decimal import Decimal
   from django.utils import timezone
   from core.models import CollectionRun, CommentSentiment, ProcessingRun

   run = CollectionRun.objects.filter(run_comments__isnull=False).distinct().latest("created_at")
   comments = [link.comment for link in run.run_comments.select_related("comment")[:3]]
   report = {"model_name": "manual-seed", "model_version": "0", "inputs": len(comments),
             "labels": {"positive": 1, "negative": 1, "neutral": 1, "mixed": 0, "unknown": 0},
             "skipped_no_text": 0}
   pr = ProcessingRun.objects.create(project=run.project, collection_run=run, status="completed",
                                     started_at=timezone.now(), finished_at=timezone.now(),
                                     summary_payload=report)
   for comment, label, score in zip(comments, ["positive", "negative", "neutral"],
                                    [Decimal("0.8"), Decimal("-0.75"), Decimal("0")]):
       CommentSentiment.objects.create(processing_run=pr, comment=comment,
           model_name="manual-seed", model_version="0", sentiment_label=label,
           sentiment_score=score, confidence=Decimal("0.9"), language_code="es")
   ```

2. Open the UI at `http://localhost:5173/`, click **Refresh** in the Collection runs panel, and open that run. The Sentiment section shows `manual-seed`, version `0`, the counts 1/1/1/0/0, and three rows with `+0.80`, `-0.75` and `0.00`, each at `90%`.

3. Compare with `http://127.0.0.1:8000/admin/` → Comment sentiments.

To remove the seed afterwards: in the same shell, run `ProcessingRun.objects.filter(summary_payload__model_name="manual-seed").delete()`. The sentiment rows go with it.

## Common errors

- **"No sentiment results yet".** No sentiment pass exists for this run. Without a configured model, that is expected (page 28).

- **Counts show, but the table says "Data purged on …".** The run's YouTube data was purged after 30 days. The counts come from the kept report.

- **The section shows a model you don't recognise.** It shows the **latest** pass. Older passes are in `/admin/` → Processing runs.

## Known gaps

- The section has no automated render test (no React test setup yet). The manual check above covers it.

- Only the latest pass is shown in the app.

- Real results arrive with US-025 part B.
