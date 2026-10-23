"""Execution evidence must come from real steps and an exact scenario inventory."""

import json
from pathlib import Path
import sys
import os
import py_compile
import tempfile
import unittest

from specmd.core import inspect_project
from specmd.runner import execute_project


CONTRACT = """---
specmd:
  schema: 1
  id: SMD-RUN-DOC-001
  kind: behavioral
---

## SMD-RUN-REQ-001 — Somar valores

```gherkin
# language: pt
@SMD-RUN-REQ-001
Funcionalidade: Soma executada
  @SMD-RUN-SCN-001
  Cenário: Chamar a aplicação
    Dado os números 2 e 3
    Quando a soma for calculada
    Então o resultado deve ser 5
```
"""

STEPS = """from behave import given, when, then
from application import add

@given('os números {a:d} e {b:d}')
def operands(context, a, b):
    context.operands = a, b

@when('a soma for calculada')
def calculate(context):
    context.result = add(*context.operands)

@then('o resultado deve ser {expected:d}')
def check(context, expected):
    assert context.result == expected
"""


class RunnerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="specmd-runner-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        (self.root / "specmd.toml").write_text("schema = 1\n")
        self.write("contract.md", CONTRACT)
        self.write("application.py", "from pathlib import Path\ndef add(a,b):\n Path('calls.txt').open('a').write('called\\n')\n return a+b\n")
        self.write("tests/steps/steps.py", STEPS)

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def execute(self, runner=None, *, inspection=None, evidence=None):
        return execute_project(self.root, inspection or inspect_project(self.root), {
            "schema": 2, "runners": [runner or {"id": "python", "language": "python"}],
            "evidence": evidence or {},
        })

    def bridge(self, transform="", *, exit_code=0):
        script = self.write("bridge.py", "import json,sys\np=json.load(sys.stdin)\ns=[]\n"
                            "for item in p['expected_scenarios']:\n"
                            " n=item.get('steps',1)\n"
                            " s.append({**item,'status':'passed','steps_executed':n,'steps':[{'status':'passed'}]*n})\n"
                            "r={'schema':1,'mode':'real','dry_run':False,'engine_failed':False,'passed':True,'scenarios':s}\n"
                            + transform + "\nprint(json.dumps(r))\nsys.exit(" + str(exit_code) + ")\n")
        return {"id": "bridge", "language": "go", "command": [sys.executable, str(script)]}

    def test_real_behave_steps_call_application_and_preserve_markdown_origin(self):
        result = self.execute()
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["mode"], "real")
        self.assertEqual((self.root / "calls.txt").read_text(), "called\n")
        scenario = result["scenarios"][0]
        self.assertEqual((scenario["id"], scenario["path"], scenario["block"], scenario["line"]),
                         ("SMD-RUN-SCN-001", "contract.md", 1, 15))
        self.assertEqual(scenario["steps_executed"], 3)
        self.assertFalse(list(self.root.rglob("*.feature")))

    def test_real_assertion_failure_cannot_be_evidence(self):
        self.write("contract.md", CONTRACT.replace("ser 5", "ser 99"))
        result = self.execute()
        self.assertFalse(result["passed"], result)
        self.assertEqual(result["scenarios"][0]["status"], "failed")
        self.assertEqual((self.root / "calls.txt").read_text(), "called\n")

    def test_timestamp_valid_old_bytecode_cannot_mask_changed_source(self):
        source = self.root / "application.py"
        py_compile.compile(str(source), doraise=True, invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
        before = source.stat()
        original = source.read_text()
        modified = original.replace("return a+b", "return a-b")
        self.assertNotEqual(original, modified)
        self.assertEqual(len(original.encode()), len(modified.encode()))
        source.write_text(modified)
        os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
        result = self.execute()
        self.assertFalse(result["passed"], result)
        self.assertEqual(result["scenarios"][0]["status"], "failed")

    def test_multiple_blocks_execute_once_each_with_separate_origins(self):
        second = CONTRACT.split("```gherkin", 1)[1].rsplit("```", 1)[0].replace("SMD-RUN-SCN-001", "SMD-RUN-SCN-002")
        self.write("contract.md", CONTRACT + "\nOutro exemplo obrigatório.\n\n```gherkin" + second + "```\n")
        result = self.execute()
        self.assertTrue(result["passed"], result)
        self.assertEqual([item["block"] for item in result["scenarios"]], [1, 2])
        self.assertEqual((self.root / "calls.txt").read_text(), "called\ncalled\n")

    def test_real_undefined_step_cannot_be_evidence(self):
        self.write("tests/steps/steps.py", STEPS.replace("@then('o resultado deve ser {expected:d}')", "@then('outro passo {expected:d}')"))
        result = self.execute()
        self.assertFalse(result["passed"], result)
        self.assertIn("undefined", {step["status"] for step in result["scenarios"][0]["steps"]})

    def test_project_dry_run_and_tag_configuration_are_not_loaded(self):
        self.write("behave.ini", "[behave]\ndry_run = true\ntags = @missing\n")
        self.assertTrue(self.execute()["passed"])
        self.assertTrue((self.root / "calls.txt").exists())

    def test_rule_outline_instances_execute_real_application_with_row_origins(self):
        self.write("specmd.toml", 'schema = 2\nproject_id = "runner-outline"\n')
        prefix = CONTRACT.split("```gherkin")[0]
        self.write("contract.md", prefix + """```gherkin
# language: pt
@SMD-RUN-REQ-001
Funcionalidade: Soma por linhas
  Regra: Somar cada linha
    @SMD-RUN-SCN-001
    Esquema do Cenário: Somar os valores
      Dado os números <a> e <b>
      Quando a soma for calculada
      Então o resultado deve ser <resultado>
    Exemplos:
      | a | b | resultado |
      | 2 | 3 | 5 |
      | 4 | 5 | 9 |
```
""")
        inspection = inspect_project(self.root)
        result = self.execute(inspection=inspection)
        self.assertTrue(result["passed"], result)
        self.assertEqual([item["id"] for item in result["scenarios"]],
                         ["SMD-RUN-SCN-001:row:1:1", "SMD-RUN-SCN-001:row:1:2"])
        self.assertEqual([item["line"] for item in result["scenarios"]],
                         [item["line"] for item in inspection["documents"][0]["scenarios"]])
        self.assertEqual((self.root / "calls.txt").read_text(), "called\ncalled\n")
        self.assertFalse(list(self.root.rglob("*.feature")))

    def test_new_markdown_since_inventory_blocks_execution(self):
        inspection = inspect_project(self.root)
        self.write("new.md", "# Novo requisito ainda não classificado\n")
        self.assertFalse(self.execute(inspection=inspection)["passed"])
        self.assertFalse((self.root / "calls.txt").exists())

    def test_workflow_traceability_manifest_extension_preserves_extraction_guard(self):
        import hashlib
        inspection = inspect_project(self.root)
        inspection["manifest"]["traceability_sha256"] = "a" * 64
        inspection["manifest_sha256"] = hashlib.sha256(json.dumps(
            inspection["manifest"], sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()).hexdigest()
        self.assertTrue(self.execute(inspection=inspection)["passed"])
        self.write("contract.md", CONTRACT + "\nAlterado.\n")
        self.assertFalse(self.execute(inspection=inspection)["passed"])

    def test_nonzero_bridge_exit_rejects_claimed_success(self):
        self.assertFalse(self.execute(self.bridge(exit_code=7))["passed"])

    def test_zero_filtered_skipped_pending_undefined_and_dry_run_are_rejected(self):
        mutations = (
            "r['scenarios']=[]", "s[0]['status']='skipped'", "s[0]['status']='pending'",
            "s[0]['status']='undefined'", "r['dry_run']=True", "s[0]['steps_executed']=0",
            "s[0]['steps_executed']=1; s[0]['steps']=[{'status':'passed'}]",
            "s[0]['steps'][0]['status']='skipped'", "s[0]['id']='SMD-UNKNOWN-SCN-1'",
            "r['scenarios']=s+s", "s[0]['line']=999", "r.pop('dry_run')",
            "r['mode']='mock'", "r['engine_failed']=True",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assertFalse(self.execute(self.bridge(mutation))["passed"])

    def test_malformed_bridge_output_fails_closed(self):
        command = [sys.executable, "-c", "print('not JSON')"]
        result = self.execute({"id": "bad", "language": "java", "command": command})
        self.assertFalse(result["passed"])
        self.assertEqual(result["findings"][0]["kind"], "runner_failed")

    def test_runner_timeout_is_not_success(self):
        result = self.execute({"id": "timeout", "language": "go", "timeout": 0.05,
                               "command": [sys.executable, "-c", "import time; time.sleep(5)"]})
        self.assertFalse(result["passed"])
        self.assertEqual(result["findings"][0]["kind"], "runner_timeout")

    def test_mock_requires_explicit_opt_in_and_preserves_simulated_assurance(self):
        runner = self.bridge("r['mode']='mock'")
        runner["language"] = "mock"
        self.assertFalse(self.execute(runner)["passed"])
        result = self.execute(runner, evidence={"allow_mock": True})
        self.assertTrue(result["passed"], result)
        self.assertEqual((result["mode"], result["assurance"]), ("mock", "simulated"))
        self.assertEqual(result["scenarios"][0]["mode"], "mock")

    def test_changed_markdown_is_rejected_before_application_execution(self):
        inspection = inspect_project(self.root)
        self.write("contract.md", CONTRACT + "\nTexto mudou.\n")
        self.assertFalse(self.execute(inspection=inspection)["passed"])
        self.assertFalse((self.root / "calls.txt").exists())

    def test_paths_must_assign_each_scenario_exactly_once(self):
        inspection = inspect_project(self.root)
        for runners in ([{"id": "missing", "language": "python", "paths": ["other.md"]}],
                        [{"id": "one", "language": "python"}, {"id": "two", "language": "python"}]):
            with self.subTest(runners=runners):
                result = execute_project(self.root, inspection, {"schema": 2, "runners": runners})
                self.assertFalse(result["passed"])
                self.assertFalse((self.root / "calls.txt").exists())

    def test_empty_inventory_is_not_success(self):
        result = execute_project(self.root, {"documents": []}, {"runners": [{"id": "p", "language": "python"}]})
        self.assertFalse(result["passed"])

    def test_invalid_runner_configuration_is_rejected(self):
        for value in (True, 0, -1, float("inf"), "10"):
            with self.subTest(timeout=value):
                self.assertFalse(self.execute({"id": "p", "language": "python", "timeout": value})["passed"])
        self.assertFalse(self.execute({"id": "p", "language": "python", "command": "echo success"})["passed"])
        self.assertFalse(self.execute({"id": "p", "language": "python", "steps": "../outside"})["passed"])


if __name__ == "__main__":
    unittest.main()
