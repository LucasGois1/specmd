"""Read-only inspection of opt-in Markdown documentation and its scenarios.

The scanner reports structural gaps (requirements without scenarios, invalid
Gherkin, duplicate IDs) and never executes scenarios.
"""

from __future__ import annotations

import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from behave.model import Rule, ScenarioOutline
from behave.parser import ParserError, parse_feature
from markdown_it import MarkdownIt
import yaml
from yaml.constructor import ConstructorError

from .config import ConfigError, parse_config, read_regular_file as _read_regular_file


_PRUNED_DIRECTORIES = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "target",
    "__pycache__", ".specmd", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "build", "dist",
})
_MARKDOWN_SUFFIXES = frozenset({".md", ".markdown"})
_KINDS = frozenset({"behavioral", "reference", "mixed"})
_CACHE_PARSER = "scanner-2|" + "|".join(
    f"{name}={version(name)}" for name in ("behave", "markdown-it-py", "PyYAML")
)
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


def _result(status: str, findings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "protocol_version": 2,
        "status": status,
        "manifest": None,
        "manifest_sha256": None,
        "spec_fp": None,
        "documents": [],
        "findings": findings if findings is not None else [],
    }


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
                      findings: list[dict[str, Any]], *, advanced: bool = False) -> dict[str, Any]:
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
    # Prose edits do not change the specification digest; requirements and
    # scenarios do. Hooks use it to tell which scenarios the developer saw.
    document["spec_sha256"] = hashlib.sha256(json.dumps(
        [[item["id"] for item in document["requirements"]], [token.content for token in fences]],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    if document["kind"] == "reference" and (document["requirements"] or fences):
        findings.append(_finding(
            "classification_conflict",
            "Documento reference declara requisitos ou blocos Gherkin; revise a classificação em vez de autoisentar o conteúdo.", path,
        ))
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
        initial_count = len(document["scenarios"])

        def add_scenario(scenario: Any, inherited: set[str], template: Any = None,
                         position: tuple[int, int] | None = None) -> None:
            tags = inherited | {str(tag) for tag in scenario.tags}
            identity_source = template if template is not None else scenario
            scenario_ids = sorted({str(tag) for tag in identity_source.tags if _SCENARIO_ID.fullmatch(str(tag))})
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
            background = getattr(scenario, "background", None)
            step_count = len(scenario.steps) + len(getattr(background, "steps", []))
            if not step_count:
                findings.append(_finding(
                    "scenario_steps_missing", "Cenário sem passos não fornece comportamento verificável.", path, scenario.line,
                ))
            identity = scenario_ids[0] if len(scenario_ids) == 1 else None
            item = {
                "id": f"{identity}:row:{position[0]}:{position[1]}" if identity and position else identity,
                "name": scenario.name,
                "line": scenario.line,
                "requirements": requirement_ids,
                "block": block,
                "steps": step_count,
            }
            if template is not None:
                item.update({
                    "template_id": identity,
                    "definition_line": template.line,
                    "example_index": position[0],
                    "row_index": position[1],
                })
            document["scenarios"].append(item)

        def visit(container: Any, inherited: set[str]) -> None:
            for scenario in getattr(container, "run_items", container.scenarios):
                if isinstance(scenario, Rule):
                    if not advanced:
                        findings.append(_finding(
                            "gherkin_unsupported", "Rule/Regra exige configuração schema 2.", path, scenario.line,
                        ))
                    else:
                        visit(scenario, inherited | {str(tag) for tag in scenario.tags})
                elif isinstance(scenario, ScenarioOutline):
                    if not advanced:
                        findings.append(_finding(
                            "gherkin_unsupported", "Scenario Outline/Esquema do Cenário exige configuração schema 2.", path, scenario.line,
                        ))
                        continue
                    positions = [
                        (example_index, row_index)
                        for example_index, example in enumerate(scenario.examples, start=1)
                        if example.table is not None
                        for row_index, _ in enumerate(example.table.rows, start=1)
                    ]
                    try:
                        concrete = list(scenario.scenarios)
                    except (LookupError, ValueError, TypeError, AssertionError) as exc:
                        findings.append(_finding("gherkin_invalid", str(exc), path, scenario.line))
                        continue
                    if not positions or len(concrete) != len(positions):
                        findings.append(_finding(
                            "scenarios_missing", "Esquema do Cenário exige linhas de Exemplos concretas e mapeáveis.", path, scenario.line,
                        ))
                        continue
                    for instance, position in zip(concrete, positions):
                        add_scenario(instance, inherited, scenario, position)
                else:
                    add_scenario(scenario, inherited)

        visit(feature, {str(tag) for tag in feature.tags})
        if len(document["scenarios"]) == initial_count:
            findings.append(_finding(
                "scenarios_missing", "Bloco sem cenários concretos verificáveis pelo scanner.", path, feature.line,
            ))
    return document


def _validate_links(documents: list[dict[str, Any]], findings: list[dict[str, Any]]) -> None:
    seen_documents: dict[str, str] = {}
    requirements: dict[str, tuple[str, int]] = {}
    scenarios: dict[str, tuple[str, int]] = {}
    templates: dict[str, tuple[str, int]] = {}
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
            template = scenario.get("template_id", identifier)
            declaration = (path, scenario.get("definition_line", scenario["line"]))
            if template in templates and templates[template] != declaration:
                earlier = templates[template]
                findings.append(_finding(
                    "scenario_id_duplicate", f"Identidade de cenário {template} também declarada em {earlier[0]}:{earlier[1]}.", path, declaration[1],
                ))
            else:
                templates[template] = declaration
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


def _cache_snapshot(root: Path, schema: int, document: dict[str, Any],
                    findings: list[dict[str, Any]]) -> None:
    """Write an advisory parse snapshot, never a trusted validation result.

    Local cache files can be edited by the agent. Consequently the scanner
    always reparses source before deciding; these records are an incremental
    index foundation, not yet a trusted semantic parse-reuse optimization.
    """
    cache_root = root / ".specmd"
    cache_dir = cache_root / "cache"
    temporary: str | None = None
    try:
        if cache_root.is_symlink() or cache_dir.is_symlink():
            return
        cache_dir.mkdir(parents=True, exist_ok=True)
        key = {
            "sha256": document["sha256"], "path": document["path"],
            "parser": _CACHE_PARSER, "config_schema": schema,
        }
        digest = hashlib.sha256(json.dumps(key, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        target = cache_dir / f"{digest}.json"
        payload = {"schema": 1, "key": key, "document": document, "findings": findings, "authority": False}
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if target.is_symlink():
            return
        if target.exists():
            try:
                if _read_regular_file(target) == encoded:
                    return
            except OSError:
                return
        descriptor, temporary = tempfile.mkstemp(prefix=".parse-", suffix=".tmp", dir=cache_dir)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
        os.replace(temporary, target)
        temporary = None
    except (OSError, UnicodeError, ValueError):
        # A cache failure must not change the actual scan or create approval.
        return
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def inspect_project(root: Path, use_cache: bool = False) -> dict[str, Any]:
    """Inspect an explicitly opted-in project without changing any project file.

    Schema 1 preserves the original simple-scenario scanner. Schema 2 enables
    project identity, runner configuration, Rule and concrete outline rows.
    Default inspection writes nothing; use_cache only writes advisory records.
    """
    root = Path(root).absolute()
    config_path = root / "specmd.toml"
    if config_path.is_symlink():
        return _result("error", [_finding(
            "config_symlink", "specmd.toml não pode ser um link simbólico.", "specmd.toml",
        )])
    if not config_path.exists():
        return _result("inactive")
    try:
        config_bytes = _read_regular_file(config_path)
        config = parse_config(config_bytes)
    except (OSError, ConfigError) as exc:
        return _result("error", [_finding("config_invalid", str(exc), "specmd.toml")])

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
            start = len(findings)
            document = _inspect_document(raw, relative, findings, advanced=config["schema"] == 2)
            documents.append(document)
            if use_cache:
                _cache_snapshot(root, config["schema"], document, findings[start:])

    documents.sort(key=lambda item: item["path"])
    _validate_links(documents, findings)
    result = _result("needs_scenarios" if findings else "ready", findings)
    result["documents"] = documents
    result["spec_fp"] = hashlib.sha256(json.dumps(
        [[document["path"], document.get("spec_sha256")] for document in documents],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
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


def extract_features(root: Path, inspection: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return in-memory Gherkin blocks padded to their original Markdown lines.

    A supplied inspection is checked against a fresh inventory, including new
    and removed documents. Extraction never creates .feature files.
    """
    root = Path(root).absolute()
    current = inspect_project(root, use_cache=False)
    if current["status"] == "inactive":
        return []
    if current["status"] == "error" or current["manifest_sha256"] is None:
        raise ValueError("Não foi possível obter um snapshot contratual completo para extração.")
    if inspection is not None and inspection.get("manifest_sha256") != current["manifest_sha256"]:
        raise ValueError("A documentação mudou desde a inspeção; inspecione novamente.")
    features: list[dict[str, Any]] = []
    for document in current["documents"]:
        if document["kind"] not in {"behavioral", "mixed"}:
            continue
        raw = _read_regular_file(root / document["path"])
        if hashlib.sha256(raw).hexdigest() != document["sha256"]:
            raise ValueError("O documento mudou durante a extração; repita a inspeção.")
        text = raw.decode("utf-8")
        _, body = _frontmatter(text, document["path"], [])
        block = 0
        for token in MarkdownIt().parse(body):
            language = token.info.strip().split(maxsplit=1)
            if token.type != "fence" or not language or language[0].casefold() != "gherkin":
                continue
            block += 1
            first_line = token.map[0] + 2
            features.append({
                "path": document["path"], "block": block, "line": first_line,
                "content": "\n" * (first_line - 1) + token.content,
            })
    config_raw = _read_regular_file(root / "specmd.toml")
    if hashlib.sha256(config_raw).hexdigest() != current["manifest"]["config_sha256"]:
        raise ValueError("A configuração mudou durante a extração; repita a inspeção.")
    return features
