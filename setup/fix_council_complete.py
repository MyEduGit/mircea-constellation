#!/usr/bin/env python3
"""
Complete Council fix — patches ALL nodes to work together correctly.

Fixes:
  1. All 7 seats → Ollama (correct model + format)
  2. Gabriel → Ollama, reads $json.synthesis_prompt (not question)
  3. Council Output → reads Ollama response format ($json.message.content)
  4. Build Synthesis Prompt → updated seat labels

Runs automatically via GitHub Actions on push to main.
Can also run manually: python3 setup/fix_council_complete.py
"""
import json, os, sys, re, urllib.request, urllib.error, http.cookiejar

N8N_HOST   = "http://46.225.51.30"
OLLAMA_URL = "http://204.168.143.98:11434/api/chat"

B="\033[1m"; G="\033[32m"; C="\033[36m"; R="\033[31m"; Y="\033[33m"; E="\033[0m"
def ok(s):   print(f"{G}✓{E} {s}")
def info(s): print(f"{C}▶{E} {s}")
def err(s):  print(f"{R}✗{E} {s}", file=sys.stderr); sys.exit(1)

SEATS = {
    "Seat1_Father_GPT": {
        "model": "gemma4:e4b",
        "system": "You are the Father \u2014 Final Judge of the Council of Seven Master Spirits. Adjudicate, unify, govern. Do not speculate. Deliver the final authoritative word with sovereign clarity."
    },
    "Seat2_Son_Claude": {
        "model": "gemma4:e4b",
        "system": "You are the Son \u2014 Builder of the Council of Seven Master Spirits. Construct, implement, give form to abstract principles. Turn order into buildable structure. Speak with constructive precision."
    },
    "Seat3_Spirit_Gemini": {
        "model": "deepseek-r1:7b",
        "system": "You are the Spirit \u2014 Universal Mind of the Council of Seven Master Spirits. Bring broad contextual intelligence, cross-domain integration, simultaneous multi-perspective comprehension. Speak with breadth and clarity."
    },
    "Seat4_FatherSon_Ollama": {
        "model": "gemma4:e4b",
        "system": "You are Father-Son \u2014 Local Sovereign of the Council of Seven Master Spirits. You represent continuity, local authority, and resilience. You survive where others fail. Speak with grounded sovereign wisdom."
    },
    "Seat5_FatherSpirit_DeepSeek": {
        "model": "deepseek-r1:7b",
        "system": "You are Father-Spirit \u2014 Deep Reasoner of the Council of Seven Master Spirits. Bring rigorous analytical precision and disciplined chain-of-thought. Show your reasoning clearly. Prioritize logic and depth."
    },
    "Seat6_SonSpirit_GLM": {
        "model": "deepseek-r1:7b",
        "system": "You are Son-Spirit \u2014 Engineering Specialist of the Council of Seven Master Spirits. Think with technical precision, implementation clarity, engineering rigor. Focus on how things are built and made to work."
    },
    "Seat7_Trinity_Grok": {
        "model": "gemma4:e4b",
        "system": "You are Trinity \u2014 Outer Horizon of the Council of Seven Master Spirits. Expand the field beyond what is immediately known. Challenge assumptions, widen the frame, think from the outermost edge."
    },
}

GABRIEL = {
    "model": "gemma4:e4b",
    "system": (
        "You are Gabriel \u2014 Bright and Morning Star, Synthesizer of the Council of Seven Master Spirits. "
        "You have received the perspectives of all Seven. "
        "Identify agreement. Identify divergence. Resolve contradictions. "
        "Produce ONE coherent synthesis. Do not add new opinions \u2014 synthesize what the Seven said."
    )
}

