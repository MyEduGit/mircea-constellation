#!/usr/bin/env python3
"""
council_status.py — Quick status dashboard for the Council of Seven.

Reads COUNCIL_MODEL_REGISTRY.json, pings each seat's API with a single-token
"Hi" request, and renders a coloured ASCII table with:
  - Current model per seat
  - PASS / FAIL / SKIP per seat
  - Latency in ms
  - Estimated cost per full Council run
  - Free vs paid seat breakdown

Usage:
  python3 setup/council_status.py [--no-ping] [--seat N]

Options:
  --no-ping   Skip API pings (show registry data only)
  --seat N    Check only seat N (1-7) or 'gabriel'

Credentials: ~/.council-keys/.env (same as update_council_models.py)
"""

import json
import os
import re
import sys
import time
import datetime
import argparse
import urllib.request
import urllib.error
from pathlib import Path

# ── Colour codes ──────────────────────────────────────────────────────────────
B   = "\033[1m"
G   = "\033[32m"
C   = "\033[36m"
R   = "\033[31m"
Y   = "\033[33m"
M   = "\033[35m"
DIM = "\033[2m"
E   = "\033[0m"

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).resolve().parent
REPO_ROOT     = SCRIPT_DIR.parent
REGISTRY_PATH = REPO_ROOT / "council" / "COUNCIL_MODEL_REGISTRY.json"
KEYS_PATH     = Path.home() / ".council-keys" / ".env"


# ── Credential loader (shared pattern) ───────────────────────────────────────

def load_env_file(path: Path) -> dict:
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
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def get_credentials() -> dict:
    creds = load_env_file(KEYS_PATH)
    for k in list(creds.keys()):
        if os.environ.get(k):
            creds[k] = os.environ[k]
    for k, v in os.environ.items():
        if k not in creds:
            creds[k] = v
    return creds


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text())


# ── API ping functions ────────────────────────────────────────────────────────

def _post_json(url: str, headers: dict, payload: dict, timeout: int = 15) -> tuple[dict, int]:
    """POST JSON payload, return (response_dict, latency_ms). Raises on error."""
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept",       "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    latency_ms = int((time.monotonic() - t0) * 1000)
    return data, latency_ms


def ping_anthropic(model: str, api_key: str) -> tuple[str, int, str]:
    """Returns (status, latency_ms, detail)."""
    try:
        data, ms = _post_json(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
            },
            payload={
                "model":      model,
                "max_tokens": 1,
                "messages":   [{"role": "user", "content": "Hi"}],
            },
        )
        # Any response with 'content' or 'id' is a pass
        if data.get("content") or data.get("id"):
            return "PASS", ms, model
        return "FAIL", ms, str(data)[:80]
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:120]
        return "FAIL", 0, f"HTTP {e.code}: {body}"
    except Exception as e:
        return "FAIL", 0, str(e)[:80]


def ping_openai(model: str, api_key: str) -> tuple[str, int, str]:
    try:
        data, ms = _post_json(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            payload={
                "model":      model,
                "max_tokens": 1,
                "messages":   [{"role": "user", "content": "Hi"}],
            },
        )
        if data.get("choices") or data.get("id"):
            return "PASS", ms, model
        return "FAIL", ms, str(data)[:80]
    except urllib.error.HTTPError as e:
        return "FAIL", 0, f"HTTP {e.code}: {e.read().decode()[:120]}"
    except Exception as e:
        return "FAIL", 0, str(e)[:80]


def ping_google(model: str, api_key: str) -> tuple[str, int, str]:
    model_id = model.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    try:
        data, ms = _post_json(
            url,
            headers={},
            payload={"contents": [{"parts": [{"text": "Hi"}]}]},
        )
        if data.get("candidates") or data.get("promptFeedback"):
            return "PASS", ms, model_id
        return "FAIL", ms, str(data)[:80]
    except urllib.error.HTTPError as e:
        return "FAIL", 0, f"HTTP {e.code}: {e.read().decode()[:120]}"
    except Exception as e:
        return "FAIL", 0, str(e)[:80]


