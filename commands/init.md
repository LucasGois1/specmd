---
description: Enables SpecMD for the team in this repository (marketplace and plugin in .claude/settings.json)
---

Enable SpecMD for the whole team in this repository. At the project root, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/specmd_cli.py" init --root "$(pwd)"
```

This declares the SpecMD marketplace and enables the plugin in the project's `.claude/settings.json` and `.codex/config.toml`, without touching the rest of those files. Then:

1. Show the developer what changed and remind them to commit `.claude/settings.json` and `.codex/config.toml`: anyone who opens Claude Code in the repository and trusts the folder gets the plugin; in Codex, anyone who installs the plugin (`codex plugin marketplace add LucasGois1/specmd` and `codex plugin add specmd@specmd`) has it active in the trusted project.
2. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/specmd_cli.py" check --root "$(pwd)"` and review with the developer the Markdown files without scenarios: those that do not describe system behavior go into a `.specmdignore` at the root; those that do need Gherkin scenarios.
3. If the BDD steps are not in `tests/steps`, `features/steps` or `steps`, create a `specmd.toml` with the runner; for Java or Go, point `command` to the bridge.
4. To get SpecMD's messages in Portuguese, add `language = "pt"` to `specmd.toml`.
