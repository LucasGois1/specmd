"""CLI for inventory, human review, execution and agent adapters."""

import argparse
import json
import os
from pathlib import Path

from . import __version__


def _port(value):
    number = int(value)
    if not 0 <= number <= 65535:
        raise argparse.ArgumentTypeError("A porta deve estar entre 0 e 65535.")
    return number


def _print(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _gate_exit(result):
    if result.get("status") in {"error", "inactive"}:
        return 2
    if result.get("may_complete") is True:
        from .codex import validate_result
        validate_result(result)
        return 0
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="specmd", description="Contratos Markdown, revisão humana e evidências verificáveis.")
    parser.add_argument("--version", action="version", version=f"specmd {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "inventory", "check", "status", "run", "verify", "audit", "review"):
        command = commands.add_parser(name)
        command.add_argument("--root", type=Path, default=Path.cwd())
        command.add_argument("--format", choices=("json",), default="json")
        if name == "init":
            command.add_argument("--legacy", action="store_true", help="Criar apenas o preflight schema 1")
        if name in {"check", "status", "run", "verify", "audit", "review"}:
            command.add_argument("--trust", type=Path)
        if name in {"check", "status", "run", "verify"}:
            command.add_argument("--stage", choices=("completion",), default="completion")
            command.add_argument("--require-real", action="store_true", default=name == "verify")
        if name == "review":
            command.add_argument("--prepare", action="store_true", help="Gerar proposta JSON sem iniciar a interface")
            command.add_argument("--authority", type=Path)
            command.add_argument("--port", type=_port, default=0)
            command.add_argument("--no-open", action="store_true")
    demo = commands.add_parser("demo", help="Criar uma aplicação e autoridade local de demonstração, sem aceite automático")
    demo.add_argument("--dest", type=Path, required=True)
    demo.add_argument("--authority", type=Path)
    demo.add_argument("--format", choices=("json",), default="json")
    commands.add_parser("codex-hook", help="Lê o payload de hook do Codex pelo stdin")
    commands.add_parser("claude-hook", help="Lê o payload de hook do Claude Code pelo stdin")
    args = parser.parse_args(argv)
    if hasattr(args, "trust") and args.trust is None and os.environ.get("SPECMD_TRUST_STORE"):
        args.trust = Path(os.environ["SPECMD_TRUST_STORE"])
    if args.command in {"codex-hook", "claude-hook"}:
        if args.command == "codex-hook":
            from .codex import run_hook
        else:
            from .claude import run_hook
        return run_hook()
    try:
        if args.command == "demo":
            from .demo import create_demo
            result = create_demo(args.dest, args.authority)
        else:
            root = args.root.resolve(strict=True)
            if not root.is_dir():
                raise ValueError("A raiz precisa ser um diretório existente.")
            if args.command == "init":
                from .demo import initial_config
                content = "schema = 1\n" if args.legacy else initial_config(root.name or "specmd-project")
                with (root / "specmd.toml").open("x", encoding="utf-8") as stream:
                    stream.write(content)
                result = {"status": "initialized", "root": str(root), "may_complete": False,
                          "schema": 1 if args.legacy else 2,
                          "message": "Projeto ativado; nenhum documento foi aprovado. Configure os vínculos e revise os contratos."}
            elif args.command == "inventory":
                from .core import inspect_project
                result = inspect_project(root)
            elif args.command == "review":
                if args.prepare:
                    from .workflow import prepare_review
                    result = {"status": "review_prepared", "may_complete": False, **prepare_review(root, trust_path=args.trust)}
                else:
                    if args.authority is None:
                        raise ValueError("Informe --authority para a interface local, ou use --prepare para apenas gerar a proposta.")
                    from .review_server import serve_review
                    serve_review(root, args.authority, trust_path=args.trust,
                                 port=args.port, open_browser=not args.no_open)
                    return 0
            elif args.command == "audit":
                from .workflow import audit_project
                result = audit_project(root, args.trust)
            else:
                from .workflow import check_project, run_project
                if args.command in {"run", "verify"}:
                    result = run_project(root, args.trust, require_real=args.require_real)
                else:
                    result = check_project(root, args.trust, require_real=args.require_real)
        if args.command in {"check", "status", "run", "verify"}:
            exit_code = _gate_exit(result)
        else:
            exit_code = 2 if result.get("status") == "error" else 0
        _print(result)
        return exit_code
    except Exception as error:
        _print({"protocol_version": 1, "stage": "completion", "status": "error", "may_complete": False,
                "findings": [{"kind": "command_error", "message": str(error)}]})
        return 2
