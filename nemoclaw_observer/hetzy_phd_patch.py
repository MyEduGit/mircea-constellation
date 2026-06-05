#!/usr/bin/env python3
"""
NemoClaw Observer — hetzy_phd.py autopatcher

Finds the real hetzy_phd.py on the VPS and adds the /dashboard
and /status Telegram command handlers automatically.

Usage:
    python3 hetzy_phd_patch.py /path/to/hetzy_phd.py

If no path is given, searches common locations automatically.

What it changes
---------------
  1. Adds the import at the top of the file (after existing imports)
  2. Adds CommandHandler registrations before application.run_polling()

The patch is idempotent — safe to run multiple times.
"""

import sys
import os
import re
import shutil
import datetime

IMPORT_LINE = (
    "from nemoclaw_observer.telegram_handler import "
    "handle_dashboard_command, handle_status_command"
)

HANDLER_LINES = [
    "    application.add_handler(CommandHandler(\"dashboard\", handle_dashboard_command))",
    "    application.add_handler(CommandHandler(\"status\",    handle_status_command))",
]

COMMON_LOCATIONS = [
    "/opt/nemoclaw/hetzy_phd.py",
    "/opt/hetzy_phd.py",
    "/home/mircea/hetzy_phd.py",
    "/root/hetzy_phd.py",
    os.path.expanduser("~/hetzy_phd.py"),
]


def find_file():
    for path in COMMON_LOCATIONS:
        if os.path.isfile(path):
            return path
    return None


def already_patched(content: str) -> bool:
    return "handle_dashboard_command" in content


def find_import_insertion_point(lines: list[str]) -> int:
    """Return index after the last import block."""
    last_import = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")) and not stripped.startswith("#"):
            last_import = i
    return last_import + 1


def find_run_polling_line(lines: list[str]) -> int:
    """Return index of the line containing run_polling() or run_until_disconnected()."""
    for i, line in enumerate(lines):
        if "run_polling" in line or "run_until_disconnected" in line:
            return i
    return -1


def patch(filepath: str) -> None:
    print(f"\nTarget file : {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()

    if already_patched(original):
        print("Already patched — nothing to do.")
        return

    # Backup
    backup = filepath + ".bak." + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(filepath, backup)
    print(f"Backup saved : {backup}")

    lines = original.splitlines(keepends=True)

    # 1. Insert import
    insert_at = find_import_insertion_point(lines)
    lines.insert(insert_at, IMPORT_LINE + "\n")
    print(f"Import added : line {insert_at + 1}")

    # 2. Insert handlers before run_polling (index shifted by +1 after import insert)
    run_line = find_run_polling_line(lines)
    if run_line == -1:
        print(
            "WARNING: could not find run_polling() — add these lines manually "
            "before application.run_polling():"
        )
        for h in HANDLER_LINES:
            print(f"  {h.strip()}")
    else:
        for i, handler in enumerate(reversed(HANDLER_LINES)):
            lines.insert(run_line, handler + "\n")
        print(f"Handlers added : before line {run_line + 1} ({lines[run_line + len(HANDLER_LINES)].strip()})")

    # Write patched file
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("\nPatch complete. Restart hetzy_phd.py to activate /dashboard command.")
    print(f"  Undo with: cp {backup} {filepath}")


def main():
    if len(sys.argv) > 1:
        target = sys.argv[1]
        if not os.path.isfile(target):
            print(f"ERROR: file not found: {target}")
            sys.exit(1)
    else:
        print("No path given — searching common locations...")
        target = find_file()
        if not target:
            print(
                "hetzy_phd.py not found in any standard location.\n"
                "Pass the path explicitly:\n"
                "  python3 hetzy_phd_patch.py /full/path/to/hetzy_phd.py"
            )
            sys.exit(1)
        print(f"Found: {target}")

    patch(target)


if __name__ == "__main__":
    main()
