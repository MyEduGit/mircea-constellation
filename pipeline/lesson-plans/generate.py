#!/usr/bin/env python3
"""
CommunityPlus EAL — term-plan + session-plan pipeline generator.

Two modes:

  session  (default)  — single-session plan
    Reads:  templates/session-plan.template.md   (Jinja2)
            templates/mapping.schema.yaml        (default unit shape)
            units/<UNIT>.yaml                    (per-unit overrides)
    Writes: output/<UNIT>_S<NN>_<DATE>.md

  term               — term macro-skills matrix plan
    Reads:  templates/term-plan.template.md      (Jinja2)
            terms/<TERM_SLUG>.yaml               (per-term YAML)
            units/<UNIT>.yaml                    (for each unit threaded in)
    Writes: output/<TERM_SLUG>.md

Usage:
    python3 generate.py VU22358 --session 3 --date 2026-04-22
    python3 generate.py VU22358 --session 3 --date 2026-04-22 --draft
    python3 generate.py --check VU22358
    python3 generate.py --mode term 22640VIC-cert3-term1-2026

Governing frame enforced: VRQA accredited course doc + Standards for RTOs 2025
(ASQA) + AMEP Deed or SEE contract + CommunityPlus audit trail. See
COMPLIANCE.md.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    sys.stderr.write(
        "error: PyYAML is required. Install with: pip install pyyaml\n"
    )
    sys.exit(2)

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
except ImportError:
    sys.stderr.write(
        "error: Jinja2 is required. Install with: pip install jinja2\n"
    )
    sys.exit(2)


TEMPLATE_VERSION = "1.0"   # bump + add CHANGELOG entry when template changes

ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = ROOT / "templates"
UNITS_DIR = ROOT / "units"
TERMS_DIR = ROOT / "terms"
OUTPUT_DIR = ROOT / "output"

TBD_RE = re.compile(r"TBD_FROM_[A-Z_]+")


# ──────────────────────────────────────────────────────────────────────
# Deep merge — unit YAML overrides schema defaults
# ──────────────────────────────────────────────────────────────────────
def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Lists from override replace base."""
    out = dict(base)
    for k, v in (override or {}).items():
        if (
            k in out
            and isinstance(out[k], dict)
            and isinstance(v, dict)
        ):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# ──────────────────────────────────────────────────────────────────────
# Load context for a unit
# ──────────────────────────────────────────────────────────────────────
def load_context(unit_code: str) -> dict:
    schema_path = TEMPLATES_DIR / "mapping.schema.yaml"
    unit_path = UNITS_DIR / f"{unit_code}.yaml"
    if not schema_path.exists():
        sys.exit(f"error: schema not found: {schema_path}")
    if not unit_path.exists():
        sys.exit(f"error: unit YAML not found: {unit_path}")

    with schema_path.open() as f:
        schema = yaml.safe_load(f) or {}
    with unit_path.open() as f:
        unit = yaml.safe_load(f) or {}

    return deep_merge(schema, unit)


# ──────────────────────────────────────────────────────────────────────
# Compliance checks (subset — see COMPLIANCE.md for the full list)
# ──────────────────────────────────────────────────────────────────────
def check(ctx: dict, *, allow_tbd: bool) -> list[str]:
    errs: list[str] = []

    # 1. No TBD_FROM_* placeholders anywhere (unless --draft)
    if not allow_tbd:
        flat = json.dumps(ctx, default=str)
        found = sorted(set(TBD_RE.findall(flat)))
        if found:
            errs.append(
                "unresolved placeholders: " + ", ".join(found)
                + "  (fix the unit YAML, or pass --draft to override)"
            )

    # 2. Mapping rows reference real assessor-guide tasks
    ag_task_ids = {
        t.get("id")
        for t in (ctx.get("unit", {}).get("assessor_guide", {}).get("tasks") or [])
    }
    for row in ctx.get("unit", {}).get("mapping", {}).get("rows") or []:
        if row.get("assessment_task") not in ag_task_ids:
            errs.append(
                f"mapping row {row.get('id')} → unknown assessor-guide task "
                f"{row.get('assessment_task')}"
            )

    # 3. Session activities' maps_to reference real mapping rows
    mapping_row_ids = {
        r.get("id")
        for r in (ctx.get("unit", {}).get("mapping", {}).get("rows") or [])
    }
    for a in ctx.get("session", {}).get("activities") or []:
        for m in a.get("maps_to") or []:
            if m not in mapping_row_ids:
                errs.append(
                    f"session activity '{a.get('stage')}' → unknown mapping row {m}"
                )

    # 4. Formative checks' mapping_row + assessor_guide_task resolve
    for f in ctx.get("session", {}).get("formative_checks") or []:
        if f.get("mapping_row") and f["mapping_row"] not in mapping_row_ids:
            errs.append(
                f"formative check {f.get('id')} → unknown mapping row "
                f"{f['mapping_row']}"
            )
        if f.get("assessor_guide_task") and f["assessor_guide_task"] not in ag_task_ids:
            errs.append(
                f"formative check {f.get('id')} → unknown assessor-guide task "
                f"{f['assessor_guide_task']}"
            )

    # 5. Template version declared in unit YAML ≤ TEMPLATE_VERSION in generator
    declared = str(ctx.get("template", {}).get("version", TEMPLATE_VERSION))
    if _version_tuple(declared) > _version_tuple(TEMPLATE_VERSION):
        errs.append(
            f"unit declares template v{declared} but generator ships v{TEMPLATE_VERSION}"
        )

    # 6. Nominal-hours budget not over-allocated
    total = float(ctx.get("unit", {}).get("nominal_hours_total") or 0)
    used_prior = float(ctx.get("session", {}).get("nominal_hours_used_prior") or 0)
    this_session = float(ctx.get("session", {}).get("duration_hours") or 0)
    if total and used_prior + this_session > total:
        errs.append(
            f"nominal-hours over-allocation: {used_prior} + {this_session} "
            f"> {total}"
        )

    return errs


