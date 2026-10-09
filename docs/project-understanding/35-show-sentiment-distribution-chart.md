# 35 - Show sentiment distribution chart

Story: US-028, Show sentiment distribution chart.

Status note: this document describes the US-028 implementation **after** the code review of 2026-10-09 and the fix that followed it. It builds on the Results card (pages 25 and 32) and the sentiment rules of page 31. Until a real sentiment model exists (US-025 part B), it is checked with seeded rows.

## What this story added

The project's **Results** card now ends with a sentiment chart, one per model:

```text
Sentiment by manual-seed 0
4 comments. Comments collected between <first> and <last>
positive  ██████████░░░░░░░░░░  2 (50.0%)
negative  █████░░░░░░░░░░░░░░░  1 (25.0%)
neutral   █████░░░░░░░░░░░░░░░  1 (25.0%)
mixed     ░░░░░░░░░░░░░░░░░░░░  0 (0.0%)
unknown   ░░░░░░░░░░░░░░░░░░░░  0 (0.0%)
```

When nothing is counted, the card says "No sentiment results yet".

Behind it, the existing summary endpoint, `GET /api/projects/<p>/results/summary/`, returns one more field:

```text
"sentiment": [
  {"model_name": "...", "model_version": "...", "total": 4,
   "labels": {"positive": 2, "negative": 1, "neutral": 1, "mixed": 0, "unknown": 0},
   "first_collected_at": "...", "last_collected_at": "..."}
]
```

The list is empty (`[]`) when nothing is counted.

## Why this matters

The point of sentiment analysis is to see broad audience opinion: is the reaction to these videos mostly positive, mostly negative, or split? The counts in each run's detail (page 31) answer that for one run. The chart answers it for the whole project, at a glance, and narrows with the same date and video filters as the rest of the card.

## Key concept: which labels count

A project can have many runs, and each run can have several sentiment passes. Three rules decide what the chart counts.

| rule | why |
| :-- | :-- |
| only each run's **latest** sentiment pass | the same rule as the run detail (page 31); an older pass was superseded |
| only rows of the model that pass's report names | a stray row of another model version never sneaks in |
| each comment **once** per model, with the label from the newest counted pass | two runs can find the same comment; the card already counts each comment once (page 25) |

The tests pin each rule: an older pass that disagrees, a stray row, and a comment shared by two runs.

## Key concept: never mix models

A "positive" from one model and a "positive" from another are not the same measurement. So if the project's runs used different models, there is **one chart per model**, each with its own name, version, total and dates. They are ordered by model name, then version.

## Key concept: labeled with its collection dates

Each chart states "Comments collected between X and Y", in your browser's local date format: the earliest and latest moment this project's runs collected the comments it counts (`CollectionRunComment.discovered_at`).

The review found that nothing proved the "this project's runs" part. A comment is shared across projects, so a link from someone else's run could have silently widened the range. The fix is a test that gives counted comments links to another owner's run and to a sibling project's run, dated outside the range. The test fails if the filter is removed.

These dates can differ from the card's "Data collected between" line, which describes when the runs found the **videos**. Comments are collected after their video, so the chart's range usually starts later.

## Key concept: a chart without a chart library

Five horizontal bars do not need a library. Each row is plain HTML:

- the label as text;
- a bar: a grey track with a coloured inner `<span>` whose CSS `width` is the share, e.g. `50%`;
- the count and percentage as text, e.g. `2 (50.0%)`.

The bar is marked `aria-hidden`, so a screen reader reads only "positive, 2 (50.0%)". The numbers are always written out, so the meaning never depends on colour or length alone.

The maths lives in a pure function, `sentimentDistribution(labels)`, which is tested on its own. It returns the rows in the fixed label order. When every count is zero, it gives `0.0%` and an empty bar instead of dividing by zero (which would print `NaN%`).

## Key concept: the chart follows the filters, and the purge

The chart arrives in the same response as the card, so US-029's filters (page 32) apply automatically. Pick one video and the chart counts only that video's comments.

The chart counts stored sentiment rows, so after the 30-day purge (page 26) it empties, just like the card's comment counts. The run detail keeps its counts, because those come from the pass's report, which outlives the purge.

## File-by-file explanation

### `src/api/core/views.py`

- `sentiment_distributions(project, video_ids)`: finds each run's latest pass, keeps each comment's newest label per model, and adds the dates. It counts in Python rather than with PostgreSQL's `DISTINCT ON`, which SQLite does not have.
- `ResultsSummaryView`: adds the `sentiment` field, computed over the already-filtered videos.

### `src/api/core/tests.py`

`ResultsSummaryApiTests` gained a test for each case:
- one model with dates, and dates kept inside this project;
- only the latest pass;
- a stray row of another model;
- a shared comment counted once;
- two models;
- no pass, or purged rows;
- another owner's rows;
- the video and date filters.

### `src/ui/src/apiClient.ts` and `src/ui/tests/resultsSummaryApi.test.ts`

The `SentimentDistribution` type, `ResultsSummary.sentiment`, and the check that each entry has a model, a total and all five label counts.

### `src/ui/src/sentimentFormat.ts` and `src/ui/tests/sentimentFormat.test.ts`

`sentimentDistribution` and `SentimentBar`, tested for order, rounding (`33.3%`, `66.7%`) and all zeros.

### `src/ui/src/App.tsx` and `src/ui/src/App.css`

The chart sections in the Results card and the `.sentiment-chart` styles.

## How the pieces connect

```text
GET /api/projects/P/results/summary/?date_from=…&video=…
   filtered videos (US-029)
   each run of P -> latest sentiment pass -> rows of its reported model
      per model: each comment once, newest pass's label
      dates: min/max discovered_at of those comments on P's runs
   -> "sentiment": [one entry per model]

Results card
   counts · "Data collected between …"
   for each model: heading, total + dates, five rows (sentimentDistribution)
   or "No sentiment results yet"
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

Passing looks like `OK` (337 tests), `pass 88`, a finished build and no lint output.

## How to test manually

1. Seed a sentiment pass with page 31's shell snippet. It creates one positive, one negative and one neutral result.

2. Open that run's project in the UI and press **Refresh**. The Results card shows "Sentiment by manual-seed 0": 3 comments, positive, negative and neutral at 1 (33.3%) each, and mixed and unknown at 0 (0.0%).

3. Pick a video in the Results filters and press **Apply**. The chart counts only that video's comments, or says "No sentiment results yet" if it has none.

4. Press **Clear**. The full chart is back.

5. Remove the seed with page 31's cleanup line. The card says "No sentiment results yet" again.

## Common errors

- **"No sentiment results yet" although a run shows sentiment.** Either the filters exclude its videos, or the data was purged: the run detail still shows the report's counts, the chart does not.

- **Two charts.** The runs used different models or versions. That is intended: their labels are not comparable.

- **The chart's dates differ from the card's.** The chart dates the comments; the card dates the videos.

## Known gaps

- The chart covers the project as a whole. A run's own counts stay in its detail (page 31), without bars.

- Counting is done in Python over the project's rows. That is fine at the current per-run caps; a very large project would want it in SQL.
