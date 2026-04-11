#!/usr/bin/env bash
# MacBook Pro M1 Terminal Setup — Mircea Constellation (web)
# UrantiOS governed — Truth, Beauty, Goodness
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }

echo ""
echo "================================================="
echo "  MacBook Pro M1 Terminal Setup"
echo "  Mircea Constellation (web project)"
echo "================================================="
echo ""

# ── 1. Homebrew ──────────────────────────────────────────────────────────────
info "[1/3] Homebrew (arm64)..."
if ! command -v brew &>/dev/null; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv)"
  ok "Homebrew installed."
else
  brew update --quiet
  ok "Homebrew up to date."
fi

# ── 2. Web dev tools ─────────────────────────────────────────────────────────
info "[2/3] Web dev tools..."
brew install node git || true
npm install -g serve 2>/dev/null || true
ok "node: $(node --version)  serve: $(npx serve --version 2>/dev/null || echo 'installed')"

# ── 3. Local preview ─────────────────────────────────────────────────────────
info "[3/3] Local preview options:"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo ""
echo "  Option A — static file server (recommended):"
echo "    cd $REPO_DIR"
echo "    npx serve ."
echo "    # then open http://localhost:3000"
echo ""
echo "  Option B — open directly in browser:"
echo "    open $REPO_DIR/index.html"
echo ""

echo "================================================="
echo "  Mircea Constellation M1 Setup Complete!"
echo "================================================="
echo ""
