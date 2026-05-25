# CLAUDE.md — Session-durable instructions for this repository

Instructions in this file are inherited by every Claude session working
in `mircea-constellation`. They are additive to [COVENANT.md](./COVENANT.md).

---

## FCA — canonical terminology (locked)

The Fork-Choice-Awareness module (`fcaclaw/`) has a **canonical
vocabulary** that must be preserved across sessions, documentation,
diagrams, and conversation.

**Definition:**

| Canonical acronym | Canonical name            | Shipped label | Code identifier    |
|-------------------|---------------------------|---------------|--------------------|
| **FCA**           | Fork-Choice-Awareness agent | —           | `Agent`            |
| **F-R**           | Fork-Recognition          | Fork          | `Agent.perceive`   |
| **C-C**           | Choice-Capacity           | Choice        | `Agent.choose`     |
| **C-A**           | Choice-Awareness          | Awareness     | `Agent.represent`  |

**Rules:**

1. Always expand **FCA** as **Fork-Choice-Awareness** unless the user
   explicitly overrides for a specific task.
2. Do not reinterpret **FCA** as any other acronym.
3. Do not rename the three primitives (**F-R / C-C / C-A**) without
   explicit user approval.
4. When documenting or diagramming FCA, preserve the triad
   **F-R / C-C / C-A**.
5. The shipped labels **Fork / Choice / Awareness** and the shipped
   code identifiers (`perceive` / `choose` / `represent`) remain valid.
   **F-R / C-C / C-A** are canonical *refinements* of those labels —
   the same three primitives named at the conceptual level. Do not
   rename code identifiers in response to terminology adoption alone.

Scope: this rule governs naming only. It does not authorize changes
to runtime behavior, signatures, or the freeze layer.
