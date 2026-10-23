import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from specmd.cli import main
from specmd.demo import create_demo


class DemoTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-demo-test-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / "cart"

    def cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(list(args))
        return code, json.loads(output.getvalue())

    def test_demo_creates_documented_project_without_feature_files(self):
        result = create_demo(self.root)
        self.assertEqual(result["status"], "demo_created")
        self.assertTrue((self.root / "docs/cart.md").is_file())
        self.assertTrue((self.root / "tests/steps/cart_steps.py").is_file())
        self.assertFalse(list(self.root.rglob("*.feature")))
        self.assertFalse((self.root / ".specmd/traceability.json").exists())

    def test_demo_refuses_to_overwrite_existing_project(self):
        self.root.mkdir()
        (self.root / "keep.txt").write_text("x")
        with self.assertRaises(ValueError):
            create_demo(self.root)
        self.assertEqual((self.root / "keep.txt").read_text(), "x")

    def test_cli_check_and_run_report_status_with_exit_codes(self):
        create_demo(self.root)
        code, result = self.cli("check", "--root", str(self.root))
        self.assertEqual((code, result["status"]), (0, "ready"))
        code, result = self.cli("run", "--root", str(self.root))
        self.assertEqual((code, result["status"]), (0, "passing"))
        (self.root / "docs/extra.md").write_text("# Sem classificação\n")
        code, result = self.cli("check", "--root", str(self.root))
        self.assertEqual((code, result["status"]), (1, "needs_scenarios"))

    def test_cli_init_prepares_the_repository_and_can_run_again(self):
        self.root.mkdir()
        code, result = self.cli("init", "--root", str(self.root))
        self.assertEqual((code, result["status"]), (0, "initialized"))
        self.assertIn("[[runners]]", (self.root / "specmd.toml").read_text())
        self.assertIn("specmd.toml", result["changed"])
        code, result = self.cli("init", "--root", str(self.root))
        self.assertEqual((code, result["changed"]), (0, []))

    def test_cli_without_configuration_is_inactive(self):
        self.root.mkdir()
        code, result = self.cli("check", "--root", str(self.root))
        self.assertEqual((code, result["status"]), (2, "inactive"))


if __name__ == "__main__":
    unittest.main()
