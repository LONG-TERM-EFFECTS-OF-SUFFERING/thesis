# 29 - Add LLM query translation tests

Story: US-035, Add LLM query translation tests.

Status note: this document describes the US-035 implementation **after** the code review of 2026-10-08 and the fix that followed it. Like pages 15, 21 and 24, this story added **tests only**.

## What this story added

The query translator turns a researcher's sentence ("videos about mobility in Cali from the first half of 2026") into YouTube search parameters by asking an OpenAI model (US-006). It was already well tested: 55 tests from US-006, US-007 and US-009. An audit found two gaps, and this story fills them:

1. **A table of worked examples.** Before, there was a single example of model output. Now `TRANSLATION_EXAMPLES` holds five cases, each with the exact draft and validation result it must produce.

2. **One test of the whole path.** Every draft-endpoint test used to replace the function that calls OpenAI, so the real request code never ran with the view. The new tests fake only Python's network call, `urllib.request.urlopen`, the same approach US-034 took for YouTube (page 15).

## Why this matters

The thesis claims the translation is **predictable**: the same sentence gives the same request, and the model's answer is checked before a researcher sees it. The example table is that claim written down as evidence a reader can rerun. The end-to-end tests prove that the real code sends what the claim says, to the right place, with the right safety rules.

## Key concept: the example table

Each entry in `TRANSLATION_EXAMPLES` holds a prompt, the project's language, the model's JSON answer (shaped like the OpenAI Responses API), and the **exact** expected draft and validation findings.

| case | what it shows |
| :-- | :-- |
| Spanish, date window, cap 30 | dates and the cap become search parameters |
| English, region `GB`, language `en`, 200 videos asked | `maxResults` is capped at YouTube's 50 per request |
| no dates, no cap, project without a language | missing values are left out, not sent as `null` |
| `order` = `viewCount` | the ordering choice passes through |
| "from" date after "to" date | the draft is still returned, with an `invalid_range` finding (US-007: findings inform, never block) |

The checks compare **whole values** with `assertEqual`, never "contains". AGENTS.md records a past test that passed because it looked for a substring the prompt itself already contained.

The payloads are modelled on the API documentation and the earlier fixture, not recorded from a live call, and a comment says so.

## Key concept: determinism

The model's answer can vary, but **our** side must not. One test translates the same prompt for the same project twice and checks:

- the request bodies are identical, byte for byte, once serialized;
- the same model answer gives an equal draft.

So any difference between two runs comes from the model, never from the app.

## Key concept: the real path, end to end

The end-to-end tests POST to `/api/projects/<id>/queries/draft/` with only `urlopen` faked, so the view, the prompt builder, the HTTP code, the answer parser and the validator all run for real. They check:

- the request goes to `https://api.openai.com/v1/responses` as a POST, with `Authorization: Bearer <key>`;
- it asks for **strict** structured output with the project's schema (`DRAFT_SCHEMA`);
- the researcher's sentence is the user message, and the project's language hint is in the system message only when the project has one;
- the response is exactly the expected draft, including the model name, prompt version and validation list;
- a model **refusal** returns `422`;
- an **upstream error** returns a generic `502`. The operator's log names the status (`HTTP 500`), and neither the log nor the response ever contains the API key, even though the fake error deliberately includes it;
- **round trip:** saving the draft as-is stores a query marked `llm_generated`, with the same provenance and parameters.

## Key concept: a test that could not fail

The implementer checked the new tests by breaking the product code 24 ways, and each break made a test fail. The review found one recorded result that wasn't true: removing the HTTP status from the log line did **not** fail anything. The test only checked that *some* warning was logged, not what it said. It now checks the log's content, and the same break does fail it. Checking a test by breaking the code is how such gaps are found.

## File-by-file explanation

### `src/api/core/tests.py`

- `TRANSLATION_EXAMPLES`: the five cases, beside `OPENAI_DRAFT_RESPONSE` and `OPENAI_REFUSAL_RESPONSE`.
- `QueryTranslationExampleTests`: each case, plus determinism.
- `QueryTranslationEndToEndTests`: the endpoint through the real path, the refusal, the upstream error and the round trip.

No product file changed.

## How the pieces connect

```text
POST /api/projects/<id>/queries/draft/   {natural_language_prompt}
   '-- SavedQueryDraftView
          '-- translate_prompt(prompt, model, key, project language)
                 builds the request body (system + user messages, strict DRAFT_SCHEMA)
                 '-- _post_json -> urllib.request.urlopen   <- the only fake
                 '-- draft_from_response(answer)            (parse, clamp, drop nulls)
          '-- validate_search_parameters(draft)             (findings, never errors)
   <- 200 draft + validation | 422 refusal | 502 upstream failure

then POST /api/projects/<id>/queries/  (the draft, named) -> saved as llm_generated
```

## Commands

```bash
cd src
docker compose up -d db
cd api
DATABASE_ENGINE=postgresql venv/bin/python manage.py test --noinput
venv/bin/python manage.py test core.tests.QueryTranslationExampleTests core.tests.QueryTranslationEndToEndTests
```

Passing looks like `OK` (281 tests). The second command runs only this story's tests.

## How to test manually

This story adds no screen. To see what the tests guard, break one rule on purpose. For example, in `_post_json` (`src/api/core/query_translation.py`), remove `"Authorization"` from the headers. Run `QueryTranslationEndToEndTests`, watch it fail, then restore the file with `git checkout core/query_translation.py`.

## Common errors

- **A test fails with a mismatched dict after you change a rule in `draft_from_response`.** That is the example table doing its job. If the change is intended, update the expected values for that case, and say why in the commit.

## Known gaps

- The examples are not recorded from live calls. Validation with real topics and the live API is US-039.
