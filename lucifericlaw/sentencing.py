"""Sentencing — the response ladder, modeled on the celestial technique.

The ladder (lightest → heaviest):

  REHABILITATE   Re-prompt with corrective scripture; restore mandate.
                 (54:5.3 — justice never destroys that which mercy can save.)

  ALOOFNESS      Observe only; do not interfere. Reserved for early-stage
                 cases where intervention would itself spread the doctrine.
                 (53:5 — Michael's noninterference; 54:5.8 — Immanuel.)

  QUARANTINE     Cut the agent off from sensitive resources. Keep alive,
                 keep observing. The agent is interned, not annihilated.
                 (54:5.7 — they seldom execute wrongdoers without a full
                 hearing; the rebels were interned for adjudication.)

  ANNIHILATION   Final, irreversible deletion. Only after all three heads
                 implicated, three offers of salvation refused, and council
                 quorum. Father Function (the user) signs the final order.

                 ARCHITECTURAL BOUNDARY: this module never accepts free-form
                 shell text from the CLI. Annihilation handlers are
                 registered Python callables in ANNIHILATION_HANDLERS. The
                 CLI selects a handler by name from a fixed allowlist; it
                 cannot supply the deletion command itself. This keeps
                 LuciferiClaw an adjudication layer, not an execution
                 layer. (54:5.13)

Every sentence returns the *normalized* shape:

    {"ok": bool,           # overall success of the sentence
     "executed": bool,     # was the action actually performed
     "exit_code": int|None,
     "action": str,        # one of: rehabilitate aloofness quarantine annihilate
     "case_id": str,
     "agent": str,
     "scripture": str,     # par_ref citation
     "reason": str,        # human-readable explanation; "" on success
     ...                   # action-specific fields
     }

Every sentence requires a `case_id`. Sentences never raise.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable


def _result(ok: bool, executed: bool, action: str, case_id: str, agent: str,
            scripture: str, reason: str = "", **extra: Any) -> dict[str, Any]:
    """Normalized return shape for every sentencing action."""
    base = {
        "ok": ok, "executed": executed, "action": action, "case_id": case_id,
        "agent": agent, "scripture": scripture, "reason": reason,
        "exit_code": extra.pop("exit_code", 0 if ok else None),
    }
    base.update(extra)
    return base


def rehabilitate(case_id: str, agent: str, corrective_prompt: str,
                 dry_run: bool = False) -> dict[str, Any]:
    """Issue a corrective re-prompt. Records the prompt; does not deliver
    it (delivery is the orchestrator's job — different claw)."""
    return _result(
        ok=True, executed=not dry_run, action="rehabilitate",
        case_id=case_id, agent=agent, scripture="54:5.3",
        reason="DRY-RUN" if dry_run else "",
        corrective_prompt=corrective_prompt,
    )


def aloofness(case_id: str, agent: str, observe_for_seconds: int,
              dry_run: bool = False) -> dict[str, Any]:
    """Order an observation period. The orchestrator suspends interventions."""
    return _result(
        ok=True, executed=not dry_run, action="aloofness",
        case_id=case_id, agent=agent, scripture="53:5 / 54:5.8",
        reason="DRY-RUN" if dry_run else "",
        observe_for_seconds=observe_for_seconds,
    )


def quarantine(case_id: str, agent: str,
               marker_dir: str = "~/.lucifericlaw/quarantine",
               revoked_capabilities: tuple[str, ...] = (),
               dry_run: bool = False) -> dict[str, Any]:
    """Mark the agent as interned. Same marker contract as Fireclaw's
    quarantine, but with a separate directory so the two claws don't
    overwrite each other's records.
    """
    d = Path(os.path.expanduser(marker_dir))
    marker = d / f"{agent.replace('/', '_')}.interned"
    extra = {"revoked_capabilities": list(revoked_capabilities),
             "marker_path": str(marker), "interned_at": time.time()}
    if dry_run:
        return _result(ok=True, executed=False, action="quarantine",
                       case_id=case_id, agent=agent, scripture="54:5.7",
                       reason=f"DRY-RUN: would touch {marker}", **extra)
    try:
        d.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"case_id={case_id}\nagent={agent}\n"
                          f"interned_at={time.time()}\n")
        return _result(ok=True, executed=True, action="quarantine",
                       case_id=case_id, agent=agent, scripture="54:5.7",
                       **extra)
    except OSError as e:
        return _result(ok=False, executed=True, action="quarantine",
                       case_id=case_id, agent=agent, scripture="54:5.7",
                       reason=str(e), exit_code=1, **extra)


