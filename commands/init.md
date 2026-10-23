---
description: Prepara este repositório para o SpecMD (specmd.toml, .specmdignore e o plugin no .claude/settings.json)
---

Prepare este repositório para o SpecMD. Na raiz do projeto, execute:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/specmd_cli.py" init --root "$(pwd)"
```

Depois:

1. Mostre ao dev quais arquivos foram criados ou alterados.
2. Liste os Markdown do projeto e revise o `.specmdignore` com o dev: documentos que não descrevem comportamento do sistema ficam nele; os que descrevem precisam de cenários Gherkin.
3. Se o projeto tem passos BDD (por exemplo `tests/steps` ou `features/steps`), ajuste o runner no `specmd.toml`; para Java ou Go, aponte o `command` do bridge.
4. Lembre o dev de fazer commit de `specmd.toml`, `.specmdignore` e `.claude/settings.json`: assim o plugin carrega sozinho para quem abrir o Claude Code no repositório e confiar na pasta.
