# JabbokRiverProductions — Operator Runbook

Everything in this document requires a human operator. The repo holds
the scaffold; nothing here can be done by an automation alone.

---

## Hard launch gate

> **No public upload is permitted until ALL of the following are true.**

- [ ] Dr. Emanoil Geaboc has given **written consent** to be the face of
      JabbokRiverProductions, with a signed letter on file under
      `channels/jabbokriver/consent/<YYYY-MM-DD>-geaboc-consent.pdf`.
      **Draft letters ready to send:**
      `channels/jabbokriver/consent/LETTER-TEMPLATE-ro.md` (Romanian)
      and `LETTER-TEMPLATE-en.md` (English) — fill the `[bracketed]`
      blanks, print, mail/email.
- [ ] `channels/jabbokriver/channel.json` field
      `host.consent_status` has been flipped from `"pending"` to
      `"confirmed"`, with `consent_confirmed_at` set to the ISO-8601
      timestamp.
- [ ] The first episode has passed a Council of Seven review with a
      written evidence record under
      `/opt/scribeclaw-data/evidence/`.
- [ ] At least one source-video entry in `catalog.yaml` has a
      `rights_note` that is reviewed and accepted by the operator.

If any box is unchecked, **do not publish**. The infrastructure is
deliberately quiet (no `youtube_upload` handler) until you say go.

---

## 1. Create the YouTube channel (one-time)

1. Sign in to a Google Account dedicated to JabbokRiverProductions
   (recommended: `messagetostephanos@gmail.com` per the existing
   archive).
2. YouTube → **Settings → Add or manage your channel(s) → Create a
   channel** → **Use a custom name** → `JabbokRiverProductions`.
3. Verify the channel by phone (required for thumbnails > 1MB and
   videos > 15 min).
4. Set: handle `@JabbokRiverProductions`, **channel art** via the
   pre-built banner composition:
   ```
   cd remotion
   npx remotion render ChannelBanner out/channel-banner.png --frame=0
   npx remotion render ChannelAvatar out/channel-avatar.png --frame=0
   ```
   Upload `channel-banner.png` (2560×1440) as "Banner image" and
   `channel-avatar.png` (1080×1080) as "Picture". About text: copy
   `channel.json` → `thesis.en`.
5. Configure default upload settings: language `Romanian`, license
   `Standard YouTube License`, category `Education`.

## 2. OAuth credentials for `youtube_upload`

The `youtube_upload` handler in `scribeclaw/youtube.py` is now fully
implemented. It reads the metadata bundle, calls YouTube Data API v3
`videos.insert`, and returns a structured `not_ready` refusal if any
prerequisite is missing. To enable live uploads:

1. **Google Cloud project:** Cloud Console → create project
   `jabbokriver-upload` → enable **YouTube Data API v3**.
2. **OAuth client:** create an OAuth 2.0 Client ID (Desktop) and
   download `client_secret.json`.
3. **Install on the operator host:**
   ```
   mkdir -p /opt/scribeclaw-data/youtube/credentials
   mv ~/Downloads/client_secret_*.json \
      /opt/scribeclaw-data/youtube/credentials/client_secret.json
   chmod 600 /opt/scribeclaw-data/youtube/credentials/client_secret.json
   ```
4. **Install optional Python deps** (scribeclaw core does not need
   these; the handler imports them lazily and refuses gracefully):
   ```
   pip install google-api-python-client google-auth google-auth-oauthlib
   ```
5. **Mint a refresh token** (one-time, requires a browser):
   ```python
   # save as bootstrap_refresh_token.py and run once on the operator host
   from google_auth_oauthlib.flow import InstalledAppFlow
   import json, pathlib
   SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
   creds_dir = pathlib.Path("/opt/scribeclaw-data/youtube/credentials")
   flow = InstalledAppFlow.from_client_secrets_file(
       str(creds_dir / "client_secret.json"), SCOPES)
   creds = flow.run_local_server(port=0)
   (creds_dir / "refresh_token.json").write_text(json.dumps({
       "refresh_token": creds.refresh_token
   }))
   ```
6. **Dry-run before the first real upload** — the handler will validate
   everything without hitting the YouTube API:
   ```
   curl -X POST http://127.0.0.1:8081/tasks \
     -H 'content-type: application/json' \
     -d '{"handler":"youtube_upload","payload":{
            "stem":"<id>.edited",
            "dry_run":true,
            "privacy":"unlisted"
          }}'
   ```
7. **Live upload** (only after the hard launch gate at the top of this
   doc is green):
   ```
   curl -X POST http://127.0.0.1:8081/tasks \
     -H 'content-type: application/json' \
     -d '{"handler":"youtube_upload","payload":{
            "stem":"<id>.edited",
            "video_path":"/opt/scribeclaw-data/media/edited/<id>.final.mp4",
            "privacy":"private"
          }}'
   ```
   Start with `privacy:"private"`, verify on YouTube Studio, then flip
   to `unlisted` or `public` manually. The handler never auto-publishes.

