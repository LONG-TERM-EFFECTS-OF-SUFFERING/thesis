---
title: 'US-048 Configurable retention period'
type: 'feature'
ticket: ''
created: '2026-11-09'
status: 'done'
baseline_revision: 'api=122943fa113abce30e2727ae28a1d90b86781cca ui=ea61084ea42173671922475a5de2222be25f8462 thesis=a12777d23e161c46ae83d16487dd26448b6537f2'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The 30-day retention period is the constant `RETENTION_DAYS` in `core/purge.py`. The advisor asked for it to be configurable, so a future policy change does not need a code change, and he asked for a way to turn the purge off.

**Approach:** A non-secret setting, `YOUTUBE_RETENTION_DAYS`, read through the env helpers: default 30, where `0` means no purge. The purge, the exports' `delete_by` dates and the dataset's `retention_days` all read it. A Django system-check warning fires when the value is above 30 or 0, because the YouTube API Services Developer Policies (III.E.4) allow at most 30 days.

## Boundaries & Constraints

**Always:**
- Blank or missing means 30. A non-integer or negative value fails loudly at startup (`ImproperlyConfigured`).
- With `0`, `purge_youtube_data` prints one line saying retention is disabled, deletes and stamps nothing, and exits 0. Check this before the US-046 running-run check. With `0`, the exports write an empty `delete_by` and the dataset writes `retention_days: null`.
- The warning is a `Warning` (`core.W001`), not an `Error`: the app still starts.
- Existing behavior at the default (30) is unchanged, and every existing test passes.

**Never:**
- No database or migration change, and no UI to edit the value. It is an operator setting, like the other keys.
- No secret-style failure: the value has a safe default.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default | variable unset or blank | 30 days, no warning | — |
| Shorter | `7` | data older than 7 days is purged; exports' `delete_by` = collected + 7 days | — |
| Disabled | `0` | purge prints the disabled line and deletes nothing; `delete_by` empty; `retention_days` null; warning `core.W001` | — |
| Above policy | `45` | purge uses 45 days; warning `core.W001` | — |
| Invalid | `abc` or `-1` | startup fails naming the variable | `ImproperlyConfigured` |

</frozen-after-approval>

## Code Map

- `src/api/opentube_insights_api/settings.py`: `env_bool`, `env_str` and `env_list` live here. Add an `env_int(name, default, environ)` beside them with the same docstring style. It reads through `env_str` (blank means the default) and raises `ImproperlyConfigured` for non-integers and negatives. Then add `YOUTUBE_RETENTION_DAYS = env_int("YOUTUBE_RETENTION_DAYS", 30)` near the other YouTube settings, with a comment citing III.E.4.d.
- `src/api/core/purge.py`: replace `RETENTION_DAYS = 30` and its "policy, not configuration" comment with a read of the setting at call time (for example `retention_days()`). `purge_youtube_data` computes `cutoff` from it, and with 0 the command returns before calling it.
- `src/api/core/management/commands/purge_youtube_data.py` `Command.handle`: the disabled check goes first.
- `src/api/core/views.py`:
  - CSV export: `row["delete_by"]` ~527.
  - `ProjectDatasetExportView`: `retention` ~558 and `"retention_days"` ~585.
  - With 0, `delete_by` is `None`, as for request logs.
- `src/api/core/checks.py`: add `check_retention_days` (`core.W001`) next to `check_sentiment_model`, and register it in `core/apps.py`.
- Tests:
  - These files import `RETENTION_DAYS` from `core.purge`: `test_purge.py`, `test_exports.py`, `test_processing.py` and `test_sentiment.py`. Point them at the setting, or at a module helper, without changing what they assert.
  - `test_workflow.py` keeps its literal 30 on purpose.
  - Add a test for `env_int` in `test_settings.py`.
  - Add tests for 7 and 0 in `test_purge.py`, the 0 case in `test_exports.py`, and the check.
- `src/api/README.md`: document the setting and the dataset's `retention_days` (now integer or null).
- `src/ui/src/ResultsSection.tsx` export note (~200) and its `i18n.ts` entry: "30 days after it was fetched" becomes "the retention period, 30 days by default, after it was fetched".
- Thesis repo, committed there: `src/.env.example` and `src/docker-compose.yml` `x-api-env` get `YOUTUBE_RETENTION_DAYS: ${YOUTUBE_RETENTION_DAYS:-}`.

## Tasks & Acceptance

**Execution:**
- [x] `settings.py`: `env_int` and the setting.
- [x] `purge.py`, the purge command and `views.py`: read the setting and handle 0.
- [x] `checks.py` and `apps.py`: `core.W001`.
- [x] Tests for the matrix. Removing the 0 branch must fail a test.
- [x] README, the UI note, `.env.example` and the Compose environment.

**Acceptance Criteria:**
- Given the default configuration, when the full backend suite runs, then it passes unchanged apart from the import updates.
- Given `YOUTUBE_RETENTION_DAYS=0`, when `manage.py check` runs, then `core.W001` is printed and the command still succeeds.

## Review Triage Log

Pass 1 (quick), 8 findings: 7 patch (2 medium, 5 low), 1 reject.

- **medium, patch.** The tests now read the live setting, which `settings_environ` takes from `.env` and the OS. With `YOUTUBE_RETENTION_DAYS=0` the reviewer saw 30 failures; with 7 or 45, `test_workflow` fails on its literal 30. Fix: pin `override_settings(YOUTUBE_RETENTION_DAYS=30)` on the affected test classes.
- **medium, patch.** No upper bound. `1000000` raises `OverflowError` in `purge.py`, which the Compose `|| true` hides every hour, and larger values make the exports return 500. Fix: `env_int` rejects values above a maximum (36500 days) with `ImproperlyConfigured`.
- **low, patch.** "30-day" wording is left in `views.py`, `models.py`, `processing.py`, `sentiment.py` and `results.py` docstrings, and the `test_workflow` comment names the removed `RETENTION_DAYS`.
- **low, patch.** The matrix rows Shorter (exports at 7) and Above policy (purge at 45) have no tests.
- **low, patch.** The acceptance criterion is checked only through `run_checks()`. Fix: add one `call_command("check")` test at 0.
- **low, patch.** The UI export note says only request logs have an empty `delete_by`; with 0, every row does.
- **low, patch.** `env_int` accepts `+7`, `1_0` and non-ASCII digits through `int()`. Fix: ASCII digits only.
- **reject.** Thesis-repo changes are on `main`. The thesis repo commits to `main` by practice (no PRs since US-009). The two `src/` files get their own commit, separate from the uncommitted prose edits.

## Design Notes

Why a warning and not an error: the setting exists for a future change of the policy, which the code cannot know. The warning tells the operator, at every start, that the value leaves the policy as of 2026.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test` -- expected: all pass.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.
- `cd src/ui && npm test && npm run build` -- expected: pass.
- `cd src && docker compose config --quiet` -- expected: exit 0.
