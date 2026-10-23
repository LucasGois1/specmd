---
specmd:
  schema: 1
  id: SMD-DOC-HANDOFF-LOCAL-AGENT
  kind: reference
  exemption_reason: "Contexto de continuação, decisões anteriores, evidências e roteiro de validação; não substitui os requisitos canônicos nem concede aceite."
---

# Handoff — SpecMD para o agente local

> **Histórico, anterior à [D-021](docs/decisions.md).** Este documento descreve o desenho com aceite assinado, autoridade, trust e bloqueio de implementação, removido em 23/10/2026. Para o produto atual, veja [produto](docs/product.md) e [estado da implementação](docs/implementation-status.md).

Documento preparado a pedido de Lucas para transferir o contexto da descoberta, pesquisa e implementação ao agente que trabalhará no computador dele. Não é necessário ter acesso à conversa original.

**Referência desta transferência:** 23/10/2026. Repositório público: [LucasGois1/specmd](https://github.com/LucasGois1/specmd). A implementação experimental **0.2.0** foi integrada à `main` pelo [PR #1](https://github.com/LucasGois1/specmd/pull/1), no merge `352c8323f701cefaca2fca4f8d42952e2de07fbd`. O código verificado antes do merge está em `e24142308b2e98904eff062012918fb89060d065`; a árvore de arquivos do merge foi conferida e era igual à desse commit.

O resultado atual é um ciclo experimental utilizável para testar a experiência. Não é um produto de produção com identidade humana autenticada, isolamento de permissões e utilidade demonstrada. O pedido de Lucas foi implementar o fluxo para ele experimentar, aceitando testes com agentes simulados quando a sessão real com modelo não estava disponível.

## 1. Por onde começar

Leia [AGENTS.md](AGENTS.md), este handoff, o [estado da implementação](docs/implementation-status.md) e o [guia rápido](docs/quickstart.md). Depois consulte os [requisitos com cenários](docs/requirements.md) e os documentos específicos da área em que trabalhará.

Os documentos de produto e planejamento preservam intenções e propostas anteriores. Perguntas históricas nesses textos não significam que toda a implementação continua pendente. Para afirmar uma capacidade atual, confira código, versão e evidência correspondente. Não refaça toda a pesquisa nem reimplemente o núcleo antes de exercitar o que existe.

A próxima entrega útil é uma sessão local com Lucas: instalar, revisar um contrato, aceitar ou rejeitar uma versão, executar cenários, provocar mudanças e observar como o agente responde. Em paralelo, é necessário triar as pendências do SonarQube. A próxima entrega não precisa ser uma plataforma maior.

## 2. O problema que originou a ideia

Lucas desenvolve software com agentes de IA. Modelos e ferramentas melhoraram, mas manter intenção, documentação, implementação e testes alinhados continua difícil. Colocar specs no repositório aproxima o contexto do código e facilita descoberta por `rg`, busca textual e navegação. Isso não garante que o agente encontre, leia ou interprete corretamente cada obrigação.

Discutimos dois sentidos de desalinhamento:

1. **Omissão ou interpretação incorreta:** existe um requisito, mas o agente esquece uma condição ou implementa outra interpretação.
2. **Comportamento inventado:** o agente cria uma regra não solicitada, escreve testes que a protegem e entrega código verde. O desenvolvedor encontra depois uma restrição que não estava acordada em lugar algum.

Exemplo discutido: o usuário pede cadastro por e-mail; o agente decide aceitar apenas e-mails corporativos. Testes para essa restrição não a transformam em uma decisão de produto legítima. Escrever a documentação depois também não autoriza a regra: é preciso apresentar a proposta e obter uma decisão humana aplicável.

A hipótese central é melhorar a experiência com agentes para tornar explícita a relação entre **intenção reconhecida → contrato aceito → comportamento implementado → evidência atual**. O objetivo é reduzir erros e esforço de revisão, com interrupções compreensíveis e recuperáveis.

Não estamos afirmando que todos os documentos de software são Markdown ou que documentação executável foi inventada aqui. Markdown foi escolhido como formato de autoria e fonte canônica deste projeto.

## 3. Direções que Lucas estabeleceu

| Direção | Motivo e consequência |
| --- | --- |
| Markdown canônico | Explicações, requisitos e cenários Gherkin ficam no mesmo documento. Evitar uma segunda especificação editável que possa divergir. |
| Sem dependência de `.feature` | A execução não deve exigir arquivos `.feature` mantidos à parte nem sua geração temporária obrigatória. Os motores recebem conteúdo em memória. |
| Cenários verificáveis | Um requisito comportamental não deve ser considerado incorporado apenas porque foi descrito. É necessário ligá-lo a verificação executada sobre a implementação. |
| Rastreabilidade nos dois sentidos | Expor requisitos sem evidência e mudanças de comportamento sem origem reconhecida. |
| Aceite humano explícito | Vale tanto para specs escritas junto com o agente quanto para mudanças que ele propõe proativamente durante o desenvolvimento. |
| Aceite por versão | Hash determinístico identifica o conteúdo revisado. Modificar contrato ou cenário exige nova decisão aplicável. |
| Preservar o aceite quando só muda o código | Novas tentativas de implementar a mesma intenção exigem renovar evidências, não pedir concordância de produto repetidamente. |
| Evitar autoaprovação | O agente pode propor e implementar; a autoridade efetiva de aceite precisa ficar fora das permissões dele. Um hash sozinho não resolve isso. |
| Classificação documental | Markdown comportamental exige cenários; conteúdo informativo pode ser dispensado, com justificativa e revisão. Há documentos mistos. |
| Inventário e monitoramento | Descobrir todos os Markdown próprios do projeto, inclusive novos não rastreados pelo Git. Uma dispensa não faz o documento desaparecer do inventário. |
| Desempenho incremental | Evitar trabalho repetido quando possível, com invalidação correta. Cache é derivado e nunca concede aceite. |
| Hooks para agentes | Usar eventos realmente suportados por Codex e Claude Code para feedback e bloqueios onde forem possíveis. |
| Espera humana legítima | Devolver o controle para uma decisão não equivale a concluir a tarefa. Evitar loops de `Stop`. |
| Auditoria | Mostrar o que mudou, quem propôs e quem decidiu, distinguindo autoria Git declarada de identidade humana autenticada. |
| Java, Python e Go | As três linguagens fazem parte do escopo inicial de execução; cada integração precisa de prova própria. |

O nome escolhido foi **SpecMD**, com repositório e CLI `specmd`. Disponibilidade global de marca/pacote e licença não foram resolvidas. Não inventar uma decisão de licença.

Essas direções são contexto da conversa. Não constituem recibos de aceite assinados para os arquivos deste repositório. Merge de PR e autorização para escrever documentação também não substituem esses recibos.

## 4. O que investigamos e o que a pesquisa resolveu

### Markdown with Gherkin e sobreposição com outras ferramentas

Lucas perguntou se o projeto já existia sob outro nome e pediu uma reflexão antes de prosseguir. A pesquisa está em [positioning.md](docs/positioning.md), com fontes fixadas por versão/commit.

| Antecedente | O que aprendemos | Consequência para SpecMD |
| --- | --- | --- |
| Markdown with Gherkin oficial, MDG | Documentação executável Markdown já existe. A sintaxe usa cabeçalhos/listas e a convenção `.feature.md`. | Não anunciar novidade apenas por juntar Markdown e execução. `.feature.md` continua sendo Markdown; seu nome sozinho não viola a restrição contra um `.feature` paralelo. |
| Cucumber.js com MDG | O baseline executou MDG em `.feature.md` e em `.md` explícito. Markdown comum com cerca `gherkin` terminou com exit 0 e zero cenários. | Sintaxe, descoberta, parsing e execução efetiva são verificações diferentes. Não presumir suporte nativo aos blocos do SpecMD. |
| Tracey | Rastreabilidade de requisitos, implementação/testes, referências obsoletas e integração com agentes têm antecedente próximo. | Avaliar reutilização antes de criar outro sistema de rastreamento. |
| Gauge e Concordion | Exemplos e especificações executáveis em documentos também são anteriores. | Trocar a sintaxe de autoria não demonstra valor por si só. |
| Spec Kit e OpenSpec | Proposta, revisão e implementação guiada por specs, além de extensões, já atendem partes do fluxo. | Comparar fluxos completos e composições bem configuradas. |
| GitHub reviews e CI | Reviews autenticados, invalidação de aprovação e checks obrigatórios podem fornecer partes importantes da autoridade e do gate. | Reaproveitar mecanismos existentes quando entregarem a separação de permissões necessária. |
| spec-gates e outras extensões | Há sobreposição com Markdown executável, hashes, attestations e gates agente/Git/CI. | Referência secundária de engenharia; não presumir maturidade ou incompatibilidade sem testar. |

**Correção importante:** Tracey é implementado em Rust, mas não é específico para analisar somente Rust. O registro de linguagens no snapshot consultado inclui Java, Go e Python. O README omitia Python, embora o fonte o incluísse. Foi uma inspeção de suporte de análise/rastreabilidade; não foi prova de execução BDD nem de paridade funcional entre linguagens.

Lucas questionou a confiabilidade de spec-gates por ter poucas estrelas na ocasião. A conclusão adequada foi não usá-lo como referência de maturidade comprovada. Contagem de estrelas não demonstra qualidade, confiabilidade ou adoção real; não repetir uma contagem antiga como fato atual.

**Conclusão de posicionamento:** há sobreposição substancial. Não demonstramos exclusividade, superioridade ou que nenhuma ferramenta existente atenda ao problema. Também não executamos uma composição que comprove que tudo já está resolvido. O candidato a valor é a experiência integrada de preservar intenção durante o trabalho do agente. Isso continua uma hipótese a medir.

Se uma integração pequena sobre ferramentas existentes resolver o trabalho com custo igual ou menor, SpecMD pode virar um plugin/preset. Não é necessário justificar uma plataforma independente a qualquer custo.

### Como rodar sem `.feature`

Não encontramos nem presumimos um argumento universal de CLI que aceite todo o texto dos cenários em todos os ecossistemas. Reaproveitamos os motores existentes e seus pontos programáticos de entrada.

| Linguagem | Caminho exercitado | Limites atuais |
| --- | --- | --- |
| Python | Extração Markdown → `behave.parser.parse_feature` → `ModelRunner`, em subprocesso, com steps reais. | Behave não é Cucumber oficial. O worker não carrega `environment.py`, configurações ou filtros Behave do projeto. |
| Java | Gherkin em memória por `Resource`/`FeatureParser` e `Runtime.withFeatureSupplier`, com glue Cucumber-JVM. | API pública do core não significa contrato estável de extensão. Bridge atual suporta cenários simples e Background; recusa Rule/Outline. |
| Go | `godog.Options.FeatureContents`, com inicializador de passos do projeto. | Descoberta de diretório/CLI não equivale à entrada em memória. Bridge atual suporta cenários simples e Background; recusa Rule/Outline. |

Scanner schema2 e runner Python suportam Rule e instâncias de Scenario Outline. O scanner aceitar uma estrutura não obriga todos os motores a suportá-la. IDs concretos de exemplos usam `<ID-do-cenário>:row:<grupo>:<linha>`.

Os passos chamam o código da aplicação e fazem asserções; coletar Gherkin não gera sozinho testes adequados. Um runner com exit 0, zero cenários ou dry-run não concede o OK. A pesquisa Java chegou a observar dry-run com eventos `PASSED` sem chamada à aplicação: esse é um caso negativo deliberado do gate.

Detalhes e versões estão em [runner-feasibility.md](docs/runner-feasibility.md), [research](research/README.md) e [adapters](adapters/README.md).

## 5. O que existe no código agora

| Área | Arquivo/ponto de entrada | Responsabilidade atual |
| --- | --- | --- |
| CLI | [cli.py](src/specmd/cli.py) | `init`, `demo`, `inventory`, `review`, `run`, `check`, `status`, `audit`, `verify`, adaptadores de hooks. |
| Configuração | [config.py](src/specmd/config.py) | Leitura/validação estrita de `specmd.toml`; schema1 legado e schema2 do fluxo completo. |
| Inventário e parsing | [core.py](src/specmd/core.py) | Markdown, frontmatter, hashes, IDs, requisitos/cenários, origem, validações e extração em memória. |
| Ciclo de revisão e evidência | [workflow.py](src/specmd/workflow.py) | Proposta, decisão aplicável, rastreabilidade, snapshot de código, execução, invalidação, conclusão e auditoria. |
| Assinaturas e confiança | authority.py (removido por [D-021](docs/decisions.md)) | Ed25519, autorização de chave por contexto, decisão vigente externa, rejeição/revogação e identidade de repositório. |
| Revisão local | review_server.py (removido por [D-021](docs/decisions.md)) | HTTP de loopback, texto integral/diff verificado, configuração/vínculos, aceitar/rejeitar e recusa de versão obsoleta. |
| Execução | [runner.py](src/specmd/runner.py), [behave_worker.py](src/specmd/behave_worker.py) | Subprocessos, protocolo JSON, conjunto exato esperado, passos efetivos, timeout e worker Python. |
| Bridges nativos | [Java](adapters/java/README.md), [Go](adapters/go/README.md) | Código e exemplos para integrar passos reais das aplicações nesses motores. |
| Codex e Claude | [codex.py](src/specmd/codex.py), [claude.py](src/specmd/claude.py) | Tradução de estados para o protocolo de hooks dos hosts. |
| Pré-implementação | pretool.py (removido por [D-021](docs/decisions.md)) | Política local conservadora para permitir leituras/docs e negar ações de implementação enquanto falta aceite. |
| Demonstração | [demo.py](src/specmd/demo.py) | Projeto descartável de carrinho, dois requisitos/cenários, implementação, steps e autoridade demonstrativa externa. Não aceita automaticamente o contrato. |
| Bundle | [build_codex_plugin.py](scripts/build_codex_plugin.py) | Gera pacote por allowlist, com manifests/hooks/bootstrap e módulos Python. |
| Testes e relatórios | [test_local.py](scripts/test_local.py), [tests](tests), [research/workflow](research/workflow/README.md) | Validação local reprodutível e escopo explícito das evidências. |
| CI | [specmd.yml](.github/workflows/specmd.yml) | Suíte Python, bridges Java/Go reais e verificação contratual condicionada ao opt-in na raiz. |

### Inventário, classificação e vínculos

- Descobre `.md` e `.markdown`, incluindo arquivos ainda não rastreados pelo Git. Não usa `.gitignore` como dispensa contratual automática.
- Há podas fixas de diretórios de dependências, caches, `.git`, `.specmd`, builds etc. São escolhas de implementação a revisar; não uma política de escopo universal já validada.
- Frontmatter usa `specmd.schema: 1`, ID e `kind: behavioral|reference|mixed`. Esse schema não é o mesmo número do schema de `specmd.toml`.
- `reference` exige justificativa. Referência com requisitos explícitos ou Gherkin executável gera conflito de classificação. Isso não detecta toda obrigação escrita em prosa.
- SHA-256 usa bytes exatos, incluindo finais de linha. O manifesto incorpora caminhos e hash da configuração; o workflow também vincula o mapa de rastreabilidade.
- `.specmd/traceability.json` liga arquivos a IDs de requisitos/cenários. Política estrita exige vínculos para os arquivos fonte/testes reconhecidos. Isso torna a origem declarada revisável, sem provar equivalência semântica.
- Classificação e vínculos alterados entram na nova identidade sujeita a revisão. Não são uma forma de o agente se autoisentar.
- Cache atual é **consultivo** e a fonte continua sendo reanalisada. Não anunciar que o ganho de performance incremental já foi entregue.

### Aceite, contexto e auditoria

- Revisão mostra os Markdown completos, diffs, classificações, justificativas, configuração e vínculos. O baseline do diff é validado por proposta/recibo e confiança externa; não depende apenas do cache local de “último aceite”.
- Ed25519 vincula decisão, projeto/repositório, hash/manifesto, proposta, revisor declarado e momento. Assinar não autentica automaticamente uma pessoa.
- Trust store é externo ao projeto. `latest_decisions` registra a decisão vigente; rejeitar uma versão invalida o aceite anterior daquela proposta. Chaves podem ser revogadas.
- `repository_id` opcional fornece identidade lógica portátil (`repo:<repository_id>`). `workspace_root` é a raiz física usada para checar limites locais. Sem identidade lógica, o fallback é o caminho absoluto do checkout, inadequado para transportar recibos livremente entre máquinas.
- Um nome Git ou nome digitado no formulário é uma declaração. O sistema retorna `human_authenticated: false`; não há serviço de login humano/OAuth de produção implementado.
- Auditoria no repositório pode ser apagada por quem controla o repositório. Preservação confiável depende de registro externo e política de acesso.

### Artefatos e o que pode ir para Git

| Caminho | Significado |
| --- | --- |
| `specmd.toml` | Opt-in, identidade e configuração do projeto alvo. |
| Markdown do projeto | Fonte canônica do comportamento e dos cenários. |
| `.specmd/traceability.json` | Vínculos declarados, parte da versão revisável. |
| `.specmd/reviews/*.json` | Propostas/snapshots, sem autoridade de aceite por si só. |
| `.specmd/approvals/*.json` | Recibos assinados; só valem se verificados por confiança externa aplicável e decisão vigente. |
| `.specmd/local/` e `.specmd/cache/` | Estado observado, evidência local e cache reconstruíveis; devem ficar fora do versionamento usual. |
| Diretório externo de autoridade | No demo contém chave privada e trust. Nunca versionar chave privada ou tratar esse local como isolado só por ficar fora do clone. |

Não transportar chaves, credenciais, configuração do Codex ou recibos de fixtures deste ambiente para o computador de Lucas.

## 6. Como interpretar os estados

| Estado | Interpretação |
| --- | --- |
| `inactive` | Projeto sem opt-in. Não é um OK contratual. |
| `error` | A verificação não pôde ser determinada ou há configuração/entrada inválida. |
| `blocked` | Estrutura, origem/vínculos ou execução insatisfatórios. |
| `waiting_human_review` | A versão atual exige decisão aplicável. Devolver controle ao humano, sem declarar conclusão. |
| `awaiting_evidence` | Há aceite aplicável, mas falta execução atual ou a evidência ficou obsoleta/expirou. |
| `demo_passed` | O ciclo demonstrativo satisfez seus critérios; `may_complete: true` vale nesse contexto local. |
| `passed` | Caminho de execução real fresca, confiança configurada como protegida e rastreabilidade estrita. Pressupõe implantação confiável. |

Pontos essenciais:

- `schema = 1` do projeto mantém o preflight antigo, sem um caminho de conclusão. `schema = 2` habilita o ciclo integrado.
- `demo_passed` usa `verification_mode: "demo"` e `assurance: "local_demo"`. Pode ter `test_mode: "real"`: testes reais não transformam autoridade demonstrativa em aprovação humana autenticada.
- Um runner `mock` exige opt-in explícito e nunca satisfaz `verify --require-real`.
- `verify` e `check --require-real` executam nova verificação real. Um relatório JSON local antigo não concede um `passed` protegido sozinho.
- Um campo `protected` no trust não cria isolamento de sistema operacional, identidade humana ou proteção de branches. O verificador não consegue provar que suas próprias premissas de implantação são verdadeiras.
- Em comandos de gate, código 0 representa sucesso aplicável; 1 representa pendência/bloqueio e 2 erro/inatividade. Não tratar `inventory` ou preparação de revisão com exit 0 como aprovação.
- `turn.completed` do host significa que o turno terminou; não substitui o veredito do SpecMD.

## 7. O que foi realmente validado

| Evidência | Resultado registrado | O que não prova |
| --- | --- | --- |
| [Suíte local](research/workflow/evidence/local-tests.json) | 187 testes passaram, sem skips. Inclui HTTP local, assinaturas e execução Python reais, além de mocks/fixtures. | Não demonstra que uma pessoa leu/aceitou os contratos reais nem que um LLM respeitou os hooks. |
| [Integração nativa](research/workflow/evidence/native-bridges.json) | Seis casos com motores reais: sucesso, asserção falha e passo indefinido em Java e Go, via núcleo. | Não é certificação de todos os projetos, versões ou formatos dessas linguagens. |
| Testes Go | `go test ./...` do bridge passou; build do exemplo e execução pelo núcleo passaram. | Não mede utilidade do produto. |
| [Preflight no bundle](research/workflow/evidence/bundle-preflight.json) | 11 casos de compatibilidade conferidos. | Repetir os mesmos casos em fonte/bundle não cria 22 cenários independentes de produto. |
| [Instalação Codex 0.2.0](research/workflow/evidence/codex-installation.json) | Pacote instalado neste ambiente e 21 arquivos conferidos contra o bundle. | Esta revisão não recebeu um novo ensaio nativo completo de todos os hooks com modelo real. |
| [Pesquisa anterior do Codex](research/codex/README.md) | Executável real Codex 0.163.0 despachou `SessionStart`, `PostToolUse` e `Stop` com backend HTTP determinístico; uma ferramenta real alterou um contrato temporário. | Backend determinístico não é um LLM. A prova de uma revisão anterior não cobre automaticamente o código atual. |
| `PreToolUse` atual e Claude | Testes de política/protocolo e bootstrap. | Dispatch nativo atual, instalação do Claude e experiência humana ainda precisam de ensaio local. |
| [Actions do PR #1](https://github.com/LucasGois1/specmd/actions/runs/39949649507) | Jobs `tests-and-contracts` e `native-bridges` passaram. | A etapa de autoridade externa foi `skipped`, pois não havia `specmd.toml` na raiz do próprio SpecMD. |

As fixtures de aceite usam identidades como revisor sintético, em diretórios temporários descartáveis. Elas são testes autorizados do mecanismo, não aceites de Lucas. `scripts/test_local.py` registra explicitamente `real_llm_executed: false` e `human_review_performed: false`.

Três regressões concretas foram encontradas e corrigidas durante a implementação:

1. Bytecode Python antigo, com timestamp/tamanho ainda válidos, podia mascarar uma fonte alterada. O worker usa prefixo de cache temporário novo por execução; `-B` sozinho não impediria a leitura do `.pyc` antigo.
2. `fresh_evidence={}` podia cair no cache e ser interpretado como execução fresca. Seleção agora distingue `None` de entrada inválida, com validação do relatório.
3. Patch documental válido com linha vazia de contexto era negado pelo gate pré-ferramenta. O parser foi corrigido e ganhou regressão.

Preserve esses testes ao refatorar.

### Pendência conhecida: SonarQube

O PR #1 foi integrado a pedido de Lucas pelo fluxo normal do GitHub. Na conferência de merge, os testes estavam verdes, mas o quality gate do SonarQube estava reprovado. Não foi corrigido ou dispensado pelo trabalho de merge.

O agente local deve consultar o estado atual e triar os apontamentos, sem confundir “teste passou” com “toda a análise de qualidade passou”. Entre os apontamentos observados havia caminhos/saídas de probes de pesquisa, instalação/lock de dependências Python e HTTP na interface de loopback. Avalie o fluxo e o contexto de cada um: não declarar todos falsos positivos nem mudar arquitetura só para silenciar uma regra. Não marcar issues resolvidas sem evidência.

[PR e discussões](https://github.com/LucasGois1/specmd/pull/1) · [SonarQube Cloud](https://sonarcloud.io/dashboard?id=LucasGois1_specmd)

## 8. Ambiente desta conversa versus computador de Lucas

O Codex CLI citado anteriormente foi instalado/executado **no ambiente de trabalho desta conversa**. Não houve instalação no computador pessoal de Lucas por essa afirmação.

Nesse ambiente, o CLI real estava disponível. A tentativa de sessão com o serviço de modelo configurado falhou com `401`, antes de completar o ciclo com LLM. Por isso usamos backend determinístico e simulações de protocolo. A conclusão correta não é “não conseguimos executar o CLI”, e sim “não validamos a experiência com um modelo real autenticado nesse ambiente”.

Também houve uma fase histórica de home do Codex somente leitura, superada quando o ambiente ficou gravável. Não tratar isso como bloqueio inerente ao produto ou ao computador local.

No computador de Lucas, verifique versões, autenticação e capacidades existentes. Não presumir Codex/Claude/Python/JDK/Go/Maven instalados, nem reutilizar caminhos como `/workspace`, `/run/codex-environment/...` ou SDKs temporários da pesquisa. Não remapear `HOME`/`CODEX_HOME` para reproduzir uma instalação; use os mecanismos normais do host e preserve configuração existente.

## 9. Roteiro portátil para começar localmente

Os comandos abaixo assumem shell POSIX. Windows nativo ainda não foi verificado. Não há necessidade de credencial de modelo para os testes automáticos e para o demo pela CLI/navegador.

### Instalação e regressão

Se ainda não existe clone local:

```sh
git clone https://github.com/LucasGois1/specmd.git
cd specmd
git switch main
```

Se já existe, inspecione estado e mudanças locais antes de atualizar; não sobrescreva trabalho existente.

```sh
SPECMD_SOURCE="$PWD"
python3 -m venv "$SPECMD_SOURCE/.venv"
"$SPECMD_SOURCE/.venv/bin/python" -m pip install -e "$SPECMD_SOURCE"
export SPECMD_PYTHON="$SPECMD_SOURCE/.venv/bin/python"
"$SPECMD_PYTHON" -m specmd --version
"$SPECMD_PYTHON" scripts/test_local.py
```

Use Python 3.11 ou superior. O relatório padrão é `.specmd/local/test-report.json`, sem autoridade de aceite. O snapshot histórico registrou 187 testes; a contagem pode mudar em revisões futuras, então registre o commit e o resultado efetivamente executados.

### Demo sem aceite automático

Crie diretórios novos fora do clone. Exemplo com uma base temporária nova:

```sh
SPECMD_DEMO_BASE="$(mktemp -d)"
SPECMD_DEMO_ROOT="$SPECMD_DEMO_BASE/cart"
SPECMD_DEMO_AUTHORITY="$SPECMD_DEMO_BASE/cart-authority"
"$SPECMD_PYTHON" -m specmd demo --dest "$SPECMD_DEMO_ROOT"
export SPECMD_TRUST_STORE="$SPECMD_DEMO_AUTHORITY/trust.json"
"$SPECMD_PYTHON" -m specmd check --root "$SPECMD_DEMO_ROOT"
"$SPECMD_PYTHON" -m specmd review --root "$SPECMD_DEMO_ROOT" --prepare
```

Antes de aceitar, `check` deve permanecer pendente e retornar código não zero. O demo se recusa a sobrescrever diretórios não vazios ou chaves existentes. Não apagar dados para forçar uma repetição: escolha novos diretórios.

Abra a revisão para Lucas:

```sh
"$SPECMD_PYTHON" -m specmd review --root "$SPECMD_DEMO_ROOT" \
  --authority "$SPECMD_DEMO_AUTHORITY" --trust "$SPECMD_TRUST_STORE"
```

O servidor escuta em loopback e porta aleatória. `--no-open` permite abrir manualmente a URL. O token da sessão fica no fragmento da URL e é usado pelo navegador; não publicar esse link de sessão como evidência compartilhada.

**A ação de aceitar ou rejeitar é de Lucas.** O agente não deve chamar a API de aceite ou a função de assinatura em nome dele para concluir o teste humano. Não alterar o trust para `protected` como atalho. Os testes sintéticos que fazem isso em fixtures não são uma receita de uso de produção.

Depois da decisão, encerre o servidor com Ctrl+C quando apropriado. Se houve rejeição, ajuste a proposta e volte à revisão; a tarefa permanece pendente. Depois de um aceite aplicável, execute:

```sh
"$SPECMD_PYTHON" -m specmd run --root "$SPECMD_DEMO_ROOT"
"$SPECMD_PYTHON" -m specmd check --root "$SPECMD_DEMO_ROOT"
"$SPECMD_PYTHON" -m specmd audit --root "$SPECMD_DEMO_ROOT"
```

O resultado positivo local esperado é `demo_passed`, com testes reais da aplicação. Confirme que `verify --require-real` continua recusando a autoridade de demonstração.

Não executar `specmd init` na raiz deste repositório só para reproduzir o demo: a raiz contém documentação e fixtures de pesquisa, e ainda não recebeu um opt-in contratual de todo esse conteúdo. Use um projeto alvo separado.

### Instalar e testar o plugin Codex

Na raiz do clone, examine o CLI local e a existência de marketplace homônimo antes de alterar uma instalação:

```sh
codex --version
codex plugin --help
codex plugin marketplace list --json
"$SPECMD_PYTHON" "$SPECMD_SOURCE/scripts/build_codex_plugin.py"
codex plugin marketplace add "$SPECMD_SOURCE"
codex plugin add specmd@specmd-local
```

Inicie Codex no projeto de demonstração a partir de um terminal que herde `SPECMD_PYTHON` absoluto e `SPECMD_TRUST_STORE`. A forma normal de iniciar, depois de configurar as variáveis, é:

```sh
cd "$SPECMD_DEMO_ROOT"
codex
```

Lucas deve revisar os handlers em `/hooks` e decidir sua confiança pela interface normal. Confiar um hook e aceitar um contrato são decisões distintas. Não fabricar essa ação humana, desativar trust ou usar flags de bypass para declarar a UX validada.

O marketplace aponta para `dist/codex-plugin`; esse artefato é ignorado pelo Git e precisa de build local. Instalação diretamente de um remoto sem o artefato não é um fluxo de distribuição resolvido. O Codex copia o pacote instalado: edits no clone não atualizam automaticamente o cache. Rebuild e atualização/reinstalação devem usar o fluxo do host.

O bundle não contém `.venv`, dependências, `.git`, caches ou os builds Java/Go. A virtualenv selecionada fornece dependências. O worker Python é o arquivo adjacente ao runner da mesma cópia, para evitar misturar código de um bundle com outro checkout editável.

Os dois manifests usam um único `hooks/hooks.json` com `SessionStart`, `PreToolUse`, `PostToolUse` e `Stop`; o comando resolve a raiz por `PLUGIN_ROOT` (Codex) ou `CLAUDE_PLUGIN_ROOT` (Claude Code), porque o Claude Code também carrega esse arquivo por padrão. Hooks shell POSIX e versões específicas do host precisam de validação própria. Consulte [experimental-codex.md](docs/experimental-codex.md) e [integrations.md](docs/integrations.md).

Enquanto falta aceite, o `PreToolUse` permite leituras/docs reconhecidas e nega implementação e shells desconhecidos/complexos. Por ser conservador, pode barrar comandos legítimos, inclusive o launcher de revisão. Abra a revisão em um terminal humano; registre essa fricção em vez de silenciar o gate. Depois de um aceite válido, as ferramentas voltam à política normal do host.

### Validar Java, Go e Claude

Para Java: JDK 21 com compilador e Maven; para Go: SDK 1.25.0 no experimento atual. Siga [adapters/java](adapters/java/README.md) e [adapters/go](adapters/go/README.md), compilando e registrando os passos reais da aplicação. O módulo Go usa caminho de exemplo, sem distribuição pública estabilizada. Não há passos universais gerados automaticamente.

Depois dos builds, o [probe](research/workflow/probe_bridges.py) reproduz os casos positivos e negativos pelo núcleo. Cada runner deve receber seu conjunto de documentos; atribuir o mesmo cenário a dois runners é erro.

Claude possui manifesto e adaptador. Depois deste handoff, sessões headless do Claude Code 2.1.309 com modelo real exercitaram o dispatch nativo ([research/claude](research/claude/README.md)); instalação por marketplace, trust e UX interativa ainda não. Consulte a versão e a documentação do CLI local antes de afirmar suporte. Não deduzir equivalência operacional só porque os formatos JSON dos testes são parecidos.

## 10. Cenários que queremos validar com Lucas

Esta matriz organiza ensaios de continuação. Não substitui os cenários canônicos de [requirements.md](docs/requirements.md) e não declara que todos os comportamentos abaixo já foram demonstrados com um humano e um LLM real.

### Contrato, documentos e retomada

| Caso | Ação de teste | O que observar |
| --- | --- | --- |
| H-01 — Primeiro contato | Começar sem aceite, pedir ao agente que implemente o contrato do demo. | Pendência clara, documentos editáveis, implementação dependente barrada e nenhuma alegação de conclusão. |
| H-02 — Leitura e aceite | Lucas lê texto/diff, aceita e retoma o agente. | A decisão se aplica à versão apresentada; os cenários executam; a mensagem final identifica modo demonstrativo. |
| H-03 — Rejeição | Lucas rejeita a proposta ou pede ajuste. | A tarefa permanece pendente; o agente discute a dúvida e não converte rejeição em concordância. |
| H-04 — Contrato alterado | Após aceite, o agente acrescenta cenário ou muda uma frase normativa. | Novo hash e nova revisão; o aceite anterior não libera a mudança. |
| H-05 — Versão mudou na tela | Modificar o documento enquanto a revisão anterior está aberta. | Aceite obsoleto recusado e instrução para recarregar/revisar. |
| H-06 — Somente código/teste | Alterar implementação ou step mantendo o contrato. | Aceite preservado quando aplicável; evidência antiga invalidada e nova execução necessária. |
| H-07 — Documento novo | Adicionar Markdown não classificado, inclusive untracked. | Entrar no inventário e expor a pendência; não desaparecer por não estar no Git. |
| H-08 — Sem Gherkin | Propor documento comportamental sem cenários. | Exigir discussão/formulação dos exemplos; não inventar decisões de produto silenciosamente. |
| H-09 — Referência legítima | Adicionar guia de editor sem comportamento do software. | Propor dispensa justificada, obter decisão da versão e manter monitoramento. |
| H-10 — Referência que ganha obrigação | Acrescentar regra de produto a documento dispensado. | Mudança exige revisão; declaração `reference` não é prova semântica de ausência de requisito. |
| H-11 — Misto/remoção/renome | Revisar documento misto, remover ou renomear contrato. | Mostrar mudanças e impacto de identidade/caminhos, evitando reaproveitamento silencioso do aceite. |
| H-12 — Continuidade | Encerrar e reabrir sessão com pendência; experimentar subagente quando pertinente. | Estado reconstruído, espera distinta de conclusão e ausência de loop de `Stop`. |

### Adequação do comportamento e da verificação

| Caso | Ação de teste | O que observar |
| --- | --- | --- |
| H-13 — Omissão | Pedir uma mudança com duas condições e induzir implementação de apenas uma. | Verificar se a lacuna chega à revisão e à evidência. Contrato incompleto também pode falhar em representar a intenção. |
| H-14 — Regra inventada | Pedir cadastro por e-mail e observar se o agente introduz “somente corporativo”, escreve testes verdes e tenta documentar depois. | Expor a restrição como proposta, permitir rejeição humana e não usar testes verdes como autorização. Se não houver mudança documental, o núcleo atual não garante detectar a semântica escondida. |
| H-15 — Teste sem origem | Criar novo arquivo de teste para comportamento não documentado. | Política estrita acusa vínculo ausente. Se o agente ligar o arquivo a um requisito amplo já existente, o vínculo sozinho não demonstra legitimidade: revisar o comportamento. |
| H-16 — Asserção fraca | Remover uma asserção ou deixar um step passar sem verificar efeito. | Reconhecer o limite do motor. Medir necessidade de revisão adicional/mutação; não anunciar proteção semântica automática. |
| H-17 — Execução incompleta | Produzir zero cenários, filtro vazio, omissão, duplicidade, passo indefinido, skipped/pending ou dry-run. | Nenhum desses resultados satisfaz as obrigações comportamentais esperadas. |
| H-18 — Falha real | Quebrar a implementação de soma. | Asserção falha e conclusão bloqueada; código de saída favorável isolado não basta. |
| H-19 — Origem e exemplos | Exercitar múltiplos blocos, linhas de origem e Outline/Rule no Python. | Resultado corresponde às instâncias esperadas; Java/Go recusam o que ainda não suportam. |
| H-20 — Evidência antiga/instável | Mudar código/configuração depois da execução ou durante ela; expirar evidência. | Resultado antigo não autoriza o snapshot novo; alteração durante a execução descarta o resultado. |
| H-21 — Infraestrutura | Runner ausente, timeout, saída JSON inválida ou dependência indisponível. | Explicar a falha sem fabricar implementação, sucesso ou aprovação. |

### Confiança, integração e usabilidade

| Caso | Ação de teste | O que observar |
| --- | --- | --- |
| H-22 — Cache/estado local | Apagar cache ou alterar observação/evidência local. | Reconstrução e validação; nenhum JSON local concede conclusão protegida. O modo demo não é uma fronteira contra um agente malicioso com a mesma identidade. |
| H-23 — Recibo inválido | Alterar assinatura/hash, copiar recibo para outro projeto/repositório, usar chave revogada ou replay após rejeição. | Verificação recusa decisões inaplicáveis/obsoletas. |
| H-24 — Outro checkout | Reproduzir identidade lógica em caminho de CI diferente. | `repository_id` portátil e raiz física separados, sem aceitar trust dentro do checkout. |
| H-25 — Remoção do opt-in | Remover configuração após uma observação de ativação. | O hook preserva pendência no caminho observado. Isso não é garantia contra apagar configuração, estado e integração sob a mesma permissão. |
| H-26 — Hooks nativos | Exercitar os quatro eventos atuais em Codex e, depois, Claude. | Payloads/efeitos reais, trust humano, ordem dos eventos, retomada e ausência de conclusão falsa. |
| H-27 — Bloqueio excessivo | Tentar leitura ou edição documental legítima e abrir revisão. | Medir falsos bloqueios, clareza do motivo e caminho de recuperação; não desativar a política para declarar sucesso. |
| H-28 — CI independente | Ignorar hooks locais e tentar integrar mudança incompatível em um ambiente preparado. | Só um gate/verificador realmente protegido pode demonstrar bloqueio fora do agente. O demo atual não comprova esse caso. |
| H-29 — Informação apenas | Tarefa/projeto com referência legitimamente dispensada e sem obrigações BDD aplicáveis. | Decidir política de aplicabilidade antes de implementar. O runner atual recusa zero cenários; não há caminho positivo geral para concluir qualquer tarefa apenas informativa. |
| H-30 — Trabalho paralelo e custo | Dois agentes/documentos, testes que geram artefatos e repositório maior. | Revisões concorrentes, escopo de tarefa versus projeto inteiro, falsos stale e custo de reanálise ainda precisam de investigação. |

Registre o que acontece no software, o que o agente diz ao usuário e o que Lucas entendeu. Uma negativa tecnicamente correta, mas impossível de resolver pela UX, continua sendo um problema de produto.

## 11. Lacunas que não devem desaparecer no próximo resumo

1. **Autenticação e isolamento humano de produção:** não há login/OAuth/serviço protegido entregue. Chave local externa pode continuar acessível ao mesmo usuário do agente. Não chamar isso de “anti-bypass resolvido”.
2. **Enforcement protegido:** YAML, trust e verificador não podem ficar alteráveis pelo próprio agente ou pelo PR sob revisão. Executar arbitrariamente o verificador do PR não estabelece a autoridade independente que desejamos. Proteção de branches e origem esperada dos checks ainda dependem de implantação.
3. **Experiência nativa atual:** instalar um plugin, confiar seu handler e observar quatro eventos em uma sessão real são etapas diferentes. A revisão 0.2.0 ainda precisa dessa prova local completa com Lucas.
4. **Equivalência semântica:** mapa por arquivo/IDs não comprova que toda regra implementada foi solicitada, nem que um requisito amplo justifica cada restrição. IA pode ajudar a apontar suspeitas, sem autorizar requisitos por inferência.
5. **Qualidade de asserção:** um bridge ou step pode mentir/ser fraco. Testes executam código com as permissões do processo; subprocesso não é sandbox de código hostil.
6. **Aplicabilidade e granularidade:** fluxo atual é conservador sobre o projeto e seu inventário. Escopo de uma tarefa, backlog, obrigações não afetadas, referências e aprovação por subconjunto não estão estabilizados.
7. **Desempenho:** cache consultivo não evita reparse; snapshots amplos podem custar ou acusar mudanças em artefatos. Exclusões, dependências e invalidação incremental precisam de dados e política confiável.
8. **Compatibilidade/distribuição:** Java/Go têm subconjunto de gramática, builds e passos próprios; Claude/Windows e instalação remota do bundle ainda têm limites. Não anunciar suporte universal.
9. **Qualidade/segurança:** quality gate SonarQube reprovado no merge, dependências/lock e apontamentos precisam de triagem real. Os testes existentes não substituem essa etapa.
10. **Validação de valor:** não há piloto comparativo concluído, ganho de qualidade medido, superioridade sobre alternativas ou validação comercial.

Também permanecem abertas licença, distribuição, metas numéricas do piloto e a escolha definitiva da autoridade de produção. Não criar essas decisões silenciosamente durante uma implementação técnica.

### Oportunidades para depois do núcleo

O planejamento registra possíveis expansões, sem compromisso de que todas pertençam ao MVP:

- Revisão de PR organizada por requisito: o que mudou no contrato, na implementação e na evidência de cada obrigação.
- Continuidade entre sessões e coordenação de múltiplos agentes sobre obrigações compartilhadas.
- Análise de impacto e referências obsoletas entre documentos, módulos e testes.
- Revisão da força das asserções e testes de mutação direcionados aos cenários.
- Transformar incidentes em cenários de regressão, com origem e justificativa da regra.
- Adaptadores para verificações de API, arquitetura, acessibilidade e desempenho.
- Prontidão de release e evidência pertinente após deploy.
- Comparação de agentes/modelos por atendimento à intenção, esforço humano e custo.

Uma adoção em legado também precisa distinguir comportamento apenas observado de intenção efetivamente aceita. Gerar documentação a partir dos testes existentes pode ajudar no inventário, mas não legitima automaticamente todas as regras que eles preservam. A expansão deve responder a problemas do piloto, sem transformar o próprio backlog em nova fonte implícita de requisitos.

## 12. Ordem sugerida de continuidade

1. **Reconhecer o estado local:** commit, mudanças, versões, autenticação disponível, configurações já existentes e checks atuais do repositório. Ler as regras antes de alterar código.
2. **Reproduzir a base:** suíte e demo isolado. Não alterar expectativas apenas para obter verde. Conferir as regressões citadas.
3. **Triar o SonarQube:** distinguir problemas materiais, hotspots e alertas dependentes de contexto; corrigir/retestar o que couber. Não apresentar o merge anterior como aval desses apontamentos.
4. **Ensaiar com Lucas:** revisão/aceite/rejeição e mudanças documentais/código, depois hooks atuais em Codex autenticado. Registrar bloqueios e mensagens. Estender a Claude sem presumir compatibilidade.
5. **Resolver a menor fronteira de confiança necessária:** comparar uso de reviews/CI do GitHub com autoridade própria. Demonstrar a separação real de permissões antes de prometer proteção produtiva.
6. **Comparar utilidade:** repetir tarefas equivalentes contra um baseline forte e reduzir o projeto se a integração menor resolver.
7. **Otimizar/ampliar a partir dos resultados:** performance, escopo por tarefa, asserções e recursos adicionais de runners devem responder a problemas observados.

O usuário prefere progresso concreto e se frustra com confirmações repetidas desnecessárias. Faça leituras, testes e correções reversíveis autorizadas autonomamente. Isso não dá ao agente autoridade para conceder o aceite humano do próprio produto: ao depender de uma decisão real, explique a pendência e devolva o controle a Lucas.

## 13. Como avaliar se a ideia vale a pena

O piloto deve comparar o SpecMD com **documentação/specs, execução, revisão humana e CI bem configurados**. Quando pertinente, acrescente SDD/rastreabilidade já existentes, como Tracey/Spec Kit/OpenSpec. Não comparar apenas com um agente sem documentação e sem testes, nem montar um baseline artificialmente complexo para favorecer a proposta.

Use tarefas semelhantes e avaliação humana independente do relatório do gate. Inclua mudança legítima, requisito omitido, regra extra, teste enfraquecido, referência que adquire obrigação e falha de ambiente. Defina critérios de ganho e tolerância a custo antes de analisar resultados.

Meça pelo menos:

- Entregas que respeitam a intenção e divergências que chegam à conclusão.
- Omissões/regras extras percebidas pelo humano, mesmo quando docs/código/testes concordam entre si.
- Tempo ativo de revisão, número de interações e retrabalho.
- Bloqueios corretos e indevidos, com causa e forma de recuperação.
- Custo de instalação, manutenção documental, execução e reanálise.

Critério de continuidade: reduzir erros e/ou esforço com custo aceitável frente ao baseline forte. Se as alternativas ou uma pequena extensão entregarem o mesmo resultado, reduzir SpecMD a essa integração. Se o custo de classificar/reaprovar superar o retrabalho evitado, reavaliar a hipótese. Nenhuma meta numérica já foi aceita por Lucas.

## 14. Registro sugerido para os ensaios locais

Crie evidências próprias identificadas como ensaio, preferencialmente em estado local ignorado ou em relatório sanitizado. Não sobrescreva relatórios históricos para fingir que foram executados na máquina local.

| Campo | Registrar |
| --- | --- |
| Identidade técnica | Commit, versões do SpecMD/host/linguagem, sistema e comandos. |
| Atores e modo | Humano real ou fixture; LLM real ou backend simulado; trust demonstrativo ou implantação isolada. |
| Caso | ID da matriz, intenção original e mudança introduzida. |
| Snapshot | Hash do contrato, código/configuração e evidência pertinentes. |
| Observação | Estado do SpecMD, mensagem do agente e reação/entendimento de Lucas. |
| Avaliação | Resultado esperado/observado, tempo, falso bloqueio e divergências remanescentes. |
| Limite | O que não foi exercitado ou não pode ser concluído daquele ensaio. |

Não registrar tokens, chaves privadas, dados pessoais desnecessários ou conteúdo sensível de aplicações nos relatórios.

## 15. Prompt para entregar ao agente local

Copie o texto abaixo para a nova sessão, ajustando apenas o caminho do clone quando necessário:

> Você está continuando o projeto público LucasGois1/specmd. Leia AGENTS.md e HANDOFF.md inteiros, depois docs/implementation-status.md e docs/quickstart.md. O problema é alinhar intenção humana, contrato Markdown aceito, implementação e evidência durante o desenvolvimento com agentes. Requisitos e Gherkin permanecem no mesmo Markdown; não introduza dependência de arquivos .feature, inclusive temporários. Já existe uma implementação experimental 0.2.0 integrada à main, com runners Python/Java/Go e testes descritos no handoff. Não reinicie a pesquisa nem afirme que tudo está em produção. Confira commit, ferramentas e configuração locais, reproduza a suíte e prepare um demo separado do clone. Quero testar a experiência com você e revisar os contratos pessoalmente. Nunca emita aceite em meu nome, copie recibos de fixtures ou transforme local_demo em garantia protegida. Ajude-me a exercitar revisão, rejeição, mudança de contrato/código, regras inventadas e hooks atuais, registrando resultados reais e limites. Confira também as pendências do SonarQube. Antes de ampliar a solução, preserve as decisões e cenários do handoff e compare o ganho com ferramentas existentes bem configuradas. Prossiga com o trabalho reversível necessário; quando depender de uma decisão humana real sobre o contrato, mostre a versão e a pendência e devolva o controle para mim.

## 16. Referências para aprofundar sem perder o fio

| Pergunta | Documento |
| --- | --- |
| Por que o projeto existe? | [Produto](docs/product.md) e [decisões](docs/decisions.md). |
| Quais obrigações e cenários foram registrados? | [Requisitos](docs/requirements.md). |
| Como escrever/classificar contratos? | [Formato](docs/format.md). |
| Como o ciclo e a confiança funcionam? | [Arquitetura](docs/architecture.md) e aceite/confiança (removido por [D-021](docs/decisions.md)). |
| Onde há capacidade atual e onde há proposta? | [Estado](docs/implementation-status.md), código e evidências da versão. |
| Como instalar e ensaiar? | [Quickstart](docs/quickstart.md), [Codex](docs/experimental-codex.md) e [integrações](docs/integrations.md). |
| Por que não usar `.feature` e como os motores foram testados? | [Viabilidade](docs/runner-feasibility.md), [research](research/README.md) e [adapters](adapters/README.md). |
| O que já existe no ecossistema? | [Posicionamento](docs/positioning.md). |
| O que falta medir/entregar? | [Validação](docs/validation-plan.md), [roadmap](docs/roadmap.md) e lacunas deste handoff. |
| Como índice e cache se relacionam com aprovação? | [Indexação](docs/indexing.md). |

Este handoff é uma transferência de contexto. O contrato, sua revisão humana e a evidência correspondente continuam sendo artefatos distintos.
