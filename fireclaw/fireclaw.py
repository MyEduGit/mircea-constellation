#!/usr/bin/env python3
"""Fireclaw daemon — remediation & incident-response loop.

UrantiOS governed: Truth, Beauty, Goodness.

Run:
    python3 -m fireclaw.fireclaw --dry-run --once
    python3 -m fireclaw.fireclaw --execute --once
    python3 -m fireclaw.fireclaw --execute --loop --interval 60

Exit codes:
    0 — clean cycle (no actions, or actions all succeeded)
    1 — at least one action failed
    2 — config / IO error (rules.yaml unreadable, etc.)
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
        "fireclaw: PyYAML not installed. Run setup/fireclaw_install.sh "
        "or `pip install pyyaml`.\n"
    )
    sys.exit(2)

from . import __version__, actions, signals

# ── Paths ──────────────────────────────────────────────────────────────
DEFAULT_RULES = Path(__file__).parent / "rules.yaml"
STATE_DIR = Path(os.path.expanduser("~/.fireclaw"))
INCIDENTS_PATH = STATE_DIR / "incidents.jsonl"
COUNTERS_PATH = STATE_DIR / "counters.json"


# ── Persistent state (per-rule consecutive failures + last action ts) ──
def load_state() -> dict[str, dict[str, Any]]:
    if not COUNTERS_PATH.exists():
        return {}
    try:
        return json.loads(COUNTERS_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict[str, dict[str, Any]]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = COUNTERS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(COUNTERS_PATH)


def append_incident(record: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with INCIDENTS_PATH.open("a") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


# ── Lucifer Test (every fired rule must pass before action) ─────────────
def lucifer_test(rule: dict[str, Any], signal: dict[str, Any]) -> tuple[bool, str]:
    """Return (allowed, reason). Refusal is honest: log and escalate."""
    if not rule.get("action"):
        return False, "no action declared (rule violates mandate)"
    if rule["action"].get("kind") not in actions.DISPATCH:
        return False, f"action kind not in DISPATCH: {rule['action'].get('kind')!r}"
    if not signal.get("ok") is False:  # only fire when signal says NOT ok
        # This is defensive — main loop already filtered. Keep the invariant.
        return False, "signal is ok; refuse to act on healthy state"
    return True, "passed"


# ── Main eval loop ──────────────────────────────────────────────────────
def evaluate_cycle(rules: list[dict[str, Any]], state: dict[str, dict[str, Any]],
                   dry_run: bool, log: callable) -> tuple[int, int]:
    """Run one cycle. Return (actions_executed, actions_failed)."""
    now = time.time()
    now_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    executed = 0
    failed = 0

    for rule in rules:
        rid = rule.get("id")
        if not rid:
            log(f"[skip] rule missing 'id': {rule}")
            continue

        sig = signals.collect(rule.get("signal", {}))
        rs = state.setdefault(rid, {"consecutive_failures": 0,
                                    "last_action_ts": 0,
                                    "trigger_count_24h": 0,
                                    "first_trigger_in_window_ts": 0})

        if sig["ok"]:
            if rs["consecutive_failures"]:
                log(f"[recover] {rid}: signal ok, resetting failure count "
                    f"(was {rs['consecutive_failures']})")
            rs["consecutive_failures"] = 0
            continue

        rs["consecutive_failures"] += 1
        cond = rule.get("condition", {}) or {}
        threshold = int(cond.get("consecutive_failures", 1))
        cooldown = float(cond.get("cooldown_seconds", 300))

        if rs["consecutive_failures"] < threshold:
            log(f"[watch] {rid}: failure {rs['consecutive_failures']}/{threshold} "
                f"({sig['detail']})")
            continue

        if (now - rs["last_action_ts"]) < cooldown:
            remaining = int(cooldown - (now - rs["last_action_ts"]))
            log(f"[cooldown] {rid}: {remaining}s remaining")
            continue

        allowed, reason = lucifer_test(rule, sig)
        if not allowed:
            log(f"[REFUSE] {rid}: {reason}")
            append_incident({
                "ts": now_iso, "rule": rid, "signal": sig,
                "action": {"kind": rule.get("action", {}).get("kind"),
                           "executed": False, "exit_code": None,
                           "duration_ms": 0, "stdout": "",
                           "stderr": f"refused: {reason}"},
                "escalated": True, "fireclaw_version": __version__,
            })
            failed += 1
            continue

        result = actions.execute(rule["action"], dry_run=dry_run)
        rs["last_action_ts"] = now

        # 24h trigger window
        if (now - rs["first_trigger_in_window_ts"]) > 86400:
            rs["first_trigger_in_window_ts"] = now
            rs["trigger_count_24h"] = 0
        rs["trigger_count_24h"] += 1

        # Escalation
        esc_cfg = rule.get("escalate") or {}
        escalate = False
        if result.get("executed") and result.get("exit_code") not in (0, None):
            if esc_cfg.get("on_action_failure"):
                escalate = True
        repeat_threshold = esc_cfg.get("on_repeated_trigger")
        if repeat_threshold and rs["trigger_count_24h"] >= int(repeat_threshold):
            escalate = True

        if escalate and not dry_run:
            actions.alert_telegram(
                f"[Fireclaw] {rid} fired (signal: {sig['detail']}); "
                f"action {result.get('kind')} exit={result.get('exit_code')} "
                f"24h_count={rs['trigger_count_24h']}",
                dry_run=False,
            )

        append_incident({
            "ts": now_iso, "rule": rid, "signal": sig, "action": result,
            "escalated": escalate, "trigger_count_24h": rs["trigger_count_24h"],
            "fireclaw_version": __version__,
        })

        if result.get("executed") and result.get("exit_code") == 0:
            executed += 1
            log(f"[ACT] {rid}: {result['kind']} exit=0 ({result['duration_ms']}ms)")
            # On successful action, reset failure count so the next probe is fresh
            rs["consecutive_failures"] = 0
        else:
            failed += 1
            log(f"[FAIL] {rid}: {result['kind']} exit={result.get('exit_code')} "
                f"stderr={(result.get('stderr') or '')[:120]}")

    return executed, failed


# ── CLI ─────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fireclaw — remediation daemon")
    ap.add_argument("--rules", default=str(DEFAULT_RULES),
                    help="Path to rules.yaml (default: bundled)")
    ap.add_argument("--once", action="store_true", help="One cycle, then exit")
    ap.add_argument("--loop", action="store_true", help="Run forever")
    ap.add_argument("--interval", type=int, default=60,
                    help="Seconds between cycles in --loop mode (default: 60)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="Evaluate rules but do not execute actions")
    mode.add_argument("--execute", action="store_true",
                      help="Actually execute matching actions")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(argv)

    if not args.once and not args.loop:
        args.once = True
    if not args.dry_run and not args.execute:
        args.dry_run = True  # safe default

    rules_path = Path(args.rules)
    if not rules_path.exists():
        sys.stderr.write(f"fireclaw: rules file not found: {rules_path}\n")
        return 2
    try:
        rules_doc = yaml.safe_load(rules_path.read_text()) or {}
    except yaml.YAMLError as e:
        sys.stderr.write(f"fireclaw: rules YAML error: {e}\n")
        return 2
    rules = rules_doc.get("rules", [])
    if not isinstance(rules, list):
        sys.stderr.write("fireclaw: rules.yaml must contain top-level 'rules:' list\n")
        return 2

    def log(msg: str) -> None:
        if args.verbose or not msg.startswith("[watch]"):
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"{ts} {msg}", flush=True)

    log(f"fireclaw v{__version__} — {len(rules)} rules — "
        f"{'DRY-RUN' if args.dry_run else 'EXECUTE'} mode")

    state = load_state()
    overall_failed = 0

    try:
        while True:
            executed, failed = evaluate_cycle(rules, state, args.dry_run, log)
            save_state(state)
            overall_failed += failed
            if executed or failed:
                log(f"[cycle] executed={executed} failed={failed}")
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log("interrupted")

    return 1 if overall_failed else 0


if __name__ == "__main__":
    sys.exit(main())
