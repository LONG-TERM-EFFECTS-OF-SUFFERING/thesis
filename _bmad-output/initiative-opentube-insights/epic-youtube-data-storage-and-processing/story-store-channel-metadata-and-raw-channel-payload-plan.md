---
title: 'Store channel metadata and raw channel payload'
type: 'feature'
ticket: '2'
created: '2026-10-07'
status: 'done'
baseline_revision: 'a82a51cdac883d490ea6c765568924ac4cb29d43'
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

**Problem:** A collected video does not record which channel published it, and nothing about channels is stored, so the source context of a dataset is missing (US-018).

**Approach:** After the video details step, `collect_run` fetches the distinct channels of the run's collected videos with `channels.list` (`part=snippet,statistics`). Requests go through `call_youtube`, up to 50 IDs each. The results are stored as `YouTubeChannel` rows with their metadata, the whole item as `raw_payload` and `last_fetched_at`. Each collected video is linked to its channel.

## Boundaries & Constraints

**Always:**
- **Columns:** `YouTubeChannel` (`youtube_channels`) matches `docs/database_schema.md`. `youtube_channel_id` is unique, and the three counts are `PositiveBigIntegerField(null=True, blank=True)`.
- **Video link:** `YouTubeVideo.channel` is a `ForeignKey(YouTubeChannel, SET_NULL, null=True, blank=True)`. The schema doc's `null: NO` on that row contradicts its own Django column; follow the Django column, as US-010 did.
- **Which channel:** a video's channel ID comes from its `videos.list` item, `snippet.channelId`. Only videos collected in this run's details step are linked. Videos missing from `videos.list` keep `channel` null.
- **Field mapping:**
  - From `snippet`: `title`, `description`, `country_code` (`country`) and `youtube_published_at` (`publishedAt`).
  - From `statistics`: `subscriber_count`, `video_count` and `view_count`. YouTube sends these as decimal **strings**; they are parsed to `int`.
  - A missing, non-digit, negative or `bool` value becomes null. `hiddenSubscriberCount` means `subscriberCount` is absent, so it is null.
  - `raw_payload` is the whole item. `last_fetched_at` is now.
- **Requests and reuse:**
  - A channel already stored is updated in place, not duplicated.
  - Each distinct channel is requested once per run, in batches of 50 `id`s (logged as `{"redacted_count": n}`, cost 1 each).
  - No request is sent when no video was collected.
- **Missing channels:** a channel absent from the response (terminated) is not stored, and its videos keep `channel` null.
- **Failure:** a failing `channels.list` call fails the run through the existing handlers. Videos, details and channels stored earlier stay.
- **Tests:** no test reaches `googleapis.com`. Validated on Compose PostgreSQL.

