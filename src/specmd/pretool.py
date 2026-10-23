"""Cooperative local preimplementation gate, not a malicious-process sandbox.

While a contract awaits review, known reads and document-only edits remain
available. Shell recognition is intentionally conservative. Verified workflow
approval restores the host's normal tool policy; this module grants no trust.
"""

from __future__ import annotations

from pathlib import Path
import shlex


_DOC_SUFFIXES = {".md", ".markdown"}
_RESERVED = {".git", ".hg", ".svn", ".specmd"}


def _deny(detail: str) -> dict:
    reason = ("SpecMD: aguardando revisão. Alterações de documentação são permitidas; "
              "a implementação depende do aceite do contrato. " + detail
              + " Abra a revisão em um terminal humano com specmd review --root PROJETO --authority AUTORIDADE --trust TRUST; o agente pode continuar ajustando os documentos enquanto aguarda."
              + " Este bloqueio é uma heurística local cooperativa, não uma sandbox contra processos maliciosos.")
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": "deny", "permissionDecisionReason": reason}}


def _inside(root: Path, raw: str, base: Path) -> Path:
    if not isinstance(raw, str) or not raw or raw != raw.strip() or "\x00" in raw or "\\" in raw:
        raise ValueError("Caminho ausente ou ambíguo.")
    value = Path(raw)
    if ".." in value.parts:
        raise ValueError("Travessia de diretórios não é permitida.")
    candidate = value if value.is_absolute() else base / value
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("Caminhos externos, incluindo autoridade e confiança, não são permitidos nesta etapa.") from error
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Caminhos simbólicos não são permitidos nesta etapa.")
    return candidate


def _base(root: Path, payload: dict, tool_input: object) -> Path:
    raw = payload.get("cwd", str(root))
    if not isinstance(raw, str) or not Path(raw).is_absolute():
        raise ValueError("O diretório da ferramenta precisa ser absoluto.")
    base = _inside(root, raw, root)
    if isinstance(tool_input, dict) and "workdir" in tool_input:
        base = _inside(root, tool_input["workdir"], base)
    return base


def _document_path(root: Path, raw: str, base: Path) -> None:
    candidate = _inside(root, raw, base)
    relative = candidate.relative_to(root)
    if relative.as_posix() in {"specmd.toml", ".specmd/traceability.json"}:
        return
    if any(part in _RESERVED for part in relative.parts) or candidate.suffix.casefold() not in _DOC_SUFFIXES:
        raise ValueError(f"A alteração em {relative.as_posix()} não é exclusivamente documental.")


def _paths(values: dict) -> list[str]:
    paths = [values[key] for key in ("file_path", "path") if key in values]
    if any(not isinstance(path, str) or not path for path in paths):
        raise ValueError("A ferramenta informou um caminho inválido.")
    return paths


def _edit_paths(name: str, values: dict) -> list[str]:
    paths = _paths(values)
    has_global_path = bool(paths)
    if name == "MultiEdit":
        edits = values.get("edits")
        if not isinstance(edits, list) or not edits or any(not isinstance(edit, dict) for edit in edits):
            raise ValueError("MultiEdit exige uma lista não vazia de alterações conhecidas.")
        for edit in edits:
            local = _paths(edit)
            if not local and not has_global_path:
                raise ValueError("MultiEdit contém uma alteração sem caminho conhecido.")
            paths.extend(local)
    if not paths:
        raise ValueError("Não foi possível identificar todos os arquivos da alteração.")
    return paths


def _patch_paths(tool_input: object) -> list[str]:
    patch = tool_input
    if isinstance(tool_input, dict):
        candidates = [tool_input[key] for key in ("input", "patch") if key in tool_input]
        if not candidates or any(not isinstance(value, str) for value in candidates) or len(set(candidates)) != 1:
            raise ValueError("Patch ausente ou ambíguo.")
        patch = candidates[0]
    if not isinstance(patch, str):
        raise ValueError("A ferramenta precisa informar o texto do patch.")
    lines = patch.strip().splitlines()
    if len(lines) < 3 or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise ValueError("Formato de patch não reconhecido.")
    paths = []
    operation = None
    moved = False
    hunk = False
    content = 0
    ended = False
    def finish():
        if operation == "Update" and not moved and not hunk:
            raise ValueError("Atualização sem hunk ou movimento reconhecido.")
        if operation == "Update" and hunk and not content:
            raise ValueError("Hunk vazio não reconhecido.")
    for line in lines[1:-1]:
        header = next((kind for kind in ("Add", "Update", "Delete")
                       if line.startswith(f"*** {kind} File: ")), None)
        if header:
            finish()
            paths.append(line[len(f"*** {header} File: "):])
            operation, moved, hunk, content, ended = header, False, False, 0, False
        elif line.startswith("*** Move to: "):
            if operation != "Update" or moved or hunk:
                raise ValueError("Movimento de arquivo fora de uma atualização reconhecida.")
            paths.append(line[len("*** Move to: "):])
            moved = True
        elif line == "*** End of File":
            if operation != "Update" or not hunk or ended:
                raise ValueError("Marcador de fim inesperado.")
            ended = True
        elif operation == "Add" and line.startswith("+"):
            content += 1
        elif operation == "Update" and not ended and (line == "@@" or line.startswith("@@ ")):
            hunk = True
        elif operation == "Update" and hunk and not ended and (line == "" or line.startswith((" ", "+", "-"))):
            content += 1
        else:
            raise ValueError("O patch contém conteúdo ou ação não reconhecida.")
    finish()
    if not paths:
        raise ValueError("Patch sem arquivos identificáveis.")
    return paths


