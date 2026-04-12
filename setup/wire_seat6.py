#!/usr/bin/env python3
"""
Wire Seat 6 (Z.ai / GLM) into the Council of Seven n8n workflow.
Uses n8n REST API — no UI clicking required.

Run from iMac Terminal:
  curl -fsSL https://raw.githubusercontent.com/MyEduGit/mircea-constellation/claude/count-claws-NrqRh/setup/wire_seat6.py | python3
"""
import json
import getpass
import sys
import urllib.request
import urllib.error
import http.cookiejar

N8N_HOST = "http://46.225.51.30"

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

    def get(self, p):       return self._req("GET",  p)
    def post(self, p, b):   return self._req("POST", p, b)
    def put(self, p, b):    return self._req("PUT",  p, b)


def find_workflows(client):
    result = client.get("/rest/workflows")
    # n8n returns {"data": [...]} or just [...]
    ws = result.get("data", result)
    if isinstance(ws, dict):
        ws = list(ws.values())
    return ws if isinstance(ws, list) else []


def main():
    print(f"\n{B}=== WIRE SEAT 6 — Z.ai / GLM ==={E}")
    print("Configures the Authorization header in n8n via REST API.\n")

    email    = input("n8n email:    ").strip()
    password = getpass.getpass("n8n password: ")
    z_key    = getpass.getpass("Z.ai API key: ")
    print()

    client = N8n()

    # ── Login ───────────────────────────────────────────────────────
    info("Logging into n8n...")
    result = client.post("/rest/login", {"emailOrLdapLoginId": email, "password": password})
    if not result.get("data"):
        err(f"Login failed — check email/password. Response: {result}")
    ok("Logged in\n")

    # ── Find workflow ────────────────────────────────────────────────
    info("Finding Council of Seven workflow...")
    workflows = find_workflows(client)
    wf = next((w for w in workflows if "Council" in w.get("name", "")), None)

    if not wf:
        names = [w.get("name", "?") for w in workflows]
        err(f"Council of Seven not found. Workflows in n8n: {names}\n"
            "Run claws_boot.sh first to import it.")

    wf_id = wf["id"]
    ok(f'Found: "{wf["name"]}" (ID: {wf_id})\n')

    # ── Fetch full workflow ──────────────────────────────────────────
    info("Fetching full workflow JSON...")
    result = client.get(f"/rest/workflows/{wf_id}")
    full_wf = result.get("data", result)
    ok(f"Fetched ({len(full_wf.get('nodes', []))} nodes)\n")

    # ── Patch Seat 6 ─────────────────────────────────────────────────
    info("Patching Seat6_SonSpirit_GLM...")
    patched = False
    for node in full_wf.get("nodes", []):
        if node.get("name") == "Seat6_SonSpirit_GLM":
            # Fix Authorization header — this is the key fix
            params = node.setdefault("parameters", {})
            params["sendHeaders"] = True
            params["headerParameters"] = {
                "parameters": [
                    {"name": "Authorization", "value": f"Bearer {z_key}"},
                    {"name": "Content-Type",  "value": "application/json"}
                ]
            }
            # Fix model: glm-4 (as specified by Z.ai / GLM)
            # Keep n8n expression body; just fix the model name inside it
            if "body" in params:
                params["body"] = params["body"].replace("glm-4-flash", "glm-4").replace("glm-4.5", "glm-4")
            ok("  Authorization: Bearer [key set]")
            ok("  Content-Type: application/json")
            ok("  Model: glm-4")
            patched = True
            break

    if not patched:
        node_names = [n.get("name") for n in full_wf.get("nodes", [])]
        err(f"Seat6_SonSpirit_GLM not found in workflow nodes: {node_names}")

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
    print("  In your browser at http://46.225.51.30:")
    print("  1. Open Workflows → Council of Seven Master Spirits v1")
    print("  2. Click Execute Workflow (top right)")
    print("  3. Check Seat6_SonSpirit_GLM output")
    print(f"  4. Expect: response with {Y}choices[0].message.content{E}")
    print()
    print("  If Seat 6 responds → you have a live Council seat!")
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
