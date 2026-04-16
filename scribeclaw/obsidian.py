"""export_obsidian — write a transcript as a markdown note into a vault.

Closes the loop on the operator's existing Obsidian pipeline: once a
transcript lives under /data/transcripts/<stem>/ (via transcribe_ro,
transcribe_assemblyai, or bulk_import_assemblyai_romanian), this handler
renders it as a single markdown file with YAML front-matter and drops it
into the operator-supplied vault.

Operator contract:
  - vault_path is resolved from the payload or the OBSIDIAN_VAULT env
    var. If neither is set the handler refuses (status=error) rather
    than silently defaulting to /data.
  - The vault must be bind-mounted into the container at the configured
    path. The handler does not read the operator's host fs directly.
  - If a bundle (from youtube_metadata) exists at
    /data/youtube/<stem>/bundle.json, chapters and title candidates are
    embedded in the note.

Idempotent: overwrites the target note on every run (sources of truth
remain under /data/transcripts and /data/youtube).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._\- ]+")


def _yaml_escape(value: Any) -> str:
    """Minimal YAML string escaper for front-matter values.

    We intentionally avoid importing PyYAML — front-matter is simple
    enough that one deterministic function is cheaper than a dep.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_yaml_escape(v) for v in value) + "]"
    s = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def _safe_filename(name: str, fallback: str) -> str:
    cleaned = _SAFE_FILENAME.sub(" ", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:120] or fallback


def _format_hhmmss(sec: float) -> str:
    s = int(sec)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def _render_note(stem: str, seg_data: dict, bundle: dict | None,
                 title: str, tags: list[str]) -> str:
    segments = seg_data.get("segments", [])
    duration = float(seg_data.get("duration") or 0.0)
    language = seg_data.get("language", "ro")
    aai_id = seg_data.get("assemblyai_id")
    model = seg_data.get("model", "")

    lines: list[str] = ["---"]
    lines.append(f"title: {_yaml_escape(title)}")
    lines.append(f"stem: {_yaml_escape(stem)}")
    lines.append(f"language: {_yaml_escape(language)}")
    lines.append(f"duration_sec: {_yaml_escape(duration)}")
    lines.append(f"model: {_yaml_escape(model)}")
    if aai_id:
        lines.append(f"assemblyai_id: {_yaml_escape(aai_id)}")
    if tags:
        lines.append(f"tags: {_yaml_escape(tags)}")
    lines.append(f"source: {_yaml_escape('scribeclaw')}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")

    if bundle:
        tc = bundle.get("title_candidates") or []
        if tc:
            lines.append("## Title candidates")
            for cand in tc:
                lines.append(f"- {cand}")
            lines.append("")
        chapters = bundle.get("chapters") or []
        if chapters:
            lines.append("## Chapters")
            for ch in chapters:
                ts = ch.get("timestamp") or _format_hhmmss(
                    float(ch.get("start_seconds", 0.0))
                )
                lines.append(f"- `{ts}` {ch.get('title', '')}")
            lines.append("")

    lines.append("## Transcript")
    lines.append("")
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        ts = _format_hhmmss(float(seg.get("start", 0.0)))
        lines.append(f"**[{ts}]** {text}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


async def export_obsidian(payload: dict[str, Any], data_root: Path) -> dict:
    """Render /data/transcripts/<stem>/ as a markdown note inside a vault.

    Payload:
      stem       (str, required): transcript directory under /data/transcripts/
      vault_path (str, optional): vault root; falls back to OBSIDIAN_VAULT env
      subdir     (str, optional): within-vault subdirectory; default "Transcripts"
      title      (str, optional): note title; default = first bundle title or stem
      filename   (str, optional): output filename without extension
    """
    stem = Path(payload["stem"]).name
    transcripts_dir = data_root / "transcripts" / stem
    # Prefer the cleaned segments if postprocess_transcript ran; fall back.
    seg_file = transcripts_dir / "segments.clean.json"
    if not seg_file.exists():
        seg_file = transcripts_dir / "segments.json"
    if not seg_file.exists():
        return {"status": "error", "handler": "export_obsidian",
                "error": "segments_not_found", "expected_at": str(seg_file),
                "hint": "run a transcribe_* handler first"}

    vault_arg = payload.get("vault_path") or os.getenv("OBSIDIAN_VAULT", "")
    vault_path = Path(vault_arg).expanduser() if vault_arg else None
    if not vault_path:
        return {"status": "error", "handler": "export_obsidian",
                "error": "vault_path_missing",
                "hint": "pass payload.vault_path or set OBSIDIAN_VAULT env "
                        "and bind-mount the vault into the container"}
    if not vault_path.exists() or not vault_path.is_dir():
        return {"status": "error", "handler": "export_obsidian",
                "error": "vault_path_not_a_directory",
                "vault_path": str(vault_path),
                "hint": "ensure the vault is bind-mounted and the path is correct"}

    subdir = str(payload.get("subdir", "Transcripts")).strip().strip("/")
    out_dir = vault_path / subdir if subdir else vault_path
    out_dir.mkdir(parents=True, exist_ok=True)

    seg_data = json.loads(seg_file.read_text(encoding="utf-8"))
    bundle_file = data_root / "youtube" / stem / "bundle.json"
    bundle = None
    if bundle_file.exists():
        bundle = json.loads(bundle_file.read_text(encoding="utf-8"))

    default_title = None
    if bundle and bundle.get("title_candidates"):
        default_title = bundle["title_candidates"][0]
    title = str(payload.get("title") or default_title or stem)
    tags = (bundle or {}).get("tags") or []

    filename_stem = _safe_filename(
        str(payload.get("filename") or title), fallback=stem,
    )
    out_path = out_dir / f"{filename_stem}.md"

    body = _render_note(stem, seg_data, bundle, title, tags)
    out_path.write_text(body, encoding="utf-8")

    return {
        "status": "success",
        "handler": "export_obsidian",
        "stem": stem,
        "vault_path": str(vault_path),
        "output": str(out_path),
        "bytes": len(body.encode("utf-8")),
        "used_bundle": bundle is not None,
        "title": title,
    }