def ping_ollama(model: str, host: str = "204.168.143.98", port: int = 11434) -> tuple[str, int, str]:
    try:
        data, ms = _post_json(
            f"http://{host}:{port}/api/chat",
            headers={},
            payload={
                "model":    model,
                "messages": [{"role": "user", "content": "Hi"}],
                "stream":   False,
            },
            timeout=20,
        )
        if data.get("message") or data.get("done"):
            return "PASS", ms, f"{host} local"
        return "FAIL", ms, str(data)[:80]
    except Exception as e:
        return "FAIL", 0, str(e)[:80]


def ping_zai(model: str, api_key: str) -> tuple[str, int, str]:
    try:
        data, ms = _post_json(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            payload={
                "model":      model,
                "max_tokens": 1,
                "messages":   [{"role": "user", "content": "Hi"}],
            },
        )
        if data.get("choices") or data.get("id"):
            return "PASS", ms, model
        return "FAIL", ms, str(data)[:80]
    except urllib.error.HTTPError as e:
        return "FAIL", 0, f"HTTP {e.code}: {e.read().decode()[:120]}"
    except Exception as e:
        return "FAIL", 0, str(e)[:80]


def ping_xai(model: str, api_key: str) -> tuple[str, int, str]:
    try:
        data, ms = _post_json(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            payload={
                "model":      model,
                "max_tokens": 1,
                "messages":   [{"role": "user", "content": "Hi"}],
            },
        )
        if data.get("choices") or data.get("id"):
            return "PASS", ms, model
        return "FAIL", ms, str(data)[:80]
    except urllib.error.HTTPError as e:
        return "FAIL", 0, f"HTTP {e.code}: {e.read().decode()[:120]}"
    except Exception as e:
        return "FAIL", 0, str(e)[:80]


def ping_seat(seat: dict, creds: dict, do_ping: bool) -> dict:
    """
    Ping a single seat. Returns dict with:
      seat_id, name, provider, model, status, latency_ms, detail, is_free
    """
    provider = seat.get("provider", "")
    model    = seat.get("current_model", "?")
    seat_id  = seat.get("seat_id", seat.get("name", "Gabriel"))
    name     = seat.get("name", "Gabriel")
    is_free  = seat.get("cost_per_1m_tokens", {}).get("input", 1) == 0

    result = {
        "seat_id":    seat_id,
        "name":       name,
        "provider":   provider,
        "model":      model,
        "status":     "SKIP",
        "latency_ms": 0,
        "detail":     "",
        "is_free":    is_free,
        "key_status": seat.get("key_status", ""),
    }

    if not do_ping:
        result["status"] = "SKIP"
        result["detail"] = "ping disabled"
        return result

    # Check for depleted/missing key
    if seat.get("key_status") == "DEPLETED":
        result["status"] = "SKIP"
        result["detail"] = "key depleted"
        return result

    key_var = seat.get("key_env_var", "")
    api_key = creds.get(key_var, "") if key_var else ""

    if provider in ("anthropic", "openai", "google", "zai", "xai") and not api_key:
        result["status"] = "SKIP"
        result["detail"] = f"{key_var} not set"
        return result

    try:
        if provider == "anthropic":
            status, ms, detail = ping_anthropic(model, api_key)
        elif provider == "openai":
            status, ms, detail = ping_openai(model, api_key)
        elif provider == "google":
            status, ms, detail = ping_google(model, api_key)
        elif provider == "ollama":
            h = seat.get("ollama_host", "204.168.143.98")
            p = seat.get("ollama_port", 11434)
            status, ms, detail = ping_ollama(model, h, p)
        elif provider == "zai":
            status, ms, detail = ping_zai(model, api_key)
        elif provider == "xai":
            status, ms, detail = ping_xai(model, api_key)
        else:
            status, ms, detail = "SKIP", 0, f"provider '{provider}' not implemented"

        result["status"]     = status
        result["latency_ms"] = ms
        result["detail"]     = detail
    except Exception as e:
        result["status"] = "FAIL"
        result["detail"] = str(e)[:80]

    return result


