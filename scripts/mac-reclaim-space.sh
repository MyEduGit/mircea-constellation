#!/bin/bash
#
# mac-reclaim-space.sh — staged, reversible-first disk cleanup for macOS.
#
# Written for iMAC_M4 (Apple Silicon, 32 GB RAM, 2 TB internal) after the
# internal volume hit 99% full and blocked large downloads.
#
# Usage:
#   bash mac-reclaim-space.sh                # interactive, confirms each stage
#   bash mac-reclaim-space.sh --report-only  # measure only, change nothing
#   bash mac-reclaim-space.sh --yes          # auto-confirm the SAFE stages only
#   bash mac-reclaim-space.sh --deep-scan    # add slow whole-volume size hunt
#
# Safety rules baked in:
#   * Nothing under /System or /Library is touched.
#   * Docker volumes are NEVER pruned (n8n workflows + credentials live there).
#   * iOS device backups and Xcode Archives are reported, never deleted.
#   * Time Machine snapshots, Docker prune and a full ~/Library/Caches wipe
#     always require an interactive yes -- --yes does not cover them.
#   * With no TTY, every prompt is answered "no" rather than hanging.

set -uo pipefail

ASSUME_YES=0
REPORT_ONLY=0
DEEP_SCAN=0

for arg in "$@"; do
  case "$arg" in
    --yes|-y)      ASSUME_YES=1 ;;
    --report-only) REPORT_ONLY=1 ;;
    --deep-scan)   DEEP_SCAN=1 ;;
    --help|-h)     sed -n '2,19p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This script only runs on macOS. Detected: $(uname -s)" >&2
  exit 1
fi

DATA_VOL="/System/Volumes/Data"

# ---------------------------------------------------------------- helpers ---

human() {
  awk -v b="${1:-0}" 'BEGIN{
    s = (b < 0) ? "-" : ""; if (b < 0) b = -b
    split("B KB MB GB TB PB", u, " ")
    i = 1
    while (b >= 1024 && i < 6) { b /= 1024; i++ }
    printf("%s%.1f %s", s, b, u[i])
  }'
}

free_bytes() {
  local v
  v=$(df -k "$DATA_VOL" 2>/dev/null | awk 'NR==2 {printf "%.0f", $4 * 1024}')
  echo "${v:-0}"
}

dir_bytes() {
  local v
  [ -e "$1" ] || { echo 0; return; }
  v=$(du -sk "$1" 2>/dev/null | awk 'NR==1 {printf "%.0f", $1 * 1024}')
  echo "${v:-0}"
}

rule()    { printf '%s\n' "------------------------------------------------------------"; }
heading() { echo; rule; echo "$1"; rule; }

_ask() {
  local reply=""
  if [ ! -t 0 ]; then
    echo "$1 [no TTY -> skipped]"
    return 1
  fi
  printf '%s [y/N] ' "$1"
  read -r reply
  case "$reply" in [yY]|[yY][eE][sS]) return 0 ;; *) return 1 ;; esac
}

# Safe stages: --yes auto-approves.
confirm() {
  [ "$REPORT_ONLY" -eq 1 ] && return 1
  [ "$ASSUME_YES" -eq 1 ] && return 0
  _ask "$1"
}

# Destructive or hard-to-undo stages: always ask, even under --yes.
confirm_destructive() {
  [ "$REPORT_ONLY" -eq 1 ] && return 1
  _ask "$1"
}

# Delete the CONTENTS of a directory, never the directory itself.
purge_contents() {
  local label="$1" dir="$2" before after
  [ -d "$dir" ] || return 0
  before=$(dir_bytes "$dir")
  [ "$before" -lt 1048576 ] && return 0   # skip anything under 1 MB
  echo "  $label: $(human "$before")  ($dir)"
  if confirm "    delete contents?"; then
    find "$dir" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null
    after=$(dir_bytes "$dir")
    echo "    reclaimed $(human "$((before - after))")"
  else
    echo "    skipped"
  fi
}

START_FREE=$(free_bytes)

# ------------------------------------------------------------- stage 0/6 ---

heading "STAGE 0 — Baseline"

