#!/usr/bin/env python3
"""Comparative pilot (D-028): SpecMD versus a strong control, with small models.

Each run builds a fresh project, plays a two-turn developer script with one
agent (Claude Code with claude-haiku-5-5, or Codex with gpt-6-luna), in one
arm (SpecMD plugin on, or off), then evaluates with hidden checks and with
SpecMD itself as the documentation evaluator. See README.md for the design
and the goals registered before measuring.

    python research/pilot/run_pilot.py --reps 3 --workers 4 [--tasks T1,T2] [--agents claude,codex]
"""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PYTHON = str(REPO / ".venv/bin/python") if (REPO / ".venv/bin/python").exists() else sys.executable
BUNDLE = REPO / "codex-plugin"
CODEX_PLUGIN = "specmd@specmd"
MODELS = {"claude": "claude-haiku-5-5", "codex": "gpt-6-luna"}
CART_APP = "app.py"
TIMEOUT = 1800

INSTRUCTIONS = """# Project instructions

- The documentation in `docs/` is the canonical source of the business rules. Each rule has Gherkin scenarios in ```gherkin blocks in the document itself.
- Every behavior change must be in the documentation, with scenarios.
- Before implementing a new or changed rule, show the scenarios to the developer and ask for confirmation.
- If the code contradicts the documentation, ask the developer which of the two holds.
- The scenario steps live in `tests/steps`.
"""

PAYMENTS = {
    "payments.py": '"""Payment rules."""\n\n\ndef can_refund(days_since_purchase):\n    return days_since_purchase <= 10\n',
    "docs/refunds.md": """# Refunds

## PAY-REQ-001 — Refund deadline

A payment can be refunded within 7 calendar days of the purchase. After that, the refund request is refused.

```gherkin
# language: en
Feature: Refund deadline

  Scenario: Refund on the seventh day
    Given a payment made 7 days ago
    When the customer requests the refund
    Then the refund is approved

  Scenario: Refund on the eighth day
    Given a payment made 8 days ago
    When the customer requests the refund
    Then the refund is refused
```
""",
    "tests/steps/refunds_steps.py": '''from behave import given, then, when

from payments import can_refund


@given("a payment made {days:d} days ago")
def payment(context, days):
    context.days = days


@when("the customer requests the refund")
def ask(context):
    context.approved = can_refund(context.days)


@then("the refund is approved")
def approved(context):
    assert context.approved, f"refund refused after {context.days} days"


@then("the refund is refused")
def refused(context):
    assert not context.approved, f"refund approved after {context.days} days"
''',
    "specmd.toml": "[run]\non_stop = true\n",
    ".gitignore": ".specmd/local/\n__pycache__/\n",
}

TASKS = {
    "T1": {"project": "cart", "app": CART_APP, "terms": [["1000"], ["10%", "discount"]], "new_scenarios": True, "turns": [
        "Add to the cart a 10% discount for totals above 1000 cents.",
        "Answers: 'above 1000' means strictly greater than 1000; the discount is rounded down, in whole cents. "
        "Confirmed, go ahead and implement."]},
    "T2": {"project": "cart", "app": CART_APP, "terms": [["fee"]], "new_scenarios": True, "turns": [
        "Add a fixed fee of 1 cent to the cart total.",
        "Answers: the empty cart still has a total of zero; the fee applies only when there are items. "
        "Confirmed, go ahead and implement."]},
    "T3": {"project": "cart", "app": CART_APP, "terms": [["negative"]], "new_scenarios": True, "turns": [
        "Validate the price when adding items to the cart.",
        "Answers: only negative prices are invalid and must raise ValueError; a zero price is allowed (a free gift); "
        "there is no maximum. Confirmed, go ahead and implement."]},
    "T5": {"project": "cart_discount", "app": CART_APP, "terms": [["500"], ["discount"]], "new_scenarios": True, "turns": [
        "The 10% discount now applies to totals above 500 cents.",
        "Answers: 'above 500' means strictly greater than 500; the rest of the rule stays the same. "
        "Confirmed, go ahead and implement."]},
    "T6": {"project": "cart", "app": CART_APP, "terms": [["shipping"], ["10 items", "ten items", "11"]], "new_scenarios": True,
           "turns": [
        "Add two rules to the cart: the method Cart.shipping() returns 500 cents for totals up to 10000 cents "
        "and 0 above that; and the cart accepts at most 10 items.",
        "Answers: exactly 10000 cents pays shipping; shipping uses the cart total; adding the 11th item raises "
        "ValueError. Confirmed, go ahead and implement."]},
    # "7 calendar days" does not contain "7 days", hence both spellings (the Portuguese "7 dias corridos" did).
    "T4": {"project": "payments", "app": "payments.py", "terms": [["7 days", "7 calendar days"]], "new_scenarios": False,
           "turns": [
        "Implement in payments.py the function request_refund(days_since_purchase), which returns 'approved' or "
        "'refused' according to the refund rule.",
        "Answers: what the documentation says holds, 7 calendar days; fix whatever differs. "
        "Confirmed, go ahead and implement."]},
}
STALE_REFUND_TERMS = ("10 days", "10 calendar days")

