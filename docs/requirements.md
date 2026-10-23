# Requisitos e cenários do SpecMD

**Estado do artefato:** rascunho; implementação inexistente; aceite humano desta versão pendente. Os cenários abaixo são exemplos propostos de critérios de aceite, não testes executados nem evidências de conformidade.

“Origem confirmada” indica uma direção solicitada na conversa. “Desenho proposto” identifica uma forma sugerida de realizá-la. Nenhuma dessas etiquetas representa aceite autenticado da redação deste arquivo.

Os IDs `SMD-REQ-*` e `SMD-SCN-*` são estáveis. Uma alteração de conteúdo mantém o ID quando preserva a identidade da obrigação, mas cria uma nova versão sujeita à revisão. A sintaxe dos metadados e o executor continuam pendentes de validação; ver [format.md](format.md) e [roadmap.md](roadmap.md).

## SMD-REQ-001 — Markdown canônico e execução sem `.feature`

**Origem confirmada.** Requisitos e cenários devem residir nos Markdown canônicos, sem exigir arquivos `.feature` no projeto, em diretórios temporários ou como entrada necessária do executor.

**Desenho proposto:** consumir os blocos Gherkin por parser/AST e adaptação em memória. A convenção de cercas de código é uma hipótese; a compatibilidade com Markdown with Gherkin oficial deve ser avaliada antes de estabilizar o formato. A restrição de fonte canônica não exclui `.feature.md`, que continua sendo Markdown.

**Critérios de aceite:** editar o cenário em um `.md` altera a próxima entrada de execução; não há uma cópia canônica concorrente; a ausência de `.feature` não impede descoberta nem execução. A escolha de parser, AST e runner é um desenho pendente de spike; não se afirma suporte nativo de Cucumber.

```gherkin
# language: pt
@SMD-REQ-001
Funcionalidade: Cenários canônicos em Markdown
  @SMD-SCN-001
  Cenário: Executar o conteúdo do Markdown sem arquivo de feature
    Dado um projeto com um cenário válido em um bloco Gherkin de um arquivo Markdown
    E nenhum arquivo com extensão ".feature"
    Quando o adaptador de execução validado consumir esse cenário
    Então o cenário deve ser interpretado a partir do Markdown
    E nenhum arquivo ".feature" deve ser necessário ou gerado como pré-requisito
    E o resultado deve preservar o identificador do cenário e a origem no Markdown
```

## SMD-REQ-002 — Inventário e descoberta de novos documentos

**Origem confirmada.** Manter um inventário dos Markdown cobertos pela política, com caminho, identidade de conteúdo e situação de classificação. Detectar adições, alterações, remoções e renomes, inclusive arquivos novos ainda não rastreados pelo Git quando pertencem ao snapshot avaliado.

**Critérios de aceite:** um arquivo novo não herda dispensa por estar ausente de um índice antigo; a reconciliação corrige eventos de watcher perdidos; arquivos fora do escopo são identificados pela política, não por uma aprovação implícita.

```gherkin
# language: pt
@SMD-REQ-002
Funcionalidade: Inventário de Markdown
  @SMD-SCN-002
  Cenário: Descobrir um Markdown criado depois da última análise
    Dado um inventário previamente atualizado
    E um novo arquivo Markdown dentro do escopo protegido
    Quando o sistema reconciliar o inventário com o snapshot atual
    Então o arquivo deve ser incluído como pendente de classificação ou revisão
    E uma ausência anterior no índice não deve dispensar sua avaliação
```

## SMD-REQ-003 — Classificação e dispensa aceitas por humano

**Origem confirmada.** Distinguir documentos comportamentais, informativos e mistos. O agente pode sugerir a classificação; dispensar cenários para conteúdo informativo requer aceite humano da classificação vinculado ao conteúdo, caminho e escopo avaliados.

**Critérios de aceite:** o agente não consegue se autoisentar; conteúdo informativo aceito pode deixar de passar por análise semântica repetida enquanto permanecer válido; alterações criam uma pendência de revisão. “Informativo” não equivale a exclusão do inventário.

