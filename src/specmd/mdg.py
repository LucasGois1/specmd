"""Markdown with Gherkin (MDG, `*.feature.md`) read as classic Gherkin, line for line.

Follows Cucumber's specification (MARKDOWN_WITH_GHERKIN.md): keywords are
Markdown headings, steps are list items, tables are GFM tables indented 2 to 5
spaces, a fenced block right after a step is its doc string, and tags sit in
backticks on the line above a keyword. Any other line is prose and becomes
blank, so every Gherkin line keeps its line number. MDG has no
`# language:` header: the language comes from gherkin_language.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import functools
import re
from typing import Any

HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(\S.*))?$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_TAG_LINE = re.compile(r"^\s*(?:`@[^`\s]+`\s*)+$")
_TAG = re.compile(r"`(@[^`\s]+)`")
_TABLE_ROW = re.compile(r"^ {2,5}(\|.*\|)\s*$")
_SEPARATOR_CELL = re.compile(r"^\s*:?-+:?\s*$")
_LIST_ITEM = re.compile(r"^ {0,3}[*+-][ \t]+(\S.*)$")
_HEADER_KINDS = ("feature", "rule", "background", "scenario", "scenario_outline", "examples")
_STEP_KINDS = ("given", "when", "then", "and", "but")


def heading_title(match: re.Match[str]) -> str:
    """The heading text without an optional closing sequence of #."""
    title = (match.group(2) or "").rstrip()
    stripped = title.rstrip("#")
    return stripped.rstrip() if stripped != title and (not stripped or stripped[-1] in " \t") else title


def is_mdg(path: str) -> bool:
    return path.casefold().endswith(".feature.md")


@functools.lru_cache(maxsize=None)
def _keywords(language: str) -> tuple[dict[str, str], re.Pattern[str], re.Pattern[str]] | None:
    """Header keyword to kind, a header pattern and a step pattern for one language."""
    from behave.i18n import languages

    words = languages.get(language)
    if words is None:
        return None
    kinds = {word.strip(): kind for kind in _HEADER_KINDS for word in words.get(kind, []) if word.strip() != "*"}
    steps = [word for kind in _STEP_KINDS for word in words.get(kind, []) if word.strip() != "*"]
    header = re.compile(r"^(" + "|".join(sorted(map(re.escape, kinds), key=len, reverse=True)) + r")\s*:(.*)$")
    step = re.compile(r"^(?:" + "|".join(sorted(map(re.escape, steps), key=len, reverse=True)) + r")")
    return kinds, header, step


@dataclass
class Converted:
    text: str
    requirements: list[dict[str, Any]] = field(default_factory=list)
    contexts: list[str | None] = field(default_factory=list)
    scenarios: bool = False

    def context_at(self, line: int) -> str | None:
        return self.contexts[line - 1] if 0 < line <= len(self.contexts) else None


class _Converter:
    def __init__(self, language: str, requirement: re.Pattern[str]):
        self.language = language
        self.keywords = _keywords(language) or _keywords("en")
        self.requirement = requirement
        self.output: list[str] = []
        self.result = Converted("")
        self.stack: list[tuple[int, str | None]] = []
        self.fence: tuple[str, bool] | None = None  # closing marker, inside a doc string
        self.after_step = False
        self.feature_line: int | None = None

    def line(self, raw: str) -> str:
        if self.fence is not None:
            return self.in_fence(raw)
        opening = _FENCE.match(raw)
        if opening:
            self.fence = (opening.group(1)[0] * len(opening.group(1)), self.after_step)
            return '"""' if self.after_step else ""
        heading = HEADING.match(raw)
        if heading:
            return self.heading(len(heading.group(1)), heading_title(heading))
        if _TAG_LINE.match(raw):
            self.after_step = False
            return " ".join(_TAG.findall(raw))
        row = _TABLE_ROW.match(raw)
        if row:
            cells = row.group(1).strip("|").split("|")
            return "" if all(_SEPARATOR_CELL.match(cell) for cell in cells) else row.group(1)
        item = _LIST_ITEM.match(raw)
        if item and self.keywords[2].match(item.group(1)):
            self.after_step = True
            return item.group(1).rstrip()
        if raw.strip():
            self.after_step = False
        return ""

    def in_fence(self, raw: str) -> str:
        closing, doc_string = self.fence
        if raw.strip().startswith(closing) and not raw.strip().strip(closing[0]):
            self.fence = None
            self.after_step = False
            return '"""' if doc_string else ""
        return raw if doc_string else ""

    def heading(self, level: int, title: str) -> str:
        self.after_step = False
        self.stack = [item for item in self.stack if item[0] < level]
        kinds, header, _ = self.keywords
        keyword = header.match(title)
        kind = kinds.get(keyword.group(1)) if keyword else None
        named = keyword.group(2).strip() if keyword else title
        match = self.requirement.match(named) if kind in {None, "rule"} else None
        if match:
            self.result.requirements.append({"id": match.group(1), "line": len(self.output) + 1})
        self.stack.append((level, match.group(1) if match else None))
        if kind is None:
            return ""
        if kind == "feature":
            self.feature_line = len(self.output) + 1
        self.result.scenarios |= kind in {"scenario", "scenario_outline"}
        return f"{keyword.group(1)}:{keyword.group(2)}"

    def context(self) -> str | None:
        return next((identifier for _, identifier in reversed(self.stack) if identifier), None)

    def finish(self, lines: list[str]) -> Converted:
        if self.feature_line is None:
            self.name_feature(lines)
        if self.output and not self.output[0] and len(self.output) > 1:
            # Room for the language header that bridges read from the text itself.
            self.output[0] = f"# language: {self.language}"
        self.result.text = "\n".join(self.output) + "\n"
        return self.result

    def name_feature(self, lines: list[str]) -> None:
        """Without a Feature heading, the first line of prose names the feature."""
        for index, raw in enumerate(lines):
            if raw.strip():
                if not self.output[index]:
                    keyword = next(word for word, kind in self.keywords[0].items() if kind == "feature")
                    self.output[index] = f"{keyword}: {raw.strip().lstrip('#').strip()}"
                return


def convert(text: str, language: str | None, requirement: re.Pattern[str]) -> Converted:
    """Classic Gherkin with the same lines, the requirements declared and the requirement at each line."""
    converter = _Converter(language or "en", requirement)
    lines = text.splitlines()
    for raw in lines:
        converter.output.append(converter.line(raw))
        converter.result.contexts.append(converter.context())
    if converter.output and converter.feature_line == 1 and len(converter.output) > 1 and not converter.output[1]:
        # Move the feature title one line down so the first line can hold the language header.
        converter.output[0], converter.output[1] = "", converter.output[0]
        converter.feature_line = 2
    return converter.finish(lines)
