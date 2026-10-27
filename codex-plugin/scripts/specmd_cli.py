#!/usr/bin/env python3
"""Run the SpecMD CLI from the plugin, with its vendored dependencies.

Used by the /specmd:init command; standard library only until the bootstrap
finds Python 3.11+.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specmd_bootstrap  # noqa: E402

if not specmd_bootstrap.ensure(__file__):
    print("SpecMD precisa de Python 3.11 ou superior; defina SPECMD_PYTHON com o caminho do interpretador.", file=sys.stderr)
    raise SystemExit(2)

from specmd.cli import main  # noqa: E402

raise SystemExit(main())
