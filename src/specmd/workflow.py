"""Inspection plus scenario execution, remembered in the local hook state.

There is no approval step: the developer confirms scenarios in the
conversation, and this module only reports whether documentation and code
agree.

The code side is tracked through snapshots: in a Git repository, the current
commit plus the content of the files that differ from it. Taking one costs a
`git status`, not a read of the whole project, and committing the work does
not count as a change.
"""
from __future__ import annotations

import contextlib
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from typing import Any

from . import state as hook_state
from .core import _PRUNED_DIRECTORIES, inspect_project

# Writes here must never count as code changes, or every hook would see one.
_EXCLUDED_TOP_LEVEL = {".git", ".specmd", ".claude", ".codex"}
_IGNORED_NAMES = {".DS_Store"}
_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_WALK_LIMIT = 50_000
_HASH_LIMIT = 32 * 1024 * 1024
_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def _is_code(relative: str) -> bool:
    parts = relative.split("/")
    return (parts[0] not in _EXCLUDED_TOP_LEVEL and parts[-1] not in _IGNORED_NAMES
            and Path(relative).suffix.lower() not in _MARKDOWN_SUFFIXES)


def _git(root: Path, *arguments: str) -> str | None:
    try:
        completed = subprocess.run(["git", "--no-optional-locks", "-C", str(root), *arguments],
                                   capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.decode("utf-8", "surrogateescape") if completed.returncode == 0 else None


def _object(value: str) -> str | None:
    return None if not value.strip("0") else value


def _content_id(path: Path, algorithm: str) -> str | None:
    """The Git object id of a working-tree file, comparable with the ids Git reports."""
    try:
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode):
            data = os.fsencode(os.readlink(path))
        elif stat.S_ISREG(info.st_mode) and info.st_size <= _HASH_LIMIT:
            data = path.read_bytes()
        else:
            return f"stat:{info.st_mode:o}:{info.st_size}:{info.st_mtime_ns}"
    except FileNotFoundError:
        return None
    return hashlib.new(algorithm, b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def _walk_digest(root: Path) -> str:
    """Without Git: a digest of every non-Markdown file's metadata in a pruned walk."""
    entries: list[list[Any]] = []
    for directory, names, filenames in os.walk(root, followlinks=False):
        names[:] = sorted(name for name in names if name not in _PRUNED_DIRECTORIES)
        base = Path(directory)
        for name in sorted(filenames):
            relative = (base / name).relative_to(root).as_posix()
            if _is_code(relative):
                info = os.lstat(base / name)
                entries.append([relative, info.st_size, info.st_mtime_ns, info.st_mode])
        if len(entries) > _WALK_LIMIT:
            raise ValueError("Projeto grande demais para a varredura sem Git.")
    return hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()


def code_snapshot(root: Path) -> dict[str, Any]:
    """The state of the non-Markdown files: commit plus files that differ from it."""
    root = Path(root)
    output = _git(root, "status", "--porcelain=v2", "-z", "--branch", "--no-renames", "--untracked-files=all")
    if output is None:
        return {"walk": _walk_digest(root)}
    head, differing = None, {}
    for record in output.split("\0"):
        if record.startswith("# branch.oid "):
            value = record.split(" ", 2)[2]
            head = None if value == "(initial)" else value
        elif record.startswith("1 "):
            fields = record.split(" ", 8)
            differing[fields[8]] = _object(fields[6])
        elif record.startswith("u "):
            fields = record.split(" ", 10)
            differing[fields[10]] = _object(fields[8])
        elif record.startswith("? ") and not set(record[2:].split("/")[:-1]) & _PRUNED_DIRECTORIES:
            differing[record[2:]] = None
    algorithm = "sha256" if head and len(head) == 64 else "sha1"
    return {"head": head, "files": {path: [committed, _content_id(root / path, algorithm)]
                                    for path, committed in sorted(differing.items()) if _is_code(path)}}


def _valid_snapshot(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if "walk" in value:
        return isinstance(value["walk"], str)
    files = value.get("files")
    return ((value.get("head") is None or isinstance(value.get("head"), str)) and isinstance(files, dict)
            and all(isinstance(pair, list) and len(pair) == 2 for pair in files.values()))


def _between_commits(root: Path, old: str | None, new: str | None) -> dict[str, list[str | None]] | None:
    output = _git(root, "diff", "--raw", "-z", "--no-renames", "--no-abbrev", old or _EMPTY_TREE, new or _EMPTY_TREE)
    if output is None:
        return None
    fields = output.split("\0")
    changes = {}
    for meta, path in zip(fields[0::2], fields[1::2]):
        parts = meta.split(" ")
        if len(parts) >= 4:
            changes[path] = [_object(parts[2]), _object(parts[3])]
    return changes


def code_changes(root: Path, before: Any, after: Any) -> set[str] | None:
    """Non-Markdown files whose content differs between two snapshots; None when unknown."""
    if not (_valid_snapshot(before) and _valid_snapshot(after)):
        return None
    if "walk" in before or "walk" in after:
        return set() if before == after else None
    first, second = before["files"], after["files"]
    between: dict[str, list[str | None]] = {}
    if before["head"] != after["head"]:
        between = _between_commits(root, before["head"], after["head"])
        if between is None:
            return None
    return {path for path in first.keys() | second.keys() | between.keys()
            if _is_code(path) and _content(path, first, second, between, 0) != _content(path, second, first, between, 1)}


def _content(path: str, own: dict[str, Any], other: dict[str, Any], between: dict[str, list[str | None]],
             side: int) -> str | None:
    """A file's content in one snapshot: listed in it, changed between the commits, or as committed."""
    if path in own:
        return own[path][1]
    if path in between:
        return between[path][side]
    return other[path][0]  # Unlisted in both snapshots with the same commit content.


def matches_code(root: Path, run: dict[str, Any], now: dict[str, Any]) -> bool:
    """True when the code is as it was before or after the run."""
    snapshots = run.get("code") if isinstance(run.get("code"), list) else []
    return any(code_changes(root, snapshot, now) == set() for snapshot in snapshots)


def _reported(run: dict[str, Any]) -> dict[str, Any]:
    """A run as shown to the agent and the CLI, without the code snapshots."""
    return {key: value for key, value in run.items() if key != "code"}


def scenario_count(inspection: dict[str, Any]) -> int:
    return sum(len(document.get("scenarios", [])) for document in inspection.get("documents", []))


def check_project(root: Path, now: dict[str, Any] | None = None) -> dict[str, Any]:
    """Inspect the documentation and attach the last run when it is still current."""
    root = Path(root).resolve(strict=True)
    result = inspect_project(root)
    if result["status"] != "ready":
        return result
    last = hook_state.load(root).get("last_run")
    if isinstance(last, dict):
        current = (last.get("spec_fp") == result["spec_fp"]
                   and matches_code(root, last, now if now is not None else code_snapshot(root)))
        result["run"] = {**_reported(last), "current": current}
        if current:
            result["status"] = "passing" if last.get("passed") else "failing"
    return result


def run_project(root: Path, affected: bool = False) -> dict[str, Any]:
    """Run the documented scenarios and remember the result for the hooks.

    With ``affected``, only the scenarios the code change since the last run
    can affect are executed (see selection.py); the others keep their result.
    """
    from .config import load_config
    from .runner import execute_project
    from .selection import COVERAGE_FILE, record, select, steps_directories

    root = Path(root).resolve(strict=True)
    inspection = inspect_project(root)
    if inspection["status"] != "ready":
        return inspection
    config = load_config(root)
    before = code_snapshot(root)
    last = hook_state.load(root).get("last_run")
    previous = last.get("code") if isinstance(last, dict) and isinstance(last.get("code"), list) else []
    changes = code_changes(root, previous[-1], before) if previous else None
    database = hook_state.read_local(root, COVERAGE_FILE)
    only = select(root, inspection, database, changes, steps_directories(root, config)) if affected else None
    execution = execute_project(root, inspection, config, only=only)
    after = code_snapshot(root)
    with contextlib.suppress(OSError, ValueError):
        hook_state.write_local(root, COVERAGE_FILE, record(root, database, inspection, execution, only, changes))
    last_run = {
        "at": datetime.now(timezone.utc).isoformat(),
        "spec_fp": inspection["spec_fp"],
        # The post-run snapshot absorbs artifacts written by the tests themselves.
        "code": [before, after],
        "passed": execution["passed"],
        "scenarios": len(execution["scenarios"]),
        "expected": scenario_count(inspection),
        "unselected": execution["unselected"],
        "failures": execution["failures"],
        "findings": execution["findings"],
    }
    hook_state.update(root, lambda state: state.__setitem__("last_run", last_run))
    return {**inspection, "status": "passing" if execution["passed"] else "failing",
            "run": {**_reported(last_run), "current": True}}
