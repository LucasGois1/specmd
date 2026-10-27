"""Run every documented scenario, even when the documentation has gaps (pilot evaluation only).

    PYTHONPATH=src:vendor python run_scenarios.py <project>

`specmd run` refuses to run while a document lacks scenarios; as an evaluator
of a repository without the plugin, the pilot needs the scenarios that do
exist to run anyway. Prints one JSON line.
"""
import json
from pathlib import Path
import sys

from specmd.config import load_config
from specmd.core import inspect_project
from specmd.runner import execute_project

root = Path(sys.argv[1]).resolve()
inspection = inspect_project(root)
if inspection["status"] == "error" or not any(document.get("scenarios") for document in inspection.get("documents", [])):
    print(json.dumps({"status": "error" if inspection["status"] == "error" else "no_scenarios", "checks": 0,
                      "failures": 0, "gaps": inspection["status"] == "needs_scenarios"}))
    sys.exit()
try:
    execution = execute_project(root, inspection, load_config(root))
except ValueError as error:
    print(json.dumps({"status": "error", "checks": 0, "failures": 0, "message": str(error)}))
    sys.exit()
print(json.dumps({"status": "passing" if execution["passed"] else "failing", "checks": len(execution["scenarios"]),
                  "failures": len(execution["failures"]), "gaps": inspection["status"] == "needs_scenarios"}))