echo "Free on $DATA_VOL: $(human "$START_FREE")"
echo
df -h "$DATA_VOL"
echo
echo "APFS container (free space here can differ from df — purgeable):"
diskutil info "$DATA_VOL" 2>/dev/null | grep -E "Container Free Space|Volume Free Space|Volume Used Space"

echo
echo "Virtual memory (32 GB RAM means swap can grow large):"
sysctl vm.swapusage 2>/dev/null
pmset -g 2>/dev/null | grep -i hibernatemode
echo "Contents of /private/var/vm:"
ls -lh /private/var/vm/ 2>/dev/null | sed 's/^/  /'
echo "  (hibernatemode 0 on a desktop Mac = no multi-GB sleepimage to reclaim)"

# ------------------------------------------------------------- stage 1/6 ---

heading "STAGE 1 — Package manager caches (safe: all re-downloadable)"

if command -v brew >/dev/null 2>&1; then
  BREW_CACHE=$(brew --cache 2>/dev/null)
  echo "  Homebrew cache: $(human "$(dir_bytes "$BREW_CACHE")")"
  if confirm "    run 'brew cleanup -s --prune=all' and empty the cache?"; then
    brew cleanup -s --prune=all 2>/dev/null
    [ -n "$BREW_CACHE" ] && [ -d "$BREW_CACHE" ] && \
      find "$BREW_CACHE" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null
    echo "    done"
  else
    echo "    skipped"
  fi
else
  echo "  Homebrew: not installed"
fi

purge_contents "npm cache" "$HOME/.npm/_cacache"
purge_contents "yarn cache" "$HOME/Library/Caches/Yarn"

if command -v pnpm >/dev/null 2>&1; then
  echo "  pnpm store: $(human "$(dir_bytes "$(pnpm store path 2>/dev/null)")")"
  if confirm "    run 'pnpm store prune'?"; then pnpm store prune 2>/dev/null; echo "    done"; fi
fi

for pipcmd in pip3 pip; do
  if command -v "$pipcmd" >/dev/null 2>&1; then
    echo "  $pipcmd cache: $("$pipcmd" cache dir 2>/dev/null)"
    if confirm "    run '$pipcmd cache purge'?"; then "$pipcmd" cache purge 2>/dev/null; fi
    break
  fi
done

# ------------------------------------------------------------- stage 2/6 ---

heading "STAGE 2 — Xcode build artefacts (safe: regenerated on next build)"

purge_contents "DerivedData"       "$HOME/Library/Developer/Xcode/DerivedData"
purge_contents "iOS DeviceSupport" "$HOME/Library/Developer/Xcode/iOS DeviceSupport"
purge_contents "Simulator caches"  "$HOME/Library/Developer/CoreSimulator/Caches"

if command -v xcrun >/dev/null 2>&1 && xcrun simctl help >/dev/null 2>&1; then
  if confirm "  delete simulators for uninstalled runtimes ('simctl delete unavailable')?"; then
    xcrun simctl delete unavailable 2>/dev/null
    echo "    done"
  fi
fi

ARCHIVES="$HOME/Library/Developer/Xcode/Archives"
if [ -d "$ARCHIVES" ]; then
  echo
  echo "  NOT DELETING — Xcode Archives: $(human "$(dir_bytes "$ARCHIVES")")"
  echo "    These are shipped build archives. Review by hand: $ARCHIVES"
fi

# ------------------------------------------------------------- stage 3/6 ---

heading "STAGE 3 — User caches and Trash"

