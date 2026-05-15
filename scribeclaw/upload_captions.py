#!/usr/bin/env python3
"""upload_captions.py — Upload a corrected SRT as Romanian captions to YouTube.

Usage (on Mac, one-time setup):
    pip install google-auth-oauthlib google-api-python-client
    python3 upload_captions.py GFttc7f5zEo GFttc7f5zEo_RO_corrected.srt

First run opens a browser for Google sign-in (messagetostephanos@gmail.com).
Credentials are saved to ~/.jrp_youtube_token.json for all future runs.

Requirements:
  - client_secrets.json in the same directory (download from Google Cloud Console)
    OR set env var YOUTUBE_CLIENT_SECRETS=/path/to/client_secrets.json
  - The account must have edit access to the video (messagetostephanos@gmail.com)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
TOKEN_PATH = Path.home() / ".jrp_youtube_token.json"
API_SERVICE = "youtube"
API_VERSION = "v3"


def get_authenticated_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None

    # Load existing token
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    # Refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[Auth] Refreshing existing credentials...")
            creds.refresh(Request())
        else:
            secrets_path = os.environ.get("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
            if not Path(secrets_path).exists():
                print(f"\n❌ client_secrets.json not found at: {secrets_path}")
                print("\nTo get it:")
                print("  1. Go to https://console.cloud.google.com/")
                print("  2. Create/select a project → APIs & Services → Credentials")
                print("  3. Create OAuth 2.0 Client ID (Desktop app)")
                print("  4. Download JSON → save as client_secrets.json next to this script")
                print("  OR: set YOUTUBE_CLIENT_SECRETS=/path/to/file.json")
                sys.exit(1)

            print(f"[Auth] Opening browser for Google sign-in...")
            print(f"       Sign in as: messagetostephanos@gmail.com")
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for next run
        TOKEN_PATH.write_text(creds.to_json())
        print(f"[Auth] Credentials saved to {TOKEN_PATH}")

    return build(API_SERVICE, API_VERSION, credentials=creds)


def get_existing_caption_id(youtube, video_id: str, language: str = "ro") -> str | None:
    """Return existing caption track ID for the language, or None."""
    response = youtube.captions().list(part="snippet", videoId=video_id).execute()
    for item in response.get("items", []):
        if item["snippet"]["language"] == language:
            return item["id"]
    return None


def upload_captions(video_id: str, srt_path: Path, language: str = "ro", name: str = "Română"):
    print(f"\n{'='*60}")
    print(f"  JRP Caption Upload")
    print(f"  Video:    {video_id}")
    print(f"  SRT file: {srt_path}")
    print(f"  Language: {language} ({name})")
    print(f"{'='*60}\n")

    if not srt_path.exists():
        print(f"❌ SRT file not found: {srt_path}")
        sys.exit(1)

    youtube = get_authenticated_service()

    # Check for existing Romanian caption track
    existing_id = get_existing_caption_id(youtube, video_id, language)

    if existing_id:
        print(f"[YouTube] Existing '{language}' caption track found (id={existing_id})")
        print(f"[YouTube] Updating (replacing) existing track...")
        response = youtube.captions().update(
            part="snippet",
            body={
                "id": existing_id,
                "snippet": {
                    "language": language,
                    "name": name,
                    "isDraft": False,
                }
            },
            media_body=srt_path,
        ).execute()
        print(f"[YouTube] ✅ Updated caption track: {response['id']}")
    else:
        print(f"[YouTube] No existing '{language}' track — inserting new track...")
        response = youtube.captions().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "language": language,
                    "name": name,
                    "isDraft": False,
                }
            },
            media_body=srt_path,
        ).execute()
        print(f"[YouTube] ✅ Inserted caption track: {response['id']}")

    print(f"\n✅ Done! Romanian captions are now live.")
    print(f"   View: https://studio.youtube.com/video/{video_id}/translations")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Upload SRT captions to YouTube")
    parser.add_argument("video_id", help="YouTube video ID (e.g. GFttc7f5zEo)")
    parser.add_argument("srt_file", nargs="?", help="Path to corrected SRT file")
    parser.add_argument("--lang", default="ro", help="Language code (default: ro)")
    parser.add_argument("--name", default="Română", help="Caption track name")
    args = parser.parse_args()

    srt_path = Path(args.srt_file) if args.srt_file else Path(f"{args.video_id}_RO_corrected.srt")
    upload_captions(args.video_id, srt_path, args.lang, args.name)


if __name__ == "__main__":
    main()
