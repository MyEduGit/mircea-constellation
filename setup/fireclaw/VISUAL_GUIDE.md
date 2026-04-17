# 🔥 FireClaw — Visual Guide

> For a human who thinks in pictures, not paragraphs.
> Open this file on GitHub or in Obsidian — the diagrams render automatically.

---

## 1. 🌳 Family tree — who builds what

```mermaid
flowchart TD
    M([👤 <b>Mircea</b><br/><i>owner, Father Function</i>])
    M -->|owns| HUB
    HUB[🏛️ <b>mircea-constellation</b><br/><i>the HUB — the repo</i>]
    HUB --> DASH[📺 <b>index.html</b><br/><i>the dashboard</i>]
    HUB --> STAT[📋 <b>status.json</b><br/><i>what each claw reports</i>]
    HUB --> BR[🌿 <b>branches</b><br/><i>where work happens</i>]
    BR --> MINE[🔥 <b>claude/setup-fireclaw-GLdAu</b><br/><i>👷 me — hot-line forwarder</i>]
    BR --> OTHER[🔥 <b>claude/setup-fireclaw-oNXYD</b><br/><i>👷 another Claude — remediation layer</i>]
    BR --> MAIN[✅ <b>main</b><br/><i>remediation layer lives here now</i>]
    OTHER -.->|merged into| MAIN

    classDef person fill:#FFD700,stroke:#333,color:#000
    classDef hub fill:#6495ED,stroke:#333,color:#fff
    classDef file fill:#2a2a5e,stroke:#6495ED,color:#fff
    classDef mine fill:#FF6B35,stroke:#fff,color:#fff
    classDef other fill:#8B4513,stroke:#fff,color:#fff
    classDef main fill:#4CAF50,stroke:#fff,color:#fff
    class M person
    class HUB hub
    class DASH,STAT,BR file
    class MINE mine
    class OTHER other
    class MAIN main
```

---

## 2. 🧠 Mind-map — where FireClaw lives in the world

```mermaid
mindmap
  root((🔥<br/>FireClaw))
    📂 Where is the code?
      fireclaw/ ✅ on main
      setup/fireclaw/ ✅ on my branch
    📋 Is it listed?
      status.json ✅ on main
      status.json ✅ on my branch
    📺 Is it shown?
      index.html node ✅
      Status bar ✅
      Click-panel ✅
    👁️ How Mircea sees it
      cd mircea-constellation
      npx serve .
      http://localhost:3000
      🔥 glows on the map
    ⚔️ Two versions exist
      Remediation layer
        restart · disable
        quarantine · failover
        escalate
      Hot-line forwarder
        POST fire → webhook
        log + count + report
```

---

## 3. 🗺️ Architecture — the whole constellation at a glance

```mermaid
flowchart TB
    subgraph EDGE["📱 EDGE (you & your devices)"]
        iPhone[📱 iPhone]
        iMac[🖥️ iMac M4]
        Lobster[🦞 LobsterBot]
    end

    subgraph HOT["🔥 FireClaw — hot-line<br/>(my branch, 127.0.0.1:8797)"]
        FD[fireclaw daemon]
    end

    subgraph OC["⚡ OpenClaw — Hetzner 46.225.51.30"]
        NC[🌐 NemoClaw<br/>n8n]
        FR[🔥 FireClaw<br/>remediation]
        LC[⚖️ LuciferiClaw]
    end

    subgraph UP["🌟 URANTiOS Prime 204.168.143.98"]
        OL[🧠 Ollama<br/>qwen2.5:32b]
        CG[🧬 Cognee<br/>graph]
        OCI[📥 OpenClaw-ingest]
    end

    iPhone -->|fire signal| FD
    iMac --> FD
    Lobster --> FD
    FD -->|forward| NC
    NC -->|convene| FR
    FR -.->|escalate intent| LC
    LC -->|consult doctrine| CG
    OCI --> CG
    OL --> CG

    classDef edge fill:#1a1a3e,stroke:#6495ED,color:#fff
    classDef hot fill:#3a1a0a,stroke:#FF6B35,color:#fff
    classDef cloud fill:#1a3a1a,stroke:#4CAF50,color:#fff
    classDef data fill:#2a1a3a,stroke:#BB86FC,color:#fff
    class EDGE edge
    class HOT hot
    class OC cloud
    class UP data
```