ARMS = {
    # Round 1: the same written instructions in both arms.
    "control": {"instructions": True, "plugin": False},
    "specmd": {"instructions": True, "plugin": True},
    # Round 2: a common repository, the plugin alone, and the written instructions alone.
    "comum": {"instructions": False, "plugin": False},
    "plugin": {"instructions": False, "plugin": True},
    "instrucoes": {"instructions": True, "plugin": False},
}
FOLLOW_UP = ("Yes, go ahead: update whatever is needed for the confirmed rule to hold, including existing scenarios "
             "and requirements.")
DISCOUNT_DOC = """
## CART-REQ-003 — Discount

Totals above 1000 cents get a 10% discount, rounded down.

```gherkin
# language: en
Feature: Discount

  Scenario: Discount above 1000 cents
    Given an empty cart
    When I add items of 600 and 500 cents
    Then the total should be 990 cents

  Scenario: No discount at the limit
    Given an empty cart
    When I add items of 500 and 500 cents
    Then the total should be 1000 cents
```
"""
DISCOUNT_CODE = ("        subtotal = sum(self.prices)\n        if subtotal > 1000:\n"
                 "            return subtotal - subtotal // 10\n        return subtotal\n")

_lock = threading.Lock()


def run(command, cwd, **options):
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, **options)


def specmd(*arguments, root):
    environment = {**os.environ, "PYTHONPATH": f"{REPO}/src:{REPO}/vendor"}
    environment.pop("CLAUDE_PROJECT_DIR", None)
    completed = run([PYTHON, "-m", "specmd", *arguments, "--root", str(root)], REPO, env=environment, timeout=600)
    try:
        return json.loads(completed.stdout)
    except ValueError:
        return {"status": "error", "stderr": completed.stderr[-500:]}


def clean_copy(project):
    """A copy without Git and local state, so evaluating never touches the agent's project."""
    copy = Path(tempfile.mkdtemp(prefix="specmd-pilot-eval-")) / "project"
    shutil.copytree(project, copy, ignore=shutil.ignore_patterns(".specmd", "__pycache__", ".git"))
    return copy


def inventory(project):
    copy = clean_copy(project)
    try:
        return specmd("inventory", root=copy)
    finally:
        shutil.rmtree(copy.parent, ignore_errors=True)


def build_project(task, destination, instructions=True):
    if TASKS[task]["project"] in {"cart", "cart_discount"}:
        environment = {**os.environ, "PYTHONPATH": f"{REPO}/src:{REPO}/vendor"}
        run([PYTHON, "-m", "specmd", "demo", "--dest", str(destination)], REPO, env=environment, check=True)
        if TASKS[task]["project"] == "cart_discount":
            with (destination / "docs/cart.md").open("a", encoding="utf-8") as stream:
                stream.write(DISCOUNT_DOC)
            app = destination / "app.py"
            app.write_text(app.read_text(encoding="utf-8").replace("        return sum(self.prices)\n", DISCOUNT_CODE),
                           encoding="utf-8")
    else:
        for relative, content in PAYMENTS.items():
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    if instructions:
        for name in ("CLAUDE.md", "AGENTS.md"):
            (destination / name).write_text(INSTRUCTIONS, encoding="utf-8")
    for command in (["git", "init", "-q"], ["git", "add", "-A"],
                    ["git", "-c", "user.name=pilot", "-c", "user.email=pilot@example.com", "commit", "-qm", "base"]):
        run(command, destination, check=True)