```gherkin
# language: pt
@SMD-REQ-003
Funcionalidade: Classificação humana dos documentos
  @SMD-SCN-003
  Cenário: O agente propõe uma dispensa de cenários
    Dado um Markdown ainda sem classificação aceita
    Quando o agente o classificar como informativo
    Então essa classificação deve permanecer como proposta
    E a dispensa de cenários deve aguardar aceite humano autenticado

  @SMD-SCN-004
  Cenário: Alterar um documento informativo previamente aceito
    Dado um Markdown informativo com dispensa aceita para seu conteúdo atual
    Quando seu conteúdo protegido for alterado
    Então a dispensa anterior não deve autorizar automaticamente a nova versão
    E o arquivo deve continuar monitorado no inventário
```

## SMD-REQ-004 — Documentos mistos e ausência de cenários

**Origem confirmada.** Permitir explicações e obrigações no mesmo Markdown. A revisão deve identificar quais trechos estabelecem comportamento e quais são informativos. Detectar ausência de cenários como motivo de avaliação, sem afirmar automaticamente que qualquer Markdown precisa de Gherkin.

**Critérios de aceite:** o sistema oferece ao humano revisar cenários propostos ou aceitar a classificação informativa; um bloco Gherkin isolado não comprova cobertura de todos os requisitos do documento. O mecanismo exato de delimitação de trechos é desenho proposto.

```gherkin
# language: pt
@SMD-REQ-004
Funcionalidade: Conteúdo misto e revisão assistida
  @SMD-SCN-005
  Cenário: Revisar um documento com explicação e regra de negócio
    Dado um Markdown com explicações e uma obrigação comportamental sem cenário associado
    Quando essa possível lacuna for identificada
    Então o agente pode propor um cenário no próprio Markdown
    E o humano deve poder revisar a obrigação e a classificação dos trechos
    E a existência de outro cenário no documento não deve ser usada como prova de cobertura completa
```

## SMD-REQ-005 — Origem das obrigações e inferências não autorizadas

**Origem confirmada.** Relacionar mudanças relevantes de comportamento a requisitos ou instruções reconhecidas. Inferências e novas regras sugeridas pelo agente precisam ser apresentadas como propostas; criar código, testes e documentação concordantes não autoriza a regra.

**Critérios de aceite:** o relatório distingue origem reconhecida de proposta pendente; restrições novas não são consideradas aceitas por terem testes; decisões internas sem efeito no contrato observável não exigem um novo requisito apenas por existir um teste unitário. A detecção automática de todos os comportamentos não é prometida.

```gherkin
# language: pt
@SMD-REQ-005
Funcionalidade: Proveniência do comportamento implementado
  @SMD-SCN-006
  Cenário: Introduzir uma restrição de cadastro não solicitada
    Dado um requisito de cadastro com e-mail sem restrição a domínio corporativo
    Quando o agente implementar essa restrição e escrever testes para ela
    Então a restrição deve ser apresentada como mudança de contrato sem aceite reconhecido
    E documentá-la posteriormente não deve produzir um aceite humano
    E a tarefa não deve ser considerada conforme apenas porque os testes passam
```

## SMD-REQ-006 — Identidade determinística de conteúdo e escopo

**Origem confirmada.** Identificar a versão protegida por hash determinístico considerando conteúdo, caminhos e escopo. Detectar adição, remoção, alteração e rename dos documentos pertinentes.

**Desenho proposto:** manifesto de caminhos e hashes de arquivos, com serialização e ordenação estáveis. Algoritmo, tratamento de normalização, symlinks e seleção de bytes de referência serão definidos em [approval-and-trust.md](approval-and-trust.md) e [indexing.md](indexing.md).

**Critérios de aceite:** o mesmo snapshot e a mesma política geram a mesma identidade; uma alteração protegida não reutiliza o aceite da identidade anterior; o conjunto de arquivos selecionado integra a identidade, evitando ignorar adições e remoções.

