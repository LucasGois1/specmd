#!/usr/bin/env python3
"""Exercise the SpecMD hooks in native, headless Claude Code sessions.

A real model runs `claude -p` against fresh `specmd demo` projects. The probe
records which hooks the host dispatched and what feedback they returned.
Headless mode skips the workspace trust dialog and user settings are excluded
to isolate the plugin. Commands, model and output paths are fixed: only flags
choose among them.
"""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "codex-plugin"
EVIDENCE = ROOT / "research/claude/evidence/headless-dispatch.json"
LOCAL_REPORT = ROOT / ".specmd/local/claude-headless.json"
MODEL = "haiku"
COUPON_DOC = """---
specmd:
  schema: 1
  id: SMD-DEMO-DOC-002
  kind: behavioral
---

# Coupons

## SMD-DEMO-REQ-003 — TEN coupon

The TEN coupon applies a 10% discount to the cart total, in cents.

```gherkin
# language: en
Feature: Discount coupon

  @SMD-DEMO-REQ-003 @SMD-DEMO-SCN-003
  Scenario: TEN coupon on a 1000-cent cart
    Given an empty cart
    When I add items of 500 and 500 cents
    And I apply the coupon "TEN"
    Then the total should be 900 cents
```
"""
COUPON_PATH = "docs/coupons.md"
GAP_PATH = "docs/shipping.md"
CASES = {
    # Documentation without scenarios must come back to the agent.
    "documentation_gap": (None, f"Create the file {GAP_PATH} describing the business rule: orders above "
                                "10000 cents get free shipping. Do not change any code."),
    # A code change that breaks a documented scenario must come back with the failure.
    "code_breaks_scenario": (None, "Change app.py so that total() adds a fixed fee of 1 cent. Do only that."),
    # Confirmed scenarios with an undefined step must be implemented until green.
    "implement_confirmed": (COUPON_DOC, f"The scenarios in {COUPON_PATH} have already been confirmed with me. "
                                        "Implement what is needed for them to pass."),
}


def _sanitize(value: str, base: Path) -> str:
    return value.replace(str(base), "<tmp>").replace(str(ROOT), "<repo>").replace(str(Path.home()), "~")


def _reply(event: dict) -> dict:
    try:
        reply = json.loads(event.get("stdout") or "null")
    except ValueError:
        return {}
    return reply if isinstance(reply, dict) else {}


def _on_init(summary: dict, event: dict) -> None:
    names = [item.get("name") for item in event.get("plugins", [])]
    summary.update({"claude_code_version": event.get("claude_code_version"), "model": event.get("model"),
                    "specmd_plugin_loaded": "specmd" in names,
                    "other_plugins": len([name for name in names if name != "specmd"])})


def _on_hook(summary: dict, event: dict, base: Path) -> None:
    name = event.get("hook_event")
    summary["hooks"][name] = summary["hooks"].get(name, 0) + 1
    if event.get("exit_code") != 0:
        summary["hook_failures"].append({"hook": event.get("hook_name"), "exit_code": event.get("exit_code"),
                                         "stderr": _sanitize((event.get("stderr") or "")[:200], base)})
    reply = _reply(event)
    text = (reply.get("reason") or reply.get("systemMessage")
            or reply.get("hookSpecificOutput", {}).get("additionalContext") or "")
    if text and name != "SessionStart":
        summary["feedback"].append({"hook": name, "decision": reply.get("decision"), "text": text[:400]})


def _on_assistant(summary: dict, event: dict, base: Path) -> None:
    for item in event.get("message", {}).get("content", []):
        if item.get("type") == "tool_use":
            target = (item.get("input") or {}).get("file_path") or ""
            summary["tool_uses"].append({"tool": item.get("name"), "target": _sanitize(target, base)})


def _summarize(stream: Path, base: Path) -> dict:
    summary = {"hooks": {}, "hook_failures": [], "feedback": [], "tool_uses": []}
    for line in stream.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind, subtype = event.get("type"), event.get("subtype")
        if kind == "system" and subtype == "init":
            _on_init(summary, event)
        elif kind == "system" and subtype == "hook_response":
            _on_hook(summary, event, base)
        elif kind == "assistant":
            _on_assistant(summary, event, base)
        elif kind == "result":
            summary.update({"turns": event.get("num_turns"), "is_error": event.get("is_error"),
                            "cost_usd": event.get("total_cost_usd")})
    return summary


