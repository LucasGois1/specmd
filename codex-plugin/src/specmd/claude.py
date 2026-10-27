"""Claude Code command-hook entry point; the lifecycle lives in specmd.hooks.

Both hosts use the same event names, stdin fields and command-hook outputs, so
one translator keeps the feedback identical.
"""

from .hooks import handle_hook, run_hook

__all__ = ["handle_hook", "run_hook"]
