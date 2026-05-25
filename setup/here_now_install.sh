#!/usr/bin/env bash
# here.now Install — publish Mircea's Constellation dashboard to a live URL
# UrantiOS governed — Truth, Beauty, Goodness
# Context: Mircea's Constellation — makes the dashboard shareable via
#          https://{slug}.here.now/
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STAGE_DIR="${REPO_DIR}/.here-now-site"
STATE_DIR="${REPO_DIR}/.herenow"
SKIP_PUBLISH="${HERENOW_SKIP_PUBLISH:-0}"
CLIENT_TAG="${HERENOW_CLIENT:-herenow/mircea-constellation}"

echo ""
echo "================================================="
echo "  here.now Install"
echo "  Mircea's Constellation — publish dashboard"
echo "================================================="
echo ""

# ── 1. Dependency check ────────────────────────────────────────────────────
info "[1/5] Checking dependencies (node, npx, curl, file, jq)..."
missing=()
for bin in node npx curl file jq; do
  command -v "$bin" >/dev/null 2>&1 || missing+=("$bin")
done
if [ "${#missing[@]}" -gt 0 ]; then
  fail "Missing required binaries: ${missing[*]}. Install them and re-run."
fi
ok "All required binaries on PATH."

# ── 2. Install / update the here.now skill ─────────────────────────────────
info "[2/5] Installing here.now agent skill (npx skills add heredotnow/skill)..."
SKILL_AGENT="${HERENOW_SKILL_AGENT:-claude-code}"
if ! npx --yes skills add heredotnow/skill --skill here-now --agent "${SKILL_AGENT}" -g -y; then
  fail "npx skills add failed. Check network + npx availability."
fi
ok "here.now skill installed."

# Resolve skill directory. Honour override, then walk common locations.
resolve_skill_dir() {
  if [ -n "${HERENOW_SKILL_DIR:-}" ] && [ -x "${HERENOW_SKILL_DIR}/scripts/publish.sh" ]; then
    printf '%s\n' "${HERENOW_SKILL_DIR}"
    return 0
  fi
  local candidates=(
    "${HOME}/.claude/skills/here-now"
    "${HOME}/.claude/skills/heredotnow/here-now"
    "${HOME}/.claude/skills/heredotnow-skill/here-now"
    "${XDG_DATA_HOME:-${HOME}/.local/share}/claude/skills/here-now"
    "${XDG_DATA_HOME:-${HOME}/.local/share}/skills/here-now"
  )
  for c in "${candidates[@]}"; do
    [ -x "${c}/scripts/publish.sh" ] && { printf '%s\n' "$c"; return 0; }
  done
  # Last resort: find the first publish.sh under any skills/here-now directory.
  local hit
  hit="$(find "${HOME}/.claude/skills" "${XDG_DATA_HOME:-${HOME}/.local/share}" \
           -maxdepth 6 -type f -name publish.sh -path '*/here-now/scripts/publish.sh' \
           -print 2>/dev/null | head -n1)"
  if [ -n "${hit}" ]; then
    printf '%s\n' "$(dirname "$(dirname "${hit}")")"
    return 0
  fi
  return 1
}

if ! SKILL_DIR="$(resolve_skill_dir)"; then
  fail "Could not locate installed here-now skill. Set HERENOW_SKILL_DIR=/path/to/here-now."
fi
ok "Skill directory: ${SKILL_DIR}"

# ── 3. Stage the dashboard ─────────────────────────────────────────────────
info "[3/5] Staging dashboard into ${STAGE_DIR}..."
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}"
cp "${REPO_DIR}/index.html" "${STAGE_DIR}/index.html"
cp "${REPO_DIR}/status.json" "${STAGE_DIR}/status.json"
ok "Staged index.html + status.json."

# ── 4. Publish ─────────────────────────────────────────────────────────────
if [ "${SKIP_PUBLISH}" = "1" ]; then
  warn "HERENOW_SKIP_PUBLISH=1 — skipping publish step."
  SITE_URL=""
  AUTH_MODE="skipped"
