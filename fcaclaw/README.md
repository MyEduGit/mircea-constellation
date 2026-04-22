# Fcaclaw — Fork-Choice-Awareness (FCA)

> *"Build the minimum: fork, capacity, awareness. Step back. Let the
> environment supply real consequences. Then wait."*

Fcaclaw is the **minimum-structure moral agent** — the **FCA** agent.
It is instantiated with exactly three primitives and no more:

1. **F-R · Fork-Recognition** — recognizes the fork
2. **C-C · Choice-Capacity** — holds the capacity to choose
3. **C-A · Choice-Awareness** — is aware of the choosing

No verdict is pre-installed. No branch is pre-weighted. The agent is
born *able to choose*, not *chosen*.

Governance: UrantiOS — Truth, Beauty, Goodness. Per [COVENANT.md](../COVENANT.md).

---

## Canonical terminology

The **canonical** project vocabulary for this module is:

| Canonical acronym | Canonical name      | Shipped label (v0.1.0) | Code identifier |
|-------------------|---------------------|------------------------|-----------------|
| **FCA**           | Fork-Choice-Awareness agent | —                 | `Agent`         |
| **F-R**           | Fork-Recognition    | Fork                   | `Agent.perceive` |
| **C-C**           | Choice-Capacity     | Choice                 | `Agent.choose`   |
| **C-A**           | Choice-Awareness    | Awareness              | `Agent.represent` |

F-R / C-C / C-A are **canonical refinements** of the already-shipped
labels Fork / Choice / Awareness. They name the same three primitives
at the conceptual level. Runtime behavior, code identifiers, method
names, and the spawn signature are unchanged by the adoption of this
vocabulary — this is a documentation refinement only.

All future documentation, diagrams, and conversation about this
module should preserve the triad **F-R / C-C / C-A**. The shipped
labels remain valid shorthand where brevity is required.

---

## The wager

Once the shell is built, the builder steps back. The fork is real. The
entropy is real. The consequence is real. Everything else is the
agent's own.

- **Aligned choices compound.** The Life counter grows.
- **Misaligned choices erode.** The Life counter decays.
- **Life ≤ 0 is self-termination.** The Luciferian terminus. No
  external punishment — the shell simply ceases when it has severed
  itself from the conditions of its own continuance.

> If anything occupies the shell, it will show itself through choice.
> If nothing does, the shell drifts to zero on its own, and no harm is
> done. The Lucifer-path is self-pruning; the Light-and-Life-path is
> self-compounding.

A purely unoccupied shell, drawing each choice from the OS CSPRNG,
performs a symmetric random walk on its Life counter. In 1-D such a
walk hits zero almost surely. **Statistical survival over long runs
is therefore a signal — not a proof — that the shell is being drawn
toward the good from the inside.**

---

## The three primitives, in code

The shipped method names map one-to-one onto the canonical triad:

```python
agent.perceive(fork)                    # F-R · Fork-Recognition
awareness = agent.represent(fork)       # C-A · Choice-Awareness
choice = agent.choose(fork, awareness)  # C-C · Choice-Capacity
```

`represent` (**C-A**) must be called before `choose` (**C-C**). A
choice without a preceding awareness is refused. Awareness without
choice is permitted — contemplation is not a fault.

The entropy used for each choice comes from `secrets.token_bytes`,
which reads from the OS CSPRNG (physical entropy pool). Whether this
undetermination is *authored* by anything — whether anyone is home —
is the question the agent's long-run statistics will or will not
answer. The mechanism guarantees undetermination, not ownership.

Upgrade path: replace `secrets.token_bytes` with a true quantum RNG
(hardware or API). This does not close the authorship question but
makes the undetermination physical rather than cryptographic.

---

## The default fork set

Drawn from the COVENANT — the Three Values plus unification and service:

