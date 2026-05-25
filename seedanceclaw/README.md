# SeedanceClaw

**Truthful label:** deployable scaffold. Real handlers: `text_to_video`,
`image_to_video`, `download_video`. Requires a `FAL_KEY` from fal.ai.

Singular primary role: **controlled execution** (video-generation sub-role).
Calls ByteDance Seedance models via the fal.ai API and saves the resulting
video locally. Does not observe, remediate, adjudicate, explain, or bundle
evidence — those belong to NemoClaw / Fireclaw / LuciferiClaw /
VisualUrantiClaw / Paperclip respectively.

UrantiOS governed — Truth, Beauty, Goodness.

---

## Canonical sentence

> NemoClaw sees. VisualUrantiClaw explains. Fireclaw reacts to technical
> faults. LuciferiClaw adjudicates intent and mandate violation.
> **OpenClaw instances execute.** Paperclip preserves the evidence.

SeedanceClaw is another OpenClaw-class instance. Same role (controlled
execution), different sub-scope: AI video generation via Seedance.

---

## Pipeline

```
  operator supplies prompt / image
          │
          ▼    text_to_video / image_to_video   # fal.ai Seedance API
  fal.ai generates video (hosted URL)
          │
          ▼    auto-download                    # httpx streams the file
  /data/videos/<stem>.mp4
```

Every handler call emits an evidence record under `/data/evidence/`.

---

## Allowlist — the canonical boundary

```python
ALLOWED_HANDLERS = {
    "smoke_test",
    "text_to_video",    # REAL — requires FAL_KEY
    "image_to_video",   # REAL — requires FAL_KEY + image URL or local path
    "download_video",   # REAL — fetch any video URL to /data/videos/
}
```

Anything outside this set is **rejected** with an evidence record
stamped `status: rejected`.

---

## Prerequisites

1. A fal.ai account and API key: <https://fal.ai>
2. Docker + Docker Compose plugin
3. The `FAL_KEY` set in `seedanceclaw/.env` (the install script prompts you)

---

## Install + run

```bash
cd ~/mircea-constellation
bash setup/seedanceclaw_install.sh
```

The installer:
1. Checks Docker is available and refuses to run as root.
2. Discovers UID/GID via `id -u` / `id -g` (no hardcoding).
3. Creates `/opt/seedanceclaw-data/` with correct ownership.
4. Writes `seedanceclaw/.env` preserving an existing `FAL_KEY`.
5. Runs `docker compose up --build -d` from `seedanceclaw/`.
6. Waits for `/health` to respond.

### Verify

```bash
docker logs seedanceclaw --tail 30
curl -s http://127.0.0.1:8086/health | python3 -m json.tool
```

`/health` returns `fal_client_installed`, `fal_key_set`, and current
model IDs. If `fal_key_set` is `false`, the generation handlers refuse.

---

## Invoke a handler

The only way to run handlers is `POST /tasks` (bound to `127.0.0.1:8086`):

```bash
# Smoke test
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{"handler":"smoke_test","payload":{}}'

# Text → video (5 s, 16:9, 720p)
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "text_to_video",
    "payload": {
      "prompt": "A golden sunset over the ocean, cinematic, slow pan",
      "duration": 5,
      "aspect_ratio": "16:9",
      "resolution": "720p"
    }
  }'

# Image → video (local file under /opt/seedanceclaw-data/images/)
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Camera slowly zooms in, gentle breeze moves the trees",
      "image_path": "landscape.jpg",
      "duration": 5,
      "aspect_ratio": "16:9"
    }
  }'

# Image → video (remote image URL)
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "image_to_video",
    "payload": {
      "prompt": "Stars begin to appear in the night sky",
      "image_url": "https://example.com/photo.jpg",
      "duration": 10
    }
  }'

# Download a video by URL
curl -sX POST http://127.0.0.1:8086/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "handler": "download_video",
    "payload": {
      "url": "https://cdn.fal.ai/outputs/example.mp4",
      "stem": "my_video"
    }
  }'
```

Generated videos land in `/opt/seedanceclaw-data/videos/`.

---

## Switching to Seedance 2.0

Set `SEEDANCE_MODEL_T2V` and/or `SEEDANCE_MODEL_I2V` in
`seedanceclaw/.env`, then restart the container:

```bash
# In seedanceclaw/.env:
SEEDANCE_MODEL_T2V=fal-ai/bytedance/seedance/v2/text-to-video
SEEDANCE_MODEL_I2V=fal-ai/bytedance/seedance/v2/image-to-video

docker compose -f seedanceclaw/docker-compose.yml restart
```

---

## Configuration surface

| Env var                | Default                                                | Purpose                        |
|------------------------|--------------------------------------------------------|--------------------------------|
| `CLAW_NAME`            | `SeedanceClaw`                                         | Logged on every record         |
| `DATA_ROOT`            | `/data`                                                | Bind-mounted host path         |
| `LOG_LEVEL`            | `INFO`                                                 |                                |
| `HTTP_PORT`            | `8086`                                                 |                                |
| `FAL_KEY`              | *(required)*                                           | fal.ai API key                 |
| `SEEDANCE_MODEL_T2V`   | `fal-ai/bytedance/seedance/v1/pro/text-to-video`       | Text-to-video model ID         |
| `SEEDANCE_MODEL_I2V`   | `fal-ai/bytedance/seedance/v1/pro/image-to-video`      | Image-to-video model ID        |

---

## What this is **not** yet

- Not a batch processor. Each `/tasks` call generates one video; a batch
  handler can be added without touching the existing pipeline.
- Not a local GPU runner. All inference happens on fal.ai's cloud;
  no local GPU is needed.
- Not Paperclip-integrated. Emits evidence records; bundling will come
  from Paperclip under its own contract.
