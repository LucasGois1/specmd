"""Choose the scenarios a code change can affect, from per-scenario coverage.

The Python worker records, for each scenario, the project functions it
executed and the files it read. After a change, a scenario runs again when it
executed a changed function, read a changed file, is new or changed, did not
pass, or has no coverage. A change at module level (imports, constants,
decorators, signatures), in the steps or in the configuration runs every
scenario, because it can alter any execution. Dependencies outside Python
code (environment variables, databases) are not seen; `specmd run` runs every
scenario and remains the safety net.

The coverage table is derived data in .specmd/local; deleting it only makes
the next run complete.
"""
from __future__ import annotations

import ast
import bisect
import hashlib
from pathlib import Path
import sys
from typing import Any

COVERAGE_FILE = "coverage.json"
MODULE = "<module>"
_VERSION = 1
# Files that decide how scenarios run or which dependencies they load.
_RUN_SETTINGS = frozenset({
    "specmd.toml", ".specmdignore", "behave.ini", ".behaverc", "setup.cfg", "tox.ini", "pyproject.toml",
    "requirements.txt", "pylock.toml", "uv.lock", "poetry.lock", "Pipfile.lock",
})


def _hash(node: ast.AST) -> str:
    return hashlib.sha256(ast.dump(node).encode()).hexdigest()[:24]


