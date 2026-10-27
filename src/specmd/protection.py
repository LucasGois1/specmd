"""Changes to confirmed scenarios and rules written in ignored documents.

The scenarios as they were at the developer's last message are the baseline.
Removing one, changing what it expects, marking it work in progress or
removing a requirement is reported to the agent after the edit and to the
developer at the end of the turn; it is information, not a block. Only a
scenario that was failing, whose expected value changed together with the
code, comes back to the agent once.

Ignored documents are read lightly; one that changes and starts declaring
requirements, Gherkin blocks or MDG titles is reported to the agent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import state as local_state
from .messages import text as t

BASELINE_FILE = "prompt-scenarios.json"
_BASELINE_KEYS = ("id", "name", "line", "sha256", "tags", "steps_text")
MAX_LINES = 8


def baseline_of(inspection: dict[str, Any]) -> dict[str, Any]:
    return {"spec_fp": inspection.get("spec_fp"), "documents": {
        document["path"]: {
            "spec_sha256": document.get("spec_sha256"),
            "requirements": document.get("requirements", []),
            "scenarios": [{key: scenario.get(key) for key in _BASELINE_KEYS} for scenario in document.get("scenarios", [])],
        } for document in inspection.get("documents", [])}}


def save_baseline(root: Path, inspection: dict[str, Any], replace: bool = True) -> None:
    """Remember the scenarios the developer has seen; rewritten only when they changed."""
    stored = local_state.read_local(root, BASELINE_FILE)
    if stored and (not replace or stored.get("spec_fp") == inspection.get("spec_fp")):
        return
    local_state.write_local(root, BASELINE_FILE, baseline_of(inspection))


def load_baseline(root: Path) -> dict[str, Any] | None:
    stored = local_state.read_local(root, BASELINE_FILE)
    return stored if isinstance(stored.get("documents"), dict) else None


def _steps(scenario: dict[str, Any], then: bool) -> list[Any]:
    return [step for step in scenario.get("steps_text") or [] if isinstance(step, list) and len(step) == 3
            and (step[0] == "then") == then]


def _difference(old: dict[str, Any], new: dict[str, Any], wip_tags: set[str]) -> dict[str, Any]:
    before_then, after_then = _steps(old, True), _steps(new, True)
    change: dict[str, Any] = {"kind": "changed", "then": None, "context": None, "data": False, "wip": False}
    if [step[1] for step in before_then] != [step[1] for step in after_then]:
        change["then"] = [[step[1] for step in before_then], [step[1] for step in after_then]]
    before_context, after_context = _steps(old, False), _steps(new, False)
    if [step[:2] for step in before_context] != [step[:2] for step in after_context]:
        change["context"] = [[step[1] for step in before_context], [step[1] for step in after_context]]
    change["data"] = [step[2] for step in before_then + before_context] != [step[2] for step in after_then + after_context]
    change["wip"] = not wip_tags & set(old.get("tags") or []) and bool(wip_tags & set(new.get("tags") or []))
    return change


def scenario_changes(baseline: dict[str, Any] | None, inspection: dict[str, Any], wip_tags: set[str],
                     paths: set[str] | None = None) -> list[dict[str, Any]]:
    """Scenarios and requirements of the baseline that were removed or changed."""
    if baseline is None:
        return []
    current_documents = {document["path"]: document for document in inspection.get("documents", [])}
    current = {scenario["id"]: {**scenario, "path": document["path"]}
               for document in inspection.get("documents", []) for scenario in document.get("scenarios", [])}
    requirements = {requirement["id"] for document in inspection.get("documents", [])
                    for requirement in document.get("requirements", [])}
    changes = []
    for path, old_document in sorted(baseline["documents"].items()):
        document = current_documents.get(path)
        unchanged = document is not None and document.get("spec_sha256") == old_document.get("spec_sha256")
        if (paths is None or path in paths) and not unchanged:
            changes.extend(_document_changes(path, old_document, current, requirements, wip_tags))
    return changes


def _document_changes(path: str, old_document: dict[str, Any], current: dict[str, Any], requirements: set[str],
                      wip_tags: set[str]) -> list[dict[str, Any]]:
    changes = []
    for old in old_document.get("scenarios", []):
        new = current.get(old.get("id"))
        base = {"id": old.get("id"), "name": old.get("name"), "path": path, "line": old.get("line")}
        if new is None:
            changes.append({**base, "kind": "removed"})
        elif new.get("sha256") != old.get("sha256"):
            changes.append({**base, "path": new["path"], "line": new.get("line"), **_difference(old, new, wip_tags)})
    changes.extend({"kind": "requirement_removed", "id": requirement.get("id"), "path": path,
                    "line": requirement.get("line")}
                   for requirement in old_document.get("requirements", []) if requirement.get("id") not in requirements)
    return changes


def _steps_text(steps: list[str]) -> str:
    return " / ".join(steps) if steps else t("(none)", "(nenhum)")


def _step_diff(before: list[str], after: list[str]) -> list[str]:
    """Only the steps that changed; whole lists when steps were added or removed."""
    if len(before) != len(after):
        return [f"{_steps_text(before)} → {_steps_text(after)}"]
    return [f"{old} → {new}" for old, new in zip(before, after) if old != new]


def describe(change: dict[str, Any]) -> str:
    location = f"{change['path']}:{change['line']}" if change.get("line") else change["path"]
    if change["kind"] == "requirement_removed":
        return t(f"- requirement {change['id']} ({location}) — removed", f"- requisito {change['id']} ({location}) — removido")
    title = f'- {location} "{change.get("name")}"'
    if change["kind"] == "removed":
        return f"{title} — " + t("removed or renamed", "removido ou renomeado")
    parts = []  # Step texts keep their keyword: "Then the total should be 900 cents".
    for key in ("then", "context"):
        if change.get(key):
            parts.extend(_step_diff(*change[key]))
    if change.get("data") and not parts:
        parts.append(t("a step's table or text changed", "tabela ou texto de um passo alterado"))
    if change.get("wip"):
        parts.append(t("tagged @wip", "marcado @wip"))
    return f"{title} — " + ("; ".join(parts) if parts else t("changed", "alterado"))


def describe_all(changes: list[dict[str, Any]]) -> list[str]:
    lines = [describe(change) for change in changes[:MAX_LINES]]
    if len(changes) > MAX_LINES:
        more = len(changes) - MAX_LINES
        lines.append(t(f"- … and {more} more changes.", f"- … e mais {more} mudanças."))
    return lines


def strong_signals(changes: list[dict[str, Any]], last_run: Any) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Changed expectations of scenarios that were failing in the last run."""
    if not isinstance(last_run, dict):
        return []
    failures = {item.get("id"): item for item in last_run.get("failures", []) if isinstance(item, dict)}
    return [(change, failures[change["id"]]) for change in changes
            if change["kind"] == "changed" and change.get("then") and change["id"] in failures]


