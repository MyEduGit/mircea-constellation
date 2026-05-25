"""Refusal-path tests for scribeclaw.youtube_upload.

The upload handler must return structured refusals (never crash) when
prerequisites are missing, so the operator gets a clear diagnosis.

Run from the repo root:
  python -m scribeclaw.tests.test_upload_refusals
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scribeclaw.youtube import youtube_upload  # noqa: E402


def _seed_bundle(data_root: Path, stem: str) -> None:
    d = data_root / "youtube" / stem
    d.mkdir(parents=True, exist_ok=True)
    (d / "bundle.json").write_text(json.dumps({
        "title_candidates": ["Religia lui Isus"],
        "description": "test",
        "tags": ["jabbokriver"],
        "language": "ro",
    }), encoding="utf-8")


def _seed_video(data_root: Path, stem: str) -> Path:
    d = data_root / "media" / "edited"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{stem}.mp4"
    p.write_bytes(b"\x00" * 16)  # dummy bytes; upload handler never reads in dry_run
    return p


def test_missing_stem(data_root: Path) -> None:
    r = asyncio.run(youtube_upload({}, data_root))
    assert r["status"] == "error" and r["error"] == "stem_required", r
    print("OK  missing_stem")


def test_missing_bundle(data_root: Path) -> None:
    r = asyncio.run(youtube_upload({"stem": "nope"}, data_root))
    assert r["status"] == "error" and r["error"] == "bundle_not_found", r
    print("OK  missing_bundle")


def test_missing_video(data_root: Path) -> None:
    _seed_bundle(data_root, "bundle-only")
    r = asyncio.run(youtube_upload({"stem": "bundle-only"}, data_root))
    assert r["status"] == "error" and r["error"] == "video_not_found", r
    print("OK  missing_video")


def test_missing_client_secret(data_root: Path) -> None:
    _seed_bundle(data_root, "no-creds")
    _seed_video(data_root, "no-creds")
    r = asyncio.run(youtube_upload({"stem": "no-creds"}, data_root))
    assert r["status"] == "not_ready" and r["missing"] == "client_secret.json", r
    print("OK  missing_client_secret")


def test_invalid_privacy(data_root: Path, creds_dir: Path) -> None:
    _seed_bundle(data_root, "bad-privacy")
    _seed_video(data_root, "bad-privacy")
    # Seed fake creds so we get past the client_secret gate; we expect the
    # privacy validation to trip before any network call.
    (creds_dir / "client_secret.json").write_text(json.dumps({
        "installed": {"client_id": "x", "client_secret": "y"}
    }), encoding="utf-8")
    (creds_dir / "refresh_token.json").write_text(json.dumps({"refresh_token": "r"}),
                                                  encoding="utf-8")
    r = asyncio.run(youtube_upload(
        {"stem": "bad-privacy", "privacy": "launch-it-everywhere",
         "credentials_dir": str(creds_dir), "dry_run": True},
        data_root,
    ))
    assert r["status"] == "error" and r["error"] == "invalid_privacy", r
    print("OK  invalid_privacy")


def test_dry_run_happy_path(data_root: Path, creds_dir: Path) -> None:
    _seed_bundle(data_root, "dry")
    _seed_video(data_root, "dry")
    (creds_dir / "client_secret.json").write_text(json.dumps({
        "installed": {"client_id": "x", "client_secret": "y"}
    }), encoding="utf-8")
    (creds_dir / "refresh_token.json").write_text(json.dumps({"refresh_token": "r"}),
                                                  encoding="utf-8")
    r = asyncio.run(youtube_upload(
        {"stem": "dry", "credentials_dir": str(creds_dir), "dry_run": True},
        data_root,
    ))
    assert r["status"] == "success" and r.get("mode") == "dry_run", r
    assert r["would_upload"]["privacy"] == "private"
    assert r["would_upload"]["title"] == "Religia lui Isus"
    print("OK  dry_run_happy_path")


def main() -> int:
    with tempfile.TemporaryDirectory() as data_dir, tempfile.TemporaryDirectory() as creds:
        data_root = Path(data_dir)
        creds_dir = Path(creds)
        test_missing_stem(data_root)
        test_missing_bundle(data_root)
        test_missing_video(data_root)
        test_missing_client_secret(data_root)
        test_invalid_privacy(data_root, creds_dir)
        test_dry_run_happy_path(data_root, creds_dir)
    print("\nAll upload-refusal tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
