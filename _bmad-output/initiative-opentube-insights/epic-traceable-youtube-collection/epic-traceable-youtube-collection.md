---
type: epic
title: "Collection runs and API requests are logged and auditable"
parent: initiative-opentube-insights
covers: [US-010, US-011, US-012, US-013, US-014, US-015, US-016]
after: []
assignee: ""
risk: low
estimate: ""
estimate_basis: entries
created: 2026-10-02
---

# Collection runs and API requests are logged and auditable

## Description

Starting a collection from a saved query creates a run with a status lifecycle, and every YouTube API call it makes is logged with its parameters, quota cost, timestamps and errors, so the dataset can be audited and a failed run can be explained.

## Outcome

For any dataset, a reviewer can list the requests that produced it with their parameters and quota cost; the signal is a run whose log accounts for every discovered video.

## Requirements

Transcribed from `docs/product_backlog.md`, each line keeping its `US-0NN` id so entries cite the same ids the thesis uses.

- US-010: Create collection run model and status lifecycle — A run stores project, query, status, started/finished timestamps and basic lifecycle states. (docs/product_backlog.md, User stories, priority must)
- US-011: Start a collection run from a saved query — The user can start a run from a saved query; the backend records effective parameters used for the run. (docs/product_backlog.md, User stories, priority must)
- US-012: Store collection run counts, quota, timestamps and errors — A run records item counts, quota units, timestamps and error message when applicable. (docs/product_backlog.md, User stories, priority must)
- US-013: Create API request log model and service wrapper — YouTube API calls go through one wrapper that records endpoint, method, params, status, quota cost, timestamps, counts and errors. (docs/product_backlog.md, User stories, priority must)
- US-014: Show request logs for each collection run — A run detail page or section shows the request logs linked to that run in a readable table. (docs/product_backlog.md, User stories, priority must)
- US-015: Discover videos with YouTube search.list — The app calls search.list with documented parameters, stores discovered video IDs and avoids unnecessary repeated calls. (docs/product_backlog.md, User stories, priority must)
- US-016: Show video discovery summary — The user can see discovered count, duplicate/skipped count and a basic list of discovered video IDs. (docs/product_backlog.md, User stories, priority must)

## Done when

1. A collection run has a status lifecycle and is started from a saved query.
2. Each run stores its counts, quota usage, timestamps and errors.
3. Every API call is logged through one service wrapper and is visible per run.
4. Video discovery uses `search.list` and reports a summary the researcher can read.

## Boundaries

Run orchestration, request logging and video discovery. Not storing video or channel detail (epic YouTube data storage and processing), not comments.

## References

- parent — ../initiative-opentube-insights.md, section Requirements
- backlog — ../../../docs/product_backlog.md, row EPIC-004 and its user-story rows
- sprint plan — ../../../docs/sprint_planning.md
- project context — ../../project-context.md

## Notes

- Assumption: Done when was written from the backlog's epic row and its stories' done-when column; v6 had no epics.md stating epic-level checks. Confirm or correct it.
