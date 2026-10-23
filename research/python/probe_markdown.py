"""Real Markdown -> Behave model probe; requires the pinned research packages."""

import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from behave.configuration import Configuration
from behave.parser import parse_feature
from behave.runner import ModelRunner
from behave.step_registry import StepRegistry
from markdown_it import MarkdownIt

from probe_minimal import add, check_result, operands

BASE = Path(__file__).resolve().parent
FIXTURE = BASE / "addition.md"


def execute_case(name, selected, expected_ids, should_allow, tags=None):
    source = FIXTURE.read_text(encoding="utf-8")
    fences = [t for t in MarkdownIt().parse(source) if t.type == "fence" and t.info.strip() == "gherkin"]
    features = []
    origins = []
    for index in selected:
        token = fences[index]
        first_line = token.map[0] + 2
        uri = f"addition.md#block-{index + 1}"
        feature = parse_feature("\n" * (first_line - 1) + token.content, filename=uri)
        features.append(feature)
        origins.append({"uri": uri, "first_content_line": first_line})

    calls = []

    def calculate(context):
        calls.append(list(context.operands))
        context.result = add(*context.operands)

    registry = StepRegistry()
    registry.add_step_definition("given", "os números {a:d} e {b:d}", operands)
    registry.add_step_definition("when", "a soma for calculada", calculate)
    registry.add_step_definition("then", "o resultado deve ser {expected:d}", check_result)
    config_args = ["--tags", tags] if tags else []
    config = Configuration(config_args, load_config=False)
    config.reporters = []
    runner = ModelRunner(config, features=features, step_registry=registry)
    engine_failed = runner.run_model()
    observed = []
    for feature in features:
        for scenario in feature.scenarios:
            scenario_id = next((str(t) for t in scenario.tags if str(t).startswith("SMD-PY-SCN-")), None)
            observed.append({
                "id": scenario_id,
                "status": scenario.status.name,
                "uri": scenario.filename,
                "line": scenario.line,
                "source_line_matches": "Cenário:" in source.splitlines()[scenario.line - 1],
                "steps": [step.status.name for step in scenario.steps],
            })
    passed = [item["id"] for item in observed if item["status"] == "passed"]
    gate_allowed = (
        not engine_failed
        and bool(expected_ids)
        and sorted(passed) == sorted(expected_ids)
        and len(passed) == len(set(passed))
        and all(item["source_line_matches"] for item in observed)
        and len(calls) == len(expected_ids)
    )
    return {
        "case": name, "engine_failed": bool(engine_failed),
        "origins": origins, "required_scenario_ids": expected_ids,
        "observed_scenarios": observed, "application_calls": calls,
        "gate_allowed": gate_allowed, "expected_gate_allowed": should_allow,
        "expectation_met": gate_allowed == should_allow,
    }


def main():
    positive_ids = ["SMD-PY-SCN-001", "SMD-PY-SCN-002"]
    cases = [
        execute_case("two_blocks_pass", [0, 1], positive_ids, True),
        execute_case("assertion_failure", [2], ["SMD-PY-SCN-003"], False),
        execute_case("undefined_step", [3], ["SMD-PY-SCN-004"], False),
        execute_case("all_filtered", [0, 1], positive_ids, False, "@does_not_exist"),
    ]
    passed = all(item["expectation_met"] for item in cases)
    passed = passed and cases[0]["engine_failed"] is False
    passed = passed and cases[1]["engine_failed"] is True
    passed = passed and cases[2]["engine_failed"] is True
    result = {
        "status": "executed", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "versions": {"python": platform.python_version(), "behave": importlib.metadata.version("behave"),
                     "markdown_it_py": importlib.metadata.version("markdown-it-py")},
        "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in [Path(__file__), BASE / "probe_minimal.py"]},
        "feature_files_found": [str(p.relative_to(BASE)) for p in BASE.rglob("*.feature")],
        "cases": cases, "harness_passed": passed,
        "scope": "Research only: no human approval authority or protected production gate implemented.",
    }
    result["harness_passed"] = passed and not result["feature_files_found"]
    evidence = BASE / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"harness_passed": result["harness_passed"], "cases": cases}, ensure_ascii=False, indent=2))
    return 0 if result["harness_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
