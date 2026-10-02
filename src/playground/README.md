# YouTube Data API v3 Playground

This playground demonstrates direct HTTP REST endpoint interaction with the YouTube Data API v3, fully adhering to the architectural specification in the thesis (Section 9.1.1):

> _"For the data collection layer, the system uses direct HTTP requests to interact with the YouTube Data API... direct HTTP integration supports a transparent and reproducible implementation, since the request URLs, parameters, response payloads and error handling logic remain visible in the source code."_

Unlike generic client abstractions (e.g., `google-api-python-client`), this implementation uses Python's standard `urllib.request` library to issue explicit `GET` requests directly to `https://www.googleapis.com/youtube/v3/` endpoints.

## Covered API methods and endpoints

1. `search.list` (`GET https://www.googleapis.com/youtube/v3/search`).

2. `videos.list` (`GET https://www.googleapis.com/youtube/v3/videos`).

3. `commentThreads.list` (`GET https://www.googleapis.com/youtube/v3/commentThreads`).

4. `comments.list` (`GET https://www.googleapis.com/youtube/v3/comments`).

5. `channels.list` (`GET https://www.googleapis.com/youtube/v3/channels`).

6. `playlistItems.list` (`GET https://www.googleapis.com/youtube/v3/playlistItems`).

## Setup and execution

### Prerequisites

Python 3.8+ (zero external dependencies required).

```bash
# Clone/navigate to directory and run directly
python3 main.py --help
```

## Credentials and authentication

### Public data with API key (recommended for standard collection)

Pass your API key as an environment variable or command-line flag:

```bash
export YOUTUBE_API_KEY="YOUR_API_KEY"
python3 main.py
```

or

```bash
python3 main.py --api-key YOUR_API_KEY
```

_HTTP Mechanism:_ appends `?key=YOUR_API_KEY` to the direct URL.

### OAuth 2.0 Access Token (for authenticated endpoints like `mine=true`)

If querying authenticated user data, pass a Bearer Token:

```bash
export YOUTUBE_ACCESS_TOKEN="YOUR_OAUTH_ACCESS_TOKEN"
python3 main.py
```

or

```bash
python3 main.py --access-token YOUR_OAUTH_ACCESS_TOKEN
```

_HTTP Mechanism:_ includes header `Authorization: Bearer <YOUR_OAUTH_ACCESS_TOKEN>`.

## Output and audit trail

Every API response is automatically logged in `./playground_outputs/` as a timestamped JSON file containing:

- `capturedAtUtc`: ISO 8601 UTC timestamp.

- `method`: endpoint method name (e.g. `search.list`).

- `endpoint`: full REST URI destination.

- `estimatedQuotaCost`: quota units consumed (e.g. 100 for `search.list`, 1 for others).
- `request`: exact query parameters used.

- `response`: raw JSON payload returned directly by YouTube.

This complete logging ensures auditability and documented data provenance for research replication.