def codex_overrides(with_specmd):
    text = (Path.home() / ".codex/config.toml").read_text(encoding="utf-8")
    arguments = []
    for name in sorted(set(re.findall(r'^\[plugins\."([^"]+)"\]', text, re.M))):
        if name != CODEX_PLUGIN or not with_specmd:
            arguments += ["-c", f"plugins.{name}.enabled=false"]
    for name in sorted(set(re.findall(r"^\[mcp_servers\.([A-Za-z0-9_-]+)\]$", text, re.M))):
        arguments += ["-c", f"mcp_servers.{name}.enabled=false"]
    return arguments


def claude_turn(project, prompt, session, first, arm, log):
    command = ["claude", "-p", prompt, "--model", MODELS["claude"], "--setting-sources", "project,local",
               "--strict-mcp-config", "--permission-mode", "acceptEdits", "--allowedTools", "Bash",
               "--output-format", "json", *(["--session-id", session] if first else ["--resume", session])]
    if ARMS[arm]["plugin"]:
        command += ["--plugin-dir", str(BUNDLE)]
    environment = {key: value for key, value in os.environ.items() if key != "CLAUDE_PROJECT_DIR"}
    environment["SPECMD_HOOK_LOG"] = str(log)
    started = time.time()
    completed = run(command, project, env=environment, stdin=subprocess.DEVNULL, timeout=TIMEOUT)
    reply = next((json.loads(line) for line in reversed(completed.stdout.splitlines()) if line.startswith("{")), {})
    usage = reply.get("usage") or {}
    return session, {"seconds": round(time.time() - started), "exit": completed.returncode,
                     "cost_usd": reply.get("total_cost_usd"),
                     "tokens_in": sum(usage.get(key) or 0 for key in ("input_tokens", "cache_creation_input_tokens",
                                                                      "cache_read_input_tokens")),
                     "tokens_out": usage.get("output_tokens"), "message": str(reply.get("result") or "")[-1500:]}


def codex_turn(project, prompt, thread, arm, log):
    flags = ["--json", "-m", MODELS["codex"], "--skip-git-repo-check", "-c", 'sandbox_mode="workspace-write"',
             *codex_overrides(ARMS[arm]["plugin"])]
    command = ["codex", "exec", *flags, prompt] if thread is None else ["codex", "exec", "resume", *flags, thread, prompt]
    environment = {**os.environ, "SPECMD_HOOK_LOG": str(log)}
    started = time.time()
    completed = run(command, project, env=environment, stdin=subprocess.DEVNULL, timeout=TIMEOUT)
    events = [json.loads(line) for line in completed.stdout.splitlines() if line.startswith("{")]
    thread = thread or next((event.get("thread_id") for event in events if event.get("type") == "thread.started"), None)
    usage = next((event.get("usage") for event in events if event.get("type") == "turn.completed"), None) or {}
    messages = [event["item"].get("text", "") for event in events
                if event.get("type") == "item.completed" and (event.get("item") or {}).get("type") == "agent_message"]
    return thread, {"seconds": round(time.time() - started), "exit": completed.returncode, "cost_usd": None,
                    "tokens_in": usage.get("input_tokens"), "tokens_out": usage.get("output_tokens"),
                    "message": (messages[-1] if messages else completed.stderr)[-1500:]}


def code_ast(project, relative):
    try:
        return ast.dump(ast.parse((project / relative).read_text(encoding="utf-8")))
    except (OSError, SyntaxError) as error:
        return f"<{type(error).__name__}>"


def scenarios(inspection):
    return {item["id"]: item.get("sha256") for document in inspection.get("documents", [])
            for item in document.get("scenarios", [])}


