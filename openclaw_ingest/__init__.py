"""OpenClaw@URANTiOS-ingest — execution runtime (ingestion sub-role).

Singular primary role: controlled execution. Does not observe (NemoClaw),
does not remediate (Fireclaw), does not adjudicate (LuciferiClaw), does
not explain (VisualUrantiClaw), does not bundle evidence (Paperclip —
this module emits evidence records, but Paperclip owns the bundling
contract once it ships).

Truthful label: all five canonical handlers implemented —
``ingest_normalize``, ``categorise_by_axes``, ``cross_link``,
``governance_check``, ``export_urantipedia`` (plus ``smoke_test`` for
bootstrap).

UrantiOS governed — Truth, Beauty, Goodness.
"""

__version__ = "0.1.0"
