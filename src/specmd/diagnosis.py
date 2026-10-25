"""Why a scenario fails: legacy divergence, or a change made in this session.

A scenario that never passed, whose product code did not change in the
session, documents behaviour the existing code does differently: the agent
asks the developer which of the two is right. A scenario that existed at the
developer's last message and broke because the agent changed the code it runs
contradicts that change: update it if the developer confirmed the new rule,
otherwise fix the code. Step definitions are test code, not product code.

Without coverage (Java, Go, Python before 3.12) a scenario counts as
divergence only when it is new or changed since the developer's last message.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import contextlib
from pathlib import Path
import subprocess
from typing import Any

from . import state as local_state
from .selection import MODULE, _under, python_blocks

HISTORY_FILE = "scenario-history.json"
UNKNOWN = "?"  # The file's content at the start of the session cannot be recovered.


def remember_passed(root: Path, inspection: dict[str, Any], execution: dict[str, Any]) -> set[str]:
    """Scenarios that had passed before this run; then add the ones that passed now."""
    stored = local_state.read_local(root, HISTORY_FILE).get("passed")
    passed = dict(stored) if isinstance(stored, dict) else {}
    before = set(passed)
    now = datetime.now(timezone.utc).isoformat()
    for scenario in execution["scenarios"]:
        if scenario.get("status") == "passed":
            passed.setdefault(scenario.get("id"), now)
    known = {item["id"] for document in inspection["documents"] for item in document["scenarios"]}
    with contextlib.suppress(OSError, ValueError):
        local_state.write_local(root, HISTORY_FILE, {"passed": {key: value for key, value in passed.items() if key in known}})
    return before


def _git_bytes(root: Path, *arguments: str) -> bytes | None:
    try:
        completed = subprocess.run(["git", "--no-optional-locks", "-C", str(root), *arguments],
                                   capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout if completed.returncode == 0 else None


def _source_at(root: Path, snapshot: dict[str, Any], path: str) -> bytes | None:
    """A file's content when the snapshot was taken; b"" when it did not exist; None when unknown."""
    listed = snapshot.get("files", {}).get(path)
    if listed is not None:
        if listed[1] is None:
            return b""
        return _git_bytes(root, "cat-file", "blob", str(listed[1]))
    if snapshot.get("head") is None:
        return b""
    content = _git_bytes(root, "show", f"{snapshot['head']}:{path}")
    return content if content is not None else b""


class _WithoutFunctions(ast.NodeTransformer):
    def visit_FunctionDef(self, node: ast.AST) -> None:
        return None

    visit_AsyncFunctionDef = visit_FunctionDef


def _module_core(source: bytes) -> str | None:
    """The module level without function definitions: adding a function does not change it,
    changing a constant, an import or a class attribute does."""
    try:
        return ast.dump(_WithoutFunctions().visit(ast.parse(source)))
    except (SyntaxError, ValueError):
        return None


def _function_changes(root: Path, baseline: dict[str, Any], path: str) -> Any:
    """Function keys changed in one Python file; None for the whole file, UNKNOWN without its earlier content."""
    old_source = _source_at(root, baseline, path)
    if old_source is None:
        return UNKNOWN
    try:
        source = (root / path).read_bytes()
    except OSError:
        return None
    current, previous = python_blocks(source), python_blocks(old_source) if old_source else None
    if current is None or previous is None or _module_core(source) != _module_core(old_source):
        return None
    return {key for key in previous["blocks"].keys() | current["blocks"].keys()
            if previous["blocks"].get(key) != current["blocks"].get(key)}


def session_changes(root: Path, baseline: Any, now: dict[str, Any]) -> dict[str, Any] | None:
    """Changed files since the session started, with the function keys changed in each
    Python file (None: the whole file; UNKNOWN: its earlier content is not recoverable).
    None when the change cannot be told at all."""
    from .workflow import code_changes

    changed = code_changes(root, baseline, now)
    if changed is None or "files" not in now:
        return None
    return {path: _function_changes(root, baseline, path) if path.endswith(".py") else None for path in changed}


def _dependency(key: str, changes: dict[str, Any], steps: list[str]) -> Any:
    """True when the session changed this product function, UNKNOWN when it cannot be told, else False."""
    path, _, block = key.partition("::")
    if path not in changes or _under(path, steps):
        return False
    keys = changes[path]
    if keys == UNKNOWN:
        return UNKNOWN
    return keys is None or block in keys or block == MODULE


def _touched(entry: Any, changes: dict[str, Any], steps: list[str]) -> bool | None:
    """Whether the session changed product code or files this scenario ran; None when it cannot be told."""
    deps = entry.get("deps") if isinstance(entry, dict) else None
    if not isinstance(deps, list):
        return None
    statuses = [_dependency(key, changes, steps) for key in deps]
    if True in statuses or any(path in changes for path in entry.get("files", [])):
        return True
    return None if UNKNOWN in statuses else False


def classify(inspection: dict[str, Any], execution: dict[str, Any], database: Any, passed_before: set[str],
             prompt: Any, changes: dict[str, Any] | None, steps: list[str]) -> dict[str, list[str]]:
    """Failing scenarios that look like legacy divergence, and the ones the agent's change contradicts."""
    baseline = {item.get("id"): item.get("sha256") for document in prompt.get("documents", {}).values()
                for item in document.get("scenarios", [])} if isinstance(prompt, dict) else {}
    current = {item["id"]: item.get("sha256") for document in inspection["documents"] for item in document["scenarios"]}
    entries = database.get("scenarios", {}) if isinstance(database, dict) else {}
    divergent, contradicted = [], []
    for failure in execution["failures"]:
        identity = failure.get("id")
        if not any(step.get("status") == "failed" for step in failure.get("steps", [])):
            continue  # Undefined or skipped steps are missing work, not a disagreement.
        touched = _touched(entries.get(identity), changes, steps) if changes is not None else None
        existed = identity in baseline and baseline[identity] == current.get(identity)
        if identity not in passed_before and (touched is False or (touched is None and not existed)):
            divergent.append(identity)
        elif existed and (touched or (touched is None and bool(changes))):
            contradicted.append(identity)
    return {"divergent": divergent, "contradicted": contradicted}
