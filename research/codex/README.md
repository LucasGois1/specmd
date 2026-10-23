# Preparação da integração local com Codex

Estado: investigação de interfaces e descoberta local do pacote SpecMD. O host reconheceu o pacote como disponível, mas este relatório ainda não comprova instalação, concessão de trust ou disparo de hooks em runtime. A autorização para testar não é evidência de um teste que ainda não ocorreu.

## Verificações executadas

O executável `/opt/codex/bin/codex` responde `codex-cli 0.163.0`. Foram executados comandos de versão, ajuda, descoberta de marketplace local, uma tentativa oficial de registrar o marketplace e tentativas de iniciar o runtime. Os caminhos de instalação e runtime falharam em filesystem somente leitura. Não há execução observada de modelo ou de hooks pelo host, instalação concluída, trust validado por dispatch ou inspeção de arquivos de autenticação nesta investigação.

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

## Tentativa oficial de instalação neste ambiente

Após autorização para instalar o pacote concreto, foi conferida a ausência de marketplace homônimo. `codex plugin marketplace list --json` retornou lista vazia, conforme [evidence/marketplace-before-install.json](evidence/marketplace-before-install.json).

O comando oficial `codex plugin marketplace add /workspace/specmd --json` retornou código `1`:

```text
failed to create marketplace install directory /run/codex-environment/codex-home/.tmp/marketplaces: Read-only file system (os error 30)
```

A saída está em [evidence/marketplace-add-attempt.json](evidence/marketplace-add-attempt.json). O registro do marketplace não foi concluído e o comando de instalação do plugin não foi executado após essa falha de pré-requisito. Não foi sobrescrita configuração existente, concedido trust ou remapeado o diretório de usuário. A disponibilidade mostrada pelo comando de descoberta com overrides não deve ser apresentada como uma instalação concluída.

## Hooks confirmados no schema da versão

O schema oficial `rust-v0.163.0` define estes eventos:

`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, `Stop`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PostCompact` e `Interrupt`.

Há configuração de handlers de comando e MCP; o schema também declara variantes prompt/agent. A presença no schema não demonstra que qualquer combinação foi exercitada neste ambiente. Para SpecMD, os primeiros candidatos são início de sessão, detecção após ferramentas e decisão de conclusão por `Stop`.

O manifesto oficial de plugin possui um componente `hooks`, com declaração inline ou referência a arquivos. A configuração expõe estado com `enabled` e `trusted_hash`. Um recorte do schema, com URL e blob de origem, está em [evidence/schema-excerpt.json](evidence/schema-excerpt.json).

## Trust e controle: fatos da fonte, ainda sem prova de runtime

A fonte oficial de `config_rules.rs` aceita alterações de estado do hook somente das camadas de usuário e de flags da sessão. Camadas de projeto e de plugin podem declarar hooks, mas não escrever esse estado do usuário.

Essa regra de camadas não estabelece, sozinha, uma autoridade fora do alcance do agente: se ele controla a configuração de usuário ou as flags da invocação, a separação precisa ser aplicada pelo ambiente. A tentativa de runtime descrita abaixo solicitou confiança somente para dois handlers concretos por flags da sessão, como ensaio autorizado; a inicialização falhou antes de haver confirmação de dispatch. Não foi utilizada flag de bypass nem apresentada uma ação de UI humana como realizada.

Na implementação de `Stop`, um handler autorizado a aplicar efeitos de controle pode bloquear a parada por JSON com `decision: "block"` e uma razão não vazia. Existe também tratamento de saída `2` com razão no stderr. A própria fonte possui caso de teste indicando que saída `2` sem razão não bloqueia. Portanto, traduzir cegamente qualquer código não zero da futura CLI SpecMD em bloqueio seria incorreto.

A implementação de `PreToolUse` também possui resultado de bloqueio, incluindo decisão de permissão deny e tratamento de saída `2` com razão. Essas observações vêm de leitura da fonte fixada; nenhum hook foi ativado ou disparado nesta investigação.

A TUI oficial possui o comando `/hooks`, descrito como gerenciamento de hooks de ciclo de vida. A interação dessa tela e a concessão humana de confiança não foram exercitadas. Um hash de trust pode ser específico do handler; atribuí-lo por configuração continua sendo um ato de confiança, não uma operação que o plugin pode realizar em nome do humano.

Na fonte inspecionada, o hash de trust é calculado sobre a identidade normalizada da configuração do handler — evento, matcher e comando — e não sobre os bytes de todo script externo chamado. Alterar um script mantendo a declaração do comando pode preservar essa identidade. A integridade do pacote e o aceite do contrato exigem controles próprios; não podem ser atribuídos automaticamente ao mecanismo de trust do Codex.

O trust do hook não equivale ao aceite de requisitos do SpecMD. O primeiro autoriza executar uma integração; o segundo deve registrar concordância com uma versão específica do contrato. O adaptador precisa preservar essa diferença, permitir devolver o controle enquanto aguarda o usuário e manter a verificação protegida no CI como garantia independente.

## Tentativas de runtime: bloqueio antes de hooks ou modelo

O núcleo e o adaptador local já têm implementação experimental. O ensaio de dispatch pelo Codex instalado foi tentado, mas **não conseguiu inicializar o host neste ambiente**. Isso é diferente de um teste de hook que passou ou falhou após executar seu conteúdo.