def _version_tuple(s: str) -> tuple[int, ...]:
    try:
        return tuple(int(p) for p in s.split("."))
    except ValueError:
        return (0,)


# ──────────────────────────────────────────────────────────────────────
# Render
# ──────────────────────────────────────────────────────────────────────
def render(ctx: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        trim_blocks=False,
        lstrip_blocks=False,
        keep_trailing_newline=True,
    )
    tpl = env.get_template("session-plan.template.md")

    # doc metadata
    ctx = dict(ctx)
    ctx.setdefault("template", {})["version"] = TEMPLATE_VERSION
    ctx["doc"] = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(
            timespec="seconds"
        ),
        "input_sha256": _hash_context(ctx),
    }
    return tpl.render(**ctx)


def _hash_context(ctx: dict) -> str:
    blob = json.dumps(ctx, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


# ──────────────────────────────────────────────────────────────────────
# Term-plan mode
# ──────────────────────────────────────────────────────────────────────
def load_term_context(term_slug: str) -> dict:
    term_path = TERMS_DIR / f"{term_slug}.yaml"
    if not term_path.exists():
        sys.exit(f"error: term YAML not found: {term_path}")
    with term_path.open() as f:
        term = yaml.safe_load(f) or {}

    # Resolve each threaded unit via its unit_yaml pointer (or fallback
    # to units/<code>.yaml).
    unit_index: dict[str, dict] = {}
    for u in term.get("units", []):
        code = u.get("code")
        rel = u.get("unit_yaml") or f"units/{code}.yaml"
        path = ROOT / rel
        if not path.exists():
            sys.exit(f"error: unit YAML for {code} not found: {path}")
        with path.open() as f:
            data = yaml.safe_load(f) or {}
        unit_index[code] = data.get("unit", {})
    term["unit_index"] = unit_index
    return term


def render_term(ctx: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        trim_blocks=False,
        lstrip_blocks=False,
        keep_trailing_newline=True,
    )
    tpl = env.get_template("term-plan.template.md")
    ctx = dict(ctx)
    ctx.setdefault("template", {})["version"] = TEMPLATE_VERSION
    ctx["doc"] = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "input_sha256": _hash_context(ctx),
    }
    return tpl.render(**ctx)


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("target",
                   help="unit code (session mode) or term slug (term mode) — "
                        "e.g. VU22358  or  22640VIC-cert3-term1-2026")
    p.add_argument("--mode", choices=("session", "term"), default="session",
                   help="artefact to produce (default: session)")
    p.add_argument("--session", type=int, help="session number (session mode only)")
    p.add_argument("--date", help="delivery date YYYY-MM-DD (session mode only)")
    p.add_argument("--draft", action="store_true",
                   help="allow unresolved TBD_FROM_* placeholders")
    p.add_argument("--check", action="store_true",
                   help="run compliance checks and exit (no output file)")
    args = p.parse_args()

    if args.mode == "term":
        ctx = load_term_context(args.target)
        # Basic TBD sweep (term plans don't have the session-level checks).
        if not args.draft:
            flat = json.dumps(ctx, default=str)
            found = sorted(set(TBD_RE.findall(flat)))
            if found:
                sys.stderr.write("compliance errors:\n")
                sys.stderr.write(
                    "  - unresolved placeholders: " + ", ".join(found) + "\n"
                )
                sys.stderr.write(
                    "refusing to generate non-draft term plan; "
                    "fix the YAML or re-run with --draft\n"
                )
                if args.check:
                    return 1
                return 1
        if args.check:
            print(f"OK: term plan {args.target} passes (basic TBD check)")
            return 0
        rendered = render_term(ctx)
        OUTPUT_DIR.mkdir(exist_ok=True)
        out_path = OUTPUT_DIR / f"{args.target}.md"
        out_path.write_text(rendered)
        print(f"wrote {out_path}")
        return 0

    # ── session mode ──
    ctx = load_context(args.target)

    if args.session is not None:
        ctx.setdefault("session", {})["number"] = args.session
    if args.date:
        ctx.setdefault("session", {})["date"] = args.date

    errs = check(ctx, allow_tbd=args.draft)
    if errs and not args.check:
        sys.stderr.write("compliance errors:\n")
        for e in errs:
            sys.stderr.write(f"  - {e}\n")
        if not args.draft:
            sys.stderr.write(
                "refusing to generate non-draft plan; "
                "fix errors or re-run with --draft\n"
            )
            return 1

    if args.check:
        if errs:
            for e in errs:
                print(f"FAIL: {e}")
            return 1
        print(f"OK: {args.target} passes compliance checks")
        return 0

    rendered = render(ctx)

    OUTPUT_DIR.mkdir(exist_ok=True)
    session_n = ctx.get("session", {}).get("number") or 0
    session_d = ctx.get("session", {}).get("date") or "undated"
    out_path = OUTPUT_DIR / f"{args.target}_S{int(session_n):02d}_{session_d}.md"
    out_path.write_text(rendered)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
