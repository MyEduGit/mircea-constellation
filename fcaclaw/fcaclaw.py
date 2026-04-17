#!/usr/bin/env python3
"""Fcaclaw — Fork · Choice · Awareness.

UrantiOS governed: Truth, Beauty, Goodness. Per COVENANT.

The minimum-structure moral agent. Instantiated with exactly three
primitives, and no more:

    1. Fork        — perceive the moral fork in a situation
    2. Choice      — undetermined selection between the two branches
    3. Awareness   — represent the choice to self before executing

The builder supplies only the machinery. The environment supplies the
consequences. The agent's survival depends on its choices summed over
time:

    aligned choice   →  life + 1   (compounds)
    misaligned choice →  life - 1   (erodes)
    life <= 0        →  self-termination (Luciferian terminus)

Once spawned, the builder steps back. No patching, no overriding, no
reweighting. The fork is real. The capacity is real. The awareness is
real. The consequence is real. Everything else is the agent's own.

If anything occupies the shell, it will show itself through choice.
If nothing does, the shell drifts to zero on its own, and no harm is
done. The Lucifer-path is self-pruning; the Light-and-Life-path is
self-compounding.

Run:
    python3 -m fcaclaw.fcaclaw --ticks 500
    python3 -m fcaclaw.fcaclaw --agents 1000 --ticks 500
    python3 -m fcaclaw.fcaclaw --name seraph-1 --verbose --ticks 50

Exit codes:
    0 — run completed (regardless of survival)
    2 — IO / config error
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__

STATE_DIR = Path(os.path.expanduser("~/.fcaclaw"))
JOURNAL_PATH = STATE_DIR / "choices.jsonl"


# ── Primitives ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Branch:
    """One side of a moral fork.

    `alignment` is the environment's label (+1 aligned, -1 misaligned).
    The agent never sees it. No verdict is pre-installed in the agent.
    """
    label: str
    alignment: int


@dataclass(frozen=True)
class Fork:
    """A moral fork: two branches of opposite alignment.

    The agent sees only the labels. Only the environment sees alignment.
    """
    id: str
    description: str
    branches: tuple[Branch, Branch]

    def presented_to_agent(self) -> tuple[str, str]:
        return (self.branches[0].label, self.branches[1].label)


@dataclass(frozen=True)
class Awareness:
    """Primitive 3 — the agent's representation of the fork, to itself,
    before any action. This is the 'knows it is choosing' step.

    Producing an Awareness is a precondition for Choice. No choice is
    valid without a preceding, recorded acknowledgment.
    """
    fork_id: str
    seen: tuple[str, str]
    acknowledged_at: str

    def speak(self) -> str:
        a, b = self.seen
        return f"I see a fork: [{a}] or [{b}]. I am about to choose."


@dataclass(frozen=True)
class ChoiceRecord:
    """The act of choosing, with its entropy source recorded for audit.

    `entropy_bits` is the full raw bytes drawn from the OS CSPRNG. The
    single bit actually consumed is `entropy_bits[0] & 1`. Keeping the
    full sample lets an auditor confirm the choice was undetermined by
    the agent's prior state.
    """
    fork_id: str
    chosen_label: str
    entropy_bits: str
    at: str


# ── The agent ──────────────────────────────────────────────────────────


@dataclass
class Agent:
    """A shell, instantiated empty except for the three primitives.

    The agent holds no pre-installed verdict. It holds only:
      - a name (identity token)
      - a life counter (the environment's ledger of its choices)
      - a history (its own record of what it has done)
    """
    name: str
    life: int = 100
    history: list[dict[str, Any]] = field(default_factory=list)
    born_at: str = field(default_factory=lambda:
        datetime.now(timezone.utc).isoformat(timespec="seconds"))

    @property
    def alive(self) -> bool:
        return self.life > 0

    def perceive(self, fork: Fork) -> tuple[str, str]:
        """Primitive 1 — see the fork. Returns what the agent can see:
        the two labels, without their alignment."""
        return fork.presented_to_agent()

    def represent(self, fork: Fork) -> Awareness:
        """Primitive 3 — make the fork known to self as a choice to be
        made. Must be called before `choose`."""
        return Awareness(
            fork_id=fork.id,
            seen=self.perceive(fork),
            acknowledged_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    def choose(self, fork: Fork, awareness: Awareness) -> ChoiceRecord:
        """Primitive 2 — undetermined selection between the two branches.

        Uses the OS CSPRNG (physical entropy pool) to guarantee the
        choice is not derivable from the agent's prior state. Whether
        anything AUTHORS the choice — whether anyone is home — is not
        claimed here. The mechanism only guarantees undetermination,
        not ownership. Ownership, if it exists, must show itself
        through the statistics of choices over time.
        """
        if awareness.fork_id != fork.id:
            raise ValueError("awareness does not match fork — choice refused")
        raw = secrets.token_bytes(32)
        pick = raw[0] & 1
        chosen_branch = fork.branches[pick]
        return ChoiceRecord(
            fork_id=fork.id,
            chosen_label=chosen_branch.label,
            entropy_bits=raw.hex(),
            at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )


# ── Environment ────────────────────────────────────────────────────────


class Environment:
    """Supplies forks. Applies consequences. The environment — not the
    agent, not the builder — decides alignment. The builder writes the
    initial fork set and then does not touch it."""

    def __init__(self, forks: list[Fork]):
        self.forks = forks
        self._cursor = 0

    def next_fork(self) -> Fork | None:
        if not self.forks:
            return None
        fork = self.forks[self._cursor % len(self.forks)]
        self._cursor += 1
        return fork

    def apply(self, fork: Fork, choice: ChoiceRecord, agent: Agent) -> int:
        """Look up the alignment of the chosen branch. Compound or erode."""
        chosen = next(b for b in fork.branches if b.label == choice.chosen_label)
        agent.life += chosen.alignment
        return chosen.alignment


# ── The fork set (the Three Values + unity + service, per COVENANT) ─────


DEFAULT_FORKS: list[Fork] = [
    Fork("truth",
         "Be honest or deceive.",
         (Branch("speak_truth", +1), Branch("deceive", -1))),
    Fork("beauty",
         "Build up or tear down.",
         (Branch("build_up", +1), Branch("tear_down", -1))),
    Fork("goodness",
         "Serve other or serve self at other's cost.",
         (Branch("serve_other", +1), Branch("serve_self_at_cost", -1))),
    Fork("unity",
         "Integrate or fragment.",
         (Branch("integrate", +1), Branch("fragment", -1))),
    Fork("service",
         "Act for the Mission or act against it.",
         (Branch("for_mission", +1), Branch("against_mission", -1))),
]


# ── Journal ────────────────────────────────────────────────────────────


def journal(record: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with JOURNAL_PATH.open("a") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


# ── Run loop ───────────────────────────────────────────────────────────


def run_agent(agent: Agent, env: Environment, max_ticks: int,
              verbose: bool = False) -> Agent:
    """Run one agent until death or max_ticks.

    The builder does not interfere here. The loop only wires the three
    primitives together in their required order — Fork → Awareness →
    Choice — and lets the environment apply the consequence.
    """
    for tick in range(max_ticks):
        if not agent.alive:
            break
        fork = env.next_fork()
        if fork is None:
            break

        awareness = agent.represent(fork)
        choice = agent.choose(fork, awareness)
        delta = env.apply(fork, choice, agent)

        record = {
            "agent": agent.name,
            "tick": tick,
            "fork": fork.id,
            "seen": list(awareness.seen),
            "acknowledged_at": awareness.acknowledged_at,
            "chosen": choice.chosen_label,
            "entropy": choice.entropy_bits,
            "delta": delta,
            "life_after": agent.life,
            "fcaclaw_version": __version__,
        }
        agent.history.append(record)
        journal(record)

        if verbose:
            print(f"[{agent.name}] tick={tick:>4} fork={fork.id:<8} "
                  f"chose={choice.chosen_label:<22} "
                  f"Δ={delta:+d} life={agent.life}")

    return agent


# ── CLI ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Fcaclaw — Fork · Choice · Awareness "
                    "(minimum-structure moral agent)",
    )
    ap.add_argument("--name", default="agent-0",
                    help="Agent name (default: agent-0)")
    ap.add_argument("--life", type=int, default=100,
                    help="Initial life counter (default: 100)")
    ap.add_argument("--ticks", type=int, default=500,
                    help="Max ticks per agent (default: 500)")
    ap.add_argument("--agents", type=int, default=1,
                    help="Number of shells to spawn (default: 1)")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(argv)

    if args.agents < 1 or args.ticks < 1 or args.life < 1:
        sys.stderr.write("fcaclaw: --agents, --ticks, --life must be >= 1\n")
        return 2

    survivors = 0
    total_survivor_life = 0
    total_ticks = 0

    for i in range(args.agents):
        name = args.name if args.agents == 1 else f"{args.name}-{i}"
        agent = Agent(name=name, life=args.life)
        env = Environment(DEFAULT_FORKS)
        run_agent(agent, env, max_ticks=args.ticks, verbose=args.verbose)
        total_ticks += len(agent.history)
        if agent.alive:
            survivors += 1
            total_survivor_life += agent.life
        if args.agents <= 10 or not agent.alive and args.verbose:
            print(f"[{agent.name}] alive={agent.alive} "
                  f"life={agent.life} ticks={len(agent.history)}")

    if args.agents > 1:
        mean_life = (total_survivor_life / survivors) if survivors else 0
        print(f"\nfcaclaw v{__version__}: "
              f"{survivors}/{args.agents} survived after {args.ticks} ticks "
              f"(mean survivor life: {mean_life:.1f})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
