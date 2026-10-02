# 07 - Validate generated YouTube API parameters

Story: US-007, Validate generated YouTube API parameters.

Status note: this document describes the US-007 implementation **after** the code review of 2026-10-02 and the fixes that followed it.

## What this story added

US-006 drafts YouTube search parameters from a sentence. This story checks those parameters against YouTube's rules and tells the researcher what is wrong with them.

A researcher can now:

- press **Draft parameters** as before.

- see a **Validation findings** list in the draft panel when a drafted value breaks a rule, for example a language the model wrote as `spanish` instead of `es`.

- see no list at all when the draft is clean.

Nothing is blocked by this story. A draft with findings is still a successful draft. Fixing values is US-008's job and refusing to save bad values is US-009's.

## Why this matters

US-006 already stops the model from inventing parameter **names**. It does not check whether the **values** are ones YouTube accepts. A region of `colombia`, a date of `this year` or a start date later than the end date would all pass through and only fail when a collection run spends quota against the YouTube API.

US-007 answers this question:

```text
Before anything is collected, can the app tell which parameter values YouTube would reject?
```

The answer is now yes, for every rule YouTube documents that can be checked offline.

## Key concept: report, never fix

The validator looks at a parameter set and returns a list of problems. It never changes the parameter set.

That is a deliberate choice. If the code quietly "corrected" `spanish` into `es`, the researcher would not know their request was reinterpreted, and a reproducible research tool must not change a researcher's parameters behind their back. Correcting a value is a human decision, made on the editing screen in US-008.

Each problem is a small object:

```json
{
    "parameter": "relevanceLanguage",
    "code": "invalid_format",
    "message": "relevanceLanguage must be a language code, for example es or zh-Hans."
}
```

- `parameter` says which field the problem belongs to, so US-008 can show it next to that field.

- `code` is one of a small fixed set (`not_allowed`, `missing`, `invalid_type`, `invalid_value`, `invalid_format`, `out_of_range`, `invalid_range`). Code can branch on it.

- `message` is for people. Tests never check it, so the wording can change without breaking anything.

## Key concept: one function, three callers

The rules live in a single pure function, `validate_search_parameters`. "Pure" means it reads its input and returns an answer, with no database, no network and no side effects.

Three stories call it:

- US-007 (this one) on the freshly generated draft.

- US-008 on the values a researcher has edited.

- US-009 at save time, to refuse a parameter set that still has problems.

Writing the rules once means the three screens can never disagree about what is valid.

## File-by-file explanation

### `src/api/core/parameter_validation.py` (new)

Holds the rules. The important names:

- `ALLOWED_SEARCH_PARAMS`: the nine YouTube parameters this app is allowed to send. Any other key is reported as `not_allowed`. Today the draft cannot contain another key, because Python builds it. The allowlist matters once US-008 lets a person edit the object, because then anything could be typed in.

- `REQUIRED_SEARCH_PARAMS`: `part`, `type`, `q` and `maxResults`. An empty object therefore never validates clean.

- `RFC3339_PATTERN`: the shape a YouTube date must have, such as `2026-01-01T00:00:00Z`.

- `REGION_CODE_PATTERN` and `RELEVANCE_LANGUAGE_PATTERN`: the shape of a country code (`CO`) and a language code (`es`, `zh-Hans`).

The rules, in the order they are checked:

| parameter                            | rule                                                               |
| :----------------------------------- | :----------------------------------------------------------------- |
| any key                              | must be one of the nine allowed names                              |
| `part`, `type`, `q`, `maxResults`    | must be present                                                    |
| every key except `maxResults`        | must be a string, so a `null` is reported rather than sent         |
| `part`                               | exactly `snippet`                                                  |
| `type`                               | exactly `video`                                                    |
| `q`                                  | not blank                                                          |
| `maxResults`                         | a whole number from 0 to 50, and not `true`/`false`                |
| `publishedAfter`, `publishedBefore`  | RFC 3339 with a time zone                                          |
| `publishedAfter` / `publishedBefore` | the start is not later than the end, reported on `publishedBefore` |
| `regionCode`                         | two capital letters                                                |
| `relevanceLanguage`                  | a language code, optionally with a subtag such as `-Hans`          |
| `order`                              | one of the six values YouTube accepts                              |

The six `order` values and the limit of 50 are **imported** from `query_translation.py`, not written again. If YouTube changes either one, there is still only one place to edit.

### `src/api/core/views.py`

`SavedQueryDraftView.post` adds one key to its existing response:

```json
"validation": []
```

It is still a `200`. The error table from US-006 is unchanged. Validation findings are information, not an error.

### `src/api/core/tests.py`

Adds `ValidateSearchParametersTests`, plus two tests on the draft endpoint.

The tests that matter most:

- the parameter set `draft_from_response` actually builds validates clean. If the translation code and the validator ever drift apart, this fails.

- a model draft with **every** field filled in, including `publishedBefore`, also validates clean and uses exactly the nine allowed names.

- one broken example for every rule, each asserting the exact `(parameter, code)` list it should produce.

- the input is deep-copied before validation and compared afterwards, which proves "report, never fix".

- a model answer with `relevance_language: "spanish"` still returns `200` from the endpoint, with exactly one finding.

### `src/ui/src/apiClient.ts`

Adds the `QueryParameterValidationFinding` type and a `validation` field on `QueryParameterDraft`.

`isQueryParameterDraft` now rejects a response whose `validation` is missing, is not an array, or contains an element without string `parameter`, `code` and `message`. That runtime check is the trust boundary: without it, a backend mistake would reach the screen as `undefined` and crash the panel.

### `src/ui/src/App.tsx` and `App.css`

Inside the existing draft panel, when there are findings, a **Validation findings** label and a list of `parameter: message` lines appear above the raw JSON. The panel already sits in an `aria-live="polite"` region, so a screen reader announces the findings with the rest of the draft.

The list is read-only. There are no inputs and no buttons are disabled because of it.

## How the pieces connect

```text
App.tsx  "Draft parameters" button
   |
   v
views.py  SavedQueryDraftView
   |
   +--> query_translation.py  translate_prompt()   (US-006, unchanged)
   |
   +--> parameter_validation.py  validate_search_parameters(structured_query_params)
   |
   v
response: the draft + "validation": [findings]
   |
   v
apiClient.ts  isQueryParameterDraft()  checks the shape
   |
   v
App.tsx  draft panel lists the findings
```

## Things the validator deliberately does not do

- **It checks shape, not existence.** `ZZ` looks like a country code and passes, even though no country uses it. A real lookup would need a library such as `pycountry`. The code marks this limit with a `ponytail:` comment, so it is easy to find if it ever matters.

- **It does not call YouTube.** Everything is checked offline. Calling YouTube is US-015.

- **It does not block saving yet.** The existing saved-query endpoint still accepts any JSON object as parameters. US-009 will call this same function there.

- **Equal start and end dates are allowed.** That matches the rule `SavedQuerySerializer` already applies to the saved-query date fields, so the app has one rule, not two.

## Concepts worth understanding

### Why `True` is checked separately

In Python, `bool` is a subclass of `int`, so `isinstance(True, int)` is `True` and `0 <= True <= 50` is also `True`. Without an explicit `bool` check, `{"maxResults": true}` would validate clean. The project's AGENTS.md lists this as a known pitfall.

### Why a regular expression and `fromisoformat` together

`datetime.fromisoformat` accepts many ISO 8601 forms that are **not** RFC 3339, such as `2026-01-01`, `20260101T000000Z` and week dates. YouTube rejects those. The code review also found that it accepts the hour `24`, quietly turning `2026-01-01T24:00:00Z` into midnight of the next day.

So the check has two steps. The regular expression requires the exact RFC 3339 layout, with an hour from `00` to `23`. Then `fromisoformat` rejects dates that have the right shape but do not exist, such as 30 February. Each step catches something the other misses.

### Why the cross-field finding goes on `publishedBefore`

"The start is later than the end" is a problem with two fields. It is reported on `publishedBefore` because the saved-query serializer already reports the same rule there, with the same message. One rule, one wording, one place for the researcher to look.

## Commands

Backend:

```bash
cd src/api
venv/bin/python manage.py test
venv/bin/python manage.py makemigrations --check --dry-run
```

Frontend:

```bash
cd src/ui
npm test
npm run lint
npm run build
```

Passing looks like `OK` from the backend tests, `No changes detected` from the migration check, `fail 0` from `npm test`, and a finished Vite build.

## How to test manually

1. Set `LLM_API_KEY` in `src/api/.env`, start the app and select a project.

2. Draft "Videos about mobility debates in Cali published this year, in Spanish". You should see no **Validation findings** list.

3. To see a finding without depending on the model, call the validator directly:

    ```bash
    cd src/api
    venv/bin/python manage.py shell -c "from core.parameter_validation import validate_search_parameters as v; print(v({'part': 'snippet', 'type': 'video', 'q': 'x', 'maxResults': 51, 'regionCode': 'colombia'}))"
    ```

    You should see one `out_of_range` finding for `maxResults` and one `invalid_format` finding for `regionCode`.

## Known gap

No test renders the draft panel. The frontend tests stop at `apiClient.ts`, because the project has no React rendering test setup and this story did not add a dependency. If the list's condition were inverted, every test would still pass. This is recorded in `_bmad-output/initiative-opentube-insights/deferred-work.md` for when a UI test harness arrives.
