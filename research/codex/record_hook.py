#!/usr/bin/env python3
"""Record sanitized native payload shape, then call the actual SpecMD adapter."""

import hashlib
import json
from pathlib import Path
import sys

REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "src"))

from specmd.codex import error_response, handle_hook


def main():
    payload = json.load(sys.stdin)
    try:
        reply = handle_hook(payload)
    except Exception as error:
        reply = error_response(str(error))
    cwd = Path(payload.get("cwd", "/"))
    try:
        relative_cwd = str(cwd.relative_to(REPOSITORY))
    except ValueError:
        relative_cwd = "[OUTSIDE_REPOSITORY]"
    message = payload.get("last_assistant_message")
    record = {
        "case": cwd.name,
        "native_payload_keys": sorted(payload),
        "hook_event_name": payload.get("hook_event_name"),
        "cwd": relative_cwd,
        "source": payload.get("source"),
        "model": payload.get("model"),
        "permission_mode": payload.get("permission_mode"),
        "stop_hook_active": payload.get("stop_hook_active"),
        "transcript_path_present": bool(payload.get("transcript_path")),
        "last_assistant_message_present": message is not None,
        "last_assistant_message_characters": len(message) if isinstance(message, str) else None,
        "session_id_digest": hashlib.sha256(str(payload.get("session_id")).encode()).hexdigest(),
        "turn_id_digest": hashlib.sha256(str(payload.get("turn_id")).encode()).hexdigest() if "turn_id" in payload else None,
        "adapter_reply": reply,
    }
    evidence = REPOSITORY / "research/codex/evidence/runtime-hook-events.jsonl"
    evidence.parent.mkdir(exist_ok=True)
    with evidence.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(reply, ensure_ascii=False))


if __name__ == "__main__":
    main()
