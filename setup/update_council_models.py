#!/usr/bin/env python3
"""
update_council_models.py — Council of Seven auto-model updater.

Reads COUNCIL_MODEL_REGISTRY.json, queries each provider's models endpoint
to find the latest/best available model, compares against current assignments,
and updates both the registry JSON and the live n8n workflow via REST API.

Credentials are read from ~/.council-keys/.env (or env vars directly).

Usage:
  python3 setup/update_council_models.py [--dry-run] [--seat N]

Options:
  --dry-run   Report what would change, but do not write anything
  --seat N    Check only seat N (1-7) or 'gabriel'
"""

import json
import os
import sys
import re
import urllib.request
import urllib.error
import http.cookiejar
import subprocess
import datetime
import argparse
from pathlib import Path

# ── Colour codes ─────────────────────────────────────────────────────────────
B  = "\033[1m"
G  = "\033[32m"
C  = "\033[36m"
R  = "\033[31m"
Y  = "\033[33m"
M  = "\033[35m"
DIM = "\033[2m"
E  = "\033[0m"

def ok(s):    print(f"  {G}✓{E} {s}")
def info(s):  print(f"  {C}▶{E} {s}")
def warn(s):  print(f"  {Y}⚠{E}  {s}")
def err(s):   print(f"  {R}✗{E} {s}")
def dim(s):   print(f"  {DIM}{s}{E}")

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
REPO_ROOT    = SCRIPT_DIR.parent
REGISTRY_PATH = REPO_ROOT / "council" / "COUNCIL_MODEL_REGISTRY.json"
KEYS_PATH    = Path.home() / ".council-keys" / ".env"
LOG_PATH     = REPO_ROOT / "council" / "update_log.jsonl"

N8N_HOST     = "http://46.225.51.30"

# ── Credential loader ─────────────────────────────────────────────────────────

