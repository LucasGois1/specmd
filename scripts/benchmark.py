#!/usr/bin/env python3
"""Measure SpecMD's hook latency on a large synthetic repository.

The repository is generated once (Markdown documents with scenarios plus many
code files, committed to Git) and reused while its parameters do not change.
Each measurement starts the real hook entry point, as Claude Code does.

    python scripts/benchmark.py [--docs 5000] [--files 50000] [--repeat 5]
    python scripts/benchmark.py --rules 2000   # runs: every scenario vs only the affected ones
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

PLUGIN = Path(__file__).resolve().parents[1]
HOOK = PLUGIN / "scripts" / "specmd_hook.py"
LOCAL_STATE = ".specmd"
DOCUMENT = """# Area {area}, rule {index}

Explanation of rule {index}, as in real documentation.

## BEN-REQ-{index:05d} — Rule {index}

```gherkin
Feature: Rule {index}

  Scenario: Main case {index}
    Given a value {index}
    When the rule is applied
    Then the result is {index}

  Scenario: Alternative case {index}
    Given a value {index}
    When the rule is applied twice
    Then the result is {index}
```
"""


def generate(root: Path, docs: int, files: int) -> None:
    marker = root / ".bench.json"
    wanted = {"docs": docs, "files": files, "version": 1}
    if marker.is_file() and json.loads(marker.read_text()) == wanted:
        return
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for index in range(docs):
        area = index % 50
        path = root / "docs" / f"area-{area:02d}" / f"regra-{index:05d}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DOCUMENT.format(area=area, index=index), encoding="utf-8")
    for index in range(files):
        path = root / "src" / f"pkg{index % 200:03d}" / f"mod{index:05d}.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"VALUE = {index}\n\n\ndef value():\n    return VALUE\n", encoding="utf-8")
    (root / "specmd.toml").write_text("[run]\non_stop = true\n", encoding="utf-8")
    (root / ".gitignore").write_text(LOCAL_STATE + "/\n", encoding="utf-8")
    git = ["git", "-C", str(root), "-c", "user.name=bench", "-c", "user.email=bench@example.com"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "bench"], check=True)
    marker.write_text(json.dumps(wanted), encoding="utf-8")


RULE_STEPS = """import importlib

from behave import given, then, when


@given("the value {value:d}")
def given_value(context, value):
    context.value = value


@when("rule {index:d} is applied")
def apply_rule(context, index):
    module = importlib.import_module(f"rules.area_{index % 20:02d}")
    context.result = getattr(module, f"rule_{index:05d}")(context.value)


@then("the result is {expected:d}")
def check_result(context, expected):
    assert context.result == expected
