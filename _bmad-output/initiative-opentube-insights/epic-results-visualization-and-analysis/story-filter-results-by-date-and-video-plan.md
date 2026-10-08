---
title: 'Filter results by date and video'
type: 'feature'
ticket: '3'
created: '2026-10-08'
status: 'built'
baseline_revision: '89b97aa8fec9b7bf6954953255379748a6a2ea3c'
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

**Problem:** A researcher cannot focus the results on one slice of a project, such as a date range or a single video (US-029).

**Approach:** Add a date-range filter and a video selector to the **Results** panel. They narrow the summary card's counts through query parameters on the existing summary endpoint. A small endpoint lists the project's videos for the selector. Later results views (the sentiment chart in US-028, the sentiment filter in US-030) reuse the same parameters.

## Boundaries & Constraints

**Always:**
- **Parameters** on `GET /api/projects/<project_id>/results/summary/`, all optional and combinable: `date_from`, `date_to` (ISO dates `YYYY-MM-DD`, inclusive, applied to `youtube_published_at` as in Decisions) and `video` (the internal `YouTubeVideo` UUID).
  - A bad date, `date_from` after `date_to`, or a malformed UUID gives 400 with a message per field.
  - A well-formed `video` that is not linked to the project gives 404, so it never leaks another project's data.
- **What narrows:** with filters, the counts cover only the matching videos and the comments, replies and snapshots linked to them through **this project's** runs. That keeps US-027's project scoping and distinct counting. The response echoes the applied filters in `filters`. Without parameters, the response is unchanged from US-027.
- **Selector source:** `GET /api/projects/<project_id>/results/videos/` lists the project's distinct linked videos as `{id, title, youtube_published_at}`, ordered by title. It is read-only, scoped through `get_project()`, and has no YouTube IDs.
- **UI:**
  - two `<input type="date">` and one `<select>` (native controls; no date-picker library);
  - Apply and Clear buttons;
  - the card states the active filters ("Showing videos … from … to …");
  - fetches follow the AGENTS.md late-response rule, and changing project resets the filters.
- **Validation:** query-parameter parsing is pure and tested. No `any`. JSDoc on new exports.
- Validated on Compose PostgreSQL.

**Decisions** (approved by the human on 2026-10-08):
- **Scope:** the filters apply to the Results panel only. Today that is the summary card; US-028's chart and US-030's sentiment filter will reuse the same query parameters. Per-run sections are untouched.
- **Date field:** `date_from`/`date_to` filter on the video's YouTube publish date (`youtube_videos.youtube_published_at`), inclusive, by calendar day in UTC (`date_from` ≤ the day of `youtube_published_at` ≤ `date_to`). A video with a null `youtube_published_at` is excluded whenever a date bound is given. The card's "Data collected between" line keeps US-027's meaning (run-video `discovered_at`), but is computed over the filtered videos.

**Never:**
- No charts (US-028) and no sentiment filter (US-030).
- No filtering of the run detail (Discovery, Sentiment, Requests): that is per-run already.
- No saved filter presets.
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No filters | summary without parameters | identical to US-027's response, plus `filters: {}` | No error expected |
| Date range | `date_from`/`date_to` around 2 of 3 videos' publish dates | counts cover those 2 videos and their comments, replies and snapshots | No error expected |
| Day bounds | a video published at `2026-03-31T23:59:59Z`, `date_to=2026-03-31` | included; with `date_to=2026-03-30` excluded | No error expected |
| No publish date | a video with null `youtube_published_at`, any date bound | excluded; without date bounds it counts | No error expected |
| One video | `video=<id>` | counts for that video only; `videos` 1 | No error expected |
| Combined | a date range that excludes the selected video | all counts 0 | No error expected |
| Bad input | `date_from=2026-13-01`, `date_from` > `date_to`, or `video=abc` | no data | 400 per field |
| Foreign video | the UUID of a video linked only to another project or owner | no data | 404 |
| Video list | project with 3 linked videos, one also in another project | 3 entries, title order, no YouTube IDs; another project's videos absent | No error expected |
| UI late response | the filters change while a request is in flight | the stale response is dropped | abort + identity check |

