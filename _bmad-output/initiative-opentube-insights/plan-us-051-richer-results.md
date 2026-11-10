---
title: 'US-051 Richer results'
type: 'feature'
ticket: ''
created: '2026-11-09'
status: 'ready-for-dev'
baseline_revision: ''
route: 'full'
route_source: 'auto'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The advisor found the Results section very basic. It shows six counts, one sentiment chart per model, and filters by date and video. He asked for more statistics (users analyzed, channels, sentiment per channel), interactive filters by channel and date, and word or tag clouds.

**Approach:** Extend the existing results summary rather than adding a new page. Add four things, each computed on request through the project's own runs, as every figure is today, so the purge needs no new rule:
1. **Distinct comment authors**, as a count.
2. **Sentiment by channel**: the top 15 channels by comment count, each with its label distribution, per model.
3. A **channel filter**, applied to every count next to the date and video filters.
4. Two **word clouds**: the top 30 video tags and the top 30 comment terms.

Everything is drawn with native HTML and CSS, as today.

## Boundaries & Constraints

**Always:**
- **Scoping:** every figure goes through the project's run links and respects all three filters, as `results_summary` does now. Another researcher's comments on a shared video never count.
- **Privacy:** authors appear only as a count. No author name, identifier or individual comment appears in any new figure.
- **Sentiment rule:** sentiment by channel uses the same rule as the existing chart: the latest pass per run, each comment once, one table per model.
- **Comment terms:** they come from `text_normalized`, lowercased, keeping words of 3 or more letters. They exclude the `<URL>` placeholder and a short fixed stopword list for Spanish and English, kept in code. They are computed over at most the 5,000 most recently collected comments, marked with a `ponytail:` comment. The response says when the cap applied.
- **Channel filter:** an unknown or foreign channel returns 404, like the video filter. Invalid input returns 400 with a message.
- **UI:** new text is translated (es/en), and every new figure carries its number as text, not only bar length or font size, as the sentiment chart does.

**Never:**
- No chart or word-cloud library, no new dependency, no migration and no stored aggregates.
- No per-author figures, such as top commenters.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Authors | 3 comments by 2 authors in the project; 1 more by a third author on the same video in another project | `comment_authors: 2` | — |
| By channel | 2 channels with labeled comments | one row per channel with its count per label, ordered by comment count, top 15 | — |
| Channel filter | `channel=<id>` of one of the project's channels | every count, distribution and cloud is limited to that channel's videos | — |
| Bad channel | a foreign or unknown channel id; `channel=abc` | 404; 400 with "Enter a valid channel id." | — |
| Clouds | videos with tags; comments with words | top 30 tags and top 30 terms with counts; stopwords and `<URL>` absent | — |
| Cap | more than 5,000 comments | terms computed over the 5,000 most recent; `terms_sampled: true` | — |
| No sentiment | `SENTIMENT_MODEL` empty | the by-channel section is empty and says why; the clouds and counts still show | — |

</frozen-after-approval>

## Code Map

- `src/api/core/results.py`:
  - `ResultsFilters` and `parse_results_filters`: add a `channel` UUID, mirroring `video`.
  - `results_summary`: its `videos` queryset is scoped through `run_links__collection_run__project`. Add a channel restriction there, so every count follows it, and add `comment_authors`, a distinct count of `author_channel_id` over the project-scoped comments.
  - `latest_sentiment_passes` and `sentiment_distributions`: reuse them for `sentiment_by_channel`, grouping by `comment__video__channel`.
  - Add `top_terms(...)` and `top_tags(...)` here as pure functions, plus the stopword `frozenset`, so they are unit-testable without the database.
- `src/api/core/views.py` `ResultsSummaryView` (~412): passes the filters through. The channel 404 is raised in `results_summary`, as the video one is.
- Add `ProjectChannelListView` beside `ProjectVideoListView` (~441), mirroring it: channels linked by the project's runs, with id and title, for the UI select. Add its route in `core/urls.py`.
- Tests in `core/tests/test_results.py`: one per matrix row, plus scoping across projects.
- `src/ui/src/apiClient.ts`:
  - Extend `ResultsSummary` and `isResultsSummary` with `comment_authors`, `sentiment_by_channel`, `top_tags`, `top_terms` and `terms_sampled`.
  - Add `listProjectChannels`.
  - Test with a stubbed `fetch`.
- `src/ui/src/resultsFilters.ts`: add `channel` to the filter parsing and query building, with tests.
- `src/ui/src/ResultsSection.tsx`:
  - The authors count goes in the summary card.
  - A channel select goes next to the video select, through `latestRequest`.
  - Sentiment by channel is a table with stacked CSS bars per row; reuse the colors and the count-and-percent text pattern of the current chart in `sentimentFormat.ts`.
  - The two clouds are lists of words whose font size scales with the count, each word showing its count on hover and to screen readers.
- `src/ui/src/i18n.ts`: Spanish entries for the new text.

## Tasks & Acceptance

**Execution:**
- [ ] `results.py` and the tests: the filter, authors, by-channel, `top_terms` and `top_tags`.
- [ ] `views.py` and `urls.py`: the channel list endpoint, with a test.
- [ ] `apiClient.ts` and `resultsFilters.ts`: types, guards and filter, with tests.
- [ ] `ResultsSection.tsx` and `i18n.ts`: the new card value, the select, the table and the clouds.

**Acceptance Criteria:**
- Given a project with two channels, when the researcher picks one channel, then every number on the Results page changes to that channel only, and the sentence describing the filters names it.
- Given any new figure, when it is read without color or size, then its numbers are still available as text.

## Design Notes

- **Policy:** the YouTube developer policies (III.E.4.h) restrict derived metrics. These figures are aggregates computed on request and never stored, like the existing counts and the sentiment chart. 6.3.2 of the thesis should name the clouds and the by-channel table next to sentiment.
- **Order if time runs short:** the filter and authors first, then by-channel, then the clouds. Each part is useful on its own.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test` -- expected: all pass.
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: clean.

**Manual checks:**
- With `manage.py demo_data`:
  - Open Results and pick a channel: every figure changes.
  - The clouds show words with counts.
  - The by-channel table matches the overall distribution when the channel filter is cleared.
