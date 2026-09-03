#!/bin/bash
#
# fetch-drive-video.sh — pull a large Google Drive file straight onto an
# external volume, never staging it on the boot drive.
#
# Defaults target the job this was written for:
#   C0042.MP4, 19.4 GiB, owned by messagestostephanos@gmail.com and already
#   shared with mirceamatthews@gmail.com, destined for the FCP scratch SSD.
#
# Usage:
#   bash fetch-drive-video.sh                 # do it
#   bash fetch-drive-video.sh --check-only    # run preflight, download nothing
#   bash fetch-drive-video.sh --id ID --name NAME.MP4 --bytes N --dest /Volumes/X
#
# Why rclone and not curl or a browser:
#   * A ~20 GB browser download cannot resume; rclone can.
#   * rclone writes to the destination path, so the boot volume stays clear.
#   * The file is shared with a specific account, so an unauthenticated curl
#     gets a sign-in page and cheerfully saves the HTML.

set -uo pipefail

FILE_ID="1XdYEoeeDT1Boue98jX4mlw-FmsMcXXKo"
FILE_NAME="C0042.MP4"
EXPECT_BYTES=20805349763
DEST="/Volumes/SSD_Adobe:FCP"
REMOTE="gdrive"
ACCOUNT="mirceamatthews@gmail.com"
CHECK_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --id)         FILE_ID="$2"; shift 2 ;;
    --name)       FILE_NAME="$2"; shift 2 ;;
    --bytes)      EXPECT_BYTES="$2"; shift 2 ;;
    --dest)       DEST="$2"; shift 2 ;;
    --remote)     REMOTE="$2"; shift 2 ;;
    --account)    ACCOUNT="$2"; shift 2 ;;
    --check-only) CHECK_ONLY=1; shift ;;
    --help|-h)    sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

[ "$(uname -s)" = "Darwin" ] || { echo "macOS only. Detected: $(uname -s)" >&2; exit 1; }

TARGET="$DEST/$FILE_NAME"
FAT32_MAX=4294967295   # 4 GiB - 1

human() {
  awk -v b="${1:-0}" 'BEGIN{
    split("B KiB MiB GiB TiB", u, " "); i = 1
    while (b >= 1024 && i < 5) { b /= 1024; i++ }
    printf("%.1f %s", b, u[i])
  }'
}

die()  { echo; echo "BLOCKED: $*" >&2; exit 1; }
ok()   { echo "  ok    $*"; }
info() { echo "  ..    $*"; }

echo "------------------------------------------------------------"
echo "PREFLIGHT"
echo "------------------------------------------------------------"
echo "  file    $FILE_NAME  ($(human "$EXPECT_BYTES"))"
echo "  id      $FILE_ID"
echo "  dest    $TARGET"
echo "  account $ACCOUNT"
echo

# --- destination volume -----------------------------------------------------

[ -d "$DEST" ] || die "destination volume not mounted: $DEST"
ok "volume mounted"

FS=$(diskutil info "$DEST" 2>/dev/null | \
       awk -F: '/File System Personality/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2}')
RO=$(diskutil info "$DEST" 2>/dev/null | \
       awk -F: '/Read-Only Volume/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2}')
[ -n "$FS" ] || FS="unknown"
ok "filesystem: $FS"

case "$RO" in
  Yes*|yes*) die "volume is mounted read-only" ;;
esac

# exFAT contains the string FAT, so it has to be matched first.
MAXFILE=0
case "$FS" in
  *[eE]x[fF][aA][tT]*)          MAXFILE=0 ;;
  *FAT32*|*"MS-DOS"*|*fat32*)   MAXFILE=$FAT32_MAX ;;
esac

if [ "$MAXFILE" -gt 0 ] && [ "$EXPECT_BYTES" -gt "$MAXFILE" ]; then
  die "$FS caps a single file at $(human "$MAXFILE"). This file is
         $(human "$EXPECT_BYTES") and cannot be written here at any free-space
         level. Reformat the volume as exFAT or APFS, or pick another
         destination. Reformatting erases it -- move the 719 GB off first."
fi
ok "no filesystem file-size limit blocks this file"

