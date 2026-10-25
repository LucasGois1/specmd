#!/usr/bin/env python3
"""Measure SpecMD's hook latency on a large synthetic repository.

The repository is generated once (Markdown documents with scenarios plus many
code files, committed to Git) and reused while its parameters do not change.
Each measurement starts the real hook entry point, as Claude Code does.

    python scripts/benchmark.py [--docs 5000] [--files 50000] [--repeat 5]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

PLUGIN = Path(__file__).resolve().parents[1]
HOOK = PLUGIN / "scripts" / "specmd_hook.py"
DOCUMENT = """# Área {area}, regra {index}

Texto explicativo da regra {index}, como numa documentação real.

## BEN-REQ-{index:05d} — Regra {index}

```gherkin
# language: pt
Funcionalidade: Regra {index}

  Cenário: Caso principal {index}
    Dado um valor {index}
    Quando a regra é aplicada
    Então o resultado é {index}

  Cenário: Caso alternativo {index}
    Dado um valor {index}
    Quando a regra é aplicada duas vezes
    Então o resultado é {index}
```
"""


def generate(root: Path, docs: int, files: int) -> None:
    marker = root / ".bench.json"
    wanted = {"docs": docs, "files": files, "version": 1}
    if marker.is_file() and json.loads(marker.read_text()) == wanted:
        return
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for index in range(docs):
        area = index % 50
        path = root / "docs" / f"area-{area:02d}" / f"regra-{index:05d}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DOCUMENT.format(area=area, index=index), encoding="utf-8")
    for index in range(files):
        path = root / "src" / f"pkg{index % 200:03d}" / f"mod{index:05d}.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"VALUE = {index}\n\n\ndef value():\n    return VALUE\n", encoding="utf-8")
    (root / "specmd.toml").write_text("[run]\non_stop = true\n", encoding="utf-8")
    (root / ".gitignore").write_text(".specmd/\n", encoding="utf-8")
    git = ["git", "-C", str(root), "-c", "user.name=bench", "-c", "user.email=bench@example.com"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "bench"], check=True)
    marker.write_text(json.dumps(wanted), encoding="utf-8")


def hook(root: Path, payload: dict) -> float:
    environment = {**os.environ, "CLAUDE_PROJECT_DIR": str(root), "SPECMD_PYTHON": sys.executable}
    start = time.perf_counter()
    completed = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), cwd=root,
                               env=environment, capture_output=True, text=True, timeout=300)
    elapsed = time.perf_counter() - start
    reply = json.loads(completed.stdout or "{}")
    if "SpecMD: verificação indisponível" in json.dumps(reply, ensure_ascii=False):
        raise RuntimeError(reply)
    return elapsed


def measure(label: str, action, repeat: int, prepare=None) -> dict:
    samples = []
    for _ in range(repeat):
        if prepare:
            prepare()
        samples.append(action())
    row = {"event": label, "p50_ms": round(statistics.median(samples) * 1000),
           "max_ms": round(max(samples) * 1000)}
    print(f"{label:<34} p50 {row['p50_ms']:>6} ms   max {row['max_ms']:>6} ms", flush=True)
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docs", type=int, default=5000)
    parser.add_argument("--files", type=int, default=50000)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--root", type=Path, default=Path(tempfile.gettempdir()) / "specmd-bench")
    parser.add_argument("--json", type=Path, help="grava as medições neste arquivo")
    args = parser.parse_args()
    root = args.root.resolve()
    start = time.perf_counter()
    generate(root, args.docs, args.files)
    print(f"Repositório: {root} ({args.docs} documentos, {args.files} arquivos; "
          f"preparado em {time.perf_counter() - start:.1f} s)", flush=True)
    shutil.rmtree(root / ".specmd", ignore_errors=True)

    document = root / "docs" / "area-00" / "regra-00000.md"
    original = document.read_text(encoding="utf-8")
    counter = iter(range(10**6))

    def edit_document() -> None:
        document.write_text(original + f"\nNota {next(counter)}.\n", encoding="utf-8")

    rows = [measure("SessionStart (estado vazio)", lambda: hook(root, {"hook_event_name": "SessionStart"}), 1,
                    prepare=lambda: shutil.rmtree(root / ".specmd", ignore_errors=True))]
    rows.append(measure("SessionStart", lambda: hook(root, {"hook_event_name": "SessionStart"}), args.repeat))
    rows.append(measure("UserPromptSubmit", lambda: hook(root, {"hook_event_name": "UserPromptSubmit"}), args.repeat))
    rows.append(measure("PostToolUse (Edit em código)", lambda: hook(
        root, {"hook_event_name": "PostToolUse", "tool_name": "Edit",
               "tool_input": {"file_path": str(root / "src/pkg000/mod00000.py")}}), args.repeat))
    rows.append(measure("PostToolUse (Bash)", lambda: hook(
        root, {"hook_event_name": "PostToolUse", "tool_name": "Bash"}), args.repeat))
    rows.append(measure("PostToolUse (documento editado)", lambda: hook(
        root, {"hook_event_name": "PostToolUse", "tool_name": "Edit",
               "tool_input": {"file_path": str(document)}}), args.repeat, prepare=edit_document))
    rows.append(measure("Stop (sem mudança de código)", lambda: hook(root, {"hook_event_name": "Stop"}), args.repeat))
    document.write_text(original, encoding="utf-8")
    if args.json:
        args.json.write_text(json.dumps({"docs": args.docs, "files": args.files, "rows": rows}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
