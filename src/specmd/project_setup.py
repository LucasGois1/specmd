"""Prepare a repository so the SpecMD plugin loads for everyone who opens it.

Safe to run again: existing files are kept and only missing entries are added.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core import IGNORE_FILE
from .demo import DEFAULT_IGNORE, initial_config

MARKETPLACE = {"source": {"source": "github", "repo": "LucasGois1/specmd"}, "autoUpdate": True}
PLUGIN_ID = "specmd@specmd"
LOCAL_STATE = ".specmd/local/"


def _merge_claude_settings(root: Path) -> bool:
    path = root / ".claude" / "settings.json"
    settings: Any = {}
    if path.exists():
        settings = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(settings, dict):
            raise ValueError(".claude/settings.json precisa conter um objeto JSON.")
    before = json.dumps(settings, sort_keys=True)
    marketplaces = settings.setdefault("extraKnownMarketplaces", {})
    plugins = settings.setdefault("enabledPlugins", {})
    if not isinstance(marketplaces, dict) or not isinstance(plugins, dict):
        raise ValueError("extraKnownMarketplaces e enabledPlugins precisam ser objetos em .claude/settings.json.")
    marketplaces.setdefault("specmd", MARKETPLACE)
    plugins.setdefault(PLUGIN_ID, True)
    if json.dumps(settings, sort_keys=True) == before:
        return False
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def _ensure_gitignore(root: Path) -> bool:
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if any(line.strip() in {LOCAL_STATE, LOCAL_STATE.rstrip("/"), ".specmd/", ".specmd"} for line in text.splitlines()):
        return False
    path.write_text(text + ("" if not text or text.endswith("\n") else "\n") + LOCAL_STATE + "\n", encoding="utf-8")
    return True


def initialize(root: Path) -> dict[str, Any]:
    root = Path(root).resolve(strict=True)
    changed = []
    if not (root / "specmd.toml").exists():
        (root / "specmd.toml").write_text(initial_config(), encoding="utf-8")
        changed.append("specmd.toml")
    if not (root / IGNORE_FILE).exists():
        (root / IGNORE_FILE).write_text(DEFAULT_IGNORE, encoding="utf-8")
        changed.append(IGNORE_FILE)
    if _merge_claude_settings(root):
        changed.append(".claude/settings.json")
    if _ensure_gitignore(root):
        changed.append(".gitignore")
    return {
        "status": "initialized", "root": str(root), "changed": changed,
        "message": ("SpecMD ativado. Faça commit de specmd.toml, .specmdignore e .claude/settings.json: quem abrir o "
                    "Claude Code neste repositório e confiar na pasta recebe o plugin automaticamente."),
    }
