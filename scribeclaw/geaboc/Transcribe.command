#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  TRANSCRIBE  —  double-click this file to turn audio into text.
#
#  It opens the Geaboc Subtitle Console in your browser. Drag in your audio,
#  click "Transcribe with AssemblyAI", done. AssemblyAI supplies every word.
#
#  (macOS: if double-click is blocked the first time, right-click → Open once.)
# ─────────────────────────────────────────────────────────────────────────────
cd "$(dirname "$0")" || exit 1
exec python3 "geaboc_subtitle_console.py" serve
