#!/usr/bin/env python3
"""Run the repeatable local validation, without a model account or real approval."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".specmd/local/test-report.json")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sources = sorted((ROOT / "src/specmd").glob("*.py")) + sorted((ROOT / "tests").glob("test_*.py"))
    report = {
        "schema": 1, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": result.wasSuccessful(), "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "duration_seconds": round(time.monotonic() - started, 3),
        "real_llm_executed": False,
        "scope": "Documentation scanner, scenario execution with real Python BDD and hook lifecycle through simulated agent payloads. Native Java/Go tests are separate.",
        "source_sha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "tests_run": result.testsRun, "report": str(args.output)}, indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
