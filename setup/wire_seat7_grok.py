#!/usr/bin/env python3
"""
Wire Seat 7 (xAI / Grok) into the Council of Seven n8n workflow.
Replaces the local Mistral fallback with the live Grok API.

Credentials can be set as env vars to avoid re-prompting:
  export N8N_EMAIL=mircea8@me.com
  export N8N_PASSWORD=yourpassword
  export XAI_API_KEY=xai-...
  python3 setup/wire_seat7_grok.py

Or just run and enter them when prompted.

Options:
  --dry-run   Show what would change without writing anything
  --model M   Force a specific model (default: auto-detect best available)
"""
import json
import getpass
import os
import sys
import argparse
import re
import datetime
import urllib.request
import urllib.error
import http.cookiejar
from pathlib import Path

N8N_HOST      = "http://46.225.51.30"
XAI_ENDPOINT  = "https://api.x.ai/v1/chat/completions"
XAI_MODELS_EP = "https://api.x.ai/v1/models"

SCRIPT_DIR    = Path(__file__).resolve().parent
REPO_ROOT     = SCRIPT_DIR.parent
REGISTRY_PATH = REPO_ROOT / "council" / "COUNCIL_MODEL_REGISTRY.json"

# xAI pricing (USD per 1M tokens) — update as pricing changes
XAI_PRICING = {
    "grok-4":      {"input": 3.00,  "output": 15.00},
    "grok-3":      {"input": 3.00,  "output": 15.00},
    "grok-3-mini": {"input": 0.30,  "output": 0.50},
    "grok-2":      {"input": 2.00,  "output": 10.00},
}
DEFAULT_PRICING = {"input": 3.00, "output": 15.00}

B = "\033[1m"; G = "\033[32m"; C = "\033[36m"; R = "\033[31m"; Y = "\033[33m"; E = "\033[0m"
def ok(s):   print(f"{G}✓{E} {s}")
def info(s): print(f"{C}▶{E} {s}")
def warn(s): print(f"{Y}⚠{E}  {s}")
def err(s):  print(f"{R}✗{E} {s}", file=sys.stderr); sys.exit(1)


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_cred(env_var, prompt, secret=False):
    val = os.environ.get(env_var, "").strip()
    if val:
        label = "[from env, hidden]" if secret else "[from env]"
        print(f"{prompt}{label}")
        return val
    if secret:
        return getpass.getpass(prompt)
    return input(prompt).strip()


def _http_get_json(url, headers=None, timeout=10):
    req = urllib.request.Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def best_grok_model(xai_key):
    """Query xAI /v1/models and return the highest-ranked available model."""
    try:
        data = _http_get_json(XAI_MODELS_EP, headers={"Authorization": f"Bearer {xai_key}"})
        models = [m["id"] for m in data.get("data", [])]

        def rank(mid):
            m = mid.lower()
            if "grok-4"      in m and "mini" not in m: return 0
            if "grok-3"      in m and "mini" not in m: return 1
            if "grok-3-mini" in m:                     return 2
            if "grok-2"      in m:                     return 3
            return 9

        models.sort(key=rank)
        return models[0] if models else "grok-3", models
    except Exception as e:
        warn(f"Could not query xAI models API: {e}")
        warn("Defaulting to grok-3")
        return "grok-3", []


