#!/usr/bin/env python3
"""Build a small local Codex plugin from canonical sources, without caches.

Codex 0.163.0 recursively copies plugin sources without honoring .gitignore.
The generated digest manifest is a build inventory, not human approval or trust.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


REPOSITORY = Path(__file__).resolve().parent.parent
FIXED_FILES = (
    ".codex-plugin/plugin.json",
    "hooks/hooks.json",
    "scripts/codex_hook.py",
    "pyproject.toml",
)
MANIFEST = "bundle-manifest.json"


def build() -> dict[str, object]:
    dist = REPOSITORY / "dist"
    target = dist / "codex-plugin"
    if dist.is_symlink() or target.is_symlink():
        raise ValueError("A saída gerada não pode ser um link simbólico")
    files = list(FIXED_FILES)
    package = REPOSITORY / "src" / "specmd"
    if package.is_symlink() or not (package / "core.py").is_file():
        raise ValueError("O núcleo canônico src/specmd/core.py precisa existir antes do build")
    files.extend(str(path.relative_to(REPOSITORY)) for path in sorted(package.glob("*.py")))
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
        "schema": "specmd-codex-bundle-v1",
        "purpose": "Build inventory only; not a human approval, signature, or hook trust receipt.",
        "content_sha256": content_hash,
        "files_sha256": file_hashes,
    }
    dist.mkdir(exist_ok=True)
    if target.exists():
        previous = target / MANIFEST
        if not previous.is_file() or json.loads(previous.read_text()).get("schema") != manifest["schema"]:
            raise ValueError("Recusa substituir saída sem marcador de bundle gerado pelo SpecMD")
    with tempfile.TemporaryDirectory(prefix="specmd-build-", dir=dist) as staging_dir:
        staging = Path(staging_dir) / "plugin"
        for relative, data in payloads.items():
            output = staging / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
        (staging / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if target.exists():
            shutil.rmtree(target)
        staging.rename(target)
    return {"output": str(target), "files": len(payloads), "bytes": sum(len(data) for data in payloads.values()), "content_sha256": content_hash, "manifest": MANIFEST}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(build(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
