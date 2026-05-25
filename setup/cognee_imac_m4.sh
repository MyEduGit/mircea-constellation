#!/usr/bin/env bash
# Cognee Install — iMac M4 (Apple Silicon)
# UrantiOS governed — Truth, Beauty, Goodness
# Date: 2026-04-13
# Context: Mircea — Apple-local / NemoClaw
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

echo ""
echo "================================================="
echo "  Cognee Install — iMac M4"
echo "  Mircea's Constellation / NemoClaw context"
echo "================================================="
echo ""

# ── 1. Python version check ────────────────────────────────────────────────
info "[1/5] Checking Python version (requires 3.10–3.13)..."
PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -ne 3 ] || [ "$PY_MINOR" -lt 10 ] || [ "$PY_MINOR" -gt 13 ]; then
  fail "Python $PY_VERSION is outside Cognee's supported range (3.10–3.13)."
fi
ok "Python $PY_VERSION — within supported range."

# ── 2. uv package manager ──────────────────────────────────────────────────
info "[2/5] Checking uv package manager..."
if command -v uv &>/dev/null; then
  ok "uv found at $(which uv)"
else
  info "Installing uv via Homebrew..."
  if command -v brew &>/dev/null; then
    brew install uv
    ok "uv installed via Homebrew."
  else
    warn "Homebrew not found. Installing uv via pip..."
    python3 -m pip install --upgrade uv
    ok "uv installed via pip."
  fi
fi

# ── 3. Create virtual environment (recommended for iMac) ───────────────────
info "[3/5] Setting up Cognee virtual environment..."
COGNEE_VENV="${HOME}/.cognee-env"
if [ -d "$COGNEE_VENV" ]; then
  ok "Virtual environment already exists at $COGNEE_VENV"
else
  uv venv "$COGNEE_VENV"
  ok "Created virtual environment at $COGNEE_VENV"
fi
source "$COGNEE_VENV/bin/activate"
ok "Activated: $(python3 --version) at $(which python3)"

# ── 4. Install Cognee ──────────────────────────────────────────────────────
info "[4/5] Installing Cognee..."
uv pip install cognee
ok "Cognee installed."

# ── 5. Proof check ─────────────────────────────────────────────────────────
info "[5/5] Verifying import..."
PROOF=$(python3 -c "import cognee; print(f'COGNEE_IMPORT_OK v{cognee.__version__}')" 2>&1)

if echo "$PROOF" | grep -q "COGNEE_IMPORT_OK"; then
  ok "$PROOF"
else
  fail "Import verification failed. Output: $PROOF"
fi

echo ""
echo "================================================="
echo "  Cognee Install Complete — iMac M4"
echo "================================================="
echo ""
echo "  Environment:  $COGNEE_VENV"
echo "  Activate:     source $COGNEE_VENV/bin/activate"
echo "  Python:       $PY_VERSION"
echo "  Cognee:       $(python3 -c 'import cognee; print(cognee.__version__)')"
echo ""
echo "  Next steps:"
echo "    1. Set your LLM API key:"
echo "       export LLM_API_KEY='your-anthropic-key'"
echo "    2. Run the URANTiOS Cognee bootstrap:"
echo "       python3 ~/URANTiOS/pipeline/cognee_bootstrap.py"
echo "    3. Query the knowledge graph:"
echo "       python3 -c \"import asyncio, cognee; print(asyncio.run(cognee.recall('What is the Foreword?')))\""
echo ""
echo "  UrantiOS governed — Truth, Beauty, Goodness"
echo ""
