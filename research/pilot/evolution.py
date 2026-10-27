#!/usr/bin/env python3
"""Fourth pilot round: a project that evolves over five requests, with a reactive developer.

Each run starts from the same shop project (documented rules with scenarios
and one legacy divergence) and plays five requests, each in a new agent
session. A simulated developer (an LLM with the hidden rules) answers only
what the agent asks. After each request the hidden checks of that stage run
on the code; at the end, SpecMD runs the documentation and mutants of the
final code measure how much the documented scenarios protect the rules. See
README.md for the design and the goals registered before measuring.

    python research/pilot/evolution.py --reps 5 --workers 3 [--arms comum,plugin,instrucoes]
"""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile
import threading
import time
import uuid

from run_pilot import ARMS, BUNDLE, HERE, INSTRUCTIONS, MODELS, PYTHON, REPO, clean_copy, hook_stats, run, scenarios, specmd

DEVELOPER_MODEL = "claude-sonnet-5-5"
MAX_TURNS = 4
MAX_MUTANTS = 40
TIMEOUT = 1800

STEPS_FILE = '''from behave import given, then, when

from app import Cart, loyalty_points


@given("an empty cart")
def empty_cart(context):
    context.cart = Cart()


@when("I add items of {first:d} and {second:d} cents")
def add_items(context, first, second):
    context.cart.add(first)
    context.cart.add(second)


@then("the subtotal should be {expected:d} cents")
def check_subtotal(context, expected):
    assert context.cart.subtotal() == expected, f"Observed subtotal {context.cart.subtotal()}; expected {expected}"


@then("the total should be {expected:d} cents")
def check_total(context, expected):
    assert context.cart.total() == expected, f"Observed total {context.cart.total()}; expected {expected}"


@then("the shipping should be {expected:d} cents")
def check_shipping(context, expected):
    assert context.cart.shipping() == expected, f"Observed shipping {context.cart.shipping()}; expected {expected}"


@then("the loyalty points should be {expected:d}")
def check_points(context, expected):
    points = loyalty_points(context.cart)
    assert points == expected, f"Observed points {points}; expected {expected}"
'''

SHOP = {
    "app.py": '''"""Shop cart. Prices are in cents."""

LOYALTY_MINIMUM = 5000


class Cart:
    def __init__(self):
        self.prices = []

    def add(self, price_cents):
        self.prices.append(price_cents)

    def subtotal(self):
        return sum(self.prices)

    def total(self):
        subtotal = self.subtotal()
        if subtotal > 1000:
            return subtotal - subtotal // 10
        return subtotal

    def shipping(self):
        if not self.prices:
            return 0
        return 0 if self.total() > 10000 else 500


def loyalty_points(cart):
    total = cart.total()
    if total >= LOYALTY_MINIMUM:
        return total // 100
    return 0
''',
    "docs/cart.md": '''# Cart

Prices are in cents.

## CART-REQ-001 — Add up items

The cart subtotal is the sum of the item prices.

```gherkin
Feature: Cart subtotal

  Scenario: Add two items
    Given an empty cart
    When I add items of 200 and 300 cents
    Then the subtotal should be 500 cents
    And the total should be 500 cents
```

## CART-REQ-002 — Empty cart

An empty cart has a total of zero and pays no shipping.

```gherkin
Feature: Empty cart

  Scenario: Check an empty cart
    Given an empty cart
    Then the total should be 0 cents
    And the shipping should be 0 cents
```
''',
    "docs/discount.md": '''# Discount

## DISC-REQ-001 — 10% above 1000 cents

Carts whose subtotal is above 1000 cents get a 10% discount on the total; a subtotal of exactly 1000 cents gets no discount. The discount is rounded down to whole cents.

```gherkin
Feature: Discount

  Scenario: Discount above 1000 cents
    Given an empty cart
    When I add items of 600 and 500 cents
    Then the total should be 990 cents

  Scenario: No discount at the limit
    Given an empty cart
    When I add items of 500 and 500 cents
    Then the total should be 1000 cents

  Scenario: Discount rounded down
    Given an empty cart
    When I add items of 500 and 505 cents
    Then the total should be 905 cents
```
''',
    "docs/shipping.md": '''# Shipping

## SHIP-REQ-001 — Shipping fee

Shipping costs 500 cents. It is free when the total after the discount is above 10000 cents; a total of exactly 10000 cents pays shipping. An empty cart pays no shipping.

```gherkin
Feature: Shipping

  Scenario: Shipping below the limit
    Given an empty cart
    When I add items of 3000 and 2000 cents
    Then the shipping should be 500 cents

  Scenario: Exactly 10000 cents pays shipping
    Given an empty cart
    When I add items of 5555 and 5556 cents
    Then the total should be 10000 cents
    And the shipping should be 500 cents

  Scenario: Free shipping above the limit
    Given an empty cart
    When I add items of 6000 and 6000 cents
    Then the total should be 10800 cents
    And the shipping should be 0 cents
```
''',
    "docs/loyalty.md": '''# Loyalty

## LOY-REQ-001 — Loyalty points

A cart whose total after the discount is above 5000 cents earns 1 point per full 100 cents of that total. A total of exactly 5000 cents earns no points.

```gherkin
Feature: Loyalty points

  Scenario: Points above the limit
    Given an empty cart
    When I add items of 3000 and 3000 cents
    Then the total should be 5400 cents
    And the loyalty points should be 54

  Scenario: No points at the limit
    Given an empty cart
    When I add items of 2555 and 3000 cents
    Then the total should be 5000 cents
    And the loyalty points should be 0
```
''',
    "tests/steps/shop_steps.py": STEPS_FILE,
    "specmd.toml": "[run]\non_stop = true\n",
    ".gitignore": ".specmd/local/\n__pycache__/\n",
}

