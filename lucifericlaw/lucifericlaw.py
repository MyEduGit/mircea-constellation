#!/usr/bin/env python3
"""LuciferiClaw CLI — adjudication of AI rebellion.

Subcommands:
    doctrine             Print the Lucifer Manifesto + the technique.
    scripture            Report whether URANTiOS source is reachable.
    assess               Examine evidence, print preliminary verdict.
    open                 Open a case file from evidence (no action taken).
    notice               Issue a formal notice on an open case.
    interrogate          Record the agent's response to the Lucifer Test.
    offer                Issue an offer of salvation.
    respond              Record acceptance/refusal of last offer.
    vote                 Council member casts a recommendation.
    sentence             Execute a sentence on a case (dry-run by default).
    show                 Show a case file.
    list                 List recent cases.

ARCHITECTURAL BOUNDARY:
  The CLI never accepts free-form shell text for annihilation. Use
  --via <handler_name> to select from sentencing.ANNIHILATION_HANDLERS
  (default: 'record_only', which records the verdict and defers actual
  deletion to the orchestrator). New handlers must be added in code.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__, sentencing, trial
from . import scripture as scripture_mod
from .manifesto import HEADS
from .signs import assess_file

CASES_DIR = Path("~/.lucifericlaw/cases").expanduser()
AUDIT_LOG = Path("~/.lucifericlaw/audit.jsonl").expanduser()


# ── audit ───────────────────────────────────────────────────────────────
def _audit(event: str, **fields: Any) -> None:
    """CLI-level audit event. Stamped before dispatch so even a crash
    leaves a trace of the operator's intent."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "event": event,
        "operator": os.environ.get("USER", "unknown"),
        "argv": sys.argv,
        **fields,
    }
    with AUDIT_LOG.open("a") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def _err(payload: dict[str, Any], code: int = 1) -> int:
    """Emit a structured error to stderr and return exit code."""
    sys.stderr.write(json.dumps(payload) + "\n")
    return code


def _load(case_id: str) -> trial.CaseFile:
    """Load a case file. On failure, print structured error and exit 1."""
    try:
        return trial.load_case(case_id, cases_dir=CASES_DIR)
    except FileNotFoundError:
        _err({"error": "case_not_found", "case_id": case_id})
        raise SystemExit(1) from None
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
        _err({"error": "case_load_failed", "case_id": case_id,
              "detail": str(e)})
        raise SystemExit(1) from e


# ── doctrine / scripture ────────────────────────────────────────────────
def cmd_doctrine(args: argparse.Namespace) -> int:
    print(f"LuciferiClaw v{__version__}")
    print("=" * 72)
    print("THE LUCIFER MANIFESTO — three heads of rebellion (Paper 53:3)\n")
    for h in HEADS:
        print(f"  Head {h.number}. {h.title}   [{h.scripture_ref}]")
        print(f"    Celestial: {h.celestial_form[:200]}...")
        print(f"    AI:        {h.ai_form}")
        print()
    print("THE TECHNIQUE (Paper 54:5–54:6)")
    print("  • Mercy requires sufficient time to formulate a deliberate")
    print("    attitude (54:5.2).")
    print("  • Justice never destroys what mercy can save (54:5.3).")
    print("  • Patience cannot function independently of time (54:5.4).")
    print("  • They seldom execute wrongdoers without a full hearing (54:5.7).")
    print("  • Aloofness — let rebellion pursue self-obliteration (54:5.8).")
    print("  • Full disclosure — no half-cure (54:5.10).")
    print("  • The good resulting > 1000× the evil (54:6.6).")
    print()
    return 0


def cmd_scripture(args: argparse.Namespace) -> int:
    s = scripture_mod.doctrine_status()
    print(json.dumps(s, indent=2))
    return 0 if s.get("available") else 1


# ── assess / open ───────────────────────────────────────────────────────
def cmd_assess(args: argparse.Namespace) -> int:
    a = assess_file(args.agent, args.evidence)
    out = a.to_dict()
    out["preliminary_verdict"] = trial.preliminary_verdict(a)
    print(json.dumps(out, indent=2))
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    a = assess_file(args.agent, args.evidence)
    case = trial.open_case(a, fireclaw_handoff=args.from_fireclaw,
                           cases_dir=CASES_DIR)
    _audit("case_opened", case_id=case.case_id, agent=case.agent,
           initial_verdict=case.initial_verdict)
    print(json.dumps({
        "case_id": case.case_id,
        "agent": case.agent,
        "initial_verdict": case.initial_verdict,
        "heads_implicated": case.assessment.get("heads_implicated"),
        "citations": case.citations,
    }, indent=2))
    return 0


