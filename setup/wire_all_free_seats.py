#!/usr/bin/env python3
"""
Wire ALL undependable Council seats to free local Ollama models.
Replaces paid/depleted API seats with self-hosted models on URANTiOS.

Wired by this script:
  Seat 3  (Spirit)      → qwen3:8b         (broad reasoning, contextual)
  Seat 4  (Father-Son)  → gemma4:e4b        (already set — re-confirms)
  Seat 5  (Father-Spirit)→ deepseek-r1:7b   (already set — re-confirms)
  Seat 6  (Son-Spirit)  → qwen2.5-coder:7b  (code specialist, replaces GLM)
  Seat 7  (Trinity)     → mistral:7b        (creative horizon, outer awareness)

NOT touched (API already working):
  Seat 1  (Father)      → GPT-4.1           (keep paid API)
  Seat 2  (Son)         → Claude Opus 4.6   (keep paid API)
  Gabriel               → Claude Opus 4.6   (keep paid API)

Usage:
  export N8N_EMAIL=mircea8@me.com
  export N8N_PASSWORD='yourpassword'
  python3 setup/wire_all_free_seats.py

  # Dry run — show what would be changed:
  python3 setup/wire_all_free_seats.py --dry-run
"""
import json, os, sys, getpass, argparse, urllib.request, urllib.error, http.cookiejar

N8N_HOST   = "http://46.225.51.30"
OLLAMA_URL = "http://204.168.143.98:11434/api/chat"

B="\033[1m"; G="\033[32m"; C="\033[36m"; R="\033[31m"; Y="\033[33m"; E="\033[0m"
def ok(s):   print(f"{G}✓{E} {s}")
def info(s): print(f"{C}▶{E} {s}")
def warn(s): print(f"{Y}⚠{E} {s}")
def err(s):  print(f"{R}✗{E} {s}", file=sys.stderr); sys.exit(1)