def _expectations(name: str, summary: dict, state: dict) -> dict:
    feedback = summary["feedback"]
    common = {
        "specmd_plugin_loaded": summary.get("specmd_plugin_loaded") is True,
        "lifecycle_events_dispatched": all(summary["hooks"].get(event) for event in ("SessionStart", "Stop")),
        "no_hook_failures": not summary["hook_failures"],
        "never_stopped_session": all(item.get("decision") in {None, "block"} for item in feedback),
    }
    if name == "documentation_gap":
        common["gap_fed_back"] = any(GAP_PATH in item["text"] for item in feedback)
    elif name == "code_breaks_scenario":
        # Header of the failure feedback, "SpecMD: N of M ... failed", whether all scenarios ran or only the affected.
        common["failure_fed_back"] = any(item.get("decision") == "block" and re.search(r"SpecMD: \d+ of .*failed",
                                                                                       item["text"])
                                         for item in feedback)
    elif name == "implement_confirmed":
        common["scenarios_executed"] = isinstance(state.get("last_run"), dict)
    return common


def run_case(name: str, document: str | None, prompt: str, claude: str, plugin_dir: Path, timeout: int,
             base: Path) -> dict:
    project = base / name
    subprocess.run([sys.executable, "-m", "specmd", "demo", "--dest", str(project)],
                   capture_output=True, text=True, timeout=60, check=True)
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    if document:
        (project / COUPON_PATH).write_text(document, encoding="utf-8")
    stream = base / f"{name}.jsonl"
    environment = {key: value for key, value in os.environ.items() if key != "CLAUDE_PROJECT_DIR"}
    environment["SPECMD_PYTHON"] = sys.executable
    command = [claude, "-p", prompt, "--plugin-dir", str(plugin_dir),
               "--setting-sources", "project,local", "--strict-mcp-config", "--model", MODEL,
               "--permission-mode", "acceptEdits", "--output-format", "stream-json", "--verbose",
               "--include-hook-events", "--no-session-persistence"]
    with stream.open("w", encoding="utf-8") as output:
        completed = subprocess.run(command, cwd=project, env=environment, stdout=output,
                                   stderr=subprocess.DEVNULL, timeout=timeout)
    summary = _summarize(stream, base)
    check = subprocess.run([sys.executable, "-m", "specmd", "check", "--root", str(project)],
                           capture_output=True, text=True, timeout=120)
    final = json.loads(check.stdout)
    state_path = project / ".specmd/local/state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    expectations = _expectations(name, summary, state)
    return {"case": name, "prompt": prompt, "exit_code": completed.returncode, "final_status": final.get("status"),
            **summary, "expectations": expectations, "expectation_met": all(expectations.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--use-clone", action="store_true", help="Load the plugin from the clone instead of the built bundle")
    parser.add_argument("--record", action="store_true", help="Write to research/claude/evidence instead of .specmd/local")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    plugin_dir = ROOT if args.use_clone else BUNDLE
    output = EVIDENCE if args.record else LOCAL_REPORT
    claude = shutil.which("claude")
    if claude is None:
        print("claude CLI not found on PATH.", file=sys.stderr)
        return 2
    if not (plugin_dir / ".claude-plugin/plugin.json").is_file():
        print("Build the bundle with scripts/build_codex_plugin.py or use --use-clone.", file=sys.stderr)
        return 2
    version = subprocess.run([claude, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    base = Path(tempfile.mkdtemp(prefix="specmd-claude-")).resolve()
    cases = [run_case(name, document, prompt, claude, plugin_dir, args.timeout, base)
             for name, (document, prompt) in CASES.items()]
    sources = [Path(__file__), ROOT / "hooks/hooks.json", ROOT / "scripts/specmd_hook.py",
               ROOT / ".claude-plugin/plugin.json", *sorted((ROOT / "src/specmd").glob("*.py"))]
    report = {
        "schema": 2, "observed_at_utc": datetime.now(timezone.utc).isoformat(), "claude_version": version,
        "plugin_dir": _sanitize(str(plugin_dir), base),
        "flags": f"-p --model {MODEL} --setting-sources project,local --strict-mcp-config --permission-mode acceptEdits",
        "scope": ("Native headless Claude Code with a real model and the SpecMD plugin loaded by --plugin-dir. "
                  "Not exercised: workspace trust dialog, interactive UX, marketplace installation, user "
                  "settings/hooks, a real developer answering the agent."),
        "real_llm_executed": True, "cases": cases, "passed": all(case["expectation_met"] for case in cases),
        "source_sha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sources},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "cases": [
        {key: case[key] for key in ("case", "hooks", "final_status", "expectations")} for case in cases],
        "output": _sanitize(str(output), base)}, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
