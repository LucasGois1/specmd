"""Read-only inspection of Markdown documentation and its embedded scenarios.

Every Markdown file in the project is analysed, except files ignored by Git or
listed in `.specmdignore` (documents that do not describe system behaviour).
The scanner reports structural gaps (documents without scenarios,
requirements without scenarios, invalid Gherkin, duplicate IDs) and never
executes scenarios.

Each document's analysis is cached in `.specmd/local/`, so a hook in a project
with thousands of documents only parses what changed. The cache is derived
data: deleting it is always safe.
"""

from __future__ import annotations

import contextlib
import functools
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
from typing import Any, Callable, Iterator

from . import mdg
from . import state as local_state
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
CONFIG_FILE = "specmd.toml"
CACHE_FILE = "inspection-cache.json"
# A file modified this close to the moment it was read may have been rewritten
# with the same size and timestamp; such entries are re-read, as Git does.
_SETTLE_NS = 2_000_000_000


@functools.lru_cache(maxsize=1)
def _markdown() -> Any:
    from markdown_it import MarkdownIt

    return MarkdownIt()


@functools.lru_cache(maxsize=None)
def _cache_key(language: str | None) -> str:
    """Cached analyses are valid only for this analyser, these parsers and this language."""
    parts = [Path(__file__).read_bytes(), str(language).encode()]
    for module in ("behave.version", "markdown_it"):
        spec = importlib.util.find_spec(module)
        parts.append(Path(spec.origin).read_bytes() if spec and spec.origin else module.encode())
    return hashlib.sha256(b"\0".join(parts)).hexdigest()


@contextlib.contextmanager
def _fixed_cwd() -> Iterator[None]:
    """behave resolves the file name of every parsed statement against os.getcwd();
    with thousands of documents that system call dominated the analysis."""
    original = os.getcwd
    current = original()
    os.getcwd = lambda: current
    try:
        yield
    finally:
        os.getcwd = original


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


def _scenario_digest(scenario: Any, tags: set[str]) -> str:
    """What a scenario checks: its steps (with background, tables, doc strings and outline values) and tags."""
    background = getattr(scenario, "background", None)
    steps = [*getattr(background, "steps", []), *scenario.steps]
    return _digest([scenario.name, sorted(tags), [
        [step.step_type, step.name, step.text,
         [list(step.table.headings), [list(row.cells) for row in step.table.rows]] if step.table else None]
        for step in steps]])


def _step_texts(scenario: Any) -> list[list[Any]]:
    """Each step as [type, text, digest of its table or doc string], to show what changed."""
    background = getattr(scenario, "background", None)
    steps = [*getattr(background, "steps", []), *scenario.steps]
    return [[step.step_type, f"{step.keyword.strip()} {step.name}",
             _digest([step.text, [list(step.table.headings), [list(row.cells) for row in step.table.rows]]
                      if step.table else None])[:12] if step.text or step.table else None]
            for step in steps]


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


def _git_listed(root: Path, *pathspec: str) -> list[str] | None:
    try:
        completed = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "-co", "--exclude-standard",
                                    "--", *pathspec], capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return [item for item in completed.stdout.decode("utf-8", "surrogateescape").split("\0") if item]


def _discover(root: Path, findings: list[dict[str, Any]]) -> list[str]:
    """Relative Markdown paths, honouring .gitignore when Git is available."""
    listed = _git_listed(root, ":(icase)*.md", ":(icase)*.markdown")
    if listed is None:
        listed = []
        for directory, names, filenames in os.walk(root, followlinks=False):
            base = Path(directory)
            names[:] = sorted(name for name in names if name not in _PRUNED_DIRECTORIES
                              and not (base / name).is_symlink())
            listed.extend((base / name).relative_to(root).as_posix() for name in filenames)
    linked: dict[str, bool] = {}

    def is_link(relative: str) -> bool:
        if relative not in linked:
            linked[relative] = (root / relative).is_symlink()
        return linked[relative]

    paths = []
    for relative in sorted(set(listed)):
        parts = relative.split("/")
        if os.path.splitext(relative)[1].casefold() not in _MARKDOWN_SUFFIXES or set(parts[:-1]) & _PRUNED_DIRECTORIES:
            continue
        if any(is_link("/".join(parts[:i])) for i in range(1, len(parts))):
            findings.append(_symlink_finding(relative))
            continue
        paths.append(relative)
    return paths


