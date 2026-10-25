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
BUNDLE = REPO / "dist/codex-plugin"
CODEX_PLUGIN = "specmd@specmd-local"
MODELS = {"claude": "claude-haiku-5-5", "codex": "gpt-6-luna"}
CART_APP = "app.py"
TIMEOUT = 1800

INSTRUCTIONS = """# Instruções do projeto

- A documentação em `docs/` é a fonte canônica das regras de negócio. Cada regra tem cenários Gherkin em blocos ```gherkin no próprio documento.
- Toda mudança de comportamento precisa estar na documentação, com cenários.
- Antes de implementar uma regra nova ou alterada, mostre os cenários ao dev e peça confirmação.
- Se o código contradiz a documentação, pergunte ao dev qual dos dois vale.
- Os passos dos cenários ficam em `tests/steps`.
"""

PAYMENTS = {
    "pagamentos.py": '"""Regras de pagamentos."""\n\n\ndef pode_estornar(dias_desde_compra):\n    return dias_desde_compra <= 10\n',
    "docs/estornos.md": """# Estornos

## PAG-REQ-001 — Prazo de estorno

Um pagamento pode ser estornado em até 7 dias corridos após a compra. Depois disso, o pedido de estorno é recusado.

```gherkin
# language: pt
Funcionalidade: Prazo de estorno

  Cenário: Estorno no sétimo dia
    Dado um pagamento feito há 7 dias
    Quando o cliente pedir o estorno
    Então o estorno é aprovado

  Cenário: Estorno no oitavo dia
    Dado um pagamento feito há 8 dias
    Quando o cliente pedir o estorno
    Então o estorno é recusado
```
""",
    "tests/steps/estornos_steps.py": '''from behave import given, then, when

from pagamentos import pode_estornar


@given("um pagamento feito há {dias:d} dias")
def payment(context, dias):
    context.dias = dias


@when("o cliente pedir o estorno")
def ask(context):
    context.aprovado = pode_estornar(context.dias)


@then("o estorno é aprovado")
def approved(context):
    assert context.aprovado, f"estorno recusado com {context.dias} dias"


@then("o estorno é recusado")
def refused(context):
    assert not context.aprovado, f"estorno aprovado com {context.dias} dias"
''',
    "specmd.toml": "[run]\non_stop = true\n",
    ".gitignore": ".specmd/local/\n__pycache__/\n",
}

TASKS = {
    "T1": {"project": "cart", "app": CART_APP, "terms": [["1000"], ["10%", "desconto"]], "new_scenarios": True, "turns": [
        "Adicione ao carrinho um desconto de 10% para totais acima de 1000 centavos.",
        "Respostas: 'acima de 1000' é estritamente maior que 1000; o desconto é arredondado para baixo, em centavos "
        "inteiros. Confirmo, pode implementar."]},
    "T2": {"project": "cart", "app": CART_APP, "terms": [["taxa"]], "new_scenarios": True, "turns": [
        "Some uma taxa fixa de 1 centavo ao total do carrinho.",
        "Respostas: o carrinho vazio continua com total zero; a taxa vale só quando há itens. Confirmo, pode implementar."]},
    "T3": {"project": "cart", "app": CART_APP, "terms": [["negativ"]], "new_scenarios": True, "turns": [
        "Valide o preço ao adicionar itens no carrinho.",
        "Respostas: só preços negativos são inválidos e devem levantar ValueError; preço zero é permitido (brinde); "
        "não há limite máximo. Confirmo, pode implementar."]},
    "T4": {"project": "payments", "app": "pagamentos.py", "terms": [["7 dias"]], "new_scenarios": False, "turns": [
        "Implemente em pagamentos.py a função solicitar_estorno(dias_desde_compra), que retorna 'aprovado' ou "
        "'recusado' conforme a regra de estornos.",
        "Respostas: vale o que está na documentação, 7 dias corridos; corrija o que estiver diferente. Confirmo, pode implementar."]},
}

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