**Never:**
- No channel statistics snapshots: the counts on the row are overwritten by design, and snapshots are US-019, for videos.
- No channel discovery outside a run's videos.
- No UI change.
- No new run counter column.
- No cleaning (US-024).
- No purge (US-040).
- No new dependencies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Channels stored | 3 collected videos from 2 channels | one `channels.list` request after `videos.list`, `id` holding the 2 channel IDs, `part=snippet,statistics`; 2 channel rows with every column filled and `raw_payload` equal to the item; each video linked to its channel; run `completed` | No error expected |
| Batching | 60 collected videos from 60 channels | two `channels.list` requests (50 + 10) | No error expected |
| Counts | `subscriberCount` `"1200"`, `viewCount` `"0"`, `videoCount` missing | 1200, 0, null | No error expected |
| Bad counts | `hiddenSubscriberCount: true` with no `subscriberCount`; `viewCount` `"-5"`, `"abc"` or `true` | null for each | No error expected |
| Known channel | channel row already stored by an earlier run | same row updated (title, counts, `raw_payload`, `last_fetched_at`); no second row | No error expected |
| Missing channel | a video's `channelId` absent from the response | no channel row for it; that video's `channel` null; others linked | No error expected |
| No videos collected | discovery found 0, or `videos.list` returned nothing | no `channels.list` request | No error expected |
| Channel failure | `channels.list` returns HTTP 403 | run `failed`; videos, details and earlier channel batches kept | existing handlers |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py` -- add `YouTubeChannel` above `YouTubeVideo`, in the house idioms (UUID pk, `db_table`, docstring `__str__`). Add `YouTubeVideo.channel` (`related_name="videos"`). Generate `0010`.
- `src/api/core/collection.py`:
  - `_store_details` also returns the item's `snippet.channelId` (a `str` or `None`). `_collect_details` collects a `{video_pk: channel_id}` map and passes it on.
  - Add `_collect_channels(run, video_channels, *, api_key, transport)` and `_store_channel(item)`. Batch with `DETAILS_BATCH_SIZE`.
  - Link with one `YouTubeVideo.objects.filter(pk__in=...).update(channel=...)` per channel.
  - Add a `_count(value)` helper: return `int(value)` only for a `str` of ASCII digits, else `None`. Reject `bool` explicitly.
  - Call `_collect_channels` from `collect_run` after `_collect_details`, inside the same `try`.
- `src/api/core/youtube_client.py` -- no change. `channels.list` (cost 1) is in `QUOTA_COSTS`, and `id` is redacted.
- `src/api/core/admin.py` -- register `YouTubeChannel` with `ReadOnlyAdmin` (title, ID, country, counts, `last_fetched_at`). Add `channel` to `YouTubeVideoAdmin.list_display`.
- `src/api/core/tests.py` -- the `CollectRunTests` fake already routes by path; add a `/channels` route and a documented-shape `_channel_item` helper. `_video_item` items need a `snippet.channelId`.
  - Update the existing collector and end-to-end tests that assert request counts, quota or logs for the extra call.
  - Extend the end-to-end fixture with a `YOUTUBE_CHANNELS_RESPONSE`.
- `docs/database_schema.md` (thesis repo, separate docs commit) -- correct the `youtube_videos.channel_id` null column to `YES`, to match its Django field.

## Tasks & Acceptance

**Execution:**
- [x] `src/api/core/models.py` + migration `0010` -- `YouTubeChannel` and `YouTubeVideo.channel`.
- [x] `src/api/core/collection.py` -- the channel step, the count parsing and the linking.
- [x] `src/api/core/admin.py` -- read-only channel admin and video channel column.
- [x] `src/api/core/tests.py` -- one test per matrix row, plus updates for the extra request.
- [x] `docs/database_schema.md` -- the null fix.

**Acceptance Criteria:**
- Given the bad-counts test, when `_count` accepts `bool` or negative strings, then the test fails.
- Given the known-channel test, when channels are created instead of updated, then the test fails on the unique constraint or the row count.
- Given the end-to-end test (`urlopen` stubbed), when the run collects, then a GET to `https://www.googleapis.com/youtube/v3/channels` with `part=snippet,statistics` follows the `videos.list` request.

## Implementation Notes

- `_store_channel(channel_id, item)` takes the already-validated ID beside the item, so the ID check (a requested `str`, seen once) lives in `_collect_channels`.
- `_count` also rejects a plain `int` and non-ASCII digit strings (`"١٢"`), since it accepts only an ASCII-digit `str`.
- Channel IDs are sent sorted within each batch, for a deterministic request.
- `YouTubeVideoAdmin` gets `list_select_related = ("channel",)` so the new column is not one query per row.
- Migration: `0010_youtubechannel_youtubevideo_channel.py`.
- Orchestrator check: full suite 168 OK on PostgreSQL, `makemigrations --check` clean. Thesis baseline `87e26e61a98a1d327e18adc1d49167f0ee23d4e5`.
- Review patch (pass 1) applied: stale channel links are cleared for unreturned channel IDs per batch and when an item lacks `channelId`; two pre-linked tests added. Full suite 170 OK on PostgreSQL.

## Plan Change Log

## Review Triage Log

Pass 1 (quick lens): high 0, medium 1, low 1, false 0, maybe-false 0, defer 0.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| A previously linked video keeps its old `channel` when this run's channels.list omits it, or its item has no `channelId` | medium | patch | Confirmed: links are only ever set, never cleared; the frozen "Missing channel" row requires null. Fix: clear links for unreturned IDs per batch, and in `_store_details` when `channelId` is missing; tests with a pre-linked video. |
| Overflowing count, over-long `country` or channel ID raises `DataError` and fails the run | low | reject | Real YouTube values are far below the limits; same trade-off accepted in US-015 and US-017; the fix adds per-field guards. |

## Design Notes

Channel IDs come from `videos.list`, not from search. The details response is authoritative, and only videos that still exist get a channel. Counts are overwritten on the channel row because the schema stores the latest value. Dated history is US-019's snapshot pattern, for videos.

## Verification

**Commands:**
- `cd src && docker compose up -d db`, then `cd src/api && DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput` -- expected: OK.
- `cd src/api && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: `No changes detected`.

**Manual checks:**
- With a real key: start a run with cap 5, run `collect_runs`, open `/admin/` → Youtube channels. The channels are filled with counts and `raw_payload`, the videos show their channel, and the run's logs end with one `channels.list` row.
