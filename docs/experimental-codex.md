---
specmd:
  schema: 1
  id: SMD-DOC-EXPERIMENTAL-CODEX
  kind: mixed
---

# Preflight experimental no Codex

Este é o primeiro incremento local do SpecMD, versão `0.1.0`: uma CLI Python e um pacote de plugin Codex para inspecionar contratos Markdown em projetos que optam por usá-lo. O preflight verifica estrutura documental e registra mudanças observadas. **Não concede aceite humano, não executa os cenários e não autoriza concluir tarefas.**

O fluxo completo descrito em [Produto](product.md), [Aceite e confiança](approval-and-trust.md) e [Integrações](integrations.md) continua em desenvolvimento. Os runners executados em [research/](../research/README.md) são experimentos separados; o preflight não os chama.

## Estado da validação

| Item | Estado desta revisão |
| --- | --- |
| Scanner e tradução de hooks | 49 testes unitários passaram, sem falhas, erros ou skips: 40 do núcleo e 9 do adaptador. |
| CLI Python instalada e bootstrap do hook | Os mesmos 11 casos de integração com Markdown real passaram usando a fonte e o bundle gerado, sem sessão com modelo ou execução BDD. Não são 22 casos distintos. |
| Pacote e descoberta pelo Codex | Bundle por allowlist gerado e reconhecido como versão `0.1.0`; descoberta não equivale à instalação (`installed: false`). |
| Instalação persistente neste ambiente de nuvem | Tentativa bloqueada por configuração de usuário em filesystem somente leitura; não equivale a instalação concluída. |
| Eventos reais e controle em sessão Codex | Tentativa impedida pelo filesystem somente leitura antes de qualquer hook ou chamada ao modelo; ainda não validados no host. |
| Trust humano pelo `/hooks` | Não demonstrado neste relatório; precisa de ação do usuário na interface. |
| Aceite de contratos, execução de cenários e gate de CI | Não implementados neste incremento. |

As interfaces do host foram investigadas no Codex CLI `0.163.0`. Compatibilidade com outras versões, Windows e Claude Code ainda não foi validada.

Evidências: [testes unitários](../research/codex/evidence/unit-tests.json), [CLI/bootstrap a partir da fonte](../research/codex/evidence/preflight-integration.json), [mesmos casos usando o bundle](../research/codex/evidence/bundle-integration.json) e [tentativa de iniciar uma sessão real](../research/codex/evidence/runtime-startup-attempt.json). Os testes de tradução exercitam o protocolo do adaptador; não demonstram, sozinhos, o efeito dos controles em uma sessão do host.

## Preparar o ambiente Python

As instruções abaixo usam shell POSIX em Linux ou macOS, Python **3.11 ou superior** e uma instalação do Codex com configuração de usuário gravável. A instalação Python pode precisar baixar dependências.

Enquanto este incremento estiver em revisão, obtenha o código da branch de implementação:

```sh
git clone --branch feat/codex-preflight https://github.com/LucasGois1/specmd.git
cd specmd
```

Defina o caminho absoluto desse clone local:

```sh
SPECMD_SOURCE="$PWD"
python3 --version
python3 -m venv "$SPECMD_SOURCE/.venv"
"$SPECMD_SOURCE/.venv/bin/python" -m pip install -e "$SPECMD_SOURCE"
export SPECMD_PYTHON="$SPECMD_SOURCE/.venv/bin/python"
"$SPECMD_PYTHON" -m specmd --version
```

`SPECMD_PYTHON` precisa apontar para o intérprete absoluto da virtualenv **original**, onde estão instaladas as dependências. Inicie o Codex a partir de um processo que herde essa variável. A virtualenv não faz parte do pacote do plugin.

As dependências declaradas para este incremento são `markdown-it-py`, `PyYAML` e `behave`, com versões fixadas em [pyproject.toml](../pyproject.toml). Behave é usado para parsing; nenhum passo de aplicação é executado por esse scanner.

## Gerar o pacote e instalar o plugin

Antes de registrar o marketplace, gere o pacote local por allowlist:

```sh
"$SPECMD_PYTHON" "$SPECMD_SOURCE/scripts/build_codex_plugin.py"
codex plugin marketplace add "$SPECMD_SOURCE"
codex plugin add specmd@specmd-local
```

O builder gera `dist/codex-plugin`, usado como source pelo [marketplace local](../.agents/plugins/marketplace.json). O pacote inclui somente os componentes necessários, como metadados, hooks, bootstrap e fonte Python; não inclui `.venv`, `.git` ou os experimentos. O manifesto de conteúdo gerado pelo builder é informativo, não um recibo de aceite ou uma assinatura de distribuição.

Essa separação importa porque o instalador do host copia recursivamente a source do plugin. O `.gitignore` do clone não é uma política de empacotamento. Neste incremento, a distribuição é **clone local + build**; instalar diretamente um marketplace Git remoto precisará de uma forma de distribuir o artefato gerado, que não está versionado.

Os comandos de marketplace e instalação persistem estado de usuário do Codex. O procedimento precisa ocorrer em um ambiente onde esse estado seja gravável. A falha de instalação observada no ambiente de nuvem está registrada separadamente da prova de descoberta em [research/codex](../research/codex/README.md).

