# Preparação da integração local com Codex

Estado: plugin instalado pelo Codex CLI real e dispatch de seus hooks demonstrado com backend local determinístico. **Não houve resposta de modelo LLM real nesse ensaio.** A tentativa com o serviço configurado falhou por autenticação; trust humano pela interface continua sendo uma prova separada.

| Camada | Evidência atual |
| --- | --- |
| Núcleo e adaptador | [49 testes unitários](evidence/unit-tests.json) passaram. |
| CLI/bootstrap | Os mesmos 11 casos passaram na [fonte](evidence/preflight-integration.json) e no [bundle](evidence/bundle-integration.json). |
| Marketplace/plugin | [Instalação real](evidence/installed-plugin.json), `installed: true`, `enabled: true`, versão `0.1.0`, três hooks listados. |
| Trust do ensaio | Confirmado por listagem nativa, restrito a flags da sessão; trust persistente inalterado. |
| Controle nativo do host | [Dois casos passaram](evidence/native-fixture-results.json) com respostas HTTP locais simuladas e handlers instrumentados por flags. |
| Dispatch do plugin instalado | [Três casos passaram](evidence/installed-dispatch.json) usando o pacote do cache, sem handlers inline; incluem alteração por ferramenta real e respostas HTTP simuladas. |
| Serviço de modelo configurado | [Tentativa real](evidence/runtime-results.json) retornou `401`; ciclo de parada não foi completado. |
| `/hooks` humano e aceite contratual | Não realizados; não podem ser inferidos do trust de sessão. |

## Verificações executadas

O executável `/opt/codex/bin/codex` responde `codex-cli 0.163.0`. Foram executados comandos de ajuda, descoberta, instalação e runtime. As primeiras tentativas falharam com filesystem somente leitura; depois de o ambiente tornar-se gravável, o marketplace e o plugin foram instalados. A cronologia abaixo preserva as falhas iniciais e distingue a execução do host com respostas simuladas da tentativa com serviço de modelo real. Não foram inspecionados arquivos de autenticação.

Reprodução da coleta local:

```sh
python3 research/codex/probe_cli.py
```

Os cinco comandos e suas saídas estão em [evidence/cli-help.json](evidence/cli-help.json). O aviso de PATH aliases em filesystem somente leitura foi mantido na evidência; ele não impediu os comandos de ajuda. O caminho e a permissão de uma instalação futura precisam ser verificados no ambiente onde ela ocorrerá.

## Instalação suportada pelo CLI

O CLI possui `plugin` e aceita um marketplace local ou Git:

```text
codex plugin marketplace add <SOURCE>
codex plugin add <PLUGIN>@<MARKETPLACE>
```

`SOURCE` pode ser um caminho local, `owner/repo[@ref]`, URL HTTPS Git ou URL SSH Git. O comando de marketplace oferece `--ref`, `--sparse` e saída JSON. O comando de instalação aceita também `PLUGIN --marketplace MARKETPLACE`.

A ajuda não apresenta uma opção de escopo de instalação por projeto; o schema oficial descreve `marketplaces` como entradas de usuário. A fonte do instalador utiliza o store em Codex home e chama `set_user_plugin_enabled`; um perfil de configuração não redireciona automaticamente esse store.

## Pacote local e prova de descoberta

O pacote inicial usa os caminhos reconhecidos pelo host:

- [Marketplace local](../../.agents/plugins/marketplace.json): `specmd-local`, com source local `./dist/codex-plugin` apontando para um bundle gerado.
- [Manifesto do plugin](../../.codex-plugin/plugin.json): `specmd`, versão `0.1.0`, hooks em `./hooks/hooks.json`.
- [Declaração dos hooks](../../hooks/hooks.json): handlers síncronos `SessionStart`, `PostToolUse` e `Stop`, com timeout de 30 segundos.

Os handlers chamam o script do pacote por `PLUGIN_ROOT`, variável efetivamente injetada pelo host. A fonte também fornece o alias `CLAUDE_PLUGIN_ROOT`; não foi encontrada uma variável `CODEX_PLUGIN_ROOT` nesse caminho. O intérprete usa `SPECMD_PYTHON` quando definido e `python3` como padrão. Os comandos dessa embalagem inicial usam sintaxe de shell POSIX.

