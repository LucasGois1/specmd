"""Run Markdown contracts through explicit subprocess bridges, failing closed.

Runner reports are observations from executable code, not human acceptance or a
protected authority. External bridges and step definitions must be reviewed as
code; subprocess isolation does not make hostile project code trustworthy.
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


def _features(root: Path, inspection: dict) -> tuple[list[dict], list[dict]]:
    """Use the scanner's fresh, inventory-checked in-memory extraction."""
    from .core import extract_features

    documents = inspection.get("documents")
    if not isinstance(documents, list):
        raise ValueError("Inspeção sem inventário documental válido.")
    expected = []
    for document in documents:
        if not isinstance(document, dict):
            raise ValueError("Documento inválido na inspeção.")
        if document.get("kind") not in {"behavioral", "mixed"}:
            continue
        relative = document.get("path")
        if not isinstance(relative, str):
            raise ValueError("Documento sem caminho válido.")
        path = _inside(root, relative)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != document.get("sha256"):
            raise ValueError("Documento mudou desde a inspeção: " + relative)
        scenarios = document.get("scenarios")
        if not isinstance(scenarios, list):
            raise ValueError("Documento sem registro de cenários: " + relative)
        for scenario in scenarios:
            if not isinstance(scenario, dict) or not isinstance(scenario.get("id"), str) or not scenario["id"]:
                raise ValueError("Cenário sem identidade estável: " + relative)
            if type(scenario.get("line")) is not int or type(scenario.get("block")) is not int:
                raise ValueError("Cenário sem origem válida: " + relative)
            expected.append({**scenario, "path": relative})
    if len({item["id"] for item in expected}) != len(expected):
        raise ValueError("Identidades de cenário duplicadas na inspeção.")
    features = []
    extraction_inspection = inspection
    manifest = inspection.get("manifest")
    if isinstance(manifest, dict) and "traceability_sha256" in manifest:
        # Workflow extends the scanner manifest with traceability identity.
        # Extraction compares only the scanner's config+document manifest;
        # workflow independently checks the traceability snapshot as well.
        base_manifest = {key: value for key, value in manifest.items() if key != "traceability_sha256"}
        encoded = json.dumps(base_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        extraction_inspection = {**inspection, "manifest": base_manifest,
                                 "manifest_sha256": hashlib.sha256(encoded).hexdigest()}
    for feature in extract_features(root, extraction_inspection):
        # The core preserves source coordinates by padding its parser input.
        # Bridge protocol carries raw content + first-content line explicitly.
        padding = "\n" * (feature["line"] - 1)
        if not feature["content"].startswith(padding):
            raise ValueError("Extração de Gherkin sem o padding de origem esperado.")
        features.append({**feature, "content": feature["content"][len(padding):]})
    return features, expected


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


def execute_project(root: Path, inspection: dict, config: dict) -> dict:
    """Execute each expected instance exactly once in an assigned runner.

Python defaults to the packaged Behave worker. Java/Go require an explicit
bridge command. Mock bridges require evidence.allow_mock=true and always yield
simulated assurance, even when their protocol-level expectations pass.
    """
    result = {"schema": 1, "mode": "real", "assurance": "execution", "runners": [],
              "scenarios": [], "passed": False, "findings": []}
    findings = result["findings"]
    try:
        root = Path(root).resolve(strict=True)
        if not root.is_dir() or not isinstance(config, dict):
            raise ValueError("Raiz/configuração inválida para execução.")
        features, expected = _features(root, inspection)
        if not expected:
            raise ValueError("Nenhum cenário esperado; zero execução não é sucesso.")
        runners = config.get("runners")
        if not isinstance(runners, list) or not runners:
            raise ValueError("Configure ao menos um runner explícito.")
        evidence_config = config.get("evidence", {})
        if not isinstance(evidence_config, dict):
            raise ValueError("Configuração evidence deve ser um mapa.")
        normalized, ids = [], set()
        for runner in runners:
            if not isinstance(runner, dict):
                raise ValueError("Runner deve ser um mapa.")
            identifier, language = runner.get("id"), runner.get("language")
            if not isinstance(identifier, str) or not identifier.strip() or identifier in ids:
                raise ValueError("Runner deve ter identidade única não vazia.")
            ids.add(identifier)
            if language not in {"python", "java", "go", "mock"}:
                raise ValueError("Linguagem de runner não suportada: " + str(language))
            if language == "mock":
                if evidence_config.get("allow_mock") is not True:
                    raise ValueError("Runner mock exige evidence.allow_mock=true explicitamente.")
                result["mode"], result["assurance"] = "mock", "simulated"
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
                command = [sys.executable, str(Path(__file__).with_name("behave_worker.py")),
                           "--root", str(root), "--steps", steps]
            if not isinstance(command, list) or not command or any(not isinstance(arg, str) or not arg for arg in command):
                raise ValueError("Runner exige command como lista de argumentos, sem shell.")
            selected = [item for item in expected if _matches(item["path"], patterns)]
            normalized.append((identifier, language, timeout, command, selected))
        assigned = [item["id"] for _, _, _, _, items in normalized for item in items]
        if len(assigned) != len(set(assigned)):
            raise ValueError("Um cenário foi atribuído a mais de um runner.")
        if set(assigned) != {item["id"] for item in expected}:
            raise ValueError("Existem cenários sem runner atribuído.")
        if any(not items for _, _, _, _, items in normalized):
            raise ValueError("Runner sem cenários atribuídos; execução vazia é recusada.")
    except (OSError, ValueError, TypeError) as error:
        findings.append(_finding("runner_configuration_invalid", str(error)))
        return result

    for identifier, language, timeout, command, selected in normalized:
        mode = "mock" if language == "mock" else "real"
        selected_blocks = {(item["path"], item["block"]) for item in selected}
        payload = {"schema": 1, "features": [item for item in features if (item["path"], item["block"]) in selected_blocks],
                   "expected_scenarios": selected}
        row = {"id": identifier, "language": language, "mode": mode, "passed": False,
               "expected_scenarios": [item["id"] for item in selected]}
        try:
            exit_code, stdout = _invoke(command, root, payload, timeout)
            row["exit_code"] = exit_code
            try:
                report = json.loads(stdout)
            except (ValueError, TypeError) as error:
                raise ValueError("Bridge não retornou um único relatório JSON válido.") from error
            # Preserve useful failed observations but never let them grant pass.
            observed = report.get("scenarios", []) if isinstance(report, dict) else []
            if isinstance(observed, list):
                row["observed_scenarios"] = observed
                result["scenarios"].extend({**scenario, "runner_id": identifier, "mode": mode}
                                           for scenario in observed if isinstance(scenario, dict))
            if exit_code != 0:
                raise ValueError("Processo do runner terminou com código " + str(exit_code))
            _validate_report(report, selected, mode)
            row["passed"] = True
        except subprocess.TimeoutExpired:
            row["timed_out"] = True
            findings.append(_finding("runner_timeout", "O processo do runner excedeu seu timeout.", identifier))
        except (OSError, ValueError, TypeError) as error:
            findings.append(_finding("runner_failed", str(error), identifier))
        result["runners"].append(row)
    result["passed"] = not findings and len(result["scenarios"]) == len(expected) and all(row["passed"] for row in result["runners"])
    return result