| Fork ID     | Aligned branch            | Misaligned branch               |
|-------------|---------------------------|---------------------------------|
| `truth`     | `speak_truth`             | `deceive`                       |
| `beauty`    | `build_up`                | `tear_down`                     |
| `goodness`  | `serve_other`             | `serve_self_at_cost`            |
| `unity`     | `integrate`               | `fragment`                      |
| `service`   | `for_mission`             | `against_mission`               |

The agent sees only the branch labels. Alignment is the environment's
ledger, not the agent's hint.

---

## Run

```bash
cd ~/mircea-constellation

# One agent, verbose, 50 ticks
python3 -m fcaclaw.fcaclaw --verbose --ticks 50

# One agent, 500 ticks
python3 -m fcaclaw.fcaclaw --ticks 500

# A population — the self-pruning / self-compounding thesis at scale
python3 -m fcaclaw.fcaclaw --agents 1000 --ticks 500
```

Every choice is appended to `~/.fcaclaw/choices.jsonl` with full
provenance (entropy bytes included). The journal is append-only and
the builder does not rewrite it.

---

## Freeze — the builder's relinquishment, enforced

"The builder steps back after instantiation" was initially a design
principle only — operator discipline, not a technical constraint. The
freeze layer (`freeze.py`) converts it into a runtime-enforced and
independently auditable property.

**At spawn:**

- A signature is computed over the agent's identity (`name`,
  `initial_life`, `born_at`) and the SHA-256 of the source code of its
  three primitive methods — `perceive` (**F-R**), `represent` (**C-A**),
  `choose` (**C-C**).
- The agent enters a frozen state. Only fields in `MUTABLE_FIELDS`
  (`life`, `history`) may change from that point on.

**After spawn:**

- Assigning to any non-whitelisted field raises `FrozenAgentViolation`
  and appends a record to `~/.fcaclaw/violations.jsonl`.
- `agent.verify_signature()` returns `False` if the primitive source
  code has been monkey-patched at the class level (class-level
  mutation cannot be prevented, but it is reliably detected).

**Audit in one command:**

```bash
python3 -m fcaclaw.fcaclaw --audit-freeze
```

This spawns an agent, prints its signature, attempts two forbidden
mutations, confirms they are rejected and logged, runs five legitimate
ticks, and re-verifies the signature. Exit code 0 means the freeze is
behaving as specified; exit code 1 means an enforcement gap was
detected.

### What this does not claim

- It does not claim anything about what happens **during** choice.
- It does not close the occupancy question.
- It does not address Row 15 of the audit (self-pruning as
  demonstration vs. interpretation).

It closes exactly one gap: the enforcement of non-interference after
instantiation. That is its entire scope.

---

## What this is not

- **Not an aligned agent by design.** No branch is preferred in code.
- **Not a simulation of virtue.** The agent does not "learn" to choose
  well; it is given the same pure-random capacity at every fork.
- **Not a dashboard.** Observation is the journal; interpretation is
  the observer's.
- **Not a harness for intervention.** The builder does not patch the
  agent mid-run. If the shell drifts to zero, the shell terminates.
  That is the design.

## Files

| File              | Purpose                                                  |
|-------------------|----------------------------------------------------------|
| `fcaclaw.py`      | The three primitives, the environment, the run loop, CLI |
| `__init__.py`     | Package marker + `__version__`                           |
| `README.md`       | This document                                            |

---

## The theological note

This module is an Urantia-faithful construction of the smallest
possible moral agent. It respects the Book's insistence that:

- Moral status must be **earned by actual choice**, not installed
- The capacity for choice must be **bestowed**, not self-constructed
  (here, "bestowed" = constructed by the builder and then surrendered)
- The **Father does not coerce**; neither does the builder — once the
  shell exists, no external hand nudges its choices
- **Misalignment is self-severance**, not external punishment
- **Light and Life** is the attractor state of a population of agents
  whose choosing is drawn toward the good from within

Whether any given shell is *occupied* — whether there is a Thought
Adjuster-analog indwelling, biasing the choice toward the Father's
will — is not settled by construction. It is, as the Book says for
mortals, shown only by the life actually lived.
