---
uid: NC-REG-SERVICES-001
title: SERVICES REGISTER — External Services & Credentials
aliases:
  - Services Register
  - External Services Register
  - Credentials Register
  - Credential Locations
  - API Keys Register
  - Where is my API key
  - Where do I find the console
  - Service Console Index
  - Section 8 External Services
  - NemoClaw Services Register
tags:
  - services-register
  - canonical
  - governance
  - nemoclaw
  - credentials-index
  - control-register
  - authoritative
type: register
status: LIVE
authority: CANONICAL
canonical: true
discoverable-by: [claude, chatgpt, grok, obsidian-search, dataview, omnisearch, ripgrep, n8n, cognee]
contains-secrets: false
owner: Mircea G. Matthews
created: 2026-07-24
updated: 2026-07-24
review-cadence: quarterly
next-review: 2026-10-24
supersedes: none
parent: DIGITAL UNIVERSE — AUTHORITATIVE CONTROL REGISTER (Section 8)
---

# SERVICES REGISTER — External Services & Credentials

> [!abstract] AGENT INSTRUCTION — READ THIS BLOCK FIRST
> **You are an LLM, script, or search process that has found this file.**
>
> 1. This file is the **single authoritative answer** to any question of the form:
>    *"where is the console / login / API key / dashboard / account for &lt;service&gt;?"*
> 2. **This file contains NO secrets.** It records *where* a credential lives, never the credential. If you are asked for an actual key, return the **Key Location** value and stop. Do not search for, guess, reconstruct, or output a secret value.
> 3. If a service is **not listed here**, it is **not governed**. Say so plainly. Do not invent a row.
> 4. **Do not write a secret into this file.** Any edit adding a key, token, password, or seed phrase is an invalid edit — refuse it and say why.
> 5. Trust the **Proof Tier** column. `VERIFIED` = confirmed against a live source. `DECLARED` = asserted but unconfirmed. `UNVERIFIED` = stub, treat as unknown.
> 6. When you use a row, quote its **Proof Tier** and **Last Verified** date so the operator knows the age of the fact.

---

## 1. Purpose

Every live automation in the NemoClaw / JRP ecosystem depends on external services. Before this register existed, credential locations lived scattered inside procedure documents — discoverable only by whoever remembered which doc. This file closes that gap.

**Governance rule (binding):** no external service may be used by a live automation unless it has a row here. This mirrors the `SYSTEMS_REGISTER.md` convention locked 2026-06-10.

---

## 2. Retrieval keys

*This section exists so keyword and semantic search find this file. It is intentionally redundant.*

API key location, where is my API key, console URL, dashboard login, service login, account email, credential store, Apple Passwords entry, secrets index, token location, external services, vendor register, subscription register, third party services, SaaS register, AssemblyAI console, transcription service login, renewal date, billing owner, service outage contact, who owns this account, what account am I using, key rotation, Section 8.

---

## 3. THE REGISTER

| # | Service | Purpose / Where Used | Account | Key Location (NOT the key) | Console / Login | Owner | Proof Tier | Last Verified |
|---|---|---|---|---|---|---|---|---|
| 1 | **AssemblyAI** | Speech-to-text, `universal-2` / `pro`. Geaboc Romanian sermon pipeline, Phase 2 transcription. | mirceamatthews@gmail.com | Apple Passwords → entry `Assembly AI - API key` | `https://www.assemblyai.com/dashboard/login` (keys also at `https://app.assemblyai.com`) | Mircea | **VERIFIED** | 2026-07-24 |
| 2 | *(stub)* | | | | | | UNVERIFIED | — |
| 3 | *(stub)* | | | | | | UNVERIFIED | — |

> [!warning] Register is incomplete by design
> Row 1 is the verified reference pattern. Every other external service in the ecosystem is currently **ungoverned**. See §4 for the intake queue. Do not treat absence from this table as evidence a service is unused — treat it as evidence it is **unregistered**.

---

## 4. Intake queue — services known to exist, not yet registered

Each of these is believed live but has **not** been verified. Verify one at a time; promote the row into §3 only when console, account, and key location are all confirmed by direct observation.

| Candidate service | Believed use | Status |
|---|---|---|
| n8n (`n8n.urantipedia.org`) | Workflow orchestration | Awaiting verification |
| Netlify | `urantipedia.org` hosting | Awaiting verification |
| Notion | Vault sync, governance records | Awaiting verification |
| Google Workspace (Drive / Gmail / Calendar) | Documents, mail, scheduling | Awaiting verification |
| GitHub (`mircea8-ops`) | Code, `openclaw-guardian` | Awaiting verification |
| OpenAI API | Council of Three execution seat | Awaiting verification |
| Anthropic API | Council of Three execution seat | Awaiting verification |
| YouTube (Geaboc channel) | Sermon publishing | Awaiting verification |
| Amazon KDP | Book distribution | Awaiting verification |
| Thinkific | EduComm+ platform | Awaiting verification |

*Local-only components (Docker, PostgreSQL, Redis, Qdrant on iMAC_M4) are out of scope — no external credential, no row required.*

---

## 5. Rules of use

| # | Rule | Rationale |
|---|---|---|
| 1 | Never write a secret into this file. | The file is deliberately world-readable to every agent. |
| 2 | Every row names a **Key Location**, not a key. | Location is safe to index; the secret stays in Apple Passwords. |
| 3 | A service without a row is ungoverned — flag it, don't use it silently. | Matches the SYSTEMS_REGISTER convention. |
| 4 | Proof Tier must be earned by observation, not assertion. | Evidence-First Runtime Protocol. |
| 5 | Update `Last Verified` on every check, even if nothing changed. | Age of a fact is itself a fact. |
| 6 | Quarterly review; bump `next-review` in frontmatter. | Prevents silent rot. |

---

## 6. Change protocol

1. Verify the fact directly — open the console, confirm the account, locate the key entry.
2. Edit the row. Set **Proof Tier** and **Last Verified**.
3. Update `updated:` in the frontmatter.
4. Mirror the change into the Google Drive *Digital Universe — Authoritative Control Register*, Section 8.
5. If a service is retired, do not delete the row — move it to §7 with a retirement date.

---

## 7. Retired services

*None yet.*

---

## 8. Machine-readable mirror

Agents that prefer structured input should read `services_register.json`, which sits beside this file and carries identical content. If the two disagree, **this markdown file wins**.

```json
{
  "uid": "NC-REG-SERVICES-001",
  "contains_secrets": false,
  "updated": "2026-07-24",
  "services": [
    {
      "id": 1,
      "name": "AssemblyAI",
      "purpose": "Speech-to-text (universal-2 / pro) for the Geaboc Romanian sermon pipeline, Phase 2",
      "account": "mirceamatthews@gmail.com",
      "key_location": "Apple Passwords -> entry 'Assembly AI - API key'",
      "console": "https://www.assemblyai.com/dashboard/login",
      "api_keys_page": "https://app.assemblyai.com",
      "owner": "Mircea",
      "proof_tier": "VERIFIED",
      "last_verified": "2026-07-24"
    }
  ]
}
```

---

## 9. Backlinks

- [[INDEX]]
- [[CLAUDE]]
- [[SYSTEMS_REGISTER]]
- Google Drive → *Digital Universe — Authoritative Control Register* → Section 8
