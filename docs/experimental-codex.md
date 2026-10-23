---
specmd:
  schema: 1
  id: SMD-DOC-EXPERIMENTAL-CODEX
  kind: mixed
---

# Integração experimental com Codex

O adaptador apresenta ao agente o estado do fluxo SpecMD: documentação, revisão de uma versão, rastreabilidade e evidências de execução. O [quickstart](quickstart.md) permite experimentar esse ciclo primeiro pela CLI e pelo navegador.

O projeto continua experimental. `demo_passed` representa uma demonstração local, sem provar uma autoridade humana isolada. O caminho `passed` exige execução real fresca, confiança externa provisionada como protegida e política estrita. A implantação dessa separação depende do operador e do ambiente; veja [Aceite e confiança](approval-and-trust.md).

## Evidência de integração

O Codex CLI `0.163.0` reconheceu, instalou e habilitou `specmd@specmd-local`. Ensaios no executável real observaram `SessionStart`, `PostToolUse` e `Stop`, incluindo uma alteração por ferramenta e a atualização do hash observado. O backend forneceu respostas HTTP determinísticas simuladas. Isso comprova caminhos de dispatch e controle do host; não demonstra raciocínio ou cumprimento das instruções por um LLM.

As tentativas com o serviço de modelo configurado retornaram `401`. O bloqueio inicial de filesystem somente leitura foi superado quando o ambiente se tornou gravável. A concessão humana de confiança pela interface `/hooks` permanece uma experiência a validar separadamente.

As evidências em [research/codex](../research/codex/README.md) identificam fontes e bundles. Alterações posteriores no lifecycle exigem nova validação; o sucesso de um bundle antigo não comprova automaticamente a revisão atual. Consulte o [estado de implementação](implementation-status.md).

## Preparar e instalar

Use um clone da revisão desejada, Python 3.11 ou superior e uma instalação do Codex com estado de usuário gravável. A partir do clone:

```sh
SPECMD_SOURCE="$PWD"
python3 -m venv "$SPECMD_SOURCE/.venv"
"$SPECMD_SOURCE/.venv/bin/python" -m pip install -e "$SPECMD_SOURCE"
export SPECMD_PYTHON="$SPECMD_SOURCE/.venv/bin/python"
"$SPECMD_PYTHON" "$SPECMD_SOURCE/scripts/build_codex_plugin.py"
codex plugin marketplace add "$SPECMD_SOURCE"
codex plugin add specmd@specmd-local
```

O builder gera `dist/codex-plugin` por allowlist. A virtualenv original fornece as dependências e não é copiada para o pacote. Inicie o Codex a partir de um processo que herde `SPECMD_PYTHON`. Marketplace e instalação persistem estado do Codex. O manifesto do bundle identifica conteúdo, sem conceder confiança.

Depois de alterar a fonte, gere novamente o bundle e atualize a instalação pelo fluxo do host. A cópia instalada não acompanha automaticamente o clone.

## Revisar os handlers

Abra o Codex no projeto de teste e use `/hooks`. Confira pacote, comando, intérprete e eventos antes de conceder confiança pela interface normal. Inicie uma nova sessão para observar também o evento de início.

| Evento | Ação |
| --- | --- |
| `SessionStart` | Consultar o estado e fornecer contexto sobre pendências. |
| `PreToolUse` | Conferir a autorização antes das ferramentas cobertas pela política. |
| `PostToolUse` | Reavaliar o projeto e atualizar o estado observado após ferramentas. |
| `Stop` | Conferir a conclusão e traduzir o resultado para o protocolo do host. |

`PreToolUse` foi acrescentado nesta evolução e possui testes de protocolo; não integra as provas nativas anteriores dos três eventos. O alcance da política e os efeitos no host atual precisam de validação própria.

Enquanto falta aceite, a política local permite leituras e alterações documentais reconhecidas, e nega alterações de código e comandos desconhecidos. Shells combinados são recusados conservadoramente. Abra a revisão em um terminal humano seguindo o quickstart; não dependa de o agente lançar comandos de revisão enquanto o bloqueio estiver ativo. Um aceite válido devolve as ferramentas à política normal do host. Essa heurística pode produzir bloqueios indevidos e precisa ser avaliada no seu fluxo.

