# OmniQuery — Governance Rules

> These rules govern all phases of OmniQuery. They are inherited by every builder and reviewer.

---

## The Seven Governance Rules

1. **No claim without proof.** Gabriel synthesizes only from seats that actually responded.
2. **Continue on fail.** Any seat that errors is bypassed, not fatal. The query still completes.
3. **Gemini is not admitted.** Spirit = Grok (xAI). Do not swap Spirit to Gemini for any reason.
4. **Force-of-Three is fixed at three.** Do not add seats. Do not replace with Force-of-N.
5. **No secrets in repo.** All API key values are `REPLACE_WITH_*` placeholders. Never commit a real key.
6. **Gabriel speaks last.** No additional synthesis layer above Gabriel. He is the final voice.
7. **Phases are sequential.** Phase 2 does not begin until Phase 1 is verified. You = approval gate.

---

## Approval Gate

You (mircea8) are the approval gate. No phase begins without your signal.

```
Phase 1 complete → you approve → Phase 2 begins
Phase 2 complete → you approve → Phase 3 begins
Phase 3 complete → you approve → Phase 4 begins
```

Claude Code does not self-advance between phases.

---

## Builder Roles

| Role | Identity | Scope |
|------|----------|-------|
| Primary builder | Claude Code | All implementation |
| Secondary builder | Antigravity | Review only — no file edits without explicit approval |
| Approval gate | mircea8 | Phase transitions, architectural decisions |
| Synthesizer | Gabriel (in-workflow) | Runtime only |

---

## What Antigravity Reviews For

When Antigravity reviews a Phase 1 deliverable, it checks for:

- Duplicate work
- Schema drift from `COUNCIL_SCHEMA_v1.json`
- Accidental Gemini admission
- Force-of-N introduction (more than 3 seats)
- Secrets or credential exposure
- Browser storage of secrets
- Missing audit log (Phase 4 concern — flag only)
- Missing Gabriel Gate approval point
- Missing "stop after Phase 1" constraint
- Deployment attempted too early

Antigravity returns notes only. It does not modify files unless explicitly asked by mircea8.

---

## API Key Security

- Keys are configured **inside n8n** — not in the repo.
- n8n stores credentials in its encrypted credential store.
- Never paste a key into any `.md`, `.json`, `.env`, or `.txt` file in this repo.
- The `.gitignore` excludes `.env` files — do not bypass this.

---

## Doctrine Locks

The following are locked and cannot be changed without mircea8 approval:

| Lock | Value |
|------|-------|
| Spirit seat model | Grok (xAI grok-3) |
| Synthesizer | Gabriel (OpenAI gpt-4o) |
| Seat count | 3 (Force-of-Three) |
| Merge mode | append |
| Execution order | v1 |
| Gemini | Not admitted |
