#!/usr/bin/env python3
"""Print a short summary of a SpecMD JSON result read from stdin (Makefile shortcuts)."""
import json
import sys


def main() -> int:
    try:
        result = json.load(sys.stdin)
    except ValueError:
        print("A saída do SpecMD não é JSON válido.", file=sys.stderr)
        return 2
    print(result.get("status"))
    for finding in result.get("findings", []):
        location = finding.get("path", "")
        if finding.get("line"):
            location += f":{finding['line']}"
        print(f"- {location + ': ' if location else ''}{finding.get('message')}")
    run = result.get("run")
    if isinstance(run, dict):
        freshness = "" if run.get("current", True) else " (desatualizada)"
        print(f"Última execução{freshness}: {run.get('scenarios')} de {run.get('expected')} cenários, "
              f"{len(run.get('failures', []))} sem passar.")
        for failure in run.get("failures", []):
            print(f"- {failure.get('path')}:{failure.get('line')} {failure.get('id')} ({failure.get('status')})")
        for finding in run.get("findings", []):
            print(f"- Execução: {finding.get('message')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
