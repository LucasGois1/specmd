"""Local preimplementation policy tests; not proof of native hook dispatch."""

import json
from pathlib import Path
import tempfile
import unittest

from specmd.pretool import pretool_decision


class PretoolTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "docs").mkdir()
        self.pending = {"status": "waiting_human_review", "may_complete": False}

    def decision(self, name, values, result=None, **extra):
        payload = {"hook_event_name": "PreToolUse", "cwd": str(self.root),
                   "tool_name": name, "tool_input": values, **extra}
        return pretool_decision(self.root, payload, self.pending if result is None else result)

    def denied(self, response):
        output = response["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertIn("aceite", output["permissionDecisionReason"])

    def test_source_edits_are_denied_before_acceptance(self):
        for name in ("Edit", "Write"):
            with self.subTest(name=name):
                self.denied(self.decision(name, {"file_path": "src/application.py", "content": "x"}))

    def test_document_config_and_mapping_edits_remain_available(self):
        for path in ("docs/contract.md", "docs/notes.MARKDOWN", "specmd.toml", ".specmd/traceability.json"):
            with self.subTest(path=path):
                self.assertEqual(self.decision("Write", {"file_path": path, "content": "draft"}), {})

    def test_all_multiedit_paths_are_checked(self):
        values = {"edits": [{"file_path": "docs/one.md"}, {"file_path": "src/app.py"}]}
        self.denied(self.decision("MultiEdit", values))
        self.assertEqual(self.decision("MultiEdit", {"file_path": "docs/one.md", "edits": [{"old_string": "a", "new_string": "b"}]}), {})
        self.denied(self.decision("MultiEdit", {"edits": [{"old_string": "a"}]}))
        self.denied(self.decision("MultiEdit", {"edits": [{"file_path": "docs/one.md"}, {"old_string": "a"}]}))

    def test_external_authority_traversal_and_symlinks_are_denied(self):
        for path in (str(self.root.parent / "authority.json"), "../outside.md", "docs/../contract.md", ".git/note.md"):
            with self.subTest(path=path):
                self.denied(self.decision("Write", {"file_path": path}))
        (self.root / "docs" / "linked.md").symlink_to(self.root.parent / "outside.md")
        self.denied(self.decision("Edit", {"file_path": "docs/linked.md"}))
        self.denied(self.decision("Read", {"file_path": str(self.root.parent / "authority.json")}))

    def test_known_read_tools_are_allowed_without_authorizing_other_tools(self):
        for name, values in (("Read", {"file_path": "src/app.py"}), ("Grep", {"pattern": "requirement", "path": "."}), ("Glob", {"pattern": "**/*.md"})):
            with self.subTest(name=name):
                self.assertEqual(self.decision(name, values), {})
        self.denied(self.decision("Glob", {"pattern": "../authority/*"}))
        self.denied(self.decision("unknown_tool", {}))

    def test_document_patch_and_moves_are_allowed_but_mixed_patch_is_denied(self):
        document = "*** Begin Patch\n*** Add File: docs/new.md\n+Draft\n*** End Patch"
        self.assertEqual(self.decision("functions.apply_patch", {"input": document}), {})
        move = "*** Begin Patch\n*** Update File: docs/old.md\n*** Move to: docs/new.md\n@@\n-old\n+new\n*** End Patch"
        self.assertEqual(self.decision("apply_patch", move), {})
        mixed = document.replace("*** End Patch", "*** Add File: src/app.py\n+pass\n*** End Patch")
        self.denied(self.decision("apply_patch", {"patch": mixed}))
        self.denied(self.decision("apply_patch", move.replace("docs/new.md", "src/app.py")))

    def test_delete_paths_and_unknown_patch_syntax_do_not_escape_checks(self):
        delete = "*** Begin Patch\n*** Delete File: docs/old.md\n*** End Patch"
        self.assertEqual(self.decision("apply_patch", {"patch": delete}), {})
        for patch in (delete.replace("docs/old.md", "../outside.md"), "*** Begin Patch\n*** Mystery: docs/x.md\n*** End Patch", "*** Begin Patch\n*** Update File: docs/x.md\n@@\n*** End Patch"):
            self.denied(self.decision("apply_patch", {"patch": patch}))
        self.denied(self.decision("apply_patch", {"input": delete, "patch": "different"}))

    def test_document_update_allows_real_patch_empty_context_lines(self):
        patch = "*** Begin Patch\n*** Update File: docs/contract.md\n@@\n # Contrato\n\n-old\n+new\n*** End Patch"
        self.assertEqual(self.decision("apply_patch", {"patch": patch}), {})

    def test_simple_read_commands_are_allowed(self):
        for command in ("rg --files", "rg --files -g '*.md'", "rg -n 'contract|scenario' docs", "ls -la", "cat docs/contract.md", "git status --short", "git diff --stat", "git log -1 --format=%H", "git show HEAD:src/app.py", f"git -C {self.root} status"):
            with self.subTest(command=command):
                self.assertEqual(self.decision("exec_command", {"cmd": command}), {})
        self.assertEqual(self.decision("Bash", {"command": "git status"}), {})

    def test_shell_writes_operators_substitutions_and_unknown_commands_are_denied(self):
        for command in ("python -c 'pass'", "touch src/app.py", "cat docs/a.md > src/app.py", "git status && touch src/app.py", "cat docs/a.md | head", 'cat "$(pwd)/docs/a.md"', "cat `pwd`/a.md", "cat docs/*.md", "git status\nls", "env cat docs/a.md"):
            with self.subTest(command=command):
                self.denied(self.decision("exec_command", {"cmd": command}))

    def test_read_command_options_cannot_request_execution_or_output_files(self):
        for command in ("rg --pre evil pattern .", "rg --follow pattern .", "rg --ignore-file /outside/authority pattern .", "git -c core.pager=evil log", "git diff --ext-diff", "git diff --textconv", "git diff --output=src/app.py", "git diff --output src/app.py", "git show --no-index /outside/a /outside/b", "git checkout main"):
            with self.subTest(command=command):
                self.denied(self.decision("exec_command", {"cmd": command}))

    def test_workdir_and_read_paths_must_stay_inside_project(self):
        self.denied(self.decision("exec_command", {"cmd": "cat /outside/authority.json"}))
        self.denied(self.decision("exec_command", {"cmd": "ls", "workdir": str(self.root.parent)}))
        self.denied(self.decision("exec_command", {"cmd": "ls", "shell": "/tmp/custom-shell"}))
        self.denied(self.decision("exec_command", {"cmd": "ls", "command": "touch src/app.py"}))

    def test_verified_approval_or_completion_restores_host_policy(self):
        for result in ({"may_complete": True}, {"may_complete": False, "approval": {"valid": True}}):
            self.assertEqual(self.decision("Write", {"file_path": "src/app.py"}, result), {})
            self.assertEqual(self.decision("exec_command", {"cmd": "python app.py"}, result), {})
        self.denied(self.decision("Write", {"file_path": "src/app.py"}, {"may_complete": "true", "approval": {"valid": "true"}}))

    def test_hook_packages_declare_same_pretool_command(self):
        repository = Path(__file__).resolve().parents[1]
        for relative in ("hooks/hooks.json", "integrations/claude/hooks.json"):
            data = json.loads((repository / relative).read_text())
            pretool = data["hooks"]["PreToolUse"][0]["hooks"][0]
            original = data["hooks"]["PostToolUse"][0]["hooks"][0]
            self.assertEqual(pretool, original)


if __name__ == "__main__":
    unittest.main()
