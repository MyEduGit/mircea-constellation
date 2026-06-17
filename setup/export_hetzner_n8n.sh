#!/usr/bin/env bash
# export_hetzner_n8n.sh
# Exports ALL n8n workflows from the Hetzner VPS (46.225.51.30)
# and saves them to mircea-constellation and Obsidian.
#
# Run from your iMac:  bash ~/mircea-constellation/setup/export_hetzner_n8n.sh

set -euo pipefail

HETZNER="mircea@46.225.51.30"
TIMESTAMP=$(date +%Y-%m-%d)
LOCAL_REPO="$HOME/mircea-constellation/council/n8n_exports"
LOCAL_OBSIDIAN="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/UrantiPedia/02_OpenClaw/n8n_workflows"

echo "=== Hetzner n8n Export — $TIMESTAMP ==="
echo ""

# ── 1. Check SSH connectivity ──────────────────────────────────────────────
echo "[1] Testing SSH to $HETZNER ..."
ssh -o ConnectTimeout=10 -o BatchMode=yes "$HETZNER" "echo '    SSH OK'" || {
  echo "ERROR: Cannot SSH to Hetzner. Check key auth."
  exit 1
}

# ── 2. Detect n8n (native vs Docker) and export ───────────────────────────
echo ""
echo "[2] Detecting n8n on Hetzner ..."
ssh "$HETZNER" bash <<'REMOTE'
set -e
EXPORT_DIR="/tmp/n8n-export-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$EXPORT_DIR"
echo "    Export dir: $EXPORT_DIR"

# Try Docker first (most likely)
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q n8n; then
  N8N_CONTAINER=$(docker ps --format '{{.Names}}' | grep n8n | head -1)
  echo "    Found Docker container: $N8N_CONTAINER"
  docker exec "$N8N_CONTAINER" n8n export:workflow --all --output=/tmp/n8n-wf-export/ 2>&1
  docker cp "$N8N_CONTAINER:/tmp/n8n-wf-export/" "$EXPORT_DIR/workflows/"
  echo "    Workflows exported via Docker."
elif command -v n8n &>/dev/null; then
  echo "    Found native n8n"
  n8n export:workflow --all --output="$EXPORT_DIR/workflows/"
  echo "    Workflows exported via native n8n."
elif curl -sf http://localhost:5678/healthz &>/dev/null; then
  echo "    n8n reachable on :5678 but CLI unavailable — trying API..."
  mkdir -p "$EXPORT_DIR/workflows"
  # Try without API key (community edition default)
  curl -sf http://localhost:5678/api/v1/workflows \
    -H "accept: application/json" \
    -o "$EXPORT_DIR/workflows/all_workflows.json" && \
    echo "    API export OK." || \
    echo "    WARN: API export requires an API key — see step 4 below."
else
  echo "    WARN: n8n not found via Docker, native, or API."
  echo "    Is n8n running? Try: docker ps | grep n8n"
fi

# Also dump docker-compose files for reference
find /root /home/mircea ~/mircea-constellation -name "docker-compose*" -name "*n8n*" 2>/dev/null \
  | head -5 \
  | xargs -I{} cp {} "$EXPORT_DIR/" 2>/dev/null || true

echo "$EXPORT_DIR"
REMOTE

# ── 3. SCP the export back ────────────────────────────────────────────────
echo ""
echo "[3] Fetching exports from Hetzner ..."
REMOTE_DIR=$(ssh "$HETZNER" "ls -td /tmp/n8n-export-* 2>/dev/null | head -1")
if [[ -z "$REMOTE_DIR" ]]; then
  echo "ERROR: No export directory found on Hetzner. Check step 2 output above."
  exit 1
fi

mkdir -p "$LOCAL_REPO"
scp -r "$HETZNER:$REMOTE_DIR/." "$LOCAL_REPO/export-$TIMESTAMP/"
echo "    Saved to: $LOCAL_REPO/export-$TIMESTAMP/"

# ── 4. Copy workflow JSONs to Obsidian ────────────────────────────────────
echo ""
echo "[4] Copying to Obsidian vault ..."
mkdir -p "$LOCAL_OBSIDIAN"
find "$LOCAL_REPO/export-$TIMESTAMP/" -name "*.json" | while read -r f; do
  BASE=$(basename "$f" .json)
  DEST="$LOCAL_OBSIDIAN/HETZY_${BASE}_${TIMESTAMP}.json"
  cp "$f" "$DEST"
  echo "    → $DEST"
done

# ── 5. Git commit ──────────────────────────────────────────────────────────
echo ""
echo "[5] Committing to git ..."
cd "$HOME/mircea-constellation"
git add council/n8n_exports/
git commit -m "chore: export n8n workflows from Hetzner $TIMESTAMP" 2>/dev/null || \
  echo "    (nothing new to commit)"

# ── 6. Summary ────────────────────────────────────────────────────────────
echo ""
echo "=== Done ==="
WCOUNT=$(find "$LOCAL_REPO/export-$TIMESTAMP/" -name "*.json" | wc -l | tr -d ' ')
echo "    $WCOUNT file(s) exported"
echo "    Repo:    $LOCAL_REPO/export-$TIMESTAMP/"
echo "    Obsidian: $LOCAL_OBSIDIAN/"
echo ""
echo "NEXT: If 0 workflows exported, n8n may need an API key."
echo "  1. Open n8n: ssh -L 5678:localhost:5678 $HETZNER then visit http://localhost:5678"
echo "  2. Settings → API → Create API Key"
echo "  3. Re-run with: N8N_API_KEY=<key> bash export_hetzner_n8n.sh"
