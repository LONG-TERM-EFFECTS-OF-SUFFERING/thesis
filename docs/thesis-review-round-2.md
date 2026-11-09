# Thesis review, round 2 (first read, 2026-11-09)

The author reviewed the document up to Activity A1.3 (section 8.3) and left notes on later sections. This file records what changed in `content/*.tex` and why, the decisions the author took, and what remains open. The same material, with the answers to each question, is in the Claude Doc "Thesis review — first read". App changes from this review are queued in `docs/thesis-review-code-changes.md`.

## Decisions taken by the author

| Topic | Decision | Where it shows |
| :-- | :-- | :-- |
| Tense | Present for what the app does, past for what was done; future only in Future work | Chapters 1–7, 7.4 "Activities carried out" |
| Sentiment model | Keep the hosted OpenAI model; a local model is untested and moves to future work | 8.8.2, Figure 8.1, 9.3 |
| Notebook credit | No citation for the sentiment notebook | 8.8.2 |
| Sprint retrospectives | Not held; the per-story review replaced them | 7.2.2 |
| Sprint planning | One plan made before the first sprint | 7.1.2, 7.2, 7.2.1 |
| "Luna" | OpenAI's model family | Code change 1 |
| Field hints in the app | Built as US-047; when a field has focus, its hint wins over hover | 8.10.2, page 45 |

## What changed in the document

Section numbers are the PDF's.

| Section | Change | Why |
| :-- | :-- | :-- |
| Abstract | Tense; normalization is deterministic and versioned; each sentiment label records its model and prompt | Said sentiment was deterministic; it is an LLM |
| 2 | `\cite` inside parentheses, so no nested "(… (…))" | Author's note |
| 3.1 | Normalization and metrics can be recomputed and labels traced; "inspect and run again"; PROMUEVA "was built to support" | Overclaimed sentiment reproducibility |
| 5 | Scope written in present tense | Tense |
| 6.1 | Citations for transparency (Aguinis et al., 2018) and provenance (W3C PROV-Overview); auditability marked as this work's own definition | Author's note |
| 6.2.1 | Plain wording instead of "semantic understanding of intent …" and "syntactic simplification"; "proposed" removed | Author's note, tense |
| 6.2.3 | Comparison table: Spanish row deleted (both commercial tools support Spanish); 4CAT imports YouTube data from YTDT; request logs hold no raw payloads; Spanish claim limited to the interface | Verified against the sources and the code |
| 6.3.2 | Re-collection does not "drop" deleted videos; analysis is aggregate counts and sentiment; the export contains author identifiers | Author's note; the old privacy claim contradicted the export |
| 7 | Past tense; sprint planning was one upfront plan; retrospectives were not held | Author's decisions |
| 7.3 | "triage" explained; how a test was broken on purpose | Author's note |
| 8 intro | `\label{chap:development}` for cross-references | Needed by 7.x |
| 8.1.3 | "stores" instead of "should store"; maintainability sentence made concrete | Author's note |
| 8.1.4, Figure 8.1 | Five services with `purge`; runs in a background thread; `collect_runs` as recovery; sentiment box says OpenAI | US-044, US-046 |
| 8.2.2 | Channel metadata is used for the channel count and the exports | Author's note |
| 8.2.4 | Paging cost explained (3 pages = 3 × the method's cost) | Author's note |
| 8.2.5 | The repeatable unit is the procedure, worded as a defensible claim | Author's note |
| 8.3.1 | "Stable relationships" made concrete; saved queries are not editable in the app; aggregates described as the final design; privacy controls corrected | Author's note |
| 8.4 | Runs execute from the app (US-044); 8.4.3 renamed "API key authentication …" | Author's note, US-044 |
| 8.5 | `maxResults` (page size) separated from the run's cap; final-result wording; "form, not existence" sentence removed; "single-user" removed | Author's note |
| 8.6 | Version history removed; zero-width joiner explained with a reason | Author's note |
| 8.7.3 | Hourly purge service; skips while a run is collecting | US-046 |
| 8.8.2 | The merged chat-model classifier described; local model untested | US-025 part B had been merged since October |
| 8.9 | Polarizómetro cited as PROMUEVA's tool; language toggle; automatic run reload; filter sentence clarified | Author's note, US-044, US-045 |
| 8.10 | Login described (US-042); language menus (US-043); history removed; field hints (US-047) | Author's note |
| 8.11 | 396 backend and 124 frontend tests; new table rows | Counts were stale |
| 8.12, 8.13 | Why the integration test calls `collect_runs`; validation uses the interface only | US-044 |
| 9.1–9.3 | Test counts; model sentence; limitations (shared keys, runs left running, hosted-model sentiment); future work updated | US-042, US-044, US-046 |

New bibliography entries, each checked against its source: `aguinis2018transparency`, `w3c_prov_overview`, `fourcat_datasources` and `polarizometro`.

## Still open

- **Derived metrics:** the recommendation is to add none and to cite clause III.E.4.h of the YouTube developer policies. The author has not decided.
- **Sprint dates:** May 25 – November 20 is unchanged. The one-word fix "planned" is available.
- **Export privacy:** the text is accurate now. Pseudonymizing authors is code change 5, still to decide.
- **Integration-test corpus size:** no change; the reason is in the Claude Doc.
- **Wording:** "reproducible science", "transparent", "auditable" and similar words in chapters 1–3 have safer alternatives listed in the Claude Doc. They are not applied.
- **TODO markers in the source:**
  - US-039: validation topics, results and table
  - US-037: smoke tests
  - screenshots
- **US-046 merge:** API PR #44 is not merged yet, but the document already describes the hourly purge as done.
