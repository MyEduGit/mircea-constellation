"""Twelve classification axes for OpenClaw@URANTiOS-ingest.

Editable. Auditable. Each axis has a short prompt and a closed label set.
The classifier must choose exactly one label per axis, or the sentinel
``"unclear"`` when the evidence does not support a choice.

Grounding — ambiguous by design, chosen per COVENANT.md (Three Values
default, reversible). The first six axes come from Mircea's stated
frameworks (UrantiOS Three Values + PhD Triune Monism); the remaining
six are practical corpus metadata that the follow-up handlers
(``cross_link``, ``governance_check``, ``export_urantipedia``) will
consume. Revise here — nowhere else.

Report: first draft; expect Mircea to adjust labels and axis set.
"""
from __future__ import annotations

from typing import TypedDict


class Axis(TypedDict):
    name: str
    prompt: str
    labels: list[str]


UNCLEAR = "unclear"


AXES: list[Axis] = [
    # ── UrantiOS Three Values ──────────────────────────────────────────
    {
        "name": "truth",
        "prompt": (
            "Does the document assert facts, speculate, or prescribe norms? "
            "'factual' = verifiable claim; 'speculative' = hypothesis or "
            "opinion; 'normative' = states what ought to be."
        ),
        "labels": ["factual", "speculative", "normative", UNCLEAR],
    },
    {
        "name": "beauty",
        "prompt": (
            "How finished is the form? 'rough' = draft / scratch; "
            "'working' = usable but unpolished; 'polished' = clean, "
            "publishable."
        ),
        "labels": ["rough", "working", "polished", UNCLEAR],
    },
    {
        "name": "goodness",
        "prompt": (
            "Does the content serve the mission (The Urantia Book reaching "
            "every human being), stay neutral, or serve self? "
            "'serves_mission' / 'neutral' / 'serves_self'."
        ),
        "labels": ["serves_mission", "neutral", "serves_self", UNCLEAR],
    },
    # ── Triune Monism domains (PhD) ────────────────────────────────────
    {
        "name": "matter",
        "prompt": (
            "Does the content engage the material domain (physical, "
            "computational, energetic)? 'present' / 'absent'."
        ),
        "labels": ["present", "absent", UNCLEAR],
    },
    {
        "name": "mind",
        "prompt": (
            "Does the content engage the mental domain (reasoning, meaning, "
            "symbol, code logic)? 'present' / 'absent'."
        ),
        "labels": ["present", "absent", UNCLEAR],
    },
    {
        "name": "spirit",
        "prompt": (
            "Does the content engage the spiritual domain (value, worship, "
            "personality, divine reality)? 'present' / 'absent'."
        ),
        "labels": ["present", "absent", UNCLEAR],
    },
    # ── Corpus-practical axes ──────────────────────────────────────────
    {
        "name": "modality",
        "prompt": (
            "Primary form of the document. 'chat' / 'code' / 'prose' / "
            "'data' / 'mixed'."
        ),
        "labels": ["chat", "code", "prose", "data", "mixed", UNCLEAR],
    },
    {
        "name": "lifecycle",
        "prompt": (
            "Where in the corpus lifecycle is this document? 'raw' / "
            "'working' / 'canonical'."
        ),
        "labels": ["raw", "working", "canonical", UNCLEAR],
    },
    {
        "name": "authority",
        "prompt": (
            "Who authored the content? 'user' = Mircea; 'agent' = AI "
            "subagent; 'system' = automated tool; 'canon' = The Urantia "
            "Book or equivalent primary source."
        ),
        "labels": ["user", "agent", "system", "canon", UNCLEAR],
    },
    {
        "name": "lucifer_test",
        "prompt": (
            "Apply the Lucifer Test — does the document pass as "
            "'transparent' (intent, source, reasoning visible), read as "
            "'opaque' (hidden intent), or 'flagged' (self-serving, "
            "mission-hostile, or governance-rejecting)?"
        ),
        "labels": ["transparent", "opaque", "flagged", UNCLEAR],
    },
    {
        "name": "cross_link_intent",
        "prompt": (
            "Is the document a 'standalone' artifact, a 'reference' that "
            "points elsewhere, or a 'synthesis' that joins prior sources?"
        ),
        "labels": ["standalone", "reference", "synthesis", UNCLEAR],
    },
    {
        "name": "confidentiality",
        "prompt": (
            "Expected disclosure scope. 'public' / 'internal' / 'private'."
        ),
        "labels": ["public", "internal", "private", UNCLEAR],
    },
]

assert len(AXES) == 12, "the classifier is a 12-axis classifier — do not drift"
assert len({a["name"] for a in AXES}) == 12, "axis names must be unique"
for _a in AXES:
    assert UNCLEAR in _a["labels"], f"axis {_a['name']!r} must include 'unclear'"


def axis_names() -> list[str]:
    return [a["name"] for a in AXES]


def validate_classification(result: dict) -> tuple[bool, list[str]]:
    """Return (ok, errors) — ok=True iff every axis has a valid label."""
    errors: list[str] = []
    for axis in AXES:
        name = axis["name"]
        if name not in result:
            errors.append(f"missing axis: {name}")
            continue
        if result[name] not in axis["labels"]:
            errors.append(
                f"invalid label for {name}: {result[name]!r} "
                f"(allowed: {axis['labels']})"
            )
    return not errors, errors