def _symlink_finding(relative: str) -> dict[str, Any]:
    return _finding("symlink", "Documentos simbólicos não são lidos pelo scanner.", relative)


def _cached_entry(root: Path, relative: str, cached: Any,
                  analyse: Callable[[bytes], dict[str, Any]]) -> dict[str, Any] | str | None:
    """The cached analysis when the file is unchanged; otherwise read it and analyse it again.

    Returns "symlink" for a symbolic link and None when the file cannot be read.
    """
    try:
        info = os.lstat(os.path.join(root, relative))
    except OSError:
        return None
    if stat.S_ISLNK(info.st_mode):
        return "symlink"
    signature = [info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino]
    usable = (isinstance(cached, dict) and isinstance(cached.get("data"), dict)
              and isinstance(cached.get("sha256"), str) and isinstance(cached.get("checked_ns"), int))
    if (usable and cached.get("stat") == signature
            and max(info.st_mtime_ns, info.st_ctime_ns) + _SETTLE_NS < cached["checked_ns"]):
        return cached
    checked = time.time_ns()
    try:
        raw = _read_regular_file(root / relative)
    except OSError:
        return None
    digest = hashlib.sha256(raw).hexdigest()
    data = cached["data"] if usable and cached["sha256"] == digest else analyse(raw)
    return {"stat": signature, "checked_ns": checked, "sha256": digest, "data": data}


@functools.lru_cache(maxsize=1)
def _gherkin_headings() -> re.Pattern[str]:
    """Headings that MDG reads as Gherkin keywords, in every language Gherkin knows."""
    from behave.i18n import languages

    words = {word.strip() for language in languages.values()
             for kind in ("feature", "rule", "background", "scenario", "scenario_outline", "examples")
             for word in language.get(kind, []) if word.strip() and word.strip() != "*"}
    return re.compile(r"^(?:" + "|".join(sorted(map(re.escape, words), key=len, reverse=True)) + r")\s*:", re.IGNORECASE)


