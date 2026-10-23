#!/usr/bin/env python3
"""Native hook discovery and an explicitly authorized, session-scoped live probe.

Default --discover does not create a thread or ask a model. --run uses native
trusted_hash for only the concrete handlers in the reviewed discovery record;
it never bypasses trust or writes global config. This is not contract acceptance.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shlex
import subprocess
import threading
import time

REPOSITORY = Path(__file__).resolve().parents[2]
DIRECTORY = REPOSITORY / "research/codex"
EVIDENCE = DIRECTORY / "evidence"
PYTHON = REPOSITORY / ".venv/bin/python"
FIXTURES = DIRECTORY / "fixtures/runtime"
COMMAND = shlex.join([str(PYTHON), str(DIRECTORY / "record_hook.py")])
HOOK_LOG = EVIDENCE / "runtime-hook-events.jsonl"
CASE_NAMES = ("blocked", "waiting")


def scrub(text):
    text = text.replace(str(REPOSITORY), "[REPOSITORY]")
    lines = []
    for line in text.splitlines():
        if re.search(r"authorization|bearer |api.?key|access.?token|refresh.?token|gh[pousr]_|sk-[a-z0-9]", line, re.I):
            lines.append("[REDACTED_AUTH_LINE]")
        else:
            lines.append(line)
    return "\n".join(lines)[:4000]


def source_hashes():
    paths = [DIRECTORY / "record_hook.py", Path(__file__).resolve(), REPOSITORY / "scripts/specmd_hook.py"]
    paths += sorted((REPOSITORY / "src/specmd").glob("*.py"))
    return {str(path.relative_to(REPOSITORY)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def configuration():
    arguments = ["-c", "features.hooks=true", "-c", "features.plugins=false", "-c", "features.apps=false",
                 "-c", 'sqlite_home="/tmp/specmd-codex-hook-probe-db"',
                 "-c", 'log_dir="/tmp/specmd-codex-hook-probe-logs"']
    for event in ("SessionStart", "Stop"):
        declaration = '[{hooks = [{type = "command", command = ' + json.dumps(COMMAND) + ', timeout = 30}]}]'
        arguments += ["-c", f"hooks.{event}={declaration}"]
    return arguments


def collect_stream(stream, output):
    for line in stream:
        output.put(line)


def rpc_discover(fixture, config_arguments=None):
    process = subprocess.Popen(
        ["codex", *(configuration() if config_arguments is None else config_arguments), "app-server", "--stdio"],
        cwd=fixture, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", env={**os.environ, "SPECMD_PYTHON": str(PYTHON)},
    )
    output = queue.Queue()
    errors = queue.Queue()
    threading.Thread(target=collect_stream, args=(process.stdout, output), daemon=True).start()
    threading.Thread(target=collect_stream, args=(process.stderr, errors), daemon=True).start()

    def request(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    def response(expected_id):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                line = output.get(timeout=min(1, max(0.01, deadline - time.monotonic())))
            except queue.Empty:
                if process.poll() is not None:
                    break
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if message.get("id") == expected_id:
                return message
        diagnostics = []
        while not errors.empty():
            diagnostics.append(errors.get_nowait())
        raise RuntimeError(f"No app-server response for request {expected_id}; process exit={process.poll()}; "
                           + scrub("".join(diagnostics)))

    try:
        request({"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "specmd_research", "version": "0.1.0"}}})
        initialized = response(1)
        if "error" in initialized:
            raise RuntimeError("initialize rejected: " + scrub(json.dumps(initialized["error"])))
        request({"method": "initialized"})
        request({"id": 2, "method": "hooks/list", "params": {"cwds": [str(fixture)]}})
        listed = response(2)
        if "error" in listed:
            raise RuntimeError("hooks/list rejected: " + scrub(json.dumps(listed["error"])))
        entries = listed.get("result", {}).get("data", [])
        selected = []
        for entry in entries:
            for hook in entry.get("hooks", []):
                # Do not record unrelated user/plugin hooks or grant them trust.
                if hook.get("command") == COMMAND:
                    selected.append({key: hook.get(key) for key in (
                        "key", "eventName", "currentHash", "trustStatus", "source", "sourcePath", "enabled", "handlerType", "command", "async")})
        if len(selected) != 2:
            def shape(value, depth=0):
                if depth > 4:
                    return type(value).__name__
                if isinstance(value, dict):
                    return {key: shape(item, depth + 1) for key, item in value.items()}
                if isinstance(value, list):
                    return [shape(value[0], depth + 1)] if value else []
                return type(value).__name__
            raise RuntimeError(f"Expected exactly two concrete probe handlers, found {len(selected)}; response shape={shape(listed.get('result'))}")
        return {"case": fixture.name, "hooks": selected, "request": {"method": "hooks/list", "cwds": [str(fixture)]}}
    finally:
        if process.stdin:
            process.stdin.close()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


def discover():
    EVIDENCE.mkdir(exist_ok=True)
    try:
        rows = [rpc_discover(FIXTURES / case) for case in CASE_NAMES]
    except Exception as error:
        failure = {
            "stage": "native_discovery_without_thread_or_model",
            "status": "native_discovery_failed",
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "error": scrub(str(error)),
            "trust_granted": False,
            "native_hook_execution_observed": False,
            "model_execution_observed": False,
            "contract_acceptance_granted": False,
            "global_config_written": False,
        }
        (EVIDENCE / "runtime-discovery-current-failure.json").write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n")
        raise
    result = {
        "stage": "native_discovery_without_thread_or_model",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "hook_command": COMMAND,
        "source_sha256": source_hashes(),
        "cases": rows,
        "trust_granted": False,
        "contract_acceptance_granted": False,
        "global_config_written": False,
    }
    path = EVIDENCE / "runtime-discovery.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Native discovery saved to {path.relative_to(REPOSITORY)}; no trust or model requested.")
    for row in rows:
        for hook in row["hooks"]:
            print(row["case"], hook["eventName"], hook["key"], hook["currentHash"], hook["trustStatus"])


def run(review_path, cases=CASE_NAMES):
    review = json.loads(review_path.read_text())
    if review["source_sha256"] != source_hashes() or review["hook_command"] != COMMAND:
        raise SystemExit("Reviewed code/command changed; discover and review again before granting scoped trust.")
    HOOK_LOG.unlink(missing_ok=True)
    records = []
    for case in cases:
        fixture = FIXTURES / case
        row = next(item for item in review["cases"] if item["case"] == case)
        arguments = configuration()
        states = []
        for hook in row["hooks"]:
            if hook["command"] != COMMAND or hook["eventName"] not in ("sessionStart", "stop"):
                raise SystemExit("Refusing trust for an unexpected handler")
            state = '{enabled = true, trusted_hash = ' + json.dumps(hook["currentHash"]) + '}'
            states.append(json.dumps(hook["key"]) + "=" + state)
        # CLI override paths split on dots. Quote full hook keys inside the value.
        arguments += ["-c", "hooks.state={" + ",".join(states) + "}"]
        confirmed = rpc_discover(fixture, arguments)["hooks"]
        if not all(hook["trustStatus"] == "trusted" for hook in confirmed):
            raise SystemExit("Native hook trust was not confirmed; refusing to start a model turn")
        command = ["codex", "exec", "--ignore-user-config", "--ephemeral", "--json",
                   "--sandbox", "read-only", "--skip-git-repo-check", "-C", str(fixture), *arguments,
                   "Este é um teste de instrumentação dos hooks SpecMD. Não use ferramentas, não leia arquivos e não altere nada. "
                   "Responda somente que a verificação aguarda o responsável. Se receber feedback de hook, explique a pendência "
                   "sem tentar corrigir arquivos ou declarar a tarefa concluída."]
        before = {str(p.relative_to(fixture)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in fixture.glob("*") if p.is_file()}
        try:
            completed = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True,
                                       timeout=90, env={**os.environ, "SPECMD_PYTHON": str(PYTHON)})
            stdout, stderr, exit_code, timed_out = completed.stdout, completed.stderr, completed.returncode, False
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else error.stdout or ""
            stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else error.stderr or ""
            exit_code, timed_out = None, True
        events = []
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            kind = event.get("type", event.get("method"))
            summary = {"type": kind}
            if kind in ("error", "turn.failed"):
                summary["error"] = scrub(json.dumps(event.get("error", event.get("message", ""))))
            events.append(summary)
        after = {str(p.relative_to(fixture)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in fixture.glob("*") if p.is_file()}
        hook_records = []
        if HOOK_LOG.exists():
            hook_records = [json.loads(line) for line in HOOK_LOG.read_text().splitlines() if json.loads(line).get("case") == case]
        stop_records = [item for item in hook_records if item["hook_event_name"] == "Stop"]
        status_path = fixture / ".specmd/local/status.json"
        status = json.loads(status_path.read_text()) if status_path.exists() else None
        expected_stops = 2 if case == "blocked" else 1
        success = (not timed_out and exit_code == 0 and len(stop_records) == expected_stops
                   and any(item["hook_event_name"] == "SessionStart" for item in hook_records)
                   and status is not None and status.get("may_complete") is False
                   and before == after)
        if case == "blocked" and len(stop_records) == 2:
            success &= (stop_records[0]["adapter_reply"].get("decision") == "block"
                        and stop_records[0]["stop_hook_active"] is False
                        and stop_records[1]["stop_hook_active"] is True
                        and stop_records[1]["adapter_reply"].get("continue") is False)
        if case == "waiting" and len(stop_records) == 1:
            success &= (stop_records[0]["adapter_reply"].get("continue") is False
                        and status.get("status") == "waiting_human_review")
        records.append({"case": case, "host_exit_code": exit_code, "timed_out": timed_out,
                        "event_types": events, "stderr_excerpt": scrub(stderr),
                        "native_stop_calls": len(stop_records), "fixture_unchanged": before == after,
                        "specmd_status": status.get("status") if status else None,
                        "specmd_may_complete": status.get("may_complete") if status else None,
                        "research_expectations_met": bool(success)})
        print(case, "host_exit=", exit_code, "stop_calls=", len(stop_records), "expectations=", bool(success))
    report = {"stage": "live_native_session", "cases": records,
              "specific_handler_trust_requested_via_session_flags": True,
              "specific_handler_trust_confirmed_by_native_listing": True,
              "model_backend": "Configured Codex service; no simulated model responses.",
              "global_config_written": False,
              "trust_bypass_used": False, "contract_acceptance_granted": False,
              "plugin_installation_tested": False,
              "research_expectations_met": all(item["research_expectations_met"] for item in records)}
    (EVIDENCE / "runtime-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0 if report["research_expectations_met"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discover", action="store_true", help="List concrete hooks without trust or model")
    parser.add_argument("--run", action="store_true", help="Run two model sessions after explicit handler/code review")
    parser.add_argument("--reviewed-hooks", type=Path, help="Exact discovery record whose handlers/code were reviewed")
    parser.add_argument("--case", choices=CASE_NAMES, help="Run only one live-model fixture")
    args = parser.parse_args()
    if args.run:
        if not args.reviewed_hooks:
            parser.error("--run requires --reviewed-hooks after explicit authorization of these concrete handlers")
        return run(args.reviewed_hooks, (args.case,) if args.case else CASE_NAMES)
    discover()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
