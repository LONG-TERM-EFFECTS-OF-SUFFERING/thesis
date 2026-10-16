---
type: epic
title: "Tests, exports and validation evidence support the thesis"
parent: initiative-opentube-insights
covers: [US-031, US-032, US-033, US-034, US-035, US-036, US-037, US-038, US-039]
after: []
assignee: ""
risk: low
estimate: ""
estimate_basis: entries
created: 2026-10-02
---

# Tests, exports and validation evidence support the thesis

## Description

Component tests cover the database, the collection service, query translation, processing and the presentation layer; the dataset exports as CSV and JSON; and the complete workflow is proven first on synthetic fixtures and then on two real YouTube topics, producing the evidence the thesis reports.

## Outcome

The thesis can demonstrate correctness and reproducibility from recorded evidence rather than assertion; the signal is the end-to-end workflow passing on synthetic fixtures and then on live topics.

## Requirements

Transcribed from `docs/product_backlog.md`, each line keeping its `US-0NN` id so entries cite the same ids the thesis uses.

- US-031: Export videos, channels and logs as CSV — The user can export videos, channels and request logs as CSV files; each export states the collection date and the date its data must be deleted. (docs/product_backlog.md, User stories, priority could)
- US-032: Export raw payloads, sentiment and metrics as JSON or CSV — The user can export raw payloads, sentiment results and derived metrics in a documented format that states the collection date and the date the data must be deleted. (docs/product_backlog.md, User stories, priority could)
- US-033: Add database and model tests — Tests cover important database models and relationships using controlled data, including the 30-day purge and its cascade to derived records. (docs/product_backlog.md, User stories, priority must)
- US-034: Add YouTube collection service tests — Tests cover collection behavior, request logging, dedupe and error handling with controlled responses. (docs/product_backlog.md, User stories, priority must)
- US-035: Add LLM query translation tests — Tests cover natural language translation, allowed parameters, invalid inputs and deterministic fixture examples. (docs/product_backlog.md, User stories, priority must)
- US-036: Add processing tests — Tests cover processing run creation, normalization, validation counts and error reporting. (docs/product_backlog.md, User stories, priority must)
- US-037: Add presentation smoke tests — Tests or smoke checks cover the main user path and key result screens. (docs/product_backlog.md, User stories, priority must)
- US-038: Validate the workflow with synthetic fixtures — A fixture-based path proves query review, collection-like data, processing and visual output without relying on live API availability. (docs/product_backlog.md, User stories, priority must)
- US-039: Validate the workflow with real YouTube topics — A validation run on each of two real YouTube topics records input, collection, processing and chart output within one 30-day retention window; a validation report checks the aggregate results against the requirements. (docs/product_backlog.md, User stories, priority must)

## Done when

1. Videos, channels and logs export as CSV; raw payloads, sentiment and metrics export as JSON or CSV.
2. Each layer has automated tests: database and models, the YouTube collection service, LLM query translation, processing, and a presentation smoke test.
3. The workflow is validated end to end on synthetic fixtures with no live API calls.
4. The workflow is then validated on two real YouTube topics, and a validation report checks the aggregate results against the requirements.

## Boundaries

Automated tests, exports and the thesis validation evidence. Not new product behaviour.

## References

- parent — ../initiative-opentube-insights.md, section Requirements
- backlog — ../../../docs/product_backlog.md, row EPIC-008 and its user-story rows
- sprint plan — ../../../docs/sprint_planning.md
- project context — ../../project-context.md

## Notes

- Assumption: Done when was written from the backlog's epic row and its stories' done-when column; v6 had no epics.md stating epic-level checks. Confirm or correct it.
- Decision (2026-10-16): US-039 validates exactly two real YouTube topics and adds a validation report against the requirements, because thesis activity A4.3 now reads "using real data from two YouTube topics" and its expected result asks for documentation of results against requirements. Backlog row and sprint 13 notes changed with it.
- Open question (US-039): the researcher chooses the two topics, and the run needs live YouTube and OpenAI keys, so a person runs it; it is a recorded manual run, not an automated test, since no test may reach the live APIs. Whether the entry becomes `hitl = true` is the user's call.
