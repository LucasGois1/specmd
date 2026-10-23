# Orientações para agentes

## Estado do repositório

SpecMD é um plugin assistente para agentes de programação (Claude Code e Codex). Ele mantém a documentação Markdown canônica, com cenários Gherkin embutidos, alinhada ao software. Quem define as regras é o desenvolvedor, conversando com o agente. O plugin faz checagens determinísticas em momentos-chave e devolve feedback ao agente: documentação sem cenários, cenários novos que o dev ainda não viu, cenários sem implementação ou falhando.

A direção mudou em 23/10/2026 ([D-021](docs/decisions.md)): o ciclo de aceite assinado, a autoridade, o trust e o bloqueio de implementação foram removidos. Consulte [docs/implementation-status.md](docs/implementation-status.md) para o que existe hoje. O [HANDOFF.md](HANDOFF.md) preserva o contexto anterior e está parcialmente superado. Protótipos em `research/` não constituem suporte produtivo.

Ao relatar verificações, informe somente o que foi efetivamente executado e seu alcance. Nunca fabrique execução de testes ou suporte de integração.

## Regras centrais do desenho

- O Markdown é a fonte canônica das regras de negócio. Requisitos e seus cenários ficam no mesmo documento.
- A solução não deve exigir arquivos `.feature`, nem sua geração como etapa de execução. Os cenários são lidos do Markdown e executados em memória.
- O plugin ajuda e não engessa: devolve feedback objetivo ao agente e nunca encerra a sessão. Um feedback repetido sem mudança deixa o agente parar.
- A confirmação do dev é uma resposta normal na conversa. Cenários novos ou alterados devem ser mostrados ao dev antes da implementação.
- Mudança de código renova a execução dos cenários. Estado local (`.specmd/local/`) é reconstruível e pode ser apagado.
- Hooks disponíveis devem ser verificados por plataforma e versão. Não invente nomes de eventos ou APIs como se estivessem confirmados.
- Os dois hosts usam um único `hooks/hooks.json`; o Claude Code o carrega por padrão na raiz do plugin. Não declare um segundo arquivo de hooks.
- Gere o pacote por `scripts/build_codex_plugin.py` antes de instalar localmente; não empacote o clone inteiro com `.venv`, `.git` ou dados locais.
- As dependências de runtime do plugin ficam em `vendor/`, geradas por `scripts/vendor_deps.py` a partir do `pylock.toml`. Não edite `vendor/` à mão; ao mudar dependências, regenere o lock e o `vendor/`.

## Trabalho nos documentos

- Escreva em português; preserve identificadores estáveis e links relativos.
- Mantenha requisitos e seus cenários no mesmo Markdown.
- Use Gherkin em português com a declaração `# language: pt` nos exemplos.
- Registre mudanças normativas e decisões de forma visível em [docs/decisions.md](docs/decisions.md).
- Identifique comandos, schemas e fluxos ainda não implementados como propostas.
- Não adicione licenças ou políticas como se já tivessem sido escolhidas.
