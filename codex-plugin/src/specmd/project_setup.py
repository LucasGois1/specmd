"""Enable the SpecMD plugin for everyone who opens the repository in Claude Code.

Installing the plugin with project scope already activates it; this adds the
marketplace declaration so collaborators receive it after trusting the folder.
specmd.toml and .specmdignore stay optional. Safe to run again.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MARKETPLACE = {"source": {"source": "github", "repo": "LucasGois1/specmd"}, "autoUpdate": True}
PLUGIN_ID = "specmd@specmd"
SETTINGS = ".claude/settings.json"


def _merge_claude_settings(root: Path) -> bool:
    path = root / SETTINGS
    settings: Any = {}
    if path.exists():
        settings = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(settings, dict):
            raise ValueError(f"{SETTINGS} precisa conter um objeto JSON.")
    before = json.dumps(settings, sort_keys=True)
    marketplaces = settings.setdefault("extraKnownMarketplaces", {})
    plugins = settings.setdefault("enabledPlugins", {})
    if not isinstance(marketplaces, dict) or not isinstance(plugins, dict):
        raise ValueError(f"extraKnownMarketplaces e enabledPlugins precisam ser objetos em {SETTINGS}.")
    marketplaces.setdefault("specmd", MARKETPLACE)
    plugins.setdefault(PLUGIN_ID, True)
    if json.dumps(settings, sort_keys=True) == before:
        return False
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def initialize(root: Path) -> dict[str, Any]:
    root = Path(root).resolve(strict=True)
    changed = [SETTINGS] if _merge_claude_settings(root) else []
    return {
        "status": "initialized", "root": str(root), "changed": changed,
        "message": (f"SpecMD habilitado para o time. Faça commit de {SETTINGS}: quem abrir o Claude Code neste "
                    "repositório e confiar na pasta recebe o plugin. specmd.toml e .specmdignore são opcionais."),
    }
