"""session_status — operator-readiness report.

Reads the data tree + probes runtime and produces both a JSON summary
and a human-readable markdown checklist so the operator knows, at a
glance:

  1. What's installed / configured / missing (runtime probe).
  2. Which transcripts have been processed and how far through the
     pipeline each one is.
  3. What the operator's next three actions should be.

Writes:
  /data/status/session.md    — operator-facing checklist
  /data/status/session.json  — machine-readable snapshot

Deterministic; no external deps. Safe to call from the dashboard poll
every 30 seconds.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_PIPELINE_STAGES = (
    ("segments",  "transcripts/{stem}/segments.json"),
    ("cleaned",   "transcripts/{stem}/segments.clean.json"),
    ("cues",      "transcripts/{stem}/cues.json"),
    ("bundle",    "youtube/{stem}/bundle.json"),
    ("thumbnail", "youtube/{stem}/thumbnail.jpg"),
    ("uploaded",  "youtube/{stem}/upload.result.json"),
)


def _stems_from_tree(data_root: Path) -> list[str]:
    td = data_root / "transcripts"
    if not td.is_dir():
        return []
    return sorted(p.name for p in td.iterdir() if p.is_dir())


def _stage_presence(data_root: Path, stem: str) -> dict[str, bool]:
    return {
        name: (data_root / rel.format(stem=stem)).exists()
        for name, rel in _PIPELINE_STAGES
    }


def _last_evidence_epoch(data_root: Path) -> float | None:
    ed = data_root / "evidence"
    if not ed.is_dir():
        return None
    epochs: list[float] = []
    for f in ed.glob("evidence_*.json"):
        try:
            epochs.append(f.stat().st_mtime)
        except OSError:
            continue
    return max(epochs) if epochs else None


def _readiness_checklist(probe: dict, data_root: Path) -> list[dict]:
    """Translate the runtime probe + filesystem state into actionable items."""
    creds_dir = data_root / "youtube" / "credentials"
    checks = [
        {"id": "ffmpeg",           "ok": bool(probe.get("ffmpeg_on_path")),
         "label": "ffmpeg on PATH",
         "fix": "install ffmpeg in the container image"},
        {"id": "faster_whisper",   "ok": bool(probe.get("faster_whisper_installed")),
         "label": "faster-whisper installed",
         "fix": "pip install faster-whisper (required for transcribe_ro)"},
        {"id": "httpx",            "ok": bool(probe.get("httpx_installed")),
         "label": "httpx installed",
         "fix": "pip install httpx (required for AssemblyAI handlers)"},
        {"id": "assemblyai_key",   "ok": bool(probe.get("assemblyai_key_set")),
         "label": "ASSEMBLYAI_API_KEY set",
         "fix": "set ASSEMBLYAI_API_KEY in scribeclaw/.env and restart"},
        {"id": "yt_client_secret", "ok": (creds_dir / "client_secret.json").exists(),
         "label": "YouTube OAuth client_secret.json present",
         "fix": "drop client_secret.json under /data/youtube/credentials/"},
        {"id": "yt_token",         "ok": (creds_dir / "token.json").exists(),
         "label": "YouTube OAuth token.json present",
         "fix": "run `python -m scribeclaw.youtube_oauth bootstrap` on a "
                "machine with a browser, then copy token.json to "
                "/data/youtube/credentials/"},
    ]
    return checks


_MAX_ENV_ACTIONS = 6
_MAX_STEM_ACTIONS = 6


def _next_three_actions(checklist: list[dict],
                        stems: list[dict]) -> list[str]:
    """Produce a ranked todo list for the operator. Deterministic order.

    Two budgets (env + stem) so a fresh-install operator still sees the
    first pipeline nudges alongside the runtime-missing items."""
    env_actions: list[str] = []
    for c in checklist:
        if not c["ok"]:
            env_actions.append(f"{c['label']} — {c['fix']}")
    env_actions = env_actions[:_MAX_ENV_ACTIONS]

    stem_actions: list[str] = []
    for s in stems:
        stages = s["stages"]
        missing = [name for name in ("segments", "cleaned", "cues",
                                     "bundle", "thumbnail", "uploaded")
                   if not stages.get(name)]
        if not missing:
            continue
        stem_actions.append(
            f"{s['stem']} — advance to stage '{missing[0]}' "
            f"(done: {', '.join(k for k, v in stages.items() if v) or 'none'})"
        )
        if len(stem_actions) >= _MAX_STEM_ACTIONS:
            break
    return env_actions + stem_actions


def _render_markdown(claw: str, ts_iso: str, checklist: list[dict],
                     stems: list[dict], actions: list[str]) -> str:
    lines: list[str] = []
    lines.append(f"# {claw} — Session Status\n")
    lines.append(f"_Snapshot at {ts_iso}_\n")
    lines.append("## Operator readiness\n")
    lines.append("| Check | Status | Fix |")
    lines.append("|---|:---:|---|")
    for c in checklist:
        mark = "✅" if c["ok"] else "❌"
        lines.append(f"| {c['label']} | {mark} | "
                     f"{'—' if c['ok'] else c['fix']} |")

    lines.append("\n## Pipeline progress\n")
    if not stems:
        lines.append("_No transcripts under `/data/transcripts/` yet._")
    else:
        lines.append("| Stem | seg | clean | cues | bundle | thumb | upload |")
        lines.append("|---|:---:|:---:|:---:|:---:|:---:|:---:|")
        for s in stems:
            st = s["stages"]
            def mk(k):
                return "✅" if st.get(k) else "·"
            lines.append(
                f"| `{s['stem']}` | {mk('segments')} | {mk('cleaned')} | "
                f"{mk('cues')} | {mk('bundle')} | {mk('thumbnail')} | "
                f"{mk('uploaded')} |"
            )

    lines.append("\n## Next actions\n")
    if not actions:
        lines.append("_Nothing outstanding — pipeline is clean._")
    else:
        for i, a in enumerate(actions, start=1):
            lines.append(f"{i}. {a}")

    lines.append("")
    return "\n".join(lines) + "\n"


async def session_status(payload: dict[str, Any], data_root: Path) -> dict:
    """Produce an operator-readiness snapshot."""
    # Lazy import — main.py imports session_status, so importing main
    # at module load time would be circular.
    from .main import CLAW_NAME, _probe_runtime

    probe = _probe_runtime()

    stem_names = _stems_from_tree(data_root)
    stems: list[dict] = []
    for stem in stem_names:
        stages = _stage_presence(data_root, stem)
        stems.append({
            "stem": stem,
            "stages": stages,
            "advanced_stage": next(
                (name for name, _ in reversed(_PIPELINE_STAGES) if stages[name]),
                None,
            ),
        })

    checklist = _readiness_checklist(probe, data_root)
    actions = _next_three_actions(checklist, stems)
    ts_iso = time.strftime("%Y-%m-%dT%H:%M:%S%z") or "unknown"

    out_dir = data_root / "status"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "session.json"
    md_path = out_dir / "session.md"

    snapshot = {
        "claw": CLAW_NAME,
        "ts_iso": ts_iso,
        "ts_epoch": time.time(),
        "probe": probe,
        "checklist": checklist,
        "stems": stems,
        "stems_total": len(stems),
        "stems_uploaded": sum(1 for s in stems if s["stages"]["uploaded"]),
        "next_actions": actions,
        "last_evidence_epoch": _last_evidence_epoch(data_root),
    }
    json_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    md_path.write_text(
        _render_markdown(CLAW_NAME, ts_iso, checklist, stems, actions),
        encoding="utf-8",
    )

    return {
        "status": "success",
        "handler": "session_status",
        "ts_iso": ts_iso,
        "stems_total": len(stems),
        "stems_uploaded": snapshot["stems_uploaded"],
        "outstanding_checklist_items": sum(1 for c in checklist if not c["ok"]),
        "next_actions": actions,
        "outputs": [str(md_path), str(json_path)],
    }
