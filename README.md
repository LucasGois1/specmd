# SpecMD

Documentação Markdown canônica, com cenários BDD embutidos, mantida alinhada ao software durante o trabalho com agentes de IA.

> **Estado:** experimental (0.3.0). O SpecMD é um plugin assistente para Claude Code e Codex: ele faz checagens determinísticas e devolve feedback ao agente, sem aprovação formal nem auditoria ([D-021](docs/decisions.md)). O [estado da implementação](docs/implementation-status.md) separa o que existe do que está planejado.

```bash
git clone https://github.com/LucasGois1/specmd.git
cd specmd
make setup    # .venv, dependências e plugin
make demo     # projeto de demonstração novo em ~/specmd-demo
make agent    # Claude Code no demo, com o plugin SpecMD carregado
make status   # estado do demo; make run executa os cenários
```

No `make agent`, peça uma mudança de regra ao agente, por exemplo "adicione desconto de 10% para totais acima de 1000 centavos". Ele escreve a regra e os cenários no Markdown, pede sua confirmação, implementa, e o SpecMD executa os cenários ao final.

## Usar no seu repositório

Dentro do Claude Code, no seu repositório:

```
/plugin marketplace add LucasGois1/specmd
/plugin install specmd@specmd        → escolha o escopo do projeto ou local
```

Pronto: o SpecMD já está ativo nesse repositório, com os padrões. Para o time receber o plugin automaticamente, rode `/specmd:init` (ou `make init REPO=…` a partir deste clone) e faça commit do `.claude/settings.json`; quem abrir o Claude Code no repositório e confiar na pasta recebe o plugin.

Num projeto que já tem documentação, `/specmd:adopt` conduz a adoção: lista os documentos sem cenários, você diz quais não descrevem comportamento e o agente propõe os cenários de um documento por vez.

`specmd.toml` e `.specmdignore` são opcionais, para ajustar o comportamento (veja o [formato](docs/format.md)). O plugin precisa de Python 3.11 ou superior na máquina; as dependências vêm junto.

## O problema

Agentes esquecem condições, interpretam regras de outro jeito ou inventam regras que ninguém pediu, e escrevem testes que as protegem. Com testes em arquivos `.feature` separados, a documentação e os testes ainda podem divergir entre si.

## Como o SpecMD ajuda

- **Uma fonte só.** Requisitos e cenários Gherkin ficam no mesmo Markdown, que é a regra de negócio e o teste de aceitação ao mesmo tempo. Não há `.feature` para manter.
- **Feedback no momento certo.** Depois de editar a documentação, o agente recebe as pendências (requisito sem cenário, Gherkin inválido). Cenários novos devem ser mostrados ao dev antes da implementação. Depois de mudar o código, os cenários são executados e o que falhar volta com o passo e o erro.
- **Sem travar.** O feedback se repete enquanto faz diferença; a mesma pendência repetida, ou quatro devoluções seguidas, deixam o agente concluir. Erros do plugin viram aviso.
- **Motores existentes.** Python/Behave direto, e bridges para Cucumber-JVM (Java) e Godog (Go) pelo mesmo protocolo em memória ([adapters](adapters/README.md)).

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [Guia rápido](docs/quickstart.md) | Instalar, demo, comandos e uso com o Claude Code. |
| [Estado da implementação](docs/implementation-status.md) | O que existe, limites e validações. |
| [Produto](docs/product.md) | Problema, proposta, fluxo e limites. |
| [Requisitos e cenários](docs/requirements.md) | Obrigações do SpecMD em Gherkin no próprio Markdown. |
| [Formato](docs/format.md) | Como escrever documentos, requisitos, cenários, `.specmdignore` e `specmd.toml`. |
| [Decisões](docs/decisions.md) | Diretrizes e a mudança de direção D-021. |
| [Pesquisa dos runners](research/README.md) | Protótipos e evidências por linguagem. |
| [Dispatch nativo no Claude Code](research/claude/README.md) | Sessões headless reais exercitando os hooks. |
| [Posicionamento](docs/positioning.md) | Antecedentes e sobreposição com outras ferramentas. |

Documentos anteriores à D-021 (arquitetura, integrações, indexação, roadmap, plano de validação, Codex experimental e o [HANDOFF](HANDOFF.md)) estão marcados como históricos onde descrevem o aceite assinado.

## Testes

`python -m unittest discover -s tests` (ou `make test`). Os testes de hooks criam projetos reais e executam o Behave de verdade; os payloads dos hooks são simulados. Os bridges nativos têm verificações próprias em `adapters/`.
