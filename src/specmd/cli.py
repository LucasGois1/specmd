"""CLI for documentation inspection, scenario execution and agent hooks."""

import argparse
import json
from pathlib import Path

from . import __version__

# 0: nothing pending; 1: documentation gaps or failing scenarios; 2: error.
_EXIT_CODES = {"ready": 0, "passing": 0, "adoption": 0, "needs_scenarios": 1, "failing": 1}


def _print(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="specmd", description="Documentação Markdown canônica com cenários verificáveis.")
    parser.add_argument("--version", action="version", version=f"specmd {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (("init", "Habilitar o plugin para o time no .claude/settings.json do projeto"),
                       ("inventory", "Listar documentos, requisitos e cenários"),
                       ("check", "Pendências da documentação e resultado da última execução"),
                       ("status", "Mesmo que check"),
                       ("run", "Executar todos os cenários da documentação"),
                       ("adopt", "Listar os documentos que ainda precisam de cenários, para a adoção em legado")):
        command = commands.add_parser(name, help=text)
        command.add_argument("--root", type=Path, default=Path.cwd())
        if name == "run":
            command.add_argument("--affected", action="store_true",
                                 help="executar só os cenários afetados pela mudança desde a última execução")
    demo = commands.add_parser("demo", help="Criar um projeto de demonstração")
    demo.add_argument("--dest", type=Path, required=True)
    commands.add_parser("codex-hook", help="Lê o payload de hook do Codex pelo stdin")
    commands.add_parser("claude-hook", help="Lê o payload de hook do Claude Code pelo stdin")
    args = parser.parse_args(argv)
    if args.command in {"codex-hook", "claude-hook"}:
        from .hooks import run_hook
        return run_hook()
    try:
        if args.command == "demo":
            from .demo import create_demo
            result = create_demo(args.dest)
            _print(result)
            return 0
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("A raiz precisa ser um diretório existente.")
        if args.command == "init":
            from .project_setup import initialize
            _print(initialize(root))
            return 0
        if args.command == "inventory":
            from .core import inspect_project
            result = inspect_project(root)
        elif args.command == "adopt":
            from .workflow import adoption_list
            result = adoption_list(root)
        elif args.command == "run":
            from .workflow import run_project
            result = run_project(root, affected=args.affected)
        else:
            from .workflow import check_project
            result = check_project(root)
        _print(result)
        return _EXIT_CODES.get(result.get("status"), 2)
    except Exception as error:
        _print({"protocol_version": 2, "status": "error",
                "findings": [{"kind": "command_error", "message": str(error)}]})
        return 2
