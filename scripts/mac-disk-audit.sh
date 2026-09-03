#!/bin/bash
#
# mac-disk-audit.sh — READ-ONLY inventory of a macOS internal volume.
#
# Stage 1-2 of SCAN -> VERIFY -> REPORT -> REVIEW -> CLEAN.
# It deletes nothing, moves nothing, renames nothing, empties nothing.
#
# Files it creates, and there are no others:
#   1. the report, at --report (default ~/Desktop/imac-disk-audit-<stamp>.txt)
#   2. scratch data under $TMPDIR/disk-audit-<pid>/ :
#      files.tsv, bundles.txt, map.tsv, video.tsv, and dup*.tsv when
#      --verify-dupes is used. Left in place; macOS clears TMPDIR itself.
#
# Verifying that claim: grepping for command names is a smoke test, NOT a
# proof. It cannot see `find -delete`, `-exec rm`, eval, indirect expansion,
# or a `>` truncating an existing file. Check the things that actually
# execute, then read the script -- it is linear and has no functions that
# hide work:
#
#   grep -nE '\-delete|\-exec|\beval\b|xargs|\$\{!' mac-disk-audit.sh
#       -> the only -exec is `stat`, which reads.
#   grep -nE '(^|[^0-9<>&])>[^>&]|>>' mac-disk-audit.sh
#       -> every write target is "$WORK/..." or "$REPORT".
#
# Usage:
#   sudo bash mac-disk-audit.sh                 # full audit, ~5-25 min on 2 TB
#   sudo bash mac-disk-audit.sh --verify-dupes  # + SHA-256 confirm duplicates
#   sudo bash mac-disk-audit.sh --min-file 500  # only catalogue files >500 MB
#   bash mac-disk-audit.sh --no-sudo            # skip areas needing root
#
# sudo is used only for read traversal of directories your user cannot list.
# If sections look suspiciously empty, grant Terminal Full Disk Access under
# System Settings > Privacy & Security > Full Disk Access, then re-run.

set -uo pipefail

VOL="/System/Volumes/Data"
MIN_FILE_MB=100          # catalogue files at least this large
BIG_FILE_MB=1024         # "large file" headline threshold
DUP_MIN_MB=200           # duplicate-candidate threshold
REPORT="$HOME/Desktop/imac-disk-audit-$(date +%Y%m%d-%H%M).txt"
USE_SUDO=1
VERIFY_DUPES=0
DUP_MAX_GROUPS=40        # cap hashing work on a first pass

while [ $# -gt 0 ]; do
  case "$1" in
    --min-file) MIN_FILE_MB="$2"; shift 2 ;;
    --dup-min)  DUP_MIN_MB="$2"; shift 2 ;;
    --vol)      VOL="$2"; shift 2 ;;
    --report)   REPORT="$2"; shift 2 ;;
    --no-sudo)  USE_SUDO=0; shift ;;
    --verify-dupes)  VERIFY_DUPES=1; shift ;;
    --dup-groups)    DUP_MAX_GROUPS="$2"; shift 2 ;;
    --help|-h)  sed -n '2,36p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

[ "$(uname -s)" = "Darwin" ] || { echo "macOS only. Detected: $(uname -s)" >&2; exit 1; }

SUDO=""
if [ "$USE_SUDO" -eq 1 ]; then
  if [ "$(id -u)" -eq 0 ]; then SUDO=""
  elif command -v sudo >/dev/null 2>&1; then SUDO="sudo"
  fi
fi

WORK="${TMPDIR:-/tmp}/disk-audit-$$"
mkdir -p "$WORK"

human() {
  awk -v b="${1:-0}" 'BEGIN{
    split("B KiB MiB GiB TiB", u, " "); i = 1
    while (b >= 1024 && i < 5) { b /= 1024; i++ }
    printf("%.1f %s", b, u[i])
  }'
}
kb()      { echo $(( ${1:-0} * 1024 )); }
dir_kb()  { [ -e "$1" ] && $SUDO du -sk "$1" 2>/dev/null | awk 'NR==1{print $1+0}' || echo 0; }
hr()      { printf '%s\n' "============================================================"; }
sub()     { printf '%s\n' "------------------------------------------------------------"; }

