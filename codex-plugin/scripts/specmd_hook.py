#!/usr/bin/env python3
"""Hook entry point shared by Codex and Claude Code (hooks/hooks.json).

Claude Code always loads hooks/hooks.json from a plugin root, so a second
host-specific declaration there would run twice; the translator is shared.
Standard library only until the bootstrap finds Python 3.11+.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specmd_bootstrap  # noqa: E402

if not specmd_bootstrap.ensure(__file__):
    try:
        event = json.load(sys.stdin).get("hook_event_name")
    except (ValueError, AttributeError):
        event = None
    message = {"systemMessage": "SpecMD: install Python 3.11 or later (or set SPECMD_PYTHON) to enable the checks."}
    print(json.dumps(message if event == "SessionStart" else {}, ensure_ascii=False))
    raise SystemExit(0)

from specmd.hooks import run_hook  # noqa: E402

raise SystemExit(run_hook())
