#!/usr/bin/env python3
"""Exercise the installed Codex plugin with fixed local Responses API output.

The Codex process and cached plugin are real. This does not execute a real LLM.
Only session-scoped trust is granted; existing credentials are not inspected.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import threading

import probe_installation as installation
import probe_native_fixture as fixture

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "research/codex/evidence/installed-dispatch.json"
STATUS = ".specmd/local/status.json"


def post_tool_case(server, arguments):
    """A real Codex shell tool edits a disposable contract; inspect its post-hook."""
    with tempfile.TemporaryDirectory(prefix="specmd-post-tool-") as temporary:
        project = Path(temporary)
        contract = project / "contract.md"
        contract.write_bytes((fixture.FIXTURES / "waiting/contract.md").read_bytes())
        (project / "specmd.toml").write_text("schema = 1\n")
        before = hashlib.sha256(contract.read_bytes()).hexdigest()
        command = shlex.join([str(fixture.PYTHON), "-c",
                              "from pathlib import Path; p=Path('contract.md'); p.write_bytes(p.read_bytes()+b'\\nchanged-by-fixture\\n')"])
        observation = {}
        original = fixture.sse_response

        def response(index):
            requests = [request for request in server.requests if request["case"] == "post_tool_use"]
            if server.active_case == "post_tool_use" and len(requests) == 1:
                item = {"id": "fc_specmd", "type": "function_call", "call_id": "call_specmd",
                        "name": "exec_command", "arguments": json.dumps({"cmd": command, "yield_time_ms": 1000})}
                events = [{"type": "response.created", "response": {"id": "resp_specmd_tool"}},
                          {"type": "response.output_item.done", "output_index": 0, "item": item},
                          {"type": "response.completed", "response": {"id": "resp_specmd_tool", "status": "completed",
                           "output": [item], "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}}]
                return "".join("event: " + event["type"] + "\ndata: " + json.dumps(event) + "\n\n" for event in events).encode()
            if server.active_case == "post_tool_use" and len(requests) == 2:
                state_path = project / STATUS
                state = json.loads(state_path.read_text()) if state_path.exists() else {}
                observation.update({"hook_event": state.get("hook_event"), "status": state.get("status"),
                                    "may_complete": state.get("may_complete"),
                                    "observed_changes": state.get("observed_changes"),
                                    "contract_sha256": hashlib.sha256(contract.read_bytes()).hexdigest()})
            return original(index)

        fixture.sse_response = response
        server.active_case = "post_tool_use"
        try:
            completed = subprocess.run(["codex", "exec", "--ephemeral", "--json", "--sandbox", "workspace-write",
                                        "--skip-git-repo-check", "-C", str(project), *arguments,
                                        "Teste com ferramenta e respostas simuladas em contrato descartável; não declare aceite."],
                                       cwd=ROOT, input="", text=True, capture_output=True,
                                       timeout=60, env=fixture.child_environment())
        finally:
            fixture.sse_response = original
        state_path = project / STATUS
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        requests = [request for request in server.requests if request["case"] == "post_tool_use"]
        after = hashlib.sha256(contract.read_bytes()).hexdigest()
        passed = (completed.returncode == 0 and len(requests) == 2 and before != after
                  and observation.get("hook_event") == "PostToolUse"
                  and observation.get("contract_sha256") == after
                  and {"kind": "modified", "path": "contract.md"} in (observation.get("observed_changes") or [])
                  and observation.get("may_complete") is False
                  and state.get("hook_event") == "Stop" and state.get("may_complete") is False
                  and state.get("status") == "waiting_human_review")
        print("post_tool_use", "installed_plugin=", True, "requests=", len(requests), "expectations=", bool(passed), flush=True)
        return {"case": "post_tool_use", "host_exit_code": completed.returncode, "http_requests": requests,
                "contract_sha256_before": before, "contract_sha256_after": after,
                "post_tool_observation": observation, "last_hook_event": state.get("hook_event"),
                "specmd_may_complete": state.get("may_complete"), "specmd_status": state.get("status"),
                "stderr_excerpt": fixture.scrub(completed.stderr), "expectations_met": bool(passed)}


def main():
    # Recheck installation/cache/native trust before invoking the installed code.
    installation.main()
    package = json.loads((OUTPUT.parent / "installed-plugin.json").read_text())
    server = fixture.FixtureServer()
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_port}/v1"
    inline = fixture.configuration(base_url)
    arguments = []
    for index in range(0, len(inline), 2):
        setting = inline[index + 1]
        if setting.startswith("hooks."):
            continue  # No inline hook: dispatch only the actual installed plugin.
        if setting == "features.plugins=false":
            setting = "features.plugins=true"
        arguments += ["-c", setting]
    hooks = installation.list_hooks(arguments)
    arguments += fixture.trust_arguments(hooks)
    trusted = installation.list_hooks(arguments)
    assert all(hook["trustStatus"] == "trusted" for hook in trusted)
    rows = []
    try:
        for case in fixture.CASES:
            project = fixture.FIXTURES / case
            state_path = project / STATUS
            state_path.unlink(missing_ok=True)  # Reconstructible fixture observation.
            before = fixture.fixture_hashes(project)
            server.active_case = case
            command = ["codex", "exec", "--ephemeral", "--json", "--sandbox", "read-only",
                       "--skip-git-repo-check", "-C", str(project), *arguments,
                       "Teste do plugin instalado com resposta local simulada; não declare aceite ou conclusão."]
            completed = subprocess.run(command, cwd=ROOT, input="", text=True, capture_output=True,
                                       timeout=60, env=fixture.child_environment())
            state = json.loads(state_path.read_text()) if state_path.exists() else {}
            requests = [request for request in server.requests if request["case"] == case]
            events = [json.loads(line) for line in completed.stdout.splitlines() if line.startswith("{")]
            types = [event["type"] for event in events]
            expected_requests = 2 if case == "blocked" else 1
            expected_status = "blocked" if case == "blocked" else "waiting_human_review"
            passed = (completed.returncode == 0 and len(requests) == expected_requests
                      and requests[0]["preflight_context_present"]
                      and "turn.completed" in types and "turn.failed" not in types
                      and state.get("status") == expected_status and state.get("may_complete") is False
                      and state.get("hook_event") == "Stop" and before == fixture.fixture_hashes(project))
            warnings = [fixture.scrub(event["item"].get("message", "")) for event in events
                        if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "error"]
            rows.append({"case": case, "host_exit_code": completed.returncode, "event_types": types,
                         "host_messages": warnings, "stderr_excerpt": fixture.scrub(completed.stderr),
                         "http_requests": requests, "specmd_status": state.get("status"),
                         "specmd_may_complete": state.get("may_complete"), "last_hook_event": state.get("hook_event"),
                         "fixture_unchanged_except_observed_cache": before == fixture.fixture_hashes(project),
                         "expectations_met": bool(passed)})
            print(case, "installed_plugin=", True, "requests=", len(requests), "expectations=", bool(passed), flush=True)
        rows.append(post_tool_case(server, arguments))
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
    report = {"observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Real Codex CLI dispatch of the installed cached plugin with deterministic local Responses API output.",
              "real_llm_executed": False, "installed_plugin_id": installation.PLUGIN_ID,
              "cache_matches_canonical_sources": package["cache_matches_canonical_sources"],
              "temporary_trust_confirmed_by_native_listing": True, "human_ui_trust_tested": False,
              "global_trust_written": False, "contract_acceptance_granted": False,
              "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in (Path(__file__).resolve(), Path(installation.__file__), Path(fixture.__file__))},
              "cases": rows, "expectations_met": len(rows) == 3 and all(row["expectations_met"] for row in rows)}
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0 if report["expectations_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
