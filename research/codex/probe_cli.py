#!/usr/bin/env python3
"""Collect read-only CLI help/version evidence; never start a model session."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
binary = "/opt/codex/bin/codex"
commands = [
    [binary, "--version"],
    [binary, "plugin", "--help"],
    [binary, "plugin", "add", "--help"],
    [binary, "plugin", "marketplace", "add", "--help"],
    [binary, "app-server", "generate-json-schema", "--help"],
]
results = []
for command in commands:
    result = subprocess.run(command, cwd=root.parent.parent, text=True, capture_output=True, timeout=15)
    results.append({"command": command, "exit": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
evidence = {"observed_at_utc": datetime.now(timezone.utc).isoformat(), "scope": "Help/version only; no plugin installed, trust modified, credentials inspected, or model session started.", "commands": results}
(root / "evidence" / "cli-help.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
assert all(result["exit"] == 0 for result in results)
print("5 help/version commands completed; no plugin installed")
