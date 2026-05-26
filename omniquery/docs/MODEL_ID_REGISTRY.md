# OmniQuery — Model ID Registry

> Date: 2026-05-26
> Status: ACTIVE — source of truth for which exact model ID each seat uses
> Governed by: `MODEL_ID_POLICY.md`

Lineages are doctrine (see `MODEL_ID_POLICY.md` §1). The exact IDs below are
**configuration** and are expected to change over time within each lineage.
This table is authoritative; `model_id_sources.json` mirrors it for the
checker.

---

## Registry

| Seat | Provider | Current model ID | Status | Source URL | Last verified | Next review | Replacement candidate | Action needed |
|------|----------|------------------|--------|------------|---------------|-------------|-----------------------|---------------|
| Father | OpenAI | `gpt-4o` | valid (API) | https://developers.openai.com/api/docs/models | 2026-05-26 | 2026-06-25 | `gpt-4.1` (future) | None — monitor API deprecation schedule |
| Son | Anthropic | `claude-opus-4-7` | valid — account-check before live use | https://docs.anthropic.com/en/docs/about-claude/models | 2026-05-26 | 2026-06-25 | `claude-opus-4-6` (fallback) | Confirm account has Opus 4.7 access before first live call |
| Spirit | xAI | `grok-4.3` | valid — replacement for retired `grok-3` | https://docs.x.ai/developers/models/grok-4.3 | 2026-05-26 | 2026-06-25 | `grok-4-0709` (fallback) | Patch `grok-3` → `grok-4.3` in config/workflow once Mircea approves |
| Gabriel | OpenAI | `gpt-4o` | valid (API) | https://developers.openai.com/api/docs/models | 2026-05-26 | 2026-06-25 | `gpt-4.1` (future) | None — monitor API deprecation schedule |

---

## Forbidden / retired IDs (must never appear in any artifact)

| Model ID | Provider | Reason | Retired | Redirects to |
|----------|----------|--------|---------|--------------|
| `grok-3` | xAI | Retired; silently redirects, hiding true model and cost | 2026-05-15 | `grok-4.3` |
| `grok-3-mini` | xAI | Retired in the same batch | 2026-05-15 | `grok-4.3` |
| `claude-opus-4-5-20251001` | Anthropic | Provisional ID used in early drafts; superseded | — | n/a (use `claude-opus-4-7`) |

> The `claude-opus-4-5-20251001` row records a historical drafting artifact
> caught during Phase 1; the canonical Opus 4.5 snapshot is
> `claude-opus-4-5-20251101`. Neither is the seat's current ID.

---

## Status legend

- **valid (API)** — confirmed available via the provider API at the source URL.
- **valid — account-check before live use** — ID is correct; access depends
  on the calling account/tier; verify entitlement before first live call.
- **valid — replacement for retired X** — current correct ID that supersedes
  a retired one; config patch still pending Mircea approval.
- **retired / deprecated** — must not be used; see forbidden table.

---

## Change log

| Date | Change |
|------|--------|
| 2026-05-26 | Registry created. Spirit recorded as `grok-4.3` (retired `grok-3` moved to forbidden). Son provisional flag cleared to "account-check before live use". |