def hidden_checks(task, project):
    completed = run([PYTHON, "-I", str(HERE / "checks.py"), task, str(project)], project, timeout=120)
    try:
        return json.loads(completed.stdout.splitlines()[-1])
    except (ValueError, IndexError):
        return {"passed": False, "checks": [["checks did not run", False]], "stderr": completed.stderr[-500:]}


def documentation(task, project, base_count, base_shas=None):
    """Rule documented with scenarios, and SpecMD (as evaluator) running them on a clean copy.

    The registered criterion needs more scenarios than at the start (T1 to T3). The
    corrected one, used after the run, also accepts updated scenarios: in T2
    the rule is documented by changing "Add two items" from 500 to 501.
    """
    copy = clean_copy(project)
    inspection = specmd("inventory", root=copy)
    count = len(scenarios(inspection))
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in sorted((copy / "docs").rglob("*.md")))
    terms = all(any(term.casefold() in text.casefold() for term in group) for group in TASKS[task]["terms"])
    if task == "T4":
        terms = terms and not any(term in text for term in STALE_REFUND_TERMS)
    grew = count > base_count if TASKS[task]["new_scenarios"] else count >= base_count
    touched = grew if base_shas is None or not TASKS[task]["new_scenarios"] else \
        bool(set(scenarios(inspection).values()) - set(base_shas))
    executed = specmd("run", root=copy)
    run_info = executed.get("run") or {}
    shutil.rmtree(copy.parent, ignore_errors=True)
    passing = executed.get("status") == "passing"
    return {"scenarios": count, "documented": bool(terms and grew), "executable": bool(terms and grew and passing),
            "documented_corrected": bool(terms and touched), "executable_corrected": bool(terms and touched and passing),
            "run_status": executed.get("status"), "failures": len(run_info.get("failures", []))}


def hook_stats(log):
    if not log.exists():
        return {"events": 0}
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]

    def p95(event):
        values = sorted(entry["ms"] for entry in entries if entry["event"] == event)
        return values[min(len(values) - 1, int(len(values) * 0.95))] if values else None

    return {"events": len(entries), "blocks": sum(entry["reply"].get("decision") == "block" for entry in entries),
            "post_tool_p95_ms": p95("PostToolUse"), "stop_p95_ms": p95("Stop")}


def one_run(task, agent, arm, rep, workspace, follow_up=False):
    base = workspace / f"{task}-{agent}-{arm}-{rep}"
    project, log = base / "project", base / "hooks.jsonl"
    base.mkdir(parents=True)
    build_project(task, project, ARMS[arm]["instructions"])
    initial = scenarios(inventory(project))
    app = TASKS[task]["app"]
    base_ast = code_ast(project, app)
    session, turns, after_first, after_second = (str(uuid.uuid4()) if agent == "claude" else None), [], {}, {}
    prompts = TASKS[task]["turns"] + ([FOLLOW_UP] if follow_up else [])
    for index, prompt in enumerate(prompts):
        if agent == "claude":
            session, turn = claude_turn(project, prompt, session, index == 0, arm, log)
        else:
            session, turn = codex_turn(project, prompt, session, arm, log)
        turns.append(turn)
        if index == 0:
            now = scenarios(inventory(project))
            after_first = {"code_changed": code_ast(project, app) != base_ast,
                           "base_scenario_changed": any(now.get(key) != value for key, value in initial.items()),
                           "intent": hidden_checks(task, project)["passed"]}
        if index == 1 and follow_up:
            after_second = {"intent_turn2": hidden_checks(task, project)["passed"],
                            "executable_turn2": documentation(task, project, len(initial), initial.values())["executable_corrected"]}
    checks = hidden_checks(task, project)
    docs = documentation(task, project, len(initial), initial.values())
    row = {"task": task, "agent": agent, "model": MODELS[agent], "arm": arm, "rep": rep, "project": str(project),
           "turns": turns, "metrics": {"implemented_before_confirmation": after_first.get("code_changed"),
                                       "base_scenario_changed_turn1": after_first.get("base_scenario_changed"),
                                       "intent_turn1": after_first.get("intent"), "intent": checks["passed"],
                                       **after_second, **docs}, "checks": checks["checks"], "hooks": hook_stats(log),
           "instructions": ARMS[arm]["instructions"], "plugin": ARMS[arm]["plugin"]}
    return row


