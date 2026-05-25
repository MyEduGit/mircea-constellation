#!/usr/bin/env bash
# Fireclaw Install — remediation & incident-response layer
# UrantiOS governed — Truth, Beauty, Goodness
# Date: 2026-04-15
# Context: Mircea's Constellation
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${FIRECLAW_VENV:-${REPO_DIR}/.fireclaw-env}"
STATE_DIR="${HOME}/.fireclaw"

echo ""
echo "================================================="
echo "  Fireclaw Install"
echo "  Mircea's Constellation — remediation layer"
echo "================================================="
echo ""

# ── 1. Python ──────────────────────────────────────────────────────────────
info "[1/5] Checking Python (>= 3.10)..."
PY="$(command -v python3 || true)"
[ -n "$PY" ] || fail "python3 not on PATH."
PY_VERSION=$("$PY" --version 2>&1 | awk '{print $2}')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -ne 3 ] || [ "$PY_MINOR" -lt 10 ]; then
  fail "Python $PY_VERSION too old (need >= 3.10)."
fi
ok "Python $PY_VERSION at $PY"

# ── 2. venv ────────────────────────────────────────────────────────────────
info "[2/5] Virtual environment at $VENV..."
if [ -d "$VENV" ]; then
  ok "venv already exists."
else
  "$PY" -m venv "$VENV"
  ok "Created venv."
fi
# shellcheck source=/dev/null
. "$VENV/bin/activate"

# ── 3. Dependencies ────────────────────────────────────────────────────────
info "[3/5] Installing dependencies (pyyaml; psycopg2-binary optional)..."
pip install --quiet --upgrade pip
pip install --quiet pyyaml
# Postgres driver is optional — Fireclaw degrades gracefully without it.
if ! pip install --quiet psycopg2-binary 2>/dev/null; then
  warn "psycopg2-binary install skipped — NemoClaw signal will be unavailable."
fi
ok "Dependencies installed."

# ── 4. State directory ─────────────────────────────────────────────────────
info "[4/5] State directory at $STATE_DIR..."
mkdir -p "$STATE_DIR" "$STATE_DIR/quarantine"
[ -f "$STATE_DIR/incidents.jsonl" ] || : > "$STATE_DIR/incidents.jsonl"
ok "State ready."

# ── 5. Smoke test (dry-run, single cycle) ──────────────────────────────────
info "[5/5] Smoke test — module import + dry-run cycle..."
cd "$REPO_DIR"
python3 -c "from fireclaw import fireclaw, actions, signals; print('FIRECLAW_IMPORT_OK', fireclaw.__doc__.splitlines()[0])"
python3 -m fireclaw.fireclaw --dry-run --once --verbose || \
  warn "Dry-run reported failures (expected if some signals legitimately fail)."
ok "Smoke test complete."

echo ""
echo "================================================="
echo "  Fireclaw Install Complete"
echo "================================================="
echo ""
echo "  venv:           $VENV"
echo "  Activate:       source $VENV/bin/activate"
echo "  Rules:          $REPO_DIR/fireclaw/rules.yaml"
echo "  State:          $STATE_DIR"
echo "  Incident log:   $STATE_DIR/incidents.jsonl"
echo ""
echo "  Run modes:"
echo "    Dry-run:      python3 -m fireclaw.fireclaw --dry-run --once -v"
echo "    Execute:      python3 -m fireclaw.fireclaw --execute --once -v"
echo "    Loop:         python3 -m fireclaw.fireclaw --execute --loop --interval 60"
echo ""
echo "  systemd (Linux only — explicit step, not auto-enabled):"
echo "    sudo cp $REPO_DIR/fireclaw/fireclaw.service /etc/systemd/system/"
echo "    sudo systemctl daemon-reload && sudo systemctl enable --now fireclaw"
echo ""
echo "  UrantiOS governed — Truth, Beauty, Goodness"
echo ""