def failure_hint(failure: dict[str, Any]) -> str:
    for step in failure.get("steps", []):
        lines = [line.strip() for line in str(step.get("error") or "").splitlines() if line.strip()]
        if lines:
            return lines[-1][:200]
    return str(failure.get("status") or t("failing", "falhava"))


def gained_rules(before: Any, after: dict[str, Any]) -> list[tuple[str, dict[str, Any], list[str]]]:
    """Ignored documents that now declare requirements, Gherkin blocks or MDG titles they did not have."""
    if not isinstance(before, dict):
        return []
    gained = []
    for path, markers in sorted(after.items()):
        old = before.get(path) if isinstance(before.get(path), dict) else {}
        what = sorted(set(markers.get("requirements", [])) - set(old.get("requirements", [])))
        if markers.get("gherkin", 0) > old.get("gherkin", 0):
            what.append(t("a Gherkin block", "um bloco Gherkin"))
        if markers.get("mdg", 0) > old.get("mdg", 0):
            what.append(t("Gherkin headings (MDG)", "títulos Gherkin (MDG)"))
        if what:
            gained.append((path, markers, what))
    return gained


def describe_gained(gained: list[tuple[str, dict[str, Any], list[str]]]) -> list[str]:
    lines = []
    for path, markers, what in gained[:MAX_LINES]:
        declared = ", ".join(what)
        if markers.get("default"):
            where = t("is ignored by default by SpecMD", "é ignorado por padrão pelo SpecMD")
        else:
            where = t("is in .specmdignore", "está no .specmdignore")
        lines.append(t(f"SpecMD: {path} {where}, but now declares {declared}. Move the rule to a behavior document or "
                       f"take the file out of .specmdignore (or use !{path}). When in doubt, ask the developer.",
                       f"SpecMD: {path} {where}, mas agora declara {declared}. Mova a regra para um documento "
                       f"de comportamento ou tire o arquivo do .specmdignore (ou use !{path}). Em dúvida, pergunte ao dev."))
    return lines
