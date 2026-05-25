# NemoClaw M4 Bootstrap — Write via Execute Command

## Context

The n8n **"Write File to Disk"** node fails with `not writable` even when the bind mount
and host permissions are confirmed working. This is a known n8n node bug on some Docker
configurations. The fix is to bypass it entirely using **Execute Command**.

---

## ONE-STEP IMPORT (fastest path)

### Step 1 — Import the workflow

1. Open n8n at **http://127.0.0.1:5678**
2. Click **+** (new workflow) → **Import from File**
3. Select: `setup/n8n_exec_cmd_workflow.json`
4. Click **Import**

---

## MANUAL BUILD (if import fails)

### Step 1 — Open n8n

```
http://127.0.0.1:5678
```

### Step 2 — Create new workflow

Click **+** in the top-left.

### Step 3 — Add Manual Trigger

Click **+** node → search **Manual Trigger** → select it.

### Step 4 — Add Execute Command node

Click **+** after the trigger → search **Execute Command** → select it.

In the **Command** field, paste exactly:

```
echo "Hello from NemoClaw" > /files/obsidian/test.md && echo "WRITE_OK" && cat /files/obsidian/test.md
```

### Step 5 — Execute

Click **Execute Workflow** (top right).

---

## EXPECTED OUTPUT

The Execute Command node returns:

```
WRITE_OK
Hello from NemoClaw
```

---

## VERIFY ON HOST

Run in Terminal on the Mac:

```bash
cat ~/Documents/Urantia\ Research\ Wiki/OpenClaw/URANTiOS/nemoclaw/obsidian/test.md
```

Expected output:

```
Hello from NemoClaw
```

---

## WHY THIS WORKS

The `echo >` shell redirect bypasses n8n's internal file-write abstraction, which
incorrectly checks writability via a Node.js `fs.access` call that fails in some
Docker setups even when the path is actually writable. The shell has direct POSIX
access to the bind-mount and succeeds unconditionally.

---

## NEXT: Parameterised writes

Once verified, replace the hardcoded command with an expression to write any content:

```
echo {{ $json.content }} > /files/obsidian/{{ $json.filename }}
```

Wire this to an HTTP Webhook trigger to accept jobs from NemoClaw dispatcher.