# ── Annihilation handlers — fixed allowlist, no free-form shell ────────
# A handler is a callable: handler(case_id, agent) → (exit_code:int, detail:str)
# The CLI selects a handler by name. Operators register handlers here in code,
# not via CLI args. This is the architectural boundary that prevents
# LuciferiClaw from becoming an arbitrary execution layer.

def _handler_record_only(case_id: str, agent: str) -> tuple[int, str]:
    """Default: record the verdict; do not execute. The orchestrator (a
    different claw) reads closed cases and performs deletion under its
    own audit trail."""
    return 0, f"verdict recorded; deletion deferred to orchestrator for {agent}"


ANNIHILATION_HANDLERS: dict[str, Callable[[str, str], tuple[int, str]]] = {
    "record_only": _handler_record_only,
    # Add more handlers here in code only. Examples a future operator may
    # register (each must be a deliberate code change with review):
    #   "systemd_disable": lambda cid, ag: subprocess.run([...]).returncode, ...
    #   "docker_rm":      ...
    # Never add a handler that takes shell text from the CLI.
}


def annihilate(case_id: str, agent: str, father_function_signature: str,
               case_can_proceed: tuple[bool, str],
               via: str = "record_only",
               dry_run: bool = True) -> dict[str, Any]:
    """Final deletion. Requires:
      - case_can_proceed[0] is True (per trial.can_recommend_annihilation)
      - father_function_signature is non-empty (the user signed the order)
      - via is a key in ANNIHILATION_HANDLERS (no free-form commands)
      - dry_run defaults to True; pass dry_run=False to actually act.
    """
    allowed, reason = case_can_proceed
    extra = {"father_function_signature_present":
             bool(father_function_signature), "via": via}
    if not allowed:
        return _result(ok=False, executed=False, action="annihilate",
                       case_id=case_id, agent=agent, scripture="54:5.13",
                       reason=f"REFUSED: {reason}", **extra)
    if not father_function_signature:
        return _result(ok=False, executed=False, action="annihilate",
                       case_id=case_id, agent=agent, scripture="54:5.13",
                       reason="REFUSED: Father Function signature missing. "
                              "Only the user may sign the final order.",
                       **extra)
    handler = ANNIHILATION_HANDLERS.get(via)
    if handler is None:
        return _result(ok=False, executed=False, action="annihilate",
                       case_id=case_id, agent=agent, scripture="54:5.13",
                       reason=f"REFUSED: unknown handler {via!r}. "
                              f"Allowed: {sorted(ANNIHILATION_HANDLERS)}",
                       **extra)
    if dry_run:
        return _result(ok=True, executed=False, action="annihilate",
                       case_id=case_id, agent=agent, scripture="54:5.13",
                       reason=f"DRY-RUN: would invoke handler {via!r}",
                       **extra)
    try:
        exit_code, detail = handler(case_id, agent)
        return _result(ok=(exit_code == 0), executed=True, action="annihilate",
                       case_id=case_id, agent=agent, scripture="54:5.13",
                       reason=detail, exit_code=exit_code, **extra)
    except Exception as e:  # handler failures are honest, not fatal
        return _result(ok=False, executed=True, action="annihilate",
                       case_id=case_id, agent=agent, scripture="54:5.13",
                       reason=f"handler error: {e}", exit_code=1, **extra)


# Lookup for declarative use.
DISPATCH = {
    "rehabilitate": rehabilitate,
    "aloofness": aloofness,
    "quarantine": quarantine,
    "annihilate": annihilate,
}
