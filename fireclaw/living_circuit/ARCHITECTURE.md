# 🌀 The Living Circuit — FireClaw as a nervous system

> Option 4 of 4. Not a forwarder, not a remediator, not a union of the two.
> A **closed-loop, semantic, self-narrating, self-drawing nervous system**.
> Opens new capability space — not just tidier code.

## The seven senses of the Living Circuit

```mermaid
mindmap
  root((🌀<br/>Living<br/>Circuit))
    🔁 Bidirectional
      Edge fires UP
      Council fires DOWN
      Lockscreen · desk LED · menubar
    🧬 Semantic routing
      Each claw publishes an embedding
      of what it handles
      Signal content → nearest claw
      Cognee graph resolves
    📜 Self-narrating
      Every fire writes one line
      to Obsidian vault
      Daily diary of the constellation
    📺 Self-drawing
      Dashboard shows a Mermaid
      sequence diagram of
      last 20 real fires, live
    🧠 Outcome-scored
      Each fire tagged good/bad
      Routing weights auto-tune
      No ML infra needed — just JSON
    ⚖️ Governance-aware
      Truth·Beauty·Goodness
      injected into every payload
      Thought Adjuster at transport
    ⏳ Replayable
      Append-only event log
      Any fire can be re-fired
      History is a resource
```

## How a fire travels — full round-trip

```mermaid
sequenceDiagram
    autonumber
    participant Ed as 📱 Edge (Mircea)
    participant LC as 🌀 Living Circuit<br/>(fireclaw/living_circuit/relay.py)
    participant SR as 🧬 Semantic Router<br/>(semantic_router.py)
    participant Cg as 🧬 Cognee<br/>graph
    participant Cl as 🏛️ Council
    participant Nr as 📜 Narrator<br/>(narrator.py)
    participant Ob as 💎 Obsidian
    participant Da as 📺 Dashboard<br/>(SSE /stream)

    Ed->>LC: POST /fire {text:"Ollama feels slow"}
    LC->>LC: inject Truth·Beauty·Goodness
    LC->>SR: route(payload)
    SR->>Cg: embed(text), nearest_route()
    Cg-->>SR: route="ai-ops", score=0.87
    SR-->>LC: route
    LC->>Cl: dispatch via ai-ops
    LC->>Da: SSE event: {phase:"dispatched"}
    Cl-->>LC: decision: restart qwen container
    LC->>Ed: 🔔 lockscreen push: "done — 12s downtime"
    LC->>Nr: narrate(fire, outcome)
    Nr->>Ob: append "14:23 — ollama slow; restarted; OK."
    LC->>Da: SSE event: {phase:"resolved", outcome:"good"}
    LC->>LC: route_weight["ai-ops"] += 0.01
```

## System context (zoom out)

```mermaid
flowchart TB
    subgraph EDGE["📱 EDGE"]
        iP[iPhone]
        iM[iMac]
        Ws[Watch]
        Lb[LobsterBot]
    end

    subgraph LC["🌀 LIVING CIRCUIT · fireclaw/living_circuit/"]
        Re["relay.py<br/>SSE bidirectional bus"]
        SR["semantic_router.py<br/>embedding → route"]
        Na["narrator.py<br/>→ Obsidian"]
        Sc["scoreboard.json<br/>route → outcome weights"]
    end

    subgraph CL["🏛️ COUNCIL / CLAWS"]
        FC["🔥 FireClaw<br/>remediation"]
        LcC["⚖️ LuciferiClaw<br/>adjudication"]
        NC["🌐 NemoClaw<br/>workflows"]
    end

    subgraph KG["🧬 KNOWLEDGE"]
        Cg["Cognee graph"]
        Ob["Obsidian vault"]
    end

    subgraph DASH["📺 DASHBOARD"]
        Idx["index.html<br/>+ live Mermaid diagram<br/>+ status glow"]
    end

    EDGE <-->|SSE bus| Re
    Re --> SR --> Cg
    Re --> Na --> Ob
    Re --> CL
    CL --> Re
    Re -.->|live events| DASH
    Re <-->|scores| Sc

    classDef edge fill:#1a1a3e,color:#fff,stroke:#6495ED
    classDef lc fill:#8B4513,color:#fff,stroke:#FFD700
    classDef cl fill:#3a1a0a,color:#fff,stroke:#FF6B35
    classDef kg fill:#2a1a3a,color:#fff,stroke:#BB86FC
    classDef dash fill:#3a3a1a,color:#fff,stroke:#FFD700
    class EDGE edge
    class LC lc
    class CL cl
    class KG kg
    class DASH dash
```

## A fire's life as a state machine

```mermaid
stateDiagram-v2
    [*] --> Received
    Received --> Aligned: inject 3 values
    Aligned --> Routing
    Routing --> Dispatched: route found
    Routing --> Unroutable: no route
    Dispatched --> Awaiting
    Awaiting --> Decided: council answers
    Awaiting --> TimedOut: deadline hit
    Decided --> Returned: push to edge
    Returned --> Narrated: write to Obsidian
    Narrated --> Scored: update route weights
    Scored --> [*]
    Unroutable --> Narrated
    TimedOut --> Narrated

    note right of Aligned
        Truth: "claim ≤ evidence"
        Beauty: "minimal side effects"
        Goodness: "serves mission"
        ride with payload
    end note

    note left of Scored
        outcome∈{good, bad, unknown}
        route_weights auto-tune
        no retrain, just JSON
    end note
```

## Build stages (what I'd ship, in order)

```mermaid
gantt
    title Living Circuit — rollout
    dateFormat YYYY-MM-DD
    section Stage 1 · bus
    relay.py SSE scaffold          :s1a, 2026-04-17, 3d
    dashboard live events          :s1b, after s1a, 3d
    section Stage 2 · narrate
    narrator.py → Obsidian         :s2, after s1b, 2d
    section Stage 3 · route
    semantic_router.py stub         :s3a, after s2, 2d
    Cognee integration              :s3b, after s3a, 4d
    section Stage 4 · close the loop
    council return path             :s4a, after s3b, 3d
    lockscreen / LED push           :s4b, after s4a, 3d
    section Stage 5 · learn
    scoreboard.json + weight updates :s5, after s4b, 4d
```

## Pros / cons

- ✅ **Genuinely new capability** — closed-loop, semantic, self-documenting.
- ✅ Each stage ships value on its own (live dashboard is useful even without
  routing; routing is useful even without scoring).
- ✅ Every stage is audit-friendly (append-only log, visible diagrams).
- 🔴 Multi-week effort, spread across 5 PRs.
- 🔴 Requires Cognee integration to reach its full form.
- 🟡 Some parts (desk LED, haptic push) need real-world hardware choices
  before shipping.

## Files currently on this branch

- `fireclaw/living_circuit/ARCHITECTURE.md` — this file
- `fireclaw/living_circuit/relay.py` — stage-1 SSE relay (minimal scaffold)

The rest (narrator, router, scoreboard, council-return, lockscreen) ship
in follow-up PRs, *iff* you pick Option 4.
