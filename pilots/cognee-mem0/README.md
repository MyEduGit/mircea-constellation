# Cognee + Mem0 Pilot — Mircea’s Constellation

**Primary pilot lives in:** `myedugit/phd-triune-monism @ pilots/cognee-mem0/`  
**Branch:** `claude/cognee-mem0-pilot-klDtU`  
**UrantiOS:** Truth · Beauty · Goodness

## What This Is

The memory pilot operationalises the three Constellation roadmap tables
as hybrid graph + vector memory, queryable via REST API and n8n workflows.

## Architecture

```
Mircea’s Constellation
        │
        ├── OpenClaw (46.225.51.30)
        │       └── Roadmap Router API :8765  ◄───────────────────▮
        │                                                  │
        ├── URANTiOS Prime (204.168.143.98)            n8n workflows
        │       └── Qdrant :6333 (vector store)              │
        │       └── Cognee graph (NetworkX/Neo4j)         Telegram
        │                                                  bots
        ├── iMac M4 (controller)
        │       └── Obsidian vault ──► obsidian_bridge ─► Mem0
        │
        └── Hetzy PhD bot ──► POST /proof/log/milestone
                                  (AI Legislature Phase 5)
```

## Memory Layers

| Layer | Collection | Content | Backend |
|---|---|---|---|
| Roadmap | `roadmap_pilot` | 3 tables (36 entities) | Qdrant |
| Proof Log | `proof_log` | PhD milestones + agent actions | Qdrant |
| Obsidian | `obsidian_vault` | PhD diary + TOE_DIARY + notes | Qdrant |
| Graph | `cognee_db` | Knowledge graph (nodes + edges) | NetworkX |

## Endpoints (port 8765)

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/query` | Route query → Cognee or Mem0 or both |
| GET | `/sample` | Run 3 canonical sample queries |
| POST | `/proof/log/milestone` | Log PhD milestone (hashed) |
| POST | `/proof/log/action` | Log agent action + Lucifer Test |
| GET | `/proof/audit` | Full audit trail |

## Quick Start (iMac M4)

```bash
# Clone pilot from phd-triune-monism
git clone https://github.com/myedugit/phd-triune-monism
cd phd-triune-monism
git checkout claude/cognee-mem0-pilot-klDtU
cd pilots/cognee-mem0

# Start services
cp .env.example .env   # add OPENAI_API_KEY
docker-compose up -d

# Ingest roadmap data
python cognee_pilot/ingest.py
python mem0_pilot/ingest.py

# Ingest Obsidian vault
python obsidian_bridge/ingest_vault.py ~/Documents/Obsidian

# Server is live at http://localhost:8765
# Import n8n workflows from n8n/
```

## Hetzy PhD Integration

Hetzy PhD bot can POST milestones directly:

```bash
curl -X POST http://localhost:8765/proof/log/milestone \
  -H "Content-Type: application/json" \
  -d '{
    "milestone_id": "PhD-3.1",
    "title": "Personality Analysis Complete",
    "description": "Hard problem resolved by bestowed personality concept",
    "evidence": ["09-PERSONALITY.md complete", "F29 finding logged"],
    "phd_phase": "3",
    "legislature_phase": "",
    "agent_id": "hetzy_phd"
  }'
```

## n8n Workflows

Import from `phd-triune-monism/pilots/cognee-mem0/n8n/`:
- `workflow_roadmap_query.json` — query the router via webhook
- `workflow_proof_logger.json` — log milestones via webhook

## Status

| Component | Status |
|---|---|
| Data (3 CSV tables, 36 entities) | ✓ Complete |
| Cognee pilot (graph) | ✓ Complete |
| Mem0 pilot (vector) | ✓ Complete |
| Hybrid router | ✓ Complete |
| FastAPI server | ✓ Complete |
| Proof logger (Legislature Phase 5) | ✓ Complete |
| Obsidian bridge | ✓ Complete |
| n8n workflows | ✓ Complete |
| Docker Compose | ✓ Complete |
| Benchmark + comparison report | ✓ Complete |
| **Obsidian vault ingestion** | ⏳ Run manually |
| **Benchmark results** | ⏳ Run `benchmark.py` |
