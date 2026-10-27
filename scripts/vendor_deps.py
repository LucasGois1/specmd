#!/usr/bin/env python3
"""Rebuild vendor/ from the pure-Python wheels pinned in pylock.toml.

The plugin runs from the marketplace clone with any Python 3.11+, so its
runtime dependencies ship in vendor/ instead of being installed on first use.
Every wheel is checked against the sha256 recorded in pylock.toml. --check
verifies, without network, that vendor/ still matches the lock.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tomllib
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
MANIFEST = VENDOR / "VENDOR.json"


def _locked_wheels() -> list[dict]:
    lock = tomllib.loads((ROOT / "pylock.toml").read_text(encoding="utf-8"))
    wheels = []
    for package in lock["packages"]:
        universal = [wheel for wheel in package.get("wheels", []) if wheel["url"].endswith("-none-any.whl")]
        if len(universal) != 1:
            raise SystemExit(f"{package['name']} does not have exactly one pure Python wheel in the lock.")
        wheel = universal[0]
        wheels.append({"name": package["name"], "version": package["version"],
                       "url": wheel["url"], "sha256": wheel["hashes"]["sha256"]})
    return sorted(wheels, key=lambda item: item["name"])


# Files the operating system leaves behind (Finder, Explorer); never part of a wheel.
OS_FILES = frozenset({".DS_Store", "Thumbs.db"})


def _tree_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted(VENDOR.rglob("*")):
        if path.is_file() and path != MANIFEST and "__pycache__" not in path.parts and path.name not in OS_FILES:
            digest.update(path.relative_to(VENDOR).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def build() -> dict:
    wheels = _locked_wheels()
    if VENDOR.exists():
        shutil.rmtree(VENDOR)
    VENDOR.mkdir()
    for wheel in wheels:
        with urllib.request.urlopen(wheel["url"], timeout=60) as response:  # noqa: S310 - pinned HTTPS URL
            data = response.read()
        if hashlib.sha256(data).hexdigest() != wheel["sha256"]:
            raise SystemExit(f"sha256 mismatch for {wheel['name']}.")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                name = member.filename
                if name.endswith("/") or ".data/" in name or name.startswith("/") or ".." in Path(name).parts:
                    continue
                target = VENDOR / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(member))
    manifest = {"source": "pylock.toml", "wheels": wheels, "tree_sha256": _tree_digest()}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def check() -> bool:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return manifest.get("wheels") == _locked_wheels() and manifest.get("tree_sha256") == _tree_digest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Only check vendor/ against the lock")
    args = parser.parse_args()
    if args.check:
        ok = check()
        print("vendor/ matches pylock.toml" if ok else "vendor/ differs from pylock.toml; run scripts/vendor_deps.py")
        return 0 if ok else 1
    manifest = build()
    print(json.dumps({"wheels": [f"{item['name']}=={item['version']}" for item in manifest["wheels"]]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
