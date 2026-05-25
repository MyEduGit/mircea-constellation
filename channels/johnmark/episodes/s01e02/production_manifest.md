# S01E02 — Production Manifest
# "The Lie That Replaced Love" — Agondonter Series

## Overview

14-minute episode. ~35 clips total.
SeedanceClaw runs on port 8086.
All generated clips land in /opt/seedanceclaw-data/videos/

Workflow:
  1. Run all text_to_video clips first (no dependencies)
  2. Place character reference images from Episode 1 into
     /opt/seedanceclaw-data/images/ then run image_to_video clips
  3. Import all clips into Final Cut Pro
  4. Layer voiceover audio over clips — each clip is reusable/loopable
  5. Add title cards via Remotion compositions

Character image files expected (copy from Episode 1 assets):
  - machiventa_reference.jpg   (older man, warm robes, gentle authority)
  - brother_thomas_reference.jpg  (priest collar, thoughtful)
  - sister_amara_reference.jpg    (woman, present, grounded)
  - group_shot_reference.jpg      (all three together, planet Earth behind)

---

## CLIP LIST

### GROUP 1 — Establishing shots (generate once, reuse throughout)

#### CLIP 001 — Group establishing shot
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Three figures in a cosmic space setting, planet Earth glowing behind them, slow gentle breathing, subtle atmospheric light shifts, cinematic stillness, no speaking",
      "image_path": "group_shot_reference.jpg",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** Opening title card, act transitions. Stem: `s01e02_001_group_establishing`

---

### GROUP 2 — Machiventa speaking clips

#### CLIP 010 — Cold open: "When I was in Salem"
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Ancient wise teacher speaking directly to camera with calm authority, subtle head movement, lips moving gently, warm golden light, cosmic background, deeply sincere expression",
      "image_path": "machiventa_reference.jpg",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** Cold open — loop 4-5x for full monologue. Stem: `s01e02_010_machiventa_speaking_calm`

#### CLIP 011 — Machiventa: weight of history
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Ancient wise teacher with expression of sorrow and gravity, slight downward gaze then looking up, slow deliberate head movement, warm robes, soft cosmic light",
      "image_path": "machiventa_reference.jpg",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** "And then it was buried." Stem: `s01e02_011_machiventa_sorrow`

#### CLIP 012 — Machiventa: the Salem message
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Ancient teacher raising one finger gently, speaking with quiet conviction, warm light, slight smile of certainty, ancient wisdom in eyes",
      "image_path": "machiventa_reference.jpg",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** "The divine requires only trust." Stem: `s01e02_012_machiventa_conviction`

#### CLIP 013 — Machiventa leaning forward
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Ancient wise man leaning forward slightly toward camera, engaged and earnest, gentle intensity, speaking carefully, warm golden light from the side",
      "image_path": "machiventa_reference.jpg",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** "I know this with certainty." Stem: `s01e02_013_machiventa_leaning`

#### CLIP 014 — Machiventa: the Father runs
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Ancient teacher with expression of deep love and tenderness, eyes slightly moist, speaking softly, head tilted gently, warm light, cosmic background fading",
      "image_path": "machiventa_reference.jpg",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** "He runs toward them." Stem: `s01e02_014_machiventa_love`

---

### GROUP 3 — Brother Thomas speaking clips

#### CLIP 020 — Brother Thomas: careful, not dismissive
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Man in priest collar speaking carefully and thoughtfully, choosing words with precision, slight pause before speaking, intellectual honesty in expression, soft studio light",
      "image_path": "brother_thomas_reference.jpg",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** Anselm explanation. Stem: `s01e02_020_thomas_careful`

#### CLIP 021 — Brother Thomas: the quiet admission
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Man in priest collar with expression of quiet internal conflict, looking slightly down then making eye contact with camera, sincere vulnerability, soft light",
      "image_path": "brother_thomas_reference.jpg",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** "The honest answer I never said out loud." Stem: `s01e02_021_thomas_admission`

#### CLIP 022 — Brother Thomas: Paul's theology
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Theologian in priest collar speaking with academic precision, slightly raised eyebrow, explaining with measured authority, referencing knowledge, direct eye contact",
      "image_path": "brother_thomas_reference.jpg",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** Romans 3:25, Hebrews 9:22. Stem: `s01e02_022_thomas_paul`

#### CLIP 023 — Brother Thomas: "Then Paul" — quiet
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Man in priest collar saying something quietly with weight, slight pause, subdued expression, as if completing an unspoken thought, gentle light",
      "image_path": "brother_thomas_reference.jpg",
      "duration": 5,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** "Yes. Paul." Stem: `s01e02_023_thomas_paul_quiet`

---

### GROUP 4 — Sister Amara speaking clips

