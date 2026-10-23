# Integrações com agentes e CI

> Estado: existe um primeiro preflight experimental Python e pacote Codex em validação. `init`, `inventory` e `check --stage completion` já possuem implementação local; ela não concede aceite nem executa cenários e nunca libera conclusão de projeto ativo. O restante deste documento descreve o fluxo futuro, incluindo autoridade humana, execução integrada e gate protegido. O suporte de runtime do adaptador ainda precisa de evidência por produto e versão.

O [guia experimental do Codex](experimental-codex.md) separa instalação por clone local e build, opt-in, comandos atuais, trust via UX e pendências de validação. O marketplace usa o pacote por allowlist em `dist/codex-plugin`, sem copiar dependências e dados locais do clone.

O SpecMD deve se integrar ao fluxo de desenvolvimento sem duplicar suas regras em cada agente. Um núcleo comum verifica documentos, aceites e evidências; adaptadores traduzem eventos e respostas de cada plataforma.

## Componentes

| Componente | Responsabilidade |
| --- | --- |
| Núcleo/CLI | Inventário, hashes, classificação declarada, validação de Gherkin, aceites, vínculos e decisão da etapa. |
| Adaptador do agente | Acionar o núcleo nos eventos disponíveis, apresentar pendências e aplicar as ações permitidas pelo ambiente. |
| Interface de revisão | Apresentar versões e diffs, receber decisões humanas autenticadas e registrar o aceite protegido. |
| Adaptador de execução | Consumir os blocos Gherkin do Markdown e associar resultados aos cenários e snapshots. |
| Gate de CI | Revalidar o candidato à integração com configuração e autoridade protegidas. |

A arquitetura é detalhada em [Arquitetura](architecture.md). A fronteira de autoridade está em [Aceite e confiança](approval-and-trust.md).

O adaptador do agente pode solicitar revisão e consultar seu estado. Ele não recebe autoridade para aprovar em nome do usuário.

## Entrada canônica de execução

O contrato é o Markdown. A integração deve localizar os blocos Gherkin nesse documento, preservar IDs e origem e encaminhar uma representação executável ao runner.

O projeto não deve exigir arquivos `.feature` mantidos pelo desenvolvedor, nem adotá-los como etapa temporária obrigatória. A viabilidade de consumir AST/representação em memória e executar os steps no ecossistema escolhido é um spike inicial. O Cucumber não será tratado como leitor nativo de Markdown sem comprovação.

Se um runner não permitir essa integração, será necessário avaliar outro adaptador ou abordagem compatível com o requisito. Introduzir geração de `.feature` como dependência altera o desenho e exige nova decisão do usuário; não é um fallback implícito.

## Eventos desejados

Os pontos abaixo são eventos lógicos do fluxo. Não representam nomes de hooks confirmados em nenhuma plataforma.

| Momento | Ação desejada | Custo preferido |
| --- | --- | --- |
| Início ou retomada da sessão | Reconciliar inventário, identificar novas versões e apresentar pendências. | Descoberta e conferência de identidade; reutilizar análise válida. |
| Depois de alterações relevantes | Atualizar hashes, invalidar resultados afetados e informar contratos pendentes. | Incremental, agrupando alterações próximas. |
| Antes de implementar comportamento ainda não aceito | Conferir o contrato aplicável e pausar o trabalho dependente quando a política exigir. | Consulta de estado e validação de aceite. |
| Antes de declarar tarefa concluída | Conferir classificação, aceite e evidências atuais dos requisitos aplicáveis. | Verificações necessárias para aquela conclusão. |
| Antes de integrar no CI | Reconciliar o snapshot candidato e aplicar a regra protegida. | Verificação autoritativa; não confiar no cache local do agente. |

Executar todos os testes após qualquer edição de texto produziria interrupções e custo desnecessários. Os hooks frequentes devem priorizar detecção de mudança; a execução mais cara segue a política da etapa e a validade das evidências.

## Claude Code e Codex