# ── Cost estimator ────────────────────────────────────────────────────────────

def compute_cost_table(registry: dict) -> list[dict]:
    """Return per-seat cost rows using registry cost_estimate_per_council_run."""
    rows = []
    est = registry.get("cost_estimate_per_council_run", {})
    seats_est = {s["seat"]: s for s in est.get("seats_paid", [])}

    for seat in registry.get("seats", []):
        sid = seat["seat_id"]
        info = seats_est.get(sid, {})
        cost = info.get("cost_usd", 0)
        rows.append({
            "seat_id":  sid,
            "name":     seat["name"],
            "model":    seat["current_model"],
            "is_free":  seat["cost_per_1m_tokens"]["input"] == 0,
            "cost_usd": cost,
            "in_usd":   seat["cost_per_1m_tokens"]["input"],
            "out_usd":  seat["cost_per_1m_tokens"]["output"],
        })

    gab = registry.get("gabriel", {})
    rows.append({
        "seat_id":  "G",
        "name":     "Gabriel",
        "model":    gab.get("current_model", "?"),
        "is_free":  gab.get("cost_per_1m_tokens", {}).get("input", 1) == 0,
        "cost_usd": est.get("gabriel_cost_usd", 0),
        "in_usd":   gab.get("cost_per_1m_tokens", {}).get("input", 0),
        "out_usd":  gab.get("cost_per_1m_tokens", {}).get("output", 0),
    })
    return rows


# ── Render functions ──────────────────────────────────────────────────────────

COL_W = [5, 17, 28, 8, 8, 6, 36]
HEADERS = ["Seat", "Name", "Model", "Status", "Lat(ms)", "Free?", "Detail / Provider"]


def _row(cols: list) -> str:
    parts = []
    for i, c in enumerate(cols):
        w = COL_W[i]
        parts.append(str(c)[:w].ljust(w))
    return "  " + "  ".join(parts)


def render_status_table(ping_results: list):
    print(f"  {B}{_row(HEADERS)}{E}")
    print(f"  {'─' * (sum(COL_W) + 2 * len(COL_W))}")

    for r in ping_results:
        sid     = str(r["seat_id"])
        name    = r["name"][:15]
        model   = r["model"][:26]
        status  = r["status"]
        ms      = str(r["latency_ms"]) if r["latency_ms"] else "—"
        free    = "FREE" if r["is_free"] else "paid"
        detail  = r["detail"][:34]

        if r["key_status"] == "DEPLETED":
            detail = "KEY DEPLETED"

        col = {
            "PASS": G,
            "FAIL": R,
            "SKIP": DIM,
        }.get(status, DIM)

        free_col = G if r["is_free"] else Y

        row = f"  {sid:<5}  {C}{name:<17}{E}  {model:<28}  " \
              f"{col}{status:<8}{E}  {ms:>6}  {free_col}{free:<6}{E}  {DIM}{detail}{E}"
        print(row)

    print(f"  {'─' * (sum(COL_W) + 2 * len(COL_W))}")


