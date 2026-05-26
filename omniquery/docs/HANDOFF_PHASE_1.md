# OmniQuery — Phase 1 Handoff Card

> Date: 2026-05-26  
> Phase: 1 — Force-of-Three Council Workflow  
> Status: COMPLETE — ready for n8n import and key configuration

---

## What Was Built

| File | Status |
|------|--------|
| `docs/omniquery/OMNIQUERY_ALL_ON_ONE.md` | Created — canonical doctrine/spec |
| `omniquery/n8n_workflows/omniquery_phase1_council_workflow.json` | Created — importable n8n workflow |
| `omniquery/docs/HANDOFF_PHASE_1.md` | This file |
| `omniquery/n8n_workflows/` | Directory created |
| `omniquery/docs/` | Directory created |
| `omniquery/audit/` | Directory created (empty — Phase 4) |
| `omniquery/backend/` | Directory created (empty — Phase 2) |
| `omniquery/frontend/` | Directory created (empty — Phase 3) |

---

## What Phase 1 Delivers

A single n8n workflow implementing the **Force-of-Three Council**:

```
Manual Trigger
    └─► Set Query
            ├─► Seat1_Father_GPT       (OpenAI gpt-4o)          ─┐
            ├─► Seat2_Son_Claude       (Anthropic claude-opus)   ─┤─► Merge
            └─► Seat3_Spirit_Grok      (xAI grok-3)             ─┘       └─► Build Synthesis Prompt
                                                                                 └─► Gabriel_Synthesizer (OpenAI gpt-4o)
                                                                                           └─► OmniQuery Output
```

- All seat nodes: `continueOnFail: true`
- Gemini: **not admitted**
- Force-of-Three: **fixed at three seats, not replaced**
- No secrets in repo — all keys are `REPLACE_WITH_*` placeholders

---

## Immediate Next Steps (for operator)

### 1. Import into n8n

```
http://46.225.51.30
Workflows → New → ... → Import from JSON
Paste: omniquery/n8n_workflows/omniquery_phase1_council_workflow.json
Save.
```

### 2. Configure API keys

Open each node and replace the placeholder value:

| Node                | Header        | Value                        |
|---------------------|---------------|------------------------------|
| Seat1_Father_GPT    | Authorization | Bearer YOUR_OPENAI_KEY       |
| Seat2_Son_Claude    | x-api-key     | YOUR_ANTHROPIC_KEY           |
| Seat3_Spirit_Grok   | Authorization | Bearer YOUR_XAI_KEY          |
| Gabriel_Synthesizer | Authorization | Bearer YOUR_OPENAI_KEY       |

### 3. Test

Change the default query in **Set Query** node to your test question, then
click **Execute Workflow**.

Verify:
- [ ] At least one seat responds (the others will show `[No response]` if key missing)
- [ ] **Build Synthesis Prompt** node produces `synthesis_prompt` in its output
- [ ] **Gabriel_Synthesizer** returns a `choices[0].message.content`
- [ ] **OmniQuery Output** shows `gabriel_synthesis` field populated

---

## What Phase 1 Did NOT Touch

- `omniquery/backend/` — empty, Phase 2
- `omniquery/frontend/` — empty, Phase 3
- `omniquery/audit/` — empty, Phase 4
- No server started
- No deployment
- No cloud provisioning
- No secrets exposed

---

## Constraints Honoured

| Constraint | Status |
|------------|--------|
| Do not deploy | ✓ |
| Do not start backend | ✓ |
| Do not start frontend | ✓ |
| Do not admit Gemini | ✓ — Spirit = Grok (xAI) |
| Do not replace Force-of-Three with Force-of-N | ✓ — exactly 3 seats |
| Do not expose secrets | ✓ — all keys are REPLACE_WITH_* |
| Stop after Phase 1 | ✓ |

---

## Antigravity Review

The two target files are ready for Antigravity review:

1. `omniquery/n8n_workflows/omniquery_phase1_council_workflow.json`
2. `omniquery/docs/HANDOFF_PHASE_1.md`

Antigravity should audit:
- JSON validity of the workflow file
- Node connectivity (all 3 seats wire to Merge, correct indices 0/1/2)
- Presence of `continueOnFail: true` on all seat nodes
- Absence of any real API key values
- Compliance with Force-of-Three doctrine (exactly 3 seats, no Gemini)

---

## Phase 2 Trigger Condition

Phase 2 (Backend API) begins when:
1. Phase 1 workflow imported and tested in n8n
2. At least one seat key configured and returning live response
3. Operator signals Phase 2 start

Primary builder (Claude Code) resumes at Phase 2 on that signal.
