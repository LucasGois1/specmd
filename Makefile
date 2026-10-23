# Atalhos para experimentar o SpecMD localmente com o Claude Code.
# Nenhum alvo aceita contratos: a decisão continua sendo feita na revisão.

PYTHON ?= python3
DEMO_HOME ?= $(HOME)/specmd-demo
CLAUDE_ARGS ?=
REVIEW_ARGS ?=

VENV := $(CURDIR)/.venv
PY := $(VENV)/bin/python
STAMP := $(VENV)/.specmd-installed
BUNDLE := $(CURDIR)/dist/codex-plugin

# Avaliadas a cada alvo, para enxergar um demo recém-criado.
DEMO_BASE = $(shell cat "$(DEMO_HOME)/.latest" 2>/dev/null)
DEMO = $(DEMO_BASE)/cart
AUTHORITY = $(DEMO_BASE)/cart-authority
TRUST = $(AUTHORITY)/trust.json
SPECMD_ENV = SPECMD_PYTHON="$(PY)" SPECMD_TRUST_STORE="$(TRUST)"

.DEFAULT_GOAL := help
.PHONY: help setup bundle test demo agent review status run audit require-demo

help:
	@echo "Uso: make <alvo>"
	@echo "  setup   Cria .venv, instala dependências e gera o plugin"
	@echo "  test    Roda a suíte local"
	@echo "  demo    Cria um projeto de demonstração novo em $(DEMO_HOME)"
	@echo "  agent   Abre o Claude Code no demo com o plugin SpecMD"
	@echo "  review  Abre a revisão do contrato no navegador"
	@echo "  status  Mostra o estado do demo"
	@echo "  run     Executa os cenários do demo"
	@echo "  audit   Lista as decisões registradas no demo"

$(STAMP): pyproject.toml
	$(PYTHON) -m venv "$(VENV)"
	"$(PY)" -m pip install --quiet -e .
	@touch "$(STAMP)"

setup: bundle

bundle: $(STAMP)
	@"$(PY)" scripts/build_codex_plugin.py > /dev/null
	@echo "Plugin gerado em $(BUNDLE)"

test: $(STAMP)
	"$(PY)" scripts/test_local.py

demo: $(STAMP)
	@base="$(DEMO_HOME)/$$(date +%Y%m%d-%H%M%S)"; \
	mkdir -p "$(DEMO_HOME)" && \
	"$(PY)" -m specmd demo --dest "$$base/cart" > /dev/null && \
	echo "$$base" > "$(DEMO_HOME)/.latest" && \
	echo "Demo criado em $$base/cart, sem contrato aceito." && \
	echo "Próximos passos: make agent em um terminal e make review em outro."

agent: bundle require-demo
	@command -v claude > /dev/null || { echo "CLI claude não encontrado no PATH."; exit 1; }
	@echo "Claude Code em $(DEMO), com o plugin SpecMD carregado só nesta sessão."
	@cd "$(DEMO)" && $(SPECMD_ENV) claude --plugin-dir "$(BUNDLE)" $(CLAUDE_ARGS)

review: $(STAMP) require-demo
	@"$(PY)" -m specmd review --root "$(DEMO)" --authority "$(AUTHORITY)" --trust "$(TRUST)" $(REVIEW_ARGS)

status: $(STAMP) require-demo
	@$(SPECMD_ENV) "$(PY)" -m specmd check --root "$(DEMO)" | "$(PY)" scripts/summarize_result.py

run: $(STAMP) require-demo
	@$(SPECMD_ENV) "$(PY)" -m specmd run --root "$(DEMO)" | "$(PY)" scripts/summarize_result.py

audit: $(STAMP) require-demo
	@$(SPECMD_ENV) "$(PY)" -m specmd audit --root "$(DEMO)" | "$(PY)" scripts/summarize_result.py

require-demo:
	@if [ -z "$(DEMO_BASE)" ] || [ ! -d "$(DEMO)" ]; then echo "Nenhum demo encontrado. Rode make demo primeiro."; exit 1; fi
