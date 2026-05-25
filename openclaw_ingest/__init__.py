"""OpenClaw@URANTiOS-ingest — execution runtime (ingestion sub-role).

Singular primary role: controlled execution. Does not observe (NemoClaw),
does not remediate (Fireclaw), does not adjudicate (LuciferiClaw), does
not explain (VisualUrantiClaw), does not bundle evidence (Paperclip —
this module emits evidence records, but Paperclip owns the bundling
contract once it ships).

Handlers (all real, none stubbed):
  ingest_normalize     — normalise chatcode JSONL into Cognee
  ingest_obsidian      — ingest Obsidian vault .md files into Cognee
  categorise_by_axes   — 12-axis LLM classifier (Ollama)
  cross_link           — pair-score edge emission
  governance_check     — apply governance rules, flag iniquitous docs
  export_urantipedia   — export eligible docs as Obsidian-ready markdown
  subscription_*       — subscribe / unsubscribe / list (3 handlers)

UrantiOS governed — Truth, Beauty, Goodness.
"""

__version__ = "0.2.0"