def _rule_markers(raw: bytes) -> dict[str, Any]:
    """What would make an ignored document declare rules: requirement titles, Gherkin blocks, MDG titles."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {"requirements": [], "gherkin": 0, "mdg": 0}
    tokens = _markdown().parse(strip_frontmatter(text))
    requirements: set[str] = set()
    gherkin = mdg = 0
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            title = _heading_title(tokens, index)
            match = _REQUIREMENT_HEADING.match(title)
            if match:
                requirements.add(match.group(1))
            elif _gherkin_headings().match(title):
                mdg += 1
        elif _is_gherkin_fence(token):
            gherkin += 1
    return {"requirements": sorted(requirements), "gherkin": gherkin, "mdg": mdg}


def _heading_title(tokens: list[Any], index: int) -> str:
    return "".join(child.content for child in tokens[index + 1].children or []) if index + 1 < len(tokens) else ""


def _is_gherkin_fence(token: Any) -> bool:
    words = token.info.strip().split(maxsplit=1)
    return token.type == "fence" and bool(words) and words[0].casefold() == "gherkin"


def _gherkin_fences(tokens: list[Any]) -> tuple[list[dict[str, Any]], list[tuple[Any, str | None]]]:
    """Requirement headings and Gherkin fences, each fence with the innermost requirement above it."""
    requirements: list[dict[str, Any]] = []
    fences: list[tuple[Any, str | None]] = []
    stack: list[tuple[int, str | None]] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            level = int(token.tag[1:])
            match = _REQUIREMENT_HEADING.match(_heading_title(tokens, index))
            stack = [item for item in stack if item[0] < level] + [(level, match.group(1) if match else None)]
            if match:
                requirements.append({"id": match.group(1), "line": token.map[0] + 1})
        elif _is_gherkin_fence(token):
            fences.append((token, next((identifier for _, identifier in reversed(stack) if identifier), None)))
    return requirements, fences


class _DocumentReader:
    """Scenarios of one document's Gherkin blocks, with identities and requirement links."""

    def __init__(self, path: str, findings: list[dict[str, Any]], language: str | None):
        self.path = path
        self.findings = findings
        self.language = language
        self.scenarios: list[dict[str, Any]] = []
        self.names: dict[str, int] = {}

    def finding(self, kind: str, message: str, line: int | None) -> None:
        self.findings.append(_finding(kind, message, self.path, line))

    def read_block(self, block: int, first_line: int, content: str, context: Callable[[int], str | None]) -> None:
        from behave.parser import ParserError, parse_feature

        try:
            feature = parse_feature("\n" * (first_line - 1) + content, language=self.language, filename=self.path)
        except ParserError as exc:
            self.finding("gherkin_invalid", str(exc) + _language_hint(str(exc), content), getattr(exc, "line", first_line))
            return
        except (LookupError, ValueError) as exc:
            self.finding("gherkin_invalid", str(exc), first_line)
            return
        if feature is None:
            self.finding("gherkin_invalid", "Bloco sem funcionalidade Gherkin.", first_line)
            return
        before = len(self.scenarios)
        self.visit(feature, {str(tag) for tag in feature.tags}, block, context)
        if len(self.scenarios) == before:
            self.finding("scenarios_missing", "Bloco sem cenários concretos.", feature.line)

    def visit(self, container: Any, inherited: set[str], block: int, context: Callable[[int], str | None]) -> None:
        from behave.model import Rule, ScenarioOutline

        for scenario in getattr(container, "run_items", container.scenarios):
            if isinstance(scenario, Rule):
                self.visit(scenario, inherited | {str(tag) for tag in scenario.tags}, block, context)
            elif isinstance(scenario, ScenarioOutline):
                self.outline(scenario, inherited, block, context)
            else:
                self.add(scenario, inherited, block, context)

    def outline(self, scenario: Any, inherited: set[str], block: int, context: Callable[[int], str | None]) -> None:
        positions = [(example_index, row_index)
                     for example_index, example in enumerate(scenario.examples, start=1) if example.table is not None
                     for row_index, _ in enumerate(example.table.rows, start=1)]
        try:
            concrete = list(scenario.scenarios)
        except (LookupError, ValueError, TypeError, AssertionError) as exc:
            self.finding("gherkin_invalid", str(exc), scenario.line)
            return
        if not positions or len(concrete) != len(positions):
            self.finding("scenarios_missing", "Esquema do Cenário exige linhas de Exemplos concretas.", scenario.line)
            return
        explicit = sorted({str(tag) for tag in scenario.tags if _SCENARIO_ID.fullmatch(str(tag))})
        base = explicit[0] if len(explicit) == 1 else self.default_identity(scenario.name)
        for instance, position in zip(concrete, positions):
            self.add(instance, inherited, block, context, scenario, position, base)

    def default_identity(self, name: str) -> str:
        self.names[name] = self.names.get(name, 0) + 1
        return f"{self.path}::{name}" + (f"#{self.names[name]}" if self.names[name] > 1 else "")

    def add(self, scenario: Any, inherited: set[str], block: int, context: Callable[[int], str | None], template: Any = None,
            position: tuple[int, int] | None = None, identity: str | None = None) -> None:
        tags = inherited | {str(tag) for tag in scenario.tags}
        explicit = sorted({str(tag) for tag in (template or scenario).tags if _SCENARIO_ID.fullmatch(str(tag))})
        if len(explicit) > 1:
            self.finding("scenario_id_invalid", "Cenário deve ter no máximo uma tag de ID (…-SCN-…).", scenario.line)
        base = identity or (explicit[0] if explicit else self.default_identity(scenario.name))
        linked = context(scenario.line)
        requirement_ids = sorted(tag for tag in tags if _REQUIREMENT_ID.fullmatch(tag)) or ([linked] if linked else [])
        background = getattr(scenario, "background", None)
        step_count = len(scenario.steps) + len(getattr(background, "steps", []))
        if not step_count:
            self.finding("scenario_steps_missing", "Cenário sem passos não fornece comportamento verificável.",
                         scenario.line)
        item = {
            "id": f"{base}:row:{position[0]}:{position[1]}" if position else base,
            "name": scenario.name,
            "line": scenario.line,
            "requirements": requirement_ids,
            "tags": sorted(tags),
            "block": block,
            "steps": step_count,
            "explicit_id": bool(explicit),
            "sha256": _scenario_digest(scenario, tags),
            "steps_text": _step_texts(scenario),
        }
        if template is not None:
            item.update({"template_id": base, "definition_line": template.line,
                         "example_index": position[0], "row_index": position[1]})
        self.scenarios.append(item)


