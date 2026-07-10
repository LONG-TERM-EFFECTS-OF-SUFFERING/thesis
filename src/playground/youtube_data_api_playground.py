#!/usr/bin/env python3
"""
Interactive playground for the methods listed in 09_1_2-YouTube_Data_API_review.

Covered methods:
- search.list
- videos.list
- commentThreads.list
- comments.list
- channels.list
- playlistItems.list

Auth:
- Public data: API key
- Private 'mine=True' calls: OAuth 2.0 (optional)

Environment variables:
- YOUTUBE_API_KEY
- YOUTUBE_CLIENT_SECRET_FILE
- YOUTUBE_TOKEN_FILE (optional, default: token.json)

Install:
    pip install -r requirements_youtube_playground.txt

Run:
    python youtube_data_api_playground.py
    python youtube_data_api_playground.py --api-key YOUR_KEY
    python youtube_data_api_playground.py --client-secret client_secret.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    Request = None
    Credentials = None
    InstalledAppFlow = None


SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
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
    client_secret_file: Optional[str]
    token_file: str


class ServiceFactory:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._api_key_service = None
        self._oauth_service = None

    def public_service(self):
        if self._api_key_service is not None:
            return self._api_key_service

        if self.config.api_key:
            self._api_key_service = build(
                "youtube",
                "v3",
                developerKey=self.config.api_key,
                cache_discovery=False,
            )
            return self._api_key_service

        if self.config.client_secret_file:
            print("No API key found. Falling back to OAuth 2.0.")
            return self.oauth_service()

        raise RuntimeError(
            "No credentials available. Set YOUTUBE_API_KEY or provide --api-key."
        )

    def oauth_service(self):
        if self._oauth_service is not None:
            return self._oauth_service

        if not self.config.client_secret_file:
            raise RuntimeError(
                "OAuth client secret file not configured. Set YOUTUBE_CLIENT_SECRET_FILE or use --client-secret."
            )

        if InstalledAppFlow is None or Credentials is None or Request is None:
            raise RuntimeError(
                "OAuth dependencies are missing. Install google-auth-oauthlib and google-auth-httplib2."
            )

        creds = None
        token_path = Path(self.config.token_file)

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config.client_secret_file,
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json(), encoding="utf-8")

        self._oauth_service = build(
            "youtube",
            "v3",
            credentials=creds,
            cache_discovery=False,
        )
        return self._oauth_service

    def close(self) -> None:
        for service in (self._api_key_service, self._oauth_service):
            if service is not None and hasattr(service, "close"):
                service.close()


# ---------- Input helpers ----------

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



def ask_yes_no(label: str, default: bool = False) -> bool:
    default_text = "Y/n" if default else "y/N"
    value = input(f"{label} [{default_text}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes"}



def parse_csv_ids(raw: str) -> str:
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    return ",".join(parts)


# ---------- Output helpers ----------

def timestamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")



def save_response(method_name: str, request_params: Dict[str, Any], response: Dict[str, Any]) -> Path:
    payload = {
        "capturedAtUtc": datetime.now(timezone.utc).isoformat(),
        "method": method_name,
        "estimatedQuotaCost": QUOTA_COSTS.get(method_name),
        "request": request_params,
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



def execute_request(method_name: str, request_params: Dict[str, Any], request) -> None:
    print("\n" + "=" * 80)
    print(f"Method: {method_name}")
    print(f"Estimated quota cost: {QUOTA_COSTS.get(method_name, 'unknown')} unit(s)")
    print("Request parameters:")
    print(json.dumps(request_params, indent=2, ensure_ascii=False))
    print("-" * 80)
    try:
        response = request.execute()
        print_response_summary(response)
        print(json.dumps(response, indent=2, ensure_ascii=False))
        saved_path = save_response(method_name, request_params, response)
        print(f"\nSaved response to: {saved_path}")
    except HttpError as exc:
        print("HTTP error while calling the API.")
        try:
            error_payload = json.loads(exc.content.decode("utf-8"))
            print(json.dumps(error_payload, indent=2, ensure_ascii=False))
        except Exception:
            print(str(exc))
    except Exception as exc:
        print(f"Unexpected error: {exc}")
    print("=" * 80 + "\n")


# ---------- Playground actions ----------

def run_search_list(factory: ServiceFactory) -> None:
    service = factory.public_service()
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
    params = {k: v for k, v in params.items() if v not in (None, "")}

    request = service.search().list(**params)
    execute_request("search.list", params, request)



def run_videos_list(factory: ServiceFactory) -> None:
    service = factory.public_service()
    ids = parse_csv_ids(ask_str("Video ID(s), comma-separated", required=True) or "")
    part = ask_str("part", default="snippet,statistics,contentDetails")
    fields = ask_str("fields (optional)", default=DEFAULT_FIELDS["videos.list"])

    params = {
        "part": part,
        "id": ids,
        "fields": fields,
    }
    params = {k: v for k, v in params.items() if v not in (None, "")}

    request = service.videos().list(**params)
    execute_request("videos.list", params, request)



def run_comment_threads_list(factory: ServiceFactory) -> None:
    service = factory.public_service()
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

    params = {k: v for k, v in params.items() if v not in (None, "")}

    request = service.commentThreads().list(**params)
    execute_request("commentThreads.list", params, request)



def run_comments_list(factory: ServiceFactory) -> None:
    service = factory.public_service()
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

    params = {k: v for k, v in params.items() if v not in (None, "")}

    request = service.comments().list(**params)
    execute_request("comments.list", params, request)



def run_channels_list(factory: ServiceFactory) -> None:
    oauth_ready = bool(factory.config.client_secret_file)
    choices = {
        "1": "id",
        "2": "forHandle",
        "3": "forUsername",
    }
    if oauth_ready:
        choices["4"] = "mine (OAuth 2.0 required)"

    filter_choice = ask_choice(
        "Choose the required filter for channels.list",
        choices,
        default_key="1",
    )

    service = factory.oauth_service() if filter_choice == "4" else factory.public_service()

    params: Dict[str, Any] = {
        "part": ask_str("part", default="snippet,statistics,contentDetails"),
        "fields": ask_str("fields (optional)", default=DEFAULT_FIELDS["channels.list"]),
    }

    if filter_choice == "1":
        params["id"] = parse_csv_ids(ask_str("Channel ID(s), comma-separated", required=True) or "")
    elif filter_choice == "2":
        params["forHandle"] = ask_str("forHandle (with or without @)", required=True)
    elif filter_choice == "3":
        params["forUsername"] = ask_str("forUsername", required=True)
    else:
        params["mine"] = True

    params = {k: v for k, v in params.items() if v not in (None, "")}

    request = service.channels().list(**params)
    execute_request("channels.list", params, request)



def run_playlist_items_list(factory: ServiceFactory) -> None:
    service = factory.public_service()
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

    params = {k: v for k, v in params.items() if v not in (None, "")}

    request = service.playlistItems().list(**params)
    execute_request("playlistItems.list", params, request)



def run_my_uploads(factory: ServiceFactory) -> None:
    service = factory.oauth_service()

    channels_params = {
        "part": "contentDetails,snippet",
        "mine": True,
        "fields": "items(id,snippet/title,contentDetails/relatedPlaylists/uploads)",
    }
    channels_request = service.channels().list(**channels_params)
    print("\nRetrieving the authenticated user's uploads playlist via channels.list(mine=True)...")
    response = channels_request.execute()
    saved_path = save_response("channels.list", channels_params, response)
    print(json.dumps(response, indent=2, ensure_ascii=False))
    print(f"Saved response to: {saved_path}")

    items = response.get("items", [])
    if not items:
        print("No channel found for the authenticated user.")
        return

    uploads_playlist_id = (
        items[0]
        .get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads")
    )
    if not uploads_playlist_id:
        print("Could not find the uploads playlist ID in the channel resource.")
        return

    print(f"\nUploads playlist ID: {uploads_playlist_id}")
    playlist_params = {
        "part": "snippet,contentDetails",
        "playlistId": uploads_playlist_id,
        "maxResults": ask_int("maxResults for uploads playlist", default=10),
        "fields": DEFAULT_FIELDS["playlistItems.list"],
    }
    request = service.playlistItems().list(**playlist_params)
    execute_request("playlistItems.list", playlist_params, request)



def show_help_notes() -> None:
    print(
        """
