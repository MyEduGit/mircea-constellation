#!/usr/bin/env bash
# validate.sh - mirror of .github/workflows/ci.yml, runnable locally.
# Usage:
#   ./setup/claude-doc/scripts/validate.sh           # run all checks
#   ./setup/claude-doc/scripts/validate.sh --quiet   # suppress successful output
# Exit code: 0 if all checks pass, 1 if any fail, 2 if a required tool is missing.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PKG="$REPO_ROOT/setup/claude-doc"
QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

fail=0
missing=0

say()   { [ "$QUIET" -eq 1 ] || printf '\033[1;36m[validate]\033[0m %s\n' "$*"; }
ok()    { [ "$QUIET" -eq 1 ] || printf '\033[1;32m  [ok]\033[0m %s\n' "$*"; }
bad()   { printf '\033[1;31m  [FAIL]\033[0m %s\n' "$*"; fail=1; }
miss()  { printf '\033[1;33m  [MISSING TOOL]\033[0m %s\n' "$*"; missing=1; }

# --- 1. shellcheck ------------------------------------------------------------
say "shellcheck"
if ! command -v shellcheck >/dev/null 2>&1; then
  miss "shellcheck not installed (brew install shellcheck | apt-get install shellcheck)"
else
  shopt -s nullglob
  files=("$PKG/install.sh" "$PKG/hooks/"*.sh "$PKG/scripts/"*.sh)
  if [ "${#files[@]}" -eq 0 ]; then
    ok "no shell scripts to check"
  elif shellcheck "${files[@]}"; then
    ok "all shell scripts clean"
  else
    bad "shellcheck reported issues (see above)"
  fi
fi

# --- 2. JSON validation -------------------------------------------------------
say "JSON validation"
if ! command -v jq >/dev/null 2>&1; then
  miss "jq not installed (brew install jq | apt-get install jq)"
else
  if jq . "$PKG/settings.snippet.json" >/dev/null 2>&1; then
    ok "settings.snippet.json parses"
  else
    bad "settings.snippet.json is invalid JSON"
  fi
fi

# --- 3. Skill frontmatter -----------------------------------------------------
say "skill frontmatter"
skill="$PKG/skills/diagram-on-completion.md"
if [ ! -f "$skill" ]; then
  bad "skill file missing: $skill"
else
  first_line=$(head -n 1 "$skill")
  if [ "$first_line" = "---" ]; then
    ok "skill has YAML frontmatter"
  else
    bad "skill file missing YAML frontmatter (first line: '$first_line')"
  fi
fi

# --- 4. Required package files ------------------------------------------------
say "required files"
required=(
  "$PKG/install.sh"
  "$PKG/rule.md"
  "$PKG/rules/show-everything.md"
  "$PKG/settings.snippet.json"
  "$PKG/skills/diagram-on-completion.md"
  "$PKG/scripts/verify-diagram.sh"
  "$PKG/hooks/doc-reminder.sh"
  "$PKG/hooks/doc-verify.sh"
  "$PKG/README.md"
)
for f in "${required[@]}"; do
  if [ ! -f "$f" ]; then
    bad "missing: ${f#"$REPO_ROOT/"}"
  fi
done
[ "$fail" -eq 0 ] && ok "all required files present"

# --- 5. Executable bits -------------------------------------------------------
say "executable bits"
for f in "$PKG/install.sh" "$PKG/hooks/doc-reminder.sh" "$PKG/hooks/doc-verify.sh" "$PKG/scripts/verify-diagram.sh" "$PKG/scripts/validate.sh"; do
  if [ ! -x "$f" ]; then
    bad "not executable: ${f#"$REPO_ROOT/"} (run: chmod +x '$f')"
  fi
done
[ "$fail" -eq 0 ] && ok "all scripts executable"

# --- Summary ------------------------------------------------------------------
echo
if [ "$missing" -eq 1 ]; then
  printf '\033[1;33m[validate] %s\033[0m\n' "Some tools missing - install them and re-run."
  exit 2
fi
if [ "$fail" -eq 1 ]; then
  printf '\033[1;31m[validate] %s\033[0m\n' "FAIL - fix the issues above before pushing."
  exit 1
fi
printf '\033[1;32m[validate] %s\033[0m\n' "PASS - safe to push."
exit 0
