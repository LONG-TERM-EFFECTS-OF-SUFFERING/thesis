---
type: epic
title: "Comments are collected and scored for sentiment"
parent: initiative-opentube-insights
covers: [US-021, US-022, US-023, US-025, US-026]
after: []
assignee: ""
risk: low
estimate: ""
estimate_basis: entries
created: 2026-10-02
---

# Comments are collected and scored for sentiment

## Description

Top-level comments and their replies are collected for selected videos with pagination and resume handling, stored with their raw payloads and quota cost, then scored by one pre-trained sentiment model whose label, score and model identity are stored and displayed.

## Outcome

A researcher can study audience reaction with the model that produced every score named beside it; the signal is a sentiment record traceable to its comment and its model version.

## Requirements

Transcribed from `docs/product_backlog.md`, each line keeping its `US-0NN` id so entries cite the same ids the thesis uses.

- US-021: Collect top-level comments for selected videos — The app collects top-level comments for selected videos and links comments to videos and collection runs. (docs/product_backlog.md, User stories, priority must)
- US-022: Collect comment replies with pagination and resume handling — The app collects replies, handles pagination and can resume or report partial collection safely. (docs/product_backlog.md, User stories, priority must)
- US-023: Store comment raw payloads, quota and errors — Comment and reply payloads, quota use and errors are stored for reproducibility. (docs/product_backlog.md, User stories, priority must)
- US-025: Run one pre-trained sentiment model and store results — Each analyzed comment stores sentiment label, score, confidence, model name, model version and processing run. (docs/product_backlog.md, User stories, priority must)
- US-026: Show sentiment labels, scores and model information — The UI shows sentiment results clearly, including label, score, confidence and model/version context. (docs/product_backlog.md, User stories, priority must)

## Done when

1. Top-level comments are collected for the videos the researcher selects.
2. Replies are collected with pagination, and an interrupted run resumes without duplicating.
3. Comment raw payloads, quota usage and errors are stored.
4. One pre-trained model produces a label and score per comment, stored with the model name and version and shown in the UI.

## Boundaries

Comment collection and sentiment scoring with an existing pre-trained model. No model training or fine-tuning. Not charts (epic Results visualization and analysis).

## References

- parent — ../initiative-opentube-insights.md, section Requirements
- backlog — ../../../docs/product_backlog.md, row EPIC-007 and its user-story rows
- sprint plan — ../../../docs/sprint_planning.md
- project context — ../../project-context.md

## Notes

- Assumption: Done when was written from the backlog's epic row and its stories' done-when column; v6 had no epics.md stating epic-level checks. Confirm or correct it.
