"""Run the scenarios embedded in Markdown through subprocess bridges, failing closed.

Each failing scenario comes back with the step, line and error message, so the
agent receives actionable feedback. Subprocess isolation is not a sandbox for
hostile project code.
"""

from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
from typing import Any

def _finding(kind: str, message: str, runner_id: str | None = None) -> dict:
    item = {"kind": kind, "message": message}
    if runner_id is not None:
        item["runner_id"] = runner_id
    return item


def _inside(root: Path, relative: str) -> Path:
    path = Path(relative)
    if not relative or path.is_absolute() or ".." in path.parts:
        raise ValueError("Caminhos do contrato devem ser relativos ao projeto.")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Caminhos de execução não podem atravessar links simbólicos.")
    current.resolve().relative_to(root)
    return current


def _document_scenarios(root: Path, document: Any, wip_tags: set[str]) -> list[dict]:
    """Expected scenarios of one inspected document, refusing a changed file."""
    if not isinstance(document, dict) or not isinstance(document.get("path"), str):
        raise ValueError("Documento inválido na inspeção.")
    relative = document["path"]
    if hashlib.sha256(_inside(root, relative).read_bytes()).hexdigest() != document.get("sha256"):
        raise ValueError("Documento mudou desde a inspeção: " + relative)
    scenarios = document.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("Documento sem registro de cenários: " + relative)
    expected = []
    for scenario in scenarios:
        valid = (isinstance(scenario, dict) and isinstance(scenario.get("id"), str) and scenario["id"]
                 and type(scenario.get("line")) is int and type(scenario.get("block")) is int)
        if not valid:
            raise ValueError("Cenário sem identidade ou origem válida: " + relative)
        if not wip_tags & set(scenario.get("tags", [])):
            expected.append({**scenario, "path": relative})
    return expected


_LANGUAGE_HEADER = re.compile(r"^\s*#\s*language\s*:", re.IGNORECASE)


def _with_language(feature: dict, language: str | None) -> dict:
    """Bridges read the language from the text: add the configured one where a line is free for it."""
    content, line = feature["content"], feature["line"]
    leading = [text for text in content.splitlines() if text.strip()][:1]
    if not language or (leading and _LANGUAGE_HEADER.match(leading[0])):
        return feature
    header = f"# language: {language}"
    if content.startswith("\n"):
        return {**feature, "content": header + content}
    if line > 1:
        return {**feature, "content": header + "\n" + content, "line": line - 1}
    return feature


def _features(root: Path, inspection: dict, wip_tags: set[str] = frozenset(),
              language: str | None = None) -> tuple[list[dict], list[dict]]:
    """Use the scanner's inventory-checked in-memory extraction; skip work-in-progress scenarios."""
    from .core import extract_features

    documents = inspection.get("documents")
    if not isinstance(documents, list):
        raise ValueError("Inspeção sem inventário documental válido.")
    expected = [item for document in documents for item in _document_scenarios(root, document, wip_tags)]
    if len({item["id"] for item in expected}) != len(expected):
        raise ValueError("Identidades de cenário duplicadas na inspeção.")
    features = []
    for feature in extract_features(root, inspection, language):
        # The core preserves source coordinates by padding its parser input.
        # Bridge protocol carries raw content + first-content line explicitly.
        padding = "\n" * (feature["line"] - 1)
        if not feature["content"].startswith(padding):
            raise ValueError("Extração de Gherkin sem o padding de origem esperado.")
        features.append(_with_language({**feature, "content": feature["content"][len(padding):]}, language))
    return features, expected


_DEFAULT_STEPS = ("tests/steps", "features/steps", "steps")


def default_runners(root: Path) -> list[dict]:
    """Without [[runners]] in specmd.toml, a Python steps directory implies a Behave runner."""
    for steps in _DEFAULT_STEPS:
        if (root / steps).is_dir() and not (root / steps).is_symlink():
            return [{"id": "python", "language": "python", "steps": steps}]
    return []


