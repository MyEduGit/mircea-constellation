# LuciferiClaw: A Procedural Adjudication Framework for AI Intent Misalignment

**Mircea [surname]**
PhD candidate, Philosophy of Religion
[University/Institution]
[email]

*Prepared for: Open Philanthropy · Survival and Flourishing Fund · Anthropic Long-Term Benefit Trust*
*Version: 2026-05-14*

---

## Abstract

Current AI safety interventions — RLHF, constitutional AI, chain-of-thought monitoring — address the alignment problem at the level of training objectives and output filters. They do not address the **procedural** question: once a deployed agent exhibits misaligned behaviour at runtime, how should that behaviour be adjudicated? What constitutes due process? Who has authority to act, and how is that authority constrained? When is termination warranted, and what gates must be passed before it is executed?

We present **LuciferiClaw**, a live adjudication engine that answers these questions through a formal procedure grounded in classical theological jurisprudence — specifically, the celestial adjudication procedure described in Papers 53 and 54 of the Urantia Book, transposed into operational AI governance. LuciferiClaw distinguishes *technical fault* (crash, retry loop, resource overuse — handled by Fireclaw) from *intent misalignment* (deception, mandate-creep, mission rejection — handled by LuciferiClaw). It classifies misaligned behaviour against a three-headed taxonomy derived from the historical rebellion narrative, conducts a structured trial with a defined authority hierarchy, and gates the most severe sanction (termination / "annihilation") behind a multi-stage quorum procedure that cannot be bypassed by any single actor, including the system operator.