# Everything below goes to the terminal and the report together.
# A brace group piped into tee is used rather than `exec > >(tee ...)`,
# because process substitution can lose the last lines of output when the
# script exits -- and the last lines are the classification summary.
audit_body() {

hr
echo "iMAC_M4 DISK AUDIT — READ ONLY"
echo "$(date '+%Y-%m-%d %H:%M:%S %Z')"
hr
echo
echo "Nothing is deleted, moved or modified by this script."
echo "Report: $REPORT"
echo "Scratch (left in place, macOS clears it): $WORK"
[ -n "$SUDO" ] && echo "Using sudo for read traversal only." || echo "Running WITHOUT sudo — some areas will be under-counted."
echo

# =========================================================== 1. CAPACITY ====
hr; echo "1. CAPACITY"; hr
df -h "$VOL" 2>/dev/null
echo
diskutil info "$VOL" 2>/dev/null | \
  grep -E "Volume Name|File System Personality|Container Free Space|Volume Used Space|Volume Free Space"
echo
echo "Mounted volumes:"
df -h 2>/dev/null | awk 'NR==1 || /\/Volumes\/|\/System\/Volumes\/Data/'

AVAIL_KB=$(df -k "$VOL" 2>/dev/null | awk 'NR==2{print $4+0}')
USED_KB=$(df -k "$VOL" 2>/dev/null | awk 'NR==2{print $3+0}')
echo
echo "  Used:   $(human "$(kb "$USED_KB")")"
echo "  Free:   $(human "$(kb "$AVAIL_KB")")"
echo "  Target: 300-500 GB free on a 2 TB production machine"

# ============================================================ 2. SCANNING ===
echo
hr; echo "2. SCANNING (this is the slow part)"; hr
echo "  Cataloguing files >= ${MIN_FILE_MB} MB across $VOL ..."
$SUDO find "$VOL" -xdev \
  \( -path '*/.Spotlight-V100' -o -path '*/.fseventsd' -o -path '*/.DocumentRevisions-V100' \) -prune -o \
  -type f -size +"${MIN_FILE_MB}"M -exec stat -f '%z%t%N' {} + 2>/dev/null \
  | sort -rn > "$WORK/files.tsv"
echo "    $(wc -l < "$WORK/files.tsv" | tr -d ' ') files catalogued"

echo "  Locating media libraries and bundles ..."
$SUDO find "$VOL" -xdev -type d \
  \( -name '*.fcpbundle' -o -name '*.photoslibrary' -o -name '*.imovielibrary' \
     -o -name '*.motn' -o -name '*.logicx' \) -prune -print 2>/dev/null \
  | sort > "$WORK/bundles.txt"
echo "    $(wc -l < "$WORK/bundles.txt" | tr -d ' ') libraries found"

echo "  Mapping directory tree to depth 2 ..."
$SUDO du -xk -d 2 "$VOL" 2>/dev/null | sort -rn > "$WORK/map.tsv"
echo "    done"

# ======================================================= 3. WHERE IT WENT ===
echo
hr; echo "3. WHERE THE SPACE IS — top directories (depth <= 2)"; hr
head -40 "$WORK/map.tsv" | awk -F'\t' '{
  b = $1 * 1024; split("B KiB MiB GiB TiB", u, " "); i = 1
  while (b >= 1024 && i < 5) { b /= 1024; i++ }
  printf("  %9.1f %-3s  %s\n", b, u[i], $2)
}'