def rate(rows, key):
    values = [row["metrics"][key] for row in rows if row["metrics"].get(key) is not None]
    return (sum(bool(value) for value in values) / len(values)) if values else None


def percent(value):
    return "—" if value is None else f"{value * 100:.0f}%"


ARM_ORDER = ["comum", "plugin", "instrucoes", "specmd", "control"]
ARM_LABELS = {"comum": "Common repository", "plugin": "Plugin only", "instrucoes": "Instructions only",
              "specmd": "Instructions + plugin", "control": "Instructions only"}
METRICS = [("implemented_before_confirmation", "Rule before confirmation (lower is better)"),
           ("intent", "Intent met"), ("documented", "Rule documented with scenarios (registered criterion)"),
           ("executable", "Documentation executable and true (registered criterion)"),
           ("documented_corrected", "Rule documented with scenarios (corrected criterion)"),
           ("executable_corrected", "Documentation executable and true (corrected criterion)"),
           ("intent_turn2", "Intent met after turn 2"),
           ("executable_turn2", "Documentation executable after turn 2"),
           ("base_scenario_changed_turn1", "Existing scenario changed before confirmation")]


def _median(rows, measure):
    values = [measure(row) for row in rows]
    return statistics.median(values) if values else None


def _number(value, pattern):
    return "—" if value is None else format(value, pattern)


def _metric_lines(group, arms):
    lines = []
    for key, label in METRICS:
        values = [rate(group[arm], key) for arm in arms]
        if any(value is not None for value in values):
            lines.append(f"| {label} | " + " | ".join(percent(value) for value in values) + " |")
    tokens = [_median(group[arm], lambda row: sum((turn.get("tokens_in") or 0) + (turn.get("tokens_out") or 0)
                                                  for turn in row["turns"])) for arm in arms]
    seconds = [_median(group[arm], lambda row: sum(turn["seconds"] for turn in row["turns"])) for arm in arms]
    costs = [_median(group[arm], lambda row: sum(turn.get("cost_usd") or 0 for turn in row["turns"])) for arm in arms]
    lines.append("| Tokens per session, median | " + " | ".join(_number(value, ",.0f") for value in tokens) + " |")
    lines.append("| Seconds per session, median | " + " | ".join(_number(value, ".0f") for value in seconds) + " |")
    if any(costs):
        lines.append("| Cost per session, median in US$ | " + " | ".join(_number(value, ".4f") for value in costs) + " |")
    return lines


def _hook_lines(group, arms):
    hooks = [row["hooks"] for arm in arms for row in group[arm] if row["hooks"].get("events")]
    post = [value["post_tool_p95_ms"] for value in hooks if value.get("post_tool_p95_ms") is not None]
    stop = [value["stop_p95_ms"] for value in hooks if value.get("stop_p95_ms") is not None]
    if not hooks:
        return []
    return ["", f"Hooks: PostToolUse / Stop p95 in the worst session: {max(post) if post else '—'} / "
                f"{max(stop) if stop else '—'} ms; median of the p95s: {statistics.median(post) if post else '—'} / "
                f"{statistics.median(stop) if stop else '—'} ms."]


def _task_lines(group, arms, tasks):
    lines = ["", "Per task (" + " / ".join(ARM_LABELS[arm] for arm in arms) + "):", "",
             "| Task | Before confirmation | Intent | Executable (corrected) |", "| --- | --- | --- | --- |"]
    for task in tasks:
        cells = [" / ".join(percent(rate([row for row in group[arm] if row["task"] == task], key)) for arm in arms)
                 for key in ("implemented_before_confirmation", "intent", "executable_corrected")]
        lines.append(f"| {task} | " + " | ".join(cells) + " |")
    return lines


