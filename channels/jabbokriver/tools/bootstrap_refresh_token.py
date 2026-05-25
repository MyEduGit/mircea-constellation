#!/usr/bin/env python3
"""One-time OAuth flow to mint a YouTube upload refresh token.

Run this ONCE on the operator machine (requires a browser).
It reads client_secret.json and saves refresh_token.json into the
same credentials directory.

Prerequisites:
  1. Download client_secret.json from Google Cloud Console:
       console.cloud.google.com → your project → APIs & Services
       → Credentials → OAuth 2.0 Client IDs → Download JSON
       → save to /opt/scribeclaw-data/youtube/credentials/client_secret.json
       → chmod 600 that file

  2. Install the Google libraries (one-time):
       pip install google-api-python-client google-auth google-auth-oauthlib

  3. Run this script:
       python channels/jabbokriver/tools/bootstrap_refresh_token.py

  4. A browser window opens. Log in as jabbokriverproductions@gmail.com
     and click Allow.

  5. refresh_token.json is written to the credentials directory.
     The youtube_upload handler will find it automatically from now on.

You never need to run this again unless you revoke the token or
switch Google accounts.
"""
import json
import os
import pathlib
import sys

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

DEFAULT_CREDS_DIR = pathlib.Path(
    os.environ.get(
        "YOUTUBE_CREDENTIALS_DIR",
        "/opt/scribeclaw-data/youtube/credentials",
    )
)


def main() -> None:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print(
            "ERROR: google-auth-oauthlib not installed.\n"
            "Run: pip install google-api-python-client google-auth google-auth-oauthlib"
        )
        sys.exit(1)

    creds_dir = DEFAULT_CREDS_DIR
    client_secret = creds_dir / "client_secret.json"

    if not client_secret.exists():
        print(
            f"ERROR: client_secret.json not found at:\n  {client_secret}\n\n"
            "Steps:\n"
            "  1. Go to console.cloud.google.com\n"
            "  2. Select your project (or create one named 'jabbokriver-upload')\n"
            "  3. APIs & Services → Enable APIs → search 'YouTube Data API v3' → Enable\n"
            "  4. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID\n"
            "  5. Application type: Desktop app → Create\n"
            "  6. Download JSON → save it here:\n"
            f"     {client_secret}\n"
            "  7. chmod 600 that file\n"
            "  8. Re-run this script."
        )
        sys.exit(1)

    print(f"Found client_secret.json at: {client_secret}")
    print("Opening browser for Google sign-in...")
    print("Sign in as: jabbokriverproductions@gmail.com")
    print("(Your personal JabbokRiver Productions channel)\n")

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
    creds = flow.run_local_server(port=0)

    if not creds.refresh_token:
        print(
            "ERROR: No refresh_token received. This can happen if the account\n"
            "already authorized this app. Go to myaccount.google.com/permissions,\n"
            "revoke access for your app, then re-run this script."
        )
        sys.exit(1)

    refresh_token_file = creds_dir / "refresh_token.json"
    refresh_token_file.write_text(
        json.dumps({"refresh_token": creds.refresh_token}, indent=2),
        encoding="utf-8",
    )
    refresh_token_file.chmod(0o600)

    print(f"\nDone. refresh_token.json saved to:\n  {refresh_token_file}")
    print("\nYou can now use youtube_upload. Dry-run test:")
    print(
        '  curl -X POST http://127.0.0.1:8081/tasks \\\n'
        '    -H \'content-type: application/json\' \\\n'
        '    -d \'{"handler":"youtube_upload","payload":{"stem":"<id>.edited","dry_run":true,"privacy":"unlisted"}}\''
    )


if __name__ == "__main__":
    main()