def load_env_file(path: Path) -> dict:
    """Parse a .env file into a dict. Lines: KEY=VALUE or export KEY=VALUE."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^export\s+", "", line)
        if "=" in line:
            k, _, v = line.partition("=")
            v = v.strip().strip('"').strip("'")
            env[k.strip()] = v
    return env


def get_credentials() -> dict:
    """Return merged dict of credentials: env vars win over .env file."""
    creds = load_env_file(KEYS_PATH)
    # env vars override file values
    for key in list(creds.keys()):
        if os.environ.get(key):
            creds[key] = os.environ[key]
    # also pick up anything set only in env
    for k, v in os.environ.items():
        if k not in creds:
            creds[k] = v
    return creds


# ── n8n Client (cookie-based, matches wire_seat6.py pattern) ─────────────────

class N8n:
    def __init__(self, host: str = N8N_HOST):
        self.host   = host
        self.cj     = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj)
        )
        self._logged_in = False

    def _req(self, method: str, path: str, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req  = urllib.request.Request(self.host + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept",       "application/json")
        try:
            with self.opener.open(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP {e.code} {method} {path}: {e.read().decode()[:500]}")

    def get(self, p):          return self._req("GET",   p)
    def post(self, p, b):      return self._req("POST",  p, b)
    def patch(self, p, b):     return self._req("PATCH", p, b)
    def put(self, p, b):       return self._req("PUT",   p, b)

    def login(self, email: str, password: str):
        result = self.post("/rest/login", {"emailOrLdapLoginId": email, "password": password})
        if not result.get("data"):
            raise Exception(f"n8n login failed: {result}")
        self._logged_in = True

    def save_workflow(self, wf_id, wf):
        """Try PATCH (n8n 1.x) then PUT (older). Returns saved result."""
        last_err = None
        for method in ("patch", "put"):
            try:
                return getattr(self, method)(f"/rest/workflows/{wf_id}", wf)
            except Exception as e:
                last_err = e
        raise last_err

    def get_council_workflow(self):
        result = self.get("/rest/workflows")
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
        full_wf = self.get(f"/rest/workflows/{wf_id}")
        return wf_id, full_wf.get("data", full_wf)


# ── Provider model-check helpers ──────────────────────────────────────────────

def _http_get_json(url: str, headers: dict = None, timeout: int = 10) -> dict:
    req = urllib.request.Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise Exception(f"HTTP {e.code} GET {url}: {e.read().decode()[:300]}")
    except Exception as e:
        raise Exception(f"GET {url} failed: {e}")


def check_anthropic(creds: dict) -> tuple[str | None, list[str], str]:
    """Return (best_model, all_model_ids, error_message)."""
    key = creds.get("ANTHROPIC_API_KEY", "")
    if not key:
        return None, [], "ANTHROPIC_API_KEY not set"
    try:
        data = _http_get_json(
            "https://api.anthropic.com/v1/models",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"}
        )
        models = [m["id"] for m in data.get("data", [])]
        # Prefer claude-sonnet-4 or higher, then claude-3-7, etc.
        def rank(mid):
            mid = mid.lower()
            if "claude-opus-4"   in mid: return 0
            if "claude-sonnet-4" in mid: return 1
            if "claude-opus-3"   in mid: return 2
            if "claude-sonnet-3" in mid: return 3
            if "claude-haiku"    in mid: return 4
            return 9
        models.sort(key=rank)
        best = models[0] if models else None
        return best, models, ""
    except Exception as e:
        return None, [], str(e)


def check_openai(creds: dict) -> tuple[str | None, list[str], str]:
    key = creds.get("OPENAI_API_KEY", "")
    if not key:
        return None, [], "OPENAI_API_KEY not set"
    try:
        data = _http_get_json(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"}
        )
        models = [m["id"] for m in data.get("data", [])]
        # Filter to GPT-4 family and rank
        gpt4 = [m for m in models if "gpt-4" in m.lower() and "audio" not in m.lower()]

        def rank(mid):
            mid = mid.lower()
            if "gpt-4.1"          in mid and "mini" not in mid and "nano" not in mid: return 0
            if "gpt-4o"           in mid and "mini" not in mid: return 1
            if "gpt-4-turbo"      in mid: return 2
            if "gpt-4o-mini"      in mid: return 3
            if "gpt-4.1-mini"     in mid: return 4
            if "gpt-4.1-nano"     in mid: return 5
            return 9
        gpt4.sort(key=rank)
        best = gpt4[0] if gpt4 else None
        return best, gpt4, ""
    except Exception as e:
        return None, [], str(e)


def check_google(creds: dict) -> tuple[str | None, list[str], str]:
    key = creds.get("GOOGLE_API_KEY", "")
    if not key:
        return None, [], "GOOGLE_API_KEY not set"
    try:
        data = _http_get_json(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        )
        models = [m["name"].replace("models/", "") for m in data.get("models", [])]
        gemini = [m for m in models if "gemini" in m.lower()]

        def rank(mid):
            mid = mid.lower()
            if "gemini-2.5-pro"     in mid: return 0
            if "gemini-2.5-flash"   in mid: return 1
            if "gemini-2.0-pro"     in mid: return 2
            if "gemini-2.0-flash"   in mid: return 3
            if "gemini-1.5-pro"     in mid: return 4
            return 9
        gemini.sort(key=rank)
        best = gemini[0] if gemini else None
        return best, gemini, ""
    except Exception as e:
        return None, [], str(e)


def check_ollama(host: str = "204.168.143.98", port: int = 11434) -> tuple[list[str], str]:
    """Return (installed_model_ids, error_message)."""
    try:
        data = _http_get_json(f"http://{host}:{port}/api/tags", timeout=5)
        models = [m["name"] for m in data.get("models", [])]
        return models, ""
    except Exception as e:
        return [], str(e)


def check_zai(creds: dict) -> tuple[str | None, list[str], str]:
    key = creds.get("Z_AI_API_KEY", creds.get("Z_AI_KEY", ""))
    if not key:
        return None, [], "Z_AI_API_KEY not set (seat status: KEY_DEPLETED)"
    try:
        data = _http_get_json(
            "https://open.bigmodel.cn/api/paas/v4/models",
            headers={"Authorization": f"Bearer {key}"}
        )
        models = [m["id"] for m in data.get("data", [])]

        def rank(mid):
            mid = mid.lower()
            if "glm-4-plus"  in mid: return 0
            if "glm-4"       in mid and "flash" not in mid: return 1
            if "glm-4-flash" in mid: return 2
            return 9
        models.sort(key=rank)
        best = models[0] if models else None
        return best, models, ""
    except Exception as e:
        return None, [], str(e)


def check_xai(creds: dict) -> tuple[str | None, list[str], str]:
    key = creds.get("XAI_API_KEY", "")
    if not key:
        return None, [], "XAI_API_KEY not set"
    try:
        data = _http_get_json(
            "https://api.x.ai/v1/models",
            headers={"Authorization": f"Bearer {key}"}
        )
        models = [m["id"] for m in data.get("data", [])]

        def rank(mid):
            mid = mid.lower()
            if "grok-4"       in mid and "mini" not in mid: return 0
            if "grok-3"       in mid and "mini" not in mid: return 1
            if "grok-3-mini"  in mid: return 2
            if "grok-2"       in mid: return 3
            return 9
        models.sort(key=rank)
        best = models[0] if models else None
        return best, models, ""
    except Exception as e:
        return None, [], str(e)


# ── Registry helpers ──────────────────────────────────────────────────────────

def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text())


def save_registry(registry: dict):
    registry["last_updated"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2))


def log_change(entry: dict):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ── n8n workflow patcher ──────────────────────────────────────────────────────

def patch_n8n_node(full_wf: dict, node_name: str, new_model: str) -> bool:
    """Update the model field in the named n8n node. Returns True if changed."""
    for node in full_wf.get("nodes", []):
        if node.get("name") == node_name:
            params = node.setdefault("parameters", {})
            body_str = params.get("body", "")
            if body_str:
                try:
                    body = json.loads(body_str) if isinstance(body_str, str) else body_str
                    if body.get("model") != new_model:
                        body["model"] = new_model
                        params["body"] = json.dumps(body) if isinstance(body_str, str) else body
                        return True
                except (json.JSONDecodeError, TypeError):
                    # body might be a template string — do regex replace
                    new_body, count = re.subn(
                        r'"model"\s*:\s*"[^"]+"',
                        f'"model": "{new_model}"',
                        body_str
                    )
                    if count:
                        params["body"] = new_body
                        return True
            # Also handle direct model parameter (some node types)
            if params.get("model") and params["model"] != new_model:
                params["model"] = new_model
                return True
    return False


# ── Main update logic ─────────────────────────────────────────────────────────

def check_seat(seat: dict, creds: dict) -> dict:
    """
    Check a single seat (or gabriel dict) for model updates.
    Returns a result dict with keys: seat_id, name, provider, current_model,
    latest_model, status, available_models, error.
    """
    provider     = seat.get("provider", "")
    current      = seat.get("current_model", "")
    seat_id      = seat.get("seat_id", seat.get("name", "gabriel"))
    name         = seat.get("name", "Gabriel")
    node_name    = seat.get("n8n_node_name", "")

    result = {
        "seat_id":          seat_id,
        "name":             name,
        "provider":         provider,
        "current_model":    current,
        "latest_model":     None,
        "available_models": [],
        "status":           "UNKNOWN",
        "error":            "",
        "n8n_node_name":    node_name,
        "timestamp":        datetime.datetime.utcnow().isoformat() + "Z",
    }

    if provider == "anthropic":
        best, models, error = check_anthropic(creds)
    elif provider == "openai":
        best, models, error = check_openai(creds)
    elif provider == "google":
        best, models, error = check_google(creds)
    elif provider == "ollama":
        ollama_host = seat.get("ollama_host", "204.168.143.98")
        ollama_port = seat.get("ollama_port", 11434)
        installed, error = check_ollama(ollama_host, ollama_port)
        if error:
            result["status"] = "OFFLINE"
            result["error"]  = error
            return result
        # Best model = highest-ranked installed model from the alternatives list
        alts = [a["model"] for a in seat.get("alternatives", [])]
        best = next((m for m in alts if m in installed), None)
        if best is None and installed:
            best = current if current in installed else installed[0]
        models = installed
        result["available_models"] = models
        result["latest_model"]     = best
        if best is None:
            result["status"] = "NO_MODEL"
            result["error"]  = f"None of preferred models found in {installed}"
        elif best == current:
            result["status"] = "CURRENT"
        else:
            result["status"] = "UPDATE_AVAILABLE"
        return result
    elif provider == "zai":
        best, models, error = check_zai(creds)
    elif provider == "xai":
        best, models, error = check_xai(creds)
    else:
        result["status"] = "UNSUPPORTED_PROVIDER"
        result["error"]  = f"Provider '{provider}' not implemented"
        return result

    result["available_models"] = models
    result["latest_model"]     = best

    if error:
        result["status"] = "API_ERROR"
        result["error"]  = error
    elif best is None:
        result["status"] = "NO_MODEL"
        result["error"]  = "No models returned by API"
    elif best == current:
        result["status"] = "CURRENT"
    else:
        result["status"] = "UPDATE_AVAILABLE"

    return result


def run_update(args):
    print(f"\n{B}{'=' * 62}{E}")
    print(f"{B}  Council of Seven — Model Auto-Updater{E}")
    print(f"{B}{'=' * 62}{E}")
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    print(f"  {DIM}Run: {now}  |  Registry: {REGISTRY_PATH.name}{E}\n")

    if args.dry_run:
        print(f"  {Y}DRY RUN — no files will be written, n8n will not be patched{E}\n")

    # Load credentials
    creds = get_credentials()
    if KEYS_PATH.exists():
        dim(f"Credentials loaded from {KEYS_PATH}")
    else:
        dim(f"~/.council-keys/.env not found — using environment variables only")
    print()

    # Load registry
    registry = load_registry()
    all_seats_raw = registry.get("seats", [])
    gabriel_raw   = registry.get("gabriel", {})

    # Build list of (entity_dict, label)
    entities = [(s, f"Seat {s['seat_id']}") for s in all_seats_raw]
    entities.append((gabriel_raw, "Gabriel"))

    # Filter if --seat specified
    if args.seat:
        target = args.seat.lower()
        if target == "gabriel":
            entities = [(gabriel_raw, "Gabriel")]
        else:
            try:
                sid = int(target)
                entities = [(s, lbl) for s, lbl in entities if s.get("seat_id") == sid]
            except ValueError:
                print(f"{R}Invalid --seat value: {args.seat}{E}")
                sys.exit(1)
        if not entities:
            print(f"{R}Seat not found: {args.seat}{E}")
            sys.exit(1)

    # ── Check each seat ────────────────────────────────────────────────────
    results = []
    n8n_patches = []   # (node_name, new_model)

    for seat_dict, label in entities:
        name = seat_dict.get("name", label)
        provider = seat_dict.get("provider", "?")
        print(f"  {B}{label:8s}{E}  {C}{name:16s}{E}  {DIM}{provider}{E}")
        result = check_seat(seat_dict, creds)
        results.append(result)

        status = result["status"]
        current = result["current_model"]
        latest  = result["latest_model"]

        if status == "CURRENT":
            ok(f"Current: {G}{current}{E}  {DIM}(already latest){E}")
        elif status == "UPDATE_AVAILABLE":
            warn(f"Current:  {Y}{current}{E}")
            info(f"Latest:   {G}{latest}{E}  {B}← update available{E}")
            if not args.dry_run:
                # Update registry
                if "seat_id" in seat_dict:
                    for s in registry["seats"]:
                        if s["seat_id"] == seat_dict["seat_id"]:
                            s["current_model"]  = latest
                            s["api_model_id"]   = latest
                            s["last_checked"]   = result["timestamp"]
                            break
                else:
                    registry["gabriel"]["current_model"] = latest
                    registry["gabriel"]["api_model_id"]  = latest
                    registry["gabriel"]["last_checked"]  = result["timestamp"]
                n8n_patches.append((result["n8n_node_name"], latest))
                log_change({
                    "timestamp":     result["timestamp"],
                    "seat":          label,
                    "name":          name,
                    "provider":      provider,
                    "old_model":     current,
                    "new_model":     latest,
                    "action":        "UPDATED",
                })
        elif status in ("API_ERROR", "OFFLINE", "NO_MODEL"):
            err(f"{status}: {result['error']}")
            if "seat_id" in seat_dict:
                for s in registry["seats"]:
                    if s["seat_id"] == seat_dict["seat_id"]:
                        s["last_checked"] = result["timestamp"]
            else:
                registry["gabriel"]["last_checked"] = result["timestamp"]
        elif status == "UNSUPPORTED_PROVIDER":
            dim(f"Skipped: {result['error']}")
        else:
            dim(f"Status: {status}")
        print()

    if args.dry_run:
        _print_summary(results, dry_run=True)
        return

    # ── Save registry ──────────────────────────────────────────────────────
    updated_count = sum(1 for r in results if r["status"] == "UPDATE_AVAILABLE")
    if updated_count:
        info("Saving updated registry...")
        save_registry(registry)
        ok(f"Registry saved → {REGISTRY_PATH}")
        print()

    # ── Patch n8n workflow ─────────────────────────────────────────────────
    if n8n_patches:
        n8n_email    = creds.get("N8N_EMAIL", "")
        n8n_password = creds.get("N8N_PASSWORD", "")

        if not n8n_email or not n8n_password:
            warn("N8N_EMAIL / N8N_PASSWORD not set — skipping n8n workflow update")
            warn("Set these in ~/.council-keys/.env to enable live workflow patching")
        else:
            print(f"  {B}Patching n8n workflow...{E}")
            try:
                client = N8n()
                client.login(n8n_email, n8n_password)
                ok("n8n login successful")

                wf_id, full_wf = client.get_council_workflow()
                if not wf_id:
                    warn("Council workflow not found in n8n — skipping node patches")
                else:
                    ok(f"Workflow ID: {wf_id}")
                    any_patched = False
                    for node_name, new_model in n8n_patches:
                        if not node_name:
                            continue
                        changed = patch_n8n_node(full_wf, node_name, new_model)
                        if changed:
                            ok(f"Patched node {node_name} → {new_model}")
                            any_patched = True
                        else:
                            dim(f"Node {node_name}: no body/model field found or already correct")
                    if any_patched:
                        client.save_workflow(wf_id, full_wf)
                        ok("Workflow saved")
            except Exception as e:
                err(f"n8n update failed: {e}")
            print()

    _print_summary(results, dry_run=False)


def _print_summary(results: list, dry_run: bool = False):
    """Print a coloured summary table."""
    print(f"  {B}{'─' * 58}{E}")
    print(f"  {B}  SUMMARY{E}" + (f"  {Y}(DRY RUN){E}" if dry_run else ""))
    print(f"  {B}{'─' * 58}{E}")

    header = f"  {'Seat':<10}{'Name':<17}{'Status':<22}{'Model'}"
    print(f"  {DIM}{header}{E}")

    status_colours = {
        "CURRENT":           G,
        "UPDATE_AVAILABLE":  Y,
        "API_ERROR":         R,
        "OFFLINE":           R,
        "NO_MODEL":          R,
        "UNSUPPORTED_PROVIDER": DIM,
        "UNKNOWN":           DIM,
    }

    current_count = 0
    update_count  = 0
    error_count   = 0

    for r in results:
        sid    = str(r["seat_id"])
        name   = r["name"][:15]
        status = r["status"]
        model  = r["latest_model"] or r["current_model"] or "?"
        col    = status_colours.get(status, DIM)
        badge  = {
            "CURRENT":          "✓ CURRENT",
            "UPDATE_AVAILABLE": "↑ UPDATED" if not dry_run else "↑ PENDING",
            "API_ERROR":        "✗ API_ERROR",
            "OFFLINE":          "✗ OFFLINE",
            "NO_MODEL":         "✗ NO_MODEL",
        }.get(status, status[:20])

        print(f"  {sid:<10}{name:<17}{col}{badge:<22}{E}{model}")

        if status == "CURRENT":
            current_count += 1
        elif status == "UPDATE_AVAILABLE":
            update_count += 1
        else:
            error_count += 1

    print(f"  {B}{'─' * 58}{E}")
    parts = []
    if current_count: parts.append(f"{G}{current_count} current{E}")
    if update_count:  parts.append(f"{Y}{update_count} updated{E}")
    if error_count:   parts.append(f"{R}{error_count} errors{E}")
    print(f"  {B}Result:{E}  {' | '.join(parts)}")
    print(f"  {B}{'─' * 58}{E}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Auto-update Council of Seven model assignments"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report changes without writing anything"
    )
    parser.add_argument(
        "--seat", default=None,
        help="Check only this seat number (1-7) or 'gabriel'"
    )
    args = parser.parse_args()
    run_update(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n{R}✗ Unexpected error: {e}{E}\n", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