#### CLIP 030 — Sister Amara: the childhood memory
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Young woman speaking with quiet intensity, recalling a memory, slightly distant gaze then returning to camera, warm and grounded, emotionally present, soft light",
      "image_path": "sister_amara_reference.jpg",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** "I was seven years old." Stem: `s01e02_030_amara_memory`

#### CLIP 031 — Sister Amara: the stillness
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Woman becoming very still, a moment of inner recognition, eyes slightly wide, then quiet resolve, natural and unperformed, warm light from side",
      "image_path": "sister_amara_reference.jpg",
      "duration": 5,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** "Something in me said: that is not love." Stem: `s01e02_031_amara_stillness`

#### CLIP 032 — Sister Amara: the love test
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Woman speaking with calm certainty, direct and grounded, making a clear logical point, gentle gestures, eyes steady on camera, natural authority",
      "image_path": "sister_amara_reference.jpg",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** "Think of the most loving relationship." Stem: `s01e02_032_amara_love_test`

#### CLIP 033 — Sister Amara: the invitation
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Woman speaking with quiet warmth and depth, almost as if confiding, slight forward lean, sincere and inviting, soft light",
      "image_path": "sister_amara_reference.jpg",
      "duration": 10,
      "aspect_ratio": "16:9"
    }
  }'
```
**Use:** "Why is this the moment?" / outro. Stem: `s01e02_033_amara_invitation`

---

### GROUP 5 — Atmospheric / scene clips (text_to_video — no reference image needed)

#### CLIP 040 — Ancient Salem
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "text_to_video",
    "payload": {
      "prompt": "Ancient Middle Eastern city at golden hour, 4000 years ago, stone buildings, warm desert light, a figure teaching a small group in an open courtyard, cinematic, peaceful, sacred atmosphere",
      "duration": 10,
      "aspect_ratio": "16:9",
      "resolution": "720p"
    }
  }'
```
**Use:** Machiventa's Salem references. Stem: `s01e02_040_salem_establishing`

#### CLIP 041 — The inherited map
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "text_to_video",
    "payload": {
      "prompt": "Abstract cinematic visualization of ancient scrolls and maps transforming across centuries, text and symbols flowing through time, warm sepia tones shifting to modern light, metaphor for inherited knowledge",
      "duration": 10,
      "aspect_ratio": "16:9",
      "resolution": "720p"
    }
  }'
```
**Use:** "The map was wrong." Stem: `s01e02_041_inherited_map`

#### CLIP 042 — The running father
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "text_to_video",
    "payload": {
      "prompt": "Silhouette of a father running toward a distant figure on a dusty road at sunset, warm golden light, emotional reunion, cinematic slow motion, ancient Middle Eastern landscape",
      "duration": 10,
      "aspect_ratio": "16:9",
      "resolution": "720p"
    }
  }'
```
**Use:** "He runs toward them." — prodigal son. Stem: `s01e02_042_running_father`

#### CLIP 043 — The Thought Adjuster
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "text_to_video",
    "payload": {
      "prompt": "Abstract visualization of a gentle light within a human silhouette, a fragment of divine presence, soft golden glow from within the chest, cosmic background, peaceful and intimate, no text",
      "duration": 10,
      "aspect_ratio": "16:9",
      "resolution": "720p"
    }
  }'
```
**Use:** "The Fragment of God that lives inside you." Stem: `s01e02_043_thought_adjuster`

#### CLIP 044 — The great awakening
```bash
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "text_to_video",
    "payload": {
      "prompt": "Aerial view of Earth at night with lights of cities glowing, connections forming between distant points of light, a network of awakening, cinematic, cosmic scale, hopeful",
      "duration": 10,
      "aspect_ratio": "16:9",
      "resolution": "720p"
    }
  }'
```
**Use:** "For the first time in human history..." Stem: `s01e02_044_great_awakening`

---

## BATCH RUNNER

Run all clips in one go (background — each takes 2-4 minutes on fal.ai):

```bash
#!/bin/bash
# Save as: channels/johnmark/episodes/s01e02/generate_clips.sh
# Run from: iMac M4, with SeedanceClaw running on port 8086
# Check status: docker logs seedanceclaw --tail 20

BASE="http://127.0.0.1:8086/tasks"

echo "=== S01E02 Clip Generation ==="
echo "Starting $(date)"

