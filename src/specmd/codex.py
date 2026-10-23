"""Codex command-hook entry point; the lifecycle lives in specmd.hooks."""

from .hooks import handle_hook, run_hook

__all__ = ["handle_hook", "run_hook"]
