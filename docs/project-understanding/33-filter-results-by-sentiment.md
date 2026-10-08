# 33 - Filter results by sentiment

Story: US-030, Filter results by sentiment.

Status note: this document describes the US-030 implementation **after** the code review of 2026-10-08 and the fixes that followed it. It builds on the Sentiment section from US-026 (page 31). Until a real sentiment model exists (US-025 part B), it is checked with seeded rows.

## What this story added

A **Sentiment label** dropdown in the run detail's Sentiment section, with "All" plus the five labels: `positive`, `negative`, `neutral`, `mixed` and `unknown`. Picking a label:

- shows only that label's comments in the table, starting at page 1;
- says so above the table: "Showing negative comments";
- leaves the five **label counts** above unchanged. They keep describing the whole pass.

Behind it, the sentiment endpoint takes one optional parameter: `GET /api/projects/<p>/runs/<r>/sentiment/?sentiment=negative`.

## Why this matters

The point of sentiment analysis is to compare audience reaction groups, for example reading the negative comments next to the positive ones. With the counts fixed as a baseline and the table narrowed to one group, a researcher can see both "how many" and "which ones" at the same time.

## Key concept: counts stay, rows narrow

| part of the section | with "negative" selected |
| :-- | :-- |
| model name, version, status | unchanged |
| label counts (all five) | unchanged: the whole pass, from its report |
| "Showing negative comments" | describes the table |
| table, `count`, Previous/Next | only negative rows; page links keep the filter |

The response also echoes the active label as `sentiment_filter`. The sentence above the table is built from that echo, so it always matches what the server actually filtered.

## Key concept: never mix models

A label only means something together with the model that gave it (page 31). The filter therefore sits **on top of** US-026's rules: only rows of the run's **latest** sentiment pass, and only rows whose model name and version equal that pass's. A stray row from another model version, even with the right label, is never shown. A test proves it.

## Key concept: strict input

`parse_sentiment_filter` reads the parameter before anything is queried, and is tested on its own.

| request | answer |
| :-- | :-- |
| `?sentiment=negative` | negative rows |
| `?sentiment=` (empty) | no filter |
| `?sentiment=angry`, or `Negative` | `400`: "Enter one of: positive, negative, neutral, mixed, unknown." |
| `?sentiment=positive&sentiment=negative` | `400`: "Select only one sentiment label." |
| another owner's run, with any filter | `404` |

Repeating the parameter used to slip through: Django's `QueryDict.get` silently returns only the **last** value. The review caught this, and the parser now reads every value with `getlist`. The date and video filters of US-029 (page 32) have the same weakness. It is logged in `deferred-work.md` rather than changed here.

## Key concept: the dropdown appears only when it can work

- It shows only once the run is known to **have** a sentiment pass. Before the review, it flashed while a run's first request was loading, and stayed after an error.
- It stays put, and keeps focus, while another page or label loads.
- On a **purged** run (page 26) it is hidden, together with the "Showing …" sentence. The model and the counts from the report stay, and "Data purged on <date>" replaces the table.
- It resets to "All" when you open another run or project. **Refresh** keeps it.

## File-by-file explanation

### `src/api/core/views.py`

- `parse_sentiment_filter(query)`: the pure parser, beside US-029's `parse_results_filters`.
- `CollectionRunSentimentView`: applies `sentiment_label=<label>` on top of the latest-pass and model filters, and echoes `sentiment_filter`.

### `src/api/core/tests.py`

- `ParseSentimentFilterTests`, including real `QueryDict`s with repeated and empty values.
- `SentimentResultsApiTests` gained tests for:
  - filtered rows with unchanged counts
  - paging by following the API's own `next` link
  - no match
  - bad values, with and without a pass
  - the empty value
  - a stray row of another model version
  - no pass

### `src/ui/src/apiClient.ts`, `src/ui/src/sentimentFormat.ts` and their tests

- `getRunSentiment(projectId, runId, page, sentiment?, signal?)`.
- The guarded `sentiment_filter` field.
- `describeSentimentFilter(label)`, which gives "Showing negative comments" or "Showing all comments".

### `src/ui/src/App.tsx`

The dropdown and its visibility rules. The sentiment state remembers the selected label and whether the pass is already known.

## How the pieces connect

```text
Sentiment section (run R)
   model · version · status
   positive 1 · negative 2 · neutral 2 · mixed 0 · unknown 0   <- whole pass (report)
   [Sentiment label ▾ negative]
   "Showing negative comments"                                 <- from sentiment_filter
   table: negative rows only, page 1 of N

GET /api/projects/P/runs/R/sentiment/?sentiment=negative&page=1
   parse_sentiment_filter -> 400 on bad or repeated values
   latest pass of R -> rows with its model name/version -> sentiment_label = negative
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

Passing looks like `OK` (325 tests), `pass 84`, a finished build and no lint output.

## How to test manually

1. Seed a sentiment pass with page 31's shell snippet. It creates one positive, one negative and one neutral result.

2. Open the run in the UI. The counts read 1 / 1 / 1 / 0 / 0.

3. Pick **negative**. The table shows one row and says "Showing negative comments", and the counts are unchanged.

4. Pick **mixed**. It says "No mixed comments", and the counts are still unchanged.

5. Pick **All**. All three rows come back.

## Common errors

- **`400` "Enter one of: …".** The label is misspelled or capitalised (`Negative`). Labels are lowercase.

- **`400` "Select only one sentiment label."** The parameter was sent twice. Only one label at a time is supported.

- **No dropdown.** The run has no sentiment pass yet, or its data was purged.

## Known gaps

- The filter covers the run detail only. The Results card (page 32) is not filtered by sentiment, by design.

- The labels appear lowercase in the dropdown, matching the counts and the table.

- US-029's filters still accept repeated parameters (in `deferred-work.md`).