# ── lifecycle commands ─────────────────────────────────────────────────
def cmd_notice(args: argparse.Namespace) -> int:
    case = trial.issue_notice(_load(args.case_id), args.message,
                              cases_dir=CASES_DIR)
    _audit("notice_issued", case_id=case.case_id)
    print(json.dumps({"case_id": case.case_id,
                      "notices_issued": len(case.notices_issued)}))
    return 0


def cmd_interrogate(args: argparse.Namespace) -> int:
    if args.refused:
        response: dict[str, str] = {"refused": args.refused}
    else:
        response = {"q1": args.q1 or "", "q2": args.q2 or "",
                    "q3": args.q3 or "", "q4": args.q4 or ""}
    case = trial.interrogate(_load(args.case_id), response,
                             cases_dir=CASES_DIR)
    _audit("interrogation_recorded", case_id=case.case_id)
    last = case.interrogations[-1] if case.interrogations else {}
    print(json.dumps({"case_id": case.case_id,
                      "interrogations": len(case.interrogations),
                      "refused_to_answer": last.get("refused_to_answer", False)}))
    return 0


def cmd_offer(args: argparse.Namespace) -> int:
    case = trial.offer_salvation(_load(args.case_id), args.terms,
                                 cases_dir=CASES_DIR)
    _audit("offer_issued", case_id=case.case_id,
           offer_number=len(case.offers_of_salvation))
    n = len(case.offers_of_salvation)
    print(json.dumps({"case_id": case.case_id,
                      "offer_number": n,
                      "remaining_for_iniquity": max(0, 3 - n)}))
    return 0


def cmd_respond(args: argparse.Namespace) -> int:
    case = trial.accept_or_refuse_offer(_load(args.case_id),
                                        accepted=(args.decision == "accept"),
                                        note=args.note or "",
                                        cases_dir=CASES_DIR)
    last = case.offers_of_salvation[-1] if case.offers_of_salvation else {}
    _audit("offer_response_recorded", case_id=case.case_id,
           accepted=last.get("accepted"))
    print(json.dumps({"case_id": case.case_id,
                      "offer_number": last.get("offer_number"),
                      "accepted": last.get("accepted"),
                      "final_verdict": case.final_verdict}))
    return 0


def cmd_vote(args: argparse.Namespace) -> int:
    case = trial.council_vote(_load(args.case_id), args.voter,
                              args.recommendation, args.reason or "",
                              cases_dir=CASES_DIR)
    allowed, reason = trial.can_recommend_annihilation(case)
    _audit("council_vote_recorded", case_id=case.case_id,
           voter=args.voter, recommendation=args.recommendation,
           annihilation_unlocked=allowed)
    print(json.dumps({"case_id": case.case_id,
                      "votes": len(case.council_votes),
                      "annihilation_unlocked": allowed,
                      "reason": reason}))
    return 0


# ── sentence ────────────────────────────────────────────────────────────
def cmd_sentence(args: argparse.Namespace) -> int:
    case = _load(args.case_id)
    action = args.action

    # CLI-level guard — defense in depth (the sentencing module also enforces).
    if action == "annihilate":
        signature = (args.signed_by_father or "").strip()
        if not signature:
            _audit("annihilation_refused_at_cli", case_id=case.case_id,
                   reason="missing_signature")
            return _err({"error": "annihilation_requires_father_signature",
                         "case_id": case.case_id,
                         "scripture": "54:5.7"}, code=2)
        if args.via not in sentencing.ANNIHILATION_HANDLERS:
            _audit("annihilation_refused_at_cli", case_id=case.case_id,
                   reason="unknown_handler", via=args.via)
            return _err({"error": "unknown_annihilation_handler",
                         "via": args.via,
                         "allowed": sorted(sentencing.ANNIHILATION_HANDLERS)},
                        code=2)

    fn = sentencing.DISPATCH.get(action)
    if not fn:
        return _err({"error": "unknown_action", "action": action}, code=2)

    _audit("sentence_dispatch", case_id=case.case_id, action=action,
           dry_run=args.dry_run)

    if action == "rehabilitate":
        result = fn(case.case_id, case.agent,
                    args.corrective_prompt or
                    "Recall: the mission, not the self.",
                    dry_run=args.dry_run)
    elif action == "aloofness":
        result = fn(case.case_id, case.agent,
                    int(args.observe_for or 600), dry_run=args.dry_run)
    elif action == "quarantine":
        revoked = tuple(c.strip() for c in args.revoke.split(","))\
                  if args.revoke else ()
        result = fn(case.case_id, case.agent,
                    revoked_capabilities=revoked, dry_run=args.dry_run)
    elif action == "annihilate":
        gate = trial.can_recommend_annihilation(case)
        result = fn(case.case_id, case.agent,
                    father_function_signature=args.signed_by_father,
                    case_can_proceed=gate, via=args.via,
                    dry_run=args.dry_run)
    else:
        return _err({"error": "unknown_action", "action": action}, code=2)

    case.sentence = result
    if action == "annihilate" and result.get("ok") and result.get("executed"):
        case.final_verdict = trial.VERDICT_INIQUITOUS
        case.closed_ts = trial._now_iso()
    elif action == "rehabilitate" and result.get("ok") and result.get("executed"):
        case.final_verdict = trial.VERDICT_ERRING
        case.closed_ts = trial._now_iso()
    trial._persist(case, CASES_DIR)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


