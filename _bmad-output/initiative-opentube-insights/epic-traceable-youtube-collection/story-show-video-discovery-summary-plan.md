---
title: 'Show video discovery summary'
type: 'feature'
ticket: '7'
created: '2026-10-07'
status: 'built'
baseline_revision: '9339c1dfc480994d0d695e9caf36ecb0ad4d3124'
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

**Problem:** A researcher cannot see what a run's discovery produced: how many videos it found, how many search results it skipped, or which videos they were. The skipped count is not even recorded (US-016; US-015 deferred the counter to this story).

**Approach:**
- **Counter:** add a stored `total_videos_skipped` counter that the collector fills.
- **API:** expose it, plus `data_purged_at`, on runs, and add the run's discovered videos to the run detail.
- **UI:** the Collection runs panel's run detail gets a summary (discovered, skipped, collected, purge date) and a basic list of discovered video IDs above the request-log table.

## Boundaries & Constraints

**Always:**
- **The counter:**
  - `total_videos_skipped` is a `PositiveIntegerField(default=0)` on `CollectionRun`. It counts the search results that did not produce a new link for the run: a `videoId` already linked in this run (a duplicate), or an item with no string `videoId` (a channel or playlist result).
  - It is written once, in `_discover_videos`'s existing `finally`, beside `total_videos_discovered`, so it stays right when a page fails.
  - Results never processed because the cap was reached are not counted.
- **Run fields:** both run serializers expose `total_videos_skipped` and `data_purged_at`.
- **Discovered videos:** the run detail adds `discovered_videos`, a list of `{youtube_video_id, title, page_number, discovered_at}` in `discovered_at` order, from the run's `CollectionRunVideo` links.
- **After a purge:** the summary counts come from the run row, never from counting links. Once US-040 purges, the links are gone (`CASCADE`) but the counts and `data_purged_at` remain. The UI then shows "Data purged on <date>" in place of the list.
- **Schema doc:** add a `total_videos_skipped` row to `collection_runs` in `docs/database_schema.md` (thesis repo, separate docs commit).
- **UI rules:** fetch guards as in US-014 (no new fetch: the summary rides on the existing run detail). No `any`. JSDoc on new exports.
- Validated on Compose PostgreSQL.