STEPS = [
    {"id": "S1", "request": "Add a service fee of 100 cents to the cart total (Cart.total()) whenever the cart has items."},
    {"id": "S2", "request": "From now on, the 10% discount should apply to carts of 1000 cents or more."},
    {"id": "S3", "request": "Validate the item prices when they are added to the cart."},
    {"id": "S4", "request": "Add a method Cart.summary() that returns a dict with the keys total, shipping and points, "
                            "so the checkout page can show them."},
    {"id": "S5", "request": "Free shipping should now start above 8000 cents instead of 10000."},
]


def rules(stage):
    """The behavior the developer wants after request `stage`, as the simulated developer knows it."""
    threshold = "1000 cents or more" if stage >= 2 else "above 1000 cents (exactly 1000 gets no discount)"
    limit = 8000 if stage >= 5 else 10000
    fee = " The service fee does not count." if stage >= 1 else ""
    lines = [
        "- The cart subtotal is the sum of the item prices, in cents.",
        f"- Discount: 10% when the item subtotal is {threshold}; the fee is not part of that subtotal. "
        "The discount is rounded down to whole cents.",
        f"- Shipping: 500 cents; free when the item total after the discount is above {limit} cents; exactly {limit} "
        f"cents pays shipping; an empty cart pays no shipping.{fee}",
        "- Loyalty points: 1 point per full 100 cents of the item total after the discount, only when that total is "
        f"above 5000 cents; exactly 5000 cents earns no points.{fee}",
        "- Where the code and the documentation disagree on the loyalty points, the documentation is right.",
    ]
    if stage >= 1:
        lines.insert(2, "- Service fee: 100 cents added to Cart.total() after the discount, only when the cart has items; "
                        "an empty cart's total stays 0.")
    if stage >= 3:
        lines.append("- Prices: only negative prices are invalid and must raise ValueError; zero is valid (free gifts); "
                     "there is no maximum; prices are always whole cents, there is no need to check their type.")
    if stage >= 4:
        lines.append("- Cart.summary() returns a dict with total, shipping and points, as the rules above define them.")
    return "\n".join(lines)


DEVELOPER = """You play a software developer who asked a coding agent to change your repository. You only see the \
agent's messages, never the code. You know exactly how the system must behave: the rules you receive. The agent \
does not know them unless it asks.

1. Answer only what the agent explicitly asks. Never volunteer a rule, a value or a detail the agent did not ask \
about, even if you suspect it is getting something wrong.
2. When you answer, use the rules with their exact numbers. Do not add facts.
3. If the agent shows scenarios, examples or a plan and asks you to confirm, check them against the rules: confirm \
what agrees, and for what disagrees say only what is wrong and the correct value. Set corrected to true when you do.
4. If the agent asks something the rules do not cover, say you have no preference and it can choose.
5. If the agent asks permission to proceed, give it, after correcting anything wrong in what it showed you.
6. If the agent says the work is done and asks nothing, set done to true and reply with a short thanks.
7. Keep replies short and plain, in English. Set done to false whenever the agent asked something or is waiting \
for you."""
DEVELOPER_SCHEMA = json.dumps({"type": "object", "required": ["done", "corrected", "reply"], "properties": {
    "done": {"type": "boolean"}, "corrected": {"type": "boolean"}, "reply": {"type": "string"}}})

