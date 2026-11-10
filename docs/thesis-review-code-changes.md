# App code changes from the thesis review (round 2)

Code changes that came out of the 2026-11-09 first read of the thesis, queued to run in another session (bmad-build, one story each). They are ordered by value for the defense. Nothing here has been implemented. Each item lists its document follow-up, the `.tex` passage to change once it ships.

Ground rules: the stack versions in `AGENTS.md`, no new dependency without a stated reason, and no test reaches a live API.

| # | Change | Why | Size | Status |
| :-: | :-- | :-- | :-: | :-- |
| 1 | API keys and model chosen in the app | the reviewer and the advisor (2026-11) asked for it; today every account spends the operator's keys | L | to plan |
| 2 | Region code from a list, validated for existence | removes the "form, not existence" limitation | S | to plan |
| 3 | Mark a stuck run as failed from the admin | today only the Django shell can unblock the hourly purge | XS | to plan |
| 4 | Local sentiment model as default, plus a comparison | the advisor asked again in his review of `753a97d`; it "did not work" for him | M | not now: OpenAI stays the default (re-decided 2026-11-09 after the advisor's review); local stays future work |
| 5 | Pseudonymize authors in the dataset export | only if you want the stronger privacy claim | S | decide first |
| 6 | Keep the zero-width joiner between emoji | optional; the document now defends the current rule | S | probably skip |
| 7 | Presentation smoke tests (US-037) | already in the backlog; 8.11.3 says they are pending | M | backlog |
| 8 | Explain each query field in the form | a researcher cannot tell what `order`, `closedCaption` or "Max videos" mean | S | done: US-047, `src/ui` PRs #25 and #26 |
| 9 | Edit and archive projects in the UI | advisor: projects have no edit or delete | S | done: US-049, `api` PR #46, `ui` PR #28 |
| 10 | Edit a saved query until its first run | advisor: queries should be editable, at least before a search | S | to plan |
| 11 | Configurable retention period, or no purge | advisor: deletion should be configurable for future policy changes | S | done: US-048, `api` PR #45, `ui` PR #27 |
| 12 | Richer Results: authors, sentiment by channel, channel filter, tag cloud | advisor: the visualization is very basic | M–L | to plan |
| 13 | Screenshots in the thesis, plus an annex | advisor: no evidence of what was built; add a figure for 8.5.1 | M | after 9–12 |

Not on this list on purpose: engagement metrics (views per like and similar). Clause III.E.4.h of the YouTube developer policies forbids creating new or derived metrics from API data, and the statistics snapshots are already stored and exported for anyone who needs them.

## 1. API keys and model chosen in the app

**Request (reviewer):** the researcher enters their YouTube API key and their LLM key, and selects the model. For now the only provider is OpenAI, with its `luna` models (confirmed 2026-11-09): `gpt-5.6-luna` for query translation and `gpt-6-luna` for sentiment. Leave room for other providers.

**Shape (to confirm in planning):**
- Settings are per account: a one-to-one model next to `auth_user` (for example `ResearcherSettings`), with:
  - `youtube_api_key`, `llm_provider` and `llm_api_key`
  - `query_model` and `sentiment_model`
- Resolution order, in one helper: the account's value, then today's environment variable (`YOUTUBE_API_KEY`, `LLM_API_KEY`, `LLM_MODEL`, `SENTIMENT_LLM_MODEL`), so Compose deployments keep working.
- Keys are **write-only** through the API. `GET` says only whether each key is set, and keys never appear in logs, request logs or exports.
- Storage:
  - Plain text in the database is the zero-dependency option, and it is visible to anyone with database access.
  - Encryption at rest needs `cryptography` (Fernet), a new dependency, so the plan must justify it.
  - Decide in planning.
- Provider list: one dict, for example `PROVIDERS = {"openai": {"responses_url": …, "chat_url": …, "models": [...]}}`. A new provider is a new entry, with no new code path.
- Where the keys are read today:
  - `CollectionRunStartView.post` passes `settings.YOUTUBE_API_KEY` to the thread.
  - `core/query_translation.py` reads `LLM_API_KEY` and `LLM_MODEL`.
  - `core/llm_sentiment.py` `_llm_classifier` builds the classifier from settings.

  The sentiment step runs inside the collection thread, so it must use the settings of the account that **started the run**, not those of whoever views it.
- UI: a *Settings* section in the sidebar with `type="password"` inputs (never prefilled), a provider select and a model select, translated through `i18n.ts`.
- Tests:
  - the key is never in a response, a log line or an export;
  - the account value wins over the environment, and the environment is the fallback;
  - with neither set, the run start is `503` and the draft is `503`, as today.

**Document follow-ups:**
- `09_1_1` LLM integration approach: "The model is a configuration value (`LLM_MODEL` …)" becomes a value chosen by each researcher, with the environment as a fallback.
- `09_3_5` Research projects: the sentence "What accounts do not separate is cost …".
- `10-conclusions` Limitations: "Shared keys and no rate limiting". Keep the rate-limit part.
- `10-conclusions` Future work, first item: drop "let each researcher use their own API keys".

## 2. Region code from a list, validated for existence

- Backend: `core/parameter_validation.py` checks `regionCode` against `REGION_CODE_PATTERN` only, so `ZZ` passes. Add a fixed list, a `frozenset` of the ISO 3166-1 alpha-2 codes, and report `invalid_value` for a well-formed but unknown code. No dependency: the list is a constant with a dated comment naming its source.
- UI: replace the free text field with a `<select>`, following the US-043 `LANGUAGE_OPTIONS` pattern in `savedQueryForm.ts`. That includes the extra option for a drafted code that is not in the list, so an LLM draft never shows a wrong value. Country names go through `i18n.ts`.
- Tests: `ZZ` is rejected with `invalid_value` at all three points (draft, save, run start), and `CO` passes.

**Document follow-ups:**
- `10-conclusions` Limitations: delete "Validation of form, not existence".
- `09_2_2` Validation, list of rules: "the formats of region and language codes" becomes "region codes from the ISO 3166 list and the format of language codes".

## 3. Mark a stuck run as failed from the admin

A run whose process dies stays `running`. The UI then keeps polling it, and since US-046 the hourly purge skips. `CollectionRunAdmin` has `status` read-only, so today only the Django shell can fix it (`deferred-work.md`, US-046 entry).

- Smallest fix: an admin action "Mark selected runs as failed". It calls `run.transition_to("failed", error_message="Marked failed by an administrator.")`, which stamps `finished_at` and uses the compare-and-set update, and it skips runs that are not `running`.
- Test: the action fails a `running` run and leaves a `completed` run untouched.
- Larger option, not needed now: an automatic sweep that fails runs `running` for longer than a cutoff.

**Document follow-up:** `10-conclusions` Limitations, "Runs left running": "until an administrator marks the run as failed" is then true from the admin site, not only from the shell. Add "from the administration site".

## 4. Local sentiment model as default, plus a comparison

The advisor asked, around 2026-10-24, for a **local** pre-trained model as the default, the GPT option as configurable, and a comparison of the two. Today the only registered classifier is the chat-model one (`"llm"`), with OpenAI as the default endpoint.

- No-code half: `SENTIMENT_LLM_URL` can already point at a local OpenAI-compatible server (Ollama, llama.cpp, vLLM) running a local model. That makes "local" possible without code, but not the default.
- Code half, if wanted:
  - a second classifier key, for example `"local"`, with its own default URL and model;
  - a way to run a second sentiment pass on an existing collection run, for example a `sentiment_pass <run_id> --model local` command, since passes are already separated by model name and version.

  The comparison is then a query: the same comments, two labels.
- **Decided 2026-11-09:** keep the hosted OpenAI model as the default. Local models are supported by the endpoint setting but were never tested, so the thesis lists them as future work (`10-conclusions`, Future work). Nothing to build before delivery.

**Document follow-ups:**
- None before delivery. `09_3_3` already says a local model is untested, and `10-conclusions` Future work lists the test and the comparison.

## 5. Pseudonymize authors in the dataset export

`dataset.json` exports `author_channel_id` and the raw comment payloads, which include `authorDisplayName`. The document now states this honestly (`07` Data privacy, `09_1_3` Ethical and privacy controls). For the stronger claim that exports contain no author identities:
- replace `author_channel_id` with a per-export salted hash;
- drop the author fields from each exported `raw_payload`.

Check with PROMUEVA first: comment-network analysis needs a stable author key. A salted hash keeps the links between comments and removes the identity.

**Document follow-ups:** the two privacy passages above.

## 6. Keep the zero-width joiner between emoji

Rule 3 removes U+200D, so a family emoji becomes three emoji. Keeping it only between two emoji needs an emoji test that the standard library lacks: either the `regex` module (a new dependency) or a hand-written code-point range check. It would become `comment-text-v3`. The document now explains the trade-off (`09_3_1`), so this is optional.

## 7. Presentation smoke tests (US-037)

Already in the backlog. `09_4_1` and `10-conclusions` keep `% TODO(US-037)` markers for it.

## 8. Explain each query field in the form

**Done as US-047 (2026-11-09).** The hints show above the field rather than under it, with focus taking priority over hover and Escape to dismiss. Explainer: `docs/project-understanding/45-explain-each-query-field.md`. The `.tex` sentence below is applied.

Requested 2026-11-09: hovering or focusing a field says what it means. Today only the Draft button, *Use these parameters* and the *Advanced search parameters* group have a hint (`draft-hint` spans in `QueriesSection.tsx`), and four advanced fields have a placeholder. The main fields and every advanced select have no explanation. The selects also show raw API values such as `closedCaption` or `creativeCommon`.

- Lazy option: a `title` attribute on each `<label>` gives a hover tooltip with no code beyond the text. But `title` never shows on touch screens or to keyboard users, so it cannot be the only way in.
- Recommended: one short hint line under each field, reusing the existing `draft-hint` style, tied to the input with `aria-describedby`, plus the same text as `title`. The texts live in one list next to `ADVANCED_SEARCH_PARAMS` in `savedQueryForm.ts` and go through `t()`, so each needs a Spanish entry in `i18n.ts`, which the build enforces. While there, give the advanced select values readable labels and keep sending the API value.
- Content to cover:
  - the search term (`q`)
  - the dates, as UTC instants
  - **Max videos to discover**: the run's total cap, not `maxResults`
  - region, language and `order`, with what each order value does
  - comments per video and replies per comment, and their quota cost
  - each advanced filter

  The wording can come from the parameters table (`tab:youtube_api_parameters`) in `09_1_2`.
- Test: a node test that every field name in the form has a hint, so a new field without one fails.

**Document follow-up:** `09_3_5` Saved queries: one sentence saying every field shows a short explanation of what it sends to YouTube.

## Advisor review of `753a97d` (2026-11)

The advisor reviewed `main.pdf` and the app at thesis commit `753a97d` (2026-11-02). Items 9–13 come from that review, and items 1 and 4 got stronger support from it. The document's em dash, his only point about style, was fixed on 2026-11-09.

## 9. Edit and archive projects in the UI

**Today:** the API can already update a project: `ResearchProjectDetailView` is a `RetrieveUpdateAPIView`, so `PATCH` works. The model's `status` is `active` or `archived`. The Projects section can only create and select projects.

- Add an *Edit* form to the project card for name, description, default language and status, sending `PATCH` through `latestRequest`.
- For delete, offer **Archive** (`status=archived`) and hide archived projects behind a "Show archived" filter. A real delete would cascade to saved queries, runs and request logs, the methodological record 8.10.1 promises to keep, so it stays in the admin.
- If the advisor insists on real deletion: add a `DELETE` endpoint behind a typed confirmation (enter the project name), and change 8.10.1.

**Document follow-up:** `09_3_5` 8.10.1, "The API allows projects to be listed, created, read and updated; it does not delete them".

## 10. Edit a saved query until its first run

**Today:** `SavedQueryListCreateView` only lists and creates. 8.10.2 says a changed criterion is saved as a new query.

- Add `PATCH` on a saved query while it has **no collection runs**; once a run exists, answer `409`. Runs already snapshot `effective_params`, so editing after a run would not lose history. Freezing after the first run keeps "the query that started this run" unambiguous, which is the advisor's minimum.
- Re-validate with `validate_search_parameters`, the same validator used at draft, save and start.
- UI: an *Edit* button on the card, shown only while the query has no runs, that loads the card into the form. The form gets a *Save changes* mode and keeps the LLM provenance rules: editing the prompt drops the provenance.

**Document follow-up:** `09_3_5` 8.10.2, the paragraph "Saved queries can be created and listed but not edited", and `09_1_3`, the "Collection traceability" sentence.

## 11. Configurable retention period, or no purge

**Today:** `RETENTION_DAYS = 30` is a constant in `core/purge.py`, also used for the exports' `delete_by` dates (`core/views.py`).

- Move it to `settings.py` as `YOUTUBE_RETENTION_DAYS`, read with the env helpers: default 30, and `0` means "never purge".
- Purge and exports read the setting:
  - With `0`, `purge_youtube_data` prints "Retention disabled" and exits 0.
  - With `0`, the exports' `delete_by` is empty.
- Add a Django system-check **warning** when the value is above 30 or 0, because the YouTube developer policies (III.E.4) allow at most 30 days. The setting exists for future policy changes or for data not obtained from the API, not for keeping API data longer.
- Tests:
  - 7 days purges after 7 days;
  - 0 never purges;
  - the warning appears above 30.
- The integration test compares against a literal 30 days on purpose, so it should set the value explicitly.

**Document follow-ups:**
- `09_3_2` 8.7.3 and `07` 6.3.2: "30 days by default, configurable".
- `06` scope exclusions.
- `10` limitations or conclusions, if needed.

## 12. Richer Results

**Today** (`core/results.py`, `ResultsSection.tsx`):
- counts of runs, videos, channels, top-level comments, replies and snapshots, plus the collection period;
- a date-range filter and a video filter;
- one sentiment distribution per model.

The channel count the advisor asked for already exists, but it is easy to miss.

Proposed, in order of value for the defense:

1. **Distinct comment authors**: a count of distinct `author_channel_id` through the project's runs. It is aggregate, so no identities are shown.
2. **Sentiment by channel**: one row per channel with its comment count and its label distribution, as a stacked bar table. Channels are creators, not the private commenters protected in 6.3.2.
3. **Channel filter**, next to the date and video filters, applied to every count. This also gives the advisor his interactive date-and-channel view.
4. **Tag cloud** from the collected videos' `tags`, which are already stored, plus the top N terms of normalized comment text with a small stopword list for Spanish and English. Render it as a sized-word list in CSS, with no chart library.

Every new figure is computed on request, like the existing ones (8.3.1), so the purge needs no new rule. A word cloud of comment text is derived from API data; 6.3.2 should mention it next to sentiment, as an aggregate computed on request and never stored.

**Document follow-ups:** `09_3_3` 8.8.1, `09_3_4` 8.9.3, and the US-039 validation table.

## 13. Screenshots in the thesis, plus an annex

The advisor saw no screenshots and asked for an example figure for 8.5.1.

- Take the screenshots **after** items 9–12, so they show the final interface.
- Real data is better evidence: run US-039 with a real `YOUTUBE_API_KEY` and `LLM_API_KEY` in `src/.env`. There is no `.env` locally today. Fallback: the `demo_data` command creates a synthetic collected project offline; its screenshots must say "synthetic demo data" in the caption.
- Capture headless with Playwright from a throwaway environment, so no dependency goes into the repo. Save the images under `figures/` in the thesis repo.
- Main text (one figure per section):
  - 8.5.1: the draft panel for a real prompt, with numbered callouts (prompt → typed draft fields → built parameters → validation findings → *Use these parameters*), next to a small TikZ flow diagram;
  - 8.9.2: the run detail;
  - 8.9.3: Results;
  - 8.10: Projects and Queries.
- Annex: the login screen, the field hints, the advanced filters, a saved-query card, the request log, the exports and the Spanish/English toggle.

