#!/usr/bin/env bash
# ============================================================
# Council of Seven — Full AI Toolkit Installer
# macOS Apple Silicon (M4) · UrantiOS v1.0
# Truth · Beauty · Goodness
# ============================================================
set -euo pipefail

LOG="$HOME/council-install.log"
KEYS_DIR="$HOME/.council-keys"
KEYS_FILE="$KEYS_DIR/.env"

B="\033[1m"; G="\033[32m"; R="\033[31m"; Y="\033[33m"; C="\033[36m"; E="\033[0m"

ok()   { echo -e "${G}✓${E} $1" | tee -a "$LOG"; }
fail() { echo -e "${R}✗${E} $1" | tee -a "$LOG"; }
info() { echo -e "${C}▶${E} $1" | tee -a "$LOG"; }
warn() { echo -e "${Y}⚠${E}  $1" | tee -a "$LOG"; }
sep()  { echo -e "${B}────────────────────────────────────────${E}" | tee -a "$LOG"; }

echo "" | tee -a "$LOG"
sep
echo -e "${B}  Council of Seven — AI Toolkit Installer${E}" | tee -a "$LOG"
echo -e "  $(date)" | tee -a "$LOG"
sep

# ── 1. Homebrew ──────────────────────────────────────────────
info "Checking Homebrew..."
if command -v brew &>/dev/null; then
    ok "Homebrew already installed ($(brew --version | head -1))"
else
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" >> "$LOG" 2>&1
    eval "$(/opt/homebrew/bin/brew shellenv)"
    ok "Homebrew installed"
fi

# ── 2. Node.js ───────────────────────────────────────────────
info "Checking Node.js..."
if command -v node &>/dev/null; then
    ok "Node.js already installed ($(node --version))"
else
    info "Installing Node.js via Homebrew..."
    brew install node >> "$LOG" 2>&1
    ok "Node.js installed ($(node --version))"
fi

# ── 3. Python 3 ──────────────────────────────────────────────
info "Checking Python 3..."
if command -v python3 &>/dev/null; then
    ok "Python 3 already installed ($(python3 --version))"
else
    info "Installing Python 3 via Homebrew..."
    brew install python3 >> "$LOG" 2>&1
    ok "Python 3 installed"
fi

# ── 4. Claude Code ───────────────────────────────────────────
info "Checking Claude Code..."
if command -v claude &>/dev/null; then
    ok "Claude Code already installed ($(claude --version 2>/dev/null || echo 'installed'))"
else
    info "Installing Claude Code..."
    npm install -g @anthropic-ai/claude-code >> "$LOG" 2>&1
    ok "Claude Code installed"
fi

# ── 5. Ollama ────────────────────────────────────────────────
info "Checking Ollama..."
if command -v ollama &>/dev/null; then
    ok "Ollama already installed ($(ollama --version 2>/dev/null || echo 'installed'))"
else
    info "Installing Ollama via Homebrew..."
    brew install ollama >> "$LOG" 2>&1
    ok "Ollama installed"
fi

# Start Ollama in background if not running
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    info "Starting Ollama service..."
    ollama serve >> "$LOG" 2>&1 &
    sleep 3
fi

# ── 6. Local Models ──────────────────────────────────────────
sep
info "Pulling local models (this may take a while)..."

pull_model() {
    local model="$1"
    local seat="$2"
    if ollama list 2>/dev/null | grep -q "^$model"; then
        ok "$model already pulled ($seat)"
    else
        info "Pulling $model ($seat)..."
        ollama pull "$model" >> "$LOG" 2>&1 && ok "$model pulled" || fail "$model pull failed"
    fi
}

pull_model "gemma3"    "Seat 4 — Father-Son"
pull_model "mistral"   "Seat 6 backup"
pull_model "deepseek-v3" "Seat 5 — Father-Spirit (local)"

# ── 7. Google Cloud CLI ──────────────────────────────────────
info "Checking Google Cloud CLI..."
if command -v gcloud &>/dev/null; then
    ok "gcloud already installed"
else
    info "Installing Google Cloud CLI..."
    brew install --cask google-cloud-sdk >> "$LOG" 2>&1 && ok "gcloud installed" || warn "gcloud install failed — install manually from cloud.google.com/sdk"
fi

# ── 8. n8n CLI ───────────────────────────────────────────────
info "Checking n8n CLI..."
if command -v n8n &>/dev/null; then
    ok "n8n CLI already installed ($(n8n --version 2>/dev/null || echo 'installed'))"
