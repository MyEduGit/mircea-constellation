# n8n Setup Plan — Mircea
**Email:** mirceamatthews@gmail.com
**Date:** April 12, 2026

---

## TWO OPTIONS — Pick One

---

## OPTION A — n8n Cloud (Easiest)

No server setup. n8n runs for you in the cloud.

### Step 1 — Sign Up
1. Go to: **app.n8n.cloud**
2. Click **"Get started free"**
3. Enter email: `mirceamatthews@gmail.com`
4. Choose a password
5. Verify your email

### Step 2 — Choose a Plan
- **Free trial:** 14 days, all features
- **Starter plan:** ~$20/month — good for personal use
- **Pro plan:** ~$50/month — more workflows

### Step 3 — You Are Done
- Your n8n is at: `https://your-name.app.n8n.cloud`
- No SSH needed
- Works from iPhone, iMac, anywhere

---

## OPTION B — Self-Hosted on OpenClaw (Already Running)

Your n8n is **already installed** on your Hetzner server.
Server IP: `46.225.51.30`

### Problem: No Email Set Yet
The n8n owner account was set up without an email, or uses a different email.

### Fix: Update the Owner Email

**Step 1 — SSH into your server:**
```bash
ssh root@46.225.51.30
```

**Step 2 — Find your n8n Docker folder:**
```bash
cd /home/mircea/nemoclaw
```

**Step 3 — Check current n8n config:**
```bash
cat docker-compose.yml | grep -i email
```

**Step 4 — Update the n8n owner email:**
```bash
# Stop n8n
docker compose stop n8n

# Edit the env file
nano bot.env
```

Add or update these lines:
```
N8N_EMAIL_MODE=smtp
N8N_SMTP_HOST=smtp.gmail.com
N8N_SMTP_PORT=587
N8N_SMTP_USER=mirceamatthews@gmail.com
N8N_SMTP_PASS=YOUR_GMAIL_APP_PASSWORD
N8N_SMTP_SENDER=mirceamatthews@gmail.com
```

**Step 5 — Start n8n again:**
```bash
docker compose up -d n8n
```

**Step 6 — Access n8n from Mac:**
```bash
ssh -L 5678:localhost:5678 root@46.225.51.30
```
Then open: **http://localhost:5678**

---

## GMAIL APP PASSWORD (needed for Option B)

Gmail requires an "App Password" — NOT your regular password.

1. Go to: **myaccount.google.com/security**
2. Click **"2-Step Verification"** → make sure it is ON
3. Go back to Security → scroll down to **"App passwords"**
4. Create new → name it "n8n"
5. Copy the 16-character password
6. Paste it into `N8N_SMTP_PASS=` in bot.env

---

## MY RECOMMENDATION

| | Option A (Cloud) | Option B (Self-Hosted) |
|---|---|---|
| Ease | Very easy | Needs SSH |
| Cost | $20/month | Already paying for server |
| Speed | Fast | Fast |
| Control | Limited | Full control |

**For Mircea:** Start with **Option A** (Cloud) to test n8n easily.
Then decide if you want to move to your own server.

---

## WHAT TO DO RIGHT NOW

### If you pick Option A (Cloud):
1. Go to **app.n8n.cloud**
2. Sign up with `mirceamatthews@gmail.com`
3. Tell me "n8n cloud is ready" — I will create your first workflow

### If you pick Option B (Self-hosted):
1. SSH into server: `ssh root@46.225.51.30`
2. Tell me "I am on the server" — I will walk you through each step

---

*Saved to GitHub — branch: claude/setup-n8n-plan-dwIle*
