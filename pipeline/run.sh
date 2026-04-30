#!/usr/bin/env bash
set -u

cd /Users/mircea8me.com/mircea-constellation

echo "=== LOCAL PIPELINE RUN ==="
date '+%A, %d %B %Y — %H:%M:%S %Z'
echo

echo "Stage 1: CrewAI / crew_engine orchestration"
echo "Stage 2: NemoClaw"
if [ -x nemoclaw/run.sh ]; then
  if [ -f ".venv-nemoclaw/bin/activate" ]; then
    source ".venv-nemoclaw/bin/activate"
  fi
  bash nemoclaw/run.sh || true
else
  echo "NemoClaw runner missing or not executable"
fi
echo

echo "Stage 3: OpenClaw visibility"
if [ -d openclaw_ingest ]; then
  echo "FOUND: openclaw_ingest"
else
  echo "MISSING: openclaw_ingest"
fi
echo

echo "Stage 4: Preservation"
bash preservation/run.sh --quick
echo

echo "STATUS: PIPELINE_COMPLETE"
