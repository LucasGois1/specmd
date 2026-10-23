#!/usr/bin/env python3
"""Exercise installed CLI and hook bootstrap against real Markdown, without a model."""

from datetime import datetime, timezone
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def run_probe(hook_bootstrap=None):
    cases = []
    hook_bootstrap = hook_bootstrap or ROOT / "scripts/specmd_hook.py"
    with tempfile.TemporaryDirectory(prefix="specmd-preflight-") as temporary:
        project = Path(temporary)

        def cli(name, *arguments):
            command = [sys.executable, "-m", "specmd", *arguments, "--root", str(project)]
            completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=20)
            report = json.loads(completed.stdout)
            cases.append({"name": name, "interface": "cli", "exit": completed.returncode,
                          "status": report["status"], "may_complete": report["may_complete"],
                          "manifest_sha256": report.get("manifest_sha256"),
                          "findings": [item["kind"] for item in report.get("findings", [])]})
            return completed.returncode, report

        def hook(name, event="Stop", active=False):
            payload = {"cwd": str(project), "hook_event_name": event, "stop_hook_active": active}
            completed = subprocess.run([sys.executable, str(hook_bootstrap)],
                                       input=json.dumps(payload), text=True, capture_output=True, timeout=20)
            reply = json.loads(completed.stdout)
            state_path = project / ".specmd/local/status.json"
            state = json.loads(state_path.read_text()) if state_path.exists() else None
            cases.append({"name": name, "interface": "hook-bootstrap", "event": event,
                          "exit": completed.returncode, "reply": reply,
                          "observed_status": state.get("status") if state else None,
                          "observed_may_complete": state.get("may_complete") if state else None})
            assert completed.returncode == 0
            return reply, state

        _, inactive = hook("unconfigured_noop")
        assert inactive is None
        exit_code, initialized = cli("initialize", "init", "--legacy")
        assert exit_code == 0 and initialized["may_complete"] is False
        (project / "unclassified.md").write_text("# Uma regra ainda não classificada\n", encoding="utf-8")
        exit_code, blocked = cli("unclassified_document", "check")
        assert exit_code == 1 and blocked["status"] == "blocked"
        assert blocked["may_complete"] is False
        reply, _ = hook("session_start_feedback", "SessionStart")
        assert reply["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        reply, _ = hook("repairable_first_stop")
        assert reply["decision"] == "block" and reply["reason"]
        reply, state = hook("repairable_repeated_stop", active=True)
        assert reply["continue"] is False and state["status"] == "blocked" and state["may_complete"] is False

        (project / "unclassified.md").unlink()
        source = ROOT / "examples/cancellation.contract.md"
        contract = project / "contract.md"
        contract.write_bytes(source.read_bytes())
        exit_code, pending = cli("valid_contract_pending_human", "check")
        assert exit_code == 1 and pending["status"] == "waiting_human_review"
        assert pending["may_complete"] is False
        scenarios = pending["documents"][0]["scenarios"]
        assert len(scenarios) == 2
        original_lines = source.read_text().splitlines()
        for scenario in scenarios:
            assert "Cenário:" in original_lines[scenario["line"] - 1]
        reply, state = hook("pending_human_returns_control")
        assert reply["continue"] is False and "decision" not in reply
        assert state["status"] == "waiting_human_review" and state["may_complete"] is False
        cases[-1]["scenario_origins"] = [{"id": s["id"], "line": s["line"]} for s in scenarios]

        contract.write_bytes(contract.read_bytes() + "\nProposta adicional ainda não aceita.\n".encode())
        reply, changed = hook("contract_change_detected", "PostToolUse")
        assert changed["manifest_sha256"] != pending["manifest_sha256"]
        assert {"kind": "modified", "path": "contract.md"} in changed["observed_changes"]
        assert changed["may_complete"] is False
        cases[-1]["observed_changes"] = changed["observed_changes"]
        cases[-1]["manifest_sha256"] = changed["manifest_sha256"]

        (project / "specmd.toml").write_text("schema = 2\n", encoding="utf-8")
        exit_code, error = cli("invalid_configuration", "check")
        assert exit_code == 2 and error["status"] == "error" and error["may_complete"] is False
        reply, state = hook("invalid_configuration_repeated_stop", active=True)
        assert reply["continue"] is False and state["status"] == "error"

    return {"observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "Installed Python CLI and hook bootstrap with real Markdown; no model session, human approval, protected gate, or BDD execution.",
            "versions": {name: importlib.metadata.version(name) for name in ("specmd", "markdown-it-py", "PyYAML", "behave")},
            "hook_bootstrap_sha256": hashlib.sha256(hook_bootstrap.read_bytes()).hexdigest(),
            "source_contract_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "all_expectations_met": True, "cases": cases}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, help="Validate the hook bootstrap copied into a built plugin bundle")
    args = parser.parse_args()
    result = run_probe(args.bundle / "scripts/specmd_hook.py" if args.bundle else None)
    output = Path(__file__).with_name("evidence") / ("bundle-integration.json" if args.bundle else "preflight-integration.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(result['cases'])} verificações de integração corresponderam às expectativas.")