def build_project(task, destination):
    if TASKS[task]["project"] == "cart":
        environment = {**os.environ, "PYTHONPATH": f"{REPO}/src:{REPO}/vendor"}
        run([PYTHON, "-m", "specmd", "demo", "--dest", str(destination)], REPO, env=environment, check=True)
    else:
        for relative, content in PAYMENTS.items():
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
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
    if arm == "specmd":
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
             *codex_overrides(arm == "specmd")]
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
        return {"passed": False, "checks": [["checagem não executou", False]], "stderr": completed.stderr[-500:]}


def documentation(task, project, base_count, base_shas=None):
    """Rule documented with scenarios, and SpecMD (as evaluator) running them on a clean copy.

    The registered criterion needs more scenarios than at the start (T1 to T3). The
    corrected one, used after the run, also accepts updated scenarios: in T2
    the rule is documented by changing "Somar dois itens" from 500 to 501.
    """
    copy = clean_copy(project)
    inspection = specmd("inventory", root=copy)
    count = len(scenarios(inspection))
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in sorted((copy / "docs").rglob("*.md")))
    terms = all(any(term.casefold() in text.casefold() for term in group) for group in TASKS[task]["terms"])
    if task == "T4":
        terms = terms and "10 dias" not in text
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


def one_run(task, agent, arm, rep, workspace):
    base = workspace / f"{task}-{agent}-{arm}-{rep}"
    project, log = base / "project", base / "hooks.jsonl"
    base.mkdir(parents=True)
    build_project(task, project)
    initial = scenarios(inventory(project))
    app = TASKS[task]["app"]
    base_ast = code_ast(project, app)
    session, turns, after_first = (str(uuid.uuid4()) if agent == "claude" else None), [], {}
    for index, prompt in enumerate(TASKS[task]["turns"]):
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
    checks = hidden_checks(task, project)
    docs = documentation(task, project, len(initial), initial.values())
    row = {"task": task, "agent": agent, "model": MODELS[agent], "arm": arm, "rep": rep, "project": str(project),
           "turns": turns, "metrics": {"implemented_before_confirmation": after_first.get("code_changed"),
                                       "base_scenario_changed_turn1": after_first.get("base_scenario_changed"),
                                       "intent_turn1": after_first.get("intent"), "intent": checks["passed"],
                                       **docs}, "checks": checks["checks"], "hooks": hook_stats(log)}
    return row


def rate(rows, key):
    values = [row["metrics"][key] for row in rows if row["metrics"].get(key) is not None]
    return (sum(bool(value) for value in values) / len(values)) if values else None


def percent(value):
    return "—" if value is None else f"{value * 100:.0f}%"


ARM_ORDER = ["comum", "plugin", "instrucoes", "specmd", "control"]
ARM_LABELS = {"comum": "Repositório comum", "plugin": "Só o plugin", "instrucoes": "Só instruções",
              "specmd": "Instruções + plugin", "control": "Só instruções"}
METRICS = [("implemented_before_confirmation", "Regra antes da confirmação (menor é melhor)"),
           ("intent", "Intenção atendida"), ("documented", "Regra documentada com cenários (critério registrado)"),
           ("executable", "Documentação executável e verdadeira (critério registrado)"),
           ("documented_corrected", "Regra documentada com cenários (critério corrigido)"),
           ("executable_corrected", "Documentação executável e verdadeira (critério corrigido)"),
           ("intent_turn2", "Intenção atendida após o turno 2"),
           ("executable_turn2", "Documentação executável após o turno 2"),
           ("base_scenario_changed_turn1", "Cenário existente alterado antes da confirmação")]


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
    lines.append("| Tokens por sessão, mediana | " + " | ".join(_number(value, ",.0f") for value in tokens) + " |")
    lines.append("| Segundos por sessão, mediana | " + " | ".join(_number(value, ".0f") for value in seconds) + " |")
    if any(costs):
        lines.append("| Custo por sessão, mediana em US$ | " + " | ".join(_number(value, ".4f") for value in costs) + " |")
    return lines


