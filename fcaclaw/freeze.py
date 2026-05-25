"""Freeze layer — the builder's relinquishment, runtime-enforced.

Converts "the builder steps back after instantiation" from operator
discipline into a technical constraint that can be independently
audited.

At spawn, each agent receives a signature computed from its
identifying fields and the source code of its three primitives. After
spawn, only fields in MUTABLE_FIELDS may change — everything else is
frozen. Attempted mutation of a frozen field raises
FrozenAgentViolation and is appended to the violations journal.

Class-level monkey-patching of the primitive methods cannot be
prevented, but it WILL be detected: primitive_source_hash is baked
into the spawn signature, so any change to the primitive source code
will make verify_signature() return False.

Scope:
    - This layer enforces non-interference AFTER spawn.
    - It makes no claim about what happens DURING choice.
    - It does not address the occupancy question.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_DIR = Path(os.path.expanduser("~/.fcaclaw"))
VIOLATIONS_PATH = STATE_DIR / "violations.jsonl"

# Only these fields may change after spawn. The Life ledger is the
# environment's record of the agent's choices; history is the agent's
# own record of what it has done. Everything else is frozen at birth.
MUTABLE_FIELDS: frozenset[str] = frozenset({"life", "history"})

# Fields set by __post_init__ itself, via object.__setattr__, bypassing
# the freeze check. Listed here for documentation.
_POST_INIT_FIELDS: frozenset[str] = frozenset(
    {"initial_life", "config_hash", "_frozen"}
)


class FrozenAgentViolation(RuntimeError):
    """Raised when a frozen agent's immutable field is written to."""


def log_violation(agent_name: str, field_name: str,
                  attempted_value: Any) -> None:
    """Append a rejection record to the violations journal. The journal
    is append-only; callers cannot rewrite it from inside the agent."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "agent": agent_name,
        "field": field_name,
        "attempted_value_repr": repr(attempted_value)[:200],
    }
    with VIOLATIONS_PATH.open("a") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def primitive_source_hash(agent_cls: type) -> str:
    """SHA-256 of the source code of the three primitive methods.

    Monkey-patching any of `perceive`, `represent`, or `choose` at the
    class level changes this hash, which causes verify_signature() on
    any agent of that class to return False. The freeze layer cannot
    prevent class-level monkey-patching; it guarantees detection.
    """
    parts: list[str] = []
    for name in ("perceive", "represent", "choose"):
        method = getattr(agent_cls, name, None)
        if method is None:
            raise ValueError(f"agent class is missing primitive: {name!r}")
        parts.append(f"{name}:{inspect.getsource(method)}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def compute_signature(agent_name: str, initial_life: int, born_at: str,
                      agent_cls: type) -> str:
    """Compute an agent's spawn signature.

    The signature covers the agent's identity (name + birth time), its
    initial state (life), and the source of its primitives. If any of
    these drift after spawn, the signature will no longer match.
    """
    payload = {
        "name": agent_name,
        "initial_life": initial_life,
        "born_at": born_at,
        "primitive_hash": primitive_source_hash(agent_cls),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