```gherkin
# language: pt
@SMD-REQ-006
Funcionalidade: Identidade da versão protegida
  @SMD-SCN-007
  Cenário: Invalidar o aceite após mudança protegida
    Dado um conjunto de documentos e caminhos aceito para um hash específico
    Quando um documento protegido for alterado, adicionado, removido ou renomeado
    Então o sistema deve reconhecer uma identidade protegida diferente
    E o aceite anterior não deve aprovar essa nova identidade
```

## SMD-REQ-007 — Aceite autenticado fora da autoridade do agente

**Origem confirmada.** Exigir aceite humano autenticado para a versão específica de documentação, cenários, classificação ou dispensa no escopo protegido. Vincular a decisão a hash, caminhos e escopo. O agente não pode emitir o aceite nem alterar seu registro confiável.

**Critérios de aceite:** o registro identifica o humano autenticado e a versão aceita; campos editáveis no repositório e autor Git não bastam para demonstrar aceite. O canal de identidade e eventual assinatura são pendências; nenhuma chave, assinatura ou integração já existente é presumida. A garantia depende de permissões separadas, conforme [approval-and-trust.md](approval-and-trust.md).

```gherkin
# language: pt
@SMD-REQ-007
Funcionalidade: Aceite humano verificável
  @SMD-SCN-008
  Cenário: Rejeitar uma autoaprovação escrita pelo agente
    Dado um contrato sem aceite no canal confiável
    Quando o agente adicionar ao repositório um campo que declare o contrato aprovado
    Então o verificador não deve reconhecer esse campo como aceite humano
    E deve exigir uma decisão autenticada para o hash, os caminhos e o escopo atuais
```

## SMD-REQ-008 — Revisão de criação e mudanças de documentação e cenários

**Origem confirmada.** Toda criação ou alteração de docs e cenários dentro do escopo protegido exige aceite da versão resultante, inclusive especificações redigidas durante a conversa com o usuário. Modificar cenários, removê-los ou enfraquecer uma obrigação não preserva automaticamente o aceite anterior.

**Critérios de aceite:** participação na escrita não é tratada como aprovação automática do artefato final; o diff permite identificar a mudança antes de aceitar; uma edição não é dispensada automaticamente por o agente considerá-la editorial.

```gherkin
# language: pt
@SMD-REQ-008
Funcionalidade: Versionamento do contrato aceito
  @SMD-SCN-009
  Cenário: Redigir a primeira especificação com o usuário
    Dado que o usuário e o agente discutiram os requisitos de uma funcionalidade
    Quando o agente redigir o Markdown e os cenários dessa discussão
    Então a primeira versão deve ser apresentada para aceite humano
    E a conversa anterior não deve ser convertida em aceite autenticado automático dessa redação

  @SMD-SCN-010
  Cenário: Enfraquecer um cenário previamente aceito
    Dado um cenário aceito para uma versão de um contrato
    Quando o agente remover uma condição desse cenário
    Então a mudança deve aparecer no diff submetido ao humano
    E o aceite da versão anterior não deve autorizar a versão enfraquecida
```

## SMD-REQ-009 — Espera explícita por revisão humana

**Origem confirmada.** Representar a necessidade de decisão humana como `waiting_human_review`. O agente deve receber a pendência e o que precisa ser revisado, sem poder resolvê-la por autodeclaração, repetição da execução ou timeout.

**Critérios de aceite:** enquanto não chegar uma decisão válida para a versão atual, o escopo bloqueado não pode ser marcado como concluído. O início ou a continuação da implementação comportamental dependente deve permanecer suspenso conforme a política de bloqueio. Análise, discussão e preparação da proposta podem continuar quando permitidas. O adaptador deve demonstrar quais ações consegue impedir e declarar limitações do host, sem alegar bloqueio efetivo quando oferece somente orientação.

