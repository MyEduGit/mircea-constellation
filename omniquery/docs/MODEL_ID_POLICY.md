# OmniQuery — Model ID Policy

> Date: 2026-05-26
> Status: ACTIVE
> Applies to: n8n workflow, backend, frontend, docs, and any live test or deployment

This policy governs how model identifiers are treated across OmniQuery.
It is subordinate to `COVENANT.md` and the OmniQuery doctrine
(`docs/omniquery/OMNIQUERY_ALL_ON_ONE.md`), and to Mircea as approval gate.

---

## 1. Lineages are doctrine

The **Force-of-Three** seats and their providers are doctrine, not
configuration:

| Seat | Lineage | Provider |
|------|---------|----------|
| Father | GPT | OpenAI |
| Son | Claude | Anthropic |
| Spirit | Grok | xAI |
| Gabriel | GPT (synthesis) | OpenAI |

A lineage may **not** be changed, removed, or swapped (e.g. admitting Gemini,
replacing Grok, or expanding to Force-of-N) without an **explicit doctrine
change from Mircea**. The watchdog and any patch process must preserve the
Force-of-Three.

## 2. Exact model IDs are mutable configuration

The exact string used to call a provider (`gpt-4o`, `claude-opus-4-7`,
`grok-4.3`, …) is **configuration**, not doctrine. Providers retire, rename,
and re-version models. Model IDs are expected to change over time **within a
fixed lineage**. Updating an exact ID is a configuration change; changing a
lineage is a doctrine change.

## 3. Model IDs must be checked before import, live test, or deployment

No model ID may be used in any of the following without a passing
verification on or after the relevant action date:

- Importing or editing the n8n workflow.
- Running a live provider call (backend or n8n).
- Any deployment.

A model ID that has not been verified within its review window is treated as
**unverified** and must not be promoted to live use.

## 4. Retired aliases are forbidden — even when providers redirect them

A model ID that a provider has **retired** must **not** remain in any
artifact, even if the provider silently redirects the old slug to a
replacement. Redirects:

- change pricing without notice,
- change behaviour, context window, and quality without notice,
- hide the true model being called.

Configuration must always name the **actual** model in use. Retired slugs are
**forbidden** in n8n, backend, frontend, docs, and tests.

## 5. Silent redirects are audit failures

If verification shows that a configured ID is being silently redirected to a
different model (e.g. `grok-3` → `grok-4.3`), this is an **audit failure**,
not an acceptable state. The check must return `BLOCKED` and the ID must be
corrected to name the real target explicitly before any live use.

## 6. Patches preserve the Force-of-Three

Any model ID patch:

- must keep the same **seat lineage** (Father→GPT, Son→Claude, Spirit→Grok,
  Gabriel→GPT),
- must not admit a new provider or seat,
- must not reduce or expand the council below or beyond three voices plus
  Gabriel,

unless Mircea **explicitly** changes the doctrine in writing.

## 7. Change gate

The watchdog **detects and reports only**. It never auto-patches. Any change
to a model ID in config, workflow JSON, frontend, or docs requires an explicit
approval signal from Mircea (e.g. `SPIRIT MODEL UPDATE GO`). Until then,
findings are recorded and the affected artifact is treated as blocked for
live use.

---

## Verdict vocabulary

| Verdict | Meaning | Allowed to go live? |
|---------|---------|---------------------|
| **PASS** | All configured IDs confirmed current at their official source; none forbidden; no silent redirect. | Yes (subject to Mircea gate). |
| **NEEDS_REVIEW** | An ID could not be confirmed (doc changed, page unreachable, ID missing from docs, or near a review deadline). Human review required. | No, until reviewed. |
| **BLOCKED** | A configured ID is retired, deprecated, silently redirected, or otherwise invalid. | No. Must be corrected. |

---

## Scheduling the daily check

The watchdog runs **daily**, **never auto-patches**, and **notifies Mircea**
only when the verdict is `NEEDS_REVIEW` or `BLOCKED`. A `PASS` may run silently.
Any resulting model-ID change is applied **only after explicit Mircea approval**.

Pick one runner. All are key-free and call only the public docs.

### macOS — launchd (recommended on the iMac)

`~/Library/LaunchAgents/com.omniquery.modelid.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.omniquery.modelid</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/path/to/mircea-constellation/omniquery/scripts/check_model_ids.py</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/tmp/omniquery-modelid.out</string>
  <key>StandardErrorPath</key><string>/tmp/omniquery-modelid.err</string>
</dict>
</plist>
```

Load: `launchctl load ~/Library/LaunchAgents/com.omniquery.modelid.plist`

### Linux — cron (e.g. on hetzy/urantios)

```cron
# Daily 09:00 — detect only, never patch. Exit 1=NEEDS_REVIEW, 2=BLOCKED.
0 9 * * * cd /path/to/mircea-constellation && /usr/bin/python3 omniquery/scripts/check_model_ids.py || \
  printf 'OmniQuery model-ID check needs attention (exit %s)\n' "$?" | \
  mail -s "OmniQuery model-ID: NEEDS_REVIEW/BLOCKED" mircea8@me.com
```

### n8n (Schedule Trigger → Execute Command → IF → notify)

1. **Schedule Trigger**: every day at 09:00.
2. **Execute Command**: `python3 omniquery/scripts/check_model_ids.py` (capture exit code).
3. **IF**: exit code `!= 0`.
4. **Notify**: send the dated report (`omniquery/docs/model_id_checks/YYYY-MM-DD.md`)
   to Mircea (email / Slack). **No patch node. No deploy node.**

> Notify-only by design. A `NEEDS_REVIEW`/`BLOCKED` result must never trigger
> an automatic edit to config, workflow JSON, frontend, or docs.

---

## Related files

| File | Purpose |
|------|---------|
| `MODEL_ID_REGISTRY.md` | Source-of-truth table of seat → model ID → status. |
| `model_id_sources.json` | Official source URLs + the IDs the checker validates. |
| `../scripts/check_model_ids.py` | Daily, key-free verification script. |
| `MODEL_ID_DAILY_CHECK_TEMPLATE.md` | Template for a manual/automated daily report. |
| `model_id_checks/YYYY-MM-DD.md` | Timestamped check reports (written by the script). |
| `MODEL_ID_VERIFICATION.md` | The 2026-05-26 point-in-time verification that seeded this system. |
