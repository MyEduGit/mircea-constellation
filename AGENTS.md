# AGENTS.md

## Canonical Paths

- Repo workspace: `/Users/mircea8me.com/mircea-constellation`
- Primary local Obsidian vault alias: `/Users/mircea8me.com/Obsidian/UrantiPedia`
- Backing iCloud Obsidian path uses `iCloud~md~obsidian`, not `iCloudmdobsidian`
- Treat `/Users/mircea8me.com/Documents/Obsidian/PhD-Triune-Monism` as a secondary checkout until diffed against the primary vault corpus

## Working Rules

- Keep this repo local-first, deterministic, and auditable
- Prefer file-first inventory and staging work before model-centric or speculative architecture changes
- For ingest/discovery work, stage outputs under `openclaw_ingest/out/` before any placement or move phase
- Use concrete repo files and commands as evidence; if a workflow is unclear, add a TODO instead of inventing behavior

## Current Repo-Grounded Workflows

### OpenClaw ingest

- Install on the target host from the repo root:
  - `bash setup/openclaw_ingest_install.sh`
- Autopilot deploy path for ingestion changes:
  - `.github/workflows/deploy-urantios.yml`
  - Manual trigger from GitHub Actions: `Deploy OpenClaw@URANTiOS-ingest`
- Verify:
  - `docker logs openclaw-ingest --tail 30`
  - `curl -s http://127.0.0.1:8080/health | python3 -m json.tool`
  - `ls -l /opt/openclaw-data/evidence/`
- Invoke an allowlisted handler locally:
  - `curl -s -X POST http://127.0.0.1:8080/tasks -H 'Content-Type: application/json' -d '{"handler":"ingest_normalize","payload":{}}' | python3 -m json.tool`
  - `curl -s -X POST http://127.0.0.1:8080/tasks -H 'Content-Type: application/json' -d '{"handler":"categorise_by_axes","payload":{}}' | python3 -m json.tool`
- Deterministic local outputs already used by this repo:
  - `openclaw_ingest/out/vault_manifest.jsonl`
  - `openclaw_ingest/out/vault_manifest_summary.json`
  - `openclaw_ingest/out/research_corpora_diff.json`
  - `openclaw_ingest/out/research_corpora_diff_summary.json`
  - `openclaw_ingest/out/external_import_manifest.jsonl`
  - `openclaw_ingest/out/external_import_skipped.jsonl`
  - `openclaw_ingest/out/external_import_summary.json`
  - `openclaw_ingest/out/external_segments_manifest.jsonl`
  - `openclaw_ingest/out/external_segments_summary.json`
  - `openclaw_ingest/out/external_segments_parse_errors.jsonl`

### Claw services

- Fireclaw:
  - `python3 -m fireclaw.fireclaw --dry-run --once`
  - `python3 -m fireclaw.fireclaw --execute --once`
  - `python3 -m fireclaw.fireclaw --execute --loop --interval 60`
  - `bash setup/fireclaw_install.sh`
- LuciferiClaw:
  - `python3 -m lucifericlaw.lucifericlaw assess agent_42 --evidence ./tests/fixtures/agent_42.jsonl`
  - `python3 -m lucifericlaw.lucifericlaw open agent_42 --evidence ./tests/fixtures/agent_42.jsonl`
  - `python3 -m lucifericlaw.lucifericlaw notice L-... --message "You are under formal adjudication. Patience grant begins now."`
  - `python3 -m lucifericlaw.lucifericlaw sentence L-... --action quarantine --revoke shell,network --execute`
  - `python3 -m lucifericlaw.lucifericlaw open <agent_id> --evidence <fireclaw_incident_log> --from-fireclaw`
  - `python3 -m lucifericlaw.lucifericlaw doctrine`
  - `python3 -m lucifericlaw.lucifericlaw scripture`
- ScribeClaw:
  - `bash setup/scribeclaw_install.sh`
  - `curl -s http://127.0.0.1:8081/health | python3 -m json.tool`
  - `curl -sX POST http://127.0.0.1:8081/tasks -H 'Content-Type: application/json' -d '{"handler":"media_edit","payload":{"input":"interviu.mp4","loudnorm":true,"remove_silence":true}}'`
  - `docker exec -it scribeclaw python -m scribeclaw.main --mode pipeline --input interviu.mp4`
- SeedanceClaw:
  - `bash setup/seedanceclaw_install.sh`
  - `curl -s http://127.0.0.1:8086/health | python3 -m json.tool`
  - `curl -sX POST http://127.0.0.1:8086/tasks -H 'Content-Type: application/json' -d '{"handler":"smoke_test","payload":{}}'`
  - `curl -sX POST http://127.0.0.1:8086/tasks -H 'Content-Type: application/json' -d '{"handler":"text_to_video","payload":{"prompt":"A golden sunset over the ocean, cinematic, slow pan","duration":5,"aspect_ratio":"16:9","resolution":"720p"}}'`

### Council and operator utilities

- Council import/reference:
  - `council/README.md`
  - `bash setup/claws_boot.sh`
- Council maintenance:
  - `bash setup/council_go.sh`
  - `python3 setup/update_council_models.py --dry-run`
  - `python3 setup/update_council_models.py --seat 6 --dry-run`
  - `bash setup/export_hetzner_n8n.sh`
- Jabbokriver operator workflow:
  - `python channels/jabbokriver/tools/validate_catalog.py`
  - `python channels/jabbokriver/tools/catalog_fetch.py`
  - `python channels/jabbokriver/tools/catalog_fetch.py --execute`
- Fleet diagnostics on the target server:
  - `ssh root@46.225.51.30 'bash -s' < setup/fleet_diagnostic.sh`
- Claude DOC installer:
  - `./setup/claude-doc/install.sh`
  - `./setup/claude-doc/scripts/validate.sh`
  - CI runs validation from `.github/workflows/ci.yml`

## TODO

- If older AGENTS guidance is needed beyond the commands above, rebuild it from current repo files first; do not assume historical sections still match the present checkout.