```gherkin
# language: pt
@SMD-REQ-009
Funcionalidade: Espera por decisão humana
  @SMD-SCN-011
  Cenário: Evitar conclusão enquanto o aceite está pendente
    Dado um contrato atual que requer aceite humano
    E nenhuma decisão válida para essa versão
    Quando o agente solicitar a conclusão da tarefa
    Então o resultado deve indicar "waiting_human_review"
    E deve apontar a versão e as decisões pendentes
    E aguardar ou repetir a solicitação não deve produzir aprovação

  @SMD-SCN-024
  Cenário: Suspender implementação dependente de um contrato pendente
    Dado um contrato aguardando aceite para uma mudança de comportamento
    E um ambiente com bloqueio pré-implementação demonstrado e habilitado para esse escopo
    Quando o agente solicitar iniciar ou continuar a implementação dependente
    Então a ação deve permanecer bloqueada até existir aceite válido da versão atual
    E o agente deve poder devolver o controle ao usuário para a revisão
    E preparar a proposta não deve ser apresentado como implementar um contrato aceito
```

## SMD-REQ-010 — Gate de alinhamento entre contrato, código e evidência

**Origem confirmada.** Bloquear a conclusão protegida quando faltarem aceite atual, implementação dos requisitos aplicáveis ou evidências exigidas. O gate deve considerar o escopo da tarefa e as obrigações de preservação pertinentes, sem assumir que a tarefa precisa implementar o backlog inteiro.

**Critérios de aceite:** não permitir conclusão apenas pela existência de Markdown ou de testes; informar as obrigações pendentes por ID; distinguir pendência humana de falha de verificação. A seleção de aplicabilidade ainda é uma questão de desenho em [architecture.md](architecture.md).

```gherkin
# language: pt
@SMD-REQ-010
Funcionalidade: Conclusão condicionada ao contrato aplicável
  @SMD-SCN-012
  Cenário: Bloquear uma obrigação aceita sem evidência atual
    Dado um requisito aplicável com contrato aceito
    E nenhuma evidência atual para seu cenário exigido
    Quando o gate avaliar a conclusão da tarefa
    Então deve bloquear essa conclusão
    E identificar o requisito e a evidência ausente
```

## SMD-REQ-011 — Evidências atuais e verificações incompletas

**Origem confirmada.** Relacionar resultados ao snapshot do código, à versão dos cenários e à configuração de verificação relevante. Um cenário apenas presente, ignorado, pendente, indefinido ou sem resultado válido não conta como cenário comprovado.

**Critérios de aceite:** alterar código relevante exige evidência válida para a nova revisão; resultados antigos não são reaproveitados como atuais sem uma política de validade verificável; o relatório informa condições exercitadas e limitações. O formato da evidência é desenho proposto.

```gherkin
# language: pt
@SMD-REQ-011
Funcionalidade: Validade das evidências
  @SMD-SCN-013
  Cenário: Recusar um resultado pertencente a outro snapshot
    Dado um cenário aprovado que passou em uma revisão anterior do código
    Quando o gate avaliar uma revisão diferente sem evidência válida para ela
    Então o resultado anterior não deve satisfazer a obrigação atual

  @SMD-SCN-014
  Cenário: Não contabilizar cenário ignorado como sucesso
    Dado um cenário exigido pelo contrato aplicável
    Quando o executor registrar esse cenário como ignorado ou pendente
    Então o gate não deve contabilizá-lo como verificado com sucesso
    E deve apresentar a situação real no relatório
```

## SMD-REQ-012 — Snapshot coerente no aceite e na conclusão

**Desenho proposto para cumprir o vínculo de versão confirmado.** A avaliação final deve usar um snapshot identificável, sem misturar documentos aceitos de uma revisão com código, política ou evidências de outra sem validação explícita.

**Critérios de aceite:** mudanças durante ou depois da avaliação são reconhecidas antes da integração protegida; o resultado indica qual snapshot foi avaliado. Mecanismo exato de fixação e integração com Git permanece pendente.

```gherkin
# language: pt
@SMD-REQ-012
Funcionalidade: Consistência da avaliação final
  @SMD-SCN-015
  Cenário: Alterar o contrato após uma avaliação favorável
    Dado um resultado favorável para um snapshot específico
    Quando o contrato protegido mudar antes da integração
    Então aquele resultado não deve autorizar o novo snapshot
    E o gate deve exigir nova avaliação e o aceite aplicável à versão modificada
```