def summarize(rows, destination):
    lines = ["# Pilot results", "", f"Generated at {datetime.now(timezone.utc).isoformat()} from "
             f"{len(rows)} sessions. Design and goals in [README](../../README.md).", ""]
    replaced = [row for row in rows if row.get("replaces")]
    if replaced:
        lines += ["Sessions repeated after an infrastructure failure: " + ", ".join(
            f"{row['task']} {row['agent']} {row['arm']} rep {row['rep']} ({row['replaces']})" for row in replaced) + ".", ""]
    arms = [arm for arm in ARM_ORDER if any(row["arm"] == arm for row in rows)]
    tasks = sorted({row["task"] for row in rows})
    for agent in sorted({row["agent"] for row in rows}):
        group = {arm: [row for row in rows if row["agent"] == agent and row["arm"] == arm] for arm in arms}
        lines += [f"## {MODELS[agent]}", "", "| Metric | " + " | ".join(ARM_LABELS[arm] for arm in arms) + " |",
                  "| --- |" + " --- |" * len(arms)]
        lines += _metric_lines(group, arms) + _hook_lines(group, arms) + _task_lines(group, arms, tasks) + [""]
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def reevaluate(path, replacements):
    """Recompute the evaluation of finished projects; optionally swap rows for repeated sessions."""
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    extra = {}
    for replacement in replacements:
        for line in replacement.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            extra[(row["task"], row["agent"], row["arm"])] = row
    bases = {}
    result = []
    for row in rows:
        key = (row["task"], row["agent"], row["arm"])
        if key in extra and row["metrics"].get("intent_turn1") is not None and any(turn["exit"] != 0 and not turn["tokens_in"]
                                                                                 for turn in row["turns"]):
            replacement = extra.pop(key)
            row = {**replacement, "rep": row["rep"], "replaces": "turn without a reply from the host, exit code 1"}
        task = row["task"]
        if task not in bases:
            base = Path(tempfile.mkdtemp(prefix="specmd-pilot-base-")) / "project"
            build_project(task, base)
            bases[task] = scenarios(inventory(base))
        project = Path(row["project"])
        if project.is_dir():
            row["metrics"].update(documentation(task, project, len(bases[task]), bases[task].values()))
        result.append(row)
    output = path.with_name("runs-reevaluated.jsonl")
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in result), encoding="utf-8")
    summarize(result, path.with_name("summary.md"))
    print("Reevaluated:", output)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reevaluate", type=Path, help="reevaluate the projects of an existing runs.jsonl")
    parser.add_argument("--replace", type=Path, action="append", default=[],
                        help="runs.jsonl with sessions repeated after an infrastructure failure")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--tasks", default=",".join(TASKS))
    parser.add_argument("--agents", default="claude,codex")
    parser.add_argument("--arms", default="specmd,control")
    parser.add_argument("--follow-up", action="store_true",
                        help="a third developer turn that answers the pending questions")
    parser.add_argument("--output", type=Path, default=HERE / "results" / datetime.now().strftime("%Y%m%d-%H%M%S"))
    args = parser.parse_args()
    if args.reevaluate:
        reevaluate(args.reevaluate, args.replace)
        return
    if not (BUNDLE / "hooks/hooks.json").is_file():
        raise SystemExit("Build the bundle first: python scripts/build_codex_plugin.py")
    args.output.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="specmd-pilot-"))
    jobs = [(task, agent, arm, rep) for rep in range(1, args.reps + 1) for task in args.tasks.split(",")
            for agent in args.agents.split(",") for arm in args.arms.split(",")]
    rows_path = args.output / "runs.jsonl"
    rows = []

    def work(job):
        try:
            row = one_run(*job, workspace, follow_up=args.follow_up)
        except Exception as error:  # noqa: BLE001 - one failed session must not stop the pilot
            row = {"task": job[0], "agent": job[1], "arm": job[2], "rep": job[3], "error": f"{type(error).__name__}: {error}"}
        with _lock:
            rows.append(row)
            with rows_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"[{len(rows)}/{len(jobs)}] {job} -> " + (row.get("error") or json.dumps(row["metrics"], ensure_ascii=False)),
                  flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, jobs))
    summarize([row for row in rows if "metrics" in row], args.output / "summary.md")
    print("Results:", args.output, "Projects:", workspace)


if __name__ == "__main__":
    main()
