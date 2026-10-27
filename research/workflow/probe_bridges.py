#!/usr/bin/env python3
"""Exercise real native bridges through SpecMD's strict runner protocol."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from specmd.core import inspect_project
from specmd.runner import execute_project


CONTRACT = '''---
specmd:
  schema: 1
  id: SMD-NATIVE-DOC-001
  kind: behavioral
---

# Integração de execução
## SMD-NATIVE-REQ-001 — Somar valores
O resultado deve ser a soma dos valores informados.

```gherkin
# language: pt
@SMD-NATIVE-REQ-001
Funcionalidade: Soma
  @SMD-NATIVE-SCN-001
  Cenário: Somar com a aplicação
    Dado os números 2 e 3
    Quando a aplicação somar os números
    Então o resultado deve ser 5
```
'''

MDG = '''# Funcionalidade: Soma em MDG

Prosa sobre a soma.

## SMD-NATIVE-REQ-002 — Somar em MDG

### Cenário: Somar com a aplicação em MDG
* Dado os números 2 e 3
* Quando a aplicação somar os números
* Então o resultado deve ser 5
'''


CONTRACT_FILE = "contract.md"
MDG_FILE = "contract.feature.md"
CASES = (
    ("passes", CONTRACT_FILE, CONTRACT, None, True),
    ("assertion_failure", CONTRACT_FILE, CONTRACT.replace("ser 5", "ser 999"), None, False),
    ("undefined_step", CONTRACT_FILE, CONTRACT.replace("a aplicação somar os números", "um passo não implementado"), None, False),
    ("language_from_config", CONTRACT_FILE, CONTRACT.replace("# language: pt\n", ""), "pt", True),
    ("markdown_with_gherkin", MDG_FILE, MDG, "pt", True),
    ("markdown_with_gherkin_failure", MDG_FILE, MDG.replace("ser 5", "ser 999"), "pt", False),
)


def run_case(root, language, command, name, text, gherkin_language):
    for old in root.glob("*.md"):
        old.unlink()
    (root / "specmd.toml").write_text(f'gherkin_language = "{gherkin_language}"\n' if gherkin_language else "")
    (root / name).write_text(text, encoding="utf-8")
    config = {"runners": [{"id": language, "language": language, "command": command, "timeout": 60}]}
    if gherkin_language:
        config["gherkin_language"] = gherkin_language
    return execute_project(root, inspect_project(root), config)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--go-executable", type=Path)
    parser.add_argument("--java-runner", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / ".specmd/local/native-bridges.json")
    args = parser.parse_args()
    commands = []
    if args.go_executable:
        commands.append(("go", [str(args.go_executable.resolve(strict=True))]))
    if args.java_runner:
        commands.append(("java", ["bash", str(args.java_runner.resolve(strict=True)), "--glue", "specmd.example"]))
    if not commands:
        parser.error("Provide at least one real, already compiled executable.")
    cases = []
    with tempfile.TemporaryDirectory(prefix="specmd-native-bridge-") as temporary:
        root = Path(temporary)
        for language, command in commands:
            for case, name, text, gherkin_language, expected in CASES:
                report = run_case(root, language, command, name, text, gherkin_language)
                cases.append({"language": language, "case": case, "expected_passed": expected,
                              "expectation_met": report["passed"] == expected, "report": report})
        no_feature_files = not list(root.rglob("*.feature"))
    report = {"schema": 1, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Real Java/Go engines through execute_project, with example application steps. No LLM, human acceptance or protected deployment exercised.",
              "cases": cases, "no_feature_files": no_feature_files,
              "passed": no_feature_files and all(case["expectation_met"] for case in cases)}
    sources = [Path(__file__), *sorted((ROOT / "src/specmd").glob("*.py"))]
    sources += [p for p in (ROOT / "adapters").rglob("*") if p.is_file()
                and ".work" not in p.parts and p.suffix in {".go", ".java", ".sh", ".xml", ".mod", ".sum"}]
    report["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "cases": [
        {k: case[k] for k in ("language", "case", "expectation_met")} for case in cases], "output": str(args.output)}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
