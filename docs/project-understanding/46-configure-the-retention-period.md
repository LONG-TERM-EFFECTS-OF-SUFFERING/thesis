# 46 - Configure the retention period

Story: US-048, Configure the retention period.

Status note: this page describes US-048 after its review of 2026-11-09 and the fixes that followed (`src/api` PR #45, `src/ui` PR #27). The advisor asked for it in his review of thesis commit `753a97d`; see `docs/thesis-review-code-changes.md` item 11.

## What this story added

The retention period is now a setting instead of a constant in the code:

```text
YOUTUBE_RETENTION_DAYS=30   # the default, what the YouTube policy allows
YOUTUBE_RETENTION_DAYS=7    # purge after 7 days
YOUTUBE_RETENTION_DAYS=0    # never purge
```

The hourly purge (page 44) and the deletion dates in the exports (pages 36 and 38) both read it.

- **0:** the purge prints `Skipped: retention is disabled (YOUTUBE_RETENTION_DAYS=0).` and deletes nothing. Every `delete_by` in the exports is empty, and the dataset says `"retention_days": null`.
- **Above 30 or 0:** the app still starts, but Django's system checks print warning `core.W001` at every start, because the YouTube API Services Developer Policies allow at most 30 days. The setting exists for a future change of the policy, not for keeping API data longer.
- **Not a whole number from 0 to 36500** (for example `abc`, `-1`, `+7` or `1000000`): the app refuses to start with `ImproperlyConfigured` and names the variable. The upper bound keeps the date arithmetic inside Python's date range.

## Files

- `opentube_insights_api/settings.py`: `env_int(name, default, maximum)` sits next to `env_bool` and `env_str`. Blank means the default, and only ASCII digits are accepted. `YOUTUBE_RETENTION_DAYS` uses it.
- `core/purge.py`: reads the setting each time it runs. With 0 it returns zero counts, so even a direct call can never delete everything.
- `core/management/commands/purge_youtube_data.py`: checks for "disabled" first, before the US-046 "a run is running" check.
- `core/views.py`: the CSV and dataset exports compute `delete_by` from the setting, or leave it empty at 0.
- `core/checks.py`: `check_retention_days` (`core.W001`), registered in `core/apps.py`.
- `src/.env.example`, `src/api/.env.example` and `src/docker-compose.yml` (`x-api-env`) list the variable, blank by default.

## Key concept: tests must not depend on your configuration

Settings are read from the environment and from `src/api/.env`. If a test reads the live setting, a developer with `YOUTUBE_RETENTION_DAYS=0` in their `.env` would see about 30 tests fail. The review found exactly that. So every test class that relies on the default pins it with `@override_settings(YOUTUBE_RETENTION_DAYS=30)`, and tests for other values set their own. The integration test still compares against a literal 30 on purpose.

## Commands

From `src/api`:

```bash
venv/bin/python manage.py test                              # 405 tests
YOUTUBE_RETENTION_DAYS=0 venv/bin/python manage.py check    # prints core.W001, exits 0
YOUTUBE_RETENTION_DAYS=0 venv/bin/python manage.py purge_youtube_data --dry-run
```

## Common errors

- **`ImproperlyConfigured: YOUTUBE_RETENTION_DAYS must be a whole number …`**: the value in `.env` is not plain digits, or it is above 36500.
- **`core.W001` at every start**: the value is 0 or above 30. That is allowed, but it no longer follows the YouTube policy.