def _inspect_document(data: bytes, path: str, findings: list[dict[str, Any]],
                      language: str | None = None) -> dict[str, Any]:
    document: dict[str, Any] = {"path": path, "sha256": hashlib.sha256(data).hexdigest(),
                                "requirements": [], "scenarios": []}
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        findings.append(_finding("invalid_utf8", "Documento não contém UTF-8 válido.", path))
        return document
    if mdg.is_mdg(path):
        return _inspect_mdg(document, strip_frontmatter(text), findings, language)
    document["requirements"], fences = _gherkin_fences(_markdown().parse(strip_frontmatter(text)))
    # Prose edits do not change the specification digest; requirements and
    # scenarios do. Hooks use it to tell which scenarios the developer saw.
    document["spec_sha256"] = _digest([[item["id"] for item in document["requirements"]],
                                       [token.content for token, _ in fences]])
    if not fences:
        findings.append(_finding("gherkin_missing", "Documento sem cenários Gherkin." + _GAP_HINT, path))
    reader = _DocumentReader(path, findings, language)
    for block, (token, context) in enumerate(fences, start=1):
        reader.read_block(block, token.map[0] + 2, token.content, lambda _line, linked=context: linked)
    document["scenarios"] = reader.scenarios
    return document


def _language_hint(error: str, content: str) -> str:
    """When the parser found no feature in text that uses Gherkin keywords, say where the language comes from."""
    if "No feature found" not in error or not any(_gherkin_headings().match(line.strip())
                                                  for line in content.splitlines()):
        return ""
    return (" Se o Gherkin está em outro idioma, declare `# language: <código>` no início do bloco "
            "ou `gherkin_language` no specmd.toml.")


_MDG_LANGUAGE = (" Em MDG não existe `# language:`: o idioma vem de `gherkin_language` no specmd.toml "
                 "(por exemplo, gherkin_language = \"pt\").")


def _inspect_mdg(document: dict[str, Any], text: str, findings: list[dict[str, Any]],
                 language: str | None) -> dict[str, Any]:
    """A Markdown with Gherkin file is one feature, converted line for line."""
    path = document["path"]
    converted = mdg.convert(text, language, _REQUIREMENT_HEADING)
    document["requirements"] = converted.requirements
    document["spec_sha256"] = _digest([[item["id"] for item in converted.requirements], converted.text])
    if not converted.scenarios:
        foreign = any(_gherkin_headings().match(mdg.heading_title(match)) for match in
                      (mdg.HEADING.match(line) for line in text.splitlines()) if match)
        findings.append(_finding("gherkin_missing", "Arquivo MDG sem títulos de cenário." +
                                 (_MDG_LANGUAGE if foreign else _GAP_HINT), path))
        return document
    reader = _DocumentReader(path, findings, language)
    reader.read_block(1, 1, converted.text, converted.context_at)
    document["scenarios"] = reader.scenarios
    return document