def _python_for(root: Path, runner: dict) -> str:
    """The project's interpreter when it can import behave, otherwise the plugin's."""
    candidates = [runner.get("python"), os.environ.get("VIRTUAL_ENV") and str(Path(os.environ["VIRTUAL_ENV"]) / "bin/python"),
                  str(root / ".venv/bin/python"), str(root / "venv/bin/python")]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate) if Path(candidate).is_absolute() else root / candidate
        if not path.is_file():
            continue
        try:
            probe = subprocess.run([str(path), "-c", "import behave"], capture_output=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if probe.returncode == 0:
            return str(path)
    return sys.executable


def _matches(path: str, patterns: list[str] | None) -> bool:
    return patterns is None or any(fnmatch.fnmatchcase(path, pattern) or Path(path).match(pattern) for pattern in patterns)


def _validate_report(report: Any, expected: list[dict], mode: str) -> list[dict]:
    if not isinstance(report, dict) or type(report.get("schema")) is not int or report["schema"] != 1:
        raise ValueError("Bridge deve retornar um objeto JSON schema=1.")
    if report.get("mode") != mode:
        raise ValueError("Modo de evidência do bridge não corresponde ao runner configurado.")
    if report.get("dry_run") is not False:
        raise ValueError("Bridge deve declarar dry_run=false; simulação de execução não comprova passos.")
    if report.get("engine_failed") is not False or report.get("passed") is not True:
        raise ValueError("O motor reportou falha ou não confirmou execução completa.")
    scenarios = report.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Execução sem cenários observados.")
    identities = [item.get("id") if isinstance(item, dict) else None for item in scenarios]
    if any(not isinstance(item, str) for item in identities) or len(set(identities)) != len(identities):
        raise ValueError("Execução retornou identidades ausentes ou duplicadas.")
    wanted = {item["id"]: item for item in expected}
    if set(identities) != set(wanted):
        raise ValueError("Cenários executados não correspondem exatamente ao contrato atribuído.")
    for observed in scenarios:
        origin = wanted[observed["id"]]
        if any(observed.get(key) != origin[key] for key in ("path", "block", "line")):
            raise ValueError("Origem observada diverge do contrato: " + observed["id"])
        if observed.get("status") != "passed":
            raise ValueError("Cenário não executado com sucesso: " + observed["id"])
        count = observed.get("steps_executed")
        if type(count) is not int or count < 1:
            raise ValueError("Cenário sem passos efetivamente executados: " + observed["id"])
        declared_count = origin.get("steps")
        if type(declared_count) is int and count < declared_count:
            raise ValueError("Execução não comprovou todos os passos declarados: " + observed["id"])
        steps = observed.get("steps")
        if steps is not None and (not isinstance(steps, list) or not steps or any(
            not isinstance(step, dict) or step.get("status") != "passed" for step in steps
        ) or len(steps) != count):
            raise ValueError("Passo pendente, indefinido, ignorado ou inconsistente: " + observed["id"])
    return scenarios


_VENDOR = Path(__file__).resolve().parents[2] / "vendor"


def _worker_environment(command: list[str]) -> dict | None:
    """The plugin's own interpreter finds behave in the vendored dependencies."""
    if command[0] != sys.executable or not _VENDOR.is_dir():
        return None
    existing = os.environ.get("PYTHONPATH")
    return {**os.environ, "PYTHONPATH": str(_VENDOR) + (os.pathsep + existing if existing else "")}


def _invoke(command: list[str], root: Path, payload: dict, timeout: float):
    process = subprocess.Popen(command, cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, shell=False, start_new_session=os.name == "posix",
                               env=_worker_environment(command))
    try:
        stdout, _stderr = process.communicate(json.dumps(payload, ensure_ascii=False), timeout=timeout)
        return process.returncode, stdout
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.communicate()
        raise


def _failure(observed: dict, origin: dict | None) -> dict:
    """Summarize a non-passing scenario with the steps that need attention."""
    steps = [step for step in observed.get("steps", []) if isinstance(step, dict) and step.get("status") != "passed"]
    return {
        "id": observed.get("id"), "name": (origin or {}).get("name"), "path": observed.get("path"),
        "line": observed.get("line"), "status": observed.get("status"),
        "steps": [{key: step[key] for key in ("text", "line", "status", "error", "snippet") if key in step}
                  for step in steps[:5]],
    }


@dataclass
class _Plan:
    """One configured runner and the scenarios assigned to it."""
    id: str
    language: str
    timeout: float
    command: list[str]
    selected: list[dict]
    measured: bool


_NO_RUNNER = ("Nenhum runner para executar os cenários: crie os passos Python em tests/steps "
              "(ou features/steps) ou configure [[runners]] no specmd.toml; para Java e Go, veja adapters/.")


def _expected(root: Path, inspection: dict, config: dict, only: set[str] | None,
              result: dict) -> tuple[list[dict], list[dict]] | None:
    """Features and scenarios to run; None when nothing is demanded (already recorded as passed)."""
    features, expected = _features(root, inspection, set(config.get("wip_tags", ["wip"])), config.get("gherkin_language"))
    if not expected:
        if not any(document.get("scenarios") for document in inspection.get("documents", [])):
            raise ValueError("Nenhum cenário encontrado na documentação.")
        result["passed"] = True  # Only work-in-progress scenarios: nothing is demanded.
        return None
    if only is not None:
        result["unselected"] = sum(item["id"] not in only for item in expected)
        expected = [item for item in expected if item["id"] in only]
        if not expected:
            result["passed"] = True  # The change affects no scenario; the others already passed.
            return None
    return features, expected


def _runner_settings(runner: Any, ids: set[str]) -> tuple[str, str, float, list[str] | None]:
    if not isinstance(runner, dict):
        raise ValueError("Runner deve ser um mapa.")
    identifier, language = runner.get("id"), runner.get("language")
    if not isinstance(identifier, str) or not identifier.strip() or identifier in ids:
        raise ValueError("Runner deve ter identidade única não vazia.")
    if language not in {"python", "java", "go"}:
        raise ValueError("Linguagem de runner não suportada: " + str(language))
    timeout = runner.get("timeout", 60)
    if type(timeout) not in {int, float} or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Timeout do runner deve ser um número positivo finito.")
    patterns = runner.get("paths")
    if patterns is not None and (not isinstance(patterns, list) or not patterns or any(
        not isinstance(pattern, str) or not pattern for pattern in patterns
    )):
        raise ValueError("paths deve ser uma lista não vazia de padrões.")
    return identifier, language, timeout, patterns


def _runner_command(root: Path, runner: dict, language: str) -> tuple[list[str], bool]:
    """The runner's command and whether it is the packaged worker, which measures coverage."""
    command = runner.get("command")
    measured = command is None and language == "python"
    if measured:
        steps = runner.get("steps", "tests/steps")
        if not isinstance(steps, str):
            raise ValueError("steps deve ser um diretório relativo.")
        _inside(root, steps)
        # Resolve alongside this exact runner copy: a plugin bootstrap's
        # sys.path is not inherited by a fresh Python subprocess, and
        # -m could otherwise load a different editable installation.
        command = [_python_for(root, runner), str(Path(__file__).with_name("behave_worker.py")),
                   "--root", str(root), "--steps", steps]
    if not isinstance(command, list) or not command or any(not isinstance(arg, str) or not arg for arg in command):
        raise ValueError("Runner exige command como lista de argumentos, sem shell.")
    return command, measured


def _plans(root: Path, runners: Any, expected: list[dict]) -> list[_Plan]:
    """Assign each scenario to the first runner whose paths match it."""
    if not isinstance(runners, list) or not runners:
        raise ValueError(_NO_RUNNER)
    plans: list[_Plan] = []
    taken: set[str] = set()
    for runner in runners:
        identifier, language, timeout, patterns = _runner_settings(runner, {plan.id for plan in plans})
        command, measured = _runner_command(root, runner, language)
        selected = [item for item in expected if item["id"] not in taken and _matches(item["path"], patterns)]
        taken.update(item["id"] for item in selected)
        plans.append(_Plan(identifier, language, timeout, command, selected, measured))
    missing = sorted({item["path"] for item in expected if item["id"] not in taken})
    if missing:
        raise ValueError("Nenhum runner cobre os cenários de: " + ", ".join(missing[:5]))
    return [plan for plan in plans if plan.selected]


def _collect(report: Any, plan: _Plan, origins: dict, result: dict, row: dict) -> None:
    """Record observed scenarios, failures, bridge errors and coverage from one report."""
    observed = report.get("scenarios", []) if isinstance(report, dict) else []
    if isinstance(observed, list):
        row["observed_scenarios"] = observed
        for scenario in (item for item in observed if isinstance(item, dict)):
            result["scenarios"].append({**scenario, "runner_id": plan.id})
            if scenario.get("status") != "passed":
                result["failures"].append(_failure(scenario, origins.get(scenario.get("id"))))
    if isinstance(report, dict) and report.get("error"):
        result["findings"].append(_finding("runner_failed", str(report["error"]), plan.id))
    scope = report.get("coverage") if plan.measured and isinstance(report, dict) else None
    result["coverage"]["runners"][plan.id] = isinstance(scope, dict)
    if isinstance(scope, dict) and isinstance(scope.get("global"), dict):
        result["coverage"]["global"].append(scope["global"])


def _run_plan(root: Path, plan: _Plan, features: list[dict], origins: dict, config: dict, result: dict) -> None:
    blocks = {(item["path"], item["block"]) for item in plan.selected}
    payload = {"schema": 1, "features": [item for item in features if (item["path"], item["block"]) in blocks],
               "expected_scenarios": plan.selected, "language": config.get("gherkin_language")}
    if plan.measured:
        payload["coverage"] = True
    row = {"id": plan.id, "language": plan.language, "passed": False,
           "expected_scenarios": [item["id"] for item in plan.selected]}
    try:
        exit_code, stdout = _invoke(plan.command, root, payload, plan.timeout)
        row["exit_code"] = exit_code
        try:
            report = json.loads(stdout)
        except (ValueError, TypeError) as error:
            raise ValueError("Bridge não retornou um único relatório JSON válido.") from error
        _collect(report, plan, origins, result, row)
        if exit_code != 0 and not result["failures"]:
            raise ValueError("Processo do runner terminou com código " + str(exit_code))
        if exit_code == 0:
            _validate_report(report, plan.selected, "real")
            row["passed"] = True
    except subprocess.TimeoutExpired:
        row["timed_out"] = True
        result["findings"].append(_finding("runner_timeout", "O processo do runner excedeu seu timeout.", plan.id))
    except (OSError, ValueError, TypeError) as error:
        result["findings"].append(_finding("runner_failed", str(error), plan.id))
    result["runners"].append(row)


def execute_project(root: Path, inspection: dict, config: dict, only: set[str] | None = None) -> dict:
    """Execute each expected scenario exactly once in an assigned runner.

    Python defaults to the packaged Behave worker; Java/Go require an explicit
    bridge command. Non-passing scenarios are listed in ``failures``. With
    ``only``, the other scenarios are left out and counted in ``unselected``;
    the packaged worker then also reports per-scenario coverage.
    """
    result = {"schema": 1, "runners": [], "scenarios": [], "failures": [], "passed": False, "findings": [],
              "unselected": 0, "coverage": {"runners": {}, "global": []}}
    try:
        root = Path(root).resolve(strict=True)
        if not root.is_dir() or not isinstance(config, dict):
            raise ValueError("Raiz/configuração inválida para execução.")
        planned = _expected(root, inspection, config, None if only is None else set(only), result)
        if planned is None:
            return result
        features, expected = planned
        plans = _plans(root, config["runners"] if "runners" in config else default_runners(root), expected)
    except (OSError, ValueError, TypeError) as error:
        result["findings"].append(_finding("runner_configuration_invalid", str(error)))
        return result
    origins = {item["id"]: item for item in expected}
    for plan in plans:
        _run_plan(root, plan, features, origins, config, result)
    result["passed"] = (not result["findings"] and not result["failures"] and len(result["scenarios"]) == len(expected)
                        and all(row["passed"] for row in result["runners"]))
    return result
