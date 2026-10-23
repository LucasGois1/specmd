"""Read-only inspection of Markdown documentation and its embedded scenarios.

Every Markdown file in the project is analysed, except files ignored by Git or
listed in `.specmdignore` (documents that do not describe system behaviour).
The scanner reports structural gaps (documents without scenarios,
requirements without scenarios, invalid Gherkin, duplicate IDs) and never
executes scenarios.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

from behave.model import Rule, ScenarioOutline
from behave.parser import ParserError, parse_feature
from markdown_it import MarkdownIt

from .config import ConfigError, parse_config, read_regular_file as _read_regular_file


_PRUNED_DIRECTORIES = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "target",
    "__pycache__", ".specmd", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "build", "dist",
})
_MARKDOWN_SUFFIXES = frozenset({".md", ".markdown"})
IGNORE_FILE = ".specmdignore"
# Markdown that rarely describes system behaviour; a `!` line in .specmdignore
# brings any of them back into the analysis.
DEFAULT_IGNORE = (
    "README.md", "CHANGELOG.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "SUPPORT.md",
    "LICENSE*", "NOTICE*", "AUTHORS*", "CLAUDE.md", "AGENTS.md", "GEMINI.md", ".github/", ".claude/", ".codex/",
)
_ID_TAIL = r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*"
_REQUIREMENT_ID = re.compile(r"(?:[A-Za-z0-9]+-)*REQ-" + _ID_TAIL)
_SCENARIO_ID = re.compile(r"(?:[A-Za-z0-9]+-)*SCN-" + _ID_TAIL)
_REQUIREMENT_HEADING = re.compile(r"^((?:[A-Za-z0-9]+-)*REQ-" + _ID_TAIL + r")(?=$|\s|[—–:])")
_FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n.*?^(?:---|\.\.\.)[ \t]*\r?$\n?", re.DOTALL | re.MULTILINE)
_GAP_HINT = (" Se descreve comportamento do sistema, confirme os requisitos com o dev e escreva os cenários; "
             "se não descreve, adicione o arquivo ao .specmdignore.")


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


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def strip_frontmatter(text: str) -> str:
    """Blank out a leading YAML frontmatter block, keeping line numbers intact."""
    match = _FRONTMATTER.match(text)
    if not match:
        return text
    return "\n" * match.group(0).count("\n") + text[match.end():]


def _glob_regex(pattern: str) -> str:
    out, index = [], 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif pattern[index] == "*":
            out.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(pattern[index]))
            index += 1
    return "".join(out)


def compile_ignore(lines: list[str]) -> list[tuple[bool, re.Pattern[str]]]:
    """Gitignore-style patterns: `#` comments, `!` negation, trailing `/` for directories."""
    rules = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        negate = line.startswith("!")
        line = line[1:] if negate else line
        directory = line.endswith("/")
        line = line.strip("/") if directory else line
        anchored = "/" in line or raw.strip().lstrip("!").startswith("/")
        body = _glob_regex(line.lstrip("/"))
        prefix = "^" if anchored else "^(?:.*/)?"
        suffix = "/.*$" if directory else "(?:/.*)?$"
        rules.append((negate, re.compile(prefix + body + suffix)))
    return rules


def is_ignored(path: str, rules: list[tuple[bool, re.Pattern[str]]]) -> bool:
    ignored = False
    for negate, rule in rules:
        if rule.match(path):
            ignored = not negate
    return ignored


def _git_listed(root: Path) -> list[str] | None:
    try:
        completed = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "-co", "--exclude-standard"],
                                   capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return [item for item in completed.stdout.decode("utf-8", "surrogateescape").split("\0") if item]


def _discover(root: Path, findings: list[dict[str, Any]]) -> list[str]:
    """Relative Markdown paths, honouring .gitignore when Git is available."""
    listed = _git_listed(root)
    if listed is None:
        listed = []
        for directory, names, filenames in os.walk(root, followlinks=False):
            base = Path(directory)
            names[:] = sorted(name for name in names if name not in _PRUNED_DIRECTORIES
                              and not (base / name).is_symlink())
            listed.extend((base / name).relative_to(root).as_posix() for name in filenames)
    paths = []
    for relative in sorted(set(listed)):
        parts = relative.split("/")
        if Path(relative).suffix.casefold() not in _MARKDOWN_SUFFIXES or set(parts[:-1]) & _PRUNED_DIRECTORIES:
            continue
        if (root / relative).is_symlink() or any((root / Path(*parts[:i])).is_symlink() for i in range(1, len(parts))):
            findings.append(_finding("symlink", "Documentos simbólicos não são lidos pelo scanner.", relative))
            continue
        paths.append(relative)
    return paths


def _inspect_document(data: bytes, path: str, findings: list[dict[str, Any]],
                      language: str | None = None) -> dict[str, Any]:
    document: dict[str, Any] = {
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "requirements": [],
        "scenarios": [],
    }
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        findings.append(_finding("invalid_utf8", "Documento não contém UTF-8 válido.", path))
        return document
    tokens = MarkdownIt().parse(strip_frontmatter(text))

    # Each fence belongs to the innermost requirement heading above it.
    fences: list[tuple[Any, str | None]] = []
    stack: list[tuple[int, str | None]] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and index + 1 < len(tokens):
            level = int(token.tag[1:])
            title = "".join(child.content for child in tokens[index + 1].children or [])
            match = _REQUIREMENT_HEADING.match(title)
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, match.group(1) if match else None))
            if match:
                document["requirements"].append({"id": match.group(1), "line": token.map[0] + 1})
        elif token.type == "fence":
            language_word = token.info.strip().split(maxsplit=1)
            if language_word and language_word[0].casefold() == "gherkin":
                context = next((identifier for _, identifier in reversed(stack) if identifier), None)
                fences.append((token, context))

    # Prose edits do not change the specification digest; requirements and
    # scenarios do. Hooks use it to tell which scenarios the developer saw.
    document["spec_sha256"] = _digest([[item["id"] for item in document["requirements"]],
                                       [token.content for token, _ in fences]])
    if not fences:
        findings.append(_finding("gherkin_missing", "Documento sem cenários Gherkin." + _GAP_HINT, path))

    names: dict[str, int] = {}
    for block, (token, context) in enumerate(fences, start=1):
        first_line = token.map[0] + 2
        try:
            feature = parse_feature("\n" * (first_line - 1) + token.content, language=language, filename=path)
        except ParserError as exc:
            findings.append(_finding("gherkin_invalid", str(exc), path, getattr(exc, "line", first_line)))
            continue
        except (LookupError, ValueError) as exc:
            findings.append(_finding("gherkin_invalid", str(exc), path, first_line))
            continue
        if feature is None:
            findings.append(_finding("gherkin_invalid", "Bloco sem funcionalidade Gherkin.", path, first_line))
            continue
        initial_count = len(document["scenarios"])

        def default_identity(name: str) -> str:
            names[name] = names.get(name, 0) + 1
            return f"{path}::{name}" + (f"#{names[name]}" if names[name] > 1 else "")

        def add_scenario(scenario: Any, inherited: set[str], template: Any = None,
                         position: tuple[int, int] | None = None, identity: str | None = None) -> None:
            tags = inherited | {str(tag) for tag in scenario.tags}
            explicit = sorted({str(tag) for tag in (template or scenario).tags if _SCENARIO_ID.fullmatch(str(tag))})
            if len(explicit) > 1:
                findings.append(_finding(
                    "scenario_id_invalid", "Cenário deve ter no máximo uma tag de ID (…-SCN-…).", path, scenario.line,
                ))
            base = identity or (explicit[0] if explicit else default_identity(scenario.name))
            requirement_ids = sorted(tag for tag in tags if _REQUIREMENT_ID.fullmatch(tag))
            if not requirement_ids and context:
                requirement_ids = [context]
            background = getattr(scenario, "background", None)
            step_count = len(scenario.steps) + len(getattr(background, "steps", []))
            if not step_count:
                findings.append(_finding(
                    "scenario_steps_missing", "Cenário sem passos não fornece comportamento verificável.", path, scenario.line,
                ))
            item = {
                "id": f"{base}:row:{position[0]}:{position[1]}" if position else base,
                "name": scenario.name,
                "line": scenario.line,
                "requirements": requirement_ids,
                "tags": sorted(tags),
                "block": block,
                "steps": step_count,
                "explicit_id": bool(explicit),
            }
            if template is not None:
                item.update({"template_id": base, "definition_line": template.line,
                             "example_index": position[0], "row_index": position[1]})
            document["scenarios"].append(item)

        def visit(container: Any, inherited: set[str]) -> None:
            for scenario in getattr(container, "run_items", container.scenarios):
                if isinstance(scenario, Rule):
                    visit(scenario, inherited | {str(tag) for tag in scenario.tags})
                elif isinstance(scenario, ScenarioOutline):
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
                            "scenarios_missing", "Esquema do Cenário exige linhas de Exemplos concretas.", path, scenario.line,
                        ))
                        continue
                    explicit = sorted({str(tag) for tag in scenario.tags if _SCENARIO_ID.fullmatch(str(tag))})
                    base = explicit[0] if len(explicit) == 1 else default_identity(scenario.name)
                    for instance, position in zip(concrete, positions):
                        add_scenario(instance, inherited, scenario, position, identity=base)
                else:
                    add_scenario(scenario, inherited)

        visit(feature, {str(tag) for tag in feature.tags})
        if len(document["scenarios"]) == initial_count:
            findings.append(_finding("scenarios_missing", "Bloco sem cenários concretos.", path, feature.line))
    return document


def _validate_links(documents: list[dict[str, Any]], findings: list[dict[str, Any]]) -> None:
    requirements: dict[str, tuple[str, int]] = {}
    templates: dict[str, tuple[str, int]] = {}
    for document in documents:
        path = document["path"]
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
            template = scenario.get("template_id", scenario["id"])
            declaration = (path, scenario.get("definition_line", scenario["line"]))
            if template in templates and templates[template] != declaration:
                earlier = templates[template]
                findings.append(_finding(
                    "scenario_id_duplicate", f"ID de cenário {template} também declarado em {earlier[0]}:{earlier[1]}.", path, declaration[1],
                ))
            else:
                templates[template] = declaration

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
    """Inspect the project's documentation without changing any file.

    specmd.toml is optional: without it every option takes its default.
    """
    root = Path(root).absolute()
    config_path = root / "specmd.toml"
    if config_path.is_symlink():
        return _result("error", [_finding(
            "config_symlink", "specmd.toml não pode ser um link simbólico.", "specmd.toml",
        )])
    try:
        config_bytes = _read_regular_file(config_path) if config_path.exists() else b""
        config = parse_config(config_bytes)
        ignore_path = root / IGNORE_FILE
        ignore_bytes = _read_regular_file(ignore_path) if ignore_path.exists() else b""
    except (OSError, ConfigError) as exc:
        return _result("error", [_finding("config_invalid", str(exc), "specmd.toml")])

    findings: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    complete_snapshot = True
    rules = compile_ignore([*DEFAULT_IGNORE, *ignore_bytes.decode("utf-8", "replace").splitlines()])
    for relative in _discover(root, findings):
        if is_ignored(relative, rules):
            continue
        try:
            raw = _read_regular_file(root / relative)
        except OSError:
            complete_snapshot = False
            findings.append(_finding("read_error", "Não foi possível ler um documento regular e estável.", relative))
            continue
        documents.append(_inspect_document(raw, relative, findings, config.get("gherkin_language")))

    documents.sort(key=lambda item: item["path"])
    _validate_links(documents, findings)
    result = _result("needs_scenarios" if findings else "ready", findings)
    result["documents"] = documents
    result["spec_fp"] = _digest([[document["path"], document.get("spec_sha256")] for document in documents])
    if complete_snapshot:
        manifest = {
            "schema": 2,
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "ignore_sha256": hashlib.sha256(ignore_bytes).hexdigest(),
            "documents": [{"path": document["path"], "sha256": document["sha256"]} for document in documents],
        }
        result["manifest"] = manifest
        result["manifest_sha256"] = _digest(manifest)
    return result


def extract_features(root: Path, inspection: dict[str, Any]) -> list[dict[str, Any]]:
    """Return in-memory Gherkin blocks padded to their original Markdown lines.

    Each document is re-read and checked against the inspection's hash, so a
    document changed after inspection is refused. No .feature file is created.
    """
    root = Path(root).absolute()
    features: list[dict[str, Any]] = []
    for document in inspection.get("documents", []):
        raw = _read_regular_file(root / document["path"])
        if hashlib.sha256(raw).hexdigest() != document["sha256"]:
            raise ValueError("A documentação mudou desde a inspeção; inspecione novamente: " + document["path"])
        block = 0
        for token in MarkdownIt().parse(strip_frontmatter(raw.decode("utf-8"))):
            language = token.info.strip().split(maxsplit=1)
            if token.type != "fence" or not language or language[0].casefold() != "gherkin":
                continue
            block += 1
            first_line = token.map[0] + 2
            features.append({
                "path": document["path"], "block": block, "line": first_line,
                "content": "\n" * (first_line - 1) + token.content,
            })
    return features
