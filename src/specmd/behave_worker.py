"""Private JSON bridge: execute in-memory Gherkin with real Behave steps.

No .feature file is read or generated. Scenarios are matched to the expected
list by origin (path, block, line); parsed scenarios that are not expected,
such as work-in-progress ones, are skipped. environment.py next to the steps
directory is loaded; behave.ini and its filters are not. This is process
isolation, not a sandbox for hostile Python step definitions.

With "coverage" in the payload and Python 3.12+, each scenario also reports
the project code it executed (first line of each code object), the project
files it read and whether it started a process or opened a connection, whose
effects coverage cannot follow.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile

from behave.configuration import Configuration
from behave.model import Rule, Scenario, ScenarioOutline
from behave.parser import parse_feature
from behave.runner import ModelRunner, load_step_modules
from behave.runner_util import exec_file, make_undefined_step_snippet
from behave.step_registry import registry


def _step(step):
    """Step status with the text, error tail or ready-to-paste snippet for feedback."""
    item = {"status": step.status.name, "line": step.line, "text": f"{step.keyword.strip()} {step.name}"}
    if step.status.name == "failed" and getattr(step, "error_message", None):
        item["error"] = "\n".join(str(step.error_message).strip().splitlines()[-15:])
    elif step.status.name == "undefined":
        item["snippet"] = make_undefined_step_snippet(step)
    return item


# Code and files here are not the project's behaviour under test.
_OUTSIDE_PROJECT = frozenset({".git", ".specmd", ".venv", "venv", "node_modules", "__pycache__", "site-packages"})
_OPAQUE_EVENTS = frozenset({"subprocess.Popen", "os.system", "os.posix_spawn", "os.spawn", "os.exec",
                            "os.fork", "os.forkpty", "socket.connect"})


class Coverage:
    """Project code executed and files read, per scenario; None is outside any scenario."""

    def __init__(self, root: Path):
        self.root = str(root) + os.sep
        self.own = os.path.abspath(__file__)
        self.current = None
        self.scopes = {}
        self.paths = {}

    def start(self) -> bool:
        monitoring = getattr(sys, "monitoring", None)
        if monitoring is None:
            return False
        try:
            monitoring.use_tool_id(monitoring.COVERAGE_ID, "specmd")
        except ValueError:
            return False
        monitoring.register_callback(monitoring.COVERAGE_ID, monitoring.events.PY_START, self._started)
        monitoring.set_events(monitoring.COVERAGE_ID, monitoring.events.PY_START)
        sys.addaudithook(self._audited)
        return True

    def enter(self, key):
        self.current = key
        sys.monitoring.restart_events()

    def _scope(self):
        return self.scopes.setdefault(self.current, {"code": set(), "files": set(), "opaque": False})

    def _relative(self, name):
        if name not in self.paths:
            relative = None
            if isinstance(name, str) and name and not name.startswith("<"):
                absolute = os.path.normpath(os.path.join(self.root, name))
                if absolute.startswith(self.root) and absolute != self.own:
                    candidate = absolute[len(self.root):].replace(os.sep, "/")
                    if not set(candidate.split("/")[:-1]) & _OUTSIDE_PROJECT:
                        relative = candidate
            self.paths[name] = relative
        return self.paths[name]

    def _started(self, code, _offset):
        relative = self._relative(code.co_filename)
        if relative is not None:
            self._scope()["code"].add((relative, code.co_firstlineno))
        return sys.monitoring.DISABLE

    def _audited(self, event, arguments):
        try:
            if event in _OPAQUE_EVENTS:
                self._scope()["opaque"] = True
            elif event == "open" and _reads(arguments):
                relative = self._relative(os.fsdecode(arguments[0]))
                if relative is not None and not relative.endswith((".py", ".pyc")):
                    self._scope()["files"].add(relative)
        except Exception:  # noqa: BLE001 - an audit hook must never break the scenario
            pass

    def report(self, key):
        scope = self.scopes.get(key, {"code": set(), "files": set(), "opaque": False})
        return {"code": sorted([path, line] for path, line in scope["code"]),
                "files": sorted(scope["files"]), "opaque": scope["opaque"]}


def _reads(arguments) -> bool:
    if not arguments or not isinstance(arguments[0], (str, bytes, os.PathLike)):
        return False
    mode = arguments[1] if len(arguments) > 1 else None
    if isinstance(mode, str):
        return not set(mode) & set("wax")
    flags = arguments[2] if len(arguments) > 2 else None
    return isinstance(flags, int) and flags & os.O_ACCMODE == os.O_RDONLY


def _attribute_scenarios(coverage: Coverage, identities: dict) -> None:
    """Run each scenario, its background and its hooks inside its own coverage scope."""
    run = Scenario.run

    def scoped(scenario, *arguments, **options):
        coverage.enter(identities.get(id(scenario)))
        try:
            return run(scenario, *arguments, **options)
        finally:
            coverage.enter(None)

    Scenario.run = scoped


def _concrete(container):
    for item in container.run_items:
        if isinstance(item, Rule):
            yield from _concrete(item)
        elif isinstance(item, ScenarioOutline):
            yield from item.scenarios
        else:
            yield item


def execute(root: Path, steps: str, payload: dict) -> dict:
    result = {"schema": 1, "mode": "real", "dry_run": False, "engine_failed": True,
              "scenarios": [], "passed": False}
    if not isinstance(payload, dict) or type(payload.get("schema")) is not int or payload["schema"] != 1:
        raise ValueError("The input must be a JSON object with schema=1.")
    expected = payload.get("expected_scenarios")
    features_input = payload.get("features")
    if not isinstance(expected, list) or not expected or not isinstance(features_input, list) or not features_input:
        raise ValueError("Zero scenarios or blocks prove no run.")
    step_path = Path(steps)
    if step_path.is_absolute() or ".." in step_path.parts:
        raise ValueError("The steps directory must be relative to the project.")
    candidate = root
    for part in step_path.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError("The steps directory cannot cross symbolic links.")
    candidate.resolve().relative_to(root)
    if not candidate.is_dir():
        raise ValueError("The steps directory does not exist.")
    if any(path.is_symlink() for path in candidate.glob("*.py")):
        raise ValueError("Step definitions cannot be symbolic links.")
    features, parsed, origins = [], [], []
    for item in features_input:
        path, block, line, content = item["path"], item["block"], item["line"], item["content"]
        if (not isinstance(path, str) or type(block) is not int or block < 1
                or type(line) is not int or line < 1 or not isinstance(content, str)):
            raise ValueError("Block without a valid origin or content.")
        feature = parse_feature("\n" * (line - 1) + content, language=payload.get("language"),
                                filename=f"{path}#block-{block}")
        if feature is None:
            raise ValueError("Block without a Gherkin feature.")
        features.append(feature)
        parsed.extend((scenario, path, block) for scenario in _concrete(feature))
    expected_by_origin = {(item["path"], item["block"], item["line"]): item for item in expected}
    if len(expected_by_origin) != len(expected):
        raise ValueError("Duplicate origins in the expected inventory.")
    for scenario, path, block in parsed:
        wanted = expected_by_origin.get((path, block, scenario.line))
        if wanted is None:
            scenario.mark_skipped()
        else:
            origins.append((scenario, wanted["id"], path, block))
    if len(origins) != len(expected):
        raise ValueError("The parser's scenarios do not match the expected inventory.")
    coverage = Coverage(root) if payload.get("coverage") is True else None
    if coverage is not None and coverage.start():
        _attribute_scenarios(coverage, {id(scenario): identity for scenario, identity, _, _ in origins})
    else:
        coverage = None
    sys.path[:0] = [str(root), str(candidate)]
    registry.clear()
    load_step_modules([str(candidate)])
    configuration = Configuration([], load_config=False)
    configuration.reporters = []
    configuration.dry_run = False
    runner = ModelRunner(configuration, features=features, step_registry=registry)
    environment = candidate.parent / "environment.py"
    if environment.is_file() and not environment.is_symlink():
        exec_file(str(environment), runner.hooks)
    failed = runner.run_model()
    result["engine_failed"] = bool(failed)
    for scenario, identity, path, block in origins:
        statuses = [_step(step) for step in scenario.all_steps]
        result["scenarios"].append({"id": identity, "status": scenario.status.name,
                                    "path": path, "block": block, "line": scenario.line,
                                    "steps_executed": sum(step["status"] in {"passed", "failed"} for step in statuses),
                                    "steps": statuses})
        if coverage is not None:
            result["scenarios"][-1]["coverage"] = coverage.report(identity)
    if coverage is not None:
        result["coverage"] = {"global": coverage.report(None)}
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
