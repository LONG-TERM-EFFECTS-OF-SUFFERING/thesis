#!/usr/bin/env python3
"""
Interactive playground for YouTube Data API v3 using DIRECT HTTP REQUESTS.
No Google client libraries (google-api-python-client, google-auth) are used,
aligning strictly with the thesis architecture specification.

Covered methods & endpoints:
* search.list          -> GET https://www.googleapis.com/youtube/v3/search
* videos.list          -> GET https://www.googleapis.com/youtube/v3/videos
* commentThreads.list  -> GET https://www.googleapis.com/youtube/v3/commentThreads
* comments.list        -> GET https://www.googleapis.com/youtube/v3/comments
* channels.list        -> GET https://www.googleapis.com/youtube/v3/channels
* playlistItems.list   -> GET https://www.googleapis.com/youtube/v3/playlistItems

Authentication options:
* Public data: API key passed as query parameter (?key=...)
* OAuth 2.0: Bearer token passed in HTTP Authorization header (Bearer <token>)

Environment variables:
* YOUTUBE_API_KEY
* YOUTUBE_ACCESS_TOKEN (optional OAuth 2.0 bearer token)
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

BASE_URL = "https://www.googleapis.com/youtube/v3"
OUTPUT_DIR = Path("playground_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

QUOTA_COSTS = {
    "search.list": 100,
    "videos.list": 1,
    "commentThreads.list": 1,
    "comments.list": 1,
    "channels.list": 1,
    "playlistItems.list": 1,
}

ENDPOINT_PATHS = {
    "search.list": "/search",
    "videos.list": "/videos",
    "commentThreads.list": "/commentThreads",
    "comments.list": "/comments",
    "channels.list": "/channels",
    "playlistItems.list": "/playlistItems",
}

DEFAULT_FIELDS = {
    "search.list": (
        "nextPageToken,items(id/videoId,id/channelId,id/playlistId,snippet/title,"
        "snippet/channelTitle,snippet/publishedAt,snippet/description)"
    ),
    "videos.list": (
        "items(id,snippet/title,snippet/channelTitle,snippet/publishedAt,"
        "statistics/viewCount,statistics/likeCount,statistics/commentCount,"
        "contentDetails/duration)"
    ),
    "commentThreads.list": (
        "nextPageToken,items(id,snippet/topLevelComment/id,"
        "snippet/topLevelComment/snippet/authorDisplayName,"
        "snippet/topLevelComment/snippet/publishedAt,"
        "snippet/topLevelComment/snippet/textDisplay,"
        "snippet/totalReplyCount,replies/comments/id,"
        "replies/comments/snippet/authorDisplayName,"
        "replies/comments/snippet/publishedAt,"
        "replies/comments/snippet/textDisplay)"
    ),
    "comments.list": (
        "nextPageToken,items(id,snippet/authorDisplayName,snippet/publishedAt,"
        "snippet/textDisplay,snippet/parentId)"
    ),
    "channels.list": (
        "items(id,snippet/title,snippet/customUrl,snippet/publishedAt,"
        "statistics/viewCount,statistics/subscriberCount,"
        "statistics/videoCount,contentDetails/relatedPlaylists/uploads)"
    ),
    "playlistItems.list": (
        "nextPageToken,items(id,snippet/title,snippet/channelTitle,"
        "snippet/publishedAt,snippet/resourceId/videoId,"
        "contentDetails/videoPublishedAt,status/privacyStatus)"
    ),
}


@dataclass
class AppConfig:
    api_key: Optional[str]
    access_token: Optional[str]


class DirectHttpClient:
    """Handles raw HTTP requests to YouTube Data API v3 endpoints without external libraries."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def get(self, endpoint_name: str, params: Dict[str, Any], require_oauth: bool = False) -> Dict[str, Any]:
        path = ENDPOINT_PATHS.get(endpoint_name)
        if not path:
            raise ValueError(f"Unknown endpoint method: {endpoint_name}")

        query_params = {k: str(v) for k, v in params.items() if v not in (None, "")}

        headers = {
            "Accept": "application/json",
            "User-Agent": "OpenTube-Playground/1.0 (Direct HTTP Client)",
        }

        # Handle Auth
        if require_oauth or self.config.access_token:
            if not self.config.access_token:
                raise RuntimeError(
                    "OAuth access token required for this call. "
                    "Set YOUTUBE_ACCESS_TOKEN or pass --access-token."
                )
            headers["Authorization"] = f"Bearer {self.config.access_token}"
        elif self.config.api_key:
            query_params["key"] = self.config.api_key
        else:
            raise RuntimeError(
                "No credentials available. Provide an API key (--api-key / YOUTUBE_API_KEY) "
                "or an OAuth Access Token (--access-token / YOUTUBE_ACCESS_TOKEN)."
            )

        full_url = f"{BASE_URL}{path}?{urllib.parse.urlencode(query_params)}"
        req = urllib.request.Request(full_url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as err:
            error_body = err.read().decode("utf-8")
            try:
                parsed_error = json.loads(error_body)
                raise RuntimeError(f"HTTP {err.code}: {json.dumps(parsed_error, indent=2)}")
            except json.JSONDecodeError:
                raise RuntimeError(f"HTTP {err.code}: {error_body}")
        except urllib.error.URLError as err:
            raise RuntimeError(f"Network error: {err.reason}")


### ---------- Input helpers ----------
def ask_str(label: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    while True:
        suffix = f" [{default}]" if default not in (None, "") else ""
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return None
        print("This value is required.")


def ask_int(label: str, default: Optional[int] = None, required: bool = False) -> Optional[int]:
    while True:
        raw = ask_str(label, str(default) if default is not None else None, required=required)
        if raw is None or raw == "":
            return None
        try:
            return int(raw)
        except ValueError:
            print("Please enter an integer.")


def ask_choice(label: str, options: Dict[str, str], default_key: str) -> str:
    print(label)
    for key, description in options.items():
        marker = " (default)" if key == default_key else ""
        print(f"  {key}. {description}{marker}")
    while True:
        value = input("Choose an option: ").strip() or default_key
        if value in options:
            return value
        print("Invalid choice.")


def parse_csv_ids(raw: str) -> str:
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    return ",".join(parts)


### ---------- Output helpers ----------
def timestamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def save_response(method_name: str, request_params: Dict[str, Any], response: Dict[str, Any]) -> Path:
    # Sanitized request params (redact raw API key for privacy/reproducibility)
    sanitized_params = {k: ("***" if k == "key" else v) for k, v in request_params.items()}

    payload = {
        "capturedAtUtc": datetime.now(timezone.utc).isoformat(),
        "method": method_name,
        "endpoint": f"{BASE_URL}{ENDPOINT_PATHS[method_name]}",
        "estimatedQuotaCost": QUOTA_COSTS.get(method_name),
        "request": sanitized_params,
        "response": response,
    }
    filename = f"{timestamp_utc()}_{method_name.replace('.', '_')}.json"
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def print_response_summary(response: Dict[str, Any]) -> None:
    page_info = response.get("pageInfo", {})
    if page_info:
        total = page_info.get("totalResults")
        per_page = page_info.get("resultsPerPage")
        print(f"pageInfo.totalResults: {total}")
        print(f"pageInfo.resultsPerPage: {per_page}")
    if response.get("nextPageToken"):
        print(f"nextPageToken: {response['nextPageToken']}")


def execute_request(client: DirectHttpClient, method_name: str, params: Dict[str, Any], require_oauth: bool = False) -> None:
    path = ENDPOINT_PATHS[method_name]
    full_url = f"{BASE_URL}{path}"
    print("\n" + "=" * 80)
    print(f"Method: {method_name} ({full_url})")
    print(f"Estimated quota cost: {QUOTA_COSTS.get(method_name, 'unknown')} unit(s)")
    print("Request parameters:")
    print(json.dumps(params, indent=2, ensure_ascii=False))
    print("-" * 80)

    try:
        response = client.get(method_name, params, require_oauth=require_oauth)
        print_response_summary(response)
        print(json.dumps(response, indent=2, ensure_ascii=False))
        saved_path = save_response(method_name, params, response)
        print(f"\nSaved raw HTTP response payload to: {saved_path}")
    except RuntimeError as exc:
        print(f"Error executing API request:\n{exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")
    print("=" * 80 + "\n")


### ---------- Playground actions ----------
def run_search_list(client: DirectHttpClient) -> None:
    q = ask_str("Search query (q)", required=True)
    type_value = ask_str("type", default="video")
    order = ask_str("order", default="relevance")
    published_after = ask_str("publishedAfter (RFC3339, optional)")
    published_before = ask_str("publishedBefore (RFC3339, optional)")
    max_results = ask_int("maxResults", default=5)
    page_token = ask_str("pageToken (optional)")
    fields = ask_str("fields (optional)", default=DEFAULT_FIELDS["search.list"])

    params = {
        "part": "snippet",
        "q": q,
        "type": type_value,
        "order": order,
        "maxResults": max_results,
        "publishedAfter": published_after,
        "publishedBefore": published_before,
        "pageToken": page_token,
        "fields": fields,
    }
    execute_request(client, "search.list", params)


def run_videos_list(client: DirectHttpClient) -> None:
    ids = parse_csv_ids(ask_str("Video ID(s), comma-separated", required=True) or "")
    part = ask_str("part", default="snippet,statistics,contentDetails")
    fields = ask_str("fields (optional)", default=DEFAULT_FIELDS["videos.list"])

    params = {
        "part": part,
        "id": ids,
        "fields": fields,
    }
    execute_request(client, "videos.list", params)


def run_comment_threads_list(client: DirectHttpClient) -> None:
    filter_choice = ask_choice(
        "Choose the required filter for commentThreads.list",
        {
            "1": "videoId",
            "2": "id",
            "3": "allThreadsRelatedToChannelId",
        },
        default_key="1",
    )

    filter_params: Dict[str, Any] = {}
    if filter_choice == "1":
        filter_params["videoId"] = ask_str("videoId", required=True)
    elif filter_choice == "2":
        filter_params["id"] = parse_csv_ids(ask_str("Comment thread ID(s), comma-separated", required=True) or "")
    else:
        filter_params["allThreadsRelatedToChannelId"] = ask_str(
            "allThreadsRelatedToChannelId",
            required=True,
        )

    part = ask_str("part", default="snippet,replies")
    text_format = ask_str("textFormat", default="plainText")
    fields = ask_str("fields (optional)", default=DEFAULT_FIELDS["commentThreads.list"])

    params: Dict[str, Any] = {
        "part": part,
        "textFormat": text_format,
        "fields": fields,
    }
    params.update(filter_params)

    if "id" not in filter_params:
        params["order"] = ask_str("order", default="time")
        params["maxResults"] = ask_int("maxResults", default=20)
        params["pageToken"] = ask_str("pageToken (optional)")

    execute_request(client, "commentThreads.list", params)


def run_comments_list(client: DirectHttpClient) -> None:
    filter_choice = ask_choice(
        "Choose the required filter for comments.list",
        {
            "1": "parentId (recommended for replies)",
            "2": "id",
        },
        default_key="1",
    )

    if filter_choice == "1":
        filter_params = {"parentId": ask_str("parentId", required=True)}
    else:
        filter_params = {
            "id": parse_csv_ids(ask_str("Comment ID(s), comma-separated", required=True) or "")
        }

    part = ask_str("part", default="snippet")
    text_format = ask_str("textFormat", default="plainText")
    fields = ask_str("fields (optional)", default=DEFAULT_FIELDS["comments.list"])

    params: Dict[str, Any] = {
        "part": part,
        "textFormat": text_format,
        "fields": fields,
    }
    params.update(filter_params)

    if "id" not in filter_params:
        params["maxResults"] = ask_int("maxResults", default=20)
        params["pageToken"] = ask_str("pageToken (optional)")

    execute_request(client, "comments.list", params)


def run_channels_list(client: DirectHttpClient) -> None:
    oauth_ready = bool(client.config.access_token)
    choices = {
        "1": "id",
        "2": "forHandle",
        "3": "forUsername",
    }
    if oauth_ready:
        choices["4"] = "mine (OAuth 2.0 Access Token required)"

    filter_choice = ask_choice(
        "Choose the required filter for channels.list",
        choices,
        default_key="1",
    )

    params: Dict[str, Any] = {
        "part": ask_str("part", default="snippet,statistics,contentDetails"),
        "fields": ask_str("fields (optional)", default=DEFAULT_FIELDS["channels.list"]),
    }

    require_oauth = False
    if filter_choice == "1":
        params["id"] = parse_csv_ids(ask_str("Channel ID(s), comma-separated", required=True) or "")
    elif filter_choice == "2":
        params["forHandle"] = ask_str("forHandle (with or without @)", required=True)
    elif filter_choice == "3":
        params["forUsername"] = ask_str("forUsername", required=True)
    else:
        params["mine"] = "true"
        require_oauth = True

    execute_request(client, "channels.list", params, require_oauth=require_oauth)


def run_playlist_items_list(client: DirectHttpClient) -> None:
    filter_choice = ask_choice(
        "Choose the required filter for playlistItems.list",
        {
            "1": "playlistId",
            "2": "id",
        },
        default_key="1",
    )

    params: Dict[str, Any] = {
        "part": ask_str("part", default="snippet,contentDetails,status"),
        "fields": ask_str("fields (optional)", default=DEFAULT_FIELDS["playlistItems.list"]),
        "maxResults": ask_int("maxResults", default=5),
        "pageToken": ask_str("pageToken (optional)"),
    }

    if filter_choice == "1":
        params["playlistId"] = ask_str("playlistId", required=True)
    else:
        params["id"] = parse_csv_ids(ask_str("Playlist item ID(s), comma-separated", required=True) or "")

    execute_request(client, "playlistItems.list", params)


def run_my_uploads(client: DirectHttpClient) -> None:
    if not client.config.access_token:
        print("\n[Error] My Uploads flow requires an OAuth access token.")
        print("Please provide --access-token or set YOUTUBE_ACCESS_TOKEN.\n")
        return

    channels_params = {
        "part": "contentDetails,snippet",
        "mine": "true",
        "fields": "items(id,snippet/title,contentDetails/relatedPlaylists/uploads)",
    }
    print("\nRetrieving authenticated user's channel info via GET /channels?mine=true ...")
    try:
        response = client.get("channels.list", channels_params, require_oauth=True)
        save_response("channels.list", channels_params, response)
        print(json.dumps(response, indent=2, ensure_ascii=False))

        items = response.get("items", [])
        if not items:
            print("No channel found for authenticated user.")
            return

        uploads_playlist_id = (
            items[0]
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )
        if not uploads_playlist_id:
            print("Could not find uploads playlist ID.")
            return

        print(f"\nUploads playlist ID: {uploads_playlist_id}")
        playlist_params = {
            "part": "snippet,contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": ask_int("maxResults for uploads playlist", default=10),
            "fields": DEFAULT_FIELDS["playlistItems.list"],
        }
        execute_request(client, "playlistItems.list", playlist_params, require_oauth=True)
    except Exception as exc:
        print(f"Error executing My Uploads flow: {exc}")


def show_help_notes() -> None:
    print(
        """
Notes on Direct HTTP API Integration (Thesis Compliance):
*  This playground uses direct HTTP requests (urllib) without google-api-python-client.
*  Request URLs, parameters, headers, and raw JSON payloads are explicitly exposed and logged.
*  search.list costs 100 quota units; other read endpoints cost 1 unit per request.
*  commentThreads.list requires one filter: videoId, id, or allThreadsRelatedToChannelId.
*  comments.list requires one filter: id or parentId.
*  Use part for required sections and fields to minimize payload size and processing overhead.
*  All response payloads are logged to ./playground_outputs with ISO/UTC timestamps.
""".strip()
    )


MENU = {
    "1": ("search.list (GET /search)", run_search_list),
    "2": ("videos.list (GET /videos)", run_videos_list),
    "3": ("commentThreads.list (GET /commentThreads)", run_comment_threads_list),
    "4": ("comments.list (GET /comments)", run_comments_list),
    "5": ("channels.list (GET /channels)", run_channels_list),
    "6": ("playlistItems.list (GET /playlistItems)", run_playlist_items_list),
    "7": ("My uploads flow (GET /channels?mine=true -> GET /playlistItems)", run_my_uploads),
    "8": ("Show architectural notes & parameter tips", lambda client: show_help_notes()),
    "9": ("Exit", None),
}


def parse_args() -> AppConfig:
    parser = argparse.ArgumentParser(
        description="YouTube Data API v3 Playground (Direct HTTP / No Google Client Library)"
    )
    parser.add_argument("--api-key", default=os.getenv("YOUTUBE_API_KEY"), help="YouTube API key")
    parser.add_argument(
        "--access-token",
        default=os.getenv("YOUTUBE_ACCESS_TOKEN"),
        help="OAuth 2.0 Access Token for authenticated endpoints (e.g. mine=true)",
    )
    args = parser.parse_args()
    return AppConfig(api_key=args.api_key, access_token=args.access_token)


def print_banner(config: AppConfig) -> None:
    print("=" * 80)
    print("YouTube Data API v3 Playground (Direct HTTP Implementation)")
    print("Architecture: Direct REST HTTP requests via standard library (urllib.request)")
    print("Zero dependency on google-api-python-client or Google Auth SDKs")
    print("-" * 80)
    print("Credentials status:")
    print(f"- API key: {'CONFIGURED' if bool(config.api_key) else 'NOT SET'}")
    print(f"- OAuth Access Token: {'CONFIGURED' if bool(config.access_token) else 'NOT SET'}")
    print("=" * 80)


def main() -> int:
    config = parse_args()
    client = DirectHttpClient(config)
    print_banner(config)

    try:
        while True:
            print("\nMenu")
            for key, (label, _) in MENU.items():
                print(f"  {key}. {label}")
            choice = input("Select an option: ").strip()
            if choice == "9":
                print("Bye.")
                return 0
            action = MENU.get(choice)
            if not action:
                print("Invalid choice.")
                continue
            handler = action[1]
            if handler is not None:
                handler(client)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