Antes de registrar ou instalar o marketplace, gere o bundle a partir das fontes canônicas:

```sh
python3 scripts/build_codex_plugin.py
```

O builder inclui somente `.codex-plugin/plugin.json`, `hooks/hooks.json`, `scripts/codex_hook.py`, `src/specmd/*.py` e `pyproject.toml`. Ele adiciona um manifesto SHA-256 de build, sem conceder aceite ou trust. O resultado fica em `dist/codex-plugin`, ignorado pelo Git. Não há segunda cópia de fontes mantida no repositório.

Esse limite de conteúdo é necessário: o instalador `0.163.0` chama `copy_dir_recursive`, que percorre diretórios e copia arquivos sem consultar `.gitignore`. Apontar o marketplace para a raiz copiaria também `.venv`, `.git` e artefatos de pesquisa; links simbólicos não são copiados por essa função, o que também poderia deixar uma venv copiada incompleta. O bundle evita esse custo e não contém dependências, caches ou arquivos Git.

No build observado foram incluídos nove arquivos, totalizando 29.058 bytes de fontes, além do manifesto. O fingerprint e os hashes individuais estão na evidência de descoberta. O fingerprint identifica o conteúdo do bundle, não uma aprovação humana.

`SPECMD_PYTHON` deve apontar para o intérprete absoluto do ambiente original de desenvolvimento, externo ao bundle e ao cache do plugin. A venv pode ficar na raiz do clone local, desde que não seja copiada para o pacote. O script instalado carrega o `src` do próprio bundle; o intérprete externo fornece suas dependências.

Como `dist/` é gerado e não versionado, registrar este repositório diretamente como marketplace Git remoto não produz, sozinho, um pacote instalável. O fluxo validado é clone local, instalação das dependências, build do bundle e registro do marketplace local. Distribuição remota com bundle publicado será uma etapa própria.

A descoberta foi executada pelo próprio Codex, com configuração somente da invocação:

```sh
codex -c 'marketplaces.specmd-local.source_type="local"' -c 'marketplaces.specmd-local.source="/workspace/specmd"' plugin list --marketplace specmd-local --available --json
```

O resultado foi código `0`, plugin `specmd@specmd-local`, versão `0.1.0`, source `/workspace/specmd/dist/codex-plugin`, `installed: false` e `enabled: false`. A saída está em [evidence/local-marketplace-discovery.json](evidence/local-marketplace-discovery.json), incluindo hashes do builder e do bundle. Isso comprova reconhecimento do marketplace e do manifesto pelo host, sem comprovar execução do script ou instalação.

Para instalar em um ambiente de usuário com configuração gravável, as interfaces suportadas são `codex plugin marketplace add /caminho/do/specmd` e `codex plugin add specmd@specmd-local`. Esses passos persistem estado de usuário. Não foi redirecionado `HOME` ou `CODEX_HOME` para contornar restrições do ambiente.

## Histórico inicial: instalação impedida pelo filesystem

Após autorização para instalar o pacote concreto, foi conferida a ausência de marketplace homônimo. `codex plugin marketplace list --json` retornou lista vazia, conforme [evidence/marketplace-before-install.json](evidence/marketplace-before-install.json).

O comando oficial `codex plugin marketplace add /workspace/specmd --json` retornou código `1`:

```text
failed to create marketplace install directory /run/codex-environment/codex-home/.tmp/marketplaces: Read-only file system (os error 30)
```

A saída está em [evidence/marketplace-add-attempt.json](evidence/marketplace-add-attempt.json). Naquela tentativa, o registro não foi concluído e a instalação do plugin não prosseguiu. Não foi remapeado o diretório de usuário. A disponibilidade da descoberta com overrides era uma evidência distinta de instalação.

## Instalação efetiva e listagem de hooks

Com o ambiente posteriormente gravável, os comandos oficiais de marketplace e plugin foram executados com sucesso. [installed-plugin.json](evidence/installed-plugin.json) registra `specmd@specmd-local` instalado e habilitado, versão `0.1.0`, com a cópia instalada correspondendo às fontes canônicas.

