#!/usr/bin/env python3
"""Build and exercise the real Godog runner; nonzero negative cases are expected.

This harness exits zero only when its observations match the matrix. That exit
code is distinct from the runner's and each case's completion gate.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
CONTRACT = "contract.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--go", default=os.environ.get("SPECM_GO_BIN", "go"))
    parser.add_argument("--offline", action="store_true", help="disable module proxy/checksum access")
    args = parser.parse_args()
    env = os.environ.copy()
    env["GOTOOLCHAIN"] = "local"
    # Repository-local caches: shared /tmp names could be pre-created by another user.
    cache = ROOT / ".cache"
    env.setdefault("GOCACHE", str(cache / "go-build"))
    env.setdefault("GOMODCACHE", str(cache / "go-mod"))
    env.setdefault("GOPATH", str(cache / "go-path"))
    if args.offline:
        env["GOPROXY"] = "off"
        env["GOSUMDB"] = "off"
    version = subprocess.run([args.go, "version"], env=env, text=True, capture_output=True, timeout=15)
    if version.returncode or not version.stdout.startswith("go version go"):
        print("O executável informado não é um SDK Go válido: " + version.stdout + version.stderr, file=sys.stderr)
        return 2
    build = ROOT / ".build"
    build.mkdir(exist_ok=True)
    executable = build / "specmd-go"
    subprocess.run([args.go, "build", "-mod=readonly", "-o", str(executable), "."], cwd=ROOT, env=env, check=True, timeout=120)
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    matrix = {
        "pass": {"gate": True, "observed": 2},
        "failure": {"gate": False, "observed": 1},
        "undefined": {"gate": False, "observed": 1},
        "pending": {"gate": False, "observed": 1},
        "filtered": {"gate": False, "observed": 0},
        "partial": {"gate": False, "observed": 1},
        "zero": {"gate": False, "observed": 0},
        "no-gherkin": {"gate": False, "observed": 0},
    }
    cases = []
    problems = []
    for case, expected in matrix.items():
        command = [str(executable), "-case", case]
        process = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=30)
        (evidence / f"{case}.stdout.json").write_text(process.stdout, encoding="utf-8")
        (evidence / f"{case}.stderr.log").write_text(process.stderr, encoding="utf-8")
        try:
            result = json.loads(process.stdout)
        except json.JSONDecodeError:
            problems.append(f"{case}: saída JSON inválida; processo={process.returncode}")
            continue
        ok = result["gate_allowed"] is expected["gate"] and len(result["observed_scenarios"]) == expected["observed"]
        ok = ok and process.returncode == (0 if expected["gate"] else 1)
        if not ok:
            problems.append(f"{case}: resultado divergente da matriz")
        cases.append({"case": case, "adapter_exit": process.returncode, "runner_exit": result["runner_exit"], "gate_allowed": result["gate_allowed"], "observed": len(result["observed_scenarios"]), "matches_expected": ok})
        print(json.dumps(cases[-1], ensure_ascii=False))

    # This is stdin support provided by our adapter, not a claim about Godog CLI.
    stdin_case = subprocess.run([str(executable), "-case", "pass", "-source", "-", "-uri", "contract-via-stdin.md"], cwd=ROOT, env=env, input=(ROOT / CONTRACT).read_text(encoding="utf-8"), text=True, capture_output=True, timeout=30)
    (evidence / "adapter-stdin.stdout.json").write_text(stdin_case.stdout, encoding="utf-8")
    (evidence / "adapter-stdin.stderr.log").write_text(stdin_case.stderr, encoding="utf-8")
    try:
        stdin_result = json.loads(stdin_case.stdout)
        stdin_ok = stdin_case.returncode == 0 and stdin_result["gate_allowed"] and len(stdin_result["observed_scenarios"]) == 2
    except json.JSONDecodeError:
        stdin_ok = False
    if not stdin_ok:
        problems.append("stdin do adaptador não passou")

    transport_cases = []
    for transport, expected_gate, expected_observed in (("vfs", True, 2), ("vfs-dir", False, 0)):
        process = subprocess.run([str(executable), "-case", "pass", "-transport", transport], cwd=ROOT, env=env, text=True, capture_output=True, timeout=30)
        (evidence / f"{transport}.stdout.json").write_text(process.stdout, encoding="utf-8")
        (evidence / f"{transport}.stderr.log").write_text(process.stderr, encoding="utf-8")
        result = json.loads(process.stdout)
        ok = result["gate_allowed"] is expected_gate and len(result["observed_scenarios"]) == expected_observed
        ok = ok and process.returncode == (0 if expected_gate else 1)
        transport_cases.append({"transport": transport, "runner_exit": result["runner_exit"], "adapter_exit": process.returncode, "gate_allowed": result["gate_allowed"], "observed": len(result["observed_scenarios"]), "matches_expected": ok})
        if not ok:
            problems.append(f"{transport}: resultado divergente da matriz")
        print(json.dumps(transport_cases[-1], ensure_ascii=False))

    feature_files = sorted(str(path.relative_to(ROOT)) for path in ROOT.rglob("*.feature"))
    if feature_files:
        problems.append("Arquivos .feature inesperados: " + ", ".join(feature_files))
    summary = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "go": version.stdout.strip(),
        "godog": "v0.16.0",
        "goldmark": "v1.7.13",
        "platform": platform.system() + "/" + platform.machine(),
        "source_sha256": hashlib.sha256((ROOT / CONTRACT).read_bytes()).hexdigest(),
        "cases": cases,
        "transport_cases": transport_cases,
        "adapter_stdin_passed": stdin_ok,
        "feature_files_found": feature_files,
        "harness_passed": not problems,
        "problems": problems,
        "source_files_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ("main.go", "system.go", CONTRACT, "empty.md", "reference.md", "go.mod", "go.sum", "run_experiment.py")},
        "scope": "Experimento técnico; não implementa aceite humano, proteção CI ou prova de completude de requisitos.",
    }
    (evidence / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for problem in problems:
        print(problem, file=sys.stderr)
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
