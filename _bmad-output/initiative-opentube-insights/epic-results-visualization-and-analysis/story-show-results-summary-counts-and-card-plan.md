---
title: 'Show results summary counts and card'
type: 'feature'
ticket: '1'
created: '2026-10-07'
status: 'done'
baseline_revision: 'dc472ff5156c35a1b361992c6371e35bd0f0b401'
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

**Problem:** A researcher cannot see how much has been collected without opening each run or the admin (US-027).

**Approach:**
- **API:** one read-only summary endpoint computes counts with database aggregates and the collection date range of the stored data.
- **UI:** a new "Results" panel shows them as a summary card.

## Boundaries & Constraints

**Always:**
- **Counts:** database aggregates (`Count(..., distinct=True)`, `Min`, `Max`), never Python loops over rows. Each count is scoped through the effective owner, and another owner's data is never counted.
- **Videos and channels:** a video counts when it is linked to a run in scope (`CollectionRunVideo`), and a channel counts when it belongs to such a video.
- **Collection date:** the earliest and latest `discovered_at` of this project's run-video links, shown as "Data collected between <date> and <date>". It shows "No data collected yet" when there are none.
- **Rules:** the endpoint is GET only (405 otherwise). The UI fetch follows the AGENTS.md late-response rule (an `AbortController` in a ref, an identity check, and the project id). No `any`. JSDoc on new exports.
- Validated on Compose PostgreSQL.

**Decisions** (approved by the human on 2026-10-07):
- **Scope:** the active project only, at `GET /api/projects/<project_id>/results/summary/`, through `get_project()`. The card shows the project's name and status in place of a projects count.
- **Counts shown:** runs, videos, channels, top-level comments, replies and statistics snapshots, with the data's collection date range. Processed counts (cleaning, sentiment) are added by the stories that create them (US-024, US-025); there is no placeholder now.
- **Response shape:** `{project: {id, name, status}, runs, videos, channels, comments, replies, statistics_snapshots, first_collected_at, last_collected_at}`. The two dates are the min and max `discovered_at` of **this project's** `CollectionRunVideo` links (when this project's runs found the videos), or null. Amended by the human on 2026-10-07: video `last_fetched_at` is shared across owners and overwritten on every re-fetch.

**Never:**
- No charts (US-028).
- No filters (US-029, US-030).
- No sentiment, cleaning or processing counts (they are added by US-024 and US-025).
- No caching or materialized counts.
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Counts | active project with 2 runs, 3 distinct videos (one in both runs), 2 channels, 4 top-level comments + 2 replies, 4 statistics snapshots (one per video per run) | runs 2, videos 3, channels 2, comments 4, replies 2, statistics_snapshots 4, and the dates as min/max `discovered_at` of this project's run-video links | No error expected |
| Project scope | a second project of the same owner with its own run and videos | not counted in the first project's summary | No error expected |
| Empty | no runs | all counts 0; dates null; UI "No data collected yet" | No error expected |
| Isolation | another owner's project with data | not counted | No error expected |
| Foreign project | summary requested for another owner's project | no data | 404 |
| Write | POST | nothing changes | 405 |
| UI | the active project changes while a summary request is in flight | the stale response is dropped | abort + identity check |

</frozen-after-approval>

## Code Map

