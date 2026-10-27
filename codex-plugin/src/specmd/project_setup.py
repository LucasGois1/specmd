"""Enable the SpecMD plugin for everyone who opens the repository in Claude Code or Codex.

Installing the plugin with project scope already activates it in Claude Code;
this adds the marketplace declaration so collaborators receive it after
trusting the folder. Codex installs plugins per user, so the project enables
SpecMD in its own .codex/config.toml. specmd.toml and .specmdignore stay
optional. Safe to run again; existing entries are kept.
"""
from __future__ import annotations

import json
from pathlib import Path
import tomllib
from typing import Any

from .messages import text as t

MARKETPLACE = {"source": {"source": "github", "repo": "LucasGois1/specmd"}, "autoUpdate": True}
PLUGIN_ID = "specmd@specmd"
SETTINGS = ".claude/settings.json"
CODEX_CONFIG = ".codex/config.toml"


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


def _enable_in_codex(root: Path) -> bool:
    """Add [plugins."specmd@specmd"] to the project's Codex config unless it already mentions SpecMD."""
    path = root / CODEX_CONFIG
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    try:
        config = tomllib.loads(text)
    except ValueError as error:
        raise ValueError(t(f"{CODEX_CONFIG} is not valid TOML: {error}", f"{CODEX_CONFIG} não é TOML válido: {error}")) from error
    plugins = config.get("plugins", {})
    if isinstance(plugins, dict) and any(isinstance(key, str) and key.split("@")[0] == "specmd" for key in plugins):
        return False  # An existing entry, enabled or not, is the project's decision.
    if not text.strip():
        separator = ""
    elif text.endswith("\n"):
        separator = "\n"
    else:
        separator = "\n\n"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text + separator + f'[plugins."{PLUGIN_ID}"]\nenabled = true\n', encoding="utf-8")
    return True


def initialize(root: Path) -> dict[str, Any]:
    root = Path(root).resolve(strict=True)
    changed = [SETTINGS] if _merge_claude_settings(root) else []
    changed += [CODEX_CONFIG] if _enable_in_codex(root) else []
    return {
        "status": "initialized", "root": str(root), "changed": changed,
        "message": t(f"SpecMD enabled for the team. Commit {SETTINGS} and {CODEX_CONFIG}: whoever opens Claude Code "
                     "in this repository and trusts the folder gets the plugin; in Codex, whoever has the plugin "
                     "installed has it active in this trusted project. specmd.toml and .specmdignore are optional.",
                     f"SpecMD habilitado para o time. Faça commit de {SETTINGS} e {CODEX_CONFIG}: quem abrir o "
                     "Claude Code neste repositório e confiar na pasta recebe o plugin; no Codex, quem tiver o plugin "
                     "instalado o terá ativo neste projeto confiável. specmd.toml e .specmdignore são opcionais."),
    }
