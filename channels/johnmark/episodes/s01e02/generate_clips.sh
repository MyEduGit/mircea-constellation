#!/bin/bash
# S01E02 — "The Lie That Replaced Love"
# Generates all atmospheric clips via SeedanceClaw.
# Run from your iMac M4 with SeedanceClaw running:
#   docker logs seedanceclaw --tail 5   (to verify it's up)
#   curl -s http://127.0.0.1:8086/health | python3 -m json.tool

set -euo pipefail

BASE="http://127.0.0.1:8086/tasks"
IMAGES_DIR="/opt/seedanceclaw-data/images"

echo "=== S01E02 Clip Generation — $(date) ==="

check_health() {
  local status
  status=$(curl -sf http://127.0.0.1:8086/health | python3 -c "import sys,json; d=json.load(sys.stdin); print('ok' if d.get('fal_key_set') else 'no_key')" 2>/dev/null || echo "down")
  if [ "$status" != "ok" ]; then
    echo "ERROR: SeedanceClaw not ready (status=$status)"
    echo "Run: docker compose -f seedanceclaw/docker-compose.yml up -d"
    exit 1
  fi
  echo "SeedanceClaw: ready"
}

submit() {
  local label="$1"
  local payload="$2"
  echo ""
  echo ">>> $label"
  curl -sX POST "$BASE" \
    -H 'Content-Type: application/json' \
    -d "$payload" | python3 -c "
import sys, json
r = json.load(sys.stdin)
print('  status:', r.get('status','?'))
print('  video: ', r.get('video_path', r.get('url','?')))
" 2>/dev/null || echo "  (response parse error — check docker logs)"
}

check_health

# ── ATMOSPHERIC CLIPS (text_to_video — no image needed) ──────────────────────

submit "040 — Ancient Salem" '{
  "handler": "text_to_video",
  "payload": {
    "prompt": "Ancient Middle Eastern city at golden hour, 4000 years ago, stone buildings, warm desert light, a figure teaching a small group in an open courtyard, cinematic, peaceful, sacred atmosphere",
    "duration": 10,
    "aspect_ratio": "16:9",
    "resolution": "720p"
  }
}'

submit "041 — The Inherited Map" '{
  "handler": "text_to_video",
  "payload": {
    "prompt": "Abstract cinematic visualization of ancient scrolls and maps transforming across centuries, text and symbols flowing through time, warm sepia tones shifting to modern light, metaphor for inherited knowledge",
    "duration": 10,
    "aspect_ratio": "16:9",
    "resolution": "720p"
  }
}'

submit "042 — The Running Father" '{
  "handler": "text_to_video",
  "payload": {
    "prompt": "Silhouette of a father running toward a distant figure on a dusty road at sunset, warm golden light, emotional reunion, cinematic slow motion, ancient Middle Eastern landscape",
    "duration": 10,
    "aspect_ratio": "16:9",
    "resolution": "720p"
  }
}'

submit "043 — The Thought Adjuster" '{
  "handler": "text_to_video",
  "payload": {
    "prompt": "Abstract visualization of a gentle light within a human silhouette, a fragment of divine presence, soft golden glow from within the chest, cosmic background, peaceful and intimate, no text",
    "duration": 10,
    "aspect_ratio": "16:9",
    "resolution": "720p"
  }
}'

submit "044 — The Great Awakening" '{
  "handler": "text_to_video",
  "payload": {
    "prompt": "Aerial view of Earth at night with lights of cities glowing, connections forming between distant points of light, a network of awakening, cinematic, cosmic scale, hopeful",
    "duration": 10,
    "aspect_ratio": "16:9",
    "resolution": "720p"
  }
}'

# ── CHARACTER CLIPS (image_to_video — needs reference images) ────────────────

check_images() {
  local missing=0
  for f in machiventa_reference.jpg brother_thomas_reference.jpg sister_amara_reference.jpg group_shot_reference.jpg; do
    if [ ! -f "$IMAGES_DIR/$f" ]; then
      echo "  MISSING: $IMAGES_DIR/$f"
      missing=1
    fi
  done
  return $missing
}

echo ""
echo "--- Checking character reference images ---"
if ! check_images; then
  echo ""
  echo "Copy reference images from Episode 1 assets to $IMAGES_DIR/"
  echo "then re-run this script with: bash generate_clips.sh --characters"
  echo ""
  echo "Atmospheric clips above have been submitted. Done: $(date)"
  exit 0
fi

if [[ "${1:-}" != "--characters" ]]; then
  echo "Reference images found. Run with --characters flag to generate character clips:"
  echo "  bash generate_clips.sh --characters"
  exit 0
fi

echo "Generating character clips..."