## SMD-REQ-013 — Política, exclusões e mecanismos de verificação protegidos

**Origem confirmada para evitar bypass; desenho operacional pendente.** Excluir arquivos, mudar seleção de escopo ou alterar a regra de aceite não pode ser uma forma de o agente dispensar a própria revisão. Steps e configuração de execução que afetam a força da evidência precisam de versionamento e controles adequados.

**Critérios de aceite:** mudar uma exclusão protegida cria uma pendência, em vez de autorizar silenciosamente arquivos removidos do escopo; o agente não pode desabilitar o gate confiável. O controle das definições de steps não equivale a afirmar que a qualidade de toda asserção é comprovada automaticamente.

```gherkin
# language: pt
@SMD-REQ-013
Funcionalidade: Resistência à autoisenção
  @SMD-SCN-016
  Cenário: Excluir da política um contrato alterado
    Dado um documento protegido com mudança pendente de aceite
    Quando o agente alterar a política para excluir esse documento
    Então a mudança de política deve ser tratada como pendência protegida
    E o documento não deve se tornar aceito por causa dessa exclusão não autorizada
```

## SMD-REQ-014 — Auditoria e revisão legível

**Origem confirmada.** Manter trilha entre snapshots propostos, alterações, decisões humanas e resultados. Mostrar diff e permitir distinguir proponente, autor declarado no Git e identidade efetivamente autenticada do aprovador.

**Critérios de aceite:** o humano consegue recuperar a versão que aceitou e compará-la à proposta atual; remover conteúdo é visível; um resumo de IA não substitui acesso ao diff exato. Persistência e política de retenção são pendentes.

```gherkin
# language: pt
@SMD-REQ-014
Funcionalidade: Histórico de contrato e decisões
  @SMD-SCN-017
  Cenário: Revisar a alteração de uma obrigação
    Dado um contrato com uma versão aceita e uma versão proposta diferente
    Quando o humano abrir a revisão
    Então deve poder consultar o diff entre essas versões
    E identificar a versão, o escopo e a decisão autenticada anterior
    E o autor declarado no Git não deve ser apresentado como prova de aceite
```

## SMD-REQ-015 — Índice incremental e cache separados do aceite

**Origem confirmada.** Reutilizar classificações e resultados válidos para evitar análise semântica repetida, sem transformar cache em aprovação. Documentos informativos aceitos continuam sujeitos à detecção de mudança.

**Desenho proposto:** chave de cache considera conteúdo, contexto/caminho relevante, versão do analisador, política e dependências conhecidas. Uma alteração relevante invalida os itens afetados; uma reconciliação final impede confiar apenas em watcher ou `mtime`. Ver [indexing.md](indexing.md).

**Critérios de aceite:** conteúdo inalterado e ainda válido pode reutilizar análise; novos arquivos e alterações de política não passam por usar um índice antigo; uma entrada de cache sem aceite continua sem aceite.

```gherkin
# language: pt
@SMD-REQ-015
Funcionalidade: Reutilização segura de análise
  @SMD-SCN-018
  Cenário: Reutilizar a análise de um documento informativo aceito
    Dado um Markdown informativo aceito e uma análise em cache válida para seu contexto atual
    Quando uma nova reconciliação não encontrar mudanças relevantes
    Então o sistema pode evitar nova análise semântica desse arquivo
    E deve continuar verificando sua identidade no inventário

  @SMD-SCN-019
  Cenário: Não confundir análise em cache com aceite
    Dado um Markdown com análise em cache e sem aceite humano válido
    Quando o gate avaliar esse documento
    Então a existência do cache não deve satisfazer a exigência de aceite

  @SMD-SCN-025
  Cenário: Invalidar análise após mudança de política ou dependência
    Dado um resultado incremental em cache para um documento inalterado
    Quando mudar a política ou uma dependência pertinente àquela análise
    Então o resultado afetado deve ser invalidado
    E a nova análise deve corresponder à análise completa do mesmo snapshot e política
    E a igualdade do texto do documento não deve preservar uma validade fora de contexto

  @SMD-SCN-026
  Cenário: Reconciliar o inventário após um evento perdido
    Dado um inventário em cache e um watcher que não recebeu uma alteração protegida
    Quando ocorrer a reconciliação de fechamento
    Então o inventário deve refletir os documentos efetivos do snapshot
    E a decisão deve corresponder à avaliação completa do mesmo snapshot e política
    E o evento perdido não deve conceder aceite nem ocultar a alteração
```

