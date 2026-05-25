"""Paperclip — evidence bundler.

Canonical role: evidence preservation. Collects evidence records emitted
by every claw on each handler invocation and bundles them into structured,
auditable, tamper-evident packages.

Canonical claw map:
    NemoClaw sees · Fireclaw reacts · LuciferiClaw adjudicates ·
    OpenClaw runs · NanoClaw serves at the edge ·
    Paperclip preserves the evidence.

Paperclip does not execute media pipelines (ScribeClaw), does not observe
(NemoClaw), does not remediate (Fireclaw), does not adjudicate
(LuciferiClaw). Its singular purpose: receive, verify, and bundle the
evidence trail produced by every other claw so that every handler
invocation across the constellation is auditable and provable.

Evidence records are JSON files written by each claw to its own
/data/evidence/ directory. Paperclip mounts one or more of those
directories (configured via EVIDENCE_DIRS), sweeps them, and bundles
matching records into tamper-evident JSON packages under /data/bundles/.

Bundle integrity: each bundle carries the SHA-256 of its own canonical
content, enabling downstream verification without trusting the filename.

UrantiOS governed — Truth, Beauty, Goodness.
"""

__version__ = "0.1.0"
