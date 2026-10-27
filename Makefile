# Shortcuts to try SpecMD locally with Claude Code.

PYTHON ?= python3
DEMO_HOME ?= $(HOME)/specmd-demo
CLAUDE_ARGS ?=

VENV := $(CURDIR)/.venv
PY := $(VENV)/bin/python
STAMP := $(VENV)/.specmd-installed
BUNDLE := $(CURDIR)/codex-plugin

# Evaluated on every target, to see a freshly created demo.
DEMO_BASE = $(shell cat "$(DEMO_HOME)/.latest" 2>/dev/null)
DEMO = $(DEMO_BASE)/cart
SPECMD_ENV = SPECMD_PYTHON="$(PY)"

.DEFAULT_GOAL := help
.PHONY: help setup bundle test bench demo agent status run init require-demo

help:
	@echo "Usage: make <target>"
	@echo "  setup   Create .venv, install dependencies and build the plugin"
	@echo "  test    Run the local test suite"
	@echo "  bench   Measure hook latency on a large synthetic repository"
	@echo "  demo    Create a new demo project in $(DEMO_HOME)"
	@echo "  agent   Open Claude Code in the demo with the SpecMD plugin"
	@echo "  status  Show the demo's status"
	@echo "  run     Run the demo's scenarios"
	@echo "  init    Enable the plugin for the team: make init REPO=/path/to/repo"

$(STAMP): pyproject.toml
	$(PYTHON) -m venv "$(VENV)"
	"$(PY)" -m pip install --quiet -e .
	@touch "$(STAMP)"

setup: bundle

bundle: $(STAMP)
	@"$(PY)" scripts/build_codex_plugin.py > /dev/null
	@echo "Plugin built in $(BUNDLE)"

test: $(STAMP)
	"$(PY)" scripts/test_local.py

bench: $(STAMP)
	"$(PY)" scripts/benchmark.py

demo: $(STAMP)
	@base="$(DEMO_HOME)/$$(date +%Y%m%d-%H%M%S)"; \
	mkdir -p "$(DEMO_HOME)" && \
	"$(PY)" -m specmd demo --dest "$$base/cart" > /dev/null && \
	echo "$$base" > "$(DEMO_HOME)/.latest" && \
	(cd "$$base/cart" && git init -q) && \
	echo "Demo created in $$base/cart." && \
	echo "Next step: make agent, then ask the agent for a rule change."

agent: bundle require-demo
	@command -v claude > /dev/null || { echo "claude CLI not found in PATH."; exit 1; }
	@echo "Claude Code in $(DEMO), with the SpecMD plugin loaded for this session only."
	@cd "$(DEMO)" && $(SPECMD_ENV) claude --plugin-dir "$(BUNDLE)" $(CLAUDE_ARGS)

status: $(STAMP) require-demo
	@$(SPECMD_ENV) "$(PY)" -m specmd check --root "$(DEMO)" | "$(PY)" scripts/summarize_result.py

run: $(STAMP) require-demo
	@$(SPECMD_ENV) "$(PY)" -m specmd run --root "$(DEMO)" | "$(PY)" scripts/summarize_result.py

init: $(STAMP)
	@if [ -z "$(REPO)" ]; then echo "Usage: make init REPO=/path/to/repo"; exit 1; fi
	@"$(PY)" -m specmd init --root "$(REPO)"

require-demo:
	@if [ -z "$(DEMO_BASE)" ] || [ ! -d "$(DEMO)" ]; then echo "No demo found. Run make demo first."; exit 1; fi