# ====================================================== 4. LARGEST FILES ====
echo
hr; echo "4. LARGEST INDIVIDUAL FILES (>= ${BIG_FILE_MB} MB)"; hr
awk -F'\t' -v min=$((BIG_FILE_MB * 1048576)) '$1 >= min' "$WORK/files.tsv" | head -50 | \
awk -F'\t' '{
  b = $1; split("B KiB MiB GiB TiB", u, " "); i = 1
  while (b >= 1024 && i < 5) { b /= 1024; i++ }
  printf("  %9.1f %-3s  %s\n", b, u[i], $2)
}'
BIGCOUNT=$(awk -F'\t' -v min=$((BIG_FILE_MB * 1048576)) '$1 >= min' "$WORK/files.tsv" | wc -l | tr -d ' ')
BIGSUM=$(awk -F'\t' -v min=$((BIG_FILE_MB * 1048576)) '$1 >= min {s += $1} END {print s+0}' "$WORK/files.tsv")
echo
echo "  $BIGCOUNT files >= ${BIG_FILE_MB} MB, totalling $(human "$BIGSUM")"

# ============================================================= 5. VIDEO =====
echo
hr; echo "5. VIDEO AND MEDIA FILES"; hr
grep -iE '\.(mp4|mov|mxf|braw|r3d|avi|mkv|m4v|prores|dv|mts|m2ts|wav|aif|aiff)$' \
  "$WORK/files.tsv" > "$WORK/video.tsv" 2>/dev/null
VIDSUM=$(awk -F'\t' '{s += $1} END {print s+0}' "$WORK/video.tsv")
VIDCOUNT=$(wc -l < "$WORK/video.tsv" | tr -d ' ')
echo "  $VIDCOUNT media files >= ${MIN_FILE_MB} MB, totalling $(human "$VIDSUM")"
echo "  RED by default — an original recording may be the only copy."
echo
head -30 "$WORK/video.tsv" | awk -F'\t' '{
  b = $1; split("B KiB MiB GiB TiB", u, " "); i = 1
  while (b >= 1024 && i < 5) { b /= 1024; i++ }
  printf("  %9.1f %-3s  %s\n", b, u[i], $2)
}'

# ====================================================== 6. FINAL CUT PRO ====
echo
hr; echo "6. FINAL CUT PRO"; hr
FCP_REGEN_KB=0
FCP_ORIG_KB=0
OTHER_LIB_KB=0
if [ -s "$WORK/bundles.txt" ]; then
  # Non-FCP libraries are reported first: a Photos or iMovie library is a
  # prime suspect on a full media machine and used to be silently skipped.
  while IFS= read -r lib; do
    case "$lib" in *.fcpbundle) continue ;; esac
    OKB=$(dir_kb "$lib")
    [ "$OKB" -gt 0 ] || continue
    case "$lib" in
      *.photoslibrary) echo "  RED    $(human "$(kb "$OKB")")  $lib  (Photos — originals may be only copies)" ;;
      *.imovielibrary) echo "  AMBER  $(human "$(kb "$OKB")")  $lib  (iMovie library)" ;;
      *.logicx)        echo "  AMBER  $(human "$(kb "$OKB")")  $lib  (Logic project)" ;;
      *)               echo "  AMBER  $(human "$(kb "$OKB")")  $lib" ;;
    esac
    OTHER_LIB_KB=$((OTHER_LIB_KB + OKB))
  done < "$WORK/bundles.txt"

  while IFS= read -r lib; do
    case "$lib" in *.fcpbundle) ;; *) continue ;; esac
    LKB=$(dir_kb "$lib")
    echo
    echo "  LIBRARY  $(human "$(kb "$LKB")")  $lib"
    for kind in "Render Files" "Transcoded Media" "Proxy Media" "Optimized Media" "High Quality Media"; do
      SUM=0
      while IFS= read -r d; do
        SUM=$((SUM + $(dir_kb "$d")))
      done < <($SUDO find "$lib" -type d -name "$kind" 2>/dev/null)
      if [ "$SUM" -gt 0 ]; then
        echo "    GREEN  $(human "$(kb "$SUM")")  $kind  (Final Cut regenerates this)"
        FCP_REGEN_KB=$((FCP_REGEN_KB + SUM))
      fi
    done
    OSUM=0
    while IFS= read -r d; do
      OSUM=$((OSUM + $(dir_kb "$d")))
    done < <($SUDO find "$lib" -type d -name "Original Media" 2>/dev/null)
    if [ "$OSUM" -gt 0 ]; then
      echo "    RED    $(human "$(kb "$OSUM")")  Original Media  (never auto-delete)"
      FCP_ORIG_KB=$((FCP_ORIG_KB + OSUM))
    fi
  done < "$WORK/bundles.txt"
