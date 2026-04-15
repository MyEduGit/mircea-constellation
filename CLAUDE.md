# Repo conventions — mircea-constellation

Durable rules for every Claude Code session working in this repository.

## Knowledge distribution (Mircea's standing rule)

**Every substantive artefact produced in a session must be placed where it
belongs across Mircea's knowledge graph** — not just here.

Canonical destinations:

| Destination | What lands there | How |
|---|---|---|
| This repo (`mircea-constellation`) | Pipelines, generators, schemas, compliance docs, node graph | git commit + push to the branch specified for the session |
| **Obsidian vault** (iMac + Hetzner, 477+ docs) | Human-readable analyses, session narratives, linking notes | Mirror the repo's user-facing `.md` (README, GOVERNANCE, COMPLIANCE, SOURCES, CHANGELOG) into the vault via the existing rsync bridge — standard GFM + frontmatter is Obsidian-compatible as-is |
| Other topical repos | Code / configs that are out-of-scope for the constellation repo | Raise to Mircea; do **not** push to repos not listed in the session brief |

Operational rule of thumb: when you ship work here, check whether the same
artefact (or a summary of it) also belongs in the Obsidian vault. If yes,
either format it so the next vault rsync picks it up, or flag it in your
user-facing summary so Mircea can copy it manually.

## Privacy / PII

Real learner identifiers (names, DOBs, phones, CHESSN, USI, aXcelerate
ContactID, addresses) **must never** be committed. The `_private/` folder
in `pipeline/lesson-plans/` is the only place coordinator quick-links with
embedded IDs may live — it is gitignored. The bridge between aXcelerate
(authenticated SMS) and the public pipeline is
`pipeline/lesson-plans/templates/cohort.schema.yaml`, which carries
aggregate profile only.

Obligations: *Privacy Act 1988* (Cth) APPs, *Privacy and Data Protection
Act 2014* (Vic), AMEP Deed of Standing Offer data-handling clauses.

## Branch policy

Each session is assigned a development branch in the session brief. All
commits land on that branch; never push to `main` without explicit user
authorisation. Prefer new commits over amends.