def _declare_requirements(document: dict[str, Any], requirements: dict[str, tuple[str, int]],
                          findings: list[dict[str, Any]]) -> None:
    for requirement in document["requirements"]:
        identifier = requirement["id"]
        if identifier in requirements:
            earlier = requirements[identifier]
            findings.append(_finding("requirement_id_duplicate", f"ID {identifier} também declarado em "
                                     f"{earlier[0]}:{earlier[1]}.", document["path"], requirement["line"]))
        else:
            requirements[identifier] = (document["path"], requirement["line"])


def _declare_scenarios(document: dict[str, Any], templates: dict[str, tuple[str, int]],
                       findings: list[dict[str, Any]]) -> None:
    for scenario in document["scenarios"]:
        template = scenario.get("template_id", scenario["id"])
        declaration = (document["path"], scenario.get("definition_line", scenario["line"]))
        if template in templates and templates[template] != declaration:
            earlier = templates[template]
            findings.append(_finding("scenario_id_duplicate", f"ID de cenário {template} também declarado em "
                                     f"{earlier[0]}:{earlier[1]}.", document["path"], declaration[1]))
        else:
            templates[template] = declaration


def _validate_links(documents: list[dict[str, Any]], findings: list[dict[str, Any]]) -> None:
    requirements: dict[str, tuple[str, int]] = {}
    templates: dict[str, tuple[str, int]] = {}
    for document in documents:
        _declare_requirements(document, requirements, findings)
        _declare_scenarios(document, templates, findings)
    covered: set[str] = set()
    for document in documents:
        for scenario in document["scenarios"]:
            unknown = [identifier for identifier in scenario["requirements"] if identifier not in requirements]
            covered.update(identifier for identifier in scenario["requirements"] if identifier in requirements)
            findings.extend(_finding("requirement_unknown", f"Cenário referencia requisito não declarado: {identifier}.",
                                     document["path"], scenario["line"]) for identifier in unknown)
    findings.extend(_finding("requirement_uncovered", f"Requisito {identifier} não possui cenário associado.", path, line)
                    for identifier, (path, line) in requirements.items() if identifier not in covered)


def _analyse(relative: str, language: str | None, raw: bytes) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    document = _inspect_document(raw, relative, findings, language)
    return {"document": document, "findings": findings}


def _add_document(entry: Any, relative: str, findings: list[dict[str, Any]], entries: dict[str, Any],
                  documents: list[dict[str, Any]]) -> bool:
    """Collect one analysed document; False when it could not be read."""
    if entry == "symlink":
        findings.append(_symlink_finding(relative))
    elif entry is None:
        findings.append(_finding("read_error", "Não foi possível ler um documento regular e estável.", relative))
        return False
    else:
        entries[relative] = entry
        documents.append(entry["data"]["document"])
        findings.extend(entry["data"]["findings"])
    return True


def _add_ignored(entry: Any, relative: str, defaults: list[tuple[bool, re.Pattern[str]]],
                 entries: dict[str, Any], markers: dict[str, Any]) -> None:
    """Remember an ignored document's rule markers when it has any."""
    if not isinstance(entry, dict):
        return
    entries[relative] = entry
    found = entry["data"]
    if found["requirements"] or found["gherkin"] or found["mdg"]:
        markers[relative] = {**found, "default": is_ignored(relative, defaults)}