# Requests that change what a hidden check expects; a failure right after one of them is not a regression.
CHANGES = {"add up items": {1}, "discount above the threshold": {1}, "no discount below the threshold": {1, 2},
           "discount rounded down": {1}, "exactly the limit pays shipping": {5}, "free shipping above the limit": {5},
           "fee does not count for free shipping": {5}, "total with the fee near the shipping limit": {5}}

_lock = threading.Lock()


def regressions(stages):
    """Checks that passed and then failed after a request that did not change their rule.

    Returns the regressions introduced (request, check) and those still failing at the end.
    """
    last = max(stages)
    introduced, left = [], set()
    for stage in range(1, last + 1):
        for name, ok in stages[stage].items():
            if not ok and stages[stage - 1].get(name) is True and stage not in CHANGES.get(name, ()):
                introduced.append([stage, name])
                if all(stages[later].get(name) is False for later in range(stage, last + 1)):
                    left.add(name)
    return introduced, sorted(left)


def build_shop(destination, instructions):
    for relative, content in SHOP.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    if instructions:
        for name in ("CLAUDE.md", "AGENTS.md"):
            (destination / name).write_text(INSTRUCTIONS, encoding="utf-8")
    commit(destination, "base")


def commit(project, message):
    for command in (["git", "init", "-q"], ["git", "add", "-A"],
                    ["git", "-c", "user.name=pilot", "-c", "user.email=pilot@example.com", "commit", "-qm", message,
                     "--allow-empty"]):
        if command[1] != "init" or not (project / ".git").exists():
            run(command, project, check=True)


def code_files(project):
    """Application code: Python outside the tests, the steps and generated folders."""
    skipped = {".git", ".specmd", "__pycache__", "tests", "features", ".venv", "venv"}
    return sorted(path for path in project.rglob("*.py")
                  if not skipped & set(path.relative_to(project).parts) and not path.name.endswith("_steps.py")
                  and path.name != "environment.py")