- `src/api/core/views.py` -- a new `ResultsSummaryView(ProjectOwnerMixin, APIView)` with `get` only. Reuse `get_owner()` / `get_project()` for scoping. Use plain `QuerySet` aggregates: `YouTubeVideo.objects.filter(run_links__collection_run__project=...)`, `YouTubeChannel.objects.filter(videos__in=...)` and `YouTubeComment.objects.filter(run_links...)`. Check the real `related_name`s in `models.py`.
- `src/api/core/urls.py` -- `projects/<uuid:project_id>/results/summary/`, named `project-results-summary`.
- `src/api/core/tests.py` -- `ResultsSummaryApiTests`, copying the `CollectionRunReadApiTests` setup style.
- `src/ui/src/apiClient.ts` -- a `ResultsSummary` type with an `isResultsSummary` guard and a `getResultsSummary(...)` fetcher, following `listCollectionRuns`. Add `tests/resultsSummaryApi.test.ts`.
- `src/ui/src/App.tsx` -- a fourth `<section className="panel" aria-labelledby="results-heading">` with a `<dl>` card. Load it in a `useEffect` on the active project, guarded like the runs list, and refresh it when the runs panel's Refresh is clicked.
- `src/ui/src/App.css` -- card styling only.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/views.py`, `urls.py` -- the summary endpoint.
- [x] `src/api/core/tests.py` -- one test per API matrix row.
- [x] `src/ui/src/apiClient.ts` + test -- the type, guard and fetcher.
- [x] `src/ui/src/App.tsx`, `App.css` -- the Results panel.

**Acceptance Criteria:**
- Given the counts test, when the video count drops `distinct=True`, then the test fails, because the video in both runs would count twice.
- Given the isolation test, when the owner filter is removed, then the test fails.

## Implementation Notes

- Comments, replies and statistics snapshots are scoped through this project's runs (`CollectionRunComment`, `VideoStatisticsSnapshot.collection_run`), not through the in-scope videos: videos are shared across projects and owners, so scoping by video would count another owner's comments and snapshots on a shared video. The isolation test seeds exactly that case.
- A run-less statistics snapshot is not attributable to any project and is not counted.
- The date range is the min/max `discovered_at` of this project's `CollectionRunVideo` links (amended Decision). The isolation test has the foreign owner link the shared video later and re-fetch it, and the dates do not move.
- A successful run start reloads the summary, so the Runs count is not stale.
- Mutation checks run on PostgreSQL, each failing the suite: video `distinct` dropped, channel `distinct` dropped, comments scoped by video, snapshots scoped by video, scope widened to the owner instead of the project, and the owner filter removed from `get_project()`.
- The UI shows "Loading results" whenever no summary is held for the active project; a Refresh keeps the current card until the new one lands. Unlike `loadRuns`, no loading state is set inside the effect.
- Frozen 'Counts' row amended by the human (2026-10-07): 5 snapshots was impossible under the one-per-video-per-run rule; now 4. Orchestrator check: backend 226 OK on PostgreSQL, migrations clean; UI 64 pass, build and lint clean. UI baseline `1d3b9639a79846d2fad0962f0e1a90cfab895751`; thesis baseline `d6ecb8e4c7a7508da095f69e60060f8cfac43b75`.

- Review patches (pass 1) applied: project-scoped date range from run-video links; foreign-project 404 in the isolation test; channel and reply in the same-owner project test; summary reload after a run starts. Backend 226 OK on PostgreSQL; UI 64 pass, build and lint clean.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 5, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Date range uses global video `last_fetched_at`: another owner's re-fetch moves it, and "first" is not the first collection | medium | intent_gap → patch | Confirmed: `last_fetched_at` is one shared column overwritten on every fetch. Root cause was the frozen Decision; the human chose min/max `discovered_at` of this project's run-video links and the frozen block was amended. Patched in place, not by full revert: the change is local to two aggregates and one test. |
| The AC's isolation test does not fail when the owner filter is removed | low | patch | Confirmed: the owner filter lives only in `get_project()` and the test requests the owner's own project. Add a request for the foreign owner's project (404) to the isolation test. |
| The project-scope test cannot catch channel or reply scoping regressions | low | patch | Confirmed: the other project's video has no channel and no reply. Seed both and assert `channels` and `replies`. |
| The card's Runs count lags after "Start run" | low | patch | Confirmed: `handleStartRun` prepends the run but does not reload the summary. Reload it on success. |
| The UI stale-response row has no automated test | low | reject | No React render harness (deferred since US-007); the guard mirrors the reviewed `loadRuns` pattern; same accepted gap as US-014. |
| A Refresh-started summary request is not aborted on unmount | low | reject | `App` never unmounts and the identity check still guards state; same finding rejected in US-014. |

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all pass.

**Manual checks:**
- After a collection with comments, the Results card's counts match `/admin/` (videos, channels, comments split by level) and the date range matches the videos' fetch times.