## Revisar e autorizar os hooks

Abra o Codex no projeto em que deseja testar e use a interface `/hooks` para examinar os handlers do SpecMD. Revise os eventos, o comando executado, a origem do pacote e o intérprete selecionado antes de conceder confiança pela UX do host.

O pacote declara três handlers síncronos, cada um com timeout de 30 segundos:

- `SessionStart`: apresenta o estado inicial do preflight.
- `PostToolUse`: reavalia os documentos depois das ferramentas.
- `Stop`: traduz pendências para feedback ou devolução do controle ao usuário.

Depois de autorizar os handlers, inicie uma nova sessão para observar também `SessionStart`. Não foi implementada instalação automática de trust. Este guia não pede que o agente escreva `trusted_hash` ou altere a configuração de confiança em nome do usuário.

**Trust do hook e aceite do contrato são decisões diferentes.** O primeiro autoriza a execução do comando do plugin. O segundo precisa expressar concordância com uma versão de requisitos e ainda não existe neste incremento.

## Ativar um projeto explicitamente

O plugin só inspeciona um projeto ativado. Execute na raiz desejada:

```sh
cd "/caminho/absoluto/do/projeto"
"$SPECMD_PYTHON" -m specmd init
"$SPECMD_PYTHON" -m specmd inventory --format json
"$SPECMD_PYTHON" -m specmd check --stage completion --format json
```

`init` cria `specmd.toml` com a configuração mínima abaixo e não sobrescreve um arquivo existente:

```toml
schema = 1
```

Somente esse campo e valor são aceitos nesta versão. Não há opções configuráveis de exclusão ou de autoaprovação. O opt-in não classifica documentos nem concede aceite.

Para um ensaio isolado, use um projeto de teste novo e copie os [exemplos fictícios](../examples/cancellation.contract.md) para ele. Não copie suas regras de negócio para um projeto real como se fossem requisitos acordados.

Um repositório com Markdown sem metadados ficará bloqueado por pendências estruturais. O scanner não usa IA para classificar esses arquivos, não redige cenários automaticamente e não oferece comando para registrar aceite humano. A classificação precisa ser discutida e escrita no documento; sua declaração ainda não se torna uma dispensa aceita.

## O que a CLI realmente faz

| Comando | Efeito e interpretação |
| --- | --- |
| `specmd init` | Cria o opt-in. Saída `0` significa que a criação ocorreu, sem aprovação de documento. |
| `specmd inventory --format json` | Inspeciona documentos, vínculos e hashes. Saída `0` significa que a inspeção foi produzida; o JSON ainda pode indicar pendências. |
| `specmd check --stage completion --format json` | Retorna `1` para projetos ativos bloqueados ou aguardando revisão; `2` para erro ou projeto inativo. Não retorna sucesso de conclusão neste incremento. |
| `specmd codex-hook` | Lê um payload de hook pelo stdin e emite JSON do protocolo Codex. Seu código de saída não representa conclusão da tarefa. |

Os comandos também aceitam `--root /caminho/absoluto` em `init`, `inventory` e `check`. Somente a etapa `completion` é aceita por `check`; `implementation` e `integration` continuam sendo propostas futuras.

Resultados possíveis da inspeção:

- `inactive`: não há configuração de opt-in; não há decisão de conclusão (`may_complete: null`). No hook, um projeto nunca ativado não recebe interferência.
- `error`: configuração inválida, caminho inadequado ou falha de verificação; conclusão não autorizada.
- `blocked`: há problemas estruturais, de parsing ou de vínculos; conclusão não autorizada.
- `waiting_human_review`: a estrutura passou pelas verificações disponíveis, mas falta autoridade de aceite e evidência de execução; conclusão não autorizada.

**Todo resultado de projeto ativo contém `may_complete: false`.** Mesmo o documento informativo perfeitamente declarado ou o contrato com Gherkin válido permanece pendente. Os achados `authority_not_configured` e `evidence_not_executed` explicam essa limitação. Não há modelo de mérito, sinalizador YAML ou comando local que conceda aprovação automática.

## Subconjunto documental inspecionado

O scanner percorre arquivos `.md` e `.markdown`, sem distinguir maiúsculas e minúsculas, incluindo arquivos locais ainda não commitados. Não usa o `.gitignore` como dispensa. Poda nomes conhecidos de diretórios de dependências, build e estado local; essa lista é fixa neste incremento, não uma política de escopo aprovada por usuário.

Documentos exigem frontmatter `specmd.schema: 1`, um ID e `kind` igual a `behavioral`, `reference` ou `mixed`. Referências exigem `exemption_reason`. O scanner calcula hashes do conteúdo e um manifesto determinístico com caminhos e hash da configuração.

Para contratos e documentos mistos, verifica cabeçalhos de requisitos `SMD-…-REQ-…`, blocos cercados `gherkin`, IDs estáveis `SMD-…-SCN-…`, referências e duplicatas. Preserva posições dos cenários no Markdown. O suporte atual é a cenários simples; `Rule` e `Scenario Outline` são recusados explicitamente. Documentos e diretórios simbólicos próprios não são seguidos pelo scanner e geram pendências.