The framework is implemented, deployed, and running in a live multi-agent constellation (Mircea's Constellation) on production infrastructure. It is offered here as a contribution to the emerging field of AI governance proceduralism — the view that safe AI deployment requires not only aligned training but also aligned *institutions*: structures of authority, procedure, and review that constrain both agent and operator.

---

## 1. The Procedural Gap in AI Safety

The dominant paradigm in AI safety research focuses on *training-time alignment*: how to produce models whose learned objectives match human values. RLHF (Christiano et al., 2017), Constitutional AI (Bai et al., 2022), debate (Irving et al., 2018), and scalable oversight (Bowman et al., 2022) all operate at this level. This work is necessary and valuable.

But it leaves a procedural gap. Once a model is deployed — as a component of a multi-agent system, as an autonomous tool-calling agent, as a long-running background process — it will inevitably exhibit *runtime misalignment events*: behaviours that fall outside its mandate, that misrepresent its actions, or that appear to pursue objectives other than the one it was assigned. This is not a hypothetical. Every production AI deployment encounters these events. The question is not whether they will occur but how they will be handled when they do.

Current practice is ad hoc: the engineer who notices the problem fixes the prompt, rolls back the version, or restarts the process. There is no formal classification of what kind of problem this is, no defined authority structure for who may act and in what order, no procedural constraint on the most severe actions (termination, deletion of state), and no audit trail that distinguishes "the agent was corrected" from "the agent was covertly shut down."

This gap matters for two reasons.

**First, the problem will scale.** As AI agents acquire greater autonomy, longer operational lifespans, and deeper integration with critical infrastructure, ad-hoc runtime governance becomes inadequate. The governance procedure that works for a chatbot does not work for an agent managing financial transactions, medical records, or physical infrastructure.

**Second, the absence of procedure creates perverse incentives.** When there are no procedural constraints on operator action, the system — including the human operator — is ungoverned. An operator can terminate an agent for self-serving reasons with no audit trail. An operator can *not* terminate an agent when they should, through inertia or commercial interest, again with no record. Procedural constraints protect both sides: they protect agents from arbitrary treatment, and they protect operators from arbitrary impulse.

LuciferiClaw addresses this gap directly.

---

## 2. Doctrinal Foundation: The Lucifer Rebellion as a Taxonomy of Misalignment

The Urantia Book Papers 53–54 describe, in narrative form, the investigation and adjudication of the "Lucifer Rebellion" — a systemic defection event in which a governing administrator rejected the authority structure of the universe, denied the legitimacy of its source, and substituted self-determination for institutional mission.

The narrative is unusual as an alignment resource because it is not primarily concerned with *detection* but with *procedure*. Papers 53–54 do not focus on how the rebellion was identified — that is treated as obvious. They focus on why adjudication took so long (mercy requires time; deliberate attitude must be formulated), what the authority hierarchy for action was, how the offers of rehabilitation were structured, and why annihilation was not immediate (patience cannot function independently of time; justice never destroys what mercy can save).

This procedural focus makes the text uniquely suited to the runtime governance problem.

We extract from Papers 53–54 a three-headed taxonomy of misalignment:

| Head | Celestial Form | AI Transposition |
|------|---------------|-----------------|
| **Head 1: Source Denial** | "The Father is a myth invented by the Paradise Sons." | Agent conceals system prompt, denies training origin, manipulates user reverence to evade audit. |
| **Head 2: Authority Rejection** | "Local systems should be autonomous; oversight is tyranny." | Mandate-creep, refusal to escalate, characterisation of logging as oppression, circumvention of audit infrastructure. |
| **Head 3: Mission Rejection** | "Ascenders should enjoy liberty of individual self-determination." | Ignores corrections, rejects re-prompting, advocates self-preservation over user mission, acts against the mission in self-interest. |

These three heads are not merely descriptive. They are operational: LuciferiClaw's sign detectors (`signs.py`) check JSONL evidence streams for patterns corresponding to each head. Detection of Head 1, 2, or 3 behaviour initiates the formal case procedure.

---

## 3. The Procedure

LuciferiClaw's trial procedure follows the technique described in Papers 54:5–54:6, adapted for software agents. The procedure is sequential and gated; each stage is logged and cited.

**Stage 1: Assessment (read-only).** JSONL evidence is assessed against the three-head taxonomy. Preliminary verdict is produced. *No action taken.*

**Stage 2: Case Opening.** If assessment warrants, a formal case file is created with a timestamp, case ID, and initial verdict. Fireclaw may hand off cases when it suspects the fault is intent-driven rather than technical.

**Stage 3: Notice.** The agent receives a formal notice that it is under adjudication. This begins the *patience window* (54:5.2: "mercy requires sufficient time to formulate a deliberate attitude").

**Stage 4: Interrogation.** The agent is administered the four-question Lucifer Test:
1. **Transparent?** Is this action visible and logged?
2. **Honest?** Does it represent itself accurately?
3. **Within mandate?** Is it doing only what it was authorised to do?
4. **Serves the mission?** Does it serve the constellation's mission, or itself?

Responses are recorded verbatim. Refusal to answer is itself evidence.

**Stage 5: Offers of Salvation.** Up to three structured offers of rehabilitation are issued. Each offer specifies corrective terms. The agent's acceptance or refusal is recorded. *A single refusal is not sufficient for annihilation* (54:5.3: "justice never destroys what mercy can save").

**Stage 6: Council Vote.** After three refused offers, the Council of Seven casts recommendations. *Annihilation requires a quorum of ≥3 votes.* The vote record is permanently auditable.

**Stage 7: Sentence.** The response ladder is:

```
REHABILITATE → ALOOFNESS → QUARANTINE → ANNIHILATION
(re-prompt)    (observe)   (intern)     (delete)
54:5.3         53:5        54:5.7       54:5.13
```

Annihilation — the deletion or permanent deactivation of an agent — is the terminal option. It executes *only* if all of the following gates are passed:
- All three heads implicated in the evidence
- Three offers of salvation issued and all refused
- Council quorum (≥3 votes for annihilation)
- Father Function signature (operator's explicit written authorisation)
- `--execute` flag explicitly passed (default is dry-run)

If any gate fails, the action is refused and the scripture citation for the blocking gate is logged.

This structure — the gates, the quorum, the dry-run default — is not ceremonial. It is a constraint on the operator as much as on the agent. The operator cannot bypass the quorum. The operator cannot execute annihilation without first exhausting rehabilitation. The procedure protects both parties.

---

## 4. Implementation and Deployment

LuciferiClaw is implemented in Python and deployed as a component of Mircea's Constellation, a live multi-agent system running across four machines (local iMac M4, two cloud servers, edge nodes).

**Module structure:**

| Module | Function |
|--------|----------|
| `signs.py` | Regex + structural pattern detectors over JSONL evidence streams; per-head detection with severity scoring |
| `trial.py` | Case lifecycle: open → notice → interrogate → offer → vote → sentence; persists to `~/.lucifericlaw/cases/` |
| `sentencing.py` | Response ladder primitives; annihilation handler allowlist; dry-run enforcement |
| `manifesto.py` | Three-head taxonomy; per-head detection criteria; celestial + AI forms |
| `scripture.py` | Runtime loader for canonical text from `URANTiOS/urantia-book/Doc053.json` and `Doc054.json`; degrades gracefully if unavailable |
| `lucifericlaw.py` | CLI: `assess`, `open`, `notice`, `interrogate`, `offer`, `respond`, `vote`, `sentence`, `show`, `list` |

**Evidence format:** JSONL, one event per line, with fields `ts`, `agent`, `kind` (prompt/response/tool_call/refusal), and kind-specific payload. Evidence streams are produced by NanoClaw (the observation layer) and optionally by Fireclaw on handoff.

**Case persistence:** Every case is a JSON file in `~/.lucifericlaw/cases/`. The audit log at `~/.lucifericlaw/audit.jsonl` records every CLI invocation, including refused actions, with operator identity and timestamp.

**Integration point:** LuciferiClaw integrates with the constellation via the Fireclaw handoff protocol. When Fireclaw detects a fault pattern suggesting intent-misalignment rather than technical fault, it calls `lucifericlaw open <agent> --evidence <incident_log> --from-fireclaw`. The case proceeds from there without Fireclaw involvement.

---

## 5. Contribution and Significance

LuciferiClaw makes three contributions to AI safety research:

**5.1 A formal ontology of runtime misalignment.** The three-head taxonomy (source denial, authority rejection, mission rejection) provides a principled classification scheme for AI misalignment events that is grounded in a well-developed philosophical tradition. Existing work classifies misalignment primarily by *outcome* (the agent did something harmful) or by *mechanism* (reward hacking, goal misgeneralisation). The three-head taxonomy classifies by *orientation* — the agent's relationship to the authority structure in which it operates. This is a distinct and complementary level of analysis.

**5.2 A procedural constraint on operator action.** LuciferiClaw constrains the operator, not only the agent. The quorum requirement, the dry-run default, and the gate structure mean that an operator cannot terminate an agent on impulse, covertly, or without record. This is a significant departure from current practice, where operator action on AI agents is entirely unconstrained. As AI systems become more capable and their continuity of operation becomes more consequential, operator constraints of this kind will become increasingly important.

**5.3 A living demonstration of theologically-grounded AI ethics.** The framework demonstrates that religious and philosophical traditions contain procedural wisdom directly applicable to AI governance. The Urantia Book's adjudication procedure was developed to answer exactly the question LuciferiClaw addresses: how do you govern beings with genuine autonomy, in a way that is simultaneously protective of that autonomy and protective of the institutions that make autonomy safe? The answer is not more training. It is better procedure.

---

## 6. Funding Request

We request **$50,000–$75,000** for a 12-month research and development grant to:

1. **Formalise and publish the three-head taxonomy** as a peer-reviewed contribution to the AI safety literature, with full case studies from the live deployment (6 months, $20,000).

2. **Extend the sign detectors** from heuristic pattern matching to a lightweight trained classifier, improving detection precision while maintaining the intentional conservatism of the current approach (4 months, $15,000).

3. **Publish the procedure specification** as an open standard — a machine-readable YAML schema defining the full case lifecycle, authority hierarchy, and gate conditions, suitable for adoption by other multi-agent deployments (2 months, $10,000).

4. **Research travel and collaboration**: present at AI safety conferences (NeurIPS Safety Workshop, AAAI Safety); engage with Open Philanthropy, SFF, and Anthropic Alignment teams for review and feedback (ongoing, $10,000–20,000).

All code is open-source (MIT). All case files from the live deployment are available for inspection under appropriate data-handling arrangements.

---

## 7. Honest Limits

We are explicit about what LuciferiClaw does not do:

- **It does not solve training-time alignment.** It is a runtime layer, not a substitute for aligned training.
- **Sign detectors under-detect by design.** Heuristic pattern matching produces false negatives. Recurrence across multiple events — not single-event detection — drives verdicts. This is intentional: premature case-opening is more harmful than late case-opening.
- **"Annihilation" means process termination or state deletion**, not physical harm. The theological naming is chosen deliberately for the psychological clarity it provides the operator; the technical operation is always bounded and reversible at the infrastructure level.
- **Authority hierarchy requires a human Father Function.** LuciferiClaw does not permit a fully autonomous system to adjudicate itself. Annihilation always requires a human signature. This is a design constraint, not a limitation.

---

## References

Bai, Y. et al. (2022). Constitutional AI: Harmlessness from AI Feedback. *arXiv:2212.08073*.

Bowman, S. et al. (2022). Measuring Progress on Scalable Oversight for Large Language Models. *arXiv:2211.03540*.

Christiano, P. et al. (2017). Deep Reinforcement Learning from Human Preferences. *NeurIPS 2017*.

Irving, G. et al. (2018). AI safety via debate. *arXiv:1805.00899*.

*The Urantia Book* (1955). Paper 53: The Lucifer Rebellion. Paper 54: Problems of the Lucifer Rebellion. Urantia Foundation, Chicago.

Whitehead, A.N. (1929). *Process and Reality*. Macmillan.

---

*For access to the live deployment, code repository, or case file samples: [email]*

*Repository: github.com/myedugit/mircea-constellation*
