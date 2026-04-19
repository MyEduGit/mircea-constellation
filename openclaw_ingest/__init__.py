"""OpenClaw@URANTiOS-ingest — execution runtime (ingestion sub-role).

Singular primary role: controlled execution. Does not observe (NemoClaw),
does not remediate (Fireclaw), does not adjudicate (LuciferiClaw), does
not explain (VisualUrantiClaw), does not bundle evidence (Paperclip —
this module emits evidence records, but Paperclip owns the bundling
contract once it ships).

Truthful label: deployable scaffold with two real handlers
(``ingest_normalize`` and ``categorise_by_axes``). Three of the five
canonical handlers remain declared-but-stubbed pending follow-up PR.

UrantiOS governed — Truth, Beauty, Goodness.
"""

__version__ = "0.1.0"
