"""Only the scenarios a code change can affect run again (SMD-REQ-027)."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from specmd import selection, workflow
from specmd.cli import main
from specmd.demo import create_demo

CAN_MEASURE = sys.version_info >= (3, 12)
APP = Path("app.py")


class PythonBlockTests(unittest.TestCase):
    def blocks(self, source):
        return selection.python_blocks(source.encode())

    def test_only_a_body_change_is_local(self):
        base = self.blocks("import os\n\nclass Cart:\n    def add(self, x):\n        return x\n\n"
                           "    def total(self):\n        return 0\n\n\ndef helper():\n    return 1\n")
        body = self.blocks("import os\n\nclass Cart:\n    def add(self, x):\n        return x + 1\n\n"
                           "    def total(self):\n        return 0\n\n\ndef helper():\n    return 1\n")
        self.assertEqual(base["module"], body["module"])
        changed = {key for key in base["blocks"] if base["blocks"][key] != body["blocks"][key]}
        self.assertEqual(changed, {"Cart.add#1"})

    def test_module_level_changes_and_formatting(self):
        base = self.blocks("LIMIT = 7\n\n@cache\ndef f(a):\n    return a\n")
        for source in ("LIMIT = 8\n\n@cache\ndef f(a):\n    return a\n",
                       "LIMIT = 7\n\n@other\ndef f(a):\n    return a\n",
                       "LIMIT = 7\n\n@cache\ndef f(a, b=1):\n    return a\n",
                       "import os\nLIMIT = 7\n\n@cache\ndef f(a):\n    return a\n"):
            with self.subTest(source=source):
                self.assertNotEqual(self.blocks(source)["module"], base["module"])
        formatted = self.blocks("# comment\nLIMIT = 7\n\n\n@cache\ndef f(a):  # note\n    return (a)\n")
        self.assertEqual((formatted["module"], formatted["blocks"]), (base["module"], base["blocks"]))

    def test_nested_code_belongs_to_the_enclosing_function_and_names_repeat(self):
        blocks = self.blocks("@given('a')\ndef step_impl(c):\n    inner = lambda: 1\n    return inner\n\n"
                             "@given('b')\ndef step_impl(c):\n    pass\n")
        self.assertEqual(sorted(blocks["blocks"]), ["step_impl#1", "step_impl#2"])
        self.assertEqual(selection._block_at(blocks["ranges"], 1), "step_impl#1")
        self.assertEqual(selection._block_at(blocks["ranges"], 3), "step_impl#1")
        self.assertEqual(selection._block_at(blocks["ranges"], 6), "step_impl#2")
        self.assertEqual(selection._block_at(blocks["ranges"], 5), selection.MODULE)
        self.assertIsNone(self.blocks("def broken(:\n"))


@unittest.skipUnless(CAN_MEASURE, "per-scenario coverage requires Python 3.12+")
class AffectedScenarioTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-selection-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "cart"
        create_demo(self.root)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def replace(self, path, old, new):
        target = self.root / path
        text = target.read_text()
        self.assertIn(old, text)
        target.write_text(text.replace(old, new))

    def run_project(self, affected=True):
        run = workflow.run_project(self.root, affected=affected)["run"]
        return run["scenarios"], run["unselected"], sorted(failure["name"] for failure in run["failures"])

    def test_function_change_runs_only_the_scenarios_that_executed_it(self):  # SMD-SCN-118
        self.assertEqual(self.run_project(), (2, 0, []))
        self.replace(APP, "self.prices.append(price_cents)", "self.prices.append(price_cents + 0)")
        self.assertEqual(self.run_project(), (1, 1, []))
        self.assertEqual(self.run_project(), (0, 2, []))

    def test_module_level_change_runs_every_scenario(self):  # SMD-SCN-119
        for old, new in (("class Cart:", "LIMIT = 1\n\n\nclass Cart:"),
                         ('"""Small cart', 'import os\n"""Small cart'),
                         ("def add(self, price_cents):", "def add(self, price_cents, quantity=1):")):
            with self.subTest(change=new):
                self.run_project()
                self.replace(APP, old, new)
                self.assertEqual(self.run_project(), (2, 0, []))

    def test_failing_scenario_runs_again_after_an_unrelated_change(self):  # SMD-SCN-120
        self.replace(APP, "self.prices.append(price_cents)", "self.prices.append(price_cents + 1)")
        self.assertEqual(self.run_project(), (2, 0, ["Add two items"]))
        (self.root / "other.py").write_text("VALUE = 1\n")
        self.assertEqual(self.run_project(), (1, 1, ["Add two items"]))

    def test_without_coverage_every_scenario_runs(self):  # SMD-SCN-121
        bridge = ("import json,sys\np=json.load(sys.stdin)\ns=[{**i,'status':'passed','steps_executed':i['steps'],"
                  "'steps':[{'status':'passed'}]*i['steps']} for i in p['expected_scenarios']]\n"
                  "print(json.dumps({'schema':1,'mode':'real','dry_run':False,'engine_failed':False,"
                  "'passed':True,'scenarios':s}))\n")
        (self.root / "bridge.py").write_text(bridge)
        (self.root / "specmd.toml").write_text(
            f'[[runners]]\nid = "bridge"\nlanguage = "go"\ncommand = [{json.dumps(sys.executable)}, "bridge.py"]\n')
        self.assertEqual(self.run_project(), (2, 0, []))
        self.replace(APP, "self.prices.append(price_cents)", "self.prices.append(price_cents + 0)")
        self.assertEqual(self.run_project(), (2, 0, []))

    def test_cli_run_executes_every_scenario(self):  # SMD-SCN-122
        self.run_project()
        self.replace(APP, "self.prices.append(price_cents)", "self.prices.append(price_cents + 0)")
        with open(self.root / "output.json", "w") as stream, mock.patch("sys.stdout", stream):
            self.assertEqual(main(["run", "--root", str(self.root)]), 0)
        self.assertEqual(json.loads((self.root / "output.json").read_text())["run"]["scenarios"], 2)
        self.assertEqual(self.run_project(), (0, 2, []))

    def test_changed_scenario_and_new_scenario_run(self):
        self.run_project()
        self.replace("docs/cart.md", "Then the total should be 0 cents", "Then the total should be 0 cents\n    And the total should be 0 cents")
        self.assertEqual(self.run_project(), (1, 1, []))

    def test_data_files_read_by_a_scenario_select_it(self):
        self.replace("tests/steps/cart_steps.py", "def read_total(context):\n",
                     "def read_total(context):\n    open('limit.txt').read()\n")
        (self.root / "limit.txt").write_text("7\n")
        self.run_project(affected=False)
        (self.root / "limit.txt").write_text("8\n")
        self.assertEqual(self.run_project(), (1, 1, []))

    def test_scenarios_that_start_processes_always_run(self):
        self.replace("tests/steps/cart_steps.py", "def read_total(context):\n",
                     "def read_total(context):\n    import subprocess, sys\n"
                     "    subprocess.run([sys.executable, '-c', 'pass'], check=True)\n")
        self.run_project(affected=False)
        self.assertEqual(self.run_project(), (1, 1, []))

    def test_steps_environment_and_configuration_run_every_scenario(self):
        steps = (self.root / "tests/steps/cart_steps.py").read_text()
        for path, content in (("tests/steps/extra_steps.py", "VALUE = 1\n"),
                              ("tests/steps/cart_steps.py", steps.replace("context.cart = Cart()", "context.cart = Cart()\n    pass")),
                              ("tests/environment.py", "def before_all(context):\n    pass\n"),
                              ("specmd.toml", (self.root / "specmd.toml").read_text() + "\n# note\n")):
            with self.subTest(path=path):
                self.run_project()
                (self.root / path).write_text(content)
                self.assertEqual(self.run_project(), (2, 0, []))

    def test_missing_or_corrupt_coverage_runs_every_scenario(self):
        self.run_project()
        (self.root / ".specmd/local" / selection.COVERAGE_FILE).write_text("{corrupt")
        self.replace(APP, "self.prices.append(price_cents)", "self.prices.append(price_cents + 0)")
        self.assertEqual(self.run_project(), (2, 0, []))


if __name__ == "__main__":
    unittest.main()