def _shell_tokens(command: str) -> list[str]:
    if not isinstance(command, str) or not command.strip() or any(value in command for value in ("\n", "\r", "\x00")):
        raise ValueError("Comando de shell ausente ou complexo.")
    quote = None
    for character in command:
        if quote == "'":
            if character == "'":
                quote = None
        elif quote == '"':
            if character == '"':
                quote = None
            elif character in "$`\\":
                raise ValueError("Expansões de shell não são permitidas.")
        elif character in "'\"":
            quote = character
        elif character in ";&|><()$`\\*?[]{}~!#":
            raise ValueError("Operadores, expansões e comandos combinados não são permitidos.")
    if quote is not None:
        raise ValueError("Aspas não fechadas no comando.")
    return shlex.split(command, posix=True)


def _read_arguments(root: Path, base: Path, arguments: list[str], command: str) -> None:
    options_done = False
    files = 0
    for argument in arguments:
        if argument == "--" and not options_done:
            options_done = True
            continue
        if argument.startswith("-") and not options_done:
            if command == "cat":
                safe = argument in {"--number", "--number-nonblank", "--squeeze-blank", "--show-all", "--show-ends", "--show-tabs", "--show-nonprinting", "--help", "--version"} or (
                    argument.startswith("-") and not argument.startswith("--") and len(argument) > 1 and set(argument[1:]) <= set("nbsvETA")
                )
            else:
                safe = argument in {"--all", "--almost-all", "--directory", "--human-readable", "--help", "--version", "--color=never", "--color=auto", "--color=always"} or (
                    argument.startswith("-") and not argument.startswith("--") and len(argument) > 1 and set(argument[1:]) <= set("aAlhdtrS1nFpsi")
                )
            if not safe:
                raise ValueError("Opção de leitura não reconhecida.")
        else:
            _inside(root, argument, base)
            files += 1
    if command == "cat" and not files and not any(arg in {"--help", "--version"} for arg in arguments):
        raise ValueError("cat exige caminhos explícitos do projeto.")


def _rg(root: Path, base: Path, arguments: list[str]) -> None:
    if arguments in (["--help"], ["--version"]):
        return
    flags = {"--files", "--hidden", "--no-ignore", "--no-ignore-vcs", "--no-ignore-parent", "--no-ignore-dot", "--line-number", "-n", "--ignore-case", "-i", "--smart-case", "-S", "--fixed-strings", "-F", "--word-regexp", "-w", "--line-regexp", "-x", "--count", "-c", "--files-with-matches", "-l", "--files-without-match", "--json", "--only-matching", "-o", "--multiline", "-U", "--no-heading", "--heading", "--stats", "--no-messages", "--no-config"}
    valued = {"-g", "--glob", "-e", "--regexp", "-t", "--type", "--type-not", "-A", "--after-context", "-B", "--before-context", "-C", "--context", "-m", "--max-count", "--max-depth"}
    pattern = False
    files_mode = "--files" in arguments
    options_done = False
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--" and not options_done:
            options_done = True
        elif not options_done and argument.startswith("-"):
            if argument in valued:
                index += 1
                if index >= len(arguments):
                    raise ValueError("Opção rg sem valor.")
                if argument in {"-e", "--regexp"}:
                    pattern = True
            elif argument not in flags:
                raise ValueError("Opção rg não reconhecida; preprocessadores e follow não são permitidos.")
        elif not files_mode and not pattern:
            pattern = True
        else:
            _inside(root, argument, base)
        index += 1
    if not files_mode and not pattern:
        raise ValueError("rg exige padrão ou --files.")