A listagem nativa reconheceu os três handlers `SessionStart`, `PostToolUse` e `Stop`, inicialmente não confiáveis. Flags restritas à sessão tornaram os handlers revisados confiáveis na listagem, sem alterar trust persistente. Isso comprova instalação e reconhecimento; ainda não comprova seu dispatch nem interação humana pela tela `/hooks`. `HOME` e `CODEX_HOME` foram preservados.

## Hooks confirmados no schema da versão

O schema oficial `rust-v0.163.0` define estes eventos:

`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, `Stop`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PostCompact` e `Interrupt`.

Há configuração de handlers de comando e MCP; o schema também declara variantes prompt/agent. A presença no schema não demonstra que qualquer combinação foi exercitada neste ambiente. Para SpecMD, os primeiros candidatos são início de sessão, detecção após ferramentas e decisão de conclusão por `Stop`.

O manifesto oficial de plugin possui um componente `hooks`, com declaração inline ou referência a arquivos. A configuração expõe estado com `enabled` e `trusted_hash`. Um recorte do schema, com URL e blob de origem, está em [evidence/schema-excerpt.json](evidence/schema-excerpt.json).

## Trust e controle: fonte e escopo dos ensaios

A fonte oficial de `config_rules.rs` aceita alterações de estado do hook somente das camadas de usuário e de flags da sessão. Camadas de projeto e de plugin podem declarar hooks, mas não escrever esse estado do usuário.

Essa regra de camadas não estabelece, sozinha, uma autoridade fora do alcance do agente: se ele controla a configuração de usuário ou as flags da invocação, a separação precisa ser aplicada pelo ambiente. Os ensaios posteriores solicitaram confiança restrita aos handlers concretos e conferiram `trustStatus` pela listagem nativa. Não foi utilizada flag de bypass nem apresentada uma ação de UI humana como realizada.

Na implementação de `Stop`, um handler autorizado a aplicar efeitos de controle pode bloquear a parada por JSON com `decision: "block"` e uma razão não vazia. Existe também tratamento de saída `2` com razão no stderr. A própria fonte possui caso de teste indicando que saída `2` sem razão não bloqueia. Portanto, traduzir cegamente qualquer código não zero da futura CLI SpecMD em bloqueio seria incorreto.

A implementação de `PreToolUse` também possui resultado de bloqueio, incluindo decisão de permissão deny e tratamento de saída `2` com razão. Esse evento foi estudado na fonte, mas não foi exercitado pelo SpecMD neste ensaio. A execução observada de `SessionStart` e `Stop` é descrita separadamente abaixo.

A TUI oficial possui o comando `/hooks`, descrito como gerenciamento de hooks de ciclo de vida. A interação dessa tela e a concessão humana de confiança não foram exercitadas. Um hash de trust pode ser específico do handler; atribuí-lo por configuração continua sendo um ato de confiança, não uma operação que o plugin pode realizar em nome do humano.

Na fonte inspecionada, o hash de trust é calculado sobre a identidade normalizada da configuração do handler — evento, matcher e comando — e não sobre os bytes de todo script externo chamado. Alterar um script mantendo a declaração do comando pode preservar essa identidade. A integridade do pacote e o aceite do contrato exigem controles próprios; não podem ser atribuídos automaticamente ao mecanismo de trust do Codex.

O trust do hook não equivale ao aceite de requisitos do SpecMD. O primeiro autoriza executar uma integração; o segundo deve registrar concordância com uma versão específica do contrato. O adaptador precisa preservar essa diferença, permitir devolver o controle enquanto aguarda o usuário e manter a verificação protegida no CI como garantia independente.

## Histórico inicial: runtime impedido pelo filesystem

As primeiras tentativas de `codex app-server --stdio` e `codex exec` não conseguiram inicializar o host por filesystem somente leitura. As evidências originais permanecem em [runtime-discovery-failure.json](evidence/runtime-discovery-failure.json) e [runtime-startup-attempt.json](evidence/runtime-startup-attempt.json). Essas tentativas não produziram dispatch de hooks nem respostas de modelo.

Foi tentado redirecionar somente SQLite e logs operacionais, sem alterar `HOME`, `CODEX_HOME` ou a localização da autenticação, mas isso não eliminou a necessidade de escrita no diretório original. A fonte também resolve um arquivo `installation_id` com escrita; a mensagem observada não identifica o syscall exato que falhou. Os hashes candidatos daquela primeira tentativa vieram da leitura da fonte, não de uma resposta nativa de `hooks/list`; a proveniência continua registrada no JSON histórico.

