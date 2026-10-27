"""Configuration loading for specmd.toml; every key is optional."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import tomllib
from typing import Any

from .messages import LANGUAGES, text as t, use as use_language


class ConfigError(ValueError):
    """A project configuration is absent, unreadable, or invalid."""


def read_regular_file(path: Path) -> bytes:
    """Read a stable regular file without following a final symlink."""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise OSError(t("The path must be a regular file, not a symbolic link", "O caminho deve ser um arquivo regular, sem link simbólico"))
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise OSError(t("The file changed while opening; inspect again", "O arquivo mudou durante a abertura; repita a inspeção"))
        chunks = []
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        current = path.lstat()

        def signature(value: os.stat_result) -> tuple:
            return (value.st_dev, value.st_ino, value.st_size,
                    value.st_mtime_ns, value.st_ctime_ns)

        if signature(opened) != signature(after) or signature(after) != signature(current):
            raise OSError(t("The file changed while reading; inspect again", "O arquivo mudou durante a leitura; repita a inspeção"))
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ConfigError(t(f"{label} must be non-empty text without surrounding spaces.",
                            f"{label} deve ser texto não vazio, sem espaços externos."))
    return value


def _keys(value: dict, allowed: set[str], label: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigError(t(f"Unsupported keys in {label}: {names}.", f"Campos não suportados em {label}: {names}."))


# Keys from the earlier audit design are accepted and ignored.
_LEGACY_KEYS = {"project_id", "repository_id", "traceability", "evidence"}


def parse_config(data: bytes) -> dict[str, Any]:
    """Validate specmd.toml; every key is optional and an empty file is valid."""
    try:
        config = tomllib.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(t(f"Invalid TOML configuration: {exc}", f"Configuração TOML inválida: {exc}")) from exc
    if "language" in config:
        if config["language"] not in LANGUAGES:
            raise ConfigError(t('language must be "en" or "pt".', 'language deve ser "en" ou "pt".'))
        use_language(config["language"])
    _keys(config, {"schema", "language", "gherkin_language", "wip_tags", "run", "runners"} | _LEGACY_KEYS, "specmd.toml")
    if "schema" in config and (type(config["schema"]) is not int or config["schema"] not in {1, 2}):
        raise ConfigError(t("schema, when present, must be the integer 1 or 2.", "schema, quando presente, deve ser o inteiro 1 ou 2."))
    if "gherkin_language" in config:
        _text(config["gherkin_language"], "gherkin_language")
    wip_tags = config.get("wip_tags", ["wip"])
    if not isinstance(wip_tags, list):
        raise ConfigError(t("wip_tags must be a list of texts.", "wip_tags deve ser uma lista de textos."))
    for tag in wip_tags:
        _text(tag, "wip_tags")
    run = config.get("run", {})
    if not isinstance(run, dict):
        raise ConfigError(t("run must be a table.", "run deve ser uma tabela."))
    _keys(run, {"on_stop", "timeout"}, "run")
    if "on_stop" in run and type(run["on_stop"]) is not bool:
        raise ConfigError(t("run.on_stop must be a boolean.", "run.on_stop deve ser booleano."))
    if "timeout" in run and (type(run["timeout"]) is not int or run["timeout"] <= 0):
        raise ConfigError(t("run.timeout must be a positive integer.", "run.timeout deve ser um inteiro positivo."))

    runners = config.get("runners", [])
    if not isinstance(runners, list):
        raise ConfigError(t("runners must be a list of tables.", "runners deve ser uma lista de tabelas."))
    identifiers: set[str] = set()
    for index, runner in enumerate(runners, start=1):
        label = f"runners[{index}]"
        if not isinstance(runner, dict):
            raise ConfigError(t(f"{label} must be a table.", f"{label} deve ser uma tabela."))
        _keys(runner, {"id", "language", "command", "steps", "timeout", "paths", "python"}, label)
        identifier = _text(runner.get("id"), f"{label}.id")
        _text(runner.get("language"), f"{label}.language")
        if identifier in identifiers:
            raise ConfigError(t(f"Duplicate runner ID: {identifier}.", f"ID de runner duplicado: {identifier}."))
        identifiers.add(identifier)
        for key in ("command", "paths"):
            if key not in runner:
                continue
            sequence = runner[key]
            if not isinstance(sequence, list) or (key == "command" and not sequence):
                raise ConfigError(t(f"{label}.{key} must be a" + (" non-empty" if key == "command" else "") + " list of texts.",
                                    f"{label}.{key} deve ser uma lista de textos" + (" não vazia." if key == "command" else ".")))
            if key == "command":
                if not all(isinstance(item, str) for item in sequence) or not sequence[0].strip():
                    raise ConfigError(t(f"{label}.command needs a non-empty executable and text arguments.",
                                        f"{label}.command exige um executável não vazio e argumentos textuais."))
            else:
                for item in sequence:
                    _text(item, f"{label}.{key}")
        for key in ("steps", "python"):
            if key in runner:
                _text(runner[key], f"{label}.{key}")
        if "timeout" in runner and (type(runner["timeout"]) is not int or runner["timeout"] <= 0):
            raise ConfigError(t(f"{label}.timeout must be a positive integer.", f"{label}.timeout deve ser um inteiro positivo."))
    return config


def load_config(root: Path) -> dict[str, Any]:
    """Load root/specmd.toml; without the file every option takes its default."""
    path = Path(root) / "specmd.toml"
    if not path.exists() and not path.is_symlink():
        return {}
    try:
        return parse_config(read_regular_file(path))
    except OSError as exc:
        raise ConfigError(t(f"Could not read specmd.toml: {exc}", f"Não foi possível ler specmd.toml: {exc}")) from exc
