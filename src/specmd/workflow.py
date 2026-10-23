"""Inspection plus scenario execution, remembered in the local hook state.

There is no approval step: the developer confirms scenarios in the
conversation, and this module only reports whether documentation and code
agree.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from . import state as hook_state
from .core import _PRUNED_DIRECTORIES, inspect_project

# Writes here must never count as code changes, or every hook would see one.
_EXCLUDED_TOP_LEVEL = {".git", ".specmd", ".claude", ".codex"}
_IGNORED_NAMES = {".DS_Store"}
_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_WALK_LIMIT = 50_000


def _listed_files(root: Path) -> list[str]:
    """Tracked and untracked files that Git does not ignore, or a pruned walk."""
    try:
        completed = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "-co", "--exclude-standard"],
                                   capture_output=True, timeout=20)
        if completed.returncode == 0:
            return [item for item in completed.stdout.decode("utf-8", "surrogateescape").split("\0") if item]
    except (OSError, subprocess.TimeoutExpired):
        pass
    files: list[str] = []
    for directory, names, filenames in os.walk(root, followlinks=False):
        names[:] = sorted(name for name in names if name not in _PRUNED_DIRECTORIES)
        base = Path(directory)
        files.extend((base / name).relative_to(root).as_posix() for name in filenames)
        if len(files) > _WALK_LIMIT:
            raise ValueError("Projeto grande demais para a varredura sem Git.")
    return files


def fingerprint_code(root: Path) -> str:
    """Digest of every non-Markdown file's metadata; contents are not read."""
    root = Path(root)
    entries: list[list[Any]] = []
    for relative in sorted(set(_listed_files(root))):
        parts = relative.split("/")
        if parts[0] in _EXCLUDED_TOP_LEVEL or parts[-1] in _IGNORED_NAMES:
            continue
        if Path(relative).suffix.lower() in _MARKDOWN_SUFFIXES:
            continue
        try:
            info = os.lstat(root / relative)
            entries.append([relative, info.st_size, info.st_mtime_ns, info.st_mode])
        except FileNotFoundError:
            entries.append([relative, None])
    return hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()


def scenario_count(inspection: dict[str, Any]) -> int:
    return sum(len(document.get("scenarios", [])) for document in inspection.get("documents", []))


def check_project(root: Path) -> dict[str, Any]:
    """Inspect the documentation and attach the last run when it is still current."""
    root = Path(root).resolve(strict=True)
    result = inspect_project(root)
    if result["status"] != "ready":
        return result
    last = hook_state.load(root).get("last_run")
    if isinstance(last, dict):
        current = (last.get("spec_fp") == result["spec_fp"]
                   and fingerprint_code(root) in last.get("code_fps", []))
        result["run"] = {**last, "current": current}
        if current:
            result["status"] = "passing" if last.get("passed") else "failing"
    return result


def run_project(root: Path) -> dict[str, Any]:
    """Run every documented scenario and remember the result for the hooks."""
    from .config import load_config
    from .runner import execute_project

    root = Path(root).resolve(strict=True)
    inspection = inspect_project(root)
    if inspection["status"] != "ready":
        return inspection
    before = fingerprint_code(root)
    execution = execute_project(root, inspection, load_config(root))
    after = fingerprint_code(root)
    last_run = {
        "at": datetime.now(timezone.utc).isoformat(),
        "spec_fp": inspection["spec_fp"],
        # The post-run digest absorbs artifacts written by the tests themselves.
        "code_fps": sorted({before, after}),
        "passed": execution["passed"],
        "scenarios": len(execution["scenarios"]),
        "expected": scenario_count(inspection),
        "failures": execution["failures"],
        "findings": execution["findings"],
    }
    hook_state.update(root, lambda state: state.__setitem__("last_run", last_run))
    return {**inspection, "status": "passing" if execution["passed"] else "failing",
            "run": {**last_run, "current": True}}
