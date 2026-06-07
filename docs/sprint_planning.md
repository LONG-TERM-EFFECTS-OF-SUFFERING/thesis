# Sprint planning

- Sprint length: 2 weeks.

- Capacity: about 20 to 28 total Taiga points per sprint, with higher-density final sprints used to keep all planned user stories within the updated implementation schedule.

| sprint |          dates           |                 sprint goal                  | stories                            | points | notes                                                                                                   |
| :----: | :----------------------: | :------------------------------------------: | :--------------------------------- | :----: | :------------------------------------------------------------------------------------------------------ |
|   1    | 2026-05-25 to 2026-06-05 |        local app and research records        | US-001, US-002, US-004 and US-005. |   24   | By the end, the app should run locally and support basic project and saved-query records.               |
|   2    | 2026-06-08 to 2026-06-19 |   production wiring and parameter drafting   | US-003, US-006 and US-007.         |   22   | Add production-style local wiring, then generate and validate draft YouTube API parameters.             |
|   3    | 2026-06-22 to 2026-07-03 |        query review and approval loop        | US-008 and US-009.                 |   21   | Keep review, editing, validation feedback and approved-parameter saving together as one trust workflow. |
|   4    | 2026-07-06 to 2026-07-17 |     auditable collection run foundation      | US-010, US-011 and US-013.         |   21   | Create the run lifecycle, start saved-query runs and route API calls through logging first.             |
|   5    | 2026-07-20 to 2026-07-31 |     search discovery with service tests      | US-012, US-015 and US-034.         |   22   | Record run telemetry while proving `search.list` behavior with controlled service tests.                |
|   6    | 2026-08-03 to 2026-08-14 |     run observability and video context      | US-014, US-017 and US-018.         |   24   | Expose request logs and persist video/channel payloads so discovery becomes auditable data.             |
|   7    | 2026-08-17 to 2026-08-28 |      discovery integrity and summaries       | US-016, US-019 and US-020.         |   20   | Add discovery summary, statistics snapshots and idempotent run-video links before comment collection.   |
|   8    | 2026-08-31 to 2026-09-11 |        top-level comments foundation         | US-021 and US-023.                 |   21   | Collect top-level comments and preserve raw payloads, quota use and errors for reproducibility.         |
|   9    | 2026-09-14 to 2026-09-25 |    comment depth and first result counts     | US-022 and US-027.                 |   20   | Add reply pagination/resume handling and surface dataset counts while the corpus grows.                 |
|   10   | 2026-09-28 to 2026-10-09 |     processing, sentiment core and tests     | US-024, US-025, US-035 and US-036. |   27   | Normalize data, run one sentiment model and finish core processing and LLM regression tests.            |
|   11   | 2026-10-12 to 2026-10-23 | sentiment labels, filtered review and models | US-026, US-029, US-030 and US-033. |   28   | Show model context and filters, then lock key model relationships with database tests.                  |
|   12   | 2026-10-26 to 2026-11-06 | sentiment chart, export and synthetic proof  | US-028, US-031 and US-038.         |   27   | Visualize sentiment distribution, export core CSV data and validate the workflow with synthetic data.   |
|   13   | 2026-11-09 to 2026-11-20 |   final validation and presentation proof    | US-032, US-037 and US-039.         |   23   | Export preserved research outputs, run presentation smoke checks and record real-topic thesis evidence. |
