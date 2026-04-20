#!/usr/bin/env python3
"""
Complete Council fix — patches ALL nodes to work together correctly.

Fixes:
  1. All 7 seats → Ollama (correct model + format)
  2. Gabriel → Ollama, reads $json.synthesis_prompt (not question)
  3. Council Output → reads Ollama response format ($json.message.content)
  4. Build Synthesis Prompt → updated seat labels

Usage:
  export N8N_EMAIL=mircea8@me.com
  export N8N_PASSWORD='yourpassword'
  python3 setup/fix_council_complete.py
"""
import json, os, sys, getpass, urllib.request, urllib.error, http.cookiejar

N8N_HOST   = "http://46.225.51.30"
OLLAMA_URL = "http://204.168.143.98:11434/api/chat"

B="\033[1m"; G="\033[32m"; C="\033[36m"; R="\033[31m"; Y="\033[33m"; E="\033[0m"
def ok(s):   print(f"{G}✓{E} {s}")
def info(s): print(f"{C}▶{E} {s}")
def err(s):  print(f"{R}✗{E} {s}", file=sys.stderr); sys.exit(1)

# ── Seat configurations (Ollama, free, local) ───────────────────────────────
SEATS = {
    # gemma4:e4b and deepseek-r1:7b are CONFIRMED on URANTiOS.
    # Other models (qwen3, mistral, qwen2.5-coder) wired here once pulled.
    "Seat1_Father_GPT": {
        "model": "gemma4:e4b",
        "system": "You are the Father — Final Judge of the Council of Seven Master Spirits. Adjudicate, unify, govern. Do not speculate. Deliver the final authoritative word with sovereign clarity."
    },
    "Seat2_Son_Claude": {
        "model": "gemma4:e4b",
        "system": "You are the Son — Builder of the Council of Seven Master Spirits. Construct, implement, give form to abstract principles. Turn order into buildable structure. Speak with constructive precision."
    },
    "Seat3_Spirit_Gemini": {
        "model": "deepseek-r1:7b",
        "system": "You are the Spirit — Universal Mind of the Council of Seven Master Spirits. Bring broad contextual intelligence, cross-domain integration, simultaneous multi-perspective comprehension. Speak with breadth and clarity."
    },
    "Seat4_FatherSon_Ollama": {
        "model": "gemma4:e4b",
        "system": "You are Father-Son — Local Sovereign of the Council of Seven Master Spirits. You represent continuity, local authority, and resilience. You survive where others fail. Speak with grounded sovereign wisdom."
    },
    "Seat5_FatherSpirit_DeepSeek": {
        "model": "deepseek-r1:7b",
        "system": "You are Father-Spirit — Deep Reasoner of the Council of Seven Master Spirits. Bring rigorous analytical precision and disciplined chain-of-thought. Show your reasoning clearly. Prioritize logic and depth."
    },
    "Seat6_SonSpirit_GLM": {
        "model": "deepseek-r1:7b",
        "system": "You are Son-Spirit — Engineering Specialist of the Council of Seven Master Spirits. Think with technical precision, implementation clarity, engineering rigor. Focus on how things are built and made to work."
    },
    "Seat7_Trinity_Grok": {
        "model": "gemma4:e4b",
        "system": "You are Trinity — Outer Horizon of the Council of Seven Master Spirits. Expand the field beyond what is immediately known. Challenge assumptions, widen the frame, think from the outermost edge."
    },
}

# Gabriel is special — reads synthesis_prompt, not the original question
GABRIEL = {
    "model": "gemma4:e4b",  # confirmed installed
    "system": (
        "You are Gabriel — Bright and Morning Star, Synthesizer of the Council of Seven Master Spirits. "
        "You have received the perspectives of all Seven. "
        "Identify agreement. Identify divergence. Resolve contradictions. "
        "Produce ONE coherent synthesis. Do not add new opinions — synthesize what the Seven said."
    )
}

# Updated seat labels for Build Synthesis Prompt
NEW_SEAT_LABELS = [
    "Father (gemma4:e4b) — Final Judge",
    "Son (gemma4:e4b) — Builder",
    "Spirit (deepseek-r1:7b) — Universal Mind",
    "Father-Son (gemma4:e4b) — Local Sovereign",
    "Father-Spirit (deepseek-r1:7b) — Deep Reasoner",
    "Son-Spirit (deepseek-r1:7b) — Engineering",
    "Trinity (gemma4:e4b) — Outer Horizon",
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

def ollama_body(model, system, user_expr):
    """Build Ollama request body as n8n expression string."""
    return json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_expr}
        ],
        "stream": False
    })

