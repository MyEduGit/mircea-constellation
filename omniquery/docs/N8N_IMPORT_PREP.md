# OmniQuery — n8n Import Prep

> Date: 2026-05-26
> Scope: preparation only
> Status: NOT IMPORTED / NOT ACTIVATED / NOT DEPLOYED

This note prepares the existing Phase 1 workflow JSON for a future manual n8n
import. It does **not** authorize import, activation, deployment, or live use.

---

## What Was Reviewed

Reviewed file:

- `omniquery/n8n_workflows/omniquery_phase1_council_workflow.json`

Verified from the JSON:

- Workflow name: `OmniQuery Phase 1 — Force-of-Three Council`
- Trigger type: `n8n-nodes-base.manualTrigger`
- No webhook trigger present
- No cron/schedule trigger present
- No production activation metadata present
- `triggerCount` is `0`
- Force-of-Three is preserved:
  - Father = OpenAI / `gpt-4o`
  - Son = Anthropic / `claude-opus-4-7`
  - Spirit = xAI / `grok-4.3`
  - Gabriel synthesis = OpenAI / `gpt-4o`
- Gemini is **not** admitted
- No real secrets are present in the JSON; only placeholders are present:
  - `REPLACE_WITH_OPENAI_API_KEY`
  - `REPLACE_WITH_ANTHROPIC_API_KEY`
  - `REPLACE_WITH_XAI_API_KEY`

---

## Credential Checklist

Required before any live manual run:

- OpenAI API credential for:
  - Father seat
  - Gabriel synthesizer
- Anthropic API credential for:
  - Son seat
- xAI API credential for:
  - Spirit seat

Recommended n8n-side handling:

- Do **not** leave literal bearer tokens embedded in node headers.
- Replace placeholder header values with n8n-managed credentials or approved
  env-backed expressions before any live test.
- Store credentials only inside n8n’s credential store or another approved
  secret manager.
- Re-check that exported workflow JSON does not contain live secrets after
  credential attachment.

Required future change before live use:

- Convert the current placeholder header fields into credential-backed values.
  This is a configuration/security change, not a Force-of-Three logic change.

---

## Model ID Verification Checklist

Verify these model IDs before any live manual test:

- OpenAI Father seat: `gpt-4o`
- Anthropic Son seat: `claude-opus-4-7`
- xAI Spirit seat: `grok-4.3`
- OpenAI Gabriel synthesis: `gpt-4o`

Specific caution:

- `claude-opus-4-7` was already marked provisional elsewhere in OmniQuery.
  Confirm it is valid in the target Anthropic account before live execution.

Recommended pre-import verification:

- Confirm each provider account has access to the intended model.
- Confirm billing / quota / org access is enabled.
- Confirm request shape matches each provider’s current API contract.
- If any model ID must change, preserve the Force-of-Three seat mapping:
  - Father remains OpenAI
  - Son remains Anthropic
  - Spirit remains xAI
  - Gabriel remains synthesizer, not a fourth council seat

---

## Manual Import Steps

1. Open a non-production n8n workspace.
2. Import `omniquery/n8n_workflows/omniquery_phase1_council_workflow.json`.
3. Confirm the imported workflow is still manual-trigger only.
4. Confirm the workflow is not active after import.
5. Replace placeholder auth headers with n8n-managed credentials.
6. Re-check all four model IDs before any run.
7. Re-check that Gemini is not present anywhere in the imported workflow.
8. Re-check that the council structure is still Father / Son / Spirit plus Gabriel synthesis.
9. Use a single harmless short prompt for the first live manual test.
10. Do not activate the workflow for background or production execution.

---

## Rollback Steps

If anything looks wrong during import prep or after a manual import:

1. Do not activate the workflow.
2. Remove attached credentials from the imported workflow.
3. Delete the imported workflow from the n8n workspace.
4. Confirm no webhook, schedule, or active execution remains.
5. Re-import only after the issue is documented and approved.

If a live manual test is attempted later and fails:

1. Disable or delete the imported workflow immediately.
2. Revoke or rotate credentials if secret exposure is suspected.
3. Preserve logs/screenshots for audit review.
4. Do not move to Phase 4 or deployment based on a failed or ambiguous run.

---

## Live Test Prompt Proposal

Use one short harmless prompt only:

`What is truth?`

Why:

- Minimal token cost
- Easy to inspect across all three seats
- Consistent with existing OmniQuery examples

---

## Security Warnings

- The current workflow JSON contains credential **placeholders**, not live secrets.
- Those placeholders are inside HTTP header fields, so live credentials must not
  be pasted into version-controlled JSON and re-committed.
- Import into a non-production n8n workspace only.
- Keep the workflow manual-trigger only.
- Do not add webhooks, schedules, or auto-activation during import prep.
- Do not admit Gemini.
- Do not replace Force-of-Three with another topology.
- Do not treat import success as production readiness.

---

## Gabriel Gate Approval Requirement

Before any future live manual n8n run, require explicit gate approval:

- Gabriel Gate requirement: **approved**
- Required approver: Mircea
- Minimum preconditions:
  - Credentials attached safely in n8n
  - Model IDs verified
  - Manual-trigger only confirmed
  - Workflow inactive confirmed
  - No Gemini admission confirmed
  - Force-of-Three preserved confirmed

Without explicit Mircea approval, stop at prep only.

---

## Current Conclusion

- Workflow reviewed: **yes**
- Manual-trigger only: **yes**
- No secrets present in JSON: **yes**
- Gemini admitted: **no**
- Force-of-Three preserved: **yes**
- Import performed: **no**
- Activation performed: **no**
- Deployment performed: **no**

