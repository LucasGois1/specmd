#!/usr/bin/env python3
"""Bootstrap the bundled source with the interpreter chosen by SPECMD_PYTHON."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from specmd.claude import run_hook

raise SystemExit(run_hook())