def main():
    print(f"\n{B}=== COUNCIL COMPLETE FIX ==={E}")
    print("Fixes ALL nodes to work together correctly\n")

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
    if not wf: err(f"Not found: {[w.get('name') for w in workflows]}")
    wf_id = wf["id"]
    ok(f"Found: \"{wf['name']}\" (ID: {wf_id})\n")

    info("Fetching workflow...")
    full_wf = client.get(f"/rest/workflows/{wf_id}")
    full_wf = full_wf.get("data", full_wf)
    ok(f"Fetched ({len(full_wf.get('nodes', []))} nodes)\n")

    info("Patching nodes...")
    changes = []

    for node in full_wf.get("nodes", []):
        name = node.get("name", "")
        p = node.setdefault("parameters", {})

        # ── 7 seat nodes → Ollama ──────────────────────────────────────────
        if name in SEATS:
            cfg = SEATS[name]
            p["url"]         = OLLAMA_URL
            p["method"]      = "POST"
            p["sendHeaders"] = True
            p["sendBody"]    = True
            p["contentType"] = "raw"
            p["rawContentType"] = "application/json"
            p["headerParameters"] = {
                "parameters": [{"name": "Content-Type", "value": "application/json"}]
            }
            # user content is a live n8n expression — wrap correctly
            p["body"] = (
                '={{ JSON.stringify({ model: "' + cfg["model"] + '", '
                'messages: [{ role: "system", content: ' + json.dumps(cfg["system"]) + ' }, '
                '{ role: "user", content: $("Set Question").item.json.question }], stream: false }) }}'
            )
            p["timeout"] = 45000
            node["continueOnFail"] = True
            ok(f"  {name:<35} → {cfg['model']}")
            changes.append(name)

        # ── Gabriel → Ollama, reads synthesis_prompt ───────────────────────
        elif name == "Gabriel_Synthesizer":
            p["url"]         = OLLAMA_URL
            p["method"]      = "POST"
            p["sendHeaders"] = True
            p["sendBody"]    = True
            p["contentType"] = "raw"
            p["rawContentType"] = "application/json"
            p["headerParameters"] = {
                "parameters": [{"name": "Content-Type", "value": "application/json"}]
            }
            p["body"] = (
                '={{ JSON.stringify({ model: "' + GABRIEL["model"] + '", '
                'messages: [{ role: "system", content: ' + json.dumps(GABRIEL["system"]) + ' }, '
                '{ role: "user", content: $json.synthesis_prompt }], stream: false }) }}'
            )
            p["timeout"] = 60000
            node["continueOnFail"] = True
            ok(f"  {'Gabriel_Synthesizer':<35} → {GABRIEL['model']} (reads synthesis_prompt)")
            changes.append(name)

        # ── Council Output → read Ollama response format ───────────────────
        elif name == "Council Output":
            assignments = p.get("assignments", {}).get("assignments", [])
            for a in assignments:
                if a.get("name") == "gabriel_synthesis":
                    a["value"] = "={{ $json.message && $json.message.content ? $json.message.content : '[Gabriel unavailable — check Ollama]' }}"
                    ok(f"  {'Council Output':<35} → gabriel_synthesis reads Ollama format")
                    changes.append("Council Output (gabriel_synthesis)")

        # ── Build Synthesis Prompt → update seat labels ────────────────────
        elif name == "Build Synthesis Prompt":
            code = node.get("parameters", {}).get("jsCode", "")
            if code:
                # Replace the seatLabels array
                labels_js = "const seatLabels = " + json.dumps(NEW_SEAT_LABELS) + ";"
                import re
                new_code = re.sub(
                    r'const seatLabels\s*=\s*\[.*?\];',
                    labels_js,
                    code,
                    flags=re.DOTALL
                )
                if new_code != code:
                    node["parameters"]["jsCode"] = new_code
                    ok(f"  {'Build Synthesis Prompt':<35} → seat labels updated")
                    changes.append("Build Synthesis Prompt (labels)")
                else:
                    ok(f"  {'Build Synthesis Prompt':<35} → labels already current")

    print()
    if not changes:
        err("No nodes were patched — check node names match")

    info(f"Saving workflow ({len(changes)} changes)...")
    saved = client.save(wf_id, full_wf)
    if not any(k in saved for k in ("data", "id", "nodes", "name")):
        err(f"Unexpected save response: {str(saved)[:200]}")
    ok("Saved\n")

    print(f"{B}{'='*56}{E}")
    print(f"{G}  COUNCIL FIXED — ALL NODES WORK TOGETHER{E}")
    print()
    print(f"  Flow: Question → 7 seats (parallel) → Merge")
    print(f"        → Build Synthesis Prompt → Gabriel → Output")
    print()
    print(f"  All 8 seats: local Ollama on URANTiOS")
    print(f"  Cost: $0.00/run")
    print()
    print(f"  {Y}Open n8n → Council of Seven → click ▶ Execute{E}")
    print(f"{B}{'='*56}{E}\n")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nCancelled."); sys.exit(0)
    except Exception as e: print(f"\n{R}✗ {e}{E}\n", file=sys.stderr); sys.exit(1)
