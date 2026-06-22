# OmniQuery Model-ID Check — YYYY-MM-DD (TEMPLATE)

> Copy this file to `model_id_checks/YYYY-MM-DD.md` for a manual check, or let
> `../scripts/check_model_ids.py` generate it automatically.
>
> Verdict vocabulary: **PASS** / **NEEDS_REVIEW** / **BLOCKED**
> (see `MODEL_ID_POLICY.md`).

> Verdict: **<PASS | NEEDS_REVIEW | BLOCKED>**
> Mode: <online | offline>
> Checked by: <script | name>
> Sources config version: <n>

## Infrastructure Availability — 2026-05-26

### Hetzy / Hetzner

- Status: `OFFLINE / NOT SUBSCRIBED`
- Allowed use: none
- Replacement: local iMac / NemoClaw / local launchd / ChatGPT scheduled check / manually approved future host
- Action: remove from active routing and scheduling assumptions

Historical cron-on-hetzy/urantios references are disabled/deprecated. This
daily check must not assume Hetzner, remote cron, or remote deploy capability.

Lineages are doctrine; exact model IDs are mutable configuration. This check
detects only — it never patches and never calls a provider API.

## Seat results

| Seat | Provider | Model ID | Verdict |
|------|----------|----------|---------|
| Father | OpenAI | `gpt-4o` | <verdict> |
| Son | Anthropic | `claude-opus-4-7` | <verdict> |
| Spirit | xAI | `grok-4.3` | <verdict> |
| Gabriel | OpenAI | `gpt-4o` | <verdict> |

### Seat notes

- **Father (`gpt-4o`)** — <verdict>
  - <note>
- **Son (`claude-opus-4-7`)** — <verdict>
  - <note>
- **Spirit (`grok-4.3`)** — <verdict>
  - <note>
- **Gabriel (`gpt-4o`)** — <verdict>
  - <note>

## Forbidden-ID checks

- Configured seats using a forbidden/retired ID: <none | list>
- Retired/forbidden IDs found in repo artifacts: <none | list with file paths>

## What to do

- PASS → no action.
- NEEDS_REVIEW → confirm flagged IDs against live provider docs before any
  import, live test, or deployment.
- BLOCKED → do not import/test/deploy. Patch only after explicit Mircea
  approval (e.g. `SPIRIT MODEL UPDATE GO`).

_No API keys read. No provider API called. No files patched._