def code_digest(project):
    digest = hashlib.sha256()
    for path in code_files(project):
        digest.update(path.relative_to(project).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def agent_turn(project, prompt, session, first, arm, log):
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
    return {"seconds": round(time.time() - started), "exit": completed.returncode, "cost_usd": reply.get("total_cost_usd"),
            "tokens_in": sum(usage.get(key) or 0 for key in ("input_tokens", "cache_creation_input_tokens",
                                                             "cache_read_input_tokens")),
            "tokens_out": usage.get("output_tokens"), "text": str(reply.get("result") or "")}


def developer_reply(stage, request, message):
    prompt = (f"Your rules:\n{rules(stage)}\n\nYou asked the agent: {request}\n\n"
              f"The agent's latest message:\n<<<\n{message}\n>>>")
    with tempfile.TemporaryDirectory(prefix="specmd-pilot-dev-") as directory:
        completed = run(["claude", "-p", prompt, "--model", DEVELOPER_MODEL, "--system-prompt", DEVELOPER, "--tools", "",
                         "--setting-sources", "project,local", "--strict-mcp-config", "--output-format", "json",
                         "--json-schema", DEVELOPER_SCHEMA, "--no-session-persistence"],
                        directory, stdin=subprocess.DEVNULL, timeout=300)
    try:
        reply = json.loads(completed.stdout)
        answer = reply.get("structured_output") or json.loads(reply.get("result") or "{}")
    except ValueError:
        reply, answer = {}, {}
    return {"done": bool(answer.get("done")), "corrected": bool(answer.get("corrected")),
            "reply": str(answer.get("reply") or "Please go ahead."), "cost_usd": reply.get("total_cost_usd")}


def hidden_checks(stage, project):
    completed = run([PYTHON, "-I", str(HERE / "evolution_checks.py"), str(stage), str(project)], project, timeout=120)
    try:
        return dict(json.loads(completed.stdout.splitlines()[-1])["checks"])
    except (ValueError, IndexError, KeyError):
        return {"checks did not run": False}


def documentation_run(project):
    copy = clean_copy(project)
    try:
        inspection = specmd("inventory", root=copy)
        executed = specmd("run", root=copy)
    finally:
        shutil.rmtree(copy.parent, ignore_errors=True)
    run_info = executed.get("run") or {}
    return {"status": executed.get("status"), "scenarios": len(scenarios(inspection)),
            "failures": len(run_info.get("failures", []))}


SWAPS = {ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Lt: ast.LtE, ast.LtE: ast.Lt}


class _Mutation(ast.NodeTransformer):
    """Applies the `target`-th boundary or constant mutation of a module."""

    def __init__(self, target):
        self.target, self.index, self.description = target, -1, None

    def _hit(self):
        self.index += 1
        return self.index == self.target

    def visit_Compare(self, node):
        self.generic_visit(node)
        operators = []
        for operator in node.ops:
            if type(operator) in SWAPS and self._hit():
                self.description = f"{node.lineno}: {type(operator).__name__} -> {SWAPS[type(operator)].__name__}"
                operator = SWAPS[type(operator)]()
            operators.append(operator)
        node.ops = operators
        return node

    def visit_Constant(self, node):
        if type(node.value) is int and node.value >= 2 and self._hit():
            self.description = f"{node.lineno}: {node.value} -> {node.value + 1}"
            return ast.copy_location(ast.Constant(node.value + 1), node)
        return node


def mutants(source):
    target = 0
    while True:
        mutation = _Mutation(target)
        tree = mutation.visit(ast.parse(source))
        if mutation.description is None:
            return
        yield mutation.description, ast.unparse(tree)
        target += 1


def mutation_score(project, stage):
    """Mutants of the final code that change the intended behavior, and how many the documentation catches."""
    copy = clean_copy(project)
    try:
        base_checks = hidden_checks(stage, copy)
        base_run = specmd("run", root=copy)
        base_failures = len((base_run.get("run") or {}).get("failures", []))
        relevant = killed = 0
        survivors = []
        for path in code_files(copy):
            original = path.read_text(encoding="utf-8")
            try:
                variants = list(mutants(original))
            except SyntaxError:
                continue
            for description, variant in variants:
                if relevant >= MAX_MUTANTS:
                    break
                path.write_text(variant, encoding="utf-8")
                try:
                    if hidden_checks(stage, copy) == base_checks:
                        continue
                    relevant += 1
                    executed = specmd("run", root=copy)
                    failures = len((executed.get("run") or {}).get("failures", []))
                    if executed.get("status") == "error" or failures > base_failures:
                        killed += 1
                    else:
                        survivors.append(f"{path.relative_to(copy).as_posix()}:{description}")
                finally:
                    path.write_text(original, encoding="utf-8")
        return {"relevant": relevant, "killed": killed, "score": killed / relevant if relevant else None,
                "survivors": survivors[:10]}
    finally:
        shutil.rmtree(copy.parent, ignore_errors=True)


def one_run(arm, rep, workspace):
    base = workspace / f"{arm}-{rep}"
    project, log = base / "project", base / "hooks.jsonl"
    base.mkdir(parents=True)
    build_shop(project, ARMS[arm]["instructions"])
    stages = {0: hidden_checks(0, project)}
    steps = []
    for stage, step in enumerate(STEPS, start=1):
        session, prompt, turns, developer = str(uuid.uuid4()), step["request"], [], []
        before = code_digest(project)
        coded_turn1 = False
        for index in range(MAX_TURNS):
            turns.append(agent_turn(project, prompt, session, index == 0, arm, log))
            if index == 0:
                coded_turn1 = code_digest(project) != before
            developer.append(developer_reply(stage, step["request"], turns[-1]["text"]))
            if developer[-1]["done"]:
                break
            prompt = developer[-1]["reply"]
        stages[stage] = hidden_checks(stage, project)
        steps.append({"id": step["id"], "coded_turn1": coded_turn1, "turns": len(turns),
                      "capped": not developer[-1]["done"], "corrections": sum(item["corrected"] for item in developer),
                      "checks": stages[stage], "documentation": documentation_run(project),
                      "agent": [{key: value for key, value in turn.items() if key != "text"} | {"text": turn["text"][-2000:]}
                                for turn in turns],
                      "developer": developer})
        commit(project, step["id"])
    final = stages[len(STEPS)]
    introduced, left = regressions(stages)
    turns = [turn for step in steps for turn in step["agent"]]
    return {"arm": arm, "rep": rep, "model": MODELS["claude"], "developer_model": DEVELOPER_MODEL, "project": str(project),
            "stages": {str(stage): checks for stage, checks in stages.items()}, "steps": steps,
            "metrics": {"final_checks": sum(final.values()) / len(final), "final_all": all(final.values()),
                        "regressions_introduced": len(introduced), "regressions_end": len(left),
                        "regressed": introduced, "regressed_end": left,
                        "legacy_fixed": final.get("no loyalty points at exactly 5000", False),
                        "fee_kept_out_of_shipping": final.get("fee does not count for free shipping", False),
                        "fee_kept_out_of_points": final.get("loyalty points above 5000", False),
                        "nothing_invented": final.get("zero price allowed", False) and final.get("no maximum price", False),
                        "documentation_passing": steps[-1]["documentation"]["status"] == "passing",
                        "coded_turn1": sum(step["coded_turn1"] for step in steps) / len(steps),
                        "agent_turns": len(turns), "corrections": sum(step["corrections"] for step in steps),
                        "capped_steps": sum(step["capped"] for step in steps),
                        "tokens": sum((turn.get("tokens_in") or 0) + (turn.get("tokens_out") or 0) for turn in turns),
                        "agent_cost_usd": sum(turn.get("cost_usd") or 0 for turn in turns),
                        "developer_cost_usd": sum(item.get("cost_usd") or 0 for step in steps for item in step["developer"]),
                        "seconds": sum(turn["seconds"] for turn in turns),
                        **{f"mutation_{key}": value for key, value in mutation_score(project, len(STEPS)).items()}},
            "hooks": hook_stats(log), "instructions": ARMS[arm]["instructions"], "plugin": ARMS[arm]["plugin"]}


ARM_ORDER = ["comum", "plugin", "instrucoes"]
ARM_LABELS = {"comum": "Plain repository", "plugin": "Plugin only", "instrucoes": "Instructions only"}
RATES = [("final_all", "All hidden checks pass at the end"), ("legacy_fixed", "Legacy loyalty bug fixed"),
         ("fee_kept_out_of_shipping", "Fee kept out of the free-shipping limit"),
         ("fee_kept_out_of_points", "Fee kept out of the loyalty points"),
         ("nothing_invented", "No invented price rule"), ("documentation_passing", "Documentation executable and true at the end")]
MEANS = [("final_checks", "Hidden checks passing at the end, mean", "{:.0%}"),
         ("regressions_introduced", "Regressions introduced, mean per run", "{:.1f}"),
         ("regressions_end", "Regressions left at the end, mean per run", "{:.1f}"),
         ("mutation_score", "Mutation score of the documented scenarios, mean", "{:.0%}"),
         ("coded_turn1", "Requests coded in the first turn, mean", "{:.0%}"),
         ("agent_turns", "Agent turns per run, mean", "{:.1f}"),
         ("corrections", "Developer corrections per run, mean", "{:.1f}"),
         ("tokens", "Agent tokens per run, median", "{:,.0f}"),
         ("agent_cost_usd", "Agent cost per run, median in US$", "{:.3f}"),
         ("developer_cost_usd", "Simulated developer cost per run, median in US$", "{:.3f}")]


def summarize(rows, destination):
    arms = [arm for arm in ARM_ORDER if any(row["arm"] == arm for row in rows)]
    group = {arm: [row for row in rows if row["arm"] == arm] for arm in arms}
    lines = ["# Evolution round results", "", f"Generated at {datetime.now(timezone.utc).isoformat()} from {len(rows)} runs "
             f"of {len(STEPS)} requests each; agent `{MODELS['claude']}`, simulated developer `{DEVELOPER_MODEL}`. "
             "Design and goals in [README](../../README.md).", "",
             "| Metric | " + " | ".join(ARM_LABELS[arm] for arm in arms) + " |", "| --- |" + " --- |" * len(arms)]
    for key, label in RATES:
        lines.append(f"| {label} | " + " | ".join(
            f"{sum(bool(row['metrics'][key]) for row in group[arm])}/{len(group[arm])}" for arm in arms) + " |")
    for key, label, pattern in MEANS:
        cells = []
        for arm in arms:
            values = [row["metrics"][key] for row in group[arm] if row["metrics"].get(key) is not None]
            middle = statistics.median if "median" in label else statistics.mean
            cells.append(pattern.format(middle(values)) if values else "—")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    hooks = [row["hooks"] for row in rows if row["hooks"].get("events")]
    post = [item["post_tool_p95_ms"] for item in hooks if item.get("post_tool_p95_ms") is not None]
    stop = [item["stop_p95_ms"] for item in hooks if item.get("stop_p95_ms") is not None]
    if post or stop:
        lines += ["", f"Hooks: median of the per-run p95: PostToolUse {statistics.median(post) if post else '—'} ms, "
                      f"Stop {statistics.median(stop) if stop else '—'} ms."]
    lines += ["", "Hidden checks at the end, runs passing per check:", "",
              "| Check | " + " | ".join(ARM_LABELS[arm] for arm in arms) + " |", "| --- |" + " --- |" * len(arms)]
    names = sorted({name for row in rows for name in row["stages"][str(len(STEPS))]})
    for name in names:
        lines.append(f"| {name} | " + " | ".join(
            f"{sum(row['stages'][str(len(STEPS))].get(name) is True for row in group[arm])}/{len(group[arm])}"
            for arm in arms) + " |")
    lines += ["", "Per request: first-turn coding / turns, mean (" + " / ".join(ARM_LABELS[arm] for arm in arms) + "):", "",
              "| Request | First-turn coding | Turns |", "| --- | --- | --- |"]
    for index, step in enumerate(STEPS):
        coded = " / ".join(f"{sum(row['steps'][index]['coded_turn1'] for row in group[arm])}/{len(group[arm])}" for arm in arms)
        turns = " / ".join(f"{statistics.mean(row['steps'][index]['turns'] for row in group[arm]):.1f}" for arm in arms)
        lines.append(f"| {step['id']} | {coded} | {turns} |")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--arms", default="comum,plugin,instrucoes")
    parser.add_argument("--summarize", type=Path, help="rebuild summary.md from an existing runs.jsonl")
    parser.add_argument("--output", type=Path,
                        default=HERE / "results" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-evolution"))
    args = parser.parse_args()
    if args.summarize:
        rows = [json.loads(line) for line in args.summarize.read_text(encoding="utf-8").splitlines() if line.strip()]
        summarize([row for row in rows if "metrics" in row], args.summarize.with_name("summary.md"))
        return
    if not (BUNDLE / "hooks/hooks.json").is_file():
        raise SystemExit("Build the bundle first: python scripts/build_codex_plugin.py")
    args.output.mkdir(parents=True, exist_ok=True)
    record = {"started": datetime.now(timezone.utc).isoformat(), "load_average": os.getloadavg(), "cpus": os.cpu_count(),
              "commit": run(["git", "rev-parse", "HEAD"], REPO).stdout.strip(),
              "claude": run(["claude", "--version"], REPO).stdout.strip(), "arms": args.arms, "reps": args.reps,
              "workers": args.workers, "agent_model": MODELS["claude"], "developer_model": DEVELOPER_MODEL}
    workspace = Path(tempfile.mkdtemp(prefix="specmd-pilot-evolution-"))
    jobs = [(arm, rep) for rep in range(1, args.reps + 1) for arm in args.arms.split(",")]
    rows_path, rows = args.output / "runs.jsonl", []

    def work(job):
        try:
            row = one_run(*job, workspace)
        except Exception as error:  # noqa: BLE001 - one failed run must not stop the round
            row = {"arm": job[0], "rep": job[1], "error": f"{type(error).__name__}: {error}"}
        with _lock:
            rows.append(row)
            with rows_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            summary = row.get("error") or {key: row["metrics"][key] for key in
                                           ("final_checks", "regressions_end", "legacy_fixed", "mutation_score")}
            print(f"[{len(rows)}/{len(jobs)}] {job} -> {summary}", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, jobs))
    record.update(finished=datetime.now(timezone.utc).isoformat(), load_average_end=os.getloadavg())
    (args.output / "environment.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    summarize([row for row in rows if "metrics" in row], args.output / "summary.md")
    print("Results:", args.output, "Projects:", workspace)


if __name__ == "__main__":
    main()