[ -w "$DEST" ] || die "no write permission on $DEST"
ok "writable"

AVAIL=$(df -k "$DEST" 2>/dev/null | awk 'NR==2 {printf "%.0f", $4 * 1024}')
AVAIL=${AVAIL:-0}
NEEDED=$((EXPECT_BYTES + 1073741824))   # file + 1 GiB headroom
echo "  ..    free: $(human "$AVAIL")   needed: $(human "$NEEDED")"
[ "$AVAIL" -ge "$NEEDED" ] || die "not enough free space on $DEST"
ok "space available"

# --- already done? ----------------------------------------------------------

if [ -f "$TARGET" ]; then
  HAVE=$(stat -f%z "$TARGET" 2>/dev/null || echo 0)
  if [ "$HAVE" = "$EXPECT_BYTES" ]; then
    echo
    echo "Already present at the expected size. Nothing to do."
    ls -lh "$TARGET"
    exit 0
  fi
  info "partial or mismatched file present ($(human "$HAVE")); rclone will resume"
fi

# --- rclone -----------------------------------------------------------------

if ! command -v rclone >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    info "rclone missing; installing via Homebrew"
    [ "$CHECK_ONLY" -eq 1 ] || brew install rclone || die "brew install rclone failed"
  else
    die "rclone is not installed and Homebrew is not available.
         Install Homebrew first, or download rclone from https://rclone.org/downloads/"
  fi
fi
command -v rclone >/dev/null 2>&1 && ok "rclone: $(rclone version 2>/dev/null | head -1)"

if ! rclone listremotes 2>/dev/null | grep -qx "${REMOTE}:"; then
  echo
  echo "  Remote '$REMOTE' is not configured yet."
  echo "  A browser will open. Sign in as: $ACCOUNT"
  echo "  (NOT the account that owns the file -- it is already shared with you.)"
  echo
  if [ "$CHECK_ONLY" -eq 1 ]; then
    info "check-only: skipping remote creation"
  else
    rclone config create "$REMOTE" drive scope=drive.readonly \
      || die "rclone remote setup failed. Run 'rclone config' by hand."
  fi
fi

if [ "$CHECK_ONLY" -eq 0 ]; then
  if ! rclone about "${REMOTE}:" >/dev/null 2>&1; then
    die "remote '$REMOTE' exists but is not authorised.
         Run: rclone config reconnect ${REMOTE}:"
  fi
  ok "remote authorised"
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  echo
  echo "Preflight passed. Re-run without --check-only to download."
  exit 0
fi

# --- download ---------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "DOWNLOAD"
echo "------------------------------------------------------------"
echo "  Resumable. Ctrl-C is safe; re-run this script to continue."
echo

# cd into the destination and use ./NAME so rclone cannot mistake a path
# containing a colon (SSD_Adobe:FCP) for a remote:path specifier.
cd "$DEST" || die "cannot enter $DEST"
rclone backend copyid "${REMOTE}:" "$FILE_ID" "./$FILE_NAME" \
  --progress --transfers 1 --retries 5 --low-level-retries 20 \
  || die "download failed. Re-run to resume."

# --- verify -----------------------------------------------------------------

echo
echo "------------------------------------------------------------"
echo "VERIFY"
echo "------------------------------------------------------------"

[ -f "$TARGET" ] || die "download reported success but $TARGET is missing"

GOT=$(stat -f%z "$TARGET" 2>/dev/null || echo 0)
echo "  size on disk: $(human "$GOT")"
echo "  expected:     $(human "$EXPECT_BYTES")"
if [ "$GOT" != "$EXPECT_BYTES" ]; then
  die "size mismatch. Re-run to resume the transfer."
fi
ok "size matches"

TYPE=$(file -b "$TARGET" 2>/dev/null)
echo "  type: $TYPE"
case "$TYPE" in
  *HTML*|*ASCII*|*text*) die "this is a web page, not a video -- the transfer
         fetched a sign-in or error page. Check the account and sharing." ;;
esac
ok "container looks like real media"

echo
ls -lh "$TARGET"
echo
echo "Done. The boot volume was never used as a staging area."
