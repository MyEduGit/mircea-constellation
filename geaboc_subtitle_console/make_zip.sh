#!/bin/bash
# Build the distributable ZIP that gets sent to the operator.
#
# Produces dist/geaboc_subtitle_console.zip containing a single top-level
# folder, so double-clicking the ZIP in Finder extracts a tidy
# geaboc_subtitle_console/ rather than scattering files into Downloads.
#
# Executable bits are preserved by zip on Unix — without them the
# .command files will not open on double-click.
#
# UrantiOS governed — Truth, Beauty, Goodness.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SRC_DIR/.." && pwd)"
DIST_DIR="$REPO_DIR/dist"
STAGE_DIR="$(mktemp -d)"
PAYLOAD="$STAGE_DIR/geaboc_subtitle_console"

cleanup() { rm -rf "$STAGE_DIR"; }
trap cleanup EXIT

echo "Staging..."
mkdir -p "$PAYLOAD"
cp "$SRC_DIR/geaboc_console.py"                     "$PAYLOAD/"
cp "$SRC_DIR/Geaboc Subtitle Console.command"       "$PAYLOAD/"
cp "$SRC_DIR/install_Geaboc_Subtitle_Console.command" "$PAYLOAD/"
cp "$SRC_DIR/README.md"                             "$PAYLOAD/"

chmod +x "$PAYLOAD/Geaboc Subtitle Console.command"
chmod +x "$PAYLOAD/install_Geaboc_Subtitle_Console.command"

echo "Verifying the payload runs..."
python3 "$PAYLOAD/geaboc_console.py" --self-test >/dev/null

mkdir -p "$DIST_DIR"
rm -f "$DIST_DIR/geaboc_subtitle_console.zip"

echo "Zipping..."
( cd "$STAGE_DIR" && zip -r -q "$DIST_DIR/geaboc_subtitle_console.zip" \
    geaboc_subtitle_console -x '*.DS_Store' )

echo ""
echo "Built: $DIST_DIR/geaboc_subtitle_console.zip"
unzip -l "$DIST_DIR/geaboc_subtitle_console.zip"
