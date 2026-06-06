#!/usr/bin/env python3
"""
Constellation Memory Ingestion
Adds Mircea’s Constellation infrastructure nodes into Mem0
(the nodes/services shown in index.html status map).

Run this AFTER the main roadmap ingestion in phd-triune-monism.

Usage:
    python ingest_constellation.py

UrantiOS: Truth · Beauty · Goodness
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MEM0_CONFIG = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "constellation_infra",
            "host": "localhost",
            "port": 6333,
            "embedding_model_dims": 1536,
        },
    },
    "llm": {
        "provider": "openai",
        "config": {"model": "gpt-4o-mini", "temperature": 0, "api_key": OPENAI_API_KEY},
    },
    "embedder": {
        "provider": "openai",
        "config": {"model": "text-embedding-3-small", "api_key": OPENAI_API_KEY},
    },
}

USER_ID  = "mircea"
AGENT_ID = "constellation_bridge_v1"

# Infrastructure nodes from index.html
NODES = [
    {
        "id": "imac",
        "label": "iMac M4",
        "role": "Controller Node",
        "description": "Primary controller. Hosts AMEP Hub (:18802), Fleet Bus (:18801), Dashboard (:18800). Tailscale IP 100.75.177.36. User mircea8me.com.",
        "type": "controller",
        "status": "ok",
    },
    {
        "id": "openclaw",
        "label": "OpenClaw",
        "role": "Execution Node",
        "description": "Hetzner CPX22 8GB/80GB. IP 46.225.51.30. Ports 18789/18791/18792. Hosts 9 active Telegram bots. Location: Nuremberg.",
        "type": "server",
        "status": "ok",
    },
    {
        "id": "urantios",
        "label": "URANTiOS Prime",
        "role": "AI Execution + Website Server",
        "description": "Hetzner CCX23 16GB/160GB. IP 204.168.143.98. Runs NanoClaw v1.2.17 Docker. Gabriel brain on port 18900. Hosts UrantiPedia.org and .com. Location: Helsinki.",
        "type": "server",
        "status": "ok",
    },
    {
        "id": "nanoclaw",
        "label": "NanoClaw v1.2.17",
        "role": "Docker Agent Executor",
        "description": "Docker-isolated autonomous agent on URANTiOS Prime. Bot @nanoclaw_openclaw_bot. Uses Claude SDK. Triggered by @NanoClaw mention. Status: LIVE.",
        "type": "server",
        "status": "ok",
    },
    {
        "id": "gabriel",
        "label": "Gabriel",
        "role": "Bright and Morning Star Agent",
        "description": "Spirit domain representative. Brain on port 18900. Floating chat on UrantiPedia website. Authority: joint with Mircea. Governs UrantiPedia content.",
        "type": "bot",
        "status": "ok",
    },
    {
        "id": "hetzy",
        "label": "Hetzy PhD",
        "role": "Fleet Commander + PhD Research Bot",
        "description": "@Hetzy_PhD_bot. Fleet commander managing 10 bots. Autonomous 30-minute cycles. Check-ins every 2 hours. Logs PhD milestones to proof logger.",
        "type": "bot",
        "status": "ok",
    },
    {
        "id": "botfleet",
        "label": "Bot Fleet",
        "role": "Operational Agent Layer",
        "description": "11 Telegram bots total (10 active). Governed by UrantiOS v1.0. Commander: Hetzy PhD. Gateway: UrantiPedia Agent @UrantiPedia_Agent_01_bot (user ID 828807562).",
        "type": "bot",
        "status": "ok",
    },
    {
        "id": "urantipedia",
        "label": "UrantiPedia",
        "role": "Knowledge Publishing Platform",
        "description": "UrantiPedia.org and .com. Contains 196+ Urantia Book papers + Foreword. 477 personalities. 900 concepts. SSL via Certbot. Gabriel manages content.",
        "type": "service",
        "status": "ok",
    },
    {
        "id": "amep",
        "label": "AMEP Hub",
        "role": "Education Platform",
        "description": "Australian Mathematics Education Program. 21 students: Cert I (7) + Cert II (9) + Cert III (5). Class CP123E3/4. Hosted on iMac M4 port 18802 via Tailscale.",
        "type": "service",
        "status": "ok",
    },
    {
        "id": "ollama",
        "label": "Ollama",
        "role": "Local AI Reasoning",
        "description": "Runs qwen2.5:32b on URANTiOS Prime. 16GB RAM dedicated. Used for local reasoning tasks that don’t need Claude API.",
        "type": "service",
        "status": "warn",
    },
    {
        "id": "obsidian",
        "label": "Obsidian",
        "role": "Knowledge Vault",
        "description": "Primary research workspace on iMac M4. Syncs to Hetzner vault every 10 minutes. Bridges to Mem0 via obsidian_bridge. Contains PhD diary + TOE_DIARY + all research notes.",
        "type": "service",
        "status": "ok",
    },
    {
        "id": "iphone",
        "label": "iPhone 16 Pro",
        "role": "Remote Control",
        "description": "iPhone 16 Pro Max 256GB. Primary remote control for entire Constellation. Apps: Telegram (user 828807562), Claude, Termius. Full command access.",
        "type": "controller",
        "status": "ok",
    },
]


def node_to_text(node: dict) -> str:
    return (
        f"Constellation node: {node['label']} ({node['id']}). "
        f"Role: {node['role']}. "
        f"{node['description']} "
        f"Type: {node['type']}. Status: {node['status']}."
    )


def main():
    from mem0 import Memory
    m = Memory.from_config(MEM0_CONFIG)

    print("=" * 60)
    print("CONSTELLATION MEMORY INGESTION")
    print(f"Ingesting {len(NODES)} infrastructure nodes...")
    print("UrantiOS: Truth · Beauty · Goodness")
    print("=" * 60)

    t0 = time.time()
    added = 0
    for node in NODES:
        text = node_to_text(node)
        try:
            m.add(
                [{"role": "user", "content": text}],
                user_id=USER_ID,
                agent_id=AGENT_ID,
                metadata={"source": "constellation", **node},
            )
            print(f"  + {node['label']} ({node['id']})")
            added += 1
        except Exception as exc:
            print(f"  [warn] {node['id']}: {exc}")

    elapsed = time.time() - t0
    total = len(m.get_all(user_id=USER_ID) or [])
    print(f"\n[mem0] {added}/{len(NODES)} nodes ingested in {elapsed:.1f}s")
    print(f"[mem0] Total memories: {total}")
    print()
    print("Sample queries now available:")
    print('  "What runs on URANTiOS Prime?"')
    print('  "Which nodes are controllers?"')
    print('  "What does Hetzy PhD do?"')
    print('  "Show all services with warn status"')


if __name__ == "__main__":
    main()
