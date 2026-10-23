#!/usr/bin/env python3
"""Bootstrap the packaged source with the interpreter selected by SPECMD_PYTHON.

Codex and Claude Code share hooks/hooks.json and this entry point. Claude Code
always loads hooks/hooks.json from a plugin root, so a second host-specific
declaration there would run twice; the translator itself is shared.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from specmd.codex import run_hook

raise SystemExit(run_hook())
