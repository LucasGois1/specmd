"""User-facing text: English by default, Portuguese when specmd.toml sets language = "pt".

Each message is written in both languages at the place it is used, so the two
versions stay side by side. Hooks and the CLI run one project per process; the
project's language is set once, after its configuration is read.
"""
from __future__ import annotations

from pathlib import Path

LANGUAGES = ("en", "pt")
_language = "en"


def use(language: object) -> None:
    global _language
    _language = language if language in LANGUAGES else "en"


def current() -> str:
    return _language


def text(en: str, pt: str) -> str:
    return pt if _language == "pt" else en


def plural(count: int, singular: tuple[str, str], several: tuple[str, str]) -> str:
    """`count` followed by the English or Portuguese singular or plural form."""
    forms = singular if count == 1 else several
    return f"{count} {text(*forms)}"


def use_project(root: Path) -> None:
    """Use the project's configured language; an unreadable configuration keeps English."""
    from .config import ConfigError, load_config

    try:
        use(load_config(root).get("language", "en"))
    except (OSError, ConfigError):
        use("en")