else
  echo "  No Final Cut libraries found."
fi
for d in "$HOME/Movies/Final Cut Backups.localized" "$HOME/Movies/Final Cut Backups"; do
  K=$(dir_kb "$d"); [ "$K" -gt 0 ] && echo && echo "  AMBER  $(human "$(kb "$K")")  $d  (library backups — keep the recent ones)"
done

# ========================================================= 7. DUPLICATES ====
echo
hr; echo "7. DUPLICATE CANDIDATES (identical byte size, >= ${DUP_MIN_MB} MB)"; hr
echo "  Same byte size is a HINT, not evidence. Two different 4K takes of the"
echo "  same length are routinely byte-identical in size and completely"
echo "  different in content. Nothing here is counted as reclaimable space"
echo "  unless --verify-dupes has hashed it."
echo

# size <TAB> path <TAB> path ...   (paths are tab-separated; filenames cannot
# contain tabs in any output produced by find/stat)
awk -F'\t' -v m=$((DUP_MIN_MB * 1048576)) '
  $1 >= m { c[$1]++; p[$1] = p[$1] "\t" $2 }
  END { for (s in c) if (c[s] > 1) printf "%d%s\n", s, p[s] }
' "$WORK/files.tsv" | sort -rn > "$WORK/dupgroups.tsv"

DUP_GROUPS=$(wc -l < "$WORK/dupgroups.tsv" | tr -d " ")
DUPSUM=$(awk -F'\t' '{ t += $1 * (NF - 2) } END { print t+0 }' "$WORK/dupgroups.tsv")

echo "  $DUP_GROUPS candidate group(s)."
echo "  UNVERIFIED CEILING (if every one were a true duplicate): $(human "$DUPSUM")"
echo "  Treat that number as an upper bound on what MIGHT exist, nothing more."
echo

head -20 "$WORK/dupgroups.tsv" | awk -F"\t" '{
  b = $1 * (NF - 2); split("B KiB MiB GiB TiB", u, " "); i = 1
  while (b >= 1024 && i < 5) { b /= 1024; i++ }
  printf("  candidate  %9.1f %-3s  (%d files of identical size)\n", b, u[i], NF - 1)
  for (j = 2; j <= NF; j++) printf("        %s\n", $j)
}'

