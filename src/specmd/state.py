"""Local, reconstructible hook state kept in .specmd/local/state.json.

The state only remembers observations (last run, what the developer last saw,
how many times Stop already returned feedback). Deleting it is always safe.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, Iterator

STATE_FILE = "state.json"
LOCK_FILE = "state.lock"


def _local_directory(root: Path) -> Path:
    directory = Path(root)
    for part in (".specmd", "local"):
        directory = directory / part
        if directory.is_symlink():
            raise ValueError("O estado local não pode atravessar links simbólicos.")
        directory.mkdir(exist_ok=True)
    ignore = directory / ".gitignore"
    if not ignore.exists() and not ignore.is_symlink():
        # The state ignores itself, so activating the plugin never dirties `git status`.
        ignore.write_text("*\n", encoding="utf-8")
    return directory


def load(root: Path) -> dict[str, Any]:
    path = Path(root) / ".specmd" / "local" / STATE_FILE
    try:
        if path.is_symlink():
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def save(root: Path, state: dict[str, Any]) -> None:
    directory = _local_directory(root)
    destination = directory / STATE_FILE
    if destination.is_symlink():
        raise ValueError("O estado local não pode ser um link simbólico.")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(state, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


@contextlib.contextmanager
def locked(root: Path, timeout: float | None = None) -> Iterator[None]:
    """Serialize state updates; with a timeout, raise TimeoutError instead of waiting."""
    path = _local_directory(root) / LOCK_FILE
    with open(path, "a", encoding="utf-8") as stream:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | (fcntl.LOCK_NB if deadline is not None else 0))
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Estado do SpecMD ocupado por outro hook.")
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def update(root: Path, change: Callable[[dict[str, Any]], None], timeout: float | None = None) -> dict[str, Any]:
    """Load, change and save the state under the lock; return the saved state."""
    with locked(root, timeout):
        state = load(root)
        change(state)
        save(root, state)
        return state
