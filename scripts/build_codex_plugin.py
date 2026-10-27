#!/usr/bin/env python3
"""Build the plugin bundle (Codex and Claude Code) from canonical sources.

The bundle is versioned in codex-plugin/ because Codex installs a plugin by
copying its directory from the marketplace source, a local path or a Git
repository, without honoring .gitignore; the bundle keeps that copy to the
plugin's own files. `--check` verifies that the committed bundle matches the
sources, as CI does. The digest manifest is a build inventory, not human
approval or hook trust.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile


REPOSITORY = Path(__file__).resolve().parent.parent
TARGET = REPOSITORY / "codex-plugin"
FIXED_FILES = (
    ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    "hooks/hooks.json",
    "scripts/specmd_hook.py",
    "scripts/specmd_cli.py",
    "scripts/specmd_bootstrap.py",
    "pyproject.toml",
    "pylock.toml",
)
TREES = ("commands", "skills", "vendor")
OS_FILES = frozenset({".DS_Store", "Thumbs.db"})
MANIFEST = "bundle-manifest.json"
SCHEMA = "specmd-codex-bundle-v1"


def collect() -> tuple[dict[str, bytes], dict[str, object]]:
    """The bundle's files and its manifest, read from the canonical sources."""
    files = list(FIXED_FILES)
    package = REPOSITORY / "src" / "specmd"
    if package.is_symlink() or not (package / "core.py").is_file():
        raise ValueError("O núcleo canônico src/specmd/core.py precisa existir antes do build")
    files.extend(str(path.relative_to(REPOSITORY)) for path in sorted(package.glob("*.py")))
    for tree in TREES:
        files.extend(str(path.relative_to(REPOSITORY)) for path in sorted((REPOSITORY / tree).rglob("*"))
                     if path.is_file() and "__pycache__" not in path.parts and path.name not in OS_FILES)
    payloads: dict[str, bytes] = {}
    for relative in sorted(files):
        source = REPOSITORY / relative
        if source.is_symlink() or any(parent.is_symlink() for parent in source.parents if parent != REPOSITORY.parent):
            raise ValueError(f"Fonte canônica não pode ser link simbólico: {relative}")
        if not source.is_file():
            raise ValueError(f"Fonte obrigatória ausente: {relative}")
        data = source.read_bytes()
        if relative.endswith(".py"):
            ast.parse(data, filename=relative)
        if relative.endswith(".json"):
            json.loads(data)
        payloads[relative] = data
    file_hashes = {relative: hashlib.sha256(data).hexdigest() for relative, data in payloads.items()}
    content_hash = hashlib.sha256(json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    manifest: dict[str, object] = {
        "schema": SCHEMA,
        "purpose": "Build inventory only; not a human approval, signature, or hook trust receipt.",
        "content_sha256": content_hash,
        "files_sha256": file_hashes,
    }
    return payloads, manifest


def _committed(target: Path) -> dict[str, bytes]:
    return {path.relative_to(target).as_posix(): path.read_bytes() for path in sorted(target.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts and path.name not in OS_FILES}


def build(target: Path = TARGET) -> dict[str, object]:
    if target.is_symlink():
        raise ValueError("A saída gerada não pode ser um link simbólico")
    payloads, manifest = collect()
    if target.exists():
        previous = target / MANIFEST
        if not previous.is_file() or json.loads(previous.read_text()).get("schema") != SCHEMA:
            raise ValueError("Recusa substituir saída sem marcador de bundle gerado pelo SpecMD")
    with tempfile.TemporaryDirectory(prefix="specmd-build-", dir=target.parent) as staging_dir:
        staging = Path(staging_dir) / "plugin"
        for relative, data in payloads.items():
            output = staging / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
        (staging / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if target.exists():
            shutil.rmtree(target)
        staging.rename(target)
    return {"output": str(target), "files": len(payloads), "bytes": sum(len(data) for data in payloads.values()),
            "content_sha256": manifest["content_sha256"], "manifest": MANIFEST}


def check(target: Path = TARGET) -> list[str]:
    """Paths where the committed bundle differs from a fresh build; empty when it matches."""
    payloads, manifest = collect()
    expected = {**payloads, MANIFEST: (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")}
    actual = _committed(target) if target.is_dir() else {}
    return sorted(path for path in expected.keys() | actual.keys() if expected.get(path) != actual.get(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="só conferir codex-plugin/ contra as fontes")
    args = parser.parse_args()
    if args.check:
        differences = check()
        if differences:
            print("codex-plugin/ diverge das fontes; rode scripts/build_codex_plugin.py e faça commit:")
            print("\n".join(f"- {path}" for path in differences[:20]))
            return 1
        print("codex-plugin/ confere com as fontes")
        return 0
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