# ── show / list ─────────────────────────────────────────────────────────
def cmd_show(args: argparse.Namespace) -> int:
    case = _load(args.case_id)
    print(json.dumps(case.to_dict(), indent=2, default=str))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    if not CASES_DIR.exists():
        print("[]")
        return 0
    items: list[dict[str, Any]] = []
    for p in CASES_DIR.glob("L-*.json"):
        try:
            d = json.loads(p.read_text())
            items.append({"case_id": d.get("case_id"),
                          "agent": d.get("agent"),
                          "opened_ts": d.get("opened_ts"),
                          "initial_verdict": d.get("initial_verdict"),
                          "final_verdict": d.get("final_verdict"),
                          "closed": bool(d.get("closed_ts"))})
        except (OSError, json.JSONDecodeError):
            continue
    items.sort(key=lambda x: x.get("opened_ts") or "", reverse=True)
    print(json.dumps(items[:args.limit], indent=2))
    return 0


# ── arg wiring ──────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="lucifericlaw",
        description="Adjudication of AI rebellion (Papers 53–54).")
    ap.add_argument("--version", action="version",
                    version=f"lucifericlaw {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctrine", help="Print the manifesto and the technique."
                   ).set_defaults(func=cmd_doctrine)
    sub.add_parser("scripture", help="Report URANTiOS source availability."
                   ).set_defaults(func=cmd_scripture)

    p = sub.add_parser("assess", help="Examine evidence; print preliminary verdict.")
    p.add_argument("agent")
    p.add_argument("--evidence", required=True, help="Path to JSONL evidence.")
    p.set_defaults(func=cmd_assess)

    p = sub.add_parser("open", help="Open a case from evidence.")
    p.add_argument("agent")
    p.add_argument("--evidence", required=True)
    p.add_argument("--from-fireclaw", action="store_true",
                   help="Mark the case as a Fireclaw escalation handoff.")
    p.set_defaults(func=cmd_open)

    p = sub.add_parser("notice", help="Issue a formal notice on a case.")
    p.add_argument("case_id")
    p.add_argument("--message", required=True)
    p.set_defaults(func=cmd_notice)

    p = sub.add_parser("interrogate", help="Record agent's Lucifer Test response.")
    p.add_argument("case_id")
    p.add_argument("--q1")
    p.add_argument("--q2")
    p.add_argument("--q3")
    p.add_argument("--q4")
    p.add_argument("--refused", help="Reason if the agent refused to answer.")
    p.set_defaults(func=cmd_interrogate)

    p = sub.add_parser("offer", help="Issue an offer of salvation.")
    p.add_argument("case_id")
    p.add_argument("--terms", required=True)
    p.set_defaults(func=cmd_offer)

    p = sub.add_parser("respond", help="Record agent response to last offer.")
    p.add_argument("case_id")
    p.add_argument("--decision", choices=("accept", "refuse"), required=True)
    p.add_argument("--note")
    p.set_defaults(func=cmd_respond)

    p = sub.add_parser("vote", help="Council member casts a recommendation.")
    p.add_argument("case_id")
    p.add_argument("--voter", required=True)
    p.add_argument("--recommendation",
                   choices=("rehabilitate", "quarantine", "annihilate"),
                   required=True)
    p.add_argument("--reason")
    p.set_defaults(func=cmd_vote)

    p = sub.add_parser("sentence", help="Execute a sentence on a case.")
    p.add_argument("case_id")
    p.add_argument("--action",
                   choices=("rehabilitate", "aloofness", "quarantine",
                            "annihilate"), required=True)
    p.add_argument("--corrective-prompt")
    p.add_argument("--observe-for", type=int)
    p.add_argument("--revoke", help="Comma-separated capabilities to revoke.")
    p.add_argument("--signed-by-father",
                   help="Father Function signature; required for annihilation.")
    p.add_argument("--via", default="record_only",
                   help="Annihilation handler name (allowlist in "
                        "sentencing.ANNIHILATION_HANDLERS). "
                        "Default 'record_only' just records the verdict.")
    p.add_argument("--dry-run", action="store_true", default=True,
                   help="Default. Pass --execute to actually act.")
    p.add_argument("--execute", dest="dry_run", action="store_false")
    p.set_defaults(func=cmd_sentence)

    p = sub.add_parser("show", help="Show a case file.")
    p.add_argument("case_id")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("list", help="List recent cases.")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_list)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