Primeiro, o harness [probe_runtime.py](probe_runtime.py) tentou iniciar `codex app-server --stdio` e usar somente `initialize` e `hooks/list`, sem criar thread ou turno. A primeira tentativa retornou erro ao inicializar SQLite sob `/run/codex-environment/codex-home`. O schema da versão permite `sqlite_home` e `log_dir`; apontar apenas esses dados operacionais para `/tmp`, sem alterar `HOME`, `CODEX_HOME` ou a localização da autenticação, ainda resultou em `Read-only file system (os error 30)` antes da resposta a `initialize`.

Foi então tentado `codex exec` com `--ignore-user-config`, `--ephemeral`, `--json`, sandbox `read-only`, fixture sem segredos e apenas os handlers síncronos `SessionStart` e `Stop` apontando para `/workspace/specmd/.venv/bin/python /workspace/specmd/scripts/codex_hook.py`. `--ignore-user-config` deixa de carregar a configuração de usuário, mas preserva o Codex home para autenticação; `--ephemeral` não torna todos os arquivos operacionais opcionais.

Esse comando retornou código `1`:

```text
Error: failed to initialize in-process app-server client: Read-only file system (os error 30)
```

O comando completo, stderr e limites da observação estão em [runtime-startup-attempt.json](evidence/runtime-startup-attempt.json). As tentativas de descoberta estão registradas em [runtime-discovery-failure.json](evidence/runtime-discovery-failure.json).

Como `hooks/list` não ficou disponível, os dois hashes candidatos da tentativa de `exec` foram calculados a partir do algoritmo da fonte oficial fixada: identidade normalizada do evento e handler, conversão para TOML/JSON ordenado e SHA-256. A proveniência está explícita na evidência: **esses valores não vieram de uma resposta de `hooks/list` e não foram validados por um dispatch bem-sucedido**. Foram solicitados somente por `-c hooks.state.<key>.trusted_hash`, sem persistir configuração global ou conceder aceite contratual.

A fonte do app-server também contém uma exigência de escrita no diretório original: [lib.rs:787](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server/src/lib.rs#L787) resolve `installation_id`, e [installation_id.rs:19–30](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/installation_id.rs#L19-L30) abre esse arquivo com leitura, escrita e criação. Isso mostra por que redirecionar somente SQLite não estabelece compatibilidade com um Codex home somente leitura. A última mensagem de erro não identifica o syscall exato que falhou; não se atribui a ela um rastreamento de filesystem que não foi obtido.

As tentativas foram interrompidas nesse limite. Não foram alterados permissões, mounts, credenciais, `HOME` ou `CODEX_HOME`. Todos os processos iniciados por esse harness foram aguardados e encerrados. **Não há payload nativo de `SessionStart`/`Stop`, ciclo real de retry ou resposta de modelo comprovados por essas tentativas.** Os testes offline do adaptador são uma evidência separada e não substituem esse resultado ausente.

### Como completar o ensaio em uma máquina com Codex home gravável

O harness contém duas etapas deliberadamente separadas:

```sh
# Lista somente os dois handlers concretos do probe; não executa hooks nem modelo.
.venv/bin/python research/codex/probe_runtime.py --discover

# Após revisar o comando, os scripts e os hashes de runtime-discovery.json,
# e autorizar explicitamente esses handlers para o ensaio:
.venv/bin/python research/codex/probe_runtime.py --run \
  --reviewed-hooks research/codex/evidence/runtime-discovery.json
```

O modo de descoberta exige que o app-server possa iniciar. Não existe neste ambiente um `runtime-discovery.json` bem-sucedido, portanto o segundo comando não foi executado pelo harness aqui. Ele inicia duas sessões reais e deve ser usado somente após essa revisão e autorização. Não altera configuração global nem usa bypass de trust; passa confiança restrita aos handlers revisados por flags da invocação e mantém `may_complete=false` como estado do SpecMD.

Para registrar a forma dos payloads sem armazenar mensagens ou transcrições privadas, esse probe usa [record_hook.py](record_hook.py), que encaminha a chamada ao mesmo `specmd.codex.handle_hook` do pacote. Esse comando instrumentado difere do comando direto usado na tentativa de startup acima e precisa de sua própria revisão. Os hashes de fontes são conferidos antes de solicitar confiança. O modo de execução pretende verificar `blocked → feedback → stop_hook_active=true → devolver controle` e `waiting_human_review → devolver controle` nos [fixtures](fixtures/runtime), mas **esses resultados de runtime continuam não obtidos**.

Pela fonte, `decision: "block"` com razão não vazia injeta continuação para o agente. Já `continue: false` encerra esse processamento; não aprova a tarefa. O adaptador persiste o estado pendente separadamente porque o término de um turno do Codex não é uma autorização de conclusão do SpecMD. As regras e o guard contra loop foram testados offline; a interação da sessão real precisa ser completada no ambiente gravável.

## Próxima prova necessária

O pacote e o adaptador experimental existem. Antes de anunciar integração funcional no host, será necessário escolher um ambiente de instalação gravável e verificar:

1. Instalação do pacote pelo marketplace local, além da descoberta já comprovada.
2. Revisão humana do trust sem usar mecanismos que o dispensem.
3. Disparo real de eventos com payloads e saídas registrados.
4. Bloqueio de conclusão com razão útil e espera humana sem loop.
5. Invalidação após mudanças e distinção entre trust do hook e aceite do contrato.

Essas cinco etapas de integração continuam pendentes neste relatório. A descoberta de disponibilidade foi comprovada separadamente.

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
