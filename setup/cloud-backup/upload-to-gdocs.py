#!/usr/bin/env python3
"""
upload-to-gdocs.py — Upload Obsidian job.md files as Google Docs.

Each job.md in ~/Documents/Obsidian/Jobs/<YYYY-MM-DD>/<slug>/ is created (or
updated) as a Google Doc inside a Drive folder, preserving the date/slug path.

Auth: service account JSON (GDRIVE_SA_FILE) or Application Default Credentials.
Config: reads ~/.cloud-backup/.env for GDRIVE_SA_FILE and GDOCS_JOBS_FOLDER_ID.
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

try:
    from google.oauth2 import service_account
    from google.auth import default as google_auth_default
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# ── Config ────────────────────────────────────────────────────────────────────
CRED_FILE   = Path.home() / ".cloud-backup" / ".env"
SEEN_FILE   = Path.home() / ".cloud-backup" / "gdocs-uploaded.json"
SCOPES      = ["https://www.googleapis.com/auth/drive"]

def load_env() -> dict:
    env = {}
    if not CRED_FILE.exists():
        return env
    for line in CRED_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().replace("${HOME}", str(Path.home())).replace("~", str(Path.home()))
    return env

def load_seen() -> dict:
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return {}

def save_seen(seen: dict):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(seen, indent=2))

def file_hash(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]

def build_drive_service(sa_file: str):
    """Build Google Drive API service using service account or ADC."""
    if sa_file and Path(sa_file).exists():
        creds = service_account.Credentials.from_service_account_file(
            sa_file, scopes=SCOPES
        )
    else:
        creds, _ = google_auth_default(scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def get_or_create_folder(drive, name: str, parent_id: str | None) -> str:
    """Return the Drive folder ID for `name` under `parent_id`, creating if absent."""
    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
        + (f" and '{parent_id}' in parents" if parent_id else "")
        + " and trashed=false"
    )
    res = drive.files().list(q=query, fields="files(id,name)", pageSize=1).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]
    folder = drive.files().create(body=metadata, fields="id").execute()
    return folder["id"]

def upload_as_gdoc(drive, md_path: Path, folder_id: str, title: str) -> tuple[str, str]:
    """Upload a markdown file as a Google Doc. Returns (file_id, webViewLink)."""
    media = MediaFileUpload(str(md_path), mimetype="text/plain", resumable=False)
    metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document",
        "parents": [folder_id],
    }
    result = drive.files().create(
        body=metadata,
        media_body=media,
        fields="id,webViewLink"
    ).execute()
    return result.get("id", ""), result.get("webViewLink", "")

def update_gdoc(drive, file_id: str, md_path: Path) -> str:
    """Replace content of an existing Google Doc."""
    media = MediaFileUpload(str(md_path), mimetype="text/plain", resumable=False)
    result = drive.files().update(
        fileId=file_id,
        media_body=media,
        fields="id,webViewLink"
    ).execute()
    return result.get("webViewLink", "")

def make_public(drive, file_id: str):
    """Grant anyone-with-link reader access so the doc is accessible without login."""
    try:
        drive.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
    except Exception:
        pass  # non-fatal: best-effort public sharing

def find_existing(drive, title: str, folder_id: str) -> str | None:
    """Return file ID of existing Google Doc with this title in folder, or None."""
    query = (
        f"name='{title}' and mimeType='application/vnd.google-apps.document'"
        f" and '{folder_id}' in parents and trashed=false"
    )
    res = drive.files().list(q=query, fields="files(id)", pageSize=1).execute()
    files = res.get("files", [])
    return files[0]["id"] if files else None

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not GOOGLE_AVAILABLE:
        print("[gdocs] google-api-python-client not installed — run: setup/cloud-backup/install.sh")
        sys.exit(1)

    env = load_env()
    sa_file    = env.get("GDRIVE_SA_FILE", "")
    root_folder = env.get("GDOCS_JOBS_FOLDER_ID", "")
    vault      = Path(env.get("OBSIDIAN_JOBS_VAULT", str(Path.home() / "Documents" / "Obsidian" / "Jobs")))
    anthr_vault = Path(env.get("OBSIDIAN_ANTHROPIC_VAULT", str(Path.home() / "Documents" / "Obsidian" / "Anthropic-Data")))

    if not vault.exists() and not anthr_vault.exists():
        print("[gdocs] No Obsidian vaults found — nothing to upload")
        return

    try:
        drive = build_drive_service(sa_file)
    except Exception as exc:
        print(f"[gdocs] Auth failed: {exc}")
        print("[gdocs] Set up credentials in ~/.cloud-backup/.env (GDRIVE_SA_FILE)")
        sys.exit(1)

    seen    = load_seen()
    uploaded = 0
    updated  = 0

    # Jobs vault: date/slug/job.md → GDrive: Jobs/<date>/<slug> as Google Doc
    for job_md in sorted(vault.rglob("job.md")):
        fhash   = file_hash(job_md)
        seen_key = str(job_md)

        if seen.get(seen_key) == fhash:
            continue

        # Build folder structure: Jobs / YYYY-MM-DD / job-slug
        parts    = job_md.parts
        try:
            jobs_idx  = next(i for i, p in enumerate(parts) if p == "Jobs")
            date_part = parts[jobs_idx + 1]  # YYYY-MM-DD
            slug_part = parts[jobs_idx + 2]  # job-slug
        except (StopIteration, IndexError):
            date_part = "misc"
            slug_part = job_md.parent.name

        jobs_root_id  = get_or_create_folder(drive, "ObsidianJobs", root_folder or None)
        date_folder_id = get_or_create_folder(drive, date_part, jobs_root_id)

        title   = f"Job: {slug_part} — {date_part}"
        existing = find_existing(drive, title, date_folder_id)

        if existing:
            url = update_gdoc(drive, existing, job_md)
            make_public(drive, existing)
            print(f"[gdocs] updated {title}")
            updated += 1
        else:
            file_id, url = upload_as_gdoc(drive, job_md, date_folder_id, title)
            if file_id:
                make_public(drive, file_id)
            print(f"[gdocs] created {title} → {url}")
            uploaded += 1

        seen[seen_key] = fhash

    # Anthropic-Data vault: all .md files → GDrive: AnthropicData/<path>
    for md_path in sorted(anthr_vault.rglob("*.md")):
        fhash    = file_hash(md_path)
        seen_key = str(md_path)
        if seen.get(seen_key) == fhash:
            continue

        rel       = md_path.relative_to(anthr_vault)
        # Build matching folder chain
        folder_id = get_or_create_folder(drive, "AnthropicData", root_folder or None)
        for part in rel.parts[:-1]:
            folder_id = get_or_create_folder(drive, part, folder_id)

        title    = md_path.stem
        existing = find_existing(drive, title, folder_id)
        if existing:
            update_gdoc(drive, existing, md_path)
            make_public(drive, existing)
            print(f"[gdocs] updated AnthropicData/{rel}")
            updated += 1
        else:
            file_id, url = upload_as_gdoc(drive, md_path, folder_id, title)
            if file_id:
                make_public(drive, file_id)
            print(f"[gdocs] created AnthropicData/{rel} → {url}")
            uploaded += 1
        seen[seen_key] = fhash

    save_seen(seen)
    print(f"[gdocs] Done. {uploaded} created, {updated} updated.")

if __name__ == "__main__":
    main()
