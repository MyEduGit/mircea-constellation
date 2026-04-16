#!/usr/bin/env python3
"""CinemaClaw — YouTube-video editing pipeline.

UrantiOS governed: Truth, Beauty, Goodness.

Usage:
    # List pipelines declared in the bundled (or a custom) pipeline.yaml
    python3 -m cinemaclaw.cinemaclaw --list

    # Dry-run a pipeline end-to-end (safe: touches nothing)
    python3 -m cinemaclaw.cinemaclaw --run demo --dry-run

    # Execute a pipeline (renders; still refuses to publish)
    python3 -m cinemaclaw.cinemaclaw --run demo --execute

    # Attempt publish (will still refuse in v0.1.0 — publish is DRY-ONLY)
    python3 -m cinemaclaw.cinemaclaw --run demo --execute --signed-by-father

Exit codes:
    0 — every stage ok (or dry-run with no structural errors)
    1 — at least one stage refused or failed
    2 — config / IO error (pipeline.yaml unreadable, unknown pipeline id)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # PyYAML
except ImportError:
    sys.stderr.write(
        "cinemaclaw: PyYAML not installed. Run setup/cinemaclaw_install.sh "
        "or `pip install pyyaml`.\n"
    )
    sys.exit(2)

from . import __version__, handlers

# ── Paths ──────────────────────────────────────────────────────────────
DEFAULT_PIPELINE = Path(__file__).parent / "pipeline.yaml"
STATE_DIR = Path(os.path.expanduser("~/.cinemaclaw"))
RENDERS_LOG = STATE_DIR / "renders.jsonl"
AUDIT_LOG = STATE_DIR / "audit.jsonl"


# ── append-only evidence ──────────────────────────────────────────────
def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def audit(event: str, **fields: Any) -> None:
    """One line per CLI invocation or stage dispatch."""
    _append_jsonl(AUDIT_LOG, {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "event": event,
        "cinemaclaw_version": __version__,
        "operator": os.environ.get("USER") or os.environ.get("LOGNAME") or "unknown",
        **fields,
    })


# ── Lucifer Test ──────────────────────────────────────────────────────
def lucifer_test(stage: dict[str, Any]) -> tuple[bool, str]:
    """Per-stage pre-flight. Refusal is honest: recorded + surfaced."""
    kind = stage.get("kind")
    if not kind:
        return False, "stage missing 'kind' (mandate violation)"
    if kind not in handlers.HANDLERS:
        return False, f"kind not in allowlist: {kind!r}"
    if not isinstance(stage.get("with", {}), dict):
        return False, "'with' must be a mapping"
    return True, "passed"


# ── substitution ──────────────────────────────────────────────────────
def _interpolate(value: Any, ctx: dict[str, Any]) -> Any:
    """${key} substitution from pipeline vars + prior stage outputs.

    Keeps substitution small and predictable: a single pass, no nesting,
    raises KeyError on missing keys so pipelines fail loudly.
    """
    if isinstance(value, str) and "${" in value:
        out = value
        for k, v in ctx.items():
            out = out.replace("${" + k + "}", str(v))
        if "${" in out:
            missing = out[out.find("${"):out.find("}", out.find("${")) + 1]
            raise KeyError(f"unresolved variable: {missing}")
        return out
    if isinstance(value, list):
        return [_interpolate(v, ctx) for v in value]
    if isinstance(value, dict):
        return {k: _interpolate(v, ctx) for k, v in value.items()}
    return value


# ── pipeline loader ───────────────────────────────────────────────────
def load_pipelines(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"pipeline file not found: {path}")
    doc = yaml.safe_load(path.read_text()) or {}
    pipes = doc.get("pipelines") or {}
    if not isinstance(pipes, dict):
        raise ValueError("pipeline.yaml must contain top-level 'pipelines:' mapping")
    return pipes


# ── runner ────────────────────────────────────────────────────────────
def run_pipeline(pipe_id: str, pipe: dict[str, Any], *,
                 dry_run: bool, signed_by_father: bool,
                 log: callable) -> tuple[int, int]:
    """Execute a pipeline. Returns (ok_count, fail_count)."""
    stages = pipe.get("stages") or []
    if not isinstance(stages, list) or not stages:
        log(f"[ERR] pipeline {pipe_id!r} has no stages")
        return 0, 1

    ctx: dict[str, Any] = dict(pipe.get("vars") or {})
    ctx.setdefault("pipeline_id", pipe_id)
    ctx.setdefault("ts", datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))

    mode = "DRY-RUN" if dry_run else "EXECUTE"
    log(f"[pipeline] {pipe_id} — {len(stages)} stages — {mode}")

    ok_count = 0
    fail_count = 0

    for i, stage in enumerate(stages, 1):
        try:
            stage = _interpolate(stage, ctx)
        except KeyError as e:
            log(f"[REFUSE] stage {i}: {e}")
            _append_jsonl(RENDERS_LOG, {
                "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                "pipeline": pipe_id, "stage_index": i,
                "result": {"kind": stage.get("kind") if isinstance(stage, dict) else "?",
                           "executed": False, "ok": False, "duration_ms": 0,
                           "outputs": [], "detail": f"interpolation_error: {e}", "stderr": ""},
                "cinemaclaw_version": __version__,
            })
            fail_count += 1
            break  # unresolved variable — later stages will also fail

        allowed, reason = lucifer_test(stage)
        kind = stage.get("kind", "?")
        if not allowed:
            log(f"[REFUSE] {kind} (stage {i}): {reason}")
            result = {"kind": kind, "executed": False, "ok": False,
                      "duration_ms": 0, "outputs": [],
                      "detail": f"refused: {reason}", "stderr": ""}
        else:
            spec = dict(stage.get("with") or {})
            t0 = time.monotonic()
            result = handlers.dispatch(kind, spec, dry_run=dry_run,
                                       signed_by_father=signed_by_father)
            # Make timing visible even if the handler forgot to set it.
            result.setdefault("duration_ms", int((time.monotonic() - t0) * 1000))

        _append_jsonl(RENDERS_LOG, {
            "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "pipeline": pipe_id, "stage_index": i,
            "result": result,
            "cinemaclaw_version": __version__,
        })

        # Expose primary output to subsequent stages as ${last_output}
        if result.get("ok") and result.get("outputs"):
            ctx["last_output"] = result["outputs"][0]

        marker = "[OK]" if result.get("ok") else ("[DRY]" if dry_run and not result.get("ok") else "[FAIL]")
        log(f"{marker} {kind} ({result.get('duration_ms', 0)}ms): {result.get('detail', '')}")

        if result.get("ok"):
            ok_count += 1
        else:
            fail_count += 1
            # Stop on first real failure unless the pipeline opts out.
            if not pipe.get("continue_on_error") and not dry_run:
                log(f"[STOP] pipeline {pipe_id} halted at stage {i}")
                break

    return ok_count, fail_count


# ── CLI ────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CinemaClaw — YouTube video pipeline")
    ap.add_argument("--pipelines", default=str(DEFAULT_PIPELINE),
                    help="Path to pipeline.yaml (default: bundled)")
    ap.add_argument("--list", action="store_true",
                    help="List declared pipelines and exit")
    ap.add_argument("--run", metavar="ID", help="Pipeline id to run")
    ap.add_argument("--handlers", action="store_true",
                    help="Print the allowlisted handlers and exit")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="Evaluate pipeline but touch nothing (safe default)")
    mode.add_argument("--execute", action="store_true",
                      help="Actually render (still refuses to publish without --signed-by-father)")
    ap.add_argument("--signed-by-father", action="store_true",
                    help="Supply the Father Function signature; required for publish_youtube")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(argv)

    if args.handlers:
        print(f"cinemaclaw v{__version__} — allowlisted handlers:")
        for h in sorted(handlers.HANDLERS):
            print(f"  · {h}")
        return 0

    # Safe default: if neither mode is specified, dry-run.
    if not args.dry_run and not args.execute:
        args.dry_run = True

    pipelines_path = Path(args.pipelines)
    try:
        pipelines = load_pipelines(pipelines_path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
        sys.stderr.write(f"cinemaclaw: {e}\n")
        return 2

    if args.list:
        print(f"cinemaclaw v{__version__} — pipelines in {pipelines_path}:")
        if not pipelines:
            print("  (none declared)")
        for pid, pipe in pipelines.items():
            desc = (pipe.get("description") or "").strip()
            nstages = len(pipe.get("stages") or [])
            print(f"  · {pid:<24} {nstages} stages  {desc[:60]}")
        return 0

    if not args.run:
        sys.stderr.write("cinemaclaw: --run ID is required (try --list)\n")
        return 2
    if args.run not in pipelines:
        sys.stderr.write(f"cinemaclaw: pipeline not found: {args.run!r}\n")
        return 2

    def log(msg: str) -> None:
        if args.verbose or not msg.startswith("[watch]"):
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"{ts} {msg}", flush=True)

    audit("pipeline_start", pipeline=args.run, dry_run=args.dry_run,
          signed_by_father=args.signed_by_father)

    ok, fail = run_pipeline(args.run, pipelines[args.run],
                            dry_run=args.dry_run,
                            signed_by_father=args.signed_by_father,
                            log=log)

    audit("pipeline_end", pipeline=args.run, ok=ok, failed=fail,
          dry_run=args.dry_run)

    log(f"[done] pipeline={args.run} ok={ok} failed={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