## 3. Pull the operator-held archive from `messagetostephanos@gmail.com`

The repo deliberately does **not** ship Gmail/Drive API code. Use Google
Takeout instead:

1. https://takeout.google.com → sign in as `messagetostephanos@gmail.com`.
2. Deselect everything except **Drive** (and **Mail** if recordings are
   email attachments).
3. Filter by folder/label that holds the Geaboc recordings; export as
   `.zip`.
4. Extract on the operator host into:
   ```
   /opt/scribeclaw-data/media/in/stephanos-archive/
   ```
5. For each video, add an entry to `catalog.yaml` with
   `source_channel: "messagetostephanos@gmail.com (operator-held)"`
   and `download_status: downloaded`.

## 4. Catalog the public source videos

For each Dr. Geaboc upload on a public SDA YouTube channel:

1. Append an entry to `channels/jabbokriver/catalog.yaml`:
   - `id`: short slug (e.g. `geaboc-003`)
   - `title`: from the source video
   - `source_url`: full YouTube URL
   - `source_channel`: human-readable name of the SDA channel
   - `series`: one of the `series.json` keys
   - `rights_note`: state the public-availability + commentary intent
2. Validate:
   ```
   python channels/jabbokriver/tools/validate_catalog.py
   ```
3. Dry-run the archiver (default; prints commands, touches nothing):
   ```
   python channels/jabbokriver/tools/catalog_fetch.py
   ```
4. When ready to actually pull (requires `yt-dlp` on PATH):
   ```
   python channels/jabbokriver/tools/catalog_fetch.py --execute
   ```

## 5. Per-episode workflow

```
catalog entry → archive → transcribe → council review → render → upload
```

1. Pick a `download_status: downloaded` entry from `catalog.yaml`.
2. Run the scribeclaw pipeline (see `scribeclaw/main.py` `--mode pipeline`):
   ```
   curl -X POST http://127.0.0.1:8081/tasks \
     -H 'content-type: application/json' \
     -d '{"handler":"media_edit","payload":{"input":"<id>.mp4"}}'
   curl -X POST http://127.0.0.1:8081/tasks \
     -H 'content-type: application/json' \
     -d '{"handler":"audio_extract","payload":{"input":"<id>.edited.mp4"}}'
   curl -X POST http://127.0.0.1:8081/tasks \
     -H 'content-type: application/json' \
     -d '{"handler":"transcribe_ro","payload":{"input":"<id>.edited.wav"}}'
   curl -X POST http://127.0.0.1:8081/tasks \
     -H 'content-type: application/json' \
     -d '{"handler":"postprocess_transcript","payload":{"stem":"<id>.edited"}}'
   curl -X POST http://127.0.0.1:8081/tasks \
     -H 'content-type: application/json' \
     -d '{"handler":"youtube_metadata","payload":{
            "stem":"<id>.edited",
            "channel_slug":"jabbokriver",
            "series":"religia-lui-vs-religia-despre-isus"
          }}'
   ```
3. Submit the resulting `bundle.json` to the Council of Seven for
   pre-publish review (workflow at `/council/council_of_seven_v1.n8n.json`).
   Council writes an evidence record; that record is required by the
   launch gate.
4. Render Remotion intro/outro/lower-third/thesis card:
   ```
   cd remotion
   npx remotion render JabbokIntro out/<id>-intro.mp4
   npx remotion render JabbokOutro out/<id>-outro.mp4
   npx remotion render ThesisTitleCard out/<id>-thesis.mp4 \
     --props='{"thesisRo":"...","thesisEn":"...","subCaption":"..."}'
   ```
5. Concatenate (operator's choice of NLE) the rendered intro + your
   editorial commentary + outro. **Do not include full re-uploads of
   the source video.** Short excerpts under commentary only.
6. Upload. Two options depending on whether you've wired OAuth (§2):
   - **OAuth wired:** `dry_run: true` first, then live with
     `privacy:"private"`; verify in Studio; manually flip to public.
   - **Manual:** upload through YouTube Studio. Tags + description:
     copy from `/opt/scribeclaw-data/youtube/<id>.edited/description.txt`
     and `tags.txt`.
7. After upload, set `commentary_episode_id` and bump
   `transcription_status: done` in `catalog.yaml`.

## 6. Per-source rights checklist (catalog & link policy)

For each new SDA source channel you reference:

- [ ] Source channel is publicly viewable on YouTube.
- [ ] Source channel does not display a "no derivatives" banner or
      explicit re-use prohibition.
- [ ] Your editorial cut uses **short excerpts only** (rule of thumb:
      under 30s consecutive, under 10% of source runtime in total).
- [ ] Your description names the source channel and links the original
      video.
- [ ] If in doubt, contact the source-channel operator before publish.

If the source channel asks you to take down or stop referencing them,
**comply immediately** and remove the catalog entry.

## 7. Update the dashboard counters

After each successful episode publish, bump
`status.json` → `jabbokriver.videos_transcribed`. The constellation
dashboard (`index.html`) will reflect it on its next 30-second refresh.
