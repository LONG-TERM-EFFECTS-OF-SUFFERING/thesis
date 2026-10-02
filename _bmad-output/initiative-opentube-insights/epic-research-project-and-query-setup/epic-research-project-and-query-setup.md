---
type: epic
title: "Researchers organize studies and save collection criteria"
parent: initiative-opentube-insights
covers: [US-004, US-005]
after: []
assignee: ""
status: in-progress
risk: low
estimate: ""
estimate_basis: entries
created: 2026-10-02
---

# Researchers organize studies and save collection criteria

## Description

A researcher creates a research project to group a YouTube study by topic, and saves search queries under it so each dataset carries its research context and the criteria can be reused and audited later.

## Outcome

Every saved dataset is attached to a named project and a stored query, so a reviewer can see which criteria produced it; the signal is that no query exists without a project and an owner.

## Requirements

Transcribed from `docs/product_backlog.md`, each line keeping its `US-0NN` id so entries cite the same ids the thesis uses.

- US-004: Create research project — A project has owner, name, description, status, default language, created date and updated date. (docs/product_backlog.md, User stories, priority must)
- US-005: Save YouTube search query — A saved query belongs to one project and stores the natural language prompt, structured parameters, filters and source. (docs/product_backlog.md, User stories, priority must)

## Done when

1. A project stores owner, name, description, status, default language and timestamps.
2. A saved query belongs to exactly one project and stores the prompt, structured parameters, filters and source.
3. A project and its queries are visible only to their owner.

## Boundaries

Project and saved-query records and their owner scoping. Not query generation (epic Natural language query translation), not running a collection.

## References

- parent — ../initiative-opentube-insights.md, section Requirements
- backlog — ../../../docs/product_backlog.md, row EPIC-002 and its user-story rows
- sprint plan — ../../../docs/sprint_planning.md
- project context — ../../project-context.md

## Notes

- Assumption: Done when was written from the backlog's epic row and its stories' done-when column; v6 had no epics.md stating epic-level checks. Confirm or correct it.