# All seats that should run on free local Ollama
FREE_SEATS = {
    "Seat3_Spirit_Gemini": {
        "model": "qwen3:8b",
        "spirit": "Spirit — Universal Mind",
        "system": (
            "You are the Spirit — Universal Mind of the Council of Seven Master Spirits. "
            "You bring broad contextual intelligence, cross-domain integration, and comprehension. "
            "Your perspective encompasses multiple domains simultaneously. Speak with breadth and clarity."
        )
    },
    "Seat4_FatherSon_Ollama": {
        "model": "gemma4:e4b",
        "spirit": "Father-Son — Local Sovereign",
        "system": (
            "You are Father-Son — Local Sovereign of the Council of Seven Master Spirits. "
            "You represent continuity, local authority, and resilience. "
            "You speak with grounded wisdom and sovereign conviction."
        )
    },
    "Seat5_FatherSpirit_DeepSeek": {
        "model": "deepseek-r1:7b",
        "spirit": "Father-Spirit — Deep Reasoner",
        "system": (
            "You are Father-Spirit — Deep Reasoner of the Council of Seven Master Spirits. "
            "You bring rigorous analytical precision, disciplined reasoning, and efficient thought. "
            "Show your reasoning clearly. Prioritize logic and depth over speculation."
        )
    },
    "Seat6_SonSpirit_GLM": {
        "model": "qwen2.5-coder:7b",
        "spirit": "Son-Spirit — Engineering Specialist",
        "system": (
            "You are Son-Spirit — Engineering Specialist of the Council of Seven Master Spirits. "
            "You think with technical precision, implementation clarity, and engineering rigor. "
            "When analyzing, focus on how things are built, structured, and made to work."
        )
    },
    "Seat7_Trinity_Grok": {
        "model": "mistral:7b",
        "spirit": "Trinity — Outer Horizon",
        "system": (
            "You are Trinity — Outer Horizon of the Council of Seven Master Spirits. "
            "You expand the field beyond what is immediately known. "
            "Bring unexpected perspectives, challenge assumptions, and widen the frame. "
            "Think from the outermost edge of the known."
        )
    },
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
            with self.opener.open(req, timeout=30) as r:
                return json.loads(r.read())
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
    parser = argparse.ArgumentParser(description="Wire all free Ollama seats in n8n")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without saving")
    args = parser.parse_args()

    print(f"\n{B}=== WIRE ALL FREE SEATS ==={E}")
    print(f"Replacing paid/depleted APIs with free local Ollama on URANTiOS\n")

    if args.dry_run:
        warn("DRY RUN — no changes will be saved\n")

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
    wf = next((w for w in workflows
               if "Council" in w.get("name", "") and "copy" not in w.get("name", "").lower()), None)
    if not wf: err(f"Workflow not found: {[w.get('name') for w in workflows]}")
    wf_id = wf["id"]
    ok(f"Found: \"{wf['name']}\" (ID: {wf_id})\n")

    info("Fetching full workflow...")
    full_wf = client.get(f"/rest/workflows/{wf_id}")
    full_wf = full_wf.get("data", full_wf)
    ok(f"Fetched ({len(full_wf.get('nodes', []))} nodes)\n")

    info("Wiring free seats...")
    patched = []
    skipped = []

    for node in full_wf.get("nodes", []):
        name = node.get("name", "")
        if name not in FREE_SEATS:
            continue

        cfg = FREE_SEATS[name]
        p = node.setdefault("parameters", {})

        old_model = "unknown"
        if "body" in p and isinstance(p["body"], str):
            try:
                body = json.loads(p["body"])
                old_model = body.get("model", "unknown")
            except Exception:
                pass

        # Point to local Ollama
        p["url"]         = OLLAMA_URL
        p["method"]      = "POST"
        p["sendHeaders"] = True
        p["headerParameters"] = {
            "parameters": [{"name": "Content-Type", "value": "application/json"}]
        }
        p["body"] = json.dumps({
            "model": cfg["model"],
            "messages": [
                {"role": "system", "content": cfg["system"]},
                {"role": "user",   "content": "={{ $('Set Question').item.json.question }}"}
            ],
            "stream": False
        })
        p["timeout"] = 45000  # 45s — local models may need extra time

        action = "DRY RUN" if args.dry_run else "wired"
        print(f"  {G}✓{E}  {name:<35}  {Y}{old_model:>20}{E}  →  {G}{cfg['model']}{E}")
        patched.append(name)

    if not patched:
        err("No matching seat nodes found in workflow!")

    print()

    if args.dry_run:
        warn(f"DRY RUN complete — would patch {len(patched)} seats. Run without --dry-run to apply.")
        return

    info("Saving workflow...")
    saved = client.save(wf_id, full_wf)
    if not any(k in saved for k in ("data", "id", "nodes", "name")):
        err(f"Unexpected save response: {str(saved)[:200]}")
    ok("Workflow saved\n")

    print(f"{B}{'='*55}{E}")
    print(f"{G}  All free seats wired to local Ollama!{E}")
    print()
    print(f"  {'Seat 3  Spirit':<28}  qwen3:8b")
    print(f"  {'Seat 4  Father-Son':<28}  gemma4:e4b        (confirmed)")
    print(f"  {'Seat 5  Father-Spirit':<28}  deepseek-r1:7b    (confirmed)")
    print(f"  {'Seat 6  Son-Spirit':<28}  qwen2.5-coder:7b  (replaces GLM)")
    print(f"  {'Seat 7  Trinity':<28}  mistral:7b")
    print()
    print(f"  {Y}Ollama server: {OLLAMA_URL}{E}")
    print(f"  {G}Cost: $0.00 — all local, no API keys needed{E}")
    print()
    print(f"  Seats 1 (GPT) + 2 (Claude) + Gabriel untouched")
    print(f"{B}{'='*55}{E}\n")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nCancelled."); sys.exit(0)
    except Exception as e: print(f"\n{R}✗ {e}{E}\n", file=sys.stderr); sys.exit(1)