else
    info "Installing n8n CLI..."
    npm install -g n8n >> "$LOG" 2>&1 && ok "n8n CLI installed" || warn "n8n CLI install failed"
fi

# ── 9. API Keys Template ─────────────────────────────────────
sep
info "Setting up credentials directory..."
mkdir -p "$KEYS_DIR"
chmod 700 "$KEYS_DIR"

if [ ! -f "$KEYS_FILE" ]; then
    cat > "$KEYS_FILE" << 'TEMPLATE'
# Council of Seven — API Keys
# Governed by UrantiOS v1.0 — Truth · Beauty · Goodness
# ⚠️  NEVER commit this file. NEVER share this file.
# Fill in real values. Keep this file at: ~/.council-keys/.env

# ── Seat 1 — Father / GPT (OpenAI) ──────────────────────────
OPENAI_API_KEY=REPLACE_WITH_OPENAI_KEY
OPENAI_MODEL=gpt-4o

# ── Seat 2 — Son / Claude (Anthropic) ───────────────────────
ANTHROPIC_API_KEY=REPLACE_WITH_ANTHROPIC_KEY
ANTHROPIC_MODEL=claude-sonnet-4-6

# ── Seat 3 — Spirit / Gemini (Google) ───────────────────────
GOOGLE_API_KEY=REPLACE_WITH_GOOGLE_KEY
GEMINI_MODEL=gemini-1.5-pro

# ── Seat 4 — Father-Son / Gemma (Ollama local) ──────────────
OLLAMA_HOST=http://204.168.143.98:11434
GEMMA_MODEL=gemma3

# ── Seat 5 — Father-Spirit / DeepSeek ───────────────────────
DEEPSEEK_API_KEY=REPLACE_WITH_DEEPSEEK_KEY
DEEPSEEK_MODEL=deepseek-chat

# ── Seat 6 — Son-Spirit / GLM (Z.ai) ────────────────────────
Z_AI_API_KEY=edb15cda3c5048cd8888ddcf593bfbe8.6uHApX9qKFtnrDqS
GLM_MODEL=glm-4

# ── Seat 7 — Trinity / Grok (xAI) ───────────────────────────
XAI_API_KEY=REPLACE_WITH_XAI_KEY
GROK_MODEL=grok-2

# ── Gabriel — Synthesizer / Claude ──────────────────────────
GABRIEL_MODEL=claude-sonnet-4-6
# Uses ANTHROPIC_API_KEY above

# ── n8n ─────────────────────────────────────────────────────
N8N_EMAIL=mircea8@me.com
N8N_PASSWORD=REPLACE_WITH_N8N_PASSWORD
N8N_URL=http://46.225.51.30
N8N_API_KEY=REPLACE_WITH_N8N_API_KEY

# ── Servers ─────────────────────────────────────────────────
OPENCLAW_HOST=46.225.51.30
URANTIOS_HOST=204.168.143.98
TEMPLATE
    chmod 600 "$KEYS_FILE"
    ok "Created ~/.council-keys/.env (fill in REPLACE_WITH_* values)"
else
    ok "~/.council-keys/.env already exists — not overwriting"
fi

# ── 10. Status Report ────────────────────────────────────────
sep
echo -e "${B}  INSTALLATION REPORT${E}" | tee -a "$LOG"
sep

check() {
    local name="$1"; local cmd="$2"
    if command -v $cmd &>/dev/null; then
        ok "$name"
    else
        fail "$name — NOT FOUND"
    fi
}

check "Homebrew"    "brew"
check "Node.js"     "node"
check "Python 3"    "python3"
check "Claude Code" "claude"
check "Ollama"      "ollama"
check "gcloud CLI"  "gcloud"
check "n8n CLI"     "n8n"

sep
echo -e "${B}  LOCAL MODELS${E}" | tee -a "$LOG"
ollama list 2>/dev/null | tee -a "$LOG" || warn "Ollama not running"

sep
echo ""
echo -e "${G}${B}Council toolkit install complete.${E}"
echo -e "Log saved to: ${C}$LOG${E}"
echo -e "Keys template: ${C}$KEYS_FILE${E}"
echo ""
echo -e "Next: fill in ${Y}REPLACE_WITH_*${E} values in ~/.council-keys/.env"
echo -e "Then run: ${C}claude${E} to launch Claude Code"
echo ""
