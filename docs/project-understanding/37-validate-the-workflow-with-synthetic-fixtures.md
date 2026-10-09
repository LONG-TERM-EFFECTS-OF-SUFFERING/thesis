# 37 - Validate the workflow with synthetic fixtures

Story: US-038, Validate the workflow with synthetic fixtures.

Status note: this document describes the US-038 implementation **after** the code review of 2026-10-09 and the fixes that followed it. Like pages 15, 24, 29, 30 and 34, this story added **tests only**.

## What this story added

One test runs the **whole workflow** in a single pass, offline: `SyntheticWorkflowTests.test_prompt_to_export_on_the_synthetic_corpus`. Every step goes through the same entry point the app uses:

| step | entry point | what is checked |
| :-- | :-- | :-- |
| 1. draft | `POST /api/projects/<p>/queries/draft/` | the exact draft, and one request to OpenAI so far |
| 2. review and save | `POST /api/projects/<p>/queries/` | `query_source` is `llm_generated`, parameters kept |
| 3. start | `POST /api/projects/<p>/queries/<q>/runs/` | a `pending` run |
| 4. collect | `manage.py collect_runs` | run `completed`, all totals, the requests in order, and the search used the saved query |
| 5. clean | runs after collection | the full processing report and one cleaned text |
| 6. sentiment | runs after cleaning | the model and the label counts |
| 7. results | `GET .../results/summary/` | the card's counts and the chart's sentiment entry |
| 8. export | `GET .../export/videos.csv` | two rows, `delete_by` 30 days after `collected_at` |

Two smaller tests sit beside it:
- the fake network refuses any address outside the corpus;
- running `collect_runs` again with nothing pending sends nothing and changes no rows.

## Why this matters

Pages 15, 24, 29 and 30 test each part on its own. Parts can each work and still not fit together: a saved query that collection ignores, or a cleaning step that never runs after collection. This test is the evidence that the parts **connect**, from a researcher's sentence to the file they download, and it runs on every `manage.py test` without the OpenAI or YouTube APIs. US-039 later repeats the path on real topics.

## Key concept: a synthetic corpus

The test runs on a tiny dataset written for it, with no real ids, names or comments:

- 2 videos (`SynthVid001`, `SynthVid002`) on 1 channel (`Synthetic Fixture Channel`);
- 3 top-level comments and 1 reply, by `@synthetic-author-1` to `@synthetic-author-4`;
- texts chosen so the test's fake sentiment model gives 1 positive (`good`), 1 negative (`bad`) and 2 neutral;
- one comment, `Synthetic fixture: a good  route` + new line + `see https://example.invalid/route`, that three cleaning rules change into `Synthetic fixture: a good route see <URL>`.

Every response has the shape YouTube and OpenAI document, including `etag` and `pageInfo`.

The review found that the first version reused older fixture builders whose defaults (`@vecina`, "Canal Movilidad", Cali tags) leaked into the corpus, and into the CSV the thesis would cite. Those are now overridden with clearly synthetic values.

## Key concept: fake only the network

The only thing replaced is Python's `urllib.request.urlopen`, the function that would open a connection. Everything above it runs for real: the views, the translation code, `collect_run`, cleaning, the sentiment step, the summary and the export. The fake answers by address:

- `api.openai.com/v1/responses` gets the draft;
- `www.googleapis.com/youtube/v3/search`, `videos`, `channels`, `commentThreads` (by video) and `comments` (by parent comment) get the corpus;
- **anything else** is recorded and refused.

Collection catches every error and marks the run `failed`, so a refused address would otherwise surface only as "status is not completed". The review caught that. The collection stage now also asserts that nothing unexpected was sent, and the failure names the address.

The sentiment model is the existing test fake (`FakeClassifier`, page 28). No real model exists yet (US-025 part B), and none is needed to prove the path.

## Key concept: a test that can fail at each stage

A long test is only useful if it says **where** it broke.

- **The read stages** (collect to export) are `subTest`s named `collection`, `processing`, `sentiment`, `summary` and `export`.
- **Draft, save and start** stop the test at once, with a `stage=` message. A failed draft no longer cascades into errors in every later stage, which the review caught.

Each stage was broken on purpose once, to prove its check works:

| broken on purpose | stage that fails |
| :-- | :-- |
| the draft drops `relevanceLanguage` | draft |
| `query_source` always `manual` | save |
| collection drops the saved search terms | collection |
| replies not collected | collection |
| cleaning not run, or the URL rule does nothing | processing |
| `SENTIMENT_MODEL` read as empty | sentiment |
| the summary miscounts replies | summary |
| `RETENTION_DAYS = 29` | export |

The "collection drops the saved search terms" row was added by the review. Before, the fake answered the search by path alone, so collection could have ignored the reviewed query and the test would still pass. Now the search request's logged parameters must equal the saved ones.

The export stage compares against a literal 30 days, not `RETENTION_DAYS`, so a change to the retention policy has to be made knowingly.

## File-by-file explanation

### `src/api/core/tests.py`

- **The corpus:**
  - `SYNTHETIC_PROMPT`, `SYNTHETIC_DRAFT_RESPONSE`, `SYNTHETIC_YOUTUBE`, `SYNTHETIC_COMMENT_PAGES`, `SYNTHETIC_REPLY_PAGES` and `SYNTHETIC_LABELS`;
  - the small `_synthetic_*` builders that wrap the existing fixture builders with synthetic values.
- **`SyntheticWorkflowTests`:**
  - `serve` is the address router;
  - `draft`, `save`, `start` and `collect` each run one step;
  - three tests: the full path, the stray request, and the rerun.

No product file changed.

## How the pieces connect

```text
"Synthetic fixture: videos about an invented transit line, at most 2"
   POST draft   --urlopen--> fake api.openai.com      -> draft parameters
   POST save    (reviewed: name + comment/reply limits) -> saved query
   POST start                                          -> pending run
   collect_runs --urlopen--> fake googleapis.com        -> 2 videos, 1 channel, 3 + 1 comments
        '-- process_collection_run -> report, text_normalized
        '-- analyze_comments (FakeClassifier) -> 1 / 1 / 2 / 0 / 0
   GET summary  -> counts + sentiment entry (the chart)
   GET videos.csv -> 2 rows, delete_by = collected_at + 30 days
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py test core.tests.SyntheticWorkflowTests -v 2
```

Passing looks like `OK` (351 tests). The second command lists the three synthetic tests, each `ok`.

## How to test manually

This story adds no screen. To see a stage fail:

1. Break one stage on purpose. For example, in `collect_run` in `src/api/core/collection.py`, replace `process_collection_run(run)` with `None`, so cleaning never runs after collection.

2. Run `venv/bin/python manage.py test core.tests.SyntheticWorkflowTests`. The first failure is reported under `stage=processing`. Sentiment fails too, because it only runs after a completed clean.

3. Restore the file with `git checkout core/collection.py`.

## Common errors

- **`Stub was sent: [...]`.** The code asked for an address the corpus does not serve, for example a new YouTube endpoint. Add it to the corpus deliberately, or find out why it is called.

- **A failure under one stage after you change a count.** The values are exact on purpose. If the change is intended, update the expected value and say why in the commit.

## Known gaps

- This is a test, not a demo. The running app still needs real keys to collect, which you decided (US-039 covers real topics).

- The sentiment labels come from the test fake, so they prove the path, not the quality of a model.

- The presentation layer is not rendered here. The test checks the data the chart and card draw; screen smoke tests are US-037.