Depois de o ambiente tornar-se gravável, a descoberta nativa e os ensaios abaixo foram possíveis. As falhas antigas não descrevem o estado atual e não foram reescritas como resultados positivos.

## Descoberta nativa e tentativa com serviço de modelo real

O harness [probe_runtime.py](probe_runtime.py) passou a receber uma listagem real de `hooks/list`, sem criar thread ou turno na etapa de descoberta. A resposta usa uma lista plana com metadados camelCase. Os comandos e hashes concretos estão em [runtime-discovery.json](evidence/runtime-discovery.json); esse arquivo não concede trust por si só.

O ensaio autorizado usou confiança restrita à sessão e a conferiu pela listagem nativa. O harness transmite o mapa de estado de trust de forma que preserve as chaves completas retornadas pelo host; não depende de interpretar essas chaves como caminhos TOML pontuados. A configuração persistente de trust não foi alterada.

Na tentativa com o serviço de modelo configurado, o host iniciou a thread e executou `SessionStart`, mas recebeu `401 Unauthorized` com mensagem de que a autenticação não pôde ser interpretada. Não houve resposta de modelo nem chamada de `Stop`. [runtime-results.json](evidence/runtime-results.json) registra falha das expectativas do ensaio; [runtime-hook-events.jsonl](evidence/runtime-hook-events.jsonl) registra o evento inicial observado, sem copiar transcrições privadas.

Isso é uma falha de autenticação da tentativa real, não evidência de que o ciclo do hook passou com um LLM. Não foram lidos ou substituídos arquivos de autenticação para contorná-la.

O harness mantém descoberta e execução separadas:

```sh
# Descobre os handlers concretos sem executar hooks ou modelo.
.venv/bin/python research/codex/probe_runtime.py --discover

# Após revisar e autorizar esses handlers específicos para o ensaio:
.venv/bin/python research/codex/probe_runtime.py --run \
  --reviewed-hooks research/codex/evidence/runtime-discovery.json
```

A execução depende de um serviço de modelo funcional e pode gerar uso cobrado. O guia normal de instalação continua pedindo revisão pela interface `/hooks`; as flags restritas deste harness são um mecanismo explícito de ensaio, sem representar uma ação de UI humana realizada.

## Controle do host com respostas determinísticas

O [probe_native_fixture.py](probe_native_fixture.py) iniciou o **executável real do Codex** com um endpoint HTTP local que devolve eventos da Responses API e texto fixo. Não houve inferência de modelo. O endpoint registrou somente metadados necessários, sem inspecionar cabeçalhos de autenticação ou armazenar o conteúdo dos requests.

O primeiro ensaio usou handlers instrumentados por flags da sessão, encaminhando payloads nativos ao mesmo adaptador SpecMD. A instrumentação permitiu contar os eventos, como registrado em [native-fixture-results.json](evidence/native-fixture-results.json) e [native-fixture-hook-events.jsonl](evidence/native-fixture-hook-events.jsonl):

| Caso | `SessionStart` | `Stop` | Requisições ao backend simulado | Estado final |
| --- | --- | --- | --- | --- |
| `blocked` | 1 | 2 | 2 | `blocked`, `may_complete: false` |
| `waiting` | 1 | 1 | 1 | `waiting_human_review`, `may_complete: false` |

O bloqueio solicitou uma continuação; a segunda parada devolveu o controle. A espera humana devolveu o controle na primeira parada. Terminar o turno do Codex não liberou a tarefa no estado do SpecMD. Os fixtures permaneceram inalterados, exceto pelo cache observado.

O host emitiu aviso de ausência de metadados para o identificador fictício `specmd-fixture` e uso de metadados de fallback. Esse aviso está na evidência; não representa descoberta nem execução de um modelo LLM real.

## Dispatch do plugin instalado

Um segundo ensaio, [probe_installed_dispatch.py](probe_installed_dispatch.py), usou o pacote **instalado no cache do Codex**, sem declarar handlers inline. A listagem reconheceu os três hooks do plugin e confirmou a confiança somente da sessão. Os hashes do cache correspondiam às fontes canônicas.

