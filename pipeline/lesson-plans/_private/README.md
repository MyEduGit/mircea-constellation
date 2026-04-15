# `_private/` — local-only coordinator scratch

This folder is **gitignored** by design (see `.gitignore` in this folder).
Anything inside never reaches the remote. Use it for quick-links that
embed aXcelerate IDs, learner identifiers, or any other data that should
not leave Mircea's workstation.

Committed public-scope docs live one level up (`SOURCES.md`,
`GOVERNANCE.md`, `COMPLIANCE.md`). The bridge from aXcelerate → pipeline
is the anonymised `templates/cohort.schema.yaml` — not the files in this
folder.
