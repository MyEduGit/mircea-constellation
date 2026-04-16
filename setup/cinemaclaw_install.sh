#!/usr/bin/env bash
# CinemaClaw Install — YouTube video-editing pipeline
# UrantiOS governed — Truth, Beauty, Goodness
# Date: 2026-04-15
# Context: Mircea's Constellation
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# Refuse to run as root — CinemaClaw is a user-scope tool.
if [ "$(id -u)" = "0" ]; then
  fail "Do not run cinemaclaw_install.sh as root. Run as your user."
fi

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${CINEMACLAW_VENV:-${REPO_DIR}/.cinemaclaw-env}"
STATE_DIR="${HOME}/.cinemaclaw"
DATA_ROOT="${CINEMACLAW_DATA:-${HOME}/cinemaclaw}"

echo ""
echo "================================================="
echo "  CinemaClaw Install"
echo "  Mircea's Constellation — video pipeline"
echo "================================================="
echo ""

# ── 1. Python ──────────────────────────────────────────────────────────────
info "[1/6] Checking Python (>= 3.10)..."
PY="$(command -v python3 || true)"
[ -n "$PY" ] || fail "python3 not on PATH."
PY_VERSION=$("$PY" --version 2>&1 | awk '{print $2}')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -ne 3 ] || [ "$PY_MINOR" -lt 10 ]; then
  fail "Python $PY_VERSION too old (need >= 3.10)."
fi
ok "Python $PY_VERSION at $PY"

# ── 2. ffmpeg / ffprobe presence (warn, don't fail — dry-run still works) ─
info "[2/6] Checking ffmpeg / ffprobe..."
if command -v ffmpeg >/dev/null 2>&1; then
  FF_VER=$(ffmpeg -version 2>/dev/null | head -n1)
  ok "ffmpeg: $FF_VER"
else
  warn "ffmpeg not on PATH — dry-run will work; RENDER stages will refuse."
  warn "  Install hint (macOS): brew install ffmpeg"
  warn "  Install hint (Debian/Ubuntu): sudo apt-get install -y ffmpeg"
fi
if command -v ffprobe >/dev/null 2>&1; then
  ok "ffprobe available"
else
  warn "ffprobe not on PATH — the probe stage will refuse."
fi

# ── 3. venv ────────────────────────────────────────────────────────────────
info "[3/6] Virtual environment at $VENV..."
if [ -d "$VENV" ]; then
  ok "venv already exists."
else
  "$PY" -m venv "$VENV"
  ok "Created venv."
fi
# shellcheck source=/dev/null
. "$VENV/bin/activate"

# ── 4. Dependencies ────────────────────────────────────────────────────────
info "[4/6] Installing dependencies (pyyaml)..."
pip install --quiet --upgrade pip
pip install --quiet pyyaml
ok "Dependencies installed."

# ── 5. State + data directories ────────────────────────────────────────────
info "[5/6] State at $STATE_DIR, data under $DATA_ROOT..."
mkdir -p "$STATE_DIR"
[ -f "$STATE_DIR/renders.jsonl" ] || : > "$STATE_DIR/renders.jsonl"
[ -f "$STATE_DIR/audit.jsonl" ]   || : > "$STATE_DIR/audit.jsonl"
mkdir -p "$DATA_ROOT/inbox" "$DATA_ROOT/work" "$DATA_ROOT/outbox"
ok "State + data ready."

# ── 6. Smoke test (imports + --list + --handlers, all safe) ────────────────
info "[6/6] Smoke test — imports + --list + --handlers..."
cd "$REPO_DIR"
python3 -c "from cinemaclaw import cinemaclaw, handlers; \
print('CINEMACLAW_IMPORT_OK', 'handlers=', len(handlers.HANDLERS))"
python3 -m cinemaclaw.cinemaclaw --handlers
python3 -m cinemaclaw.cinemaclaw --list
ok "Smoke test complete."

echo ""
echo "================================================="
echo "  CinemaClaw Install Complete"
echo "================================================="
echo ""
echo "  venv:        $VENV"
echo "  Activate:    source $VENV/bin/activate"
echo "  Pipelines:   $REPO_DIR/cinemaclaw/pipeline.yaml"
echo "  Data root:   $DATA_ROOT  (inbox/ work/ outbox/)"
echo "  State:       $STATE_DIR  (renders.jsonl, audit.jsonl)"
echo ""
echo "  Run modes:"
echo "    List:           python3 -m cinemaclaw.cinemaclaw --list"
echo "    Dry-run demo:   python3 -m cinemaclaw.cinemaclaw --run demo --dry-run -v"
echo "    Execute demo:   python3 -m cinemaclaw.cinemaclaw --run demo --execute -v"
echo ""
echo "  Publication is DRY-ONLY in v0.1.0. Wiring the YouTube Data API"
echo "  is a deliberate follow-up PR. publish_youtube refuses unless"
echo "  YOUTUBE_CLIENT_SECRETS + YOUTUBE_OAUTH_TOKEN are set AND the"
echo "  --signed-by-father flag is passed — and even then v0.1.0 will"
echo "  not hit the API."
echo ""
echo "  UrantiOS governed — Truth, Beauty, Goodness"
echo ""