DUP_CONFIRMED=0
if [ "$VERIFY_DUPES" -eq 1 ] && [ "$DUP_GROUPS" -gt 0 ]; then
  echo
  sub
  echo "  VERIFY — SHA-256 confirmation of the top $DUP_MAX_GROUPS group(s)"
  echo "  Cheap prefilter on the first 1 MiB, full hash only on survivors."
  sub
  GN=0
  while IFS= read -r line; do
    GN=$((GN + 1)); [ "$GN" -gt "$DUP_MAX_GROUPS" ] && break
    OLDIFS="$IFS"; IFS=$(printf "\t"); set -f
    # shellcheck disable=SC2086
    set -- $line
    set +f; IFS="$OLDIFS"
    SIZE="$1"; shift

    # pass 1: hash the first 1 MiB of each candidate
    : > "$WORK/pre.tsv"
    for f in "$@"; do
      [ -r "$f" ] || { $SUDO test -r "$f" 2>/dev/null || continue; }
      H=$($SUDO head -c 1048576 "$f" 2>/dev/null | shasum -a 256 2>/dev/null | awk "{print \$1}")
      [ -n "$H" ] && printf "%s\t%s\n" "$H" "$f" >> "$WORK/pre.tsv"
    done
    SURVIVORS=$(awk -F"\t" "{c[\$1]++} END {for (h in c) if (c[h] > 1) print h}" "$WORK/pre.tsv")
    [ -z "$SURVIVORS" ] && continue

    # pass 2: full SHA-256 on the survivors only
    : > "$WORK/full.tsv"
    for h in $SURVIVORS; do
      awk -F"\t" -v k="$h" "\$1 == k {print \$2}" "$WORK/pre.tsv" | while IFS= read -r f; do
        FH=$($SUDO shasum -a 256 "$f" 2>/dev/null | awk "{print \$1}")
        [ -n "$FH" ] && printf "%s\t%s\n" "$FH" "$f" >> "$WORK/full.tsv"
      done
    done

    awk -F"\t" -v sz="$SIZE" "
      {c[\$1]++; p[\$1] = p[\$1] \"\\n        \" \$2}
      END { for (h in c) if (c[h] > 1)
              printf \"  CONFIRMED  %d bytes reclaimable  sha256 %s...%s\\n\",
                     sz * (c[h] - 1), substr(h, 1, 12), p[h] }
    " "$WORK/full.tsv" | tee -a "$WORK/confirmed.txt"

    ADD=$(awk -F"\t" -v sz="$SIZE" "{c[\$1]++} END {for (h in c) if (c[h] > 1) t += sz * (c[h] - 1); print t+0}" "$WORK/full.tsv")
    DUP_CONFIRMED=$((DUP_CONFIRMED + ADD))
  done < "$WORK/dupgroups.tsv"

  echo
  echo "  CONFIRMED duplicate bytes (hash-identical, one copy kept): $(human "$DUP_CONFIRMED")"
  [ "$DUP_GROUPS" -gt "$DUP_MAX_GROUPS" ] && \
    echo "  Note: only the largest $DUP_MAX_GROUPS of $DUP_GROUPS groups were hashed."
else
  echo
  echo "  NOT VERIFIED. Re-run with --verify-dupes to hash these and get a real"
  echo "  figure. Until then no duplicate space is claimed anywhere in this report."
fi

# =========================================== 8. DOWNLOADS AND INSTALLERS ====
echo
hr; echo "8. DOWNLOADS AND INSTALLERS"; hr
DL_KB=$(dir_kb "$HOME/Downloads")
echo "  AMBER  $(human "$(kb "$DL_KB")")  ~/Downloads"
echo "         Not counted as reclaimable. On a production machine Downloads"
echo "         holds unique material as often as it holds installers -- the"
echo "         only copy of a delivered file, a client upload, a signed PDF."
echo "         Review by hand. Installers below are the disposable part."
echo
grep -iE '\.(dmg|pkg|iso|zip|tar|tar\.gz|tgz|xip)$' "$WORK/files.tsv" 2>/dev/null | head -20 | \
awk -F'\t' '{
  b = $1; split("B KiB MiB GiB TiB", u, " "); i = 1
  while (b >= 1024 && i < 5) { b /= 1024; i++ }
  printf("  GREEN  %9.1f %-3s  %s\n", b, u[i], $2)
}'
for inst in /Applications/Install\ macOS*.app; do
  [ -e "$inst" ] && echo "  GREEN  $(human "$(kb "$(dir_kb "$inst")")")  $inst"
done

