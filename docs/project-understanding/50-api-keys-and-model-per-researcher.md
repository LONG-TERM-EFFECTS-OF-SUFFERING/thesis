# 50 - API keys and model per researcher

Story: US-052, Set API keys and model per researcher.

Status note: this page describes US-052 after its review of 2026-11-10 and the fixes that followed (`src/api` PR #49, `src/ui` PR #31, both stacked on US-051). The advisor and the thesis review asked for it; see `docs/thesis-review-code-changes.md` item 1.

## What this story added

A new **Settings** section (*Configuración*) in the sidebar, where each researcher can:

- save their own **YouTube API key** and **OpenAI API key**;
- pick the OpenAI **model for drafting queries** and the **model for sentiment**.

Their drafts and runs then spend their own quota. If a researcher saves nothing, the server's keys and models from `.env` are used, as before.

A run always uses the keys of the researcher who **started** it, including for its sentiment pass, even if someone else opens it later.

Sentiment is now on by default (`SENTIMENT_MODEL=llm`). That was why "sentiment did not work" for the advisor: it used to be off unless configured. If no OpenAI key exists anywhere, sentiment is skipped with a warning in the server log, and collection still completes.

## Key concept: write-only keys

A key can be sent to the API but never comes back. The settings response only says `youtube_api_key_set: true` or `false`. A key never appears in a response, a log line, the request log, an export or the admin. A test proves this: it saves keys, runs a draft, a collection, a sentiment pass (including one that fails with a traceback) and the exports, then searches every response and every log line for the key text.

The review found two leaks, which are now fixed:

- **A key with a line break inside it** made Python's HTTP library raise an error that contained the key, and that error was logged. Keys with spaces or control characters are now rejected.
- **The researcher's OpenAI key went to whatever sentiment server the operator configured**, which might be a local, plain-`http` server. Now a researcher's key and model are used only with `https://api.openai.com`; any other server gets the operator's key and model.

## Files

- `src/api/core/models.py` `ResearcherSettings`: table `researcher_settings`, one row per user, migration `0017`.
- `src/api/core/keys.py`:
  - `resolve_keys(user)` returns the researcher's value or the environment's;
  - `PROVIDER_MODELS` is the list of allowed OpenAI models;
  - `allowed_models()` builds the query list and the sentiment list.
- `src/api/core/views.py` `ResearcherSettingsView`: `GET` and `PATCH /api/settings/`. The draft and run-start views now use the requesting researcher's keys.
- `src/api/core/llm_sentiment.py` `build_classifier`: the OpenAI-only rule for the researcher's key and model.
- `src/ui/src/SettingsSection.tsx`:
  - the form: password inputs that are never prefilled; a blank input keeps the saved key, and *Remove* falls back to the server's;
  - the two model selects.

## Limit

Keys are stored in the database as plain text, so whoever administers the database can read them. Encrypting them would need the `cryptography` package and a new required secret; a `ponytail:` comment and 9.2 of the thesis record this. The database documentation's ER diagram source (`docs/ER_diagram.mmd`) has the new table, but its `.svg` was not regenerated.

## How to test manually

1. Log in, open *Configuración* and save an OpenAI key. The field empties, and its status says it is saved.
2. Draft a query. It uses your key; check your OpenAI usage page.
3. Click *Remove*. The status says the server's key is used again.
