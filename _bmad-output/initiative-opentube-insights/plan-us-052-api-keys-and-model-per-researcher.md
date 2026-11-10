---
title: 'US-052 API keys and model per researcher'
type: 'feature'
ticket: ''
created: '2026-11-10'
status: 'done'
baseline_revision: 'api=53c54fc88fa05c1ad347442acf3650ce4be97a69 ui=4aede2a9f78907f12f890d570228747430b52b13 thesis=7f11aa04a28babd0a626940d594d09c18e38de82'
route: 'full'
route_source: 'auto'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The YouTube key, the LLM key and the models come only from the server's environment, so every account spends the operator's quota. Changing them means editing a file on the server. The advisor and the thesis reviewer asked for each researcher to set their own keys and model from their profile. The advisor also found that sentiment "did not work", because `SENTIMENT_MODEL` is empty by default.

**Approach:**
- A *Settings* section where the logged-in researcher saves a YouTube API key, an OpenAI API key, and the OpenAI model for query drafting and for sentiment, each chosen from a list.
- Everything that calls an external API uses the researcher's values, falling back to the environment's.
- A run uses the keys of the researcher who started it, including for its sentiment step.
- Sentiment is on by default (`SENTIMENT_MODEL=llm` in Compose and `.env.example`). When no LLM key can be resolved, the step is skipped quietly instead of failing.
- OpenAI is the only provider for now, kept in one list so others can be added later (author's decision, 2026-11-09).

## Boundaries & Constraints

**Always:**
- **Write-only keys:** keys never appear in any API response, log line, request log, export or admin page. `GET` reports only whether each key is set.
- **Clearing:** saving an empty key clears it, which falls back to the environment.
- **Resolution order, in one helper:** the researcher's value, then the environment variable (`YOUTUBE_API_KEY`, `LLM_API_KEY`, `LLM_MODEL`, `SENTIMENT_LLM_MODEL`).
- **Model list:** models are validated against a fixed per-provider list in code, starting with OpenAI's `gpt-5.6-luna` and `gpt-6-luna`, plus the current environment defaults. An unknown model returns 400.
- **Who:** settings belong to the effective owner. Anonymous requests with the fallback off get 403, as for projects.
- **The run's own keys:** a run's YouTube calls and its sentiment pass use the keys of `initiated_by_user`, even when another researcher opens it later.
- **Missing keys:** with no YouTube key resolved, starting a run returns 503 as today; with no LLM key resolved, drafting returns 503 as today.
- **Translation:** new UI text is translated (es/en), and key inputs are `type="password"` and never prefilled.

**Never:**
- No new dependency. Keys are stored in plain text in the database, marked with a `ponytail:` comment: encrypt them at rest if the database is shared.
- No admin registration of the settings model, and no provider other than OpenAI yet.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Save keys | PATCH with both keys and models | 200; GET shows `youtube_api_key_set: true`, `llm_api_key_set: true` and the models; no key text in any response | — |
| Own key used | researcher A has a YouTube key; the env has another | A's run calls YouTube with A's key | — |
| Fallback | no saved key; env key set | the env key is used | — |
| Neither | no saved key, no env key | run start 503, draft 503 (unchanged) | 503 |
| Sentiment key | the run was started by A, who has an LLM key and a sentiment model | the sentiment pass uses A's key and model | — |
| No LLM key at all | `SENTIMENT_MODEL=llm`, no key anywhere | sentiment is skipped with one log line; collection and normalization complete | — |
| Bad model | `query_model: "gpt-x"` | 400 naming the allowed models | 400 |
| Clear | PATCH `youtube_api_key: ""` | the key is removed and the env fallback applies again | — |

</frozen-after-approval>

## Code Map

- `src/api/core/models.py`: add `ResearcherSettings` (one-to-one with `settings.AUTH_USER_MODEL`, `related_name="researcher_settings"`, cascade). Fields: `youtube_api_key`, `llm_provider` (choices: `openai`), `llm_api_key`, `query_model` and `sentiment_model`, all blank-able, plus `updated_at`. One migration. Its `__str__` and `repr` must not include keys.
- New `src/api/core/keys.py` (`from __future__ import annotations`, import-safe):
  - `PROVIDER_MODELS = {"openai": ("gpt-5.6-luna", "gpt-6-luna")}`.
  - `resolve_keys(user) -> ResolvedKeys`, a frozen dataclass with `youtube_api_key`, `llm_api_key`, `query_model` and `sentiment_model`, applying the fallback order.
- `src/api/core/views.py`:
  - `SavedQueryDraftView` (~338) uses `resolve_keys(self.get_owner())` instead of `settings.LLM_API_KEY` and `settings.LLM_MODEL`.
  - `CollectionRunStartView` (~398) uses the owner's YouTube key.
  - New `ResearcherSettingsView` (GET, PATCH) at `api/settings/`, with owner resolution as in `ProjectOwnerMixin`.
  - Its serializer has write-only key fields, `*_set` booleans, model validation against `PROVIDER_MODELS` plus the env defaults, and the allowed model lists in the GET payload.
- `src/api/core/sentiment.py` `analyze_comments` (~100) and `src/api/core/llm_sentiment.py` `build_classifier` (~143):
  - Pass the run's `initiated_by_user` resolved keys into the classifier factory. The `CLASSIFIERS` callables may take an optional `ResolvedKeys`; the test classifier ignores it.
  - With `SENTIMENT_MODEL=llm` and no LLM key resolved, return `None` (skipped, with `logger.info`) instead of a failed pass.
- `src/api/core/collection.py`: the background thread already receives `api_key` from the start view, so nothing changes there.
- Tests:
  - New `core/tests/test_keys.py` for resolution and the endpoint: write-only, 403, bad model, clear.
  - Extend `test_views.py` for the draft and run start with own versus env keys (patch the transport and assert the key sent).
  - Extend `test_sentiment.py` / `test_llm_sentiment.py` for the run user's key and the quiet skip.
  - No test reaches a live API.
- Thesis repo `src/docker-compose.yml` and `src/.env.example`, plus `src/api/.env.example`: `SENTIMENT_MODEL` defaults to `llm`.
- `src/ui/src/apiClient.ts`: `getResearcherSettings` and `updateResearcherSettings`, with a type guard and tests using a stubbed `fetch`.
- `src/ui/src/navigation.ts`: add a `settings` section, and `tests/navigation.test.ts`.
- New `src/ui/src/SettingsSection.tsx`, rendered by `App.tsx` like the other sections:
  - Two password inputs, each with "Saved" or "Using the server's key" status and a *Remove* button.
  - Two model selects, from the GET lists.
  - Save, through `latestRequest`.
- `src/ui/src/i18n.ts`: Spanish entries for all of it.

## Tasks & Acceptance

**Execution:**
- [x] Model, migration, `keys.py` and its tests.
- [x] Settings endpoint and serializer, with tests.
- [x] Draft, run start and sentiment use the resolved keys; quiet skip; tests.
- [x] `SENTIMENT_MODEL=llm` defaults in Compose and `.env.example`.
- [x] UI: the client, navigation, `SettingsSection` and i18n, with tests.

**Acceptance Criteria:**
- Given researcher A with their own keys and researcher B without any, when each starts a run, then A's run uses A's keys and B's run uses the environment's.
- Given any API response or log line in the test suite, when a key was saved, then the key text never appears. A test searches the responses and the captured logs.

## Design Notes

**Plain-text storage:** the operator already holds the environment keys and the database. Encryption at rest would need `cryptography` and a new required secret. The `ponytail:` comment and 9.2 of the thesis state this ceiling.

**Thesis follow-ups:**
- 8.1.3: the model is a per-researcher setting.
- 8.4.3: the key comes from the researcher's settings or the environment.
- 8.10.1: remove "What accounts do not separate is cost".
- 9.2: replace "Shared keys"; keep "no rate limiting".
- 8.3 and 8.7: one more table (`researcher_settings`) in Figure 8.2, and the table and migration counts.
- 8.8.2: sentiment is on by default.

## Review Triage Log

Pass 1 (quick), 8 findings: 7 patch, 1 partly deferred.

- **high, patch.** A saved key with a line break passes `CharField` trimming. `http.client` then rejects the `Authorization` header with a `ValueError` that contains the key, and `logger.exception` prints the chained traceback. The reviewer reproduced it. Fix: reject whitespace and control characters inside keys.
- **medium, patch.** The researcher's OpenAI key is sent to `SENTIMENT_LLM_URL`, which may be a local or plain-`http` server. Fix: send the researcher's key only when that URL is OpenAI's endpoint; otherwise use the operator's environment key.
- **medium, patch.** One model list serves both purposes, so `SENTIMENT_LLM_MODEL=llama3` becomes a valid query model and drafting fails with 502. Fix: separate query and sentiment lists, in the API and the UI.
- **medium, patch.** The quiet skip logs at `info`, which no handler shows (there is no `LOGGING` setting), so a missing key silently disables sentiment. Fix: `logger.warning`.
- **medium, patch.** The leak acceptance test avoids a live call only because the fake YouTube transport returns no comments, and it never covers the sentiment path or a failure path. Fix: patch `urlopen`, include a comment, and add an upstream-failure case.
- **low, patch.** The help text says "A blank key uses the server's", but blank keeps the saved key.
- **low, patch.** *Remove* resets unsaved model choices.
- **low, patch and defer.** `docs/ER_diagram.mmd` lacks the new table. Fix: update the `.mmd`. Regenerating the `.svg` needs the Mermaid CLI, a new tool, so it is deferred.

## Verification

**Commands:**
- `cd src/api && venv/bin/python manage.py test && venv/bin/python manage.py makemigrations --check --dry-run` -- expected: pass; the new migration is committed.
- Validate the migration on Compose PostgreSQL (`docker compose up -d db`).
- `cd src/ui && npm test && npm run build && npm run lint` -- expected: clean.
