"""Small CLI shared by developers and the Codex adapter."""

import argparse
import json
from pathlib import Path
import sys

from . import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(prog="specmd", description="Preflight local experimental; não emite aceite humano.")
    parser.add_argument("--version", action="version", version=f"specmd {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "inventory", "check"):
        command = commands.add_parser(name)
        command.add_argument("--root", type=Path, default=Path.cwd())
        if name != "init":
            command.add_argument("--format", choices=("json",), default="json")
        if name == "check":
            command.add_argument("--stage", choices=("completion",), default="completion")
    commands.add_parser("codex-hook", help="Lê o payload de hook do Codex pelo stdin")
    args = parser.parse_args(argv)
    if args.command == "codex-hook":
        from .codex import run_hook
        return run_hook()
    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("A raiz precisa ser um diretório existente.")
        if args.command == "init":
            with (root / "specmd.toml").open("x", encoding="utf-8") as stream:
                stream.write("# Preflight experimental: não concede aceite nem verifica implementação.\nschema = 1\n")
            result = {"status": "initialized", "root": str(root), "may_complete": False,
                      "message": "Projeto ativado. Execute specmd check; nenhum documento foi aprovado."}
        else:
            from .core import inspect_project
            result = inspect_project(root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command in ("init", "inventory"):
            return 2 if result["status"] == "error" else 0
        return 2 if result["status"] in ("error", "inactive") else 1
    except Exception as error:
        print(json.dumps({"protocol_version": 1, "stage": "completion", "status": "error",
                          "may_complete": False, "findings": [{"kind": "preflight_error", "message": str(error)}]},
                         ensure_ascii=False, indent=2))
        return 2
