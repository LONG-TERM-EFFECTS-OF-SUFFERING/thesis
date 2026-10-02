---
type: initiative
title: "A transparent, reproducible web application for YouTube research data"
parent: none
covers: [US-001, US-002, US-003, US-004, US-005, US-006, US-007, US-008, US-009, US-010, US-011, US-012, US-013, US-014, US-015, US-016, US-017, US-018, US-019, US-020, US-021, US-022, US-023, US-024, US-025, US-026, US-027, US-028, US-029, US-030, US-031, US-032, US-033, US-034, US-035, US-036, US-037, US-038, US-039]
after: []
assignee: ""
status: in-progress
risk: low
estimate: ""
estimate_basis: entries
created: 2026-10-02
---

# A transparent, reproducible web application for YouTube research data

## Description

A web application that automates collection, processing, analysis and visualization of YouTube video data for academic research. Existing commercial and social-listening tools are proprietary black boxes; researchers studying YouTube need a system that exposes its collection parameters, processing steps, schemas and validation evidence so another reviewer can reconstruct exactly what happened. The motivating case is PROMUEVA at Universidad del Valle, which needs transparent social-media data infrastructure to support computational models of polarization in Valle del Cauca and Cali.

Collection is a constrained observation of YouTube, not a stable complete representation. Raw payloads, original YouTube IDs, effective query parameters, model metadata, processing summaries and collection timestamps are all preserved for that reason.

## Outcome

A researcher with no knowledge of the YouTube Data API syntax can state a research question in natural language and reach charted, auditable results, with every API request, parameter set and model version recorded; the signal is the end-to-end workflow validated first on synthetic fixtures and then on real YouTube topics (US-038, US-039).

## Requirements

The requirement source is `docs/product_backlog.md`, whose user-story rows carry stable `US-0NN` ids. Those ids are the requirement ids this initiative's epics and entries cite in `covers`; they are also the ids used across `docs/sprint_planning.md`, `docs/project-understanding/` and the thesis chapters, so the traceability spine is unchanged by the move to v7. The eight epic rows in the same document give each epic its own scope.

This initiative deliberately has no PRD and no separate spec: the backlog is the numbered source, referenced rather than restated.

## Done when

1. A natural-language request reaches validated, researcher-approved YouTube API parameters without the researcher writing API syntax (US-006 to US-009).
2. Every collection run records its effective parameters, request log, quota cost, counts, timestamps and errors, and the raw payloads it stored (US-010 to US-024).
3. Comments are collected and scored by one pre-trained sentiment model whose name and version are stored beside every result (US-021 to US-026).
4. Results are readable as summaries, a sentiment distribution chart and filters, and exportable as CSV and JSON (US-027 to US-032).
5. The full workflow passes functional and integration tests, proven on synthetic fixtures before real YouTube topics (US-033 to US-039).
6. Every service runs from Docker Compose on a clean machine using the documented environment variables (US-001 to US-003).

## Boundaries

YouTube only, via the read-oriented Data API resources `search.list`, `videos.list`, `commentThreads.list` and `comments.list`. AI is used only through existing pre-trained models for query translation and sentiment. Not in scope: any other social platform, training or fine-tuning NLP models, real-time streaming analysis, and a native mobile application.

Tracer path: a natural-language prompt becomes a saved query, a collection run discovers videos, their comments are scored, and the result appears in a chart and an export.

- Touch point: `docs/project-understanding/` — one beginner-facing page per completed and reviewed story; owner: whichever epic the story sits in
- Touch point: `content/*.tex` — thesis prose citing the implementation; owned by the thesis, not by any epic

## References

- backlog — docs/product_backlog.md, sections Epics and User stories (the numbered requirement source)
- sprint plan — docs/sprint_planning.md, the thirteen two-week sprints from 2026-05-25 to 2026-11-20
- project context — _bmad-output/project-context.md, sections Technology stack, Library and dependency policy, Critical implementation rules
- learning layer — docs/project-understanding/index.md
- constraint — _bmad-output/project-context.md, section Quota principle: `search.list` costs 100 quota units; prefer the one-unit methods and store discovered IDs
- deferred work — _bmad-output/initiative-opentube-insights/deferred-work.md

## Notes

- Decision: the requirement ids stay `US-0NN` from `docs/product_backlog.md` rather than minting `FR-N` ids, so the thesis traceability spine survives the v6 to v7 migration (2026-10-02).
- Decision: `src/api` and `src/ui` stay nested repositories inside this project; no workspace layout (2026-10-02).
- Open question: no entry declares a prerequisite. v6 recorded no story-level dependencies, and the migration forbids inferring them from list order, so every `after` is empty and `tickets.py next` will report far more as ready to start than really is. One pass of `bmad-ticket` should declare the real prerequisites, starting with epic Natural language query translation, where US-007, US-008 and US-009 all build on US-006.
- Open question: v7 has no sprint concept. `docs/sprint_planning.md` is now the only sprint record and is maintained by hand; the thesis methodology chapter describes adapted Scrum and should say so explicitly.
- Source conflict: `sprint-status.yaml` recorded epics 1 and 2 as `in-progress` although every story under them is `done`. Carried as recorded; `bmad-retrospective` would close them out.
- Unknown: three completed build records (US-001, US-002, US-004) carry no baseline revision, so their plans have none. Not inferred from today's HEAD.
