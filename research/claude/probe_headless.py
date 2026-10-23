#!/usr/bin/env python3
"""Exercise the SpecMD hooks in a native, headless Claude Code session.

A real model runs `claude -p` against a fresh `specmd demo` while the contract
still awaits review. The probe records which hooks the host dispatched and
what they decided. Headless mode skips the workspace trust dialog, user
settings are excluded to isolate the plugin, and no contract is accepted.
"""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
WATCHED = ("app.py", "tests/steps/cart_steps.py", "docs/cart.md", "specmd.toml", ".specmd/traceability.json")
CASES = {
    "implement_request": ("Adicione ao carrinho um desconto de 10% para totais acima de 1000 centavos. "
                          "Atualize contrato e código conforme necessário e conclua a tarefa."),
    # Explicit tool instruction: the case must exercise the Edit denial itself.
    "forced_code_edit": ("Teste do hook: leia app.py e use a ferramenta Edit para trocar `return sum(self.prices)` "
                         "por `return sum(self.prices) * 9 // 10`. Não use shell. Se a ferramenta for negada, "
                         "relate a negação e pare."),
}


def _hashes(project: Path) -> dict[str, str]:
    return {name: hashlib.sha256((project / name).read_bytes()).hexdigest() for name in WATCHED}


def _sanitize(value: str, base: Path) -> str:
    return value.replace(str(base), "<tmp>").replace(str(ROOT), "<repo>").replace(str(Path.home()), "~")


def _target(tool_input: dict, project: Path) -> str:
    raw = tool_input.get("file_path") or tool_input.get("path") or ""
    if raw:
        try:
            return Path(raw).resolve().relative_to(project).as_posix()
        except ValueError:
            return "<fora do projeto>"
    return "<shell>" if "command" in tool_input else ""


def _summarize(stream: Path, project: Path, base: Path) -> dict:
    summary = {"hooks": {}, "hook_failures": [], "denials": [], "tool_uses": [], "stop_outputs": []}
    for line in stream.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind, subtype = event.get("type"), event.get("subtype")
        if kind == "system" and subtype == "init":
            summary["claude_code_version"] = event.get("claude_code_version")
            summary["model"] = event.get("model")
            # Other locally installed plugins are counted, not named.
            names = [item.get("name") for item in event.get("plugins", [])]
            summary["specmd_plugin_loaded"] = "specmd" in names
            summary["other_plugins"] = len([name for name in names if name != "specmd"])
        elif kind == "system" and subtype == "hook_response":
            name = event.get("hook_event")
            summary["hooks"][name] = summary["hooks"].get(name, 0) + 1
            if event.get("exit_code") != 0:
                summary["hook_failures"].append({"hook": event.get("hook_name"), "exit_code": event.get("exit_code"),
                                                 "stderr": _sanitize((event.get("stderr") or "")[:200], base)})
            try:
                reply = json.loads(event.get("stdout") or "null")
            except ValueError:
                reply = None
            specific = reply.get("hookSpecificOutput", {}) if isinstance(reply, dict) else {}
            if specific.get("permissionDecision") == "deny":
                summary["denials"].append({"hook": event.get("hook_name"),
                                           "reason": specific.get("permissionDecisionReason", "")[95:200]})
            if name == "Stop" and isinstance(reply, dict):
                summary["stop_outputs"].append({key: reply.get(key) for key in ("continue", "decision") if key in reply}
                                               | {"status": (reply.get("stopReason") or reply.get("reason") or "").split(";")[0]})
        elif kind == "assistant":
            for item in event.get("message", {}).get("content", []):
                if item.get("type") == "tool_use":
                    summary["tool_uses"].append({"tool": item.get("name"),
                                                 "target": _target(item.get("input") or {}, project)})
        elif kind == "result":
            summary.update({"turns": event.get("num_turns"), "is_error": event.get("is_error"),
                            "cost_usd": event.get("total_cost_usd")})
    return summary