def _git(root: Path, base: Path, arguments: list[str]) -> None:
    index = 0
    while index < len(arguments) and arguments[index].startswith("-"):
        flag = arguments[index]
        if flag == "-C":
            index += 1
            if index >= len(arguments):
                raise ValueError("git -C exige caminho do projeto.")
            base = _inside(root, arguments[index], base)
        elif flag not in {"--no-pager", "--no-optional-locks"}:
            raise ValueError("Configuração ou opção global de Git não permitida.")
        index += 1
    if index >= len(arguments) or arguments[index] not in {"diff", "status", "log", "show"}:
        raise ValueError("Somente git diff/status/log/show são reconhecidos como leitura.")
    subcommand = arguments[index]
    booleans = {"--stat", "--numstat", "--shortstat", "--name-only", "--name-status", "--summary", "--compact-summary", "--check", "--cached", "--staged", "--raw", "--patch", "-p", "--no-patch", "-s", "--no-color", "--color=never", "--no-ext-diff", "--no-textconv", "--ignore-space-change", "-b", "--ignore-all-space", "-w", "--ignore-blank-lines", "--oneline", "--decorate", "--no-decorate", "--no-merges", "--first-parent", "--all", "--reverse", "--date-order", "--topo-order", "--short", "--branch", "--porcelain", "--porcelain=v1", "--porcelain=v2", "--untracked-files=all", "--untracked-files=normal", "--untracked-files=no"}
    values = {"-n", "--max-count", "--format", "--pretty", "--date", "--since", "--until", "--author", "--grep"}
    prefixes = ("--format=", "--pretty=", "--date=", "--max-count=", "--since=", "--until=", "--author=", "--grep=")
    index += 1
    paths_only = False
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--" and not paths_only:
            paths_only = True
        elif not paths_only and argument.startswith("-"):
            if argument in values:
                index += 1
                if index >= len(arguments):
                    raise ValueError("Opção Git sem valor.")
            elif not (argument in booleans or argument.startswith(prefixes)
                      or (subcommand in {"log", "show"} and argument[1:].isdigit())):
                raise ValueError("Opção Git não reconhecida; execução externa e arquivos de saída são proibidos.")
        else:
            _inside(root, argument, base)
        index += 1


def _shell(root: Path, base: Path, values: object) -> None:
    if not isinstance(values, dict):
        raise ValueError("Entrada de shell não reconhecida.")
    commands = [values[key] for key in ("cmd", "command") if key in values]
    if not commands or any(not isinstance(command, str) for command in commands) or len(set(commands)) != 1:
        raise ValueError("Comando de shell ausente ou ambíguo.")
    if "shell" in values and values["shell"] not in {"/bin/sh", "/bin/bash", "/usr/bin/sh", "/usr/bin/bash", "sh", "bash"}:
        raise ValueError("Shell customizado não reconhecido.")
    tokens = _shell_tokens(commands[0])
    if not tokens:
        raise ValueError("Comando vazio.")
    command, arguments = tokens[0], tokens[1:]
    if command in {"cat", "ls"}:
        _read_arguments(root, base, arguments, command)
    elif command == "rg":
        _rg(root, base, arguments)
    elif command == "git":
        _git(root, base, arguments)
    else:
        raise ValueError("Comando não reconhecido como leitura; execute a revisão antes da implementação.")


def pretool_decision(root: Path, payload: dict, result: dict) -> dict:
    """Return deny JSON or leave the host's own permission policy unchanged."""
    approval = result.get("approval") if isinstance(result, dict) else None
    if isinstance(result, dict) and (result.get("may_complete") is True or isinstance(approval, dict) and approval.get("valid") is True):
        return {}
    try:
        root = Path(root).resolve(strict=True)
        if not isinstance(payload, dict):
            raise ValueError("Payload da ferramenta inválido.")
        name = payload.get("tool_name")
        if isinstance(name, str) and name.startswith("functions."):
            name = name[len("functions."):]
        values = payload.get("tool_input")
        base = _base(root, payload, values)
        if name in {"Read", "Grep", "Glob"}:
            if not isinstance(values, dict):
                raise ValueError("Entrada de leitura não reconhecida.")
            paths = _paths(values)
            if name == "Read" and not paths:
                raise ValueError("Read exige um arquivo identificado.")
            for path in paths:
                _inside(root, path, base)
            if name == "Glob":
                pattern = values.get("pattern")
                if not isinstance(pattern, str) or not pattern or ".." in pattern or "\\" in pattern or pattern.startswith("~"):
                    raise ValueError("Padrão Glob ausente ou fora do escopo conhecido.")
                if Path(pattern).is_absolute():
                    _inside(root, pattern, base)
            return {}
        if name in {"Edit", "Write", "MultiEdit"}:
            if not isinstance(values, dict):
                raise ValueError("Entrada de alteração não reconhecida.")
            for path in _edit_paths(name, values):
                _document_path(root, path, base)
            return {}
        if name == "apply_patch":
            for path in _patch_paths(values):
                _document_path(root, path, base)
            return {}
        if name in {"exec_command", "Bash"}:
            _shell(root, base, values)
            return {}
        raise ValueError("Ação desconhecida enquanto o contrato aguarda revisão.")
    except (ValueError, OSError, TypeError) as error:
        return _deny(str(error))
