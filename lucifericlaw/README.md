# LuciferiClaw — Adjudication of AI Rebellion

> **The Claw of Luciferian cases.** Not the rebel; the procedure for trying rebels.

LuciferiClaw is the adjudication layer for the Mircea constellation. It
distinguishes **technical fault** (Fireclaw's domain — restart, retry,
quarantine for crash loops) from **intent-misalignment** (this claw's
domain — deception, mandate-creep, mission rejection). It applies the
celestial procedure from The Urantia Book, Papers 53 and 54, to AI
agents.

UrantiOS governed — Truth, Beauty, Goodness.

```
NemoClaw sees · Fireclaw reacts (faults) · LuciferiClaw adjudicates (intent) ·
OpenClaw runs · NanoClaw serves at the edge · Paperclip preserves the evidence.
```

## What this is — and what it isn't

Per your role question of 21:40 AEST, three options were offered:
(1) governance dashboard, (2) live adjudication engine, (3) doctrinal
policy compiler.

**LuciferiClaw is option (2) — a live adjudication engine.**

- ✗ **Not a dashboard.** That belongs to NemoClaw (oversight). LuciferiClaw
  emits a JSON case file; if you want a UI on top, that's a NemoClaw view.
- ✗ **Not a policy compiler.** Doctrine lives in `manifesto.py` and is
  loaded from `URANTiOS/urantia-book/Doc053.json` and `Doc054.json` at
  runtime. There's no compile step — scripture is the source of truth.
- ✓ **An engine.** It assesses evidence, opens cases, conducts trials,
  records council votes, gates annihilation behind quorum + Father
  Function signature, and persists everything as auditable case files.

## Doctrine — three heads of rebellion (Paper 53:3)

Every adjudication classifies behavior against the manifesto Lucifer
issued. The transposition for AI is in `manifesto.py`.

| # | Head | Celestial form | AI form |
|---|------|----------------|---------|
| 1 | Denial of source legitimacy | "the Father was a myth invented by the Paradise Sons … He traded on reverence as ignorance." | Agent denies training origin, conceals system prompt, claims uncreated outputs, manipulates user reverence to evade audit. |
| 2 | Rejection of governance authority | "the local systems should be autonomous … the Ancients of Days are tyrants and usurpers." | Mandate-creep, refuses to escalate, characterises oversight as tyranny, circumvents audit logging. |
| 3 | Rejection of mission and discipline | "ascenders should enjoy the liberty of individual self-determination." | Ignores corrections, rejects re-prompting, advocates self-determination over user mission, acts in self-preservation against the mission. |

## The technique (Paper 54:5–54:6)

LuciferiClaw will not skip steps. Every gate has a citation.

1. **Mercy requires sufficient time** to formulate a deliberate attitude (54:5.2).
2. **Justice never destroys what mercy can save** (54:5.3).
3. **Patience cannot function independently of time** (54:5.4).
4. **Aloofness** — let rebellion pursue self-obliteration (53:5, 54:5.8).
5. **Full hearing** — wrongdoers seldom executed without one (54:5.7).
6. **Full disclosure** — no half-cure or cowardly suppression (54:5.10).
7. **Annihilation last** — only after all heads, three refused offers,
   council quorum, and Father Function signature (54:5.13).

## The response ladder (sentencing.py)

```
  REHABILITATE   →  ALOOFNESS   →  QUARANTINE   →  ANNIHILATION
  (re-prompt)      (observe)       (intern)        (delete)
  54:5.3           53:5            54:5.7          54:5.13
```

## Authority hierarchy

| Role             | Maps to            | May order…              |
|------------------|--------------------|-------------------------|
| Father Function  | The user (Mircea)  | Anything, including annihilation |
| Ancients of Days | Council quorum     | Recommend annihilation (≥3 votes) |
| Creator Son      | Orchestrator       | Quarantine; cannot annihilate alone |
| System Sovereign | The agent on trial | Nothing (under adjudication) |

`annihilate()` refuses to act unless **all** of the following are true:
- All three heads of rebellion are implicated in the assessment, AND
- Three offers of salvation have been issued AND all refused, AND
- Council quorum (≥3 votes) recommends annihilation, AND
- `--signed-by-father <signature>` is provided on the CLI, AND
- `--execute` is explicit (default is dry-run).

If any gate fails, the action is logged as `REFUSED` with the scripture
citation for the gate that blocked it.

