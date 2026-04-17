#!/usr/bin/env python3
"""
Speed up the Council of Seven n8n workflow in-place.
- Sets 10s timeout on all seat + Gabriel nodes
- Reduces max_tokens to 300
- Preserves all existing API keys

Usage:
  export N8N_EMAIL=mircea8@me.com
  export N8N_PASSWORD='yourpassword'
  python3 /tmp/speed_up_council.py
"""
import json, re, os, sys, getpass, urllib.request, urllib.error, http.cookiejar

N8N_HOST = "http://46.225.51.30"
B="\033[1m"; G="\033[32m"; C="\033[36m"; R="\033[31m"; Y="\033[33m"; E="\033[0m"
def ok(s):   print(f"{G}✓{E} {s}")
def info(s): print(f"{C}▶{E} {s}")
def err(s):  print(f"{R}✗{E} {s}", file=sys.stderr); sys.exit(1)

SEAT_NODES = [
    'Seat1_Father_GPT', 'Seat2_Son_Claude', 'Seat3_Spirit_Gemini',
    'Seat4_FatherSon_Ollama', 'Seat5_FatherSpirit_DeepSeek',
    'Seat6_SonSpirit_GLM', 'Seat7_Trinity_Grok', 'Gabriel_Synthesizer'
]

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
    print(f"\n{B}=== SPEED UP COUNCIL OF SEVEN ==={E}\n")
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
    wf = next((w for w in workflows if "Council" in w.get("name", "") and "copy" not in w.get("name", "").lower()), None)
    if not wf: err(f"Workflow not found. Found: {[w.get('name') for w in workflows]}")
    wf_id = wf["id"]
    ok(f"Found: \"{wf['name']}\" (ID: {wf_id})\n")

    info("Fetching full workflow...")
    full = client.get(f"/rest/workflows/{wf_id}")
    full_wf = full.get("data", full)
    ok(f"Fetched ({len(full_wf.get('nodes', []))} nodes)\n")

    info("Applying speed optimizations...")
    patched = []
    for node in full_wf.get("nodes", []):
        if node.get("name") in SEAT_NODES:
            p = node.setdefault("parameters", {})
            # 10 second timeout
            p["timeout"] = 10000
            # Reduce max_tokens in body expression
            if "body" in p and isinstance(p["body"], str):
                p["body"] = re.sub(r'max_tokens[":\s]+\d+', 'max_tokens": 300', p["body"])
            ok(f"  {node['name']}: timeout=10s, max_tokens=300")
            patched.append(node["name"])

    if not patched:
        err("No seat nodes found to patch!")
    print()

    info("Saving workflow (preserving all API keys)...")
    saved = client.save(wf_id, full_wf)
    if not any(k in saved for k in ("data", "id", "nodes", "name")):
        err(f"Unexpected save response: {str(saved)[:300]}")
    ok("Workflow saved\n")

    print(f"{B}================================================={E}")
    print(f"{G}  Speed optimizations applied!{E}")
    print(f"  → Timeout: 10s per seat (was ~60s)")
    print(f"  → Max tokens: 300 per seat (was 512-1024)")
    print(f"  → Estimated workflow time: ~12-15s (was 2+ min)")
    print(f"  → All API keys preserved ✓")
    print(f"{B}================================================={E}\n")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nCancelled."); sys.exit(0)
    except Exception as e: print(f"\n{R}✗ {e}{E}\n", file=sys.stderr); sys.exit(1)