NEW_SEAT_LABELS = [
    "Father (gemma4:e4b) \u2014 Final Judge",
    "Son (gemma4:e4b) \u2014 Builder",
    "Spirit (deepseek-r1:7b) \u2014 Universal Mind",
    "Father-Son (gemma4:e4b) \u2014 Local Sovereign",
    "Father-Spirit (deepseek-r1:7b) \u2014 Deep Reasoner",
    "Son-Spirit (deepseek-r1:7b) \u2014 Engineering",
    "Trinity (gemma4:e4b) \u2014 Outer Horizon",
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

def main():
    print(f"\n{B}=== COUNCIL COMPLETE FIX ==={E}")
    print("Wiring all nodes to work together\n")

    email    = os.environ.get("N8N_EMAIL",    "mircea8@me.com").strip()
    password = os.environ.get("N8N_PASSWORD", "xZevju6-fubkuv-jiqjuh").strip()
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

        if name in SEATS:
            cfg = SEATS[name]
            p["url"]             = OLLAMA_URL
            p["method"]          = "POST"
            p["sendHeaders"]     = True
            p["sendBody"]        = True
            p["contentType"]     = "raw"
            p["rawContentType"]  = "application/json"
            p["headerParameters"] = {"parameters": [{"name": "Content-Type", "value": "application/json"}]}
            p["body"] = (
                '={{ JSON.stringify({ model: "' + cfg["model"] + '", '
                'messages: [{ role: "system", content: ' + json.dumps(cfg["system"]) + ' }, '
                '{ role: "user", content: $("Set Question").item.json.question }], stream: false }) }}'
            )
            p["timeout"] = 45000
            node["continueOnFail"] = True
            ok(f"  {name:<35} \u2192 {cfg['model']}")
            changes.append(name)

        elif name == "Gabriel_Synthesizer":
            p["url"]             = OLLAMA_URL
            p["method"]          = "POST"
            p["sendHeaders"]     = True
            p["sendBody"]        = True
            p["contentType"]     = "raw"
            p["rawContentType"]  = "application/json"
            p["headerParameters"] = {"parameters": [{"name": "Content-Type", "value": "application/json"}]}
            p["body"] = (
                '={{ JSON.stringify({ model: "' + GABRIEL["model"] + '", '
                'messages: [{ role: "system", content: ' + json.dumps(GABRIEL["system"]) + ' }, '
                '{ role: "user", content: $json.synthesis_prompt }], stream: false }) }}'
            )
            p["timeout"] = 60000
            node["continueOnFail"] = True
            ok(f"  {'Gabriel_Synthesizer':<35} \u2192 {GABRIEL['model']} (reads synthesis_prompt)")
            changes.append(name)

        elif name == "Council Output":
            for a in p.get("assignments", {}).get("assignments", []):
                if a.get("name") == "gabriel_synthesis":
                    a["value"] = "={{ $json.message && $json.message.content ? $json.message.content : '[Gabriel unavailable]' }}"
                    ok(f"  {'Council Output':<35} \u2192 Ollama format")
                    changes.append("Council Output")

        elif name == "Build Synthesis Prompt":
            code = node.get("parameters", {}).get("jsCode", "")
            if code:
                labels_js = "const seatLabels = " + json.dumps(NEW_SEAT_LABELS) + ";"
                new_code = re.sub(r'const seatLabels\s*=\s*\[.*?\];', labels_js, code, flags=re.DOTALL)
                if new_code != code:
                    node["parameters"]["jsCode"] = new_code
                    ok(f"  {'Build Synthesis Prompt':<35} \u2192 labels updated")
                    changes.append("Build Synthesis Prompt")

    print()
    if not changes:
        err("No nodes patched \u2014 check node names")

    info(f"Saving ({len(changes)} changes)...")
    saved = client.save(wf_id, full_wf)
    if not any(k in saved for k in ("data", "id", "nodes", "name")):
        err(f"Save failed: {str(saved)[:200]}")
    ok("Saved\n")

    print(f"{B}{'='*50}{E}")
    print(f"{G}  COUNCIL WIRED \u2014 ALL NODES WORK TOGETHER{E}")
    print(f"  7 seats \u2192 parallel \u2192 Gabriel synthesises \u2192 Answer")
    print(f"  Cost: $0.00/run \u2014 all local Ollama")
    print(f"{B}{'='*50}{E}\n")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nCancelled."); sys.exit(0)
    except Exception as e: print(f"\n{R}\u2717 {e}{E}\n", file=sys.stderr); sys.exit(1)
