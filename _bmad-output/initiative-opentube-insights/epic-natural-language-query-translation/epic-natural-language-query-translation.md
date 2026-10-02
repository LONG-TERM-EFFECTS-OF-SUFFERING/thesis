---
type: epic
title: "Natural-language requests become valid YouTube API parameters"
parent: initiative-opentube-insights
covers: [US-006, US-007, US-008, US-009]
after: []
assignee: ""
status: in-progress
risk: low
estimate: ""
estimate_basis: entries
created: 2026-10-02
---

# Natural-language requests become valid YouTube API parameters

## Description

A researcher states what they want in plain language and the app drafts, validates and presents YouTube Data API parameters for review and approval, so collecting data does not require knowing the API syntax. Translation uses an existing pre-trained model with structured outputs; the parameter set is assembled in application code, never copied verbatim from model output.

## Outcome

A researcher who does not know the YouTube Data API can reach an approved, valid parameter set from a sentence; the signal is a saved query whose parameters the researcher reviewed and accepted.

## Requirements

Transcribed from `docs/product_backlog.md`, each line keeping its `US-0NN` id so entries cite the same ids the thesis uses.

- US-006: Generate draft YouTube API parameters from natural language — The system converts a natural language request into a draft parameter set for YouTube search. (docs/product_backlog.md, User stories, priority must)
- US-007: Validate generated YouTube API parameters — Generated parameters are checked against an allowed list and basic YouTube API rules; controlled tests cover valid and invalid examples. (docs/product_backlog.md, User stories, priority must)
- US-008: Build editable query parameter review screen — The user can inspect generated parameters in a readable form and edit values before saving or running. (docs/product_backlog.md, User stories, priority must)
- US-009: Save approved parameters with validation feedback — The user sees validation errors before saving; approved parameters can be saved as the final query parameters. (docs/product_backlog.md, User stories, priority must)

## Done when

1. A natural-language prompt returns a draft parameter set for `search.list`.
2. Generated parameters are checked against an allowed list and the basic YouTube API rules before anything is collected.
3. The researcher can read and edit every generated value before saving.
4. Only approved, valid parameters are saved, and the model name, prompt version and confidence are stored with them.

## Boundaries

Drafting, validating, reviewing and saving query parameters. Not calling the YouTube API (epic Traceable YouTube collection).

## References

- parent — ../initiative-opentube-insights.md, section Requirements
- backlog — ../../../docs/product_backlog.md, row EPIC-003 and its user-story rows
- sprint plan — ../../../docs/sprint_planning.md
- project context — ../../project-context.md

## Notes

- Assumption: Done when was written from the backlog's epic row and its stories' done-when column; v6 had no epics.md stating epic-level checks. Confirm or correct it.