# Machiventa
submit "010 — Machiventa: cold open" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Ancient wise teacher speaking directly to camera with calm authority, subtle head movement, lips moving gently, warm golden light, cosmic background, deeply sincere expression",
    "image_path": "machiventa_reference.jpg",
    "duration": 10,
    "aspect_ratio": "16:9"
  }
}'

submit "011 — Machiventa: sorrow" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Ancient wise teacher with expression of sorrow and gravity, slight downward gaze then looking up, slow deliberate head movement, warm robes, soft cosmic light",
    "image_path": "machiventa_reference.jpg",
    "duration": 10,
    "aspect_ratio": "16:9"
  }
}'

submit "012 — Machiventa: conviction" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Ancient teacher raising one finger gently, speaking with quiet conviction, warm light, slight smile of certainty, ancient wisdom in eyes",
    "image_path": "machiventa_reference.jpg",
    "duration": 10,
    "aspect_ratio": "16:9"
  }
}'

submit "013 — Machiventa: leaning forward" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Ancient wise man leaning forward slightly toward camera, engaged and earnest, gentle intensity, speaking carefully, warm golden light from the side",
    "image_path": "machiventa_reference.jpg",
    "duration": 10,
    "aspect_ratio": "16:9"
  }
}'

submit "014 — Machiventa: love" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Ancient teacher with expression of deep love and tenderness, eyes slightly moist, speaking softly, head tilted gently, warm light, cosmic background fading",
    "image_path": "machiventa_reference.jpg",
    "duration": 10,
    "aspect_ratio": "16:9"
  }
}'

# Brother Thomas
submit "020 — Thomas: careful" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Man in priest collar speaking carefully and thoughtfully, choosing words with precision, slight pause before speaking, intellectual honesty in expression, soft studio light",
    "image_path": "brother_thomas_reference.jpg",
    "duration": 10,
    "aspect_ratio": "16:9"
  }
}'

submit "021 — Thomas: quiet admission" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Man in priest collar with expression of quiet internal conflict, looking slightly down then making eye contact with camera, sincere vulnerability, soft light",
    "image_path": "brother_thomas_reference.jpg",
    "duration": 10,
    "aspect_ratio": "16:9"
  }
}'

submit "022 — Thomas: Paul theology" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Theologian in priest collar speaking with academic precision, slightly raised eyebrow, explaining with measured authority, referencing knowledge, direct eye contact",
    "image_path": "brother_thomas_reference.jpg",
    "duration": 10,
    "aspect_ratio": "16:9"
  }
}'

submit "023 — Thomas: Then Paul" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Man in priest collar saying something quietly with weight, slight pause, subdued expression, as if completing an unspoken thought, gentle light",
    "image_path": "brother_thomas_reference.jpg",
    "duration": 5,
    "aspect_ratio": "16:9"
  }
}'

# Sister Amara
submit "030 — Amara: childhood memory" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Young woman speaking with quiet intensity, recalling a memory, slightly distant gaze then returning to camera, warm and grounded, emotionally present, soft light",
    "image_path": "sister_amara_reference.jpg",
    "duration": 10,
    "aspect_ratio": "16:9"
  }
}'

submit "031 — Amara: stillness" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Woman becoming very still, a moment of inner recognition, eyes slightly wide, then quiet resolve, natural and unperformed, warm light from side",
    "image_path": "sister_amara_reference.jpg",
    "duration": 5,
    "aspect_ratio": "16:9"
  }
}'

submit "032 — Amara: love test" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Woman speaking with calm certainty, direct and grounded, making a clear logical point, gentle gestures, eyes steady on camera, natural authority",
    "image_path": "sister_amara_reference.jpg",
    "duration": 10,
    "aspect_ratio": "16:9"
  }
}'

submit "033 — Amara: invitation" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Woman speaking with quiet warmth and depth, almost as if confiding, slight forward lean, sincere and inviting, soft light",
    "image_path": "sister_amara_reference.jpg",
    "duration": 10,
    "aspect_ratio": "16:9"
  }
}'

# Group shot
submit "001 — Group establishing" '{
  "handler": "image_to_video",
  "payload": {
    "prompt": "Three figures in a cosmic space setting, planet Earth glowing behind them, slow gentle breathing, subtle atmospheric light shifts, cinematic stillness, no speaking",
    "image_path": "group_shot_reference.jpg",
    "duration": 10,
    "aspect_ratio": "16:9"
  }
}'

echo ""
echo "=== All clips submitted. ==="
echo "Monitor: docker logs seedanceclaw --tail 30"
echo "Videos land in: /opt/seedanceclaw-data/videos/"
echo "Done: $(date)"