MDG nativo, adequação semântica da classificação, força das asserções e execução de steps não são implementados pelo preflight. O baseline de MDG em Cucumber.js continua sendo uma [pesquisa separada](../research/javascript-mdg/README.md).

## Comportamento do hook e estado local

Nos eventos de início e pós-ferramenta, o adaptador apresenta o resultado como contexto ao agente. Na parada:

- Para `blocked` ou `error`, a primeira passagem pode responder `decision: "block"` e pedir correção.
- Se o host informar `stop_hook_active: true` na próxima passagem, o adaptador devolve o controle com `continue: false`, mantendo a pendência e evitando um ciclo.
- Para `waiting_human_review`, devolve o controle imediatamente com `continue: false`, sem declarar aprovação ou conclusão.

Esse limite é uma solicitação de correção por ciclo de `Stop`, conforme o payload do host; não é uma autorização para ignorar a pendência depois da tentativa. O núcleo continua retornando `may_complete: false`.

O hook salva `.specmd/local/status.json` com `state_kind: "observed_local_preflight"`, o evento e diferenças observadas contra o snapshot anterior. O arquivo é cache reconstruível, sem identidade autenticada de aprovador e sem poder para autorizar a tarefa. Na primeira observação, os documentos podem aparecer como adicionados. Se a configuração for removida depois de existir estado local, o adaptador trata isso como pendência, em vez de presumir conclusão.

No projeto alvo, inclua `.specmd/local/` no `.gitignore` para manter esse estado observado fora do versionamento. `init` cria somente a configuração e não altera automaticamente o arquivo de ignore.

## Limites e próximas provas

A configuração do projeto, o cache, o pacote e o ambiente Python são mutáveis. O hash de trust pesquisado no Codex identifica a configuração do handler, não garante os bytes de todo script externo chamado. Portanto, confiar o hook não protege por si só a integridade do código nem resolve bypass por um agente com as mesmas permissões locais.

Ainda precisam de evidência separada: instalação persistente em máquina gravável, concessão humana de trust, eventos em sessão real, retomada após mudanças e experiência sem ciclos. Um ensaio por flags de sessão, quando registrado, não substitui instalação pelo marketplace nem a revisão humana pelo `/hooks`.

Aceite autenticado, evidências de implementação e gate protegido de CI permanecem fora deste incremento. As capacidades futuras e os critérios completos estão em [Integrações](integrations.md) e [Plano de validação](validation-plan.md).

## Cenários documentais do incremento

Os cenários abaixo registram os comportamentos experimentais descritos neste guia. Não possuem aceite autenticado nem ligação a steps BDD executados. Os testes Python exercitam esses comportamentos diretamente; não devem ser apresentados como execução destes blocos Gherkin.

### SMD-PREFLIGHT-REQ-001 — Identificar alterações do contrato

O manifesto identifica caminhos e bytes dos documentos e da configuração. Uma observação anterior não concede aprovação.

```gherkin
# language: pt
@SMD-PREFLIGHT-REQ-001
Funcionalidade: Identidade documental no preflight
  @SMD-PREFLIGHT-SCN-001
  Cenário: Alterar um documento depois de uma inspeção
    Dado um projeto ativado com um contrato Markdown previamente inspecionado
    Quando os bytes desse contrato forem alterados e uma nova inspeção ocorrer
    Então o digest do manifesto deve mudar
    E a conclusão da tarefa deve continuar sem autorização
```

### SMD-PREFLIGHT-REQ-002 — Separar estrutura válida de aprovação

Validar sintaxe e vínculos não concede aceite nem comprova execução. Referências declaradas também permanecem pendentes.

```gherkin
# language: pt
@SMD-PREFLIGHT-REQ-002
Funcionalidade: Ausência de autoridade de aceite no primeiro incremento
  @SMD-PREFLIGHT-SCN-002
  Cenário: Inspecionar um documento informativo estruturalmente válido
    Dado um projeto ativado com um documento de referência e justificativa válidos
    Quando a estrutura documental for inspecionada sem encontrar erros
    Então o estado deve ser "waiting_human_review"
    E o campo "may_complete" deve ser falso
```

### SMD-PREFLIGHT-REQ-003 — Devolver controle sem apagar pendências

O adaptador pede uma correção por ciclo de parada e permite devolver o controle ao usuário. Esse retorno não significa que a tarefa foi liberada.

```gherkin
# language: pt
@SMD-PREFLIGHT-REQ-003
Funcionalidade: Controle de parada sem repetição indefinida
  @SMD-PREFLIGHT-SCN-003
  Cenário: Manter um bloqueio após o feedback de correção
    Dado um documento com pendências estruturais e uma primeira resposta de bloqueio
    Quando o host repetir o evento de parada com o hook de parada já ativo
    Então o adaptador deve devolver o controle ao usuário
    E o estado observado deve continuar bloqueado
    E a conclusão da tarefa deve continuar sem autorização
```