Notes:
- search.list is expensive compared with the other read methods.
- commentThreads.list requires exactly one filter: videoId, id, or allThreadsRelatedToChannelId.
- comments.list requires exactly one filter: id or parentId.
- Use part to choose top-level sections and fields to reduce nested output.
- For text analysis, plainText is usually easier than html in comment endpoints.
- Every additional page request consumes quota again.
- All responses are saved in ./playground_outputs with UTC timestamps.
""".strip()
    )


MENU = {
    "1": ("search.list", run_search_list),
    "2": ("videos.list", run_videos_list),
    "3": ("commentThreads.list", run_comment_threads_list),
    "4": ("comments.list", run_comments_list),
    "5": ("channels.list", run_channels_list),
    "6": ("playlistItems.list", run_playlist_items_list),
    "7": ("My uploads flow (channels.list -> playlistItems.list via OAuth)", run_my_uploads),
    "8": ("Show notes and parameter tips", lambda factory: show_help_notes()),
    "9": ("Exit", None),
}



def parse_args() -> AppConfig:
    parser = argparse.ArgumentParser(description="YouTube Data API v3 playground")
    parser.add_argument("--api-key", default=os.getenv("YOUTUBE_API_KEY"))
    parser.add_argument(
        "--client-secret",
        default=os.getenv("YOUTUBE_CLIENT_SECRET_FILE"),
        help="Path to OAuth client secret JSON for installed apps",
    )
    parser.add_argument(
        "--token-file",
        default=os.getenv("YOUTUBE_TOKEN_FILE", "token.json"),
        help="Where the OAuth token should be stored",
    )
    args = parser.parse_args()
    return AppConfig(
        api_key=args.api_key,
        client_secret_file=args.client_secret,
        token_file=args.token_file,
    )



def print_banner(config: AppConfig) -> None:
    print("=" * 80)
    print("YouTube Data API v3 Playground")
    print("Official client: google-api-python-client")
    print("Covered methods: search.list, videos.list, commentThreads.list, comments.list,")
    print("                 channels.list, playlistItems.list")
    print("Credentials detected:")
    print(f"- API key: {'yes' if bool(config.api_key) else 'no'}")
    print(f"- OAuth client secret: {'yes' if bool(config.client_secret_file) else 'no'}")
    print("=" * 80)



def main() -> int:
    config = parse_args()
    factory = ServiceFactory(config)
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
            try:
                handler = action[1]
                if handler is not None:
                    handler(factory)
            except RuntimeError as exc:
                print(f"Configuration error: {exc}")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    finally:
        factory.close()


if __name__ == "__main__":
    sys.exit(main())