O núcleo deve ser independente da integração escolhida. A primeira implementação pode validar um adaptador e depois adicionar o segundo.

O usuário solicitou preparar testes locais no Codex. A [investigação do CLI 0.163.0](../research/codex/README.md) confirmou sua presença e interfaces de ajuda e examinou fontes oficiais de instalação, eventos e trust. Essa investigação antecede o preflight atual e não comprova, por si só, sua instalação ou execução em sessão. A tentativa de instalação persistente no ambiente de nuvem encontrou configuração de usuário somente leitura; validação de runtime é uma etapa separada.

O pacote atual declara `SessionStart`, `PostToolUse` e `Stop`. O adaptador apresenta contexto nos dois primeiros; no `Stop`, pede uma correção para problemas locais e depois devolve o controle para evitar ciclos, ou devolve imediatamente quando aguarda revisão humana. Em nenhum desses caminhos emite aceite ou autoriza conclusão. O guia distingue essa implementação da comprovação de efeitos no host real.

Antes de afirmar suporte, cada adaptador precisa registrar e validar:

- Produto, versão e forma de instalação suportados.
- Eventos realmente disponíveis e ferramentas que os disparam.
- Dados recebidos sobre sessão, tarefa, arquivos e chamadas de ferramentas.
- Formato de resposta, códigos de retorno e possibilidades reais de bloqueio.
- Tratamento de timeouts, cancelamento, retomada e falha do verificador.
- Comportamento diante de alterações feitas por shell ou por ferramentas externas.
- Capacidade de distinguir espera por usuário, encerramento da interação e conclusão de tarefa.
- Permissões necessárias e quais configurações o próprio agente pode modificar.

Até essa validação, o funcionamento desses itens no fluxo SpecMD permanece **não verificado** para as duas plataformas. A inspeção estática e os comandos de ajuda do Codex não substituem uma prova em sessão real. Não se presume equivalência entre hooks ou bloqueio absoluto de sessão.

Uma matriz de capacidades deve orientar a implementação: por exemplo, uma plataforma pode permitir feedback após escrita, mas não impedir toda edição futura. O adaptador deve expor essa diferença sem prometer uma garantia que seu ambiente não aplica.

## CLI experimental e etapas futuras

O primeiro incremento implementa:

```text
specmd init
specmd inventory --format json
specmd check --stage completion --format json
```

`init` cria somente o opt-in `specmd.toml` com `schema = 1`. `inventory` produz inspeção, sem conceder conclusão; código `0` dessa operação não significa aprovação. `check` retorna `1` para projeto ativo bloqueado ou aguardando revisão e `2` para erro/inativo. Não existe um caminho `passed` de conclusão nesse incremento.

As etapas abaixo continuam propostas e não são aceitas pela CLI atual:

```text
specmd check --stage implementation --format json
specmd check --stage integration --format json
```

O protocolo completo abaixo é uma proposta; a implementação local é um subconjunto, descrito no [guia](experimental-codex.md). Os campos e códigos devem permanecer versionados antes de se tornar contrato estável de integração.

O núcleo precisa distinguir a etapa verificada do estado da tarefa. Uma checagem de inventário bem-sucedida, por exemplo, não declara a implementação concluída.

Exemplo proposto de resultado:

```json
{
  "protocol_version": 1,
  "stage": "completion",
  "status": "waiting_human_review",
  "may_complete": false,
  "findings": [
    {
      "kind": "document_classification_pending",
      "document_id": "DOC-042",
      "path": "docs/cancelamento.md",
      "message": "A classificação e os cenários desta versão aguardam aceite humano."
    }
  ]
}
```

Estados propostos:

| Estado | Interpretação |
| --- | --- |
| `passed` | A etapa solicitada atende às regras verificadas. |
| `blocked` | Há obrigações não atendidas; o agente pode ter trabalho corretivo a executar. |
| `waiting_human_review` | A decisão exigida pertence ao humano; devolver o controle sem marcar conclusão. |
| `error` | A ferramenta não conseguiu determinar o resultado por falha técnica ou configuração inválida. |

