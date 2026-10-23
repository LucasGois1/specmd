"""Strict, versioned configuration loading for the experimental SpecMD core."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import tomllib
from typing import Any


class ConfigError(ValueError):
    """A project configuration is absent, unreadable, or invalid."""


def read_regular_file(path: Path) -> bytes:
    """Read a stable regular file without following a final symlink."""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise OSError("O caminho deve ser um arquivo regular, sem link simbólico")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise OSError("O arquivo mudou durante a abertura; repita a inspeção")
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
            raise OSError("O arquivo mudou durante a leitura; repita a inspeção")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ConfigError(f"{label} deve ser texto não vazio, sem espaços externos.")
    return value


def _keys(value: dict, allowed: set[str], label: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ConfigError(f"Campos não suportados em {label}: {', '.join(sorted(unknown))}.")


def parse_config(data: bytes) -> dict[str, Any]:
    """Validate one exact TOML snapshot; returned values are not approval."""
    try:
        config = tomllib.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"Configuração TOML inválida: {exc}") from exc
    schema = config.get("schema")
    if type(schema) is not int or schema not in {1, 2}:
        raise ConfigError("schema deve ser o inteiro 1 ou 2.")
    if schema == 1:
        if set(config) != {"schema"}:
            raise ConfigError("A configuração schema 1 aceita somente schema = 1, sem outras opções.")
        return config

    _keys(config, {"schema", "project_id", "repository_id", "runners", "traceability", "evidence"}, "schema 2")
    _text(config.get("project_id"), "project_id")
    if "repository_id" in config:
        _text(config["repository_id"], "repository_id")
    runners = config.get("runners", [])
    if not isinstance(runners, list):
        raise ConfigError("runners deve ser uma lista de tabelas.")
    identifiers: set[str] = set()
    for index, runner in enumerate(runners, start=1):
        label = f"runners[{index}]"
        if not isinstance(runner, dict):
            raise ConfigError(f"{label} deve ser uma tabela.")
        _keys(runner, {"id", "language", "command", "steps", "timeout", "paths"}, label)
        identifier = _text(runner.get("id"), f"{label}.id")
        _text(runner.get("language"), f"{label}.language")
        if identifier in identifiers:
            raise ConfigError(f"ID de runner duplicado: {identifier}.")
        identifiers.add(identifier)
        for key in ("command", "paths"):
            if key not in runner:
                continue
            sequence = runner[key]
            if not isinstance(sequence, list) or (key == "command" and not sequence):
                raise ConfigError(f"{label}.{key} deve ser uma lista de textos" + (" não vazia." if key == "command" else "."))
            if key == "command":
                if not all(isinstance(item, str) for item in sequence) or not sequence[0].strip():
                    raise ConfigError(f"{label}.command exige um executável não vazio e argumentos textuais.")
            else:
                for item in sequence:
                    _text(item, f"{label}.{key}")
        if "steps" in runner:
            _text(runner["steps"], f"{label}.steps")
        if "timeout" in runner and (type(runner["timeout"]) is not int or runner["timeout"] <= 0):
            raise ConfigError(f"{label}.timeout deve ser um inteiro positivo.")

    traceability = config.get("traceability", {})
    if not isinstance(traceability, dict):
        raise ConfigError("traceability deve ser uma tabela.")
    _keys(traceability, {"map", "policy"}, "traceability")
    if "map" in traceability:
        _text(traceability["map"], "traceability.map")
    policy = traceability.get("policy", "strict")
    if not isinstance(policy, str) or policy not in {"strict", "off"}:
        raise ConfigError("traceability.policy deve ser strict ou off.")

    evidence = config.get("evidence", {})
    if not isinstance(evidence, dict):
        raise ConfigError("evidence deve ser uma tabela.")
    _keys(evidence, {"allow_mock", "max_age_seconds"}, "evidence")
    if "allow_mock" in evidence and type(evidence["allow_mock"]) is not bool:
        raise ConfigError("evidence.allow_mock deve ser booleano.")
    if "max_age_seconds" in evidence and (
        type(evidence["max_age_seconds"]) is not int or evidence["max_age_seconds"] <= 0
    ):
        raise ConfigError("evidence.max_age_seconds deve ser um inteiro positivo.")
    return config


def load_config(root: Path) -> dict[str, Any]:
    """Load schema 1 or 2 from root/specmd.toml, raising ConfigError on failure."""
    try:
        return parse_config(read_regular_file(Path(root) / "specmd.toml"))
    except OSError as exc:
        raise ConfigError(f"Não foi possível ler specmd.toml: {exc}") from exc
