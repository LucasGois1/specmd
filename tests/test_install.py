import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from specmd.demo import create_demo
from specmd.project_setup import PLUGIN_ID, initialize

REPOSITORY = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPOSITORY / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ManifestTests(unittest.TestCase):
    def test_marketplace_lists_the_repository_root_as_the_plugin(self):
        marketplace = json.loads((REPOSITORY / ".claude-plugin/marketplace.json").read_text())
        plugin = json.loads((REPOSITORY / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(marketplace["name"], "specmd")
        self.assertEqual([(entry["name"], entry["source"]) for entry in marketplace["plugins"]], [(plugin["name"], "./")])
        self.assertEqual(PLUGIN_ID, f"{plugin['name']}@{marketplace['name']}")
        self.assertNotIn("hooks", plugin)

    def test_command_and_skill_reference_the_plugin_root(self):
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/scripts/specmd_cli.py", (REPOSITORY / "commands/init.md").read_text())
        self.assertIn("name: specmd", (REPOSITORY / "skills/specmd/SKILL.md").read_text())

    def test_vendored_dependencies_match_the_lock(self):
        self.assertTrue(_load("vendor_deps").check())

    def test_bundle_carries_vendor_command_skill_and_marketplace(self):
        _load("build_codex_plugin").build()
        manifest = json.loads((REPOSITORY / "dist/codex-plugin/bundle-manifest.json").read_text())
        files = set(manifest["files_sha256"])
        for expected in ("vendor/behave/__init__.py", "vendor/markdown_it/__init__.py", "commands/init.md",
                         "skills/specmd/SKILL.md", ".claude-plugin/marketplace.json", "scripts/specmd_bootstrap.py"):
            self.assertIn(expected, files)


class InitializeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-init-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def settings(self):
        return json.loads((self.root / ".claude/settings.json").read_text())

    def test_new_repository_gets_configuration_ignore_settings_and_gitignore(self):
        result = initialize(self.root)
        self.assertEqual(sorted(result["changed"]), [".claude/settings.json", ".gitignore", ".specmdignore", "specmd.toml"])
        settings = self.settings()
        self.assertEqual(settings["enabledPlugins"], {PLUGIN_ID: True})
        self.assertEqual(settings["extraKnownMarketplaces"]["specmd"]["source"],
                         {"source": "github", "repo": "LucasGois1/specmd"})
        self.assertIn(".specmd/local/", (self.root / ".gitignore").read_text())
        self.assertIn("README.md", (self.root / ".specmdignore").read_text())

    def test_running_again_changes_nothing_and_keeps_existing_settings(self):
        (self.root / ".claude").mkdir()
        (self.root / ".claude/settings.json").write_text(json.dumps({
            "permissions": {"allow": ["Bash(make test)"]}, "enabledPlugins": {"other@team": True}}))
        (self.root / ".gitignore").write_text("node_modules/")
        (self.root / "specmd.toml").write_text("# meu\n")
        initialize(self.root)
        self.assertEqual(self.settings()["permissions"], {"allow": ["Bash(make test)"]})
        self.assertEqual(self.settings()["enabledPlugins"], {"other@team": True, PLUGIN_ID: True})
        self.assertEqual((self.root / "specmd.toml").read_text(), "# meu\n")
        self.assertEqual((self.root / ".gitignore").read_text(), "node_modules/\n.specmd/local/\n")
        self.assertEqual(initialize(self.root)["changed"], [])

    def test_invalid_settings_are_not_overwritten(self):
        (self.root / ".claude").mkdir()
        (self.root / ".claude/settings.json").write_text("[]")
        with self.assertRaises(ValueError):
            initialize(self.root)
        self.assertEqual((self.root / ".claude/settings.json").read_text(), "[]")


class BootstrapTests(unittest.TestCase):
    def test_hook_and_cli_run_without_site_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "cart"
            create_demo(root)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            environment = {key: value for key, value in os.environ.items()
                           if key not in {"PYTHONPATH", "SPECMD_PYTHON", "VIRTUAL_ENV"}}
            environment["CLAUDE_PROJECT_DIR"] = str(root)
            hook = subprocess.run([sys.executable, "-I", "-S", str(REPOSITORY / "scripts/specmd_hook.py")],
                                  input=json.dumps({"hook_event_name": "SessionStart"}), text=True,
                                  capture_output=True, env=environment, timeout=30)
            self.assertEqual(hook.returncode, 0, hook.stderr)
            self.assertIn("2 cenários", json.loads(hook.stdout)["hookSpecificOutput"]["additionalContext"])
            run = subprocess.run([sys.executable, "-I", "-S", str(REPOSITORY / "scripts/specmd_cli.py"), "run",
                                  "--root", str(root)], text=True, capture_output=True, env=environment, timeout=120)
            self.assertEqual(json.loads(run.stdout)["status"], "passing", run.stdout + run.stderr)

    def test_old_interpreter_without_alternative_is_reported_softly(self):
        bootstrap = _load("specmd_bootstrap")
        self.assertTrue(bootstrap.suitable(sys.executable, (3, 0)))
        self.assertFalse(bootstrap.suitable(sys.executable, (99, 0)))
        with patch.object(bootstrap, "candidates", return_value=iter([])):
            self.assertIsNone(bootstrap.find_interpreter((99, 0)))
            self.assertFalse(bootstrap.ensure("script.py", (99, 0)))
        with patch.dict(os.environ, {"SPECMD_BOOTSTRAPPED": "1"}):
            self.assertFalse(bootstrap.ensure("script.py", (99, 0)))


if __name__ == "__main__":
    unittest.main()