[installed-dispatch.json](evidence/installed-dispatch.json) registra sucesso nos três casos. Nos casos de bloqueio e espera, a primeira requisição continha o marcador de contexto do `SessionStart`; houve duas requisições no bloqueio e uma na espera humana. O último evento salvo pelo próprio plugin foi `Stop`, e o estado continuou com `may_complete: false`. O host retornou código `0`, que significa término do ensaio, não aprovação contratual.

No terceiro caso, o backend simulado emitiu uma chamada de função e o Codex executou a ferramenta real `exec_command` para alterar um contrato em diretório temporário descartável. Antes da resposta seguinte, `PostToolUse` registrou `modified: contract.md` e o novo hash. A parada final manteve `waiting_human_review` e `may_complete: false`. Assim, os três eventos declarados foram exercitados pelo plugin instalado, sem atribuir raciocínio de modelo às respostas fixas.

O backend continuou sendo local e determinístico. Esse resultado comprova a conexão entre instalação, dispatch nativo e adaptador para os caminhos exercitados; não demonstra que um LLM interpretou as instruções, que a UX de trust foi usada ou que houve aceite humano de contrato. A instalação persistiu marketplace/plugin habilitado; a confiança dos hooks foi somente de sessão, sem alteração do trust persistente.

## Provas que permanecem pendentes

- Trust humano pela tela `/hooks`, distinto da confiança restrita ao ensaio.
- Fluxo completo com o serviço de modelo real, impedido nesta tentativa pelo `401`.
- Experiência de retomada e correção de documentos em trabalho real.
- Autoridade humana separada, execução BDD integrada e gate protegido de CI, que não existem neste incremento.

A instalação real e os testes controlados não removem essas limitações. A evidência deve permanecer separada por camada, em vez de usar “funcionou no Codex” como substituto de todas elas.

## Fontes oficiais fixadas

- [Config schema, rust-v0.163.0](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/config.schema.json), blob `4aba1bab6cd2cbcc179a5de802731f2775c6bc88`.
- [Manifesto de plugin](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/plugin/src/manifest.rs), blob `30e6cda1734e3c7c991b3b6b7990d0c42e8b6b85`.
- [Camadas autorizadas de estado dos hooks](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/hooks/src/config_rules.rs), blob `050932ecbbff46ef87a66753496e8036d5ed47e5`.
- [Tratamento de Stop](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/hooks/src/events/stop.rs), blob `be2be9100e356427b298f24872113852eab3862a`.
- [Tratamento de PreToolUse](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/hooks/src/events/pre_tool_use.rs), blob `e57b823a1c8673ff1f5fe291b13e3274a1967a8d`.
- [Resolução do marketplace e source local](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core-plugins/src/marketplace.rs), blob `2199fe4e1e937e239304e0bf26ab56b793f8409c`.
- [Instalador e ativação de usuário](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core-plugins/src/manager.rs), blob `d4411b50da9f459bd8ba267b9c785247c131312d`.
- [Cópia recursiva do pacote, sem filtro de Git](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core-plugins/src/store.rs#L736-L757), blob `087eae6d7b89fa230b3b0c44fcb5706000542cdd`.
- [Variáveis do plugin e descoberta/trust dos handlers](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/hooks/src/engine/discovery.rs), blob `0c5a28ef35ef0fb54c7f0b99c7f23a680af18ae2`.
- [Comando TUI `/hooks`](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/tui/src/slash_command.rs), blob `afb372bb7b9bc4e6f32ee82d6f86c32b4c40b97d`.
- [Algoritmo de fingerprint](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/config/src/fingerprint.rs#L58-L72) e [identidade normalizada dos hooks](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/hooks/src/engine/discovery.rs#L768-L793).
- [Efeito de Stop na continuação do turno](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/session/turn.rs#L737-L766).
- [Listagem de hooks sem executar handlers](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/hooks/src/registry.rs#L304-L318).
- [UI de confiança por handler](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/tui/src/bottom_pane/hooks_browser_view.rs#L243-L258) e [persistência de confiança na configuração de usuário](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/tui/src/hooks_rpc.rs#L58-L93).

Os blobs identificam as fontes retornadas pelo conector GitHub. A evidência local comprova a versão instalada e as interfaces de ajuda; a leitura de fonte comprova somente o desenho observado naquela revisão.