# ── n8n client ─────────────────────────────────────────────────────────────────

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
            with self.opener.open(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP {e.code} {method} {path}: {e.read().decode()[:500]}")

    def get(self, p):      return self._req("GET",   p)
    def post(self, p, b):  return self._req("POST",  p, b)
    def patch(self, p, b): return self._req("PATCH", p, b)
    def put(self, p, b):   return self._req("PUT",   p, b)

    def save_workflow(self, wf_id, wf):
        last_err = None
        for method in ("patch", "put"):
            try:
                return getattr(self, method)(f"/rest/workflows/{wf_id}", wf)
            except Exception as e:
                last_err = e
        raise last_err


def find_council_workflow(client):
    result = client.get("/rest/workflows")
    ws = result.get("data", result)
    if isinstance(ws, dict):
        ws = list(ws.values())
    if not isinstance(ws, list):
        return None, None
    wf = next(
        (w for w in ws
         if "Council" in w.get("name", "") and "copy" not in w.get("name", "").lower()),
        None
    )
    if not wf:
        return None, None
    wf_id   = wf["id"]
    full_wf = client.get(f"/rest/workflows/{wf_id}")
    return wf_id, full_wf.get("data", full_wf)


# ── Registry update ────────────────────────────────────────────────────────────

def update_registry(model, xai_key_var="XAI_API_KEY", dry_run=False):
    """Patch Seat 7 in COUNCIL_MODEL_REGISTRY.json to reflect the live xAI provider."""
    registry = json.loads(REGISTRY_PATH.read_text())
    seat7 = next((s for s in registry["seats"] if s["seat_id"] == 7), None)
    if not seat7:
        warn("Seat 7 not found in registry — skipping registry update")
        return

    pricing = DEFAULT_PRICING
    for prefix, p in XAI_PRICING.items():
        if model.startswith(prefix):
            pricing = p
            break

    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    changes = {
        "provider":            "xai",
        "current_model":       model,
        "api_model_id":        model,
        "api_endpoint":        XAI_ENDPOINT,
        "model_check_endpoint": XAI_MODELS_EP,
        "model_check_auth":    f"Authorization: Bearer {{{xai_key_var}}}",
        "key_env_var":         xai_key_var,
        "status":              "ACTIVE",
        "last_checked":        now,
        "cost_per_1m_tokens":  {
            "input":    pricing["input"],
            "output":   pricing["output"],
            "currency": "USD",
            "note":     model,
        },
        "note": (
            f"Wired to {model} (xAI live API). "
            "Mistral:7b available as local fallback via ollama_model field."
        ),
    }

    print(f"\n  {B}Registry changes for Seat 7:{E}")
    for k, v in changes.items():
        old = seat7.get(k)
        if old != v:
            print(f"    {C}{k}{E}: {Y}{old}{E}  →  {G}{v}{E}")
        seat7[k] = v

    if dry_run:
        warn("DRY RUN — registry not written")
        return

    registry["last_updated"] = now
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2))
    ok(f"Registry saved → {REGISTRY_PATH.name}")


# ── n8n node patch ─────────────────────────────────────────────────────────────

def build_seat7_body(model):
    """Return the corrected n8n expression body for Seat 7."""
    system_prompt = (
        "You are Trinity \\u2014 Live Context and Web member of the "
        "Council of Seven Master Spirits. Speak with real-time awareness "
        "and cosmic perspective."
    )
    return (
        "={{ JSON.stringify({ "
        f"model: '{model}', "
        "messages: [{ role: 'system', content: 'You are Trinity \u2014 Live Context and Web member of the Council of Seven Master Spirits. Speak with real-time awareness and cosmic perspective.' }, "
        "{ role: 'user', content: $('Set Question').item.json.question }], "
        "max_tokens: 300 }) }}"
    )


