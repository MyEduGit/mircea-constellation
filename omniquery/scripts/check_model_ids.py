#!/usr/bin/env python3
"""OmniQuery model-ID watchdog.

Verifies that the exact model IDs configured for each Force-of-Three seat are
still current at their official source, and that no retired/forbidden ID has
crept into the repo. Safe to run locally and daily.

Doctrine (see ../docs/MODEL_ID_POLICY.md):
  - Lineages are doctrine; exact model IDs are mutable configuration.
  - Retired aliases are forbidden even if providers redirect them.
  - Silent redirects are audit failures (BLOCKED).
  - This script DETECTS ONLY. It never patches and never calls a provider API.

No API keys are read or required. Network access is limited to fetching the
public documentation URLs listed in model_id_sources.json. Use --offline to
skip the network and run repo/consistency checks only.

Exit codes: 0 = PASS, 1 = NEEDS_REVIEW, 2 = BLOCKED, 3 = usage/internal error.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]  # scripts -> omniquery -> repo root
SOURCES_PATH = SCRIPT_DIR / "model_id_sources.json"
REPORT_DIR = REPO_ROOT / "omniquery" / "docs" / "model_id_checks"

USER_AGENT = "OmniQuery-ModelIDWatchdog/1.0 (+local check; no auth)"
HTTP_TIMEOUT = 20

# Verdict ordering — worst wins.
PASS = "PASS"
NEEDS_REVIEW = "NEEDS_REVIEW"
BLOCKED = "BLOCKED"
_RANK = {PASS: 0, NEEDS_REVIEW: 1, BLOCKED: 2}
_EXIT = {PASS: 0, NEEDS_REVIEW: 1, BLOCKED: 2}


def worst(*verdicts: str) -> str:
    return max(verdicts, key=lambda v: _RANK[v]) if verdicts else PASS


def load_sources() -> dict:
    with SOURCES_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def fetch(url: str) -> tuple[bool, str]:
    """Fetch a URL with no credentials. Returns (ok, text_or_error)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read().decode(charset, errors="replace")
            return True, body
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return False, f"URL error: {exc.reason}"
    except Exception as exc:  # noqa: BLE001 - report any fetch failure cleanly
        return False, f"fetch error: {exc.__class__.__name__}"


def contains_id(haystack: str, model_id: str) -> bool:
    return model_id.lower() in haystack.lower()


def check_seat(seat: dict, offline: bool, cache: dict) -> dict:
    """Return a per-seat result dict with verdict, notes, and evidence."""
    model_id = seat["model_id"]
    notes: list[str] = []
    verdict = PASS

    if offline:
        notes.append("offline mode — source docs not fetched; ID not confirmed live")
        verdict = worst(verdict, NEEDS_REVIEW)
        return {"seat": seat, "verdict": verdict, "notes": notes}

    # 1) Confirm the ID is present in the provider's model docs.
    doc_url = seat.get("doc_url")
    if doc_url:
        if doc_url not in cache:
            cache[doc_url] = fetch(doc_url)
        ok, body = cache[doc_url]
        if not ok:
            notes.append(f"could not reach model docs ({body}) — manual verification needed")
            verdict = worst(verdict, NEEDS_REVIEW)
        elif contains_id(body, model_id):
            notes.append("confirmed present in official model docs")
        else:
            notes.append("NOT found in model docs — may be renamed/removed; verify manually")
            verdict = worst(verdict, NEEDS_REVIEW)
    else:
        notes.append("no model doc URL configured")
        verdict = worst(verdict, NEEDS_REVIEW)

    # 2) Check the deprecation/retirement page for this exact ID.
    dep_url = seat.get("deprecation_url")
    if dep_url:
        if dep_url not in cache:
            cache[dep_url] = fetch(dep_url)
        ok, body = cache[dep_url]
        if not ok:
            notes.append(f"could not reach deprecation/retirement page ({body})")
            verdict = worst(verdict, NEEDS_REVIEW)
        elif contains_id(body, model_id):
            notes.append(
                "this ID appears on a deprecation/retirement page — verify it is "
                "not scheduled for shutdown or silent redirect"
            )
            verdict = worst(verdict, NEEDS_REVIEW)
        else:
            notes.append("not listed on deprecation/retirement page")

    return {"seat": seat, "verdict": verdict, "notes": notes}


def check_forbidden_against_seats(seats: list[dict], forbidden: list[dict]) -> list[dict]:
    """A configured seat must never use a forbidden ID."""
    forbidden_ids = {f["model_id"].lower() for f in forbidden}
    results = []
    for seat in seats:
        if seat["model_id"].lower() in forbidden_ids:
            results.append(
                {
                    "seat": seat["seat"],
                    "model_id": seat["model_id"],
                    "verdict": BLOCKED,
                    "note": "configured seat uses a FORBIDDEN/retired ID",
                }
            )
    return results


