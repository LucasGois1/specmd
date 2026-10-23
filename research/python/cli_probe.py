"""Probe the stock Behave CLI with literal text and stdin; no .feature files."""

import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = (
        "# language: pt\nFuncionalidade: Entrada textual\n"
        "  Cenário: Exemplo\n    Dado algo\n"
    )
    observations = []
    with tempfile.TemporaryDirectory(prefix="specmd-python-cli-") as directory:
        cases = [
            ("literal_argument", [source], None),
            ("stdin_default", [], source),
            ("stdin_dash", ["-"], source),
        ]
        for name, arguments, stdin in cases:
            command = [sys.executable, "-m", "behave", *arguments]
            completed = subprocess.run(
                command, input=stdin, text=True, capture_output=True,
                cwd=directory, timeout=10, check=False,
            )
            observations.append({
                "case": name,
                "command": ["python3", "-m", "behave", *arguments],
                "stdin_supplied": stdin is not None,
                "engine_cli_exit_status": completed.returncode,
                "stdout": completed.stdout.replace(directory, "<TMPDIR>"),
                "stderr": completed.stderr.replace(directory, "<TMPDIR>"),
                "feature_files_after": [
                    str(path.relative_to(directory))
                    for path in Path(directory).rglob("*.feature")
                ],
            })
    expected = all(
        item["engine_cli_exit_status"] != 0 and not item["feature_files_after"]
        for item in observations
    )
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine": "behave",
        "engine_version": version("behave"),
        "scope": "stock CLI, empty working directory, literal argument and stdin",
        "sanitization": "temporary directory replaced with <TMPDIR>",
        "observations": observations,
        "harness_expectations_met": expected,
        "harness_exit_status": 0 if expected else 1,
        "limitation": (
            "These failures do not exhaust custom-runner configurations or prove "
            "that no CLI extension can accept text. They record these exact attempts."
        ),
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return report["harness_exit_status"]


if __name__ == "__main__":
    raise SystemExit(main())