"""


def generate_rules(root: Path, rules: int) -> None:
    """A project whose rules each live in their own function, with real steps."""
    marker = root / ".bench.json"
    wanted = {"rules": rules, "version": 1}
    if marker.is_file() and json.loads(marker.read_text()) == wanted:
        return
    if root.exists():
        shutil.rmtree(root)
    (root / "rules").mkdir(parents=True)
    (root / "rules" / "__init__.py").write_text("", encoding="utf-8")
    (root / "tests" / "steps").mkdir(parents=True)
    (root / "tests" / "steps" / "steps.py").write_text(RULE_STEPS, encoding="utf-8")
    documents: dict[int, list[str]] = {}
    modules: dict[int, list[str]] = {}
    for index in range(rules):
        area = index % 20
        documents.setdefault(area, []).append(
            f"## BEN-REQ-{index:05d} — Rule {index}\n\n```gherkin\nFeature: Rule {index}\n\n"
            f"  Scenario: Apply rule {index}\n    Given the value {index}\n    When rule {index} is applied\n"
            f"    Then the result is {index * 2}\n```\n")
        modules.setdefault(area, []).append(f"def rule_{index:05d}(value):\n    return value * 2\n")
    (root / "docs").mkdir()
    for area, sections in documents.items():
        (root / "docs" / f"area-{area:02d}.md").write_text(f"# Area {area}\n\n" + "\n".join(sections), encoding="utf-8")
        (root / "rules" / f"area_{area:02d}.py").write_text("\n\n".join(modules[area]), encoding="utf-8")
    (root / ".gitignore").write_text(LOCAL_STATE + "/\n", encoding="utf-8")
    (root / "specmd.toml").write_text("[run]\ntimeout = 3600\n", encoding="utf-8")
    git = ["git", "-C", str(root), "-c", "user.name=bench", "-c", "user.email=bench@example.com"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "bench"], check=True)
    marker.write_text(json.dumps(wanted), encoding="utf-8")


def run_cli(root: Path, *arguments: str) -> tuple[float, dict]:
    environment = {**os.environ, "SPECMD_PYTHON": sys.executable}
    start = time.perf_counter()
    completed = subprocess.run([sys.executable, str(PLUGIN / "scripts" / "specmd_cli.py"), "run", *arguments,
                                "--root", str(root)], env=environment, capture_output=True, text=True, timeout=7200)
    elapsed = time.perf_counter() - start
    return elapsed, json.loads(completed.stdout).get("run", {})


def execution_benchmark(root: Path, rules: int) -> list[dict]:
    generate_rules(root, rules)
    shutil.rmtree(root / LOCAL_STATE, ignore_errors=True)
    module = root / "rules" / "area_00.py"
    original = module.read_text(encoding="utf-8")
    rows = []

    def row(label: str, elapsed: float, run: dict) -> None:
        rows.append({"event": label, "ms": round(elapsed * 1000), "executed": run.get("scenarios"),
                     "unselected": run.get("unselected"), "passed": run.get("passed")})
        print(f"{label:<34} {elapsed * 1000:>8.0f} ms   {run.get('scenarios')} executed, "
              f"{run.get('unselected')} left out, passed={run.get('passed')}", flush=True)

    row("run (all, first time)", *run_cli(root))
    row("run (all)", *run_cli(root))
    try:
        module.write_text(original.replace("return value * 2", "return value * 2 + 0", 1), encoding="utf-8")
        row("run --affected (one function)", *run_cli(root, "--affected"))
        row("run --affected (no change)", *run_cli(root, "--affected"))
    finally:
        module.write_text(original, encoding="utf-8")
    return rows


def hook(root: Path, payload: dict) -> float:
    environment = {**os.environ, "CLAUDE_PROJECT_DIR": str(root), "SPECMD_PYTHON": sys.executable}
    start = time.perf_counter()
    completed = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), cwd=root,
                               env=environment, capture_output=True, text=True, timeout=300)
    elapsed = time.perf_counter() - start
    reply = json.loads(completed.stdout or "{}")
    if "SpecMD: check unavailable" in json.dumps(reply, ensure_ascii=False):
        raise RuntimeError(reply)
    return elapsed


def measure(label: str, action, repeat: int, prepare=None) -> dict:
    samples = []
    for _ in range(repeat):
        if prepare:
            prepare()
        samples.append(action())
    row = {"event": label, "p50_ms": round(statistics.median(samples) * 1000),
           "max_ms": round(max(samples) * 1000)}
    print(f"{label:<34} p50 {row['p50_ms']:>6} ms   max {row['max_ms']:>6} ms", flush=True)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docs", type=int, default=5000)
    parser.add_argument("--files", type=int, default=50000)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--root", type=Path, default=Path(tempfile.gettempdir()) / "specmd-bench")
    parser.add_argument("--json", type=Path, help="write the measurements to this file")
    parser.add_argument("--rules", type=int, default=0,
                        help="also measure runs with this many rules, each with one function and one scenario")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.rules:
        rules_root = root.with_name(root.name + "-regras")
        print(f"Runs: {rules_root} ({args.rules} rules)", flush=True)
        execution = execution_benchmark(rules_root, args.rules)
        if args.json:
            args.json.write_text(json.dumps({"rules": args.rules, "rows": execution}, indent=2) + "\n")
        return
    start = time.perf_counter()
    generate(root, args.docs, args.files)
    print(f"Repository: {root} ({args.docs} documents, {args.files} files; "
          f"preparado em {time.perf_counter() - start:.1f} s)", flush=True)
    shutil.rmtree(root / LOCAL_STATE, ignore_errors=True)

    document = root / "docs" / "area-00" / "regra-00000.md"
    original = document.read_text(encoding="utf-8")
    counter = iter(range(10**6))

    def edit_document() -> None:
        document.write_text(original + f"\nNota {next(counter)}.\n", encoding="utf-8")

    rows = [
        measure("SessionStart (estado vazio)", lambda: hook(root, {"hook_event_name": "SessionStart"}), 1,
                prepare=lambda: shutil.rmtree(root / LOCAL_STATE, ignore_errors=True)),
        measure("SessionStart", lambda: hook(root, {"hook_event_name": "SessionStart"}), args.repeat),
        measure("UserPromptSubmit", lambda: hook(root, {"hook_event_name": "UserPromptSubmit"}), args.repeat),
        measure("PostToolUse (Edit on code)", lambda: hook(
            root, {"hook_event_name": "PostToolUse", "tool_name": "Edit",
                   "tool_input": {"file_path": str(root / "src/pkg000/mod00000.py")}}), args.repeat),
        measure("PostToolUse (Bash)", lambda: hook(
            root, {"hook_event_name": "PostToolUse", "tool_name": "Bash"}), args.repeat),
        measure("PostToolUse (documento editado)", lambda: hook(
            root, {"hook_event_name": "PostToolUse", "tool_name": "Edit",
                   "tool_input": {"file_path": str(document)}}), args.repeat, prepare=edit_document),
        measure("Stop (no code change)", lambda: hook(root, {"hook_event_name": "Stop"}), args.repeat),
    ]
    document.write_text(original, encoding="utf-8")
    if args.json:
        args.json.write_text(json.dumps({"docs": args.docs, "files": args.files, "rows": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main()
