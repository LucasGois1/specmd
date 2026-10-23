"""Translate local preflight into the synchronous Codex hook protocol."""

import json
import os
from pathlib import Path
import sys
import tempfile


SUPPORTED_EVENTS = {"SessionStart", "PostToolUse", "Stop"}


def find_root(cwd):
    path = Path(cwd)
    if not path.is_absolute():
        raise ValueError("O cwd do hook precisa ser absoluto.")
    path = path.resolve(strict=True)
    if not path.is_dir():
        raise ValueError("O cwd do hook precisa ser um diretório.")
    for candidate in (path, *path.parents):
        if (candidate / "specmd.toml").exists() or (candidate / ".specmd/local/status.json").exists():
            return candidate
        if (candidate / ".git").exists():
            break
    return None


def observed_changes(previous, current):
    def entries(manifest):
        if not isinstance(manifest, dict) or not isinstance(manifest.get("documents", []), list):
            return {}
        return {item["path"]: item["sha256"] for item in manifest.get("documents", [])
                if isinstance(item, dict) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str)}
    before = entries(previous)
    after = entries(current)
    return ([{"kind": "added", "path": path} for path in sorted(after.keys() - before.keys())]
            + [{"kind": "modified", "path": path} for path in sorted(after.keys() & before.keys()) if after[path] != before[path]]
            + [{"kind": "removed", "path": path} for path in sorted(before.keys() - after.keys())])


def save_status(root, result, payload):
    # This is an observed snapshot, never an approval source.
    directory = root
    for part in (".specmd", "local"):
        directory = directory / part
        if directory.is_symlink():
            raise ValueError("O estado local não pode ser gravado por um link simbólico.")
        directory.mkdir(exist_ok=True)
    destination = directory / "status.json"
    if destination.is_symlink():
        raise ValueError("O estado local não pode ser um link simbólico.")
    previous = {}
    if destination.exists():
        try:
            previous = json.loads(destination.read_text(encoding="utf-8"))
            if not isinstance(previous, dict):
                previous = {}
        except (ValueError, OSError):
            previous = {}  # Reconstructible cache, not approval authority.
    state = {**result, "state_kind": "observed_local_preflight",
             "hook_event": payload["hook_event_name"],
             "observed_changes": observed_changes(previous.get("manifest", {}), result.get("manifest", {}))}
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def describe(result):
    lines = [f"SpecMD: {result['status']}; may_complete=false."]
    for finding in result.get("findings", [])[:8]:
        location = finding.get("path", "")
        if finding.get("line"):
            location += f":{finding['line']}"
        lines.append(f"- {location + ': ' if location else ''}{finding['message']}")
    lines.append("O estado em .specmd/local/status.json é uma observação, não um aceite humano.")
    return "\n".join(lines)


def error_response(message):
    reason = f"SpecMD: erro de verificação; may_complete=false. {message} A tarefa permanece pendente."
    return {"continue": False, "stopReason": reason, "systemMessage": reason}


def handle_hook(payload, inspect=None):
    if not isinstance(payload, dict):
        raise ValueError("O payload do hook precisa ser um objeto JSON.")
    event = payload.get("hook_event_name")
    if event not in SUPPORTED_EVENTS:
        raise ValueError("Evento de hook não suportado.")
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        raise ValueError("O payload do hook precisa informar cwd.")
    if event == "Stop" and not isinstance(payload.get("stop_hook_active"), bool):
        raise ValueError("Stop precisa informar stop_hook_active como booleano.")
    root = find_root(cwd)
    if root is None:
        return {}
    if inspect is None:
        from .core import inspect_project
        inspect = inspect_project
    result = inspect(root)
    if result["status"] == "inactive":
        result = {"protocol_version": 1, "stage": "completion", "status": "error", "may_complete": False,
                  "findings": [{"kind": "configuration_removed", "message": "A configuração do projeto anteriormente ativado foi removida."}]}
    if result.get("may_complete") is not False:
        raise ValueError("Este protótipo não pode conceder conclusão ou aceite.")
    save_status(root, result, payload)
    message = describe(result)
    if event != "Stop":
        context = (message + "\nNão declare a tarefa concluída. Corrija as pendências locais; quando aguardar revisão humana, "
                   "explique a pendência e devolva o controle. Este protótipo não oferece emissão de aceite ou gate protegido.")
        return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}
    if result["status"] == "waiting_human_review":
        return {"continue": False, "stopReason": message + "\nAguardando revisão humana; devolvendo o controle sem liberar a tarefa.",
                "systemMessage": message}
    if result["status"] not in {"blocked", "error"}:
        raise ValueError("Estado inesperado do preflight.")
    if payload["stop_hook_active"]:
        return {"continue": False, "stopReason": message + "\nPendências persistem após o feedback; devolvendo o controle para evitar um ciclo.",
                "systemMessage": message}
    return {"decision": "block", "reason": message + "\nCorrija as pendências. Se depender do humano, explique o bloqueio e devolva o controle.",
            "systemMessage": message}


def run_hook():
    try:
        reply = handle_hook(json.load(sys.stdin))
    except Exception as error:
        # Hook exit errors alone do not reliably block Codex. Emit valid control JSON.
        reply = error_response(str(error))
    print(json.dumps(reply, ensure_ascii=False))
    return 0