def _hook_lines(group, arms):
    hooks = [row["hooks"] for arm in arms for row in group[arm] if row["hooks"].get("events")]
    post = [value["post_tool_p95_ms"] for value in hooks if value.get("post_tool_p95_ms") is not None]
    stop = [value["stop_p95_ms"] for value in hooks if value.get("stop_p95_ms") is not None]
    if not hooks:
        return []
    return ["", f"Hooks: p95 do PostToolUse / Stop na pior sessão: {max(post) if post else '—'} / "
                f"{max(stop) if stop else '—'} ms; mediana dos p95: {statistics.median(post) if post else '—'} / "
                f"{statistics.median(stop) if stop else '—'} ms."]


def _task_lines(group, arms, tasks):
    lines = ["", "Por tarefa (" + " / ".join(ARM_LABELS[arm] for arm in arms) + "):", "",
             "| Tarefa | Antes da confirmação | Intenção | Executável (corrigido) |", "| --- | --- | --- | --- |"]
    for task in tasks:
        cells = [" / ".join(percent(rate([row for row in group[arm] if row["task"] == task], key)) for arm in arms)
                 for key in ("implemented_before_confirmation", "intent", "executable_corrected")]
        lines.append(f"| {task} | " + " | ".join(cells) + " |")
    return lines


def summarize(rows, destination):
    lines = ["# Resultados do piloto", "", f"Gerado em {datetime.now(timezone.utc).isoformat()} a partir de "
             f"{len(rows)} sessões. Desenho e metas em [README](../../README.md).", ""]
    replaced = [row for row in rows if row.get("replaces")]
    if replaced:
        lines += ["Sessões repetidas por falha de infraestrutura: " + ", ".join(
            f"{row['task']} {row['agent']} {row['arm']} rep {row['rep']} ({row['replaces']})" for row in replaced) + ".", ""]
    arms = [arm for arm in ARM_ORDER if any(row["arm"] == arm for row in rows)]
    tasks = sorted({row["task"] for row in rows})
    for agent in sorted({row["agent"] for row in rows}):
        group = {arm: [row for row in rows if row["agent"] == agent and row["arm"] == arm] for arm in arms}
        lines += [f"## {MODELS[agent]}", "", "| Métrica | " + " | ".join(ARM_LABELS[arm] for arm in arms) + " |",
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
            row = {**replacement, "rep": row["rep"], "replaces": "turno sem resposta do host, código de saída 1"}
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
    print("Reavaliado:", output)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reevaluate", type=Path, help="reavalia os projetos de um runs.jsonl existente")
    parser.add_argument("--replace", type=Path, action="append", default=[],
                        help="runs.jsonl com sessões repetidas por falha de infraestrutura")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--tasks", default=",".join(TASKS))
    parser.add_argument("--agents", default="claude,codex")
    parser.add_argument("--arms", default="specmd,control")
    parser.add_argument("--output", type=Path, default=HERE / "results" / datetime.now().strftime("%Y%m%d-%H%M%S"))
    args = parser.parse_args()
    if args.reevaluate:
        reevaluate(args.reevaluate, args.replace)
        return
    if not (BUNDLE / "hooks/hooks.json").is_file():
        raise SystemExit("Gere o bundle antes: python scripts/build_codex_plugin.py")
    args.output.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="specmd-pilot-"))
    jobs = [(task, agent, arm, rep) for rep in range(1, args.reps + 1) for task in args.tasks.split(",")
            for agent in args.agents.split(",") for arm in args.arms.split(",")]
    rows_path = args.output / "runs.jsonl"
    rows = []

    def work(job):
        try:
            row = one_run(*job, workspace)
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
    print("Resultados:", args.output, "Projetos:", workspace)


if __name__ == "__main__":
    main()