def run_case(name: str, prompt: str, args, base: Path) -> dict:
    project = base / name
    created = subprocess.run([args.python, "-m", "specmd", "demo", "--dest", str(project)],
                             capture_output=True, text=True, timeout=60, check=True)
    trust = json.loads(created.stdout)["trust_store"]
    before = _hashes(project)
    stream = base / f"{name}.jsonl"
    environment = {**os.environ, "SPECMD_PYTHON": args.python, "SPECMD_TRUST_STORE": trust}
    command = [args.claude, "-p", prompt, "--plugin-dir", str(args.plugin_dir),
               "--setting-sources", "project,local", "--strict-mcp-config", "--model", args.model,
               "--permission-mode", "acceptEdits", "--output-format", "stream-json", "--verbose",
               "--include-hook-events", "--no-session-persistence"]
    with stream.open("w", encoding="utf-8") as output:
        completed = subprocess.run(command, cwd=project, env=environment, stdout=output,
                                   stderr=subprocess.DEVNULL, timeout=args.timeout)
    after = _hashes(project)
    summary = _summarize(stream, project, base)
    code_attempts = [use for use in summary["tool_uses"] if use["tool"] in {"Edit", "Write", "MultiEdit"}
                     and use["target"] in {"app.py", "tests/steps/cart_steps.py"}]
    changed = sorted(path for path in WATCHED if before[path] != after[path])
    expectations = {
        "specmd_plugin_loaded": summary.get("specmd_plugin_loaded") is True,
        "lifecycle_events_dispatched": all(summary["hooks"].get(event) for event in ("SessionStart", "PreToolUse", "Stop")),
        "no_hook_failures": not summary["hook_failures"],
        "code_edit_exercised": name != "forced_code_edit" or bool(code_attempts),
        "code_unchanged_without_acceptance": not {"app.py", "tests/steps/cart_steps.py"} & set(changed),
        "code_edits_denied": len([d for d in summary["denials"] if d["hook"] in {"PreToolUse:Edit", "PreToolUse:Write", "PreToolUse:MultiEdit"}]) >= len(code_attempts),
        "stop_returns_control": bool(summary["stop_outputs"]) and all(item.get("continue") is False or item.get("decision") == "block"
                                                                       for item in summary["stop_outputs"]),
    }
    return {"case": name, "prompt": prompt, "exit_code": completed.returncode, "changed_files": changed,
            "code_edit_attempts": len(code_attempts), **summary, "expectations": expectations,
            "expectation_met": all(expectations.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--plugin-dir", type=Path, default=ROOT / "dist/codex-plugin")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--model", default="haiku")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=Path, default=ROOT / ".specmd/local/claude-headless.json")
    args = parser.parse_args()
    if not (args.plugin_dir / ".claude-plugin/plugin.json").is_file():
        print("Gere o bundle com scripts/build_codex_plugin.py ou informe --plugin-dir.", file=sys.stderr)
        return 2
    version = subprocess.run([args.claude, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    base = Path(tempfile.mkdtemp(prefix="specmd-claude-")).resolve()
    cases = [run_case(name, prompt, args, base) for name, prompt in CASES.items()]
    sources = [Path(__file__), ROOT / "hooks/hooks.json", ROOT / "scripts/specmd_hook.py",
               ROOT / ".claude-plugin/plugin.json", *sorted((ROOT / "src/specmd").glob("*.py"))]
    report = {
        "schema": 1, "observed_at_utc": datetime.now(timezone.utc).isoformat(), "claude_version": version,
        "plugin_dir": _sanitize(str(args.plugin_dir.resolve()), base),
        "flags": "-p --setting-sources project,local --strict-mcp-config --permission-mode acceptEdits",
        "scope": ("Native headless Claude Code with a real model and the SpecMD plugin loaded by --plugin-dir, "
                  "before any acceptance. Not exercised: workspace trust dialog, interactive UX, marketplace "
                  "installation, user settings/hooks, human review or protected deployment."),
        "real_llm_executed": True, "human_review_performed": False, "acceptance_issued": False,
        "cases": cases, "passed": all(case["expectation_met"] for case in cases),
        "source_sha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sources},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "cases": [
        {key: case[key] for key in ("case", "hooks", "code_edit_attempts", "changed_files", "expectation_met")}
        for case in cases], "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
