#!/usr/bin/env python3
"""
Test the Council of Seven by triggering a real n8n workflow execution.
Unlike council_status.py (which pings APIs directly), this goes through
n8n — testing the full pipeline: fan-out → 7 seats → Gabriel synthesis.

Usage:
  export N8N_EMAIL=mircea8@me.com
  export N8N_PASSWORD='yourpassword'
  python3 setup/test_council_via_n8n.py

  # Custom question:
  python3 setup/test_council_via_n8n.py --question "What is the Paradise Trinity?"

  # Skip execution, just list recent runs:
  python3 setup/test_council_via_n8n.py --history
"""
import json, os, sys, time, getpass, argparse, urllib.request, urllib.error, http.cookiejar

N8N_HOST = "http://46.225.51.30"

B="\033[1m"; G="\033[32m"; C="\033[36m"; R="\033[31m"; Y="\033[33m"; E="\033[0m"
def ok(s):   print(f"{G}✓{E} {s}")
def info(s): print(f"{C}▶{E} {s}")
def warn(s): print(f"{Y}⚠{E} {s}")
def err(s):  print(f"{R}✗{E} {s}", file=sys.stderr)

DEFAULT_QUESTION = (
    "According to the Foreword of The Urantia Book, "
    "what is the nature of the Paradise Trinity and its relationship to the Seven Master Spirits?"
)

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

    def get(self, p):     return self._req("GET", p)
    def post(self, p, b): return self._req("POST", p, b)

def get_cred(env, prompt, secret=False):
    val = os.environ.get(env, "").strip()
    if val:
        print(f"{prompt}[from env]")
        return val
    return getpass.getpass(prompt) if secret else input(prompt).strip()

def find_council_workflow(client):
    ws = client.get("/rest/workflows")
    workflows = ws.get("data", ws)
    if isinstance(workflows, dict): workflows = list(workflows.values())
    wf = next((w for w in workflows
               if "Council" in w.get("name", "") and "copy" not in w.get("name", "").lower()), None)
    if not wf:
        raise Exception(f"Council workflow not found. Found: {[w.get('name') for w in workflows]}")
    return wf

def show_history(client, wf_id, limit=5):
    print(f"\n{B}=== Recent Council Executions ==={E}\n")
    try:
        execs = client.get(f"/rest/executions?workflowId={wf_id}&limit={limit}")
        runs = execs.get("data", {})
        if isinstance(runs, dict): runs = runs.get("data", [])
        if not runs:
            warn("No executions found yet.")
            return
        for run in runs:
            status = run.get("status", "unknown")
            started = run.get("startedAt", "?")[:19].replace("T", " ")
            finished = run.get("stoppedAt", "?")[:19].replace("T", " ")
            run_id = run.get("id", "?")
            color = G if status == "success" else R
            print(f"  {color}{status:10}{E}  {started}  →  {finished}  (id: {run_id})")
    except Exception as e:
        warn(f"Could not fetch history: {e}")

def trigger_webhook(client, wf_id, question):
    """Try to trigger workflow via webhook or manual execute."""
    # First, check if there's a webhook trigger
    full_wf = client.get(f"/rest/workflows/{wf_id}")
    full_wf = full_wf.get("data", full_wf)
    nodes = full_wf.get("nodes", [])

    # Look for webhook node
    webhook_node = next((n for n in nodes if n.get("type") == "n8n-nodes-base.webhook"), None)
    if webhook_node:
        webhook_path = webhook_node.get("parameters", {}).get("path", "")
        if webhook_path:
            url = f"{N8N_HOST}/webhook/{webhook_path}"
            info(f"Triggering via webhook: {url}")
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps({"question": question}).encode(),
                    method="POST"
                )
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.loads(r.read())
            except Exception as e:
                warn(f"Webhook trigger failed: {e}")

    # Fall back to manual execute
    info("Triggering via manual execution API...")
    try:
        result = client.post(f"/rest/workflows/{wf_id}/execute", {"data": {"question": question}})
        return result
    except Exception as e:
        warn(f"Manual execute failed: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Test Council of Seven via n8n")
    parser.add_argument("--question", "-q", default=DEFAULT_QUESTION, help="Question to ask the Council")
    parser.add_argument("--history", action="store_true", help="Show recent execution history only")
    args = parser.parse_args()

    print(f"\n{B}=== COUNCIL OF SEVEN — n8n Test ==={E}")
    print(f"{C}Tests the FULL pipeline via n8n (not direct API){E}\n")

    email    = get_cred("N8N_EMAIL",    "n8n email:    ")
    password = get_cred("N8N_PASSWORD", "n8n password: ", secret=True)
    print()

    client = N8n()

    info("Logging in to n8n...")
    r = client.post("/rest/login", {"emailOrLdapLoginId": email, "password": password})
    if not r.get("data"):
        err(f"Login failed: {r}")
        sys.exit(1)
    ok("Logged in\n")

    info("Finding Council workflow...")
    wf = find_council_workflow(client)
    wf_id = wf["id"]
    ok(f"Found: \"{wf['name']}\" (ID: {wf_id})\n")

    if args.history:
        show_history(client, wf_id)
        return

    # Show recent history first
    show_history(client, wf_id, limit=3)
    print()

    print(f"{B}Question:{E}")
    print(f"  {Y}{args.question}{E}\n")

    info("Triggering workflow execution...")
    print(f"{Y}  This may take 15-60 seconds (7 AI seats + Gabriel synthesis){E}\n")

    t0 = time.time()
    result = trigger_webhook(client, wf_id, args.question)
    elapsed = time.time() - t0

    if result:
        ok(f"Execution triggered ({elapsed:.1f}s)\n")
        print(f"{B}=== RESULT ==={E}\n")

        # Try to extract Gabriel's synthesis
        if isinstance(result, dict):
            # Look for Gabriel output in various places
            gabriel_output = (
                result.get("gabriel") or
                result.get("synthesis") or
                result.get("output") or
                result.get("response") or
                str(result)[:1000]
            )
            print(gabriel_output)
    else:
        warn(f"Could not get direct result after {elapsed:.1f}s")
        print()
        info("Check n8n UI for execution result:")
        print(f"  → {N8N_HOST}")
        print(f"  → Open 'Council of Seven Master Spirits v1'")
        print(f"  → Click 'Executions' tab to see latest run")

    print()
    show_history(client, wf_id, limit=3)
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n{R}✗ {e}{E}\n", file=sys.stderr)
        sys.exit(1)