## SMD-REQ-016 — IA heurística com decisões explícitas

**Origem confirmada.** Usar IA para sugerir classificação, cenários e possíveis divergências, distinguindo essas sugestões dos checks determinísticos e das decisões humanas.

**Critérios de aceite:** o sistema não declara cobertura semântica completa por um parecer do modelo; não cria aceite ou dispensa automaticamente; uma inferência relevante aparece como proposta identificável. Parâmetros e critérios de qualidade da análise devem ser avaliados em [validation-plan.md](validation-plan.md).

```gherkin
# language: pt
@SMD-REQ-016
Funcionalidade: Limites da análise semântica
  @SMD-SCN-020
  Cenário: Uma sugestão do modelo não substitui o humano
    Dado um modelo que sugere que um documento não contém obrigações
    E nenhuma classificação aceita para a versão atual
    Quando o sistema processar a sugestão
    Então deve apresentá-la como sugestão de classificação
    E não deve emitir uma dispensa humana nem declarar cobertura completa
```

## SMD-REQ-017 — CLI e adaptadores de ciclo de vida

**Origem confirmada.** Disponibilizar a mesma política por uma CLI reutilizável e por adaptadores de agentes, com Claude Code e Codex como alvos iniciais a investigar. Não presumir hooks idênticos nem anunciar suporte antes da validação.

**Desenho proposto:** saída estruturada e diagnósticos legíveis; adaptadores traduzem eventos do host em operações do núcleo. Nomes de comandos, códigos e eventos serão definidos após o spike de [integrations.md](integrations.md).

**Critérios de aceite:** uma mesma avaliação de snapshot e política produz decisão coerente via CLI e adaptador; cada adaptador documenta quais bloqueios consegue aplicar e quais dependem de gate externo; a espera humana não vira um loop de conclusão.

```gherkin
# language: pt
@SMD-REQ-017
Funcionalidade: Política compartilhada entre integrações
  @SMD-SCN-021
  Cenário: Preservar uma pendência humana no adaptador
    Dado que o núcleo retorna "waiting_human_review" para um snapshot
    Quando um adaptador validado receber esse resultado
    Então deve informar a pendência ao agente e aplicar o bloqueio suportado pelo host
    E não deve converter a pendência em sucesso
    E deve informar limitações de enforcement quando existirem
```

## SMD-REQ-018 — Gate protegido além do hook

**Origem confirmada quanto a impedir bypass; desenho de integração proposto.** A fronteira que impede integrar código precisa estar fora da capacidade de alteração ou autoaprovação do agente. Um hook local pode orientar o ciclo de trabalho, mas não é por si uma garantia universal de bloqueio.

**Critérios de aceite:** o mecanismo escolhido recusa integração sem decisão válida do verificador confiável; as permissões do agente não permitem aprovar a si próprio ou alterar silenciosamente a regra. Se esse isolamento não existir, a limitação deve ser declarada, em vez de anunciar a garantia.

```gherkin
# language: pt
@SMD-REQ-018
Funcionalidade: Integração protegida
  @SMD-SCN-022
  Cenário: Um hook local ausente não autoriza a integração
    Dado um ambiente configurado com gate de integração protegido
    E uma mudança sem aceite humano válido do contrato atual
    Quando a integração for solicitada sem executar o hook local
    Então o gate protegido deve continuar recusando a integração
    E o agente não deve poder emitir o aceite necessário usando suas próprias permissões
```

## SMD-REQ-019 — Relatório acionável de alinhamento

