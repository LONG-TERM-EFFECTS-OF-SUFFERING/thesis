# YouTube Data API Playground

This playground uses the official `google-api-python-client` to test the YouTube Data API methods covered in your review section:

- `search.list`
- `videos.list`
- `commentThreads.list`
- `comments.list`
- `channels.list`
- `playlistItems.list`

It also includes an OAuth flow to test `channels.list(mine=True)` and then retrieve the authenticated user's uploads playlist with `playlistItems.list`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_youtube_playground.txt
```

## Credentials

### Public data with API key

Set either an environment variable or pass the key as a command-line argument.

```bash
export YOUTUBE_API_KEY="YOUR_API_KEY"
python youtube_data_api_playground.py
```

or

```bash
python youtube_data_api_playground.py --api-key YOUR_API_KEY
```

### OAuth 2.0 for `mine=True`

Create an installed-app OAuth client in Google Cloud, download the JSON file, then run:

```bash
python youtube_data_api_playground.py --client-secret client_secret.json
```

The first OAuth run opens a browser and stores the token in `token.json` by default.

## What the playground tests

### 1. `search.list`
Useful parameters in the menu:
- `q`
- `type`
- `order`
- `publishedAfter`
- `publishedBefore`
- `maxResults`
- `pageToken`
- `fields`

### 2. `videos.list`
Useful parameters in the menu:
- `id`
- `part`
- `fields`

### 3. `commentThreads.list`
Useful parameters in the menu:
- one required filter: `videoId`, `id`, or `allThreadsRelatedToChannelId`
- `part`
- `order`
- `maxResults`
- `pageToken`
- `textFormat`
- `fields`

### 4. `comments.list`
Useful parameters in the menu:
- one required filter: `parentId` or `id`
- `part`
- `maxResults`
- `pageToken`
- `textFormat`
- `fields`

### 5. `channels.list`
Useful parameters in the menu:
- one required filter: `id`, `forHandle`, `forUsername`, or `mine`
- `part`
- `fields`

### 6. `playlistItems.list`
Useful parameters in the menu:
- one required filter: `playlistId` or `id`
- `part`
- `maxResults`
- `pageToken`
- `fields`

## Output and reproducibility

Every response is saved in `./playground_outputs/` as a timestamped JSON file that includes:
- capture time in UTC
- method name
- estimated quota cost
- request parameters
- raw API response

This is useful if you want to document collection settings in your thesis.

## Notes

- `search.list` is much more expensive than the other read methods.
- Every extra page request consumes quota again.
- For text processing, `plainText` is usually easier than `html` for comment endpoints.
- Use `fields` to keep responses smaller and more focused.
