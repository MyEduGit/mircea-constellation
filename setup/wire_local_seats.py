#!/usr/bin/env python3
"""
Wire Seat 4 (gemma4:e4b) and Seat 5 (deepseek-r1:7b) using local Ollama on URANTiOS.
Both models already installed — no API keys needed.

Usage:
  export N8N_EMAIL=mircea8@me.com
  export N8N_PASSWORD='yourpassword'
  python3 /tmp/wire_local_seats.py
"""
import json, re, os, sys, getpass, urllib.request, urllib.error, http.cookiejar

N8N_HOST   = "http://46.225.51.30"
OLLAMA_URL = "http://204.168.143.98:11434/api/chat"

B="\033[1m"; G="\033[32m"; C="\033[36m"; R="\033[31m"; E="\033[0m"
def ok(s):   print(f"{G}✓{E} {s}")
def info(s): print(f"{C}▶{E} {s}")
def err(s):  print(f"{R}✗{E} {s}", file=sys.stderr); sys.exit(1)

LOCAL_SEATS = {
    "Seat4_FatherSon_Ollama": {
        "model": "gemma4:e4b",
        "spirit": "Father-Son — Local Sovereign",
        "system": "You are Father-Son — Local Sovereign of the Council of Seven Master Spirits. Speak with authority and constructive wisdom."
    },
    "Seat5_FatherSpirit_DeepSeek": {
        "model": "deepseek-r1:7b",
        "spirit": "Father-Spirit — Deep Reasoner",
        "system": "You are Father-Spirit — Deep Reasoner of the Council of Seven Master Spirits. Speak with rigorous analytical precision."
    }
}

class N8n:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))

    def _req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(N8N_HOST + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        try:
            with self.opener.open(req) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP {e.code} {method} {path}: {e.read().decode()[:300]}")

    def get(self, p):      return self._req("GET", p)
    def post(self, p, b):  return self._req("POST", p, b)
    def patch(self, p, b): return self._req("PATCH", p, b)
    def put(self, p, b):   return self._req("PUT", p, b)

    def save(self, wf_id, wf):
        for m in ("patch", "put"):
            try: return getattr(self, m)(f"/rest/workflows/{wf_id}", wf)
            except Exception as e: last = e
        raise last

def get_cred(env, prompt, secret=False):
    val = os.environ.get(env, "").strip()
    if val:
        print(f"{prompt}[from env]")
        return val
    return getpass.getpass(prompt) if secret else input(prompt).strip()

def main():
    print(f"\n{B}=== WIRE LOCAL SEATS (Seat 4 + Seat 5) ==={E}")
    print("gemma4:e4b + deepseek-r1:7b — free, local, no API keys\n")

    email    = get_cred("N8N_EMAIL",    "n8n email:    ")
    password = get_cred("N8N_PASSWORD", "n8n password: ", secret=True)
    print()

    client = N8n()

    info("Logging in...")
    r = client.post("/rest/login", {"emailOrLdapLoginId": email, "password": password})
    if not r.get("data"): err(f"Login failed: {r}")
    ok("Logged in\n")

    info("Finding Council workflow...")
    ws = client.get("/rest/workflows")
    workflows = ws.get("data", ws)
    if isinstance(workflows, dict): workflows = list(workflows.values())
    wf = next((w for w in workflows if "Council" in w.get("name","") and "copy" not in w.get("name","").lower()), None)
    if not wf: err(f"Not found: {[w.get('name') for w in workflows]}")
    wf_id = wf["id"]
    ok(f"Found: \"{wf['name']}\" (ID: {wf_id})\n")

    info("Fetching full workflow...")
    full_wf = client.get(f"/rest/workflows/{wf_id}")
    full_wf = full_wf.get("data", full_wf)
    ok(f"Fetched ({len(full_wf.get('nodes', []))} nodes)\n")

    info("Wiring local seats...")
    patched = []
    for node in full_wf.get("nodes", []):
        name = node.get("name", "")
        if name in LOCAL_SEATS:
            cfg = LOCAL_SEATS[name]
            p = node.setdefault("parameters", {})

            # Point to local Ollama
            p["url"] = OLLAMA_URL
            p["method"] = "POST"
            p["sendHeaders"] = True
            p["headerParameters"] = {
                "parameters": [
                    {"name": "Content-Type", "value": "application/json"}
                ]
            }
            # Ollama chat API body
            p["body"] = json.dumps({
                "model": cfg["model"],
                "messages": [
                    {"role": "system", "content": cfg["system"]},
                    {"role": "user",   "content": "={{ $('Set Question').item.json.question }}"}
                ],
                "stream": False
            })
            p["timeout"] = 30000  # 30s for local model (slightly slower than API)

            ok(f"  {name}: {cfg['model']} @ {OLLAMA_URL}")
            patched.append(name)

    if not patched:
        err("No local seat nodes found!")
    print()

    info("Saving workflow...")
    saved = client.save(wf_id, full_wf)
    if not any(k in saved for k in ("data","id","nodes","name")):
        err(f"Unexpected response: {str(saved)[:200]}")
    ok("Saved\n")

    print(f"{B}================================================={E}")
    print(f"{G}  Seats 4 + 5 wired to local Ollama!{E}")
    print()
    print(f"  Seat 4 — Father-Son:      gemma4:e4b")
    print(f"  Seat 5 — Father-Spirit:   deepseek-r1:7b")
    print(f"  Server: {OLLAMA_URL}")
    print(f"  Cost: FREE (local models)")
    print(f"{B}================================================={E}\n")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nCancelled."); sys.exit(0)
    except Exception as e: print(f"\n{R}✗ {e}{E}\n", file=sys.stderr); sys.exit(1)
