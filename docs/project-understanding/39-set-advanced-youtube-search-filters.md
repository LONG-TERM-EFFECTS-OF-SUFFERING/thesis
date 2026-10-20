# 39 - Set advanced YouTube search filters

Story: US-041, Set advanced YouTube search filters.

Status note: this document describes the US-041 implementation **after** the code review of 2026-10-19 and the fix that followed it.

## What this story added

A collapsed **Advanced search parameters** group under the saved-query form, in the **Queries** section. It sets ten more YouTube `search.list` filters by hand:

| field | `search.list` name | what it does |
| :---- | :---------------- | :----------- |
| Channel ID | `channelId` | only videos from one channel (`UC` + 22 characters) |
| Live events | `eventType` | only `completed`, `live` or `upcoming` broadcasts |
| Location, Location radius | `location`, `locationRadius` | only videos tagged within a radius of a point, for example `3.4516,-76.532` and `50km` |
| Safe search | `safeSearch` | `moderate` (YouTube's default), `none` or `strict` |
| Captions | `videoCaption` | only videos with (`closedCaption`) or without (`none`) captions |
| Category ID | `videoCategoryId` | only one YouTube category, for example `25` = News & Politics |
| Definition | `videoDefinition` | `high` or `standard` |
| Duration | `videoDuration` | `short` (under 4 min), `medium` (4–20 min) or `long` (over 20 min) |
| License | `videoLicense` | `creativeCommon` or the standard `youtube` license |

Each saved query card lists the advanced filters it holds.

The natural-language draft (page 06) does **not** fill these. "Use these parameters" leaves them as they are.

## Why this matters

The draft covers the basics: words, dates, region, language and order. A study often needs a narrower slice: long-form videos only, only captioned videos for transcript work, one channel, or videos near Cali. These filters make that slice part of the saved, audited query instead of a manual step outside the app.

## Key concept: the filters live in the JSON, not in new columns

The filters are stored only inside `structured_query_params`, the JSON object a saved query sends to YouTube. There are no new model fields and no migration.

That is enough for reproducibility, because starting a run copies `structured_query_params` into the run's `effective_params.search_list` (page 11). The filters a run used are frozen with the run, even if the query changes later.

## Key concept: one validator, three gates

`validate_search_parameters` (page 07) now knows the ten new names. The same function checks parameters three times:

- when a draft comes back from the model;
- when a query is saved;
- when a run starts.

An invalid filter never reaches YouTube. The rules:

- **Fixed values:** each filter with fixed values accepts exactly the values in YouTube's reference.
- **Channel id:** `UC` followed by 22 letters, digits, `-` or `_`.
- **Category id:** digits only.
- **Location:** `latitude,longitude` with latitude -90..90 and longitude -180..180.
- **Location radius:** a number plus `m`, `km`, `ft` or `mi`, at most 1000 km.
- **Pairing:** `location` and `locationRadius` must be set together. YouTube rejects one without the other.

## Key concept: two copies of the same list

The UI keeps its own copy of the filter names and allowed values (`ADVANCED_SEARCH_PARAMS`), just as `SEARCH_ORDER_VALUES` already copies the API's order values. That one table:

- draws the form, with a select for fixed values and a text box otherwise;
- builds the request, leaving blank fields out;
- fills the query card.

If YouTube adds a value, both copies change: `SEARCH_ENUM_VALUES` in the API and `ADVANCED_SEARCH_PARAMS` in the UI.

## File-by-file explanation

### `src/api/core/parameter_validation.py`

The allowlist grows from nine to nineteen names. `SEARCH_ENUM_VALUES` holds the allowed values of every fixed-value filter, `order` included. The new checks follow the existing `regionCode` and `relevanceLanguage` ones.

### `src/api/core/tests/`

- **`test_parameter_validation.py`:** every rule above, valid and invalid.
- **`test_views.py`:** a save, and a run start whose `effective_params.search_list` keeps the filters.
- **`test_collection.py`:** the filters reach the real `search.list` request URL.

### `src/ui/src/savedQueryForm.ts` and `src/ui/src/QueriesSection.tsx`

`ADVANCED_SEARCH_PARAMS` and the form fields, keyed by their `search.list` names. The `<details>` group in the form, and the extra rows on each card.

### `src/api/README.md`, `src/ui/README.md`, page 07 and `docs/product_backlog.md`

The new rules, the form group, and the US-041 row under EPIC-002.

## How the pieces connect

```text
Advanced search parameters (form)
  -> buildSavedQueryInput adds the non-blank ones to structured_query_params
  -> POST /api/projects/<id>/queries/  -> validate_search_parameters
  -> Start run -> validate_search_parameters again -> effective_params.search_list
  -> collect_runs -> search.list?...&videoDuration=long&location=...
```

## Commands

```bash
cd src/api
venv/bin/python manage.py test
venv/bin/python manage.py test core.tests.test_parameter_validation
venv/bin/python manage.py makemigrations --check --dry-run
cd ../ui
npm test
npm run lint
npm run build
```

Passing looks like:
- `OK` (365 tests);
- `No changes detected`;
- `pass 104`, no lint output and `✓ built`.

## How to test manually

1. `cd src && ./run-local.sh`, open `http://localhost:5173/#/queries`, and pick a project.

2. Fill **Query name** and **Search term**, open **Advanced search parameters**, and set **Duration** = `long`, **Location** = `3.4516,-76.532`, **Location radius** = `50km`. Click **Save query**.

3. The new card shows LOCATION, LOCATION RADIUS and DURATION.

4. Click **Start run**, then check what the run will send:

   ```bash
   cd src/api
   venv/bin/python manage.py shell -c "from core.models import CollectionRun; print(CollectionRun.objects.latest('created_at').effective_params['search_list'])"
   ```

   The printed object contains `'videoDuration': 'long'`, `'location': '3.4516,-76.532'` and `'locationRadius': '50km'`.

5. Clear **Location radius** and save another query. The save fails with "locationRadius is required when location is set." and nothing is added.

## Common errors

- **"locationRadius is required when location is set."** (or the reverse). Fill both or neither.

- **"location must be latitude,longitude …"** No spaces: `3.4516,-76.532`, not `3.4516, -76.532`.

- **"locationRadius must be a number followed by m, km, ft or mi …"** Write the unit in lowercase, with no space: `50km`, not `50 KM`.

- **A run finds far fewer videos than before.** That is expected. Every filter narrows the search, and `location` keeps only videos YouTube has a location for, which most videos lack.

## Known gaps

- No category picker. The category id is typed by hand, because listing categories would cost a `videoCategories.list` call per region.
- No test checks that the UI's copy of the allowed values matches the API's.
- Six rarer filters stay out on purpose: `channelType`, `videoDimension`, `videoEmbeddable`, `videoPaidProductPlacement`, `videoSyndicated` and `videoType`. `topicId` is deprecated.
- Long values such as `closedCaption` wrap inside the narrow card columns.
