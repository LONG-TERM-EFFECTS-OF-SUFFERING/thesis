---
type: epic
title: "Collected YouTube data is stored, normalized and validated"
parent: initiative-opentube-insights
covers: [US-017, US-018, US-019, US-020, US-024, US-040]
after: []
assignee: ""
risk: low
estimate: ""
estimate_basis: entries
created: 2026-10-02
---

# Collected YouTube data is stored, normalized and validated

## Description

Video, channel and statistics records are stored alongside their raw API payloads, linked to the runs that found them without duplication, then cleaned, normalized and validated into a consistent schema that later analysis can rely on. Every record holding YouTube API data is deleted 30 days after it was fetched, as the YouTube API Services Developer Policies require (III.E.4.d).

## Outcome

Later analysis reads one consistent schema and can still reach the original payload for any record within the 30-day retention window; the signal is a validation report over a stored dataset.

## Requirements

Transcribed from `docs/product_backlog.md`, each line keeping its `US-0NN` id so entries cite the same ids the thesis uses.

- US-017: Store video metadata and raw video payload — Videos are stored with key metadata, the raw YouTube payload and a fetch timestamp that starts the 30-day retention window. (docs/product_backlog.md, User stories, priority must)
- US-018: Store channel metadata and raw channel payload — Channel context is stored and linked to collected videos, including the raw channel payload and a fetch timestamp that starts the 30-day retention window. (docs/product_backlog.md, User stories, priority must)
- US-019: Store video statistics snapshots — Video statistics snapshots are stored with fetch timestamp and source run so changes across runs within the 30-day retention window can be audited. (docs/product_backlog.md, User stories, priority must)
- US-020: Link collection runs to videos idempotently — The app records run-video relationships and can safely update existing records without creating duplicate relationships; re-collecting a video refreshes its payload and fetch timestamp. (docs/product_backlog.md, User stories, priority must)
- US-024: Add basic cleaning, normalization and validation report — The app applies basic normalization rules and reports output counts plus validation errors; normalized records are deleted with the YouTube data they come from. (docs/product_backlog.md, User stories, priority must)
- US-040: Purge YouTube data after 30 days — A management command deletes YouTube data and its derived records older than 30 days, keeps collection run and request log metadata and records when each run's data was purged. (docs/product_backlog.md, User stories, priority must)

## Done when

1. Video and channel metadata are stored with their raw payloads and a fetch timestamp.
2. Statistics are stored as timestamped snapshots rather than overwritten.
3. Re-running a collection links existing videos instead of duplicating them.
4. A cleaning and normalization pass produces a validation report.
5. A purge deletes YouTube data and its derived records 30 days after fetch, keeping run and request-log metadata.

## Boundaries

Storage schema, raw payloads within the 30-day retention window, the purge and the cleaning pass. Not discovery (epic Traceable YouTube collection), not sentiment.

## References

- parent — ../initiative-opentube-insights.md, section Requirements
- backlog — ../../../docs/product_backlog.md, row EPIC-005 and its user-story rows
- sprint plan — ../../../docs/sprint_planning.md
- project context — ../../project-context.md

## Notes

- Assumption: Done when was written from the backlog's epic row and its stories' done-when column; v6 had no epics.md stating epic-level checks. Confirm or correct it.