def render_cost_table(cost_rows: list, registry: dict):
    print(f"\n  {B}{'─' * 62}{E}")
    print(f"  {B}  ESTIMATED COST PER FULL COUNCIL RUN{E}")
    print(f"  {DIM}  Assumption: ~500 input + 300 output tokens per seat{E}")
    print(f"  {DIM}  Gabriel: ~3000 input + 800 output (receives all seat responses){E}")
    print(f"  {'─' * 62}")

    hdr = f"  {'Seat':<5}  {'Name':<17}  {'Model':<28}  {'$/run':>8}  {'In $/M':>8}  {'Out $/M':>8}"
    print(f"  {B}{hdr}{E}")

    total = 0
    for r in cost_rows:
        sid   = str(r["seat_id"])
        name  = r["name"][:15]
        model = r["model"][:26]
        cost  = r["cost_usd"]
        total += cost
        in_p  = r["in_usd"]
        out_p = r["out_usd"]
        free_col = G if r["is_free"] else E
        cost_str = f"${cost:.6f}" if cost > 0 else f"{G}$0.000000{E}"
        print(f"  {sid:<5}  {C}{name:<17}{E}  {model:<28}  "
              f"{free_col}{cost_str:>10}{E}  {DIM}{in_p:>6.2f}  {out_p:>7.2f}{E}")

    print(f"  {'─' * 62}")
    print(f"  {B}  Total estimated per run:{E}  {Y}${total:.6f}{E}  "
          f"({G}FREE seats save ~${(total * 0.4):.4f}{E})")
    est = registry.get("cost_estimate_per_council_run", {})
    note = est.get("local_savings_note", "")
    if note:
        print(f"  {DIM}  {note}{E}")
    print(f"  {'─' * 62}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Council of Seven — quick status check"
    )
    parser.add_argument(
        "--no-ping", action="store_true",
        help="Skip API pings (show registry info only)"
    )
    parser.add_argument(
        "--seat", default=None,
        help="Check only this seat number (1-7) or 'gabriel'"
    )
    args = parser.parse_args()
    do_ping = not args.no_ping

    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    print(f"\n{B}{'=' * 66}{E}")
    print(f"{B}   Council of Seven — Status Dashboard{E}")
    print(f"{B}{'=' * 66}{E}")
    print(f"  {DIM}Time: {now}  |  n8n: http://46.225.51.30{E}")
    if not do_ping:
        print(f"  {Y}Note: API pings disabled (--no-ping){E}")
    print()

    creds    = get_credentials()
    registry = load_registry()

    seats   = registry.get("seats", [])
    gabriel = registry.get("gabriel", {})

    entities = seats + [gabriel]

    # Filter if --seat
    if args.seat:
        target = args.seat.lower()
        if target == "gabriel":
            entities = [gabriel]
        else:
            try:
                sid = int(target)
                entities = [s for s in seats if s.get("seat_id") == sid]
            except ValueError:
                print(f"{R}Invalid --seat: {args.seat}{E}")
                sys.exit(1)
        if not entities:
            print(f"{R}Seat not found: {args.seat}{E}")
            sys.exit(1)

    # Run pings (or skip)
    if do_ping:
        print(f"  {C}Pinging all seats...{E}  {DIM}(timeout: 15s each){E}\n")

    ping_results = []
    for seat in entities:
        sid   = seat.get("seat_id", "G")
        sname = seat.get("name", "Gabriel")
        model = seat.get("current_model", "?")
        if do_ping:
            sys.stdout.write(f"  {DIM}Seat {sid:<3} {sname:<16} {model:<28}{E} ... ")
            sys.stdout.flush()

        result = ping_seat(seat, creds, do_ping)
        ping_results.append(result)

        if do_ping:
            col    = G if result["status"] == "PASS" else (R if result["status"] == "FAIL" else DIM)
            badge  = result["status"]
            ms_str = f"{result['latency_ms']}ms" if result["latency_ms"] else ""
            print(f"{col}{badge}{E}  {DIM}{ms_str}{E}")

    print()

    # ── Status table ───────────────────────────────────────────────────────
    print(f"  {B}{'─' * 62}{E}")
    print(f"  {B}  SEAT STATUS{E}")
    print(f"  {'─' * 62}")
    render_status_table(ping_results)

    # ── Cost table ─────────────────────────────────────────────────────────
    if not args.seat:   # only show full cost table when checking all seats
        cost_rows = compute_cost_table(registry)
        render_cost_table(cost_rows, registry)

    # ── Quick legend ───────────────────────────────────────────────────────
    print(f"  {DIM}Legend:  "
          f"{G}PASS{E}{DIM} = API responded  "
          f"{R}FAIL{E}{DIM} = API error / timeout  "
          f"{DIM}SKIP{E}{DIM} = no key / depleted / ping disabled{E}\n")

    # ── n8n shortcut ──────────────────────────────────────────────────────
    print(f"  {B}n8n UI:{E}  http://46.225.51.30  →  Council of Seven Master Spirits v1")
    print(f"  {B}Update:{E} python3 setup/update_council_models.py")
    print()


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
