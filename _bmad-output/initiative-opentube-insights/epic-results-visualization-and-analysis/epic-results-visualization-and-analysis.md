---
type: epic
title: "Researchers read summaries, a chart and filters"
parent: initiative-opentube-insights
covers: [US-027, US-028, US-029, US-030]
after: []
assignee: ""
risk: low
estimate: ""
estimate_basis: entries
created: 2026-10-02
---

# Researchers read summaries, a chart and filters

## Description

A researcher sees how much was collected, how sentiment is distributed, and can narrow the dataset by date, video and sentiment, so the collected data can be interpreted without exporting it first.

## Outcome

A researcher reaches an interpretation of the dataset in the app; the signal is the sentiment distribution readable from the results screen.

## Requirements

Transcribed from `docs/product_backlog.md`, each line keeping its `US-0NN` id so entries cite the same ids the thesis uses.

- US-027: Show results summary counts and card — The results view shows clear counts for projects, runs, videos, channels and available processed records, with the collection date of the data shown. (docs/product_backlog.md, User stories, priority should)
- US-028: Show sentiment distribution chart — After sentiment analysis exists, the results view shows a simple sentiment distribution chart labeled with the collection date of its data. (docs/product_backlog.md, User stories, priority should)
- US-029: Filter results by date and video — Basic filters update visible tables and charts by date range and selected video. (docs/product_backlog.md, User stories, priority could)
- US-030: Filter results by sentiment — After sentiment exists, visible tables and charts can be filtered by sentiment group. (docs/product_backlog.md, User stories, priority could)

## Done when

1. The results screen shows collection counts and a summary card.
2. Sentiment distribution is shown as a chart.
3. Results can be filtered by date, by video and by sentiment label.

## Boundaries

Reading and filtering results in the UI. Not computing sentiment (epic Comments and sentiment analysis), not export.

## References

- parent — ../initiative-opentube-insights.md, section Requirements
- backlog — ../../../docs/product_backlog.md, row EPIC-006 and its user-story rows
- sprint plan — ../../../docs/sprint_planning.md
- project context — ../../project-context.md

## Notes

- Assumption: Done when was written from the backlog's epic row and its stories' done-when column; v6 had no epics.md stating epic-level checks. Confirm or correct it.
