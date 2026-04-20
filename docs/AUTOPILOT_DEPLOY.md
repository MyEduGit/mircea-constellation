# Autopilot Deploy — URANTiOS

> Every merge to `main` that touches ingestion files automatically deploys to
> URANTiOS (204.168.143.98). One-time SSH setup; no human hands after that.

UrantiOS governed — Truth, Beauty, Goodness.

---

## What this gives you

- **Trigger:** push to `main` that changes any of:
  - `openclaw_ingest/**`
  - `setup/openclaw_ingest_install.sh`
  - `cognee_config.py`
  - `.github/workflows/deploy-urantios.yml` (the workflow itself)
- **Action:** GitHub Actions runner SSHes into `mircea@204.168.143.98`, runs
  `git pull` on `main`, executes `bash setup/openclaw_ingest_install.sh`,
  verifies the container is healthy, prints the last 20 log lines.
- **Manual trigger:** also runnable from the Actions UI via "Run workflow".
- **Concurrency:** only one deploy at a time; in-flight deploys never get
  cancelled by a newer push.

## One-time setup (≈3 minutes)

You do this **once**. After that, every deploy is automatic.

### 1. Generate (or pick) a deploy keypair on your iMac

A dedicated key for this deploy is safer than reusing your personal key:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/urantios_deploy -N "" -C "github-actions-urantios-deploy"
```

This creates:
- `~/.ssh/urantios_deploy`     ← private key (goes into GitHub secret)
- `~/.ssh/urantios_deploy.pub` ← public key (goes onto URANTiOS)

### 2. Authorize the key on URANTiOS

```bash
ssh-copy-id -i ~/.ssh/urantios_deploy.pub mircea@204.168.143.98
# verify it works (should not prompt for password):
ssh -i ~/.ssh/urantios_deploy mircea@204.168.143.98 'whoami && hostname'
```

### 3. Capture URANTiOS host fingerprint

The workflow needs to know URANTiOS's host key so it can refuse to connect to
an impostor (MITM protection):

```bash
ssh-keyscan -t rsa,ecdsa,ed25519 204.168.143.98 2>/dev/null
```

Copy the **entire output** (3 lines, one per algorithm).

### 4. Add the two secrets to the repo

Go to: `https://github.com/MyEduGit/mircea-constellation/settings/secrets/actions`

Click **New repository secret** twice:

| Name                  | Value                                                |
|-----------------------|------------------------------------------------------|
| `URANTIOS_SSH_KEY`    | Paste the entire contents of `~/.ssh/urantios_deploy` (private key, including the BEGIN/END lines). |
| `URANTIOS_HOST_KEY`   | Paste the `ssh-keyscan` output from step 3 (3 lines). |

That's it. Setup is done.

## Verify the autopilot

Either:

- **Manual trigger** (recommended for first run):
  - Actions tab → "Deploy OpenClaw@URANTiOS-ingest" → "Run workflow" → branch `main` → Run
- **Or push a small change** to any path the workflow watches.

You should see in the Actions log:
- "Required secrets present."
- `[urantios] HEAD now at: <sha> — <commit subject>`
- `[urantios] running setup/openclaw_ingest_install.sh`
- `[urantios] healthy after N attempts`
- A pretty-printed `/health` JSON
- Last 20 lines of `docker logs openclaw-ingest`
- Last 5 evidence file entries

## Rollback

The install script is idempotent. To roll back:

```bash
# On URANTiOS, manually:
cd ~/mircea-constellation
git checkout <previous-good-sha>
bash setup/openclaw_ingest_install.sh
```

Or revert the bad commit on `main` via a PR — the next merge will auto-deploy
the revert.

## Safety properties

- **No new privileges in container:** `security_opt: no-new-privileges:true` (already in compose).
- **Loopback-only port:** `127.0.0.1:8080` — never exposed externally.
- **Refused root:** install script aborts if invoked as root.
- **Idempotent:** re-running `setup/openclaw_ingest_install.sh` against the
  same SHA is a no-op beyond rebuilding the image.
- **Concurrency lock:** only one deploy at a time; new pushes queue.
- **Key teardown:** the workflow shreds the SSH key from the runner after the
  job completes.
- **Honest health gate:** the workflow fails if `/health` doesn't respond
  within ~40 seconds.

## Limitations honestly named

- **Only deploys OpenClaw@URANTiOS-ingest.** Fireclaw and LuciferiClaw are
  installed manually on the iMac (different host; different deploy story).
  Future workflows can add them.
- **Cognee health is not gated.** `cognee_ready: true` is reported in
  `/health` but the workflow does not yet fail on `cognee_ready: false`.
  Add `jq -e '.cognee_ready == true'` to the verify step once the Cognee
  side is stable.
- **No notification.** Failure is visible in the Actions UI; no Telegram /
  email yet. Add when Paperclip ships and owns evidence binding.
- **Single host.** If URANTiOS is unreachable, the deploy fails. There is no
  failover (intentionally — the topology is single-host by design at this
  scale).

## What changed in this PR

- `.github/workflows/deploy-urantios.yml` — the workflow.
- `docs/AUTOPILOT_DEPLOY.md` — this document.

Nothing else. Pure automation; no app changes.
