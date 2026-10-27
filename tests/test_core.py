import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from specmd import core
from specmd.core import compile_ignore, extract_features, inspect_project, is_ignored


def block(*scenarios, header="# language: en\nFeature: Rules\n"):
    return "```gherkin\n" + header + "".join(scenarios) + "```\n"


def scenario(name="Add", tags="", steps="    Given a step\n"):
    tag_line = f"  {tags}\n" if tags else ""
    return f"\n{tag_line}  Scenario: {name}\n{steps}"


class InspectProjectTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-core-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.write("specmd.toml", "")

    def write(self, relative, content):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")
        return target

    def report(self):
        return inspect_project(self.root)

    def kinds(self, report):
        return {finding["kind"] for finding in report["findings"]}

    def scenarios(self, report, path="docs/rules.md"):
        return next(item for item in report["documents"] if item["path"] == path)["scenarios"]

    def test_without_configuration_the_defaults_apply(self):
        (self.root / "specmd.toml").unlink()
        self.write("docs/a.md", "# No scenarios\n")
        report = self.report()
        self.assertEqual(report["status"], "needs_scenarios")
        self.assertEqual([item["path"] for item in report["documents"]], ["docs/a.md"])

    def test_common_project_files_are_ignored_by_default(self):
        for name in ("README.md", "CHANGELOG.md", "AGENTS.md", "CLAUDE.md", "LICENSE.md", ".github/PULL_REQUEST_TEMPLATE.md"):
            self.write(name, "# Project file\n")
        self.assertEqual(self.report()["status"], "ready")
        self.write(".specmdignore", "!README.md\n")
        self.assertEqual([item["path"] for item in self.report()["documents"]], ["README.md"])

    def test_invalid_or_symlinked_configuration_is_an_error(self):
        for content in ("schema = 7\n", "x = [\n", "unknown = 1\n"):
            with self.subTest(content=content):
                self.write("specmd.toml", content)
                self.assertEqual(self.report()["status"], "error")
        (self.root / "specmd.toml").unlink()
        outside = self.root.parent / f"{self.root.name}-outside.toml"
        outside.write_text("")
        self.addCleanup(outside.unlink)
        (self.root / "specmd.toml").symlink_to(outside)
        self.assertIn("config_symlink", self.kinds(self.report()))

    def test_empty_project_is_ready(self):
        report = self.report()
        self.assertEqual((report["status"], report["protocol_version"]), ("ready", 2))

    def test_markdown_without_frontmatter_and_with_scenarios_is_ready(self):
        self.write("docs/rules.md", "# Rules\n\n" + block(scenario()))
        report = self.report()
        self.assertEqual(report["status"], "ready", report["findings"])
        self.assertEqual(self.scenarios(report)[0]["id"], "docs/rules.md::Add")

    def test_frontmatter_is_ignored_and_line_numbers_are_kept(self):
        self.write("docs/rules.md", "---\nany: thing\nlist: [1, 2\n---\n# Rules\n\n" + block(scenario()))
        report = self.report()
        self.assertEqual(report["status"], "ready", report["findings"])
        self.assertEqual(self.scenarios(report)[0]["line"], 11)

    def test_document_without_scenarios_points_to_specmdignore(self):
        self.write("docs/setup.md", "# Setup\n\nInstall the dependencies.\n")
        report = self.report()
        self.assertEqual(report["status"], "needs_scenarios")
        finding = report["findings"][0]
        self.assertEqual((finding["kind"], finding["path"]), ("gherkin_missing", "docs/setup.md"))
        self.assertIn(".specmdignore", finding["message"])

    def test_specmdignore_removes_documents_from_the_analysis(self):
        self.write("README.md", "# Project\n")
        self.write("docs/setup.md", "# Setup\n")
        self.write("notes/drafts/idea.md", "# Idea\n")
        self.write("docs/rules.md", block(scenario()))
        self.write(".specmdignore", "# comment\nREADME.md\ndocs/setup.md\nnotes/\n")
        report = self.report()
        self.assertEqual(report["status"], "ready", report["findings"])
        self.assertEqual([item["path"] for item in report["documents"]], ["docs/rules.md"])

    def test_gitignored_and_pruned_markdown_is_not_analysed(self):
        self.write("node_modules/lib/README.md", "# Lib\n")
        self.write("generated/out.md", "# Generated\n")
        self.write(".gitignore", "generated/\n")
        self.write("docs/rules.md", block(scenario()))
        self.assertEqual([item["path"] for item in self.report()["documents"]], ["docs/rules.md", "generated/out.md"])
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.assertEqual([item["path"] for item in self.report()["documents"]], ["docs/rules.md"])

    def test_untracked_markdown_is_discovered_in_a_git_repository(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.write("docs/new.md", "# New\n")
        self.assertIn("gherkin_missing", self.kinds(self.report()))

    def test_scenarios_link_to_the_requirement_heading_above_them(self):
        self.write("docs/rules.md",
                   "# Rules\n\n" + block(scenario("General")) +
                   "\n## PAY-REQ-001 — Refund\n\nText.\n\n### Scenarios\n\n" + block(scenario("Refund")) +
                   "\n## PAY-REQ-002 — Charge\n\n" + block(scenario("Charge")))
        report = self.report()
        self.assertEqual(report["status"], "ready", report["findings"])
        links = {item["name"]: item["requirements"] for item in self.scenarios(report)}
        self.assertEqual(links, {"General": [], "Refund": ["PAY-REQ-001"], "Charge": ["PAY-REQ-002"]})

    def test_explicit_requirement_tags_override_position(self):
        self.write("docs/rules.md", "## REQ-1 — One\n\n## REQ-2 — Two\n\n" +
                   block(scenario("A", tags="@REQ-1"), scenario("B")))
        links = {item["name"]: item["requirements"] for item in self.scenarios(self.report())}
        self.assertEqual(links, {"A": ["REQ-1"], "B": ["REQ-2"]})
        self.assertNotIn("requirement_uncovered", self.kinds(self.report()))

    def test_requirement_without_scenario_and_unknown_requirement(self):
        self.write("docs/rules.md", "## PAY-REQ-001 — Refund\n\nOnly text.\n\n## Another section\n\n" +
                   block(scenario(tags="@PAY-REQ-999")))
        report = self.report()
        self.assertEqual(report["status"], "needs_scenarios")
        self.assertLessEqual({"requirement_uncovered", "requirement_unknown"}, self.kinds(report))

    def test_default_ids_are_unique_within_a_document(self):
        self.write("docs/rules.md", block(scenario("Repeated"), scenario("Repeated")))
        ids = [item["id"] for item in self.scenarios(self.report())]
        self.assertEqual(ids, ["docs/rules.md::Repeated", "docs/rules.md::Repeated#2"])

    def test_explicit_scenario_ids_must_be_unique_and_single(self):
        self.write("docs/rules.md", block(scenario("A", tags="@PAY-SCN-1")))
        self.write("docs/other.md", block(scenario("B", tags="@PAY-SCN-1"), scenario("C", tags="@X-SCN-1 @X-SCN-2")))
        kinds = self.kinds(self.report())
        self.assertIn("scenario_id_duplicate", kinds)
        self.assertIn("scenario_id_invalid", kinds)

    def test_rule_and_outline_are_supported(self):
        outline = ("\n  Rule: Discounts\n\n    Scenario Outline: Total\n      Given a total of <value>\n\n"
                   "      Examples:\n        | value |\n        | 10    |\n        | 20    |\n")
        self.write("docs/rules.md", "## REQ-9 — Total\n\n" + block(outline))
        report = self.report()
        self.assertEqual(report["status"], "ready", report["findings"])
        ids = [item["id"] for item in self.scenarios(report)]
        self.assertEqual(ids, ["docs/rules.md::Total:row:1:1", "docs/rules.md::Total:row:1:2"])
        self.assertEqual({tuple(item["requirements"]) for item in self.scenarios(report)}, {("REQ-9",)})

    def test_invalid_gherkin_and_empty_scenarios_are_reported(self):
        self.write("docs/a.md", "```gherkin\nthis is not gherkin\n```\n")
        self.write("docs/b.md", block(scenario(steps="")))
        kinds = self.kinds(self.report())
        self.assertIn("gherkin_invalid", kinds)
        self.assertIn("scenario_steps_missing", kinds)

    def test_gherkin_language_comes_from_configuration(self):
        self.write("specmd.toml", 'gherkin_language = "pt"\n')
        self.write("docs/rules.md", block("\n  Cenário: Somar\n    Dado um passo\n", header="Funcionalidade: Regras\n"))
        self.assertEqual(self.report()["status"], "ready", self.report()["findings"])

    def test_spec_fingerprint_ignores_prose_but_not_scenarios(self):
        self.write("docs/rules.md", "# Rules\n\nText.\n\n" + block(scenario()))
        before = self.report()["spec_fp"]
        self.write("docs/rules.md", "# Rules\n\nOther text.\n\n" + block(scenario()))
        self.assertEqual(self.report()["spec_fp"], before)
        self.write("docs/rules.md", "# Rules\n\nOther text.\n\n" + block(scenario("Other name")))
        self.assertNotEqual(self.report()["spec_fp"], before)

    def test_manifest_tracks_documents_configuration_and_ignore_file(self):
        self.write("docs/rules.md", block(scenario()))
        first = self.report()
        self.assertEqual([item["path"] for item in first["manifest"]["documents"]], ["docs/rules.md"])
        self.write(".specmdignore", "README.md\n")
        self.assertNotEqual(self.report()["manifest_sha256"], first["manifest_sha256"])

    def test_symlinked_and_invalid_documents_are_reported(self):
        outside = self.root.parent / f"{self.root.name}-outside.md"
        outside.write_text("# Outside\n")
        self.addCleanup(outside.unlink)
        os.symlink(outside, self.root / "link.md")
        self.write("docs/bin.md", b"\xff\xfe")
        kinds = self.kinds(self.report())
        self.assertIn("symlink", kinds)
        self.assertIn("invalid_utf8", kinds)

    def test_extract_features_keeps_lines_and_rejects_changed_documents(self):
        self.write("docs/rules.md", "# Rules\n\n" + block(scenario()))
        report = self.report()
        features = extract_features(self.root, report)
        self.assertEqual((features[0]["block"], features[0]["line"]), (1, 4))
        self.assertTrue(features[0]["content"].startswith("\n" * 3))
        self.assertFalse(list(self.root.rglob("*.feature")))
        self.write("docs/rules.md", "# Changed\n\n" + block(scenario()))
        with self.assertRaises(ValueError):
            extract_features(self.root, report)


class InspectionCacheTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-cache-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.document = self.root / "docs/rules.md"
        self.document.parent.mkdir()
        self.document.write_text(block(scenario("Add")), encoding="utf-8")
        self.cache = self.root / ".specmd/local" / core.CACHE_FILE

    def analysed(self):
        with mock.patch.object(core, "_inspect_document", wraps=core._inspect_document) as spy:
            report = inspect_project(self.root)
        return report, [call.args[1] for call in spy.call_args_list]

    def test_unchanged_documents_are_not_parsed_again(self):
        self.assertEqual(self.analysed()[1], ["docs/rules.md"])
        report, parsed = self.analysed()
        self.assertEqual(parsed, [])
        self.assertEqual([item["name"] for item in report["documents"][0]["scenarios"]], ["Add"])

    def test_settled_documents_are_not_even_read(self):
        inspect_project(self.root)
        with mock.patch.object(core, "_SETTLE_NS", -10**12), \
                mock.patch.object(core, "_read_regular_file", side_effect=AssertionError("read")):
            self.assertEqual(inspect_project(self.root)["status"], "ready")

    def test_same_size_rewrite_with_the_old_timestamp_is_analysed_again(self):
        inspect_project(self.root)
        info = self.document.stat()
        self.document.write_text(block(scenario("Added")), encoding="utf-8")
        os.utime(self.document, ns=(info.st_atime_ns, info.st_mtime_ns))
        report, parsed = self.analysed()
        self.assertEqual(parsed, ["docs/rules.md"])
        self.assertEqual(report["documents"][0]["scenarios"][0]["name"], "Added")

    def test_language_change_discards_the_cache(self):
        inspect_project(self.root)
        (self.root / "specmd.toml").write_text('gherkin_language = "pt"\n', encoding="utf-8")
        self.assertEqual(self.analysed()[1], ["docs/rules.md"])

    def test_removed_documents_leave_the_cache_and_corrupt_cache_is_ignored(self):
        (self.root / "docs/another.md").write_text(block(scenario("Another")), encoding="utf-8")
        inspect_project(self.root)
        (self.root / "docs/another.md").unlink()
        inspect_project(self.root)
        self.assertEqual(list(json.loads(self.cache.read_text())["entries"]), ["docs/rules.md"])
        self.cache.write_text("{corrupt", encoding="utf-8")
        report, parsed = self.analysed()
        self.assertEqual((report["status"], parsed), ("ready", ["docs/rules.md"]))

    def test_warm_cache_does_not_import_the_gherkin_parser(self):
        inspect_project(self.root)
        repository = Path(__file__).resolve().parents[1]
        code = ("import sys; sys.path[:0] = [sys.argv[1], sys.argv[2]]; from pathlib import Path; "
                "from specmd.core import inspect_project; inspect_project(Path(sys.argv[3])); "
                "print('behave' in sys.modules)")
        completed = subprocess.run([sys.executable, "-c", code, str(repository / "src"), str(repository / "vendor"),
                                    str(self.root)], capture_output=True, text=True, check=True)
        self.assertEqual(completed.stdout.strip(), "False")

    def test_unwritable_cache_does_not_break_the_inspection(self):
        (self.root / ".specmd").mkdir()
        outside = self.root.parent / (self.root.name + "-outside")
        outside.mkdir()
        self.addCleanup(outside.rmdir)
        os.symlink(outside, self.root / ".specmd/local")
        self.assertEqual(inspect_project(self.root)["status"], "ready")
        self.assertEqual(list(outside.iterdir()), [])


class IgnorePatternTests(unittest.TestCase):
    def check(self, patterns, path):
        return is_ignored(path, compile_ignore(patterns))

    def test_gitignore_style_patterns(self):
        self.assertTrue(self.check(["README.md"], "README.md"))
        self.assertTrue(self.check(["README.md"], "sub/README.md"))
        self.assertFalse(self.check(["/README.md"], "sub/README.md"))
        self.assertTrue(self.check(["docs/internal/"], "docs/internal/a.md"))
        self.assertFalse(self.check(["docs/internal/"], "docs/internal.md"))
        self.assertTrue(self.check(["*.draft.md"], "docs/x.draft.md"))
        self.assertTrue(self.check(["docs/**/notes.md"], "docs/a/b/notes.md"))
        self.assertTrue(self.check(["LICENSE*"], "LICENSE.md"))
        self.assertFalse(self.check(["docs/", "!docs/keep.md"], "docs/keep.md"))
        self.assertTrue(self.check(["docs/", "!docs/keep.md"], "docs/other.md"))
        self.assertFalse(self.check(["# comment", ""], "README.md"))


if __name__ == "__main__":
    unittest.main()