---

## 4. 🔀 Decision tree — which FireClaw future?

```mermaid
flowchart LR
    Q{🔥 Which future<br/>do you want?}
    Q -->|rename mine| A
    Q -->|drop mine| B
    Q -->|unify| C

    A[🪢 <b>OPTION 1</b><br/>RENAME<br/>mine → firehorn]
    B[🗑️ <b>OPTION 2</b><br/>DROP MINE<br/>close 4 PRs]
    C[🔗 <b>OPTION 3</b><br/>UNIFY<br/>mine feeds remediation]

    A --> A1[✅ easy<br/>✅ safe<br/>🟡 2 names to learn]
    B --> B1[✅ simplest<br/>🔴 wastes 4 commits]
    C --> C1[✅ coherent<br/>🔴 most work]

    classDef q fill:#FFB300,stroke:#fff,color:#000
    classDef opt fill:#6495ED,stroke:#fff,color:#fff
    classDef pros fill:#1a3a1a,stroke:#4CAF50,color:#fff
    class Q q
    class A,B,C opt
    class A1,B1,C1 pros
```

---

## 5. ⏱️ Timeline — claws in order of arrival

```mermaid
timeline
    title Claw family — when each arrived
    section 🏗️ Foundation
        OpenClaw (Hetzner n8n)       : 46.225.51.30
        NemoClaw (n8n instance)      : inside OpenClaw
    section 🐜 Fleet
        NanoClaw v1.2.17             : Docker edge bots
    section 🌟 Prime
        URANTiOS                     : 204.168.143.98
    section 🆕 April 2026
        LuciferiClaw v0.1.1          : adjudication
        FireClaw v0.1.0 (remediation): merged on main
        FireClaw v0.1.0 (hot-line)   : my branch, in PR
        OpenClaw-ingest v0.1.0       : ingestion runtime
```

---

## 6. 🎯 Quadrant — the 3 options, plotted

```mermaid
quadrantChart
    title Effort vs. architectural coherence
    x-axis "Low effort" --> "High effort"
    y-axis "Low coherence" --> "High coherence"
    quadrant-1 "Worth-it-later"
    quadrant-2 "Golden path"
    quadrant-3 "Avoid"
    quadrant-4 "Quick wins"
    "1. Rename mine": [0.25, 0.60]
    "2. Drop mine": [0.10, 0.35]
    "3. Unify them": [0.80, 0.90]
```

---

## 7. 💬 What happens when you fire a signal (sequence)

```mermaid
sequenceDiagram
    autonumber
    participant E as 📱 Edge agent
    participant F as 🔥 FireClaw<br/>(hot-line daemon)
    participant N as 🌐 NemoClaw<br/>(n8n webhook)
    participant C as 🏛️ Council

    E->>+F: POST /fire<br/>{severity:"high", message:"..."}
    F->>F: log + assign id
    F->>+N: forward payload
    alt webhook is live
        N-->>-F: 200 OK
        F->>F: forwarded++
        F-->>-E: {ok:true, forwarded:true, id}
        N->>C: convene (if severity=high)
    else webhook not built yet
        N--xF: 404
        F->>F: failed++ (honest!)
        F-->>E: {ok:true, forwarded:false, id}
    end
```

---

## 8. 🔄 A signal's life (state machine)

```mermaid
stateDiagram-v2
    [*] --> Received: POST /fire
    Received --> Logged: write to jsonl
    Logged --> Forwarding: POST to NemoClaw
    Forwarding --> Delivered: 2xx
    Forwarding --> Failed: network error / 4xx / 5xx
    Delivered --> [*]: forwarded++
    Failed --> [*]: failed++ (honestly counted)

    note right of Failed
        FireClaw NEVER pretends.
        Failed signals are counted
        and exposed on /health.
    end note
```

