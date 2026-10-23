# Preparação da integração local com Codex

Estado: investigação de interfaces, sem instalação do plugin SpecMD. O núcleo e o adaptador ainda não estão implementados. A autorização para testar não é evidência de um teste que ainda não ocorreu.

## Verificações executadas

O executável `/opt/codex/bin/codex` responde `codex-cli 0.163.0`. Foram executados apenas comandos de versão e ajuda, sem iniciar sessão com modelo, instalar plugin, alterar configuração global, aceitar hooks ou inspecionar arquivos de autenticação.

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

Esses comandos são interfaces confirmadas por ajuda, não comandos executados para instalar SpecMD. Não existe um marketplace ou pacote SpecMD pronto neste diretório. A ajuda não apresenta uma opção de escopo de instalação por projeto; o schema oficial descreve `marketplaces` como entradas de usuário.

## Hooks confirmados no schema da versão

O schema oficial `rust-v0.163.0` define estes eventos:

`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, `Stop`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PostCompact` e `Interrupt`.

Há configuração de handlers de comando e MCP; o schema também declara variantes prompt/agent. A presença no schema não demonstra que qualquer combinação foi exercitada neste ambiente. Para SpecMD, os primeiros candidatos são início de sessão, detecção após ferramentas e decisão de conclusão por `Stop`.

O manifesto oficial de plugin possui um componente `hooks`, com declaração inline ou referência a arquivos. A configuração expõe estado com `enabled` e `trusted_hash`. Um recorte do schema, com URL e blob de origem, está em [evidence/schema-excerpt.json](evidence/schema-excerpt.json).

## Trust e controle: fatos da fonte, ainda sem prova de runtime

A fonte oficial de `config_rules.rs` aceita alterações de estado do hook somente das camadas de usuário e de flags da sessão. Camadas de projeto e de plugin podem declarar hooks, mas não escrever esse estado do usuário.

Essa regra de camadas não estabelece, sozinha, uma autoridade fora do alcance do agente: se ele controla a configuração de usuário ou as flags da invocação, a separação precisa ser aplicada pelo ambiente. Nesta investigação não foi emitida confiança nem utilizado um mecanismo que a dispense.

Na implementação de `Stop`, um handler autorizado a aplicar efeitos de controle pode bloquear a parada por JSON com `decision: "block"` e uma razão não vazia. Existe também tratamento de saída `2` com razão no stderr. A própria fonte possui caso de teste indicando que saída `2` sem razão não bloqueia. Portanto, traduzir cegamente qualquer código não zero da futura CLI SpecMD em bloqueio seria incorreto.

A implementação de `PreToolUse` também possui resultado de bloqueio, incluindo decisão de permissão deny e tratamento de saída `2` com razão. Essas observações vêm de leitura da fonte fixada; nenhum hook foi ativado ou disparado nesta investigação.

O trust do hook não equivale ao aceite de requisitos do SpecMD. O primeiro autoriza executar uma integração; o segundo deve registrar concordância com uma versão específica do contrato. O adaptador precisa preservar essa diferença, permitir devolver o controle enquanto aguarda o usuário e manter a verificação protegida no CI como garantia independente.

## Próxima prova necessária

Antes de anunciar integração funcional, será necessário criar um pacote local real, definir a resposta do adaptador, escolher um ambiente de instalação autorizado e verificar:

1. Descoberta e instalação do pacote pelo marketplace local.
2. Revisão humana do trust sem usar mecanismos que o dispensem.
3. Disparo real de eventos com payloads e saídas registrados.
4. Bloqueio de conclusão com razão útil e espera humana sem loop.
5. Invalidação após mudanças e distinção entre trust do hook e aceite do contrato.

Nenhum desses cinco resultados é declarado concluído aqui.

## Fontes oficiais fixadas

- [Config schema, rust-v0.163.0](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/config.schema.json), blob `4aba1bab6cd2cbcc179a5de802731f2775c6bc88`.
- [Manifesto de plugin](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/plugin/src/manifest.rs), blob `30e6cda1734e3c7c991b3b6b7990d0c42e8b6b85`.
- [Camadas autorizadas de estado dos hooks](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/hooks/src/config_rules.rs), blob `050932ecbbff46ef87a66753496e8036d5ed47e5`.
- [Tratamento de Stop](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/hooks/src/events/stop.rs), blob `be2be9100e356427b298f24872113852eab3862a`.
- [Tratamento de PreToolUse](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/hooks/src/events/pre_tool_use.rs), blob `e57b823a1c8673ff1f5fe291b13e3274a1967a8d`.

Os blobs identificam as fontes retornadas pelo conector GitHub. A evidência local comprova a versão instalada e as interfaces de ajuda; a leitura de fonte comprova somente o desenho observado naquela revisão.
