---
title: 'Add processing tests'
type: 'chore'
ticket: '6'
created: '2026-10-08'
status: 'built'
baseline_revision: '2f852a47d1c850113393220e27e4b8d11d1eb452'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: [quick]
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** US-036 asks for processing tests with controlled data, covering processing run creation, normalization, validation counts and error reporting. US-024 and US-025 already left about 30 such tests. Three gaps remain:
- processing never runs on the real collection path (the end-to-end collection tests never look at the processing run or `text_normalized`);
- no test proves that the report's counts are consistent with each other;
- there is no table of realistic comments with exact expected output.

**Approach:** Add tests only:
- a worked-example table of realistic comments;
- a reusable report-consistency check applied to several controlled corpora, including a deterministic generated one;
- an end-to-end test that runs `manage.py collect_runs` with only `urllib.request.urlopen` stubbed and then checks the normalization run and the cleaned text.

## Boundaries & Constraints

**Always:**
- **Example table:** a module-level `NORMALIZATION_EXAMPLES` in `src/api/core/tests.py`, beside the other fixtures. It holds at least eight realistic YouTube comments, Spanish and English, each with its exact expected `text_normalized` (or the error code) and the exact set of rules that changed it. The cases cover:
  - accents (composed and decomposed), `ñ`, `¡`/`¿` and emoji;
  - several lines, HTML entities from `textDisplay`, and URLs in text;
  - upper-case words (kept), an `@mention` (kept: no rule touches it);
  - a comment that is only emoji (kept), and one that is only invisible characters (`empty_text`).

  Whole values are compared with `assertEqual`, never substrings. A comment notes that the texts are written for the test, not copied from real users.
- **Report consistency,** a helper `assert_report_consistent(processing)` that checks, for any completed normalization run:
  - `rows_read == sum(inputs.values())`;
  - `rows_written == sum(written.values())`;
  - `rows_read - rows_written == sum(errors.values())`;
  - every `rules` count is ≤ `rows_read`;
  - every key in `RULE_NAMES`, `ERROR_CODES` and both comment levels is present;
  - the report's `normalization_version` equals `NORMALIZATION_VERSION`.

  It is applied to the messy fixture, to the example table, to a run with no comments, to a run where every comment is invalid, and to a **deterministic generated corpus**: 200 comments built from fixed fragments with `random.Random(36)`, mixing top-level comments and replies. For the generated corpus, the expected `written` and `errors` totals are also computed independently, by calling `normalize_comment_text` on each text, and compared with the report.
- **End-to-end:** reuse `CollectRunsEndToEndTests` (only `urlopen` stubbed, a fake that raises on any unexpected request) and the US-023 audit run setup. After `collect_runs`:
  - exactly one completed normalization `ProcessingRun` exists for the collection run;
  - its report equals the values computed from the served comment and reply items;
  - each stored comment's `text_normalized` equals `normalize_comment_text` applied to its `text_original`;
  - with `SENTIMENT_MODEL` empty, no sentiment processing run exists.
- Each new assertion is mutation-checked once and recorded in Implementation Notes.
- No network. Validated on Compose PostgreSQL.

**Never:**
- No product code changes. If a test exposes a defect, stop and report it.
- No real user comments copied into fixtures.
- No moving or splitting existing tests.
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Worked examples | each `NORMALIZATION_EXAMPLES` entry | exact normalized text or error code, exact changed-rule set | No error expected |
| Consistency, fixtures | the messy fixture, the examples, no comments, all invalid | `assert_report_consistent` passes | No error expected |
| Consistency, generated | 200 seeded comments (top-level and replies) | consistent, and `written`/`errors` equal the independently computed totals | No error expected |
| End-to-end | `collect_runs` on the audit run with `urlopen` stubbed | one completed normalization run; report and `text_normalized` as computed; no sentiment run | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/tests.py`:
  - `NormalizeCommentTextTests` and `ProcessCollectionRunTests` (with `make_comment` and `make_messy_comments`) show the style to follow.
  - `CollectRunsEndToEndTests.start_audit_run` (US-023), with `_AUDIT_THREADS` and `_AUDIT_REPLIES`, sets up the end-to-end run.
  - Add `NormalizationExampleTests(SimpleTestCase)`, a `ProcessingReportConsistencyTests(APITestCase)` holding the helper and the corpora, and one new test in `CollectRunsEndToEndTests`.
- `src/api/core/normalization.py` (`normalize_comment_text`, `RULE_NAMES`, `ERROR_CODES`, `NORMALIZATION_VERSION`) and `src/api/core/processing.py` (`process_collection_run`) -- read-only references.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/tests.py` -- `NORMALIZATION_EXAMPLES` and `NormalizationExampleTests`.
- [x] `src/api/core/tests.py` -- `assert_report_consistent` and `ProcessingReportConsistencyTests`, including the generated corpus.
- [x] `src/api/core/tests.py` -- the end-to-end processing test.

