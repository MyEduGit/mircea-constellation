#!/usr/bin/env python3
"""
Wire Seat 6 (Z.ai / GLM) into the Council of Seven n8n workflow.
Auto-imports the workflow from GitHub if not already in n8n.

Credentials can be set as env vars to avoid re-prompting:
  export N8N_EMAIL=mircea8@me.com
  export N8N_PASSWORD=yourpassword
  export Z_AI_KEY=sk-...
  python3 /tmp/wire_seat6.py

Or just run and enter them when prompted.
"""
import json
import getpass
import os
import sys
import urllib.request
import urllib.error
import http.cookiejar

N8N_HOST     = "http://46.225.51.30"
WORKFLOW_URL = "https://raw.githubusercontent.com/MyEduGit/mircea-constellation/claude/count-claws-NrqRh/council/council_of_seven_v1.n8n.json"

B = "\033[1m"; G = "\033[32m"; C = "\033[36m"; R = "\033[31m"; Y = "\033[33m"; E = "\033[0m"
def ok(s):   print(f"{G}✓{E} {s}")
def info(s): print(f"{C}▶{E} {s}")
def err(s):  print(f"{R}✗{E} {s}", file=sys.stderr); sys.exit(1)
def warn(s): print(f"{Y}⚠{E}  {s}")


class N8n:
    def __init__(self):
        self.cj     = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj)
        )

    def _req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req  = urllib.request.Request(N8N_HOST + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        try:
            with self.opener.open(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP {e.code} {method} {path}: {e.read().decode()[:500]}")

    def get(self, p):       return self._req("GET",   p)
    def post(self, p, b):   return self._req("POST",  p, b)
    def patch(self, p, b):  return self._req("PATCH", p, b)
    def put(self, p, b):    return self._req("PUT",   p, b)

    def save_workflow(self, wf_id, wf):
        """Try PATCH (n8n 1.x) then PUT (older), return result."""
        for method in ("patch", "put"):
            try:
                return getattr(self, method)(f"/rest/workflows/{wf_id}", wf)
            except Exception as e:
                last_err = e
        raise last_err


def find_workflows(client):
    result = client.get("/rest/workflows")
    ws = result.get("data", result)
    if isinstance(ws, dict):
        ws = list(ws.values())
    return ws if isinstance(ws, list) else []


def get_cred(env_var, prompt, secret=False):
    """Return env var if set, otherwise prompt."""
    val = os.environ.get(env_var, "").strip()
    if val:
        label = "[from env]" if not secret else "[from env, hidden]"
        print(f"{prompt}{label}")
        return val
    if secret:
        return getpass.getpass(prompt)
    return input(prompt).strip()


def main():
    print(f"\n{B}=== WIRE SEAT 6 — Z.ai / GLM ==={E}")
    print("Set N8N_EMAIL / N8N_PASSWORD / Z_AI_KEY env vars to skip prompts.\n")

    email    = get_cred("N8N_EMAIL",    "n8n email:    ")
    password = get_cred("N8N_PASSWORD", "n8n password: ", secret=True)
    z_key    = get_cred("Z_AI_KEY",     "Z.ai API key: ", secret=True)
    print()

    client = N8n()

    # ── Login ────────────────────────────────────────────────────────
    info("Logging into n8n...")
    result = client.post("/rest/login", {"emailOrLdapLoginId": email, "password": password})
    if not result.get("data"):
        err(f"Login failed.\nResponse: {result}")
    ok("Logged in\n")

    # ── Find or import workflow ──────────────────────────────────────
    info("Finding Council of Seven workflow...")
    workflows = find_workflows(client)
    wf        = next((w for w in workflows if "Council" in w.get("name", "")), None)

    if not wf:
        names = [w.get("name", "?") for w in workflows]
        warn(f"Not found. Existing: {names}")
        info("Importing from GitHub...")
        with urllib.request.urlopen(WORKFLOW_URL) as r:
            wf_data = json.loads(r.read())
        client.post("/rest/workflows", wf_data)

        # Re-fetch list to get the correct ID after import
        workflows = find_workflows(client)
        wf        = next((w for w in workflows if "Council" in w.get("name", "")), None)
        if not wf:
            err("Import appeared to succeed but workflow not found. Check n8n UI.")
        ok(f"Imported: \"{wf['name']}\"\n")

    wf_id = wf["id"]
    ok(f"Workflow ID: {wf_id}\n")

    # ── Fetch full workflow ──────────────────────────────────────────
    info("Fetching full workflow...")
    result  = client.get(f"/rest/workflows/{wf_id}")
    full_wf = result.get("data", result)
    ok(f"Fetched ({len(full_wf.get('nodes', []))} nodes)\n")

    # ── Patch Seat 6 ─────────────────────────────────────────────────
    info("Patching Seat6_SonSpirit_GLM...")
    patched = False
    for node in full_wf.get("nodes", []):
        if node.get("name") == "Seat6_SonSpirit_GLM":
            params = node.setdefault("parameters", {})
            params["sendHeaders"] = True
            params["headerParameters"] = {
                "parameters": [
                    {"name": "Authorization", "value": f"Bearer {z_key}"},
                    {"name": "Content-Type",  "value": "application/json"}
                ]
            }
            if "body" in params:
                params["body"] = params["body"].replace("glm-4-flash", "glm-4")
            ok("  Authorization: Bearer [key set]")
            ok("  Content-Type:  application/json")
            ok("  Model:         glm-4")
            patched = True
            break

    if not patched:
        node_names = [n.get("name") for n in full_wf.get("nodes", [])]
        err(f"Seat6_SonSpirit_GLM not found in: {node_names}")
    print()

    # ── Save (PATCH for n8n 1.x, PUT fallback) ───────────────────────
    info("Saving workflow...")
    saved = client.save_workflow(wf_id, full_wf)
    if not any(k in saved for k in ("data", "id", "nodes", "name")):
        err(f"Unexpected save response: {str(saved)[:400]}")
    ok("Workflow saved\n")

    # ── Done ─────────────────────────────────────────────────────────
    print(f"{B}================================================={E}")
    print(f"{G}  Seat 6 (GLM/Z.ai) is wired!{E}")
    print()
    print(f"  → http://46.225.51.30")
    print(f"  → Workflows → Council of Seven Master Spirits v1")
    print(f"  → Execute Workflow")
    print(f"  → Check Seat6 output for GLM response")
    print()
    print(f"  To skip prompts next time:")
    print(f"  export N8N_EMAIL={email}")
    print(f"  export N8N_PASSWORD=<your-password>")
    print(f"  export Z_AI_KEY=<your-key>")
    print(f"{B}================================================={E}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n{R}✗ {e}{E}\n", file=sys.stderr)
        sys.exit(1)