else
  info "[4/5] Publishing via here.now (client=${CLIENT_TAG})..."
  mkdir -p "${STATE_DIR}"
  cd "${REPO_DIR}"

  STDERR_LOG="$(mktemp)"
  trap 'rm -f "${STDERR_LOG}"' EXIT

  # Reuse prior slug if we've published before.
  EXTRA_ARGS=()
  if [ -f "${STATE_DIR}/state.json" ]; then
    prev_slug="$(jq -r '.publishes | to_entries | .[0].key // empty' "${STATE_DIR}/state.json" 2>/dev/null || true)"
    if [ -n "${prev_slug}" ]; then
      info "Re-publishing to existing slug: ${prev_slug}"
      EXTRA_ARGS+=(--slug "${prev_slug}")
    fi
  fi

  if ! SITE_URL="$("${SKILL_DIR}/scripts/publish.sh" \
                    "${STAGE_DIR}" \
                    --client "${CLIENT_TAG}" \
                    "${EXTRA_ARGS[@]}" \
                    2> "${STDERR_LOG}")"; then
    cat "${STDERR_LOG}" >&2
    fail "here.now publish failed."
  fi

  SITE_URL="$(echo "${SITE_URL}" | tail -n1 | tr -d '[:space:]')"
  AUTH_MODE="$(awk -F= '/^publish_result\.auth_mode=/{print $2; exit}' "${STDERR_LOG}" 2>/dev/null || true)"
  CLAIM_URL="$(awk -F= '/^publish_result\.claim_url=/{print $2; exit}' "${STDERR_LOG}" 2>/dev/null || true)"
  EXPIRES_AT="$(awk -F= '/^publish_result\.expires_at=/{print $2; exit}' "${STDERR_LOG}" 2>/dev/null || true)"

  [ -z "${SITE_URL}" ] && fail "Publish succeeded but no siteUrl was returned."
  [ -z "${AUTH_MODE}" ] && AUTH_MODE="anonymous"
  ok "Published: ${SITE_URL}  (auth: ${AUTH_MODE})"
fi

# ── 5. Record URL in status.json ──────────────────────────────────────────
info "[5/5] Recording site URL in status.json..."
STATUS_FILE="${REPO_DIR}/status.json"
TMP_STATUS="$(mktemp)"
NOW_ISO="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"

jq --arg url "${SITE_URL:-}" \
   --arg mode "${AUTH_MODE:-unknown}" \
   --arg now "${NOW_ISO}" \
   '.here_now = {
      status: (if ($url == "") then "new" else "ok" end),
      site_url: (if ($url == "") then null else $url end),
      auth_mode: $mode
    }
    | .updated = $now' \
   "${STATUS_FILE}" > "${TMP_STATUS}"
mv "${TMP_STATUS}" "${STATUS_FILE}"
ok "status.json updated."

echo ""
echo "================================================="
echo "  here.now Install Complete"
echo "================================================="
echo ""
if [ -n "${SITE_URL:-}" ]; then
  echo "  Site URL:       ${SITE_URL}"
  echo "  Auth mode:      ${AUTH_MODE}"
  if [ "${AUTH_MODE}" = "anonymous" ]; then
    echo ""
    echo "  This site expires in 24 hours."
    [ -n "${CLAIM_URL:-}" ] && [[ "${CLAIM_URL}" == https://* ]] && \
      echo "  Claim URL (one-time, save it now):"
    [ -n "${CLAIM_URL:-}" ] && [[ "${CLAIM_URL}" == https://* ]] && \
      echo "    ${CLAIM_URL}"
    echo ""
    echo "  To make it permanent:"
    echo "    1. Get an API key at https://here.now"
    echo "    2. mkdir -p ~/.herenow && echo KEY > ~/.herenow/credentials && chmod 600 ~/.herenow/credentials"
    echo "    3. Re-run this installer."
  fi
else
  echo "  Publish skipped (HERENOW_SKIP_PUBLISH=1)."
fi
echo ""
echo "  Skill dir:      ${SKILL_DIR}"
echo "  Stage dir:      ${STAGE_DIR}"
echo "  Local state:    ${STATE_DIR}/state.json  (never commit)"
echo "  Docs:           https://here.now/docs"
echo ""
echo "  Re-publish:     bash setup/here_now_install.sh"
echo "  Skip publish:   HERENOW_SKIP_PUBLISH=1 bash setup/here_now_install.sh"
echo ""
echo "  UrantiOS governed — Truth, Beauty, Goodness"
echo ""