**Acceptance Criteria:**
- Given the consistency tests, when `process_collection_run` stops counting an error (or counts a written row twice), then they fail.
- Given the end-to-end test, when `collect_run` stops calling `process_collection_run`, then it fails.
- `git diff --stat 2f852a4 -- core/ ':!core/tests.py'` is empty.

## Implementation Notes

- All changes are in `src/api/core/tests.py` (+295 lines): imports of `random`, `ERROR_CODES` and `RULE_NAMES`; `NormalizationExample` and `NORMALIZATION_EXAMPLES` (10 entries) before `NormalizeCommentTextTests`; `NormalizationExampleTests` after it; `_GENERATED_FRAGMENTS` and `ProcessingReportConsistencyTests` after `ProcessCollectionRunTests`; `test_audit_run_is_normalized_after_collection` in `CollectRunsEndToEndTests`.
- `ProcessingReportConsistencyTests` reuses `setUp`, `make_comment` and `make_messy_comments` from `ProcessCollectionRunTests` as class attributes, so no existing test moved and no fixture is duplicated.
- `assert_report_consistent` compares key sets with equality, so it rejects missing keys and unexpected extra ones.
- The end-to-end test identifies the normalization run by `summary_payload__has_key="normalization_version"`; `ProcessingRun` has no kind field. "No sentiment run" is checked as "no other processing run for this database".
- The audit texts are already clean (every rule count is 0), so the end-to-end test proves processing ran and wrote, not that a rule fired on the collection path; the rules are covered by the examples and the generated corpus.
- Finding, not tested: `chars_removed` strips U+200D, which splits zero-width-joiner emoji (a family emoji becomes three separate emoji). The table avoids such emoji; whether that is a defect is a product decision.

Mutation checks (product file edited, the four new test groups run on Compose PostgreSQL, file restored):

| Mutation | Fails |
|---|---|
| `process_collection_run` stops counting errors | `rows_read - rows_written == sum(errors)` in messy, examples, invalid, generated |
| `written` counted twice | the same assertion, plus the end-to-end report |
| a rule counted twice | `rules` count <= `rows_read` (messy, invalid, generated); table rule counts (examples) |
| `nfc_final` key only appears when it fires | key-set check (no comments, invalid, examples); end-to-end report |
| report version `comment-text-v1` | version check in every corpus; end-to-end report |
| `inputs` doubled, `rows_read` kept right | `rows_read == sum(inputs)` in every non-empty corpus |
| `written` doubled, `rows_written` kept right | `rows_written == sum(written)` |
| every error counted as `missing_text` | generated independent `errors`; examples and invalid error counts |
| every written row counted as top-level | generated independent `written`; end-to-end report |
| U+200D dropped from the zero-width set | `only_invisible_characters` example |
| first `nfc` rule removed | `decomposed_accents_and_enye_composed` rule set |
| `collect_run` skips `process_collection_run` | end-to-end: one normalization run (0 != 1) |
| `text_normalized` written as null | end-to-end per-comment `text_normalized` |
| every input counted as top-level | end-to-end report |
| `analyze_comments` ignores an empty `SENTIMENT_MODEL` | end-to-end: no other processing run |

- Orchestrator check: 288 OK on PostgreSQL; product diff empty. Thesis baseline `9f007e7aadd4ead10bce303dc3a4f27916feb803`.

- Review patch (pass 1) applied by the orchestrator: raw invisible characters escaped. Full suite 288 OK on PostgreSQL; product diff empty.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 1, false 0, maybe-false 0, defer 1.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| New fixtures contain raw combining, zero-width and BOM characters although the comment says they are escaped; invisible to readers; `ruff` PLE2515 flags them | low | patch | Confirmed; the baseline had none. Orchestrator escaped all 13 raw `Mn`/`Cf`/non-ASCII `Zs` characters as `\uXXXX`; PLE2515 clean; no raw strings affected; suite 288 OK. |
| Implementer report: rule 3 removes U+200D (zero-width joiner), splitting joined emoji sequences (a family emoji becomes three emoji) | low | defer | Confirmed by running the normalizer. Product behavior approved in US-024's frozen rules; out of scope for this tests-only story. Logged in deferred-work for a decision. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && git diff --stat 2f852a4 -- core/ ':!core/tests.py'` -- expected: empty.
