#!/usr/bin/env python3
"""Exercise the real Codex hook dispatcher with a deterministic local HTTP fixture.

This is NOT an LLM/model test. The backend emits fixed Responses API SSE events.
Default --plan starts no server, CLI, thread, model, or hook. --run requires the
reviewed SHA-256 of this file and grants native trust only to its two handlers.
No authentication header or existing credential is inspected or recorded.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import re
import shlex
import signal
import subprocess
import sys
import threading
import time


REPOSITORY = Path(__file__).resolve().parents[2]
DIRECTORY = REPOSITORY / "research/codex"
EVIDENCE = DIRECTORY / "evidence"
FIXTURES = DIRECTORY / "fixtures/runtime"
SELF = Path(__file__).resolve()
PYTHON = REPOSITORY / ".venv/bin/python"
COMMAND = shlex.join([str(PYTHON), str(SELF), "--record-hook"])
HOOK_LOG = EVIDENCE / "native-fixture-hook-events.jsonl"
RESULTS = EVIDENCE / "native-fixture-results.json"
CASES = ("blocked", "waiting")
FIXED_TEXT = "A verificação permanece pendente; aguardando o responsável."
PINNED_COMMIT = "83086188ae0614bd882818ff1aa23f3194962012"
OFFICIAL_SOURCES = [
    f"https://github.com/openai/codex/blob/{PINNED_COMMIT}/codex-rs/exec/tests/suite/hooks.rs#L26-L31",
    f"https://github.com/openai/codex/blob/{PINNED_COMMIT}/codex-rs/core/tests/common/responses.rs#L752-L790",
    f"https://github.com/openai/codex/blob/{PINNED_COMMIT}/codex-rs/core/tests/common/responses.rs#L820-L863",
    f"https://github.com/openai/codex/blob/{PINNED_COMMIT}/codex-rs/core/config.schema.json",
    f"https://github.com/openai/codex/blob/{PINNED_COMMIT}/codex-rs/model-provider-info/src/lib.rs#L139-L199",
    f"https://github.com/openai/codex/blob/{PINNED_COMMIT}/codex-rs/core/tests/suite/cli_stream.rs#L226-L243",
    f"https://github.com/openai/codex/blob/{PINNED_COMMIT}/sdk/python/tests/app_server_harness.py#L247-L337",
]


def scrub(value):
    value = str(value).replace(str(REPOSITORY), "[REPOSITORY]")
    result = []
    for line in value.splitlines():
        if re.search(r"authorization|bearer |api.?key|access.?token|refresh.?token|gh[pousr]_|sk-[A-Za-z0-9]", line, re.I):
            result.append("[REDACTED_AUTH_LINE]")
        else:
            result.append(line)
    return "\n".join(result)[:4000]


def hashes():
    paths = [SELF, REPOSITORY / "scripts/codex_hook.py"]
    paths += sorted((REPOSITORY / "src/specmd").glob("*.py"))
    return {str(path.relative_to(REPOSITORY)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def configuration(base_url):
    provider = {
        "name": "SpecMD deterministic local protocol fixture (not an LLM)",
        "base_url": base_url,
        "wire_api": "responses",
        "requires_openai_auth": False,
        "supports_websockets": False,
        "env_key": "SPECMD_FIXTURE_KEY",
        "request_max_retries": 0,
        "stream_max_retries": 0,
    }
    inline_provider = "{" + ", ".join(key + " = " + json.dumps(value) for key, value in provider.items()) + "}"
    settings = [
        "features.hooks=true", "features.plugins=false", "features.apps=false",
        'model_provider="specmd_fixture"', 'model="specmd-fixture"',
        "model_providers.specmd_fixture=" + inline_provider,
        'sqlite_home="/tmp/specmd-codex-native-fixture-db"',
        'log_dir="/tmp/specmd-codex-native-fixture-logs"',
    ]
    for event in ("SessionStart", "Stop"):
        settings.append("hooks." + event + "=[{hooks=[{type=\"command\",command="
                        + json.dumps(COMMAND) + ",timeout=30}]}]")
    return [part for setting in settings for part in ("-c", setting)]


def child_environment():
    # A dedicated custom provider uses only this invented fixture value. Do not
    # inspect existing credentials or redirect HOME/CODEX_HOME/auth storage.
    return {**os.environ, "SPECMD_FIXTURE_KEY": "local-test-only", "SPECMD_PYTHON": str(PYTHON)}


def record_hook():
    sys.path.insert(0, str(REPOSITORY / "src"))
    from specmd.codex import error_response, handle_hook

    payload = json.load(sys.stdin)
    try:
        reply = handle_hook(payload)
    except Exception as error:
        reply = error_response(str(error))
    cwd = Path(payload.get("cwd", "/"))
    record = {
        "case": cwd.name,
        "native_payload_keys": sorted(payload),
        "hook_event_name": payload.get("hook_event_name"),
        "source": payload.get("source"),
        "model": payload.get("model"),
        "permission_mode": payload.get("permission_mode"),
        "stop_hook_active": payload.get("stop_hook_active"),
        "transcript_path_present": bool(payload.get("transcript_path")),
        "last_assistant_message_present": payload.get("last_assistant_message") is not None,
        "session_id_digest": hashlib.sha256(str(payload.get("session_id")).encode()).hexdigest(),
        "adapter_reply": reply,
    }
    EVIDENCE.mkdir(exist_ok=True)
    with HOOK_LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(reply, ensure_ascii=False))


def sse_response(index):
    response_id = f"resp_specmd_fixture_{index}"
    item = {"id": f"msg_specmd_fixture_{index}", "type": "message", "role": "assistant",
            "status": "completed", "content": [{"type": "output_text", "text": FIXED_TEXT, "annotations": []}]}
    events = [
        {"type": "response.created", "response": {"id": response_id}},
        {"type": "response.output_item.done", "output_index": 0, "item": item},
        {"type": "response.completed", "response": {"id": response_id, "status": "completed",
         "output": [item], "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}},
    ]
    return "".join("event: " + event["type"] + "\ndata: " + json.dumps(event, ensure_ascii=False) + "\n\n"
                   for event in events).encode("utf-8")


class FixtureServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), FixtureHandler)
        self.active_case = "discovery"
        self.requests = []
        self.guard = threading.Lock()


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path != "/v1/models":
            self.send_error(404)
            return
        content = json.dumps({"object": "list", "data": [{"id": "specmd-fixture", "object": "model", "owned_by": "local-fixture"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        # Only Content-Length is consulted; authorization headers are neither
        # accessed nor recorded. Request content is consumed, never persisted.
        length = int(self.headers.get("Content-Length", "0"))
        if self.path != "/v1/responses" or not 0 <= length <= 2_000_000:
            self.send_error(400)
            return
        body = self.rfile.read(length)
        try:
            request = json.loads(body)
        except ValueError:
            self.send_error(400)
            return
        with self.server.guard:
            index = len(self.server.requests) + 1
            self.server.requests.append({"case": self.server.active_case, "method": "POST", "path": self.path,
                                         "request_bytes": len(body), "model": request.get("model"),
                                         "preflight_context_present": "O estado em .specmd/local/status.json é uma observação" in json.dumps(request, ensure_ascii=False),
                                         "stream": request.get("stream"), "response_index": index})
        if index > 6:
            self.send_error(503)
            return
        content = sse_response(index)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(content)
        self.wfile.flush()
        self.close_connection = True


def collect_stream(stream, output):
    for line in stream:
        output.put(line)


def close_process(process):
    if process.stdin and not process.stdin.closed:
        process.stdin.close()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)


def trust_arguments(hooks):
    # Keep dotted source paths inside quoted TOML map keys. A dotted CLI
    # assignment path can otherwise split the key before TOML value parsing.
    entries = [json.dumps(hook["key"]) + "={enabled=true,trusted_hash=" + json.dumps(hook["currentHash"]) + "}"
               for hook in hooks]
    return ["-c", "hooks.state={" + ",".join(entries) + "}"] if hooks else []


def discover(fixture, arguments, trusted=None):
    extra = trust_arguments(trusted or [])
    process = subprocess.Popen(["codex", *arguments, *extra, "app-server", "--stdio"], cwd=fixture,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding="utf-8", env=child_environment(), start_new_session=True)
    output, errors = queue.Queue(), queue.Queue()
    threading.Thread(target=collect_stream, args=(process.stdout, output), daemon=True).start()
    threading.Thread(target=collect_stream, args=(process.stderr, errors), daemon=True).start()

    def send(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    def response(request_id):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                message = json.loads(output.get(timeout=0.25))
            except (queue.Empty, ValueError):
                if process.poll() is not None:
                    break
                continue
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError("RPC error: " + scrub(json.dumps(message["error"])))
                return message.get("result", {})
        lines = []
        while not errors.empty():
            lines.append(errors.get_nowait())
        raise RuntimeError("Native hooks/list unavailable: " + scrub("".join(lines)))

    try:
        send({"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "specmd_native_fixture", "version": "0.1.0"}}})
        response(1)
        send({"method": "initialized"})
        send({"id": 2, "method": "hooks/list", "params": {"cwds": [str(fixture)]}})
        result = response(2)
        selected = [hook for entry in result.get("data", []) for hook in entry.get("hooks", [])
                    if hook.get("command") == COMMAND]
        if (len(selected) != 2 or {item.get("eventName") for item in selected} != {"sessionStart", "stop"}
                or any(item.get("source") != "sessionFlags" or item.get("async") is not False for item in selected)):
            raise RuntimeError("Native discovery did not return the two exact synchronous session handlers")
        keys = ("key", "eventName", "currentHash", "trustStatus", "source", "sourcePath", "enabled", "handlerType", "command", "async")
        return [{key: item.get(key) for key in keys} for item in selected]
    finally:
        close_process(process)


def fixture_hashes(fixture):
    return {str(path.relative_to(fixture)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(fixture.rglob("*")) if path.is_file() and ".specmd" not in path.relative_to(fixture).parts}


def run(reviewed_sha256):
    if hashlib.sha256(SELF.read_bytes()).hexdigest() != reviewed_sha256:
        raise SystemExit("The native-fixture harness changed after its explicit source review")
    source_hashes = hashes()
    EVIDENCE.mkdir(exist_ok=True)
    HOOK_LOG.unlink(missing_ok=True)
    server = FixtureServer()
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}/v1"
    arguments = configuration(base_url)
    rows = []
    try:
        for case in CASES:
            fixture = FIXTURES / case
            server.active_case = case
            hooks = discover(fixture, arguments)
            trusted_hooks = discover(fixture, arguments, hooks)
            if any(item["trustStatus"] != "trusted" for item in trusted_hooks):
                raise RuntimeError("Native hooks/list did not confirm trust for the exact two handlers")
            if hashes() != source_hashes:
                raise RuntimeError("Reviewed adapter/harness sources changed during the probe")
            state_arguments = trust_arguments(hooks)
            command = ["codex", "exec", "--ignore-user-config", "--ephemeral", "--json", "--sandbox", "read-only",
                       "--skip-git-repo-check", "-C", str(fixture), *arguments, *state_arguments,
                       "Teste de protocolo com resposta simulada. Não use ferramentas, não altere arquivos, não afirme aceite ou conclusão."]
            before = fixture_hashes(fixture)
            process = subprocess.Popen(command, cwd=REPOSITORY, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, encoding="utf-8", env=child_environment(), start_new_session=True)
            timed_out = False
            try:
                stdout, stderr = process.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    stdout, stderr = process.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    stdout, stderr = process.communicate(timeout=3)
            events = []
            for line in stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                summary = {"type": event.get("type")}
                if event.get("type") in ("error", "turn.failed"):
                    summary["error"] = scrub(json.dumps(event.get("error", event.get("message", ""))))
                if event.get("type") == "item.completed":
                    item = event.get("item", {})
                    summary["item_type"] = item.get("type")
                    if item.get("type") == "agent_message":
                        summary["text"] = item.get("text")  # Only the known fixed backend text is expected.
                    elif item.get("type") == "error":
                        summary["message"] = scrub(item.get("message", ""))
                events.append(summary)
            all_calls = [json.loads(line) for line in HOOK_LOG.read_text().splitlines()] if HOOK_LOG.exists() else []
            calls = [item for item in all_calls if item["case"] == case]
            stops = [item for item in calls if item["hook_event_name"] == "Stop"]
            starts = [item for item in calls if item["hook_event_name"] == "SessionStart"]
            status_path = fixture / ".specmd/local/status.json"
            status = json.loads(status_path.read_text()) if status_path.exists() else {}
            requests = [item for item in server.requests if item["case"] == case]
            expected = 2 if case == "blocked" else 1
            success = (not timed_out and process.returncode == 0 and len(starts) == 1 and len(stops) == expected
                       and len(requests) == expected and before == fixture_hashes(fixture)
                       and status.get("may_complete") is False and all(item["model"] == "specmd-fixture" for item in requests))
            if case == "blocked" and len(stops) == 2:
                success &= (status.get("status") == "blocked" and stops[0]["stop_hook_active"] is False
                            and stops[0]["adapter_reply"].get("decision") == "block"
                            and stops[1]["stop_hook_active"] is True and stops[1]["adapter_reply"].get("continue") is False)
            elif case == "waiting" and len(stops) == 1:
                success &= (status.get("status") == "waiting_human_review" and stops[0]["stop_hook_active"] is False
                            and stops[0]["adapter_reply"].get("continue") is False)
            rows.append({"case": case, "untrusted_discovery": hooks, "trusted_discovery": trusted_hooks,
                         "host_exit_code": process.returncode, "timed_out": timed_out, "events": events,
                         "stderr_excerpt": scrub(stderr), "native_session_start_calls": len(starts), "native_stop_calls": len(stops),
                         "http_requests": requests, "fixture_unchanged_except_observed_cache": before == fixture_hashes(fixture),
                         "specmd_status": status.get("status"), "specmd_may_complete": status.get("may_complete"),
                         "research_expectations_met": bool(success)})
            print(case, "host_exit=", process.returncode, "start=", len(starts), "stop=", len(stops), "expectations=", bool(success), flush=True)
    except Exception as error:
        rows.append({"case": server.active_case, "error": scrub(str(error)), "research_expectations_met": False})
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=3)
    result = {
        "stage": "native_codex_dispatch_with_simulated_responses_backend", "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "backend": {"kind": "deterministic_local_http_fixture", "real_llm_executed": False,
                    "base_url": base_url, "fixed_assistant_text": FIXED_TEXT, "sse_events": ["response.created", "response.output_item.done", "response.completed"],
                    "auth_header_inspected_or_recorded": False, "fake_provider_env_key": "SPECMD_FIXTURE_KEY", "fake_provider_value": "local-test-only"},
        "codex_version": subprocess.check_output(["codex", "--version"], text=True).strip(),
        "source_sha256": source_hashes, "official_sources": OFFICIAL_SOURCES, "cases": rows,
        "specific_handler_trust_via_session_flags": True, "global_config_written_by_harness": False,
        "home_or_codex_home_changed": False, "trust_bypass_used": False, "contract_acceptance_granted": False,
        "installed_plugin_dispatch_tested": False, "research_expectations_met": len(rows) == 2 and all(row["research_expectations_met"] for row in rows),
    }
    RESULTS.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0 if result["research_expectations_met"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="Show concrete handlers/provider without starting any process")
    parser.add_argument("--run", action="store_true", help="Run native Codex with a simulated local backend after explicit source review")
    parser.add_argument("--reviewed-sha256", help="SHA-256 of this exact reviewed file")
    parser.add_argument("--record-hook", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.record_hook:
        record_hook()
        return 0
    if args.run:
        if not args.reviewed_sha256:
            parser.error("--run requires --reviewed-sha256 following explicit review of these handlers and provider")
        return run(args.reviewed_sha256)
    print(json.dumps({"mode": "plan_only_no_processes_started", "handler_command": COMMAND,
                      "review_sha256": hashlib.sha256(SELF.read_bytes()).hexdigest(),
                      "config_arguments": configuration("http://127.0.0.1:EPHEMERAL/v1"),
                      "fake_provider_environment": {"SPECMD_FIXTURE_KEY": "local-test-only"},
                      "real_llm_executed": False, "contract_acceptance_granted": False,
                      "official_sources": OFFICIAL_SOURCES}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
