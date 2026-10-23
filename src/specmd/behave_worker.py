"""Private JSON bridge: execute in-memory Gherkin with real Behave steps.

No .feature file is read or generated. Project Behave configuration, filters,
dry-run options, and environment.py hooks are deliberately not loaded. This is
process isolation, not a sandbox for hostile Python step definitions.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import re
import sys
import tempfile

from behave.configuration import Configuration
from behave.model import Rule, ScenarioOutline
from behave.parser import parse_feature
from behave.runner import ModelRunner, load_step_modules
from behave.runner_util import make_undefined_step_snippet
from behave.step_registry import registry


SCENARIO_ID = re.compile(r"SMD-(?:[A-Za-z0-9]+-)*SCN-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


def _step(step):
    """Step status with the text, error tail or ready-to-paste snippet for feedback."""
    item = {"status": step.status.name, "line": step.line, "text": f"{step.keyword.strip()} {step.name}"}
    if step.status.name == "failed" and getattr(step, "error_message", None):
        item["error"] = "\n".join(str(step.error_message).strip().splitlines()[-15:])
    elif step.status.name == "undefined":
        item["snippet"] = make_undefined_step_snippet(step)
    return item


def _identity(scenario):
    identities = [str(tag) for tag in scenario.tags if SCENARIO_ID.fullmatch(str(tag))]
    if len(identities) != 1:
        raise ValueError("Cenário deve ter exatamente uma identidade estável.")
    return identities[0]


def _concrete(container):
    for item in container.run_items:
        if isinstance(item, Rule):
            yield from _concrete(item)
        elif isinstance(item, ScenarioOutline):
            concrete = iter(item.scenarios)
            for example_index, example in enumerate(item.examples, 1):
                for row_index, _row in enumerate(example.table.rows, 1):
                    scenario = next(concrete)
                    yield scenario, f"{_identity(item)}:row:{example_index}:{row_index}"
        else:
            yield item, _identity(item)


def execute(root: Path, steps: str, payload: dict) -> dict:
    result = {"schema": 1, "mode": "real", "dry_run": False, "engine_failed": True,
              "scenarios": [], "passed": False}
    if not isinstance(payload, dict) or type(payload.get("schema")) is not int or payload["schema"] != 1:
        raise ValueError("Entrada deve ser um objeto JSON schema=1.")
    expected = payload.get("expected_scenarios")
    features_input = payload.get("features")
    if not isinstance(expected, list) or not expected or not isinstance(features_input, list) or not features_input:
        raise ValueError("Zero cenários/blocos não fornece evidência de execução.")
    step_path = Path(steps)
    if step_path.is_absolute() or ".." in step_path.parts:
        raise ValueError("Diretório steps deve ser relativo ao projeto.")
    candidate = root
    for part in step_path.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError("Diretório steps não pode atravessar links simbólicos.")
    candidate.resolve().relative_to(root)
    if not candidate.is_dir():
        raise ValueError("Diretório steps não existe.")
    if any(path.is_symlink() for path in candidate.glob("*.py")):
        raise ValueError("Definições de passo não podem ser links simbólicos.")
    features, origins = [], []
    for item in features_input:
        path, block, line, content = item["path"], item["block"], item["line"], item["content"]
        if (not isinstance(path, str) or type(block) is not int or block < 1
                or type(line) is not int or line < 1 or not isinstance(content, str)):
            raise ValueError("Bloco sem origem/conteúdo válido.")
        feature = parse_feature("\n" * (line - 1) + content, filename=f"{path}#block-{block}")
        if feature is None:
            raise ValueError("Bloco sem funcionalidade Gherkin.")
        features.append(feature)
        origins.extend((scenario, identity, path, block) for scenario, identity in _concrete(feature))
    expected_by_id = {item["id"]: item for item in expected}
    if len(expected_by_id) != len(expected) or len({item[1] for item in origins}) != len(origins):
        raise ValueError("Identidades duplicadas no contrato ou parser.")
    if {item[1] for item in origins} != set(expected_by_id):
        raise ValueError("Instâncias do parser não correspondem ao inventário esperado.")
    for scenario, identity, path, block in origins:
        wanted = expected_by_id[identity]
        if any(wanted.get(key) != value for key, value in (("path", path), ("block", block), ("line", scenario.line))):
            raise ValueError("Origem do cenário diverge da inspeção.")
    sys.path[:0] = [str(root), str(candidate)]
    registry.clear()
    load_step_modules([str(candidate)])
    configuration = Configuration([], load_config=False)
    configuration.reporters = []
    configuration.dry_run = False
    runner = ModelRunner(configuration, features=features, step_registry=registry)
    failed = runner.run_model()
    result["engine_failed"] = bool(failed)
    for scenario, identity, path, block in origins:
        statuses = [_step(step) for step in scenario.all_steps]
        result["scenarios"].append({"id": identity, "status": scenario.status.name,
                                    "path": path, "block": block, "line": scenario.line,
                                    "steps_executed": sum(step["status"] in {"passed", "failed"} for step in statuses),
                                    "steps": statuses})
    result["passed"] = (not failed and bool(result["scenarios"])
                        and all(item["status"] == "passed" and item["steps"]
                                and all(step["status"] == "passed" for step in item["steps"])
                                for item in result["scenarios"]))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--steps", default="tests/steps")
    args = parser.parse_args()
    output = io.StringIO()
    try:
        payload = json.load(sys.stdin)
        with tempfile.TemporaryDirectory(prefix="specmd-bytecode-") as bytecode_directory:
            # Timestamp/size-valid .pyc files can otherwise execute old code even
            # when the current source hash changed. -B alone only stops writes.
            # A fresh cache prefix prevents reading the project's old bytecode.
            sys.pycache_prefix = bytecode_directory
            sys.dont_write_bytecode = True
            with redirect_stdout(output), redirect_stderr(output):
                report = execute(args.root.resolve(strict=True), args.steps, payload)
    except Exception as error:
        report = {"schema": 1, "mode": "real", "dry_run": False, "engine_failed": True,
                  "scenarios": [], "passed": False, "error": f"{type(error).__name__}: {error}"}
    # Step stdout is discarded to keep the protocol intact; failing steps carry
    # their own error tail in the report.
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
