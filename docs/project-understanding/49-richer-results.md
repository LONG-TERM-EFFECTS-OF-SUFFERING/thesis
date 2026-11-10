# 49 - Richer results

Story: US-051, Richer results.

Status note: this page describes US-051 after its review of 2026-11-10 and the fixes that followed (`src/api` PR #48, `src/ui` PR #30). The advisor found the Results section "very basic" in his review of thesis commit `753a97d`; see `docs/thesis-review-code-changes.md` item 12.

## What this story added

Results now shows, next to the old counts and sentiment chart:

- **Comment authors**: how many different people commented. It is only a number; no name or identifier is shown.
- **Sentiment by channel**: for each sentiment model, the 15 channels with the most classified comments, each with a stacked bar and the count and percent of every label written as text.
- **A channel filter** next to the date and video filters. Picking a channel changes every number on the page, and the sentence that describes the filters names the channel.
- **Two word clouds**: the 30 most common tags of the collected videos and the 30 most common words in the comments. Bigger words appear more often, and each word shows its count. Common Spanish and English words ("que", "the", "para") and the `<URL>` placeholder are left out.

## Key concept: computed on request, through your own runs

Nothing new is stored. Every figure is counted when you open the page, and only through the links your project's runs created. A video or comment that another researcher also collected never adds their data to yours. The same rule makes the 5,000-comment cap fair: the comment words are counted over the 5,000 comments your project linked most recently, by your own link time, not by when anyone first saw the comment. The page says when the cap applied.

## Files

- `src/api/core/results.py`:
  - The `channel` filter in `parse_results_filters`.
  - In `results_summary`: `comment_authors`, `sentiment_by_channel`, `top_tags`, `top_terms` and `terms_sampled`.
  - `newest_labels` is shared by the overall chart and the by-channel table, so both apply the same "latest pass, each comment once" rule.
  - `STOPWORDS` is the word list; add to it if a cloud shows filler words.
- `src/api/core/views.py` `ProjectChannelListView`: `GET /api/projects/<id>/results/channels/` for the select.
- `src/ui/src/ResultsSection.tsx`: the channel select, the authors value, the by-channel table and the `WordCloud` lists. The clouds have their own `results-cloud` class, so the chart's grid styles don't squash them.
- `src/ui/src/resultsFilters.ts`: the filter now includes the channel.

## Commands

```bash
cd src/api && venv/bin/python manage.py test   # 435 tests
cd src/ui && npm test                          # 143 tests
```

## How to test manually

1. `venv/bin/python manage.py demo_data`, log in as `demo` and open Results.
2. Pick a channel in the new select: every count, the charts and the clouds change.
3. The by-channel rows add up to the overall chart when no filter is set.