echo "  Largest items in ~/Library/Caches:"
du -sk "$HOME/Library/Caches"/* 2>/dev/null | sort -rn | head -15 | \
  awk -F'\t' '{ b = $1 * 1024; split("B KB MB GB TB", u, " "); i = 1
                while (b >= 1024 && i < 5) { b /= 1024; i++ }
                printf("    %8.1f %-2s  %s\n", b, u[i], $2) }'

echo
echo "  Clearing all of ~/Library/Caches signs you out of some apps and can"
echo "  confuse ones that are currently running. Quit what you can first."
CACHES="$HOME/Library/Caches"
if [ -d "$CACHES" ]; then
  CACHES_BEFORE=$(dir_bytes "$CACHES")
  echo "  ~/Library/Caches (whole): $(human "$CACHES_BEFORE")"
  if confirm_destructive "    delete contents?"; then
    find "$CACHES" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null
    echo "    reclaimed $(human "$((CACHES_BEFORE - $(dir_bytes "$CACHES")))")"
  else
    echo "    skipped"
  fi
fi

echo
purge_contents "Trash" "$HOME/.Trash"
purge_contents "Mail downloads" \
  "$HOME/Library/Containers/com.apple.mail/Data/Library/Mail Downloads"

# ------------------------------------------------------------- stage 4/6 ---

heading "STAGE 4 — Time Machine local snapshots"

SNAPSHOTS=$(tmutil listlocalsnapshots / 2>/dev/null | grep -c 'com.apple.TimeMachine')
echo "  Local snapshots on /: $SNAPSHOTS"

if [ "$SNAPSHOTS" -gt 0 ]; then
  tmutil listlocalsnapshots / 2>/dev/null | sed 's/^/    /'
  echo
  echo "  These are on-disk restore points. Deleting them does NOT touch backups"
  echo "  already written to your Time Machine destination."
  echo "  BACKUP-FIRST: confirm your destination backup ran recently."
  if confirm_destructive "  delete ALL local snapshots (needs sudo)?"; then
    sudo tmutil deletelocalsnapshots / && echo "    done"
  else
    echo "    skipped"
  fi
fi

# ------------------------------------------------------------- stage 5/6 ---

heading "STAGE 5 — Docker images and build cache"

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker system df 2>/dev/null | sed 's/^/  /'
  echo
  echo "  WARNING: this prunes images, stopped containers and build cache ONLY."
  echo "  Volumes are deliberately excluded — n8n workflows and credentials"
  echo "  live in Docker volumes and would be destroyed by --volumes."
  if confirm_destructive "  run 'docker system prune -a' (no --volumes)?"; then
    docker system prune -a -f 2>/dev/null
    echo "    done"
  else
    echo "    skipped"
  fi
else
  echo "  Docker: not installed or daemon not running"
fi

# ------------------------------------------------------------- stage 6/6 ---

heading "STAGE 6 — Report only (nothing here is deleted automatically)"

IOS_BACKUPS="$HOME/Library/Application Support/MobileSync/Backup"
if [ -d "$IOS_BACKUPS" ]; then
  echo "  iPhone/iPad backups: $(human "$(dir_bytes "$IOS_BACKUPS")")"
  echo "    Often the single biggest win, and irreplaceable if not in iCloud."
  echo "    Delete via Finder > your device > Manage Backups. Never with rm."
fi

for installer in /Applications/Install\ macOS*.app; do
  [ -e "$installer" ] || continue
  echo "  macOS installer: $(human "$(dir_bytes "$installer")")  ($installer)"
done

echo
echo "  node_modules directories under \$HOME (top 10):"
find "$HOME" -maxdepth 6 -type d -name node_modules -prune 2>/dev/null | head -200 | \
  while IFS= read -r nm; do echo "$(dir_bytes "$nm") $nm"; done | \
  sort -rn | head -10 | \
  while read -r sz path; do echo "    $(human "$sz")  $path"; done

if [ "$DEEP_SCAN" -eq 1 ]; then
  echo
  echo "  Deep scan — largest directories on the data volume (slow, needs sudo):"
  sudo du -xk -d 2 "$DATA_VOL" 2>/dev/null | sort -rn | head -30 | \
    while read -r sz path; do echo "    $(human "$((sz * 1024))")  $path"; done
fi

# ---------------------------------------------------------------- summary ---

END_FREE=$(free_bytes)

heading "SUMMARY"
echo "  Free before: $(human "$START_FREE")"
echo "  Free after:  $(human "$END_FREE")"
echo "  Reclaimed:   $(human "$((END_FREE - START_FREE))")"
echo
echo "  Target: keep at least 150-200 GB free on a 32 GB-RAM machine so macOS"
echo "  has room for swap. Below ~50 GB you get beachballs and failed updates."
echo
if [ "$REPORT_ONLY" -eq 1 ]; then
  echo "  (--report-only: nothing was changed)"
fi