Confiar o handler autoriza executar a integração. Aceitar uma proposta SpecMD concorda com uma versão do contrato. Essas decisões têm registros e escopos diferentes. O agente deve aguardar a decisão contratual do usuário.

O hash nativo de trust pesquisado identifica a declaração normalizada do handler, incluindo o comando; não cobre necessariamente os bytes de todos os scripts chamados. Integridade do pacote, autoridade e CI exigem controles adicionais.

## Projeto e estados

O opt-in é `specmd.toml`. O schema 1 conserva o scanner inicial e não oferece um caminho de conclusão. O schema 2 configura identidade, runners, rastreabilidade e evidências. Use o projeto descartável do [quickstart](quickstart.md) antes de configurar um projeto existente.

O Markdown contém requisitos e Gherkin canônicos. A execução Python recebe blocos em memória e carrega steps reais; não cria `.feature`. Classificações informativas e justificativas também integram o snapshot sujeito a revisão. Markdown novo, alterado ou removido exige reconciliar essa versão.

O hook consulta o estado; a CLI fornece as operações explícitas de preparar revisão, abrir a interface, executar e auditar. O pacote não cria uma autoridade protegida silenciosamente.

Em `waiting_human_review`, o adaptador devolve o controle para a decisão do usuário. Para pendências corrigíveis, o primeiro `Stop` pode produzir feedback de bloqueio; se o host retornar com `stop_hook_active: true`, o adaptador devolve o controle para evitar repetição indefinida. A pendência permanece.

`.specmd/local/status.json` é uma observação reconstruível. `turn.completed` do Codex indica encerramento do turno; não substitui `status`, `may_complete`, `verification_mode` e `assurance` do SpecMD. Um resultado `demo_passed` deve ser apresentado como demonstração. Integração protegida usa `verify --require-real` com autoridade externa e execução fresca.

Hooks não impedem todo trabalho de um agente que também pode editar scripts, configuração ou autoridade. O CI precisa executar código de verificação confiável, com regras protegidas pelo operador. A existência de um workflow no repositório não comprova essa implantação.

## Cenários documentais

Os IDs abaixo preservam o guia anterior. Estes blocos específicos não possuem aceite humano nem ligação demonstrada a steps executados.

### SMD-PREFLIGHT-REQ-001 — Identificar alterações do contrato

Uma nova observação identifica mudanças nos bytes. O aceite anterior não autoriza automaticamente outra versão.

```gherkin
# language: pt
@SMD-PREFLIGHT-REQ-001
Funcionalidade: Identidade documental
  @SMD-PREFLIGHT-SCN-001
  Cenário: Alterar um documento anteriormente aceito
    Dado um projeto com contrato aceito para uma versão identificada
    Quando os bytes desse contrato forem alterados
    Então a versão contratual observada deve mudar
    E a nova versão deve aguardar revisão antes da conclusão
```

### SMD-PREFLIGHT-REQ-002 — Separar estrutura válida de aprovação

Classificação declarada e sintaxe válida não registram concordância humana.

```gherkin
# language: pt
@SMD-PREFLIGHT-REQ-002
Funcionalidade: Revisão da classificação
  @SMD-PREFLIGHT-SCN-002
  Cenário: Inspecionar uma referência ainda não aceita
    Dado um projeto com documento informativo e justificativa válidos
    E nenhuma decisão válida sobre a versão proposta
    Quando a estrutura documental for inspecionada
    Então o fluxo deve aguardar revisão humana
    E a conclusão deve permanecer sem autorização
```

### SMD-PREFLIGHT-REQ-003 — Devolver controle sem apagar pendências

O retorno ao usuário permite resolver a pendência, sem conceder aprovação.

```gherkin
# language: pt
@SMD-PREFLIGHT-REQ-003
Funcionalidade: Controle de parada
  @SMD-PREFLIGHT-SCN-003
  Cenário: Manter um bloqueio após feedback
    Dado um documento com pendências e uma primeira resposta de bloqueio
    Quando o host repetir a parada com o hook de parada já ativo
    Então o adaptador deve devolver o controle ao usuário
    E a tarefa deve continuar pendente
```
