# 32 - Filter results by date and video

Story: US-029, Filter results by date and video.

Status note: this document describes the US-029 implementation **after** the code review of 2026-10-08 and the fixes that followed it.

## What this story added

The **Results** panel (page 25) gains filters for its summary card:

- **Published from / to:** two date inputs. They keep videos whose YouTube publish date falls in that range.
- **Video:** a dropdown of the project's videos, each shown as `Title (YYYY-MM-DD)`.
- **Apply** and **Clear** buttons.

With filters applied, every count on the card (runs, videos, channels, comments, replies, statistics snapshots) covers only the matching videos, and the card says so, for example `Showing video "Debate (2026-03-10)" published from 2026-03-01 to 2026-03-31 (UTC)`.

Behind it:

- the summary endpoint takes three optional parameters, `date_from`, `date_to` and `video`;
- a new endpoint, `GET /api/projects/<project_id>/results/videos/`, lists the project's videos for the dropdown.

## Why this matters

A dataset is rarely read all at once. A researcher asks "what did videos from March collect?" or "how many comments did this one video get?". The filters answer that in the app, without exporting the data. The sentiment chart (US-028) and the sentiment filter (US-030) will reuse the same parameters.

## Key concept: which date

The range filters on the video's **YouTube publish date** (`youtube_published_at`), because "videos published between …" is the usual research slice, and it matches the saved query's own date window (`publishedAfter` / `publishedBefore`).

The rules are exact:

- both days are **included**, counted as whole days in **UTC**. A video published at `2026-03-31T23:59:59Z` is inside `date_to=2026-03-31`;
- a video with **no** publish date is left out whenever a date is set, because nobody can say it is in the range;
- the card's "Data collected between X and Y" line keeps its meaning from page 25 (when this project's runs found the videos), now computed over the filtered videos.

## Key concept: the same honest counting

Filtering reuses everything US-027 got right:

- only **this project's** runs count. Videos are shared across projects and owners (page 25);
- each video counts **once**, even if several runs found it;
- comments, replies and snapshots are counted through this project's runs, never through the shared video rows.

The **Runs** count narrows too: it counts only the runs that found a matching video. Without filters, every number is exactly what page 25 describes.

## Key concept: bad input is refused, not guessed

`parse_results_filters` reads the parameters before anything is counted. It is a pure function, tested on its own.

| input | answer |
| :-- | :-- |
| `date_from=2026-13-01`, or `20260301` | `400`, "Enter a valid date in YYYY-MM-DD format." on that field |
| `date_from` later than `date_to` | `400`, on `date_to` |
| `video=abc` | `400`, on `video` |
| a valid video ID from **another** project | `404`, so nothing about that project leaks |
| `date_from=` (empty) | treated as not set |

Python's `date.fromisoformat` alone would accept `20260301`, so the parser checks the exact `YYYY-MM-DD` shape first.

## Key concept: small UI details that matter

- **Native controls.** `<input type="date">` and `<select>` are built into the browser, so no date-picker library is needed. The two dates limit each other (`min` / `max`), so you cannot pick an inverted range.

- **Same-title videos.** Channels often re-upload clips under the same title, so the dropdown and the card show the publish date next to the title. The review caught this.

- **Apply always refetches.** If a request failed, pressing Apply again retries it. A review fix: before, the second press changed nothing React could notice, so nothing was sent.

- **The description comes from the server's answer.** The card describes the filters the server echoed back in `filters`, not what the form currently shows, so the text never contradicts the numbers.

- **Switching project resets the filters.** Late responses are dropped (the AGENTS.md rule).

## File-by-file explanation

### `src/api/core/views.py` and `src/api/core/urls.py`

- `parse_results_filters(query)`: the pure parser.
- `ResultsSummaryView`: applies the filters through one subquery of matching videos and echoes `filters`.
- `ProjectVideoListView`: the dropdown's list, as `{id, title, youtube_published_at}`, ordered by title, with no YouTube IDs. It is routed as `project-results-videos`.

### `src/api/core/tests.py`

- `ResultsSummaryApiTests` gained a test for each case:
  - no filters, a date range and the day bounds
  - no publish date
  - one video, and filters combined
  - bad input and a foreign video
  - the video list
- `ParseResultsFiltersTests` covers the parser alone.

### `src/ui/src/resultsFilters.ts` and `src/ui/tests/resultsFilters.test.ts`

Pure helpers: `resultsFilterQuery` builds the query string, `describeResultsFilters` writes the card's sentence, and `videoLabel` gives `Title (YYYY-MM-DD)`. They are tested, including three same-title videos getting three different labels.

### `src/ui/src/apiClient.ts` and `src/ui/tests/resultsSummaryApi.test.ts`

`getResultsSummary(projectId, filters, signal)`, the `ProjectVideo` type with its guard, and `listProjectVideos`.

### `src/ui/src/App.tsx` and `src/ui/src/App.css`

The filter controls in the Results panel. Refresh and **Start run** now reload the card through a small reload counter, so a reload always uses the filters applied at that moment.

## How the pieces connect

```text
Results panel
   [Published from] [to] [Video ▾] [Apply] [Clear]
        '-- applied filters (fresh copy on every Apply)
               '-- GET /api/projects/P/results/summary/?date_from=…&date_to=…&video=…
                      parse_results_filters -> 400 per field | 404 foreign video
                      matching videos = P's run links ∩ publish date ∩ video
                      counts narrowed through P's runs, distinct
               <- counts + filters echoed -> card + "Showing …" line
   GET /api/projects/P/results/videos/ -> dropdown "Title (YYYY-MM-DD)"
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

Passing looks like `OK` (314 tests), `pass 82`, a finished build and no lint output. The curl commands are in [commands.md](commands.md).

## How to test manually

1. `cd src && ./run-local.sh`, open `http://localhost:5173/`, and pick a project with collected data.

2. In the Results panel, pick one video and press **Apply**. The card's counts drop to that video, and the line says which video.

3. Set a date range that excludes that video and press **Apply**. Every count becomes 0.

4. Press **Clear**. The counts are back to page 25's numbers.

## Common errors

- **"Enter a valid date in YYYY-MM-DD format."** The date was typed in another format. The date inputs normally prevent this; it can happen through curl.

- **All counts are 0.** The filters match no video. For example, the range excludes the selected video, or the videos have no publish date while a date is set.

- **`404` for a video.** That video is not linked to this project, for example after switching project with an old link.

## Known gaps

- The video list is not paginated. That is fine at the current per-run caps.

- The filters cover the Results card only. The run detail (Discovery, Sentiment, Requests) is already per-run and is not filtered.
