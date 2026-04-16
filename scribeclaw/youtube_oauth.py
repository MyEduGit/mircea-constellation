"""youtube_oauth — one-shot CLI to bootstrap OAuth2 credentials.

Runs OUTSIDE the container (or inside with SSH X-forwarding) because it
opens a browser. Produces a token.json that the operator then copies to
/data/youtube/credentials/token.json inside ScribeClaw's data root.

Why this is separate from youtube_upload: the handler refuses to trigger
an interactive browser flow — it must be deterministic and non-blocking.
Token generation happens once per channel, manually, so it stays here.

Usage:

  python -m scribeclaw.youtube_oauth bootstrap \\
      --client-secret /path/to/client_secret.json \\
      --token /path/to/write/token.json

  python -m scribeclaw.youtube_oauth verify \\
      --token /path/to/token.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def _bootstrap(client_secret: Path, token: Path, use_console: bool) -> int:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        print(f"[fail] google-auth-oauthlib missing: {exc}", file=sys.stderr)
        print("       pip install google-auth-oauthlib google-api-python-client",
              file=sys.stderr)
        return 2

    if not client_secret.exists():
        print(f"[fail] client secret not found: {client_secret}", file=sys.stderr)
        return 2

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secret), _SCOPES,
    )
    if use_console:
        # Headless flow: prints URL, reads pasted-back code.
        creds = flow.run_console()
    else:
        # Local loopback flow: opens the browser, captures the redirect.
        creds = flow.run_local_server(port=0)

    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(creds.to_json(), encoding="utf-8")
    token.chmod(0o600)
    print(f"[ok] token written to {token}")
    print(f"[next] copy to /data/youtube/credentials/token.json inside the container")
    return 0


def _verify(token: Path) -> int:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        print(f"[fail] google-auth missing: {exc}", file=sys.stderr)
        return 2
    if not token.exists():
        print(f"[fail] token not found: {token}", file=sys.stderr)
        return 2
    creds = Credentials.from_authorized_user_file(str(token), _SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token.write_text(creds.to_json(), encoding="utf-8")
            print("[ok] token refreshed")
        else:
            print("[fail] token invalid and no refresh_token; re-bootstrap",
                  file=sys.stderr)
            return 1
    print(json.dumps({
        "valid": creds.valid,
        "expired": creds.expired,
        "has_refresh_token": bool(creds.refresh_token),
        "scopes": list(creds.scopes or []),
    }, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scribeclaw.youtube_oauth")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_bootstrap = sub.add_parser("bootstrap", help="generate token.json")
    p_bootstrap.add_argument("--client-secret", required=True, type=Path)
    p_bootstrap.add_argument("--token", required=True, type=Path)
    p_bootstrap.add_argument("--headless", action="store_true",
                             help="use paste-back console flow (no browser)")

    p_verify = sub.add_parser("verify", help="verify an existing token.json")
    p_verify.add_argument("--token", required=True, type=Path)

    args = parser.parse_args(argv)
    if args.cmd == "bootstrap":
        return _bootstrap(args.client_secret, args.token, args.headless)
    if args.cmd == "verify":
        return _verify(args.token)
    return 2


if __name__ == "__main__":
    sys.exit(main())