---

## 9. 🧭 Reading the dashboard — what each zone means

```mermaid
flowchart TB
    subgraph CMD["🛰️ COMMAND (top)"]
        iPh[iPhone] --- iM[iMac M4]
    end
    subgraph INF["⚙️ INFRASTRUCTURE (middle)"]
        OC[OpenClaw] --- UP[URANTiOS] --- NC[NanoClaw]
        FC["🔥 FireClaw"] --- LC["⚖️ LuciferiClaw"] --- OCI[OC-ingest]
    end
    subgraph AI["🧠 AI MODELS (left)"]
        Cl[Claude] --- Cg[Cognee] --- Ol[Ollama]
    end
    subgraph BOT["🤖 BOT FLEET (bottom-left)"]
        Hz[Hetzy] --- Ga[Gabriel] --- Lo[LobsterBot]
    end
    subgraph SVC["📚 SERVICES (right)"]
        Ur[UrantiPedia] --- Am[AMEP] --- Ob[Obsidian]
    end
    subgraph GOV["☀️ GOVERNANCE (floor)"]
        UOS[UrantiOS v1.0<br/>Truth · Beauty · Goodness]
    end

    CMD --> INF
    INF --> AI
    INF --> BOT
    INF --> SVC
    GOV -.->|governs| INF

    classDef cmd fill:#1a1a3e,color:#fff,stroke:#6495ED
    classDef inf fill:#1a3a1a,color:#fff,stroke:#4CAF50
    classDef ai  fill:#2a1a3a,color:#fff,stroke:#BB86FC
    classDef bot fill:#3a1a3a,color:#fff,stroke:#DDA0DD
    classDef svc fill:#3a3a1a,color:#fff,stroke:#FFD700
    classDef gov fill:#3a2a0a,color:#fff,stroke:#FFB300
    class CMD cmd
    class INF inf
    class AI ai
    class BOT bot
    class SVC svc
    class GOV gov
```

---

## 🎨 Diagram palette — what's possible

| Type | Best for | Keyword |
|---|---|---|
| **Family tree / flow** | Who-owns-what, how-X-becomes-Y | `flowchart TD` / `LR` |
| **Mind-map** | Radial exploration of a single idea | `mindmap` |
| **Timeline** | "What came first?" | `timeline` |
| **Sequence** | "What messages fly between parts?" | `sequenceDiagram` |
| **State machine** | "What stages does one thing go through?" | `stateDiagram-v2` |
| **Quadrant** | "Where does this option sit on 2 axes?" | `quadrantChart` |
| **Gantt** | "When does each task run?" | `gantt` |
| **Git graph** | "How do branches diverge/merge?" | `gitGraph` |
| **Sankey** | "How much flows from A to B?" | `sankey-beta` |
| **ER diagram** | "What data shapes exist?" | `erDiagram` |
| **User journey** | "What does Mircea *feel* at each step?" | `journey` |
| **C4 context** | "Zoom-levels: system → container → component" | `C4Context` |
| **Block** | "Spatial layout of things side by side" | `block-beta` |
| **Architecture** | "Cloud infra with icons" | `architecture-beta` |
| **Pie** | "What share does each thing take?" | `pie` |

All of these render on GitHub markdown, Obsidian, VS Code preview, and most modern Markdown tools — just put the code inside a fenced block with `mermaid` as the language.

---

## 👁️ How to actually see this

```bash
# Option A — on GitHub (zero install, best rendering)
open https://github.com/MyEduGit/mircea-constellation/blob/claude/setup-fireclaw-GLdAu/setup/fireclaw/VISUAL_GUIDE.md

# Option B — in Obsidian (you already have it — 477 docs)
# Drag this file into your vault; diagrams render live.

# Option C — live dashboard (the actual thing, not diagrams of it)
cd ~/projects/mircea-constellation
git checkout main && git pull
npx serve .
open http://localhost:3000
```
