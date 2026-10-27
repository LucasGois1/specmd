---
description: Habilita o SpecMD para o time neste repositório (marketplace e plugin no .claude/settings.json)
---

Habilite o SpecMD para todo o time neste repositório. Na raiz do projeto, execute:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/specmd_cli.py" init --root "$(pwd)"
```

Isso declara o marketplace do SpecMD e habilita o plugin no `.claude/settings.json` e no `.codex/config.toml` do projeto, sem mexer no resto dos arquivos. Depois:

1. Mostre ao dev o que mudou e lembre de fazer commit do `.claude/settings.json` e do `.codex/config.toml`: quem abrir o Claude Code no repositório e confiar na pasta recebe o plugin; no Codex, quem instalar o plugin (`codex plugin marketplace add LucasGois1/specmd` e `codex plugin add specmd@specmd`) o terá ativo no projeto confiável.
2. Rode `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/specmd_cli.py" check --root "$(pwd)"` e revise com o dev os Markdown sem cenários: os que não descrevem comportamento do sistema vão para um `.specmdignore` na raiz; os que descrevem precisam de cenários Gherkin.
3. Se os passos BDD não estão em `tests/steps`, `features/steps` ou `steps`, crie um `specmd.toml` com o runner; para Java ou Go, aponte o `command` do bridge.