def scan_repo_for_forbidden(forbidden: list[dict], globs: list[str]) -> list[dict]:
    """Grep tracked artifacts for retired/forbidden IDs."""
    findings = []
    files: list[Path] = []
    for pattern in globs:
        files.extend(Path(p) for p in glob.glob(str(REPO_ROOT / pattern)))
    for entry in forbidden:
        fid = entry["model_id"]
        for fpath in files:
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if fid.lower() in text.lower():
                findings.append(
                    {
                        "model_id": fid,
                        "file": str(fpath.relative_to(REPO_ROOT)),
                        "reason": entry.get("reason", ""),
                    }
                )
    return findings


def build_report(date_str: str, sources: dict, seat_results: list[dict],
                 forbidden_seat_hits: list[dict], repo_findings: list[dict],
                 overall: str, offline: bool) -> str:
    lines = [
        f"# OmniQuery Model-ID Check — {date_str}",
        "",
        f"> Verdict: **{overall}**",
        f"> Mode: {'offline (no network)' if offline else 'online'}",
        f"> Generated by: omniquery/scripts/check_model_ids.py",
        f"> Sources config version: {sources.get('version', 'n/a')}",
        "",
        "Lineages are doctrine; exact model IDs are mutable configuration "
        "(see MODEL_ID_POLICY.md). This check detects only — it never patches.",
        "",
        "## Seat results",
        "",
        "| Seat | Provider | Model ID | Verdict |",
        "|------|----------|----------|---------|",
    ]
    for r in seat_results:
        s = r["seat"]
        lines.append(
            f"| {s['seat']} | {s['provider']} | `{s['model_id']}` | {r['verdict']} |"
        )
    lines.append("")
    lines.append("### Seat notes")
    lines.append("")
    for r in seat_results:
        s = r["seat"]
        lines.append(f"- **{s['seat']} (`{s['model_id']}`)** — {r['verdict']}")
        for note in r["notes"]:
            lines.append(f"  - {note}")
    lines.append("")

    lines.append("## Forbidden-ID checks")
    lines.append("")
    if forbidden_seat_hits:
        lines.append("**BLOCKED — a configured seat uses a forbidden/retired ID:**")
        for hit in forbidden_seat_hits:
            lines.append(f"- {hit['seat']}: `{hit['model_id']}` — {hit['note']}")
    else:
        lines.append("- No configured seat uses a forbidden/retired ID.")
    lines.append("")
    if repo_findings:
        lines.append("**Retired/forbidden IDs found in repo artifacts:**")
        for f in repo_findings:
            lines.append(f"- `{f['model_id']}` in `{f['file']}` — {f['reason']}")
    else:
        lines.append("- No retired/forbidden IDs found in scanned repo artifacts.")
    lines.append("")

    lines.append("## What to do")
    lines.append("")
    if overall == PASS:
        lines.append("- All configured IDs confirmed. No action required.")
    elif overall == NEEDS_REVIEW:
        lines.append("- Human review required. Confirm flagged IDs against the live")
        lines.append("  provider docs before any import, live test, or deployment.")
    else:
        lines.append("- **BLOCKED.** A retired/forbidden or silently redirected ID is")
        lines.append("  present. Do not import, test live, or deploy until corrected.")
        lines.append("- Patch only after explicit Mircea approval (e.g. `SPIRIT MODEL UPDATE GO`).")
    lines.append("")
    lines.append("_No API keys were read. No provider API was called. No files were patched._")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="OmniQuery model-ID watchdog (detect only).")
    parser.add_argument("--offline", action="store_true",
                        help="Skip network; run repo/consistency checks only.")
    parser.add_argument("--no-report", action="store_true",
                        help="Print to stdout but do not write a dated report file.")
    parser.add_argument("--date", default=None,
                        help="Override report date (YYYY-MM-DD), for testing.")
    args = parser.parse_args(argv)

    if not SOURCES_PATH.exists():
        print(f"ERROR: missing {SOURCES_PATH}", file=sys.stderr)
        return 3
    sources = load_sources()

    date_str = args.date or dt.date.today().isoformat()
    seats = sources.get("seats", [])
    forbidden = sources.get("forbidden_ids", [])
    globs = sources.get("repo_scan_globs", [])

    cache: dict = {}
    seat_results = [check_seat(seat, args.offline, cache) for seat in seats]
    forbidden_seat_hits = check_forbidden_against_seats(seats, forbidden)
    repo_findings = scan_repo_for_forbidden(forbidden, globs)

    overall = PASS
    for r in seat_results:
        overall = worst(overall, r["verdict"])
    if forbidden_seat_hits:
        overall = worst(overall, BLOCKED)
    if repo_findings:
        # Stale retired IDs in artifacts are an audit failure.
        overall = worst(overall, BLOCKED)

    report = build_report(date_str, sources, seat_results, forbidden_seat_hits,
                          repo_findings, overall, args.offline)

    print(report)

    if not args.no_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = REPORT_DIR / f"{date_str}.md"
        out_path.write_text(report, encoding="utf-8")
        print(f"\n[written] {out_path.relative_to(REPO_ROOT)}", file=sys.stderr)

    print(f"\nOVERALL: {overall}", file=sys.stderr)
    return _EXIT[overall]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
