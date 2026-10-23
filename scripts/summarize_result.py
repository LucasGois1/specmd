#!/usr/bin/env python3
"""Print a short summary of a SpecMD JSON result read from stdin.

Used by the Makefile shortcuts; the summary is an observation, not approval.
"""
import json
import sys


def main() -> int:
    try:
        result = json.load(sys.stdin)
    except ValueError:
        print("A saída do SpecMD não é JSON válido.", file=sys.stderr)
        return 2
    if "decisions" in result:
        for row in result["decisions"]:
            state = "válida" if row.get("valid") else "inválida ou substituída"
            print(f"- {row.get('decision')} por {row.get('reviewer')} em {row.get('issued_at')} ({state})")
        result = result.get("current", {})
    print(f"{result.get('status')}; may_complete={str(result.get('may_complete')).lower()}")
    for finding in result.get("findings", []):
        print(f"- {finding.get('message')}")
    limitations = result.get("limitations")
    for note in limitations if isinstance(limitations, list) else []:
        print(f"  ({note})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