Códigos de saída propostos: `0` para etapa permitida, `1` para bloqueio de política ou obrigação e `2` para erro técnico/configuração. O JSON distingue espera humana de outros bloqueios. Cada adaptador traduz esses resultados para o protocolo real de sua plataforma; não deve presumir que esses códigos têm a mesma interpretação em um hook.

Não concluir uma verificação é diferente de aprová-la. Falha, timeout ou ausência de resultado não devem se transformar silenciosamente em sucesso na etapa protegida.

## Interação de classificação e aceite

Ao encontrar um Markdown novo ou alterado, o agente deve apresentar uma proposta compreensível:

1. Indicar o que o documento descreve e qual classificação sugere.
2. Identificar possíveis requisitos e incertezas para discutir com o usuário.
3. Produzir cenários Gherkin para as obrigações combinadas, no próprio Markdown.
4. Apresentar o conteúdo exato e o diff sujeito a aceite.
5. Solicitar a decisão pelo canal humano protegido e aguardar seu resultado.

O usuário revisa comportamentos e exemplos; não precisa saber escrever Gherkin. A revisão pode agrupar um conjunto coerente de mudanças para reduzir interrupções, mantendo clara a versão aprovada de cada escopo.

Classificar como informativo também requer aceite. O agente pode escrever a justificativa, mas não autoisentar o documento. Documento misto exige identificar suas partes comportamentais. Regras e sintaxe propostas estão em [Formato documental](format.md).

A interface deve mostrar adições, alterações e remoções de obrigações e cenários, permitir acesso ao texto completo e ao diff original e distinguir decisões novas de comportamentos já estabelecidos. Um resumo gerado pelo agente não substitui o conteúdo que o usuário está aprovando.

## Esperar não é concluir

`waiting_human_review` deve ser uma parada válida do trabalho. O agente pode explicar a proposta e encerrar sua interação para aguardar uma resposta, preservando a tarefa como pendente.

Um hook que insiste em continuar até a aprovação, mas impede devolver o controle ao usuário, cria um ciclo sem saída. O adaptador precisa separar:

- Devolver o controle para uma decisão humana.
- Suspender o trabalho dependente de contrato pendente.
- Declarar a tarefa concluída.
- Integrar a mudança no repositório.

O alcance da pausa — tarefa, atividades dependentes ou projeto inteiro — é uma política explícita. Nenhum desses modos deve ser inferido silenciosamente pelo adaptador.

## Limites de autoridade e CI

Hooks locais oferecem feedback durante o trabalho e aplicam as restrições que o ambiente permite. Se o agente pode editar o hook, sua configuração e as mesmas credenciais usadas para aceitar, esse mecanismo local não fornece separação de autoridade.

O gate protegido de integração deve verificar o snapshot efetivo, o contrato aceito, a identidade do aprovador autorizado e as evidências correspondentes. Não pode aceitar como prova apenas um JSON produzido pelo agente ou o estado de seu índice local.

Alterações nos steps, fixtures, runner e tratamento de cenários ignorados também precisam permanecer visíveis. Uma implementação de teste enfraquecida pode produzir um resultado verde sem mudar o Markdown. Essa limitação deve orientar a revisão e o plano de validação.

## Critérios para validar um adaptador

Um adaptador só deve ser declarado suportado após demonstrar, em ambiente reproduzível:

- Detecção de Markdown novo, alterado e removido no escopo.
- Invalidação do aceite correto após mudança do contrato.
- Dispensa de Gherkin somente com classificação humana válida.
- Espera humana sem loop de encerramento ou falsa conclusão.
- Evidência atual associada ao contrato e ao código corretos.
- Mensagem útil diante de cenário ausente, falha de execução e erro técnico.
- Ausência de dependência obrigatória de arquivos `.feature`.
- Aplicação do gate de CI independentemente do resultado local.

Os cenários detalhados estão em [Requisitos](requirements.md) e [Plano de validação](validation-plan.md). A ordem de implementação está em [Roadmap](roadmap.md).