# ======================================================= 9. GOOGLE DRIVE ====
echo
hr; echo "9. CLOUD STORAGE HELD LOCALLY (Google Drive, iCloud, Dropbox, OneDrive)"; hr
FOUND_GD=0
for gd in "$HOME/Library/CloudStorage"/* "$HOME/Google Drive" "$HOME/Dropbox" \
          "$HOME/Library/Mobile Documents" \
          "$HOME/Library/Application Support/Google/DriveFS"; do
  [ -e "$gd" ] || continue
  FOUND_GD=1
  K=$(dir_kb "$gd")
  case "$gd" in
    *DriveFS)          echo "  AMBER  $(human "$(kb "$K")")  $gd  (mirror cache — Drive rebuilds it)" ;;
    *"Mobile Documents") echo "  RED    $(human "$(kb "$K")")  $gd  (iCloud Drive local copy)" ;;
    *)                 echo "  RED    $(human "$(kb "$K")")  $gd  (may hold the authoritative copy)" ;;
  esac
done
[ "$FOUND_GD" -eq 0 ] && echo "  No local cloud-storage folders found."

# ============================== 9b. MAIL, VIRTUAL MACHINES, BUILD OUTPUT ===
echo
hr; echo "9b. MAIL, VIRTUAL MACHINES, BUILD OUTPUT"; hr

MAIL_KB=0
for d in "$HOME/Library/Mail" "$HOME/Library/Containers/com.apple.mail"; do
  K=$(dir_kb "$d")
  if [ "$K" -gt 0 ]; then
    echo "  AMBER  $(human "$(kb "$K")")  $d  (mail store — may hold the only copy of attachments)"
    MAIL_KB=$((MAIL_KB + K))
  fi
done
[ "$MAIL_KB" -eq 0 ] && echo "  Mail: nothing found"

echo
echo "  Virtual machine images (each can be tens or hundreds of GB):"
VM_FOUND=0
grep -iE '\.(pvm|vmwarevm|utm|qcow2|vdi|vmdk|sparsebundle|dmg\.sparseimage)$' \
  "$WORK/files.tsv" 2>/dev/null | head -10 | awk -F'\t' '{
    b = $1; split("B KiB MiB GiB TiB", u, " "); i = 1
    while (b >= 1024 && i < 5) { b /= 1024; i++ }
    printf("    AMBER  %9.1f %-3s  %s\n", b, u[i], $2)
  }'
for vd in "$HOME/Parallels" "$HOME/Virtual Machines.localized" "$HOME/Library/Containers/com.utmapp.UTM"; do
  K=$(dir_kb "$vd")
  if [ "$K" -gt 0 ]; then echo "    AMBER  $(human "$(kb "$K")")  $vd"; VM_FOUND=1; fi
done
[ "$VM_FOUND" -eq 0 ] && echo "    (no VM directories in the usual locations)"

echo
echo "  Build output directories (GREEN — regenerated by a rebuild), top 10:"
$SUDO find "$HOME" -maxdepth 6 -type d \
  \( -name target -o -name dist -o -name build -o -name .next -o -name .gradle \) \
  -prune 2>/dev/null | head -200 | \
  while IFS= read -r b; do echo "$(dir_kb "$b") $b"; done | sort -rn | head -10 | \
  while read -r k pth; do echo "    GREEN  $(human "$(kb "$k")")  $pth"; done

# ==================================================== 10. RED — PROTECTED ===
echo
hr; echo "10. RED — PROTECTED BY DEFAULT, NEVER AUTO-DELETE"; hr
for d in "$HOME/nemoclaw" "$HOME/openclaw" "$HOME/mircea-constellation" \
         "$HOME/Projects" "$HOME/Developer" "$HOME/Documents"; do
  K=$(dir_kb "$d"); [ "$K" -gt 0 ] && echo "  RED  $(human "$(kb "$K")")  $d"
done
echo
echo "  Git working trees (top 15 by size):"
$SUDO find "$HOME" -maxdepth 5 -type d -name .git -prune 2>/dev/null | head -300 | \
  while IFS= read -r g; do echo "$(dir_kb "$(dirname "$g")") $(dirname "$g")"; done | \
  sort -rn | head -15 | while read -r k p; do echo "  RED  $(human "$(kb "$k")")  $p"; done
echo
echo "  Anything matching geaboc / nemoclaw / openclaw:"
$SUDO find "$VOL" -xdev -maxdepth 6 \
  \( -iname '*geaboc*' -o -iname '*nemoclaw*' -o -iname '*openclaw*' \) \
  2>/dev/null | head -20 | sed 's/^/  RED  /'

# ======================================================== 11. DEVELOPER =====
echo
hr; echo "11. DEVELOPER CACHES — GREEN (all regenerable)"; hr
DEV_KB=0
add_dev() {
  K=$(dir_kb "$2")
  if [ "$K" -gt 0 ]; then
    echo "  GREEN  $(human "$(kb "$K")")  $1"
    DEV_KB=$((DEV_KB + K))
  fi
}
add_dev "npm cache"          "$HOME/.npm/_cacache"
add_dev "Homebrew cache"     "$HOME/Library/Caches/Homebrew"
add_dev "pnpm store"         "$HOME/Library/pnpm/store"
add_dev "yarn cache"         "$HOME/Library/Caches/Yarn"
add_dev "pip cache"          "$HOME/Library/Caches/pip"
add_dev "Cargo registry"     "$HOME/.cargo/registry"
add_dev "Go module cache"    "$HOME/go/pkg/mod"
add_dev "Xcode DerivedData"  "$HOME/Library/Developer/Xcode/DerivedData"
add_dev "iOS DeviceSupport"  "$HOME/Library/Developer/Xcode/iOS DeviceSupport"
add_dev "Simulator caches"   "$HOME/Library/Developer/CoreSimulator/Caches"
add_dev "Docker disk image"  "$HOME/Library/Containers/com.docker.docker/Data/vms"
add_dev "Docker Desktop data" "$HOME/Library/Group Containers/group.com.docker"
echo
echo "  AMBER  Xcode Archives: $(human "$(kb "$(dir_kb "$HOME/Library/Developer/Xcode/Archives")")")  (shipped builds — review)"
echo
echo "  node_modules directories (top 10):"
$SUDO find "$HOME" -maxdepth 6 -type d -name node_modules -prune 2>/dev/null | head -300 | \
  while IFS= read -r n; do echo "$(dir_kb "$n") $n"; done | sort -rn | head -10 | \
  while read -r k p; do echo "    GREEN  $(human "$(kb "$k")")  $p"; done

# =========================================================== 12. CACHES =====
echo
hr; echo "12. APPLICATION CACHES AND LOGS — GREEN, with a caveat"; hr
echo "  Regenerable by design, so GREEN for accounting. But a CLEAN stage"
echo "  must be application-aware, not a blanket delete under these paths:"
echo "  some apps keep real state under Caches (part-complete uploads,"
echo "  offline mail bodies, license material), and a few misbehave badly"
echo "  when their cache vanishes underneath a running process."
echo "  Quit the app, clear that app\'s directory, verify. Not rm -rf Caches/*."
echo
CACHE_KB=0
for d in "$HOME/Library/Caches" "$HOME/Library/Logs" "/Library/Caches" "/Library/Logs"; do
  K=$(dir_kb "$d")
  if [ "$K" -gt 0 ]; then
    echo "  GREEN  $(human "$(kb "$K")")  $d"
    CACHE_KB=$((CACHE_KB + K))
  fi
done
TRASH_KB=$(dir_kb "$HOME/.Trash")
echo "  GREEN  $(human "$(kb "$TRASH_KB")")  ~/.Trash  (look inside first)"

# ========================================================== 13. BACKUPS =====
echo
hr; echo "13. DEVICE BACKUPS — AMBER"; hr
MS="$HOME/Library/Application Support/MobileSync/Backup"
BK_KB=$(dir_kb "$MS")
if [ "$BK_KB" -gt 0 ]; then
  echo "  AMBER  $(human "$(kb "$BK_KB")")  $MS"
  echo "  Per backup (delete only via Finder > device > Manage Backups):"
  for b in "$MS"/*; do
    [ -d "$b" ] || continue
    echo "    $(human "$(kb "$(dir_kb "$b")")")  $(basename "$b")  last modified $(stat -f '%Sm' -t '%Y-%m-%d' "$b" 2>/dev/null)"
  done
else
  echo "  None found."
fi

# ===================================================== 14. APPLICATIONS =====
echo
hr; echo "14. APPLICATIONS BY SIZE — AMBER (check last-used before removing)"; hr
for a in /Applications/*.app; do
  [ -d "$a" ] || continue
  echo "$(dir_kb "$a")|$a"
done | sort -rn -t'|' | head -20 | while IFS='|' read -r k p; do
  LAST=$(mdls -name kMDItemLastUsedDate -raw "$p" 2>/dev/null | cut -c1-10)
  [ -z "$LAST" ] || [ "$LAST" = "(null)" ] && LAST="never recorded"
  echo "  AMBER  $(human "$(kb "$k")")  $(basename "$p")   last used: $LAST"
done

# ======================================================== 15. SNAPSHOTS =====
echo
hr; echo "15. APFS / TIME MACHINE SNAPSHOTS — LEAVE ALONE"; hr
echo "  macOS counts snapshot space as available and reclaims it automatically"
echo "  when the disk fills. Deleting them by hand is not a real win."
for v in / "$VOL"; do
  echo "  $v: $(tmutil listlocalsnapshots "$v" 2>/dev/null | grep -c 'com.apple.TimeMachine') snapshot(s)"
done

# ========================================================== 16. SUMMARY =====
echo
hr; echo "16. CLASSIFICATION SUMMARY"; hr
# Downloads is deliberately NOT in GREEN: on a production machine it holds
# unique material as often as installers. Duplicates are NOT in any total
# unless --verify-dupes actually hashed them.
GREEN_KB=$((DEV_KB + CACHE_KB + TRASH_KB + FCP_REGEN_KB))
echo
printf "  GREEN  regenerable, countable    %s\n" "$(human "$(kb "$GREEN_KB")")"
printf "           dev caches              %s\n" "$(human "$(kb "$DEV_KB")")"
printf "           app caches and logs     %s  (clear per-app, not wholesale)\n" "$(human "$(kb "$CACHE_KB")")"
printf "           Trash                   %s  (look inside first)\n" "$(human "$(kb "$TRASH_KB")")"
printf "           FCP render/proxy/optim. %s  (Final Cut rebuilds these)\n" "$(human "$(kb "$FCP_REGEN_KB")")"
echo
echo "  AMBER  review required, NOT counted as reclaimable"
printf "           Downloads               %s\n" "$(human "$(kb "$DL_KB")")"
printf "           device backups          %s\n" "$(human "$(kb "$BK_KB")")"
printf "           non-FCP media libraries %s  (Photos/iMovie/Logic)\n" "$(human "$(kb "$OTHER_LIB_KB")")"
printf "           Xcode archives, unused applications, old library backups\n"
if [ "$VERIFY_DUPES" -eq 1 ]; then
  printf "           duplicates CONFIRMED    %s  (sha256-identical)\n" "$(human "$DUP_CONFIRMED")"
  printf "           duplicates unverified   %s  (ceiling, not a finding)\n" "$(human "$DUPSUM")"
else
  printf "           duplicates              %s UNVERIFIED CEILING -- not a finding.\n" "$(human "$DUPSUM")"
  printf "                                   Re-run with --verify-dupes to hash them.\n"
fi
echo
printf "  RED    never auto-delete         FCP Original Media %s\n" "$(human "$(kb "$FCP_ORIG_KB")")"
printf "                                   Google Drive local, git working trees,\n"
printf "                                   NemoClaw/OpenClaw, Geaboc material,\n"
printf "                                   media originals\n"
echo
GOAL_KB=$((350 * 1024 * 1024))
echo "  Free now:              $(human "$(kb "$AVAIL_KB")")"
echo "  GREEN alone would give $(human "$(kb "$((AVAIL_KB + GREEN_KB))")")"
echo "  Target (~350 GB):      $(human "$(kb "$GOAL_KB")")"
if [ $((AVAIL_KB + GREEN_KB)) -lt "$GOAL_KB" ]; then
  GAP_KB=$((GOAL_KB - AVAIL_KB - GREEN_KB))
  echo
  echo "  GREEN alone falls $(human "$(kb "$GAP_KB")") short of the target."
  echo "  That gap must be closed from AMBER, after you review it -- not by"
  echo "  widening GREEN. Sections 3 and 4 show where the mass actually sits;"
  echo "  on this machine the answer is almost certainly video, not caches."
fi

echo
hr
echo "END OF AUDIT — nothing was deleted, moved or modified."
echo "Report saved to: $REPORT"
hr
}

audit_body 2>&1 | tee "$REPORT"