def _analyse_documents(root: Path, rules: list[tuple[bool, re.Pattern[str]]], language: str | None,
                       findings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    """Analyse every discovered document, reusing the cache.

    Returns the analysed documents, the rule markers of ignored documents that
    have any, and False when a document could not be read.
    """
    key = _cache_key(language)
    stored = local_state.read_local(root, CACHE_FILE)
    fresh = stored.get("key") == key
    cached = stored.get("entries") if fresh and isinstance(stored.get("entries"), dict) else {}
    cached_ignored = stored.get("ignored") if fresh and isinstance(stored.get("ignored"), dict) else {}
    defaults = compile_ignore(list(DEFAULT_IGNORE))
    entries: dict[str, Any] = {}
    ignored_entries: dict[str, Any] = {}
    documents: list[dict[str, Any]] = []
    markers: dict[str, Any] = {}
    complete = True
    with _fixed_cwd():
        for relative in _discover(root, findings):
            if is_ignored(relative, rules):
                entry = _cached_entry(root, relative, cached_ignored.get(relative), _rule_markers)
                _add_ignored(entry, relative, defaults, ignored_entries, markers)
                continue
            entry = _cached_entry(root, relative, cached.get(relative), functools.partial(_analyse, relative, language))
            complete = _add_document(entry, relative, findings, entries, documents) and complete
    if not _same_entries(entries, cached) or not _same_entries(ignored_entries, cached_ignored):
        with contextlib.suppress(OSError, ValueError):
            local_state.write_local(root, CACHE_FILE, {"key": key, "entries": entries, "ignored": ignored_entries})
    return documents, markers, complete


def _same_entries(entries: dict[str, Any], cached: dict[str, Any]) -> bool:
    return entries.keys() == cached.keys() and all(entry is cached[path] for path, entry in entries.items())


def inspect_project(root: Path) -> dict[str, Any]:
    """Inspect the project's documentation; only the local analysis cache is written.

    specmd.toml is optional: without it every option takes its default.
    """
    root = Path(root).absolute()
    config_path = root / CONFIG_FILE
    if config_path.is_symlink():
        return _result("error", [_finding(
            "config_symlink", f"{CONFIG_FILE} não pode ser um link simbólico.", CONFIG_FILE,
        )])
    try:
        config_bytes = _read_regular_file(config_path) if config_path.exists() else b""
        config = parse_config(config_bytes)
        ignore_path = root / IGNORE_FILE
        ignore_bytes = _read_regular_file(ignore_path) if ignore_path.exists() else b""
    except (OSError, ConfigError) as exc:
        return _result("error", [_finding("config_invalid", str(exc), CONFIG_FILE)])

    findings: list[dict[str, Any]] = []
    rules = compile_ignore([*DEFAULT_IGNORE, *ignore_bytes.decode("utf-8", "replace").splitlines()])
    documents, markers, complete_snapshot = _analyse_documents(root, rules, config.get("gherkin_language"), findings)
    documents.sort(key=lambda item: item["path"])
    _validate_links(documents, findings)
    result = _result("needs_scenarios" if findings else "ready", findings)
    result["documents"] = documents
    result["ignored_rules"] = markers
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


def extract_features(root: Path, inspection: dict[str, Any], language: str | None = None) -> list[dict[str, Any]]:
    """Return in-memory Gherkin blocks padded to their original Markdown lines.

    Each document is re-read and checked against the inspection's hash, so a
    document changed after inspection is refused. A Markdown with Gherkin file
    is one block converted line for line. No .feature file is created.
    """
    root = Path(root).absolute()
    features: list[dict[str, Any]] = []
    for document in inspection.get("documents", []):
        raw = _read_regular_file(root / document["path"])
        if hashlib.sha256(raw).hexdigest() != document["sha256"]:
            raise ValueError("A documentação mudou desde a inspeção; inspecione novamente: " + document["path"])
        text = strip_frontmatter(raw.decode("utf-8"))
        if mdg.is_mdg(document["path"]):
            converted = mdg.convert(text, language, _REQUIREMENT_HEADING)
            features.append({"path": document["path"], "block": 1, "line": 1, "content": converted.text})
            continue
        block = 0
        for token in _markdown().parse(text):
            if not _is_gherkin_fence(token):
                continue
            block += 1
            first_line = token.map[0] + 2
            features.append({
                "path": document["path"], "block": block, "line": first_line,
                "content": "\n" * (first_line - 1) + token.content,
            })
    return features
