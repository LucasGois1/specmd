"""Claude Code command-hook adapter using the shared workflow translation.

SessionStart/PostToolUse additionalContext and Stop decision/continue outputs
follow https://code.claude.com/docs/en/hooks . This module's protocol tests do
not claim that a native Claude Code process has dispatched these hooks.
"""

import json
import sys

from .codex import error_response, handle_hook as handle_workflow_hook


def handle_hook(payload, inspect=None):
    # Both hosts use these event names, stdin fields and command-hook outputs.
    # Keep decisions in one translator to avoid different completion policies.
    return handle_workflow_hook(payload, inspect)


def run_hook():
    try:
        reply = handle_hook(json.load(sys.stdin))
    except Exception as error:
        reply = error_response(str(error))
    print(json.dumps(reply, ensure_ascii=False))
    return 0
