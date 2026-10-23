"""Translate the workflow result into the synchronous Codex hook protocol.

Hook approval does not grant contract approval. The persisted status is only an
observation; check_project is responsible for verifying authority and evidence.
"""

import json
import os
from pathlib import Path
import sys
import tempfile


SUPPORTED_EVENTS = {"SessionStart", "PreToolUse", "PostToolUse", "Stop"}


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
    state = {**result, "state_kind": "observed_workflow_check",
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
    complete = str(result["may_complete"]).lower()
    lines = [f"SpecMD: {result['status']}; may_complete={complete}."]
    if result["status"] == "demo_passed":
        lines.append("Modo DEMONSTRAÇÃO LOCAL: garantia SIMULADA, sem autoridade isolada. Não constitui garantia protegida.")
        if result.get("test_mode"):
            lines.append(f"Modo de execução dos testes: {result['test_mode']}.")
    elif result["status"] == "passed":
        lines.append("Modo real: a conclusão foi autorizada pela verificação atual do workflow.")
    for finding in result.get("findings", [])[:8]:
        location = finding.get("path", "")
        if finding.get("line"):
            location += f":{finding['line']}"
        lines.append(f"- {location + ': ' if location else ''}{finding['message']}")
    lines.append("O estado em .specmd/local/status.json é uma observação, não um aceite humano.")
    return "\n".join(lines)


def validate_result(result):
    """Reject contradictory results instead of treating truthy values as proof."""
    if not isinstance(result, dict) or type(result.get("may_complete")) is not bool:
        raise ValueError("O workflow precisa informar may_complete como booleano.")
    findings = result.get("findings")
    if not isinstance(findings, list) or any(not isinstance(item, dict) or not isinstance(item.get("message"), str) for item in findings):
        raise ValueError("Os diagnósticos do workflow precisam ser uma lista válida.")
    successful = {"passed": ("real", "protected"), "demo_passed": ("demo", "local_demo")}
    status = result.get("status")
    if result["may_complete"]:
        if status not in successful or findings:
            raise ValueError("O workflow não pode autorizar conclusão com estado ou pendências inconsistentes.")
        mode, assurance = successful[status]
        if result.get("verification_mode") != mode or result.get("assurance") != assurance:
            raise ValueError("A autorização de conclusão precisa identificar o modo e o nível de garantia corretos.")
    elif status not in {"waiting_human_review", "awaiting_evidence", "blocked", "error"}:
        raise ValueError("Estado incompatível com a conclusão pendente.")


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
        from .workflow import check_project
        inspect = check_project
    result = inspect(root)
    if result["status"] == "inactive":
        result = {"protocol_version": 1, "stage": "completion", "status": "error", "may_complete": False,
                  "findings": [{"kind": "configuration_removed", "message": "A configuração do projeto anteriormente ativado foi removida."}]}
    validate_result(result)
    save_status(root, result, payload)
    message = describe(result)
    if event == "PreToolUse":
        from .pretool import pretool_decision
        return pretool_decision(root, payload, result)
    if event != "Stop":
        if result["may_complete"]:
            context = message
        else:
            context = (message + "\nNão declare a tarefa concluída. Corrija as pendências; quando aguardar revisão humana, "
                       "explique a pendência e devolva o controle.")
        return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}
    if result["may_complete"]:
        return {}
    if result["status"] == "waiting_human_review":
        return {"continue": False, "stopReason": message + "\nAguardando revisão humana; devolvendo o controle sem liberar a tarefa.",
                "systemMessage": message}
    if result["status"] not in {"awaiting_evidence", "blocked", "error"}:
        raise ValueError("Estado inesperado do workflow.")
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