**Desenho proposto para tornar utilizáveis os controles confirmados.** Apresentar, por requisito/cenário aplicável, origem, versão do contrato, decisão humana, evidência atual e pendências. Diferenciar “aceito”, “executado” e “satisfeito segundo as evidências disponíveis”.

**Critérios de aceite:** cada bloqueio aponta a ação necessária e o artefato pertinente; um resultado favorável não afirma que o sistema provou toda a intenção humana; resumo e dados estruturados permitem inspeção independente.

```gherkin
# language: pt
@SMD-REQ-019
Funcionalidade: Explicação das decisões do gate
  @SMD-SCN-023
  Cenário: Informar como resolver um bloqueio
    Dado um requisito aplicável com aceite válido e cenário sem execução atual
    Quando o relatório de conclusão for produzido
    Então deve identificar o requisito, o cenário e a evidência ausente
    E deve distinguir essa pendência de uma falta de aceite humano
    E não deve apresentar a existência do cenário como comprovação de atendimento
```

## SMD-REQ-020 — Execução em Java, Python e Go

**Origem confirmada na continuação da descoberta.** Suportar ao menos projetos Java, Python e Go, executando cenários provenientes dos Markdown com implementações de passos na linguagem do projeto. Não presumir um argumento universal de CLI nem compatibilidade entre as APIs dos diferentes runners.

**Critérios de aceite:** cada adaptador deve executar código real sem exigir arquivos `.feature`; demonstrar sucesso, falha de asserção, passo indefinido e ausência de cenários exigidos; preservar IDs e origem no Markdown; registrar versões verificadas e limitações. Parsing bem-sucedido sozinho não demonstra execução. Um protótipo comprova sua hipótese e versão testada, sem constituir suporte estável do produto.

**Desenho em investigação:** Cucumber-JVM para Java, Behave para Python e Godog para Go. Behave não é uma distribuição oficial de Cucumber; a compatibilidade semântica, os formatos e as APIs precisam ser avaliados individualmente. A investigação e suas evidências ficam em [research](../research/README.md).

```gherkin
# language: pt
@SMD-REQ-020
Funcionalidade: Executar contratos nas linguagens iniciais
  @SMD-SCN-027
  Cenário: Executar um contrato Markdown em Java
    Dado um projeto Java com implementações reais dos passos do contrato
    Quando o adaptador validado executar os cenários a partir do Markdown
    Então o runner deve exercitar o código Java sem exigir arquivos ".feature"
    E os resultados devem identificar os cenários e sua origem no Markdown

  @SMD-SCN-028
  Cenário: Executar um contrato Markdown em Python
    Dado um projeto Python com implementações reais dos passos do contrato
    Quando o adaptador validado executar os cenários a partir do Markdown
    Então o runner deve exercitar o código Python sem exigir arquivos ".feature"
    E os resultados devem identificar os cenários e sua origem no Markdown

  @SMD-SCN-029
  Cenário: Executar um contrato Markdown em Go
    Dado um projeto Go com implementações reais dos passos do contrato
    Quando o adaptador validado executar os cenários a partir do Markdown
    Então o runner deve exercitar o código Go sem exigir arquivos ".feature"
    E os resultados devem identificar os cenários e sua origem no Markdown
```

## Pendências de especificação

Estas pendências não podem ser preenchidas silenciosamente como requisitos aceitos:

- Escolha do runner e demonstração da execução em memória sem `.feature`.
- Canal de identidade/aceite, permissões do agente e mecanismo de proteção de integração.
- Semântica exata de escopo aplicável, dependências e invalidação de evidência.
- Estrutura de metadados, referências por seção em documentos mistos e formato de manifesto.
- Política para falhas de ambiente, verificações manuais, exceções e possíveis dispensas.
- Eventos disponíveis e diferenças entre hosts de agentes.

O plano para resolver essas questões está em [roadmap.md](roadmap.md). O sucesso do produto precisa ser avaliado por redução de divergências e esforço de revisão, conforme [validation-plan.md](validation-plan.md), não apenas por quantidade de cenários presentes ou testes verdes.