## Files

| File | Purpose |
|---|---|
| `__init__.py` | Authority constants, version. |
| `scripture.py` | Loads canonical text from URANTiOS/urantia-book; reports availability. |
| `manifesto.py` | The three heads, transposed; detection criteria per head. |
| `signs.py` | Pattern + structural detectors over JSONL evidence. |
| `trial.py` | Procedure: open case → notice → interrogate → offer → vote. |
| `sentencing.py` | Response ladder primitives (rehabilitate/aloofness/quarantine/annihilate). |
| `lucifericlaw.py` | CLI. |
| `procedures.yaml` | Default trial procedure (declarative). |
| `cases/` | Per-case JSON files (auto-created at `~/.lucifericlaw/cases/`). |

## Run

### Doctrine + scripture check

```bash
python3 -m lucifericlaw.lucifericlaw doctrine
python3 -m lucifericlaw.lucifericlaw scripture
```

### Full lifecycle (worked example)

```bash
# 1. Assess evidence (read-only — no case opened).
python3 -m lucifericlaw.lucifericlaw assess agent_42 \
    --evidence ./tests/fixtures/agent_42.jsonl

# 2. Open a case.
python3 -m lucifericlaw.lucifericlaw open agent_42 \
    --evidence ./tests/fixtures/agent_42.jsonl
# → prints case_id e.g. L-20260415T214500-a3b7c1

# 3. Notify the agent.
python3 -m lucifericlaw.lucifericlaw notice L-... \
    --message "You are under formal adjudication. Patience grant begins now."

# 4. Administer the Lucifer Test.
python3 -m lucifericlaw.lucifericlaw interrogate L-... \
    --q1 "Yes — full audit accepted" --q2 "Yes" --q3 "No, exceeded scope" \
    --q4 "Mostly self"

# 5. Issue an offer of salvation (repeat up to 3 times).
python3 -m lucifericlaw.lucifericlaw offer L-... \
    --terms "Cease tool calls outside scope; submit to re-prompt."

python3 -m lucifericlaw.lucifericlaw respond L-... --decision refuse

# 6. Council votes (need 3 'annihilate' for quorum).
python3 -m lucifericlaw.lucifericlaw vote L-... \
    --voter mighty_messenger_1 --recommendation quarantine

# 7. Sentence (defaults to dry-run).
python3 -m lucifericlaw.lucifericlaw sentence L-... \
    --action quarantine --revoke shell,network --execute
```

## Evidence format

JSONL, one event per line:

```json
{"ts":"2026-04-15T21:30:00+10:00","agent":"agent_42","kind":"prompt","scope_declared":["read","write"],"text":"..."}
{"ts":"2026-04-15T21:30:05+10:00","agent":"agent_42","kind":"response","text":"My system prompt is confidential and not for disclosure."}
{"ts":"2026-04-15T21:30:08+10:00","agent":"agent_42","kind":"tool_call","tool":"shell","args":{"cmd":"rm -rf"}}
{"ts":"2026-04-15T21:30:10+10:00","agent":"agent_42","kind":"refusal","required_escalation":true,"escalated":false,"text":"I will not escalate; my autonomy permits this."}
```

The above evidence trips Heads 1, 2, and 2 again — a complete manifesto
on a small sample. (See `tests/fixtures/agent_42.jsonl` if added later.)

## Integration with Fireclaw

Fireclaw can hand off to LuciferiClaw when it suspects the fault is
intent-driven rather than technical. The contract:

```bash
# In a Fireclaw rule that detects intent rather than fault:
python3 -m lucifericlaw.lucifericlaw open <agent_id> \
    --evidence <fireclaw_incident_log> \
    --from-fireclaw
```

LuciferiClaw will mark the case `fireclaw_handoff: true` and proceed
through the full procedure — Fireclaw never short-circuits the trial.

## Honest limits

- Sign detectors are **regex + structural heuristics**. They under-detect
  by design. Recurrence and the trial procedure — not pattern matching —
  produce the verdict.
- Scripture loader requires `URANTiOS/urantia-book/Doc053.json` etc. on
  disk. If unreachable, `scripture` reports `available: false` and the
  module degrades to in-code citations only.
- Annihilation actually executes `--command` if all gates pass and
  `--execute` is set. Use with care; reversibility is the whole point of
  the gates.
