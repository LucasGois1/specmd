"""Read-only inspection of opt-in Markdown contracts.

Parsing is deliberately separate from human approval and runtime evidence.
This increment never authorizes task completion and never executes scenarios.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tomllib
from typing import Any

from behave.model import ScenarioOutline
from behave.parser import ParserError, parse_feature
from markdown_it import MarkdownIt
import yaml
from yaml.constructor import ConstructorError


_PRUNED_DIRECTORIES = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "target",
    "__pycache__", ".specmd", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "build", "dist",
})
_MARKDOWN_SUFFIXES = frozenset({".md", ".markdown"})
_KINDS = frozenset({"behavioral", "reference", "mixed"})
_REQUIREMENT_ID = re.compile(
    r"SMD-(?:[A-Za-z0-9]+-)*REQ-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*"
)
_SCENARIO_ID = re.compile(
    r"SMD-(?:[A-Za-z0-9]+-)*SCN-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*"
)
_REQUIREMENT_HEADING = re.compile(
    r"^(SMD-(?:[A-Za-z0-9]+-)*REQ-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)"
    r"(?=$|\s|[—–:])"
)


class _UniqueSafeLoader(yaml.SafeLoader):
    """Safe YAML with duplicate mapping keys rejected, including merges."""

    def construct_mapping(self, node: Any, deep: bool = False) -> dict:
        if not isinstance(node, yaml.MappingNode):
            raise ConstructorError(None, None, "Esperado um mapa YAML", node.start_mark)
        self.flatten_mapping(node)
        result: dict = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in result
            except TypeError as exc:
                raise ConstructorError(
                    "Ao ler um mapa", node.start_mark,
                    "Chave YAML não pode ser usada como chave de mapa", key_node.start_mark,
                ) from exc
            if duplicate:
                raise ConstructorError(
                    "Ao ler um mapa", node.start_mark,
                    f"Chave YAML duplicada: {key!r}", key_node.start_mark,
                )
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def _finding(kind: str, message: str, path: str | None = None,
             line: int | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"kind": kind, "message": message}
    if path is not None:
        item["path"] = path
    if isinstance(line, int) and line > 0:
        item["line"] = line
    return item


def _result(status: str, may_complete: bool | None,
            findings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "protocol_version": 1,
        "stage": "completion",
        "status": status,
        "may_complete": may_complete,
        "manifest": None,
        "manifest_sha256": None,
        "documents": [],
        "findings": findings if findings is not None else [],
    }


def _read_regular_file(path: Path) -> bytes:
    """Read a regular file, rejecting final-component symlinks and replacements."""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise OSError("O caminho deve ser um arquivo regular, sem link simbólico")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise OSError("O arquivo mudou durante a abertura; repita a inspeção")
        chunks = []
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        current = path.lstat()
        signature = lambda value: (
            value.st_dev, value.st_ino, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns,
        )
        if signature(opened) != signature(after) or signature(after) != signature(current):
            raise OSError("O arquivo mudou durante a leitura; repita a inspeção")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _frontmatter(text: str, path: str,
                 findings: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        findings.append(_finding(
            "frontmatter_missing", "Documento sem frontmatter de classificação specmd.", path, 1,
        ))
        return None, text
    closing = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if closing is None:
        findings.append(_finding(
            "frontmatter_invalid", "Frontmatter YAML sem delimitador de fechamento.", path, 1,
        ))
        return None, text
    body = "\n" * (closing + 1) + "".join(lines[closing + 1:])
    try:
        metadata = yaml.load("".join(lines[1:closing]), Loader=_UniqueSafeLoader)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = mark.line + 2 if mark is not None else 1
        findings.append(_finding("frontmatter_invalid", str(exc), path, line))
        return None, body
    if not isinstance(metadata, dict) or not isinstance(metadata.get("specmd"), dict):
        findings.append(_finding(
            "metadata_invalid", "Frontmatter deve conter o mapa specmd.", path, 1,
        ))
        return None, body
    declared = metadata["specmd"]
    valid = True
    if type(declared.get("schema")) is not int or declared["schema"] != 1:
        findings.append(_finding("metadata_invalid", "specmd.schema deve ser o inteiro 1.", path, 1))
        valid = False
    document_id = declared.get("id")
    if not isinstance(document_id, str) or not document_id.strip() or document_id != document_id.strip():
        findings.append(_finding("metadata_invalid", "specmd.id deve ser texto não vazio, sem espaços externos.", path, 1))
        valid = False
    if not isinstance(declared.get("kind"), str) or declared["kind"] not in _KINDS:
        findings.append(_finding(
            "metadata_invalid", "specmd.kind deve ser behavioral, reference ou mixed.", path, 1,
        ))
        valid = False
    if declared.get("kind") == "reference":
        reason = declared.get("exemption_reason")
        if not isinstance(reason, str) or not reason.strip():
            findings.append(_finding(
                "metadata_invalid", "Documento reference exige exemption_reason não vazio.", path, 1,
            ))
            valid = False
    return declared if valid else None, body


def _inspect_document(data: bytes, path: str,
                      findings: list[dict[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "id": None,
        "kind": None,
        "requirements": [],
        "scenarios": [],
    }
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        findings.append(_finding("invalid_utf8", "Documento não contém UTF-8 válido.", path))
        return document
    metadata, body = _frontmatter(text, path, findings)
    if metadata is not None:
        document["id"] = metadata["id"]
        document["kind"] = metadata["kind"]
        if metadata["kind"] == "reference":
            document["exemption_reason"] = metadata["exemption_reason"]

    tokens = MarkdownIt().parse(body)
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or index + 1 >= len(tokens):
            continue
        inline = tokens[index + 1]
        title = "".join(child.content for child in inline.children or [])
        match = _REQUIREMENT_HEADING.match(title)
        if match:
            document["requirements"].append({
                "id": match.group(1), "line": token.map[0] + 1,
            })

    fences = [
        token for token in tokens
        if token.type == "fence" and token.info.strip().split(maxsplit=1)
        and token.info.strip().split(maxsplit=1)[0].casefold() == "gherkin"
    ]
    if document["kind"] in {"behavioral", "mixed"}:
        if not document["requirements"]:
            findings.append(_finding(
                "requirement_missing", "Documento comportamental deve declarar requisitos em cabeçalhos SMD-…-REQ-….", path,
            ))
        if not fences:
            findings.append(_finding(
                "gherkin_missing", "Documento comportamental sem bloco Gherkin.", path,
            ))

    for block, token in enumerate(fences, start=1):
        first_line = token.map[0] + 2
        try:
            feature = parse_feature("\n" * (first_line - 1) + token.content, filename=path)
        except ParserError as exc:
            findings.append(_finding(
                "gherkin_invalid", str(exc), path, getattr(exc, "line", first_line),
            ))
            continue
        except (LookupError, ValueError) as exc:
            findings.append(_finding("gherkin_invalid", str(exc), path, first_line))
            continue
        if feature is None:
            findings.append(_finding("gherkin_invalid", "Bloco sem funcionalidade Gherkin.", path, first_line))
            continue
        if getattr(feature, "rules", None):
            findings.append(_finding(
                "gherkin_unsupported", "Rule/Regra ainda não é suportada pelo scanner inicial.", path, feature.line,
            ))
        plain_scenarios = []
        for scenario in feature.scenarios:
            if isinstance(scenario, ScenarioOutline):
                findings.append(_finding(
                    "gherkin_unsupported", "Scenario Outline/Esquema do Cenário ainda não é suportado.", path, scenario.line,
                ))
            else:
                plain_scenarios.append(scenario)
        if not plain_scenarios:
            findings.append(_finding(
                "scenarios_missing", "Bloco sem cenários simples verificáveis pelo scanner inicial.", path, feature.line,
            ))
        for scenario in plain_scenarios:
            tags = {str(tag) for tag in feature.tags} | {str(tag) for tag in scenario.tags}
            scenario_ids = sorted({str(tag) for tag in scenario.tags if _SCENARIO_ID.fullmatch(str(tag))})
            if not scenario_ids:
                findings.append(_finding(
                    "scenario_id_missing", "Cenário exige uma tag SMD-…-SCN-… estável.", path, scenario.line,
                ))
            elif len(scenario_ids) != 1:
                findings.append(_finding(
                    "scenario_id_invalid", "Cenário deve ter exatamente uma identidade SMD-…-SCN-….", path, scenario.line,
                ))
            requirement_ids = sorted(tag for tag in tags if _REQUIREMENT_ID.fullmatch(tag))
            if not requirement_ids:
                findings.append(_finding(
                    "requirement_missing", "Cenário sem vínculo com requisito SMD-…-REQ-….", path, scenario.line,
                ))
            if not scenario.steps:
                findings.append(_finding(
                    "scenario_steps_missing", "Cenário sem passos não fornece comportamento verificável.", path, scenario.line,
                ))
            document["scenarios"].append({
                "id": scenario_ids[0] if len(scenario_ids) == 1 else None,
                "name": scenario.name,
                "line": scenario.line,
                "requirements": requirement_ids,
                "block": block,
                "steps": len(scenario.steps),
            })
    return document


def _validate_links(documents: list[dict[str, Any]], findings: list[dict[str, Any]]) -> None:
    seen_documents: dict[str, str] = {}
    requirements: dict[str, tuple[str, int]] = {}
    scenarios: dict[str, tuple[str, int]] = {}
    for document in documents:
        path = document["path"]
        document_id = document["id"]
        if document_id is not None:
            if document_id in seen_documents:
                findings.append(_finding(
                    "document_id_duplicate", f"ID {document_id} também declarado em {seen_documents[document_id]}.", path, 1,
                ))
            else:
                seen_documents[document_id] = path
        for requirement in document["requirements"]:
            identifier = requirement["id"]
            if identifier in requirements:
                earlier = requirements[identifier]
                findings.append(_finding(
                    "requirement_id_duplicate", f"ID {identifier} também declarado em {earlier[0]}:{earlier[1]}.", path, requirement["line"],
                ))
            else:
                requirements[identifier] = (path, requirement["line"])
        for scenario in document["scenarios"]:
            identifier = scenario["id"]
            if identifier is None:
                continue
            if identifier in scenarios:
                earlier = scenarios[identifier]
                findings.append(_finding(
                    "scenario_id_duplicate", f"ID {identifier} também declarado em {earlier[0]}:{earlier[1]}.", path, scenario["line"],
                ))
            else:
                scenarios[identifier] = (path, scenario["line"])

    covered: set[str] = set()
    for document in documents:
        for scenario in document["scenarios"]:
            for identifier in scenario["requirements"]:
                if identifier not in requirements:
                    findings.append(_finding(
                        "requirement_unknown", f"Cenário referencia requisito não declarado: {identifier}.", document["path"], scenario["line"],
                    ))
                else:
                    covered.add(identifier)
    for identifier, (path, line) in requirements.items():
        if identifier not in covered:
            findings.append(_finding(
                "requirement_uncovered", f"Requisito {identifier} não possui cenário associado.", path, line,
            ))


def inspect_project(root: Path) -> dict[str, Any]:
    """Inspect an explicitly opted-in project without changing any project file.

    ``specmd.toml`` opts in with exactly ``schema = 1``. Valid syntax is not
    approval: this increment always leaves active projects unable to complete.
    """
    root = Path(root).absolute()
    config_path = root / "specmd.toml"
    if config_path.is_symlink():
        return _result("error", False, [_finding(
            "config_symlink", "specmd.toml não pode ser um link simbólico.", "specmd.toml",
        )])
    if not config_path.exists():
        return _result("inactive", None)
    try:
        config_bytes = _read_regular_file(config_path)
        config = tomllib.loads(config_bytes.decode("utf-8"))
        if set(config) != {"schema"} or type(config["schema"]) is not int or config["schema"] != 1:
            raise ValueError("A configuração inicial aceita somente schema = 1, sem outras opções.")
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, ValueError) as exc:
        return _result("error", False, [_finding("config_invalid", str(exc), "specmd.toml")])

    findings: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    complete_snapshot = True

    def scan_error(exc: OSError) -> None:
        nonlocal complete_snapshot
        complete_snapshot = False
        location = None
        if exc.filename:
            try:
                location = Path(exc.filename).relative_to(root).as_posix()
            except ValueError:
                pass
        findings.append(_finding("read_error", "Não foi possível inspecionar um diretório do projeto.", location))

    for directory, names, filenames in os.walk(root, topdown=True, onerror=scan_error, followlinks=False):
        directory_path = Path(directory)
        retained = []
        for name in sorted(names):
            if name in _PRUNED_DIRECTORIES:
                continue
            candidate = directory_path / name
            if candidate.is_symlink():
                findings.append(_finding(
                    "symlink", "Diretórios simbólicos não são seguidos pelo scanner.", candidate.relative_to(root).as_posix(),
                ))
                continue
            retained.append(name)
        names[:] = retained
        for name in sorted(filenames):
            candidate = directory_path / name
            if candidate.suffix.casefold() not in _MARKDOWN_SUFFIXES:
                continue
            relative = candidate.relative_to(root).as_posix()
            if candidate.is_symlink():
                findings.append(_finding("symlink", "Documentos simbólicos não são lidos pelo scanner.", relative))
                continue
            try:
                raw = _read_regular_file(candidate)
            except OSError:
                complete_snapshot = False
                findings.append(_finding("read_error", "Não foi possível ler um documento regular e estável.", relative))
                continue
            documents.append(_inspect_document(raw, relative, findings))

    documents.sort(key=lambda item: item["path"])
    _validate_links(documents, findings)
    validation_failed = bool(findings)
    findings.extend([
        _finding("authority_not_configured", "Autoridade de aceite humano ainda não implementada/configurada; classificação declarada não é aprovação."),
        _finding("evidence_not_executed", "Este scanner não executa cenários nem comprova a implementação dos requisitos."),
    ])
    result = _result("blocked" if validation_failed else "waiting_human_review", False, findings)
    result["documents"] = documents
    if complete_snapshot:
        manifest = {
            "schema": 1,
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "documents": [
                {"path": document["path"], "sha256": document["sha256"]}
                for document in documents
            ],
        }
        encoded = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        result["manifest"] = manifest
        result["manifest_sha256"] = hashlib.sha256(encoded).hexdigest()
    return result