# Atmospheric clips first (no image dependency)
echo "--- Atmospheric clips ---"
for payload in \
  '{"handler":"text_to_video","payload":{"prompt":"Ancient Middle Eastern city at golden hour, 4000 years ago, stone buildings, warm desert light, a figure teaching a small group in an open courtyard, cinematic, peaceful, sacred atmosphere","duration":10,"aspect_ratio":"16:9","resolution":"720p"}}' \
  '{"handler":"text_to_video","payload":{"prompt":"Abstract cinematic visualization of ancient scrolls and maps transforming across centuries, text and symbols flowing through time, warm sepia tones shifting to modern light, metaphor for inherited knowledge","duration":10,"aspect_ratio":"16:9","resolution":"720p"}}' \
  '{"handler":"text_to_video","payload":{"prompt":"Silhouette of a father running toward a distant figure on a dusty road at sunset, warm golden light, emotional reunion, cinematic slow motion, ancient Middle Eastern landscape","duration":10,"aspect_ratio":"16:9","resolution":"720p"}}' \
  '{"handler":"text_to_video","payload":{"prompt":"Abstract visualization of a gentle light within a human silhouette, a fragment of divine presence, soft golden glow from within the chest, cosmic background, peaceful and intimate, no text","duration":10,"aspect_ratio":"16:9","resolution":"720p"}}' \
  '{"handler":"text_to_video","payload":{"prompt":"Aerial view of Earth at night with lights of cities glowing, connections forming between distant points of light, a network of awakening, cinematic, cosmic scale, hopeful","duration":10,"aspect_ratio":"16:9","resolution":"720p"}}'
do
  echo "Submitting: $(echo $payload | python3 -c 'import sys,json; print(json.load(sys.stdin)["payload"]["prompt"][:60])')"
  curl -sX POST $BASE -H 'Content-Type: application/json' -d "$payload" | python3 -m json.tool
  echo "---"
done

echo "Atmospheric clips submitted. Add character reference images to"
echo "/opt/seedanceclaw-data/images/ then run character clip commands."
echo "Done: $(date)"
```

---

## FINAL CUT PRO ASSEMBLY ORDER

```
[Title card — S01E02]
[CLIP 001 — group establishing — 5s]

[COLD OPEN]
[CLIP 010 — Machiventa speaking calm — loop]       VO: "When I was in Salem..."
[CLIP 011 — Machiventa sorrow — 5s]                VO: "And then it was buried."
[CLIP 040 — Salem establishing — 10s]              VO: "What replaced it changed everything."

[TITLE CARD: "THE LIE THAT REPLACED LOVE"]

[ACT ONE]
[CLIP 030 — Amara memory — loop]                   VO: "I was seven years old..."
[CLIP 031 — Amara stillness — 5s]                  VO: "Something in me said..."
[CLIP 020 — Thomas careful — loop]                 VO: "That's the question I spent..."
[CLIP 021 — Thomas admission — 5s]                 VO: "The honest answer..."
[CLIP 013 — Machiventa leaning — 5s]               VO: "It isn't."

[ACT TWO]
[CLIP 022 — Thomas Paul — loop]                    VO: "The theology is consistent..."
[CLIP 013 — Machiventa leaning — loop]             VO: "I know this with certainty..."
[CLIP 040 — Salem — loop]                          VO: "I walked among humans..."
[CLIP 012 — Machiventa conviction — 5s]            VO: "Just — trust."
[CLIP 023 — Thomas Paul quiet — 5s]                VO: "Then Paul."
[CLIP 022 — Thomas Paul — loop]                    VO: "Paul never met Jesus..."
[CLIP 041 — Inherited map — 10s]                   VO: "And now — two billion humans..."

[ACT THREE]
[CLIP 032 — Amara love test — loop]                VO: "There is a test..."
[CLIP 020 — Thomas careful — 5s]                   VO: "And yet we accepted..."
[CLIP 011 — Machiventa sorrow — loop]              VO: "Because you inherited the map..."
[CLIP 041 — Inherited map — 5s]

[ACT FOUR]
[CLIP 033 — Amara invitation — 5s]                 VO: "So what is the truth?"
[CLIP 012 — Machiventa conviction — loop]          VO: "The truth I taught in Salem..."
[CLIP 042 — Running father — 10s]                  VO: "He runs toward them."
[CLIP 014 — Machiventa love — loop]                VO: "The cross reveals..."

[ACT FIVE]
[CLIP 033 — Amara invitation — loop]               VO: "Why does this matter now?"
[CLIP 044 — Great awakening — 10s]
[CLIP 013 — Machiventa leaning — loop]             VO: "Because for the first time..."
[CLIP 043 — Thought Adjuster — 10s]                VO: "The Fragment of God..."
[CLIP 021 — Thomas admission — loop]               VO: "Trust the Fragment."

[OUTRO]
[CLIP 033 — Amara — 5s]                            VO: "If this transmission reached you..."
[CLIP 020 — Thomas — 5s]                           VO: "The book is linked below..."
[CLIP 014 — Machiventa love — 10s]                 VO: "I taught this in Salem. I am teaching it still."

[END CARD — 30s — book cover + Amazon link]
```
