"""Claude Code / Codex hook lifecycle: deterministic feedback for the agent.

- SessionStart: summary of the canonical documentation and how to work with it.
- UserPromptSubmit: remembers which scenarios the developer has seen.
- PostToolUse: after documentation changes, reports gaps right away.
- Stop: documentation gaps first; then, when code changed and the developer
  already saw the scenarios, runs them and returns what is missing or failing.

The hooks never stop the session: Stop returns feedback while it is making a
difference (same feedback twice, or MAX_BLOCKS, lets the agent stop) and any
internal error becomes a warning.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from . import state as hook_state

MAX_BLOCKS = 4
MAX_FINDINGS = 8
MAX_REASON = 6000
READ_ONLY_TOOLS = frozenset({
    "Read", "Grep", "Glob", "LS", "WebFetch", "WebSearch", "TodoWrite", "NotebookRead",
    "TaskOutput", "ListMcpResourcesTool", "ReadMcpResourceTool", "view_image",
})
CONVENTIONS = (
    "Como trabalhar com o SpecMD:\n"
    "1. A documentação Markdown é a fonte canônica das regras de negócio. Todo comportamento do sistema "
    "fica num documento, com cenários Gherkin em blocos ```gherkin no próprio documento. Um requisito pode "
    "ter ID no título (ex.: `## PAG-REQ-001 — Estorno`); os cenários logo abaixo dele ficam ligados a ele.\n"
    "2. Ao escrever ou mudar cenários, mostre-os ao dev e peça confirmação antes de implementar. "
    "Em dúvida sobre um requisito, pergunte.\n"
    "3. Um Markdown que não descreve comportamento do sistema (README, guia de setup, notas) vai para o "
    "`.specmdignore` na raiz, com padrões no estilo .gitignore. Se for claramente o caso, adicione você mesmo; "
    "em dúvida, pergunte ao dev se ele precisa de cenários.\n"
    "4. Ao concluir uma implementação, o SpecMD executa os cenários e devolve o que falta ou falha. "
    "Cenários marcados com @wip não são cobrados."
)
GAP_GUIDANCE = (
    "Para cada documento: se ele descreve comportamento do sistema, confirme os requisitos com o dev e "
    "escreva os cenários Gherkin no próprio Markdown; se não descreve, adicione-o ao .specmdignore; "
    "em dúvida, pergunte ao dev."
)


def find_root() -> Path | None:
    """Project root from the host environment, never from paths in the payload.

    Claude Code exports CLAUDE_PROJECT_DIR; otherwise the hook process runs in
    the session's working directory.
    """
    for raw in (os.environ.get("CLAUDE_PROJECT_DIR"), os.getcwd()):
        if not isinstance(raw, str) or not raw or not Path(raw).is_absolute():
            continue
        start = Path(raw).resolve()
        if not start.is_dir():
            continue
        for candidate in (start, *start.parents):
            if (candidate / "specmd.toml").is_file():
                return candidate
            if (candidate / ".git").exists():
                break
    return None


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def _spec_map(inspection: dict[str, Any]) -> dict[str, str | None]:
    return {document["path"]: document.get("spec_sha256") for document in inspection.get("documents", [])}


def _doc_map(inspection: dict[str, Any]) -> dict[str, str]:
    return {document["path"]: document["sha256"] for document in inspection.get("documents", [])}


def _location(finding: dict[str, Any]) -> str:
    location = finding.get("path", "")
    if finding.get("line"):
        location += f":{finding['line']}"
    return location + ": " if location else ""


def _format_findings(findings: list[dict[str, Any]]) -> list[str]:
    lines = [f"- {_location(item)}{item.get('message', '')}" for item in findings[:MAX_FINDINGS]]
    if len(findings) > MAX_FINDINGS:
        lines.append(f"- … e mais {len(findings) - MAX_FINDINGS} pendências.")
    return lines


def _format_failures(run: dict[str, Any]) -> str:
    failures = run.get("failures", [])
    lines = [f"SpecMD: {len(failures)} de {run.get('expected', '?')} cenários da documentação não passaram."]
    for failure in failures[:MAX_FINDINGS]:
        name = f' "{failure["name"]}"' if failure.get("name") else ""
        lines.append(f"- {failure.get('path')}:{failure.get('line')} {failure.get('id')}{name} ({failure.get('status')})")
        for step in failure.get("steps", [])[:3]:
            lines.append(f"    {step.get('text', 'passo')} (linha {step.get('line')}): {step.get('status')}")
            if step.get("error"):
                lines.extend("      " + line for line in step["error"].splitlines()[-6:])
            if step.get("snippet"):
                lines.append("      Passo sem implementação. Ponto de partida:")
                lines.extend("      " + line for line in step["snippet"].strip().splitlines())
    if len(failures) > MAX_FINDINGS:
        lines.append(f"- … e mais {len(failures) - MAX_FINDINGS} cenários.")
    for finding in run.get("findings", []):
        lines.append(f"- Execução: {finding.get('message')}")
    lines.append("Implemente o comportamento documentado até os cenários passarem. Se um cenário parecer "
                 "errado, confirme com o dev antes de mudá-lo.")
    return "\n".join(lines)[:MAX_REASON]


def _block_once(root: Path, signature: str, reason: str, summary: str) -> dict[str, Any]:
    """Block with feedback while it is new; repeated feedback or the cap lets the agent stop."""
    decision: dict[str, Any] = {}

    def change(state: dict[str, Any]) -> None:
        stop = state.get("stop") if isinstance(state.get("stop"), dict) else {}
        if stop.get("signature") == signature or stop.get("count", 0) >= MAX_BLOCKS:
            decision["allow"] = True
            return
        state["stop"] = {"signature": signature, "count": stop.get("count", 0) + 1}

    hook_state.update(root, change)
    if decision.get("allow"):
        return {"systemMessage": summary}
    return {"decision": "block", "reason": reason}


def _session_start(root: Path) -> dict[str, Any]:
    from .workflow import check_project, fingerprint_code, scenario_count

    result = check_project(root)
    code_fp = fingerprint_code(root)

    def change(state: dict[str, Any]) -> None:
        state.setdefault("spec_at_prompt", _spec_map(result))
        state["docs_seen"] = _doc_map(result)
        state["spec_seen"] = _spec_map(result)
        state["code_fp_baseline"] = code_fp
        state["stop"] = {"signature": None, "count": 0}

    hook_state.update(root, change)
    documents = [document for document in result.get("documents", []) if document.get("scenarios")]
    lines = ["SpecMD ativo neste repositório.",
             f"- Documentos com cenários: {len(documents)} ({scenario_count(result)} cenários)."]
    if result["status"] == "needs_scenarios":
        lines.append(f"- Pendências na documentação: {len(result['findings'])}.")
        lines.extend(_format_findings(result["findings"])[:3])
    run = result.get("run")
    if run:
        state_text = "passando" if run.get("passed") else f"{len(run.get('failures', []))} falhando"
        freshness = "" if run.get("current") else " (o código ou os cenários mudaram depois)"
        lines.append(f"- Última execução: {run.get('scenarios')} cenários, {state_text}{freshness}.")
    lines.append(CONVENTIONS)
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(lines)}}


def _user_prompt(root: Path) -> dict[str, Any]:
    from .core import inspect_project

    result = inspect_project(root)
    if result["status"] in {"inactive", "error"}:
        return {}

    def change(state: dict[str, Any]) -> None:
        state["spec_at_prompt"] = _spec_map(result)
        state["stop"] = {"signature": None, "count": 0}

    hook_state.update(root, change, timeout=2)
    return {}


def _post_tool(root: Path) -> dict[str, Any]:
    from .core import inspect_project

    result = inspect_project(root)
    if result["status"] in {"inactive", "error"}:
        return {}
    current, spec_now = _doc_map(result), _spec_map(result)
    seen: dict[str, Any] = {}

    def change(state: dict[str, Any]) -> None:
        seen["docs"] = state.get("docs_seen")
        seen["spec"] = state.get("spec_seen") or {}
        state["docs_seen"] = current
        state["spec_seen"] = spec_now

    hook_state.update(root, change, timeout=1)
    if not isinstance(seen["docs"], dict):
        return {}  # First observation in this project: nothing to compare yet.
    changed = sorted(path for path, digest in current.items() if seen["docs"].get(path) != digest)
    if not changed:
        return {}
    findings = [item for item in result["findings"] if item.get("path") in changed]
    spec_changed = [path for path in changed if spec_now.get(path) and seen["spec"].get(path) != spec_now.get(path)]
    lines = [f"SpecMD: documentação alterada: {', '.join(changed[:6])}."]
    if findings:
        lines.append("Pendências encontradas:")
        lines.extend(_format_findings(findings))
        lines.append(GAP_GUIDANCE)
    elif spec_changed:
        lines.append("Requisitos ou cenários mudaram. Mostre os cenários novos ou alterados ao dev e peça "
                     "confirmação antes de implementar.")
    else:
        return {}
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "\n".join(lines)}}


def _runs_on_stop(root: Path) -> bool:
    from .config import load_config

    return load_config(root).get("run", {}).get("on_stop", True)


def _current_run(root: Path, result: dict[str, Any], state: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    """Reuse a run that matches the current code and scenarios, or run when code changed."""
    from .workflow import fingerprint_code, run_project

    code_fp = fingerprint_code(root)
    last = state.get("last_run") if isinstance(state.get("last_run"), dict) else None
    if last and last.get("spec_fp") == result["spec_fp"] and code_fp in last.get("code_fps", []):
        return last, True
    if code_fp == state.get("code_fp_baseline"):
        # No code changed in this session: no execution is demanded.
        return None, False
    return run_project(root).get("run"), False


def _stop(root: Path) -> dict[str, Any]:
    from .core import inspect_project
    from .workflow import scenario_count

    result = inspect_project(root)
    if result["status"] == "inactive":
        return {}
    if result["status"] == "error":
        return {"systemMessage": "SpecMD: " + "; ".join(item["message"] for item in result["findings"])}
    if result["status"] == "needs_scenarios":
        findings = result["findings"]
        reason = "\n".join(["SpecMD: a documentação tem pendências antes de concluir:",
                            *_format_findings(findings), GAP_GUIDANCE])
        return _block_once(root, _digest(["docs", findings]), reason,
                           f"SpecMD: {len(findings)} pendências na documentação continuam abertas.")
    state = hook_state.load(root)
    seen = state.get("spec_at_prompt")
    current_spec = _spec_map(result)
    if isinstance(seen, dict) and seen != current_spec:
        pending = sorted(path for path, digest in current_spec.items() if seen.get(path) != digest)
        return {"systemMessage": "SpecMD: cenários novos ou alterados aguardando sua confirmação em "
                                 + ", ".join(pending[:6]) + "."}
    if not scenario_count(result) or not _runs_on_stop(root):
        return {}
    run, fresh = _current_run(root, result, state)
    if run is None:
        return {}
    if run.get("passed"):
        return {} if fresh else {"systemMessage": f"SpecMD: {run.get('scenarios')} cenários passando."}
    signature = _digest(["run", [(item.get("id"), item.get("status"), [step.get("error") for step in item.get("steps", [])])
                                 for item in run.get("failures", [])], run.get("findings")])
    return _block_once(root, signature, _format_failures(run),
                       f"SpecMD: {len(run.get('failures', []))} cenários ainda não passam.")


def handle_hook(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("O payload do hook precisa ser um objeto JSON.")
    event = payload.get("hook_event_name")
    if event == "PostToolUse" and payload.get("tool_name") in READ_ONLY_TOOLS:
        return {}
    handlers = {"SessionStart": _session_start, "UserPromptSubmit": _user_prompt,
                "PostToolUse": _post_tool, "Stop": _stop}
    if event not in handlers:
        return {}
    root = find_root()
    if root is None:
        return {}
    return handlers[event](root)


def soft_error(event: Any, error: Exception) -> dict[str, Any]:
    """Internal failures are reported, never turned into a stopped session."""
    if event in {"SessionStart", "Stop"}:
        return {"systemMessage": f"SpecMD: verificação indisponível ({type(error).__name__}: {error})."}
    return {}


def run_hook() -> int:
    event = None
    try:
        payload = json.load(sys.stdin)
        event = payload.get("hook_event_name") if isinstance(payload, dict) else None
        reply = handle_hook(payload)
    except TimeoutError:
        reply = {}
    except Exception as error:  # noqa: BLE001 - a hook must always answer with valid JSON
        reply = soft_error(event, error)
    print(json.dumps(reply, ensure_ascii=False))
    return 0