**Never:**
- No purge implementation (US-040). `data_purged_at` stays null until then and is only displayed.
- No pagination of the video list.
- No video detail page, thumbnails or embeds. Each ID may link to `https://www.youtube.com/watch?v=<id>`, nothing more.
- No change to how videos are discovered, stored or deduplicated.
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Skipped counted | page 1 has `a`, `b` and a channel item; page 2 has `b`, `c` | discovered 3; skipped 2 (the channel item and the repeated `b`) | No error expected |
| Failure mid-run | page 1 has a duplicate; page 2 fails | `total_videos_skipped` 1 still written; run `failed` | existing handlers |
| Run fields | GET list or detail | both include `total_videos_skipped` and `data_purged_at` (null) | No error expected |
| Discovered list | GET detail of a run with 3 links | `discovered_videos` has 3 entries, in `discovered_at` order, each with ID, title, page and time | No error expected |
| Purged run | run with `data_purged_at` set and no links | `discovered_videos` `[]`; counts unchanged; `data_purged_at` returned | No error expected |
| UI summary | user opens a completed run | the summary shows discovered, skipped and collected counts above a list of video IDs, each linking to YouTube; then the request logs | No error expected |
| UI purged | user opens a purged run | the counts plus "Data purged on <date>" in place of the list | No error expected |
| UI empty | a `pending` run | the counts at 0, no list, "No requests yet" as today | No error expected |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py` `CollectionRun` -- add `total_videos_skipped` beside the other totals. Generate `0011`.
- `src/api/core/collection.py` `_discover_videos` -- count `skipped` where today's loop does `continue` (`video is None` or already in `seen`), and write it in the `finally` together with `total_videos_discovered` (one `update`).
- `src/api/core/serializers.py`:
  - Add `total_videos_skipped` and `data_purged_at` to `CollectionRunSerializer.Meta.fields`.
  - Add a new `DiscoveredVideoSerializer` on `CollectionRunVideo`, with `youtube_video_id` and `title` taken from `video`.
  - `CollectionRunDetailSerializer` gains `discovered_videos = DiscoveredVideoSerializer(source="run_videos", many=True, read_only=True)`. Ordering comes from `CollectionRunVideo.Meta.ordering` (`collection_run`, `discovered_at`).
- `src/api/core/views.py` `CollectionRunDetailView.get_queryset` -- add `Prefetch("run_videos", queryset=CollectionRunVideo.objects.select_related("video"))`.
- `src/api/core/admin.py` `CollectionRunAdmin.readonly_fields` -- add the new counter.
- `src/api/core/tests.py` -- extend `CollectRunTests` (skipped), `CollectionRunReadApiTests` (fields, list, purged), and the end-to-end dedupe test (the fixture already has one channel item and one repeat, so it expects skipped 2).
- `src/ui/src/apiClient.ts` -- `CollectionRun` gains `total_videos_skipped` and `data_purged_at`, plus `total_videos_collected` if not typed yet. Add a `DiscoveredVideo` type and guard, and `CollectionRunDetail.discovered_videos`. Update the guards and `tests/collectionRunApi.test.ts`.
- `src/ui/src/App.tsx` -- in the run detail block (the `activeRunDetail` ready branch), render a `<dl>` summary and an `<ol>` of IDs before the logs table.
- `src/ui/src/App.css` -- minimal styling for the summary and the list.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/models.py` + migration `0011`, `collection.py` -- the counter.
- [x] `src/api/core/serializers.py`, `views.py`, `admin.py` -- the fields and `discovered_videos`.
- [x] `src/api/core/tests.py` -- one test per API and collector matrix row.
- [x] `src/ui/src/apiClient.ts`, `tests/collectionRunApi.test.ts` -- types, guards and tests.
- [x] `src/ui/src/App.tsx`, `App.css` -- summary and list.
- [x] `docs/database_schema.md` -- the `total_videos_skipped` row.

**Acceptance Criteria:**
- Given the skipped test, when the channel-item branch or the duplicate branch stops counting, then the test fails.
- Given the purged-run test, when the summary counts are computed from links instead of read from the run row, then the test fails.
- Given the running app after a real collection, when the user opens the run, then the discovered count equals the number of listed IDs, and each ID opens the YouTube video.

## Implementation Notes

- Added a cap test (cap 2, page of 3) so results never processed past the cap stay uncounted.
- Mutation-checked: counting only duplicates, or only items without a `videoId`, fails the collector and end-to-end skipped tests.
- Manual check with a live key (cap 5, click an ID) not run by the implementer.
- Orchestrator check: backend 176 OK on PostgreSQL, migrations clean; UI 60 pass, build and lint clean. UI baseline `5ca8f3c62a31935447696a63a7b54ccd6e565b83`; thesis baseline `3a54101ca7050776aa673b27c831b43e67f5ca29`. UI summary, purged and empty rows have no render harness and rest on the manual check.
- Review patches (pass 1) applied: `total_videos_skipped` added to `TOTAL_FIELDS`; run-detail heading names the run with `<h4>` Discovery / Requests. Backend 176 OK on PostgreSQL; UI 60 pass, build and lint clean.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 0, low 2, false 1, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `TOTAL_FIELDS` lacks `total_videos_skipped`, so its default and its presence in the start response are untested | low | patch | Confirmed; the UI guard now requires the field on the start response. Add it to the tuple. |
| Run-detail `<h3>` "Requests for …" now heads the discovery summary and list | low | patch | Confirmed in the ready branch; accessibility basics. Rename the `<h3>` and add `<h4>` "Discovery" / "Requests". |
| Third acceptance criterion (live collection, counts match list, IDs open) not verified | false | reject | Not a code defect: it is the plan's manual check and needs the human's API key; recorded as pending in the summary. |

## Design Notes

Counts live on the run row because links are YouTube data, which the purge deletes after 30 days, while run rows are kept as methodological records. The UI never derives a count from the list, so a purged run still reads correctly.

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: all pass.

**Manual checks:**
- Collect a run with a cap of 5, open it in the panel, and check that the counts match the list. Click an ID and it opens the video.