</frozen-after-approval>

## Code Map

- `src/api/core/views.py` `ResultsSummaryView` -- parse the parameters with a new pure helper (`parse_results_filters(query) -> filters | errors`) and apply them to the existing aggregate querysets. Keep the US-027 distinct counts and project scoping. Add a `ProjectVideoListView`.
- `src/api/core/urls.py` -- `projects/<uuid:project_id>/results/videos/` (`project-results-videos`).
- `src/api/core/tests.py` -- extend `ResultsSummaryApiTests` (one test per matrix row), plus unit tests for the parser.
- `src/ui/src/apiClient.ts` -- a `filters` argument for `getResultsSummary`, a video-list type, guard and fetcher. A new `src/ui/src/resultsFilters.ts` holds pure helpers that build the query string and describe active filters, with `node --test` tests.
- `src/ui/src/App.tsx`, `App.css` -- the filter controls in the Results panel.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/views.py`, `urls.py` -- the parameters, the parser and the video list.
- [x] `src/api/core/tests.py` -- API and parser tests.
- [x] `src/ui/src/apiClient.ts`, `resultsFilters.ts` + tests -- client and helpers.
- [x] `src/ui/src/App.tsx`, `App.css` -- the controls.

**Acceptance Criteria:**
- Given the date-range test, when the filter is applied to the wrong date field, then the test fails.
- Given the foreign-video test, when the video check is skipped, then another project's counts leak and the test fails.
- Given the running app, when a researcher picks one video and a date range, then the card's counts and its filter description change, and Clear restores the US-027 numbers.

## Implementation Notes

- `runs` narrows too when any filter is set: it counts this project's runs that linked a matching video, so the Combined row reads all zeros. Unfiltered it stays `project.collection_runs.count()`, which still counts runs that linked no video, as in US-027.
- An empty parameter value (`?date_from=`) counts as absent rather than invalid. Dates must match `[0-9]{4}-[0-9]{2}-[0-9]{2}` before `date.fromisoformat`, which alone also accepts `20260301` and `2026-W10-1`. `date_from` after `date_to` is reported on `date_to`.
- Date bounds are explicit UTC datetimes (`time.min` / `time.max`), not `__date`, so they do not depend on `TIME_ZONE`. The `video` 404 check runs before the date bounds, so a linked video outside the range gives zeros, not 404.
- `ProjectVideoListView` returns `.values()` rows from a plain `APIView`, unpaginated, ordered by title then id.
- UI: the summary effect depends on the applied filters and a `resultsReloads` counter; run start and Refresh bump the counter instead of calling `loadResultsSummary` directly, so a reload never fetches with filters captured before an `await`. Changing project (select or create) clears the form and applied filters. The card describes the filters the server echoed, not the form. The date inputs cross-limit each other with `min`/`max`.

- Orchestrator check: backend 314 OK on PostgreSQL, migrations clean; UI 81 pass, build and lint clean. UI baseline `8a6492eae632641db48c4dce04a0ae060839e52b`; thesis baseline `7f92c99545ecc0a0b23ec1fa94d4e9c7e411a21e`.

- Review patches (pass 1) applied: Apply passes a fresh copy, so it always refetches; videos labelled with title plus publish date (`videoLabel`). Backend 314 OK on PostgreSQL; UI 82 pass, build and lint clean.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 1, false 0, maybe-false 0, defer 0; rejected 1.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Apply cannot retry after a failed request: the same object reaches `setAppliedResultsFilters`, React skips the update | medium | patch | Confirmed (`Object.is` bail-out; the effect depends on `appliedResultsFilters`). Apply a fresh copy. |
| Same-title videos are indistinguishable in the selector and the card's description | low | patch | Confirmed; `youtube_published_at` is already returned. Label with title plus publish date through a pure, tested helper. |
| Acceptance criterion 3 (manual browser check) has no evidence | — | reject | A manual check for the human; not a code defect. Listed as pending. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all pass.

**Manual checks:**
- On a project with collected data, pick one video and then a date range; the counts change and describe the filter; Clear restores them.