def patch_seat7_node(full_wf, xai_key, model, dry_run=False):
    """Find Seat7_Trinity_Grok and inject the real key + corrected model/body."""
    for node in full_wf.get("nodes", []):
        if node.get("name") != "Seat7_Trinity_Grok":
            continue

        params = node.setdefault("parameters", {})

        # ── Auth header ────────────────────────────────────────────────
        headers = params.setdefault("headerParameters", {}).setdefault("parameters", [])
        patched_auth = False
        for h in headers:
            if h.get("name") == "Authorization":
                old_val = h["value"]
                h["value"] = f"Bearer {xai_key}"
                if old_val != h["value"]:
                    ok(f"  Authorization: Bearer [key injected]  (was: {old_val[:30]}...)")
                else:
                    ok("  Authorization: already set")
                patched_auth = True
                break
        if not patched_auth:
            headers.append({"name": "Authorization", "value": f"Bearer {xai_key}"})
            ok("  Authorization: Bearer [key added]")

        # ── URL ────────────────────────────────────────────────────────
        if params.get("url") != XAI_ENDPOINT:
            ok(f"  URL: {params.get('url')}  →  {XAI_ENDPOINT}")
            params["url"] = XAI_ENDPOINT
        else:
            ok(f"  URL: {XAI_ENDPOINT} (already correct)")

        # ── Body (model + fix max_tokens syntax) ──────────────────────
        new_body = build_seat7_body(model)
        old_body = params.get("body", "")
        if old_body != new_body:
            old_model = re.search(r"model:\s*'([^']+)'", old_body)
            old_model = old_model.group(1) if old_model else "?"
            ok(f"  Body model: {old_model}  →  {model}")
            ok("  Body syntax: max_tokens fixed")
            params["body"] = new_body
        else:
            ok(f"  Body: {model} (already correct)")

        return True

    return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Wire Seat 7 — xAI / Grok")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show changes without writing anything")
    parser.add_argument("--model", default=None,
                        help="Force a specific model (e.g. grok-3, grok-4)")
    args = parser.parse_args()

    print(f"\n{B}=== WIRE SEAT 7 — xAI / Grok ==={E}")
    if args.dry_run:
        print(f"  {Y}DRY RUN — nothing will be written{E}")
    print("Set N8N_EMAIL / N8N_PASSWORD / XAI_API_KEY env vars to skip prompts.\n")

    email   = get_cred("N8N_EMAIL",    "n8n email:     ")
    pw      = get_cred("N8N_PASSWORD", "n8n password:  ", secret=True)
    xai_key = get_cred("XAI_API_KEY",  "xAI API key:   ", secret=True)
    print()

    # ── Discover best model ──────────────────────────────────────────────
    if args.model:
        model = args.model
        ok(f"Model (forced): {model}")
    else:
        info("Querying xAI models API...")
        model, available = best_grok_model(xai_key)
        ok(f"Best available model: {G}{model}{E}")
        if available:
            from textwrap import fill
            print(f"  Available: {', '.join(available)}")
    print()

    # ── n8n login ────────────────────────────────────────────────────────
    client = N8n()
    info("Logging into n8n...")
    result = client.post("/rest/login", {"emailOrLdapLoginId": email, "password": pw})
    if not result.get("data"):
        err(f"Login failed: {result}")
    ok("Logged in\n")

    # ── Fetch Council workflow ───────────────────────────────────────────
    info("Finding Council of Seven workflow...")
    wf_id, full_wf = find_council_workflow(client)
    if not wf_id:
        names = [w.get("name") for w in (client.get("/rest/workflows").get("data") or [])]
        err(f"Council workflow not found. Existing workflows: {names}")
    ok(f"Workflow ID: {wf_id}  ({len(full_wf.get('nodes', []))} nodes)\n")

    # ── Patch Seat 7 ─────────────────────────────────────────────────────
    info("Patching Seat7_Trinity_Grok...")
    patched = patch_seat7_node(full_wf, xai_key, model, dry_run=args.dry_run)
    if not patched:
        node_names = [n.get("name") for n in full_wf.get("nodes", [])]
        err(f"Seat7_Trinity_Grok not found in: {node_names}")
    print()

    # ── Update registry ──────────────────────────────────────────────────
    info("Updating COUNCIL_MODEL_REGISTRY.json...")
    update_registry(model, dry_run=args.dry_run)
    print()

    if args.dry_run:
        warn("DRY RUN complete — no changes written to n8n or registry")
        return

    # ── Save workflow ────────────────────────────────────────────────────
    info("Saving workflow to n8n...")
    saved = client.save_workflow(wf_id, full_wf)
    if not any(k in saved for k in ("data", "id", "nodes", "name")):
        err(f"Unexpected save response: {str(saved)[:400]}")
    ok("Workflow saved\n")

    # ── Done ─────────────────────────────────────────────────────────────
    print(f"{B}{'=' * 50}{E}")
    print(f"{G}  Seat 7 (Trinity / Grok) is live!{E}")
    print()
    print(f"  Model:    {G}{model}{E}")
    print(f"  Endpoint: {XAI_ENDPOINT}")
    print()
    print(f"  → http://46.225.51.30")
    print(f"  → Workflows → Council of Seven Master Spirits v1")
    print(f"  → Execute Workflow → check Seat 7 output")
    print()
    print(f"  To skip prompts next time:")
    print(f"    export N8N_EMAIL={email}")
    print(f"    export N8N_PASSWORD=<password>")
    print(f"    export XAI_API_KEY=<key>")
    print(f"{B}{'=' * 50}{E}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n{R}✗ {e}{E}\n", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
