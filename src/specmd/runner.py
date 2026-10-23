"""Run the scenarios embedded in Markdown through subprocess bridges, failing closed.

Each failing scenario comes back with the step, line and error message, so the
agent receives actionable feedback. Subprocess isolation is not a sandbox for
hostile project code.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import math
import os
from pathlib import Path
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


def _features(root: Path, inspection: dict, wip_tags: set[str] = frozenset()) -> tuple[list[dict], list[dict]]:
    """Use the scanner's inventory-checked in-memory extraction; skip work-in-progress scenarios."""
    from .core import extract_features

    documents = inspection.get("documents")
    if not isinstance(documents, list):
        raise ValueError("Inspeção sem inventário documental válido.")
    expected = [item for document in documents for item in _document_scenarios(root, document, wip_tags)]
    if len({item["id"] for item in expected}) != len(expected):
        raise ValueError("Identidades de cenário duplicadas na inspeção.")
    features = []
    for feature in extract_features(root, inspection):
        # The core preserves source coordinates by padding its parser input.
        # Bridge protocol carries raw content + first-content line explicitly.
        padding = "\n" * (feature["line"] - 1)
        if not feature["content"].startswith(padding):
            raise ValueError("Extração de Gherkin sem o padding de origem esperado.")
        features.append({**feature, "content": feature["content"][len(padding):]})
    return features, expected


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


def _invoke(command: list[str], root: Path, payload: dict, timeout: float):
    process = subprocess.Popen(command, cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, shell=False, start_new_session=os.name == "posix")
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


def execute_project(root: Path, inspection: dict, config: dict) -> dict:
    """Execute each expected scenario exactly once in an assigned runner.

    Python defaults to the packaged Behave worker; Java/Go require an explicit
    bridge command. Non-passing scenarios are listed in ``failures``.
    """
    result = {"schema": 1, "runners": [], "scenarios": [], "failures": [], "passed": False, "findings": []}
    findings = result["findings"]
    try:
        root = Path(root).resolve(strict=True)
        if not root.is_dir() or not isinstance(config, dict):
            raise ValueError("Raiz/configuração inválida para execução.")
        features, expected = _features(root, inspection, set(config.get("wip_tags", ["wip"])))
        if not expected:
            if any(document.get("scenarios") for document in inspection.get("documents", [])):
                result["passed"] = True  # Only work-in-progress scenarios: nothing is demanded.
                return result
            raise ValueError("Nenhum cenário encontrado na documentação.")
        runners = config.get("runners")
        if not isinstance(runners, list) or not runners:
            raise ValueError("Configure ao menos um runner em specmd.toml.")
        normalized, ids = [], set()
        for runner in runners:
            if not isinstance(runner, dict):
                raise ValueError("Runner deve ser um mapa.")
            identifier, language = runner.get("id"), runner.get("language")
            if not isinstance(identifier, str) or not identifier.strip() or identifier in ids:
                raise ValueError("Runner deve ter identidade única não vazia.")
            ids.add(identifier)
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
            command = runner.get("command")
            if command is None and language == "python":
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
            taken = {item["id"] for _, _, _, _, items in normalized for item in items}
            selected = [item for item in expected if item["id"] not in taken and _matches(item["path"], patterns)]
            normalized.append((identifier, language, timeout, command, selected))
        assigned = {item["id"] for _, _, _, _, items in normalized for item in items}
        missing = sorted({item["path"] for item in expected if item["id"] not in assigned})
        if missing:
            raise ValueError("Nenhum runner cobre os cenários de: " + ", ".join(missing[:5]))
        normalized = [entry for entry in normalized if entry[4]]
    except (OSError, ValueError, TypeError) as error:
        findings.append(_finding("runner_configuration_invalid", str(error)))
        return result

    origins = {item["id"]: item for item in expected}
    for identifier, language, timeout, command, selected in normalized:
        selected_blocks = {(item["path"], item["block"]) for item in selected}
        payload = {"schema": 1, "features": [item for item in features if (item["path"], item["block"]) in selected_blocks],
                   "expected_scenarios": selected, "language": config.get("gherkin_language")}
        row = {"id": identifier, "language": language, "passed": False,
               "expected_scenarios": [item["id"] for item in selected]}
        try:
            exit_code, stdout = _invoke(command, root, payload, timeout)
            row["exit_code"] = exit_code
            try:
                report = json.loads(stdout)
            except (ValueError, TypeError) as error:
                raise ValueError("Bridge não retornou um único relatório JSON válido.") from error
            observed = report.get("scenarios", []) if isinstance(report, dict) else []
            if isinstance(observed, list):
                row["observed_scenarios"] = observed
                for scenario in observed:
                    if not isinstance(scenario, dict):
                        continue
                    result["scenarios"].append({**scenario, "runner_id": identifier})
                    if scenario.get("status") != "passed":
                        result["failures"].append(_failure(scenario, origins.get(scenario.get("id"))))
            if isinstance(report, dict) and report.get("error"):
                findings.append(_finding("runner_failed", str(report["error"]), identifier))
            if exit_code != 0 and not result["failures"]:
                raise ValueError("Processo do runner terminou com código " + str(exit_code))
            if exit_code == 0:
                _validate_report(report, selected, "real")
                row["passed"] = True
        except subprocess.TimeoutExpired:
            row["timed_out"] = True
            findings.append(_finding("runner_timeout", "O processo do runner excedeu seu timeout.", identifier))
        except (OSError, ValueError, TypeError) as error:
            findings.append(_finding("runner_failed", str(error), identifier))
        result["runners"].append(row)
    result["passed"] = (not findings and not result["failures"] and len(result["scenarios"]) == len(expected)
                        and all(row["passed"] for row in result["runners"]))
    return result
