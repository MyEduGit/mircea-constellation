#!/usr/bin/env python3
"""
Wire Seat 6 (Z.ai / GLM) into the Council of Seven n8n workflow.
Auto-imports the workflow from GitHub if not already in n8n.

Run from iMac Terminal:
  curl -fsSL https://raw.githubusercontent.com/MyEduGit/mircea-constellation/claude/count-claws-NrqRh/setup/wire_seat6.py -o /tmp/wire_seat6.py && python3 /tmp/wire_seat6.py
"""
import json
import getpass
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
            body = e.read().decode()[:600]
            raise Exception(f"HTTP {e.code} on {method} {path}: {body}")

    def get(self, p):     return self._req("GET",  p)
    def post(self, p, b): return self._req("POST", p, b)
    def put(self, p, b):  return self._req("PUT",  p, b)


def find_workflows(client):
    result = client.get("/rest/workflows")
    ws = result.get("data", result)
    if isinstance(ws, dict):
        ws = list(ws.values())
    return ws if isinstance(ws, list) else []


def main():
    print(f"\n{B}=== WIRE SEAT 6 — Z.ai / GLM ==={E}")
    print("Auto-imports Council of Seven if missing, then wires the Z.ai key.\n")

    email    = input("n8n email:    ").strip()
    password = getpass.getpass("n8n password: ")
    z_key    = getpass.getpass("Z.ai API key: ")
    print()

    client = N8n()

    # ── Login ────────────────────────────────────────────────────────
    info("Logging into n8n...")
    result = client.post("/rest/login", {"emailOrLdapLoginId": email, "password": password})
    if not result.get("data"):
        err(f"Login failed — check email/password.\nResponse: {result}")
    ok("Logged in\n")

    # ── Find or import workflow ──────────────────────────────────────
    info("Finding Council of Seven workflow...")
    workflows = find_workflows(client)
    wf        = next((w for w in workflows if "Council" in w.get("name", "")), None)

    if wf:
        wf_id = wf["id"]
        ok(f'Found: "{wf["name"]}" (ID: {wf_id})\n')
        info("Fetching full workflow JSON...")
        result  = client.get(f"/rest/workflows/{wf_id}")
        full_wf = result.get("data", result)
        ok(f"Fetched ({len(full_wf.get('nodes', []))} nodes)\n")
    else:
        names = [w.get("name", "?") for w in workflows]
        warn(f"Council of Seven not found. Existing: {names}")
        info("Importing from GitHub...")
        with urllib.request.urlopen(WORKFLOW_URL) as r:
            wf_data = json.loads(r.read())
        result  = client.post("/rest/workflows", wf_data)
        full_wf = result.get("data", result)
        wf_id   = full_wf.get("id")
        if not wf_id:
            err(f"Import failed: {result}")
        ok(f"Workflow imported: \"{full_wf.get('name')}\" (ID: {wf_id})\n")

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
        err(f"Seat6_SonSpirit_GLM not found in nodes: {node_names}")
    print()

    # ── Save ─────────────────────────────────────────────────────────
    info("Saving workflow...")
    saved = client.put(f"/rest/workflows/{wf_id}", full_wf)
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
    print(f"  → Check Seat6_SonSpirit_GLM output for GLM response")
    print()
    print(f"  Next: Seat 4 (Ollama/Gemma — no key needed)")
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
