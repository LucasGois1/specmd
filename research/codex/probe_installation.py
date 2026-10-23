#!/usr/bin/env python3
"""Inspect the installed package and native hook trust without invoking a model."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ID = "specmd@specmd-local"


def list_hooks(overrides):
    command = ["codex", "-c", "features.hooks=true", "-c", "features.plugins=true",
               "-c", "features.apps=false", *overrides, "app-server", "--stdio"]
    process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True,
                               env={**os.environ, "SPECMD_PYTHON": str(ROOT / ".venv/bin/python")})
    output = queue.Queue()

    def reader():
        for line in process.stdout:
            output.put(line)

    threading.Thread(target=reader, daemon=True).start()

    def send(value):
        process.stdin.write(json.dumps(value) + "\n")
        process.stdin.flush()

    def receive(expected):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                line = output.get(timeout=0.2)
            except queue.Empty:
                if process.poll() is not None:
                    break
                continue
            item = json.loads(line)
            if item.get("id") == expected:
                if "error" in item:
                    raise RuntimeError("Native RPC failed: " + str(item["error"].get("code")))
                return item["result"]
        raise RuntimeError("Native hook discovery did not respond")

    try:
        send({"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "specmd_installation_probe", "version": "0.1.0"}}})
        receive(1)
        send({"method": "initialized"})
        send({"id": 2, "method": "hooks/list", "params": {"cwds": [str(ROOT / "research/codex/fixtures/runtime/waiting")]}})
        result = receive(2)
        fields = ("key", "eventName", "pluginId", "command", "source", "sourcePath", "enabled", "currentHash", "trustStatus", "async")
        hooks = [{name: hook.get(name) for name in fields} for entry in result["data"]
                 for hook in entry["hooks"] if hook.get("pluginId") == PLUGIN_ID]
        assert len(hooks) == 3, f"Expected three installed plugin hooks, found {len(hooks)}"
        assert {hook["eventName"] for hook in hooks} == {"sessionStart", "postToolUse", "stop"}
        assert all(hook["async"] is False for hook in hooks)
        return hooks
    finally:
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


def main():
    completed = subprocess.run(["codex", "plugin", "list", "--marketplace", "specmd-local", "--json"],
                               cwd=ROOT, capture_output=True, text=True, check=True, timeout=20)
    installed = [item for item in json.loads(completed.stdout)["installed"] if item["pluginId"] == PLUGIN_ID]
    assert len(installed) == 1 and installed[0]["installed"] and installed[0]["enabled"]
    initial = list_hooks([])
    states = []
    for hook in initial:
        state = '{enabled = true, trusted_hash = ' + json.dumps(hook["currentHash"]) + '}'
        states.append(json.dumps(hook["key"]) + "=" + state)
    overrides = ["-c", "hooks.state={" + ",".join(states) + "}"]
    scoped = list_hooks(overrides)
    assert all(hook["trustStatus"] == "trusted" for hook in scoped), scoped
    after = list_hooks([])
    assert {h["key"]: h["trustStatus"] for h in after} == {h["key"]: h["trustStatus"] for h in initial}
    plugin_root = Path(initial[0]["sourcePath"]).parent.parent
    manifest = json.loads((plugin_root / "bundle-manifest.json").read_text())
    matches = all(hashlib.sha256((plugin_root / name).read_bytes()).hexdigest() == digest
                  and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
                  for name, digest in manifest["files_sha256"].items())
    assert matches
    report = {"observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Actual marketplace installation and native hook listing/trust; no hook or model execution.",
              "installed": installed[0], "cache_matches_canonical_sources": matches,
              "initial_hooks": initial, "session_scoped_trust_hooks": scoped,
              "persistent_trust_unchanged": True, "human_ui_trust_tested": False,
              "contract_acceptance_granted": False, "expectations_met": True}
    output = ROOT / "research/codex/evidence/installed-plugin.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("Installed package verified; three native hooks recognized and session-scoped trust confirmed.")


if __name__ == "__main__":
    main()
