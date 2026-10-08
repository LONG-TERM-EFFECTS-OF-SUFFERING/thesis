# 30 - Add processing tests

Story: US-036, Add processing tests.

Status note: this document describes the US-036 implementation **after** the code review of 2026-10-08 and the fix that followed it. Like pages 15, 21, 24 and 29, this story added **tests only**.

## What this story added

Processing (page 27: cleaning comment text and reporting on it) already had about 30 tests from US-024 and US-025. An audit found three gaps, and this story fills them:

1. **A table of worked examples**, `NORMALIZATION_EXAMPLES`: ten realistic comments with their exact cleaned text.
2. **A check that the report adds up**, applied to several sets of comments, including 200 generated ones.
3. **Processing on the real collection path:** one end-to-end test that runs `collect_runs` and then inspects the processing run and the cleaned text.

## Why this matters

The thesis says the dataset is cleaned by fixed, documented rules, and that each processing run reports how many comments were usable and why the rest were not. These tests are the evidence: anyone can rerun them and see the exact output for typical comments, and see that the numbers in every report are consistent.

## Key concept: worked examples

Each entry has a comment, its expected cleaned text (or the error `empty_text` / `missing_text`), and the exact set of rules that changed it. Six of the ten:

| comment | cleaned | rules that changed it |
| :-- | :-- | :-- |
| `Man` + combining `~` + `ana sale el pico y placa nuevo, que` + combining accent + ` pereza` | `Mañana sale el pico y placa nuevo, qué pereza` | `nfc` |
| `¡Excelente video! ¿Habrá segunda parte? 🙌🔥` | unchanged | none |
| `Cali &amp; Jamundí: &quot;¿cuándo?&quot; &lt;3 it&#39;s a mess` | `Cali & Jamundí: "¿cuándo?" <3 it's a mess` | `html_unescape` |
| `Fuente: https://www.example.gov.co/estudio?id=12 y más en www.example.com/cali` | `Fuente: <URL> y más en <URL>` | `urls_replaced` |
| `@vecina tienes razón, ESTO NO SIRVE` | unchanged (capitals and mentions are kept) | none |
| only invisible characters (`\u200b\u200d\ufeff`) | nothing: `empty_text` | `chars_removed` |

The comments were written for the test, not copied from real users. Invisible and combining characters are written as `\u...` escapes. The review caught several that had been pasted in raw, which made a test input look like an empty string while it actually held three invisible characters.

## Key concept: a report that adds up

`assert_report_consistent(processing)` checks rules that must hold for **any** completed processing run:

```text
rows_read                  = sum of inputs   (top-level + replies)
rows_written               = sum of written
rows_read − rows_written   = sum of errors   (missing_text + empty_text)
each rule's count          ≤ rows_read
every expected key present, and the current rules version
```

It runs on five sets of comments:
- the earlier messy fixture
- the example table
- a run with no comments
- a run where every comment is invalid
- **200 generated comments**, top-level and replies, built from fixed fragments with a fixed random seed (`random.Random(36)`), so the "random" set is identical on every run

For the generated set, the expected totals are also computed separately, by cleaning each text directly, and compared with the report.

## Key concept: on the real path

One end-to-end test (only Python's network call is faked, as on pages 15 and 24) collects the US-023 audit run with the sentiment model off, then checks:

- exactly one cleaning processing run exists, and it completed;
- its report equals the numbers computed from the comments that were served;
- every comment's `text_normalized` equals the cleaning function applied to its original text;
- no other processing run exists (sentiment stays off).

## Found while testing: joined emoji are split

Rule 3 removes invisible characters, including U+200D, the **zero-width joiner**. Some emoji are several emoji glued together by that character (👨‍👩‍👧 is man + joiner + woman + joiner + girl). After cleaning, they appear as separate emoji: 👨👩👧. This is the rule as approved in US-024, so it was not changed here. It is logged in `deferred-work.md` for a decision: keep the joiner between emoji (and bump the rules version), or accept the split.

## File-by-file explanation

### `src/api/core/tests.py`

- `NormalizationExample`, `NORMALIZATION_EXAMPLES` and `NormalizationExampleTests`.
- `ProcessingReportConsistencyTests`, with `assert_report_consistent` and the five sets of comments.
- `CollectRunsEndToEndTests.test_audit_run_is_normalized_after_collection`.

No product file changed.

## How the pieces connect

```text
NORMALIZATION_EXAMPLES -> normalize_comment_text -> exact text / error / rules

comments (5 controlled sets) -> process_collection_run -> ProcessingRun
                                                             '-- assert_report_consistent

collect_runs (real path, urlopen faked) -> collect_run -> process_collection_run
   -> one completed ProcessingRun, report and text_normalized as computed
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py test core.tests.NormalizationExampleTests core.tests.ProcessingReportConsistencyTests
```

Passing looks like `OK` (288 tests). The second command runs the example and consistency tests on their own.

## How to test manually

This story adds no screen. To see what the consistency check guards, break the counting on purpose. For example, in `process_collection_run` (`src/api/core/processing.py`), stop adding to `errors` for one error code. Run `ProcessingReportConsistencyTests`, watch it fail, then restore with `git checkout core/processing.py`.

## Common errors

- **An example fails after you change a cleaning rule.** That is intended: the table pins the exact output. If the change is deliberate, update the expected values, bump `NORMALIZATION_VERSION`, and say why in the commit.

## Known gaps

- The comments collected on the end-to-end path are already clean, so no rule fires there. The example table and the generated comments cover the rules.

- The joiner question above.
