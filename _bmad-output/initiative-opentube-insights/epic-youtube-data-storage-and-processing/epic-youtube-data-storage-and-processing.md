---
type: epic
title: "Collected YouTube data is stored, normalized and validated"
parent: initiative-opentube-insights
covers: [US-017, US-018, US-019, US-020, US-024]
after: []
assignee: ""
risk: low
estimate: ""
estimate_basis: entries
created: 2026-10-02
---

# Collected YouTube data is stored, normalized and validated

## Description

Video, channel and statistics records are stored alongside their raw API payloads, linked to the runs that found them without duplication, then cleaned, normalized and validated into a consistent schema that later analysis can rely on.

## Outcome

Later analysis reads one consistent schema and can still reach the original payload for any record; the signal is a validation report over a stored dataset.

## Requirements

Transcribed from `docs/product_backlog.md`, each line keeping its `US-0NN` id so entries cite the same ids the thesis uses.

- US-017: Store video metadata and raw video payload — Videos are stored with key metadata and the raw YouTube payload for auditability. (docs/product_backlog.md, User stories, priority must)
- US-018: Store channel metadata and raw channel payload — Channel context is stored and linked to collected videos, including the raw channel payload. (docs/product_backlog.md, User stories, priority must)
- US-019: Store video statistics snapshots — Video statistics snapshots are stored with timestamp and source run so changes over time can be audited. (docs/product_backlog.md, User stories, priority must)
- US-020: Link collection runs to videos idempotently — The app records run-video relationships and can safely update existing records without creating duplicate relationships. (docs/product_backlog.md, User stories, priority must)
- US-024: Add basic cleaning, normalization and validation report — The app applies basic normalization rules and reports output counts plus validation errors. (docs/product_backlog.md, User stories, priority must)

## Done when

1. Video and channel metadata are stored with their raw payloads preserved.
2. Statistics are stored as timestamped snapshots rather than overwritten.
3. Re-running a collection links existing videos instead of duplicating them.
4. A cleaning and normalization pass produces a validation report.

## Boundaries

Storage schema, raw payload preservation and the cleaning pass. Not discovery (epic Traceable YouTube collection), not sentiment.

## References

- parent — ../initiative-opentube-insights.md, section Requirements
- backlog — ../../../docs/product_backlog.md, row EPIC-005 and its user-story rows
- sprint plan — ../../../docs/sprint_planning.md
- project context — ../../project-context.md

## Notes

- Assumption: Done when was written from the backlog's epic row and its stories' done-when column; v6 had no epics.md stating epic-level checks. Confirm or correct it.