def python_blocks(source: bytes) -> dict[str, Any] | None:
    """Hash each function and method apart from the module level.

    Nested functions, lambdas and comprehensions belong to the enclosing
    function. The module hash keeps decorators and signatures but not bodies,
    so only a body change is local. Comments and formatting change nothing.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None
    blocks: dict[str, str] = {}
    ranges: list[list[Any]] = []
    counts: dict[str, int] = {}

    def visit(body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = prefix + node.name
                counts[name] = counts.get(name, 0) + 1
                key = f"{name}#{counts[name]}"
                blocks[key] = _hash(node)
                start = min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])
                ranges.append([start, node.end_lineno, key])
                node.body = [ast.Pass()]
            elif isinstance(node, ast.ClassDef):
                visit(node.body, f"{prefix}{node.name}.")

    visit(tree.body, "")
    ranges.sort()
    return {"module": _hash(tree), "blocks": blocks, "ranges": ranges}


def _block_at(ranges: list[list[Any]], line: int) -> str:
    index = bisect.bisect_right([item[0] for item in ranges], line) - 1
    if index >= 0 and ranges[index][0] <= line <= ranges[index][1]:
        return ranges[index][2]
    return MODULE


def _valid(database: Any) -> bool:
    return (isinstance(database, dict) and database.get("version") == _VERSION
            and database.get("python") == list(sys.version_info[:2])
            and isinstance(database.get("files"), dict) and isinstance(database.get("scenarios"), dict)
            and isinstance(database.get("global"), dict))


def _under(path: str, directories: list[str]) -> bool:
    for directory in directories:
        base = directory.strip("/")
        parent = base.rsplit("/", 1)[0] if "/" in base else ""
        if path.startswith(base + "/") or path == (f"{parent}/" if parent else "") + "environment.py":
            return True
    return False


def _changed_code(root: Path, table: dict[str, Any], changes: set[str],
                  steps: list[str]) -> tuple[set[str], set[str]] | None:
    """Changed function keys and changed files; None when every scenario must run."""
    keys: set[str] = set()
    files: set[str] = set()
    for path in changes:
        if path.rsplit("/", 1)[-1] in _RUN_SETTINGS or _under(path, steps):
            return None  # Settings and step definitions can change how any scenario runs.
        if not path.endswith(".py"):
            files.add(path)
            continue
        if path not in table:
            continue  # Never executed by the scenarios.
        try:
            current = python_blocks((root / path).read_bytes())
        except OSError:
            return None
        if current is None or current["module"] != table[path].get("module"):
            return None
        before = table[path].get("blocks", {})
        keys.update(f"{path}::{key}" for key in before.keys() | current["blocks"].keys()
                    if before.get(key) != current["blocks"].get(key))
    return keys, files


def select(root: Path, inspection: dict[str, Any], database: Any, changes: set[str] | None,
           steps: list[str]) -> set[str] | None:
    """Ids of the scenarios the change can affect, or None to run every scenario."""
    if changes is None or not _valid(database):
        return None
    changed = _changed_code(Path(root), database["files"], changes, steps)
    if changed is None:
        return None
    keys, files = changed
    # Code run outside the scenarios (imports, before_all) underlies all of them.
    scope = database["global"]
    if keys & set(scope.get("deps", [])) or files & set(scope.get("files", [])):
        return None
    selected = set()
    for document in inspection.get("documents", []):
        for scenario in document.get("scenarios", []):
            entry = database["scenarios"].get(scenario["id"])
            if (not isinstance(entry, dict) or not entry.get("passed") or entry.get("opaque")
                    or not isinstance(entry.get("deps"), list) or entry.get("sha256") != scenario.get("sha256")
                    or keys.intersection(entry["deps"]) or files.intersection(entry.get("files", []))):
                selected.add(scenario["id"])
    return selected


class _Sources:
    """Function blocks of the project files a run executed, each parsed once."""

    def __init__(self, root: Path):
        self.root = root
        self.parsed: dict[str, dict[str, Any] | None] = {}

    def blocks(self, path: str) -> dict[str, Any] | None:
        if path not in self.parsed:
            try:
                self.parsed[path] = python_blocks((self.root / path).read_bytes())
            except OSError:
                self.parsed[path] = None
        return self.parsed[path]

    def dependencies(self, coverage: dict[str, Any]) -> tuple[list[str], list[str]]:
        """Function keys executed and files read; code outside a parsable .py counts as a file."""
        keys, files = set(), set(coverage.get("files", []))
        for path, line in coverage.get("code", []):
            blocks = self.blocks(path) if path.endswith(".py") else None
            if blocks is None:
                files.add(path)
            else:
                keys.add(f"{path}::{_block_at(blocks['ranges'], line)}")
        return sorted(keys), sorted(files)


def _scenario_entry(scenario: dict[str, Any], observed: Any, measured: dict[str, bool],
                    sources: _Sources) -> dict[str, Any]:
    passed = isinstance(observed, dict) and observed.get("status") == "passed"
    entry = {"sha256": scenario.get("sha256"), "passed": passed, "deps": None, "files": [], "opaque": True}
    coverage = observed.get("coverage") if isinstance(observed, dict) and measured.get(observed.get("runner_id")) else None
    if isinstance(coverage, dict):
        entry["deps"], entry["files"] = sources.dependencies(coverage)
        entry["opaque"] = bool(coverage.get("opaque"))
    return entry


def _refreshed_table(table: dict[str, Any], referenced: set[str], refresh: set[str],
                     sources: _Sources) -> dict[str, Any]:
    """Hashes of every referenced file, recomputed for the files executed now or changed."""
    for path in referenced:
        blocks = sources.blocks(path) if path in refresh or path not in table else None
        if blocks is not None:
            table[path] = {"module": blocks["module"], "blocks": blocks["blocks"]}
    return {path: value for path, value in table.items() if path in referenced}


def record(root: Path, database: Any, inspection: dict[str, Any], execution: dict[str, Any],
           executed: set[str] | None, changes: set[str] | None) -> dict[str, Any]:
    """Merge one execution into the coverage table.

    ``executed`` is the selected ids (None for a complete run, which starts a
    new table). Function hashes are refreshed for the files this run executed
    and the files that changed since the previous run.
    """
    keep = executed is not None and _valid(database)
    scenarios = dict(database["scenarios"]) if keep else {}
    scope = database["global"] if keep else {"deps": [], "files": []}
    sources = _Sources(Path(root))
    known = {item["id"]: item for document in inspection.get("documents", []) for item in document.get("scenarios", [])}
    measured = execution.get("coverage", {}).get("runners", {})
    observed = {item.get("id"): item for item in execution.get("scenarios", []) if isinstance(item, dict)}
    for identity in (executed if executed is not None else known.keys()):
        if identity in known:
            scenarios[identity] = _scenario_entry(known[identity], observed.get(identity), measured, sources)
    scenarios = {identity: entry for identity, entry in scenarios.items() if identity in known}
    deps, files = set(scope.get("deps", [])), set(scope.get("files", []))
    for coverage in execution.get("coverage", {}).get("global", []):
        new_deps, new_files = sources.dependencies(coverage)
        deps.update(new_deps)
        files.update(new_files)
    referenced = {key.split("::", 1)[0] for entry in scenarios.values() for key in entry.get("deps") or []}
    referenced |= {key.split("::", 1)[0] for key in deps}
    table = _refreshed_table(dict(database["files"]) if keep else {}, referenced,
                             set(sources.parsed) | (changes or set()), sources)
    return {"version": _VERSION, "python": list(sys.version_info[:2]), "files": table, "scenarios": scenarios,
            "global": {"deps": sorted(deps), "files": sorted(files)}}


def steps_directories(root: Path, config: dict[str, Any]) -> list[str]:
    """Steps directories of the Python runners whose scenarios are measured."""
    from .runner import default_runners

    runners = config["runners"] if "runners" in config else default_runners(root)
    return [runner.get("steps", "tests/steps") for runner in runners if isinstance(runner, dict)
            and runner.get("language") == "python" and runner.get("command") is None]
