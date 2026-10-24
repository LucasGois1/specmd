# Decisões de concepção e questões em aberto

Este registro consolida a discussão que originou o projeto. As diretrizes abaixo foram expressas durante a concepção; isso não equivale a um recibo autenticado de aceite do conteúdo destes arquivos. Os detalhes técnicos continuam sendo propostas para revisão e experimentação.

## Diretrizes da discussão

| ID | Diretriz | Consequência |
| --- | --- | --- |
| D-001 | Markdown é a fonte canônica. | Explicação, requisitos e cenários permanecem no `.md`; nenhuma cópia editável `.feature` é necessária. |
| D-002 | A execução não deve depender de arquivos `.feature`. | Demonstrar parsing e adaptação em memória; não assumir suporte nativo de Cucumber a Markdown. |
| D-003 | O alinhamento precisa ser verificado nos dois sentidos. | Relacionar requisitos à implementação e mudanças relevantes de comportamento a uma intenção reconhecida. |
| D-004 | Documentar uma suposição não a autoriza. | Distinguir comportamento acordado, proposta do agente e comportamento apenas observado no legado. |
| D-005 | O contrato precisa de aceite humano explícito. | Vincular a decisão à versão apresentada, inclusive na especificação escrita em conjunto. |
| D-006 | Alterar documentação contratual ou cenários exige nova revisão. | A versão aceita anterior não autoriza automaticamente uma nova versão. |
| D-007 | Alterar código exige renovar evidências pertinentes. | Preservar o aceite quando a intenção não mudou; evitar aprovações humanas repetidas para tentativas de implementação. |
| D-008 | O agente não pode emitir seu próprio aceite. | Separar as permissões de propor, aceitar e aplicar o gate. |
| D-009 | Conteúdo, revisão e autoria precisam de rastreabilidade. | Usar identidade de conteúdo, diff, histórico Git e identidade autenticada dos eventos. |
| D-010 | Documentos podem ser comportamentais, informativos ou mistos. | Exigir cenários das obrigações comportamentais e aceite da dispensa informativa. |
| D-011 | Dispensa de Gherkin não é exclusão do inventário. | Monitorar documentos informativos para detectar mudanças que exijam revisão. |
| D-012 | Hooks devem melhorar a experiência com agentes. | Conectar análises a eventos suportados, sem presumir equivalência entre Claude Code e Codex. |
| D-013 | Aguardar o usuário é um estado legítimo. | Permitir devolução de controle sem marcar conclusão ou entrar em ciclos de bloqueio. |
| D-014 | A análise deve ser incremental. | Reutilizar resultados válidos, mantendo reconciliação e invalidação corretas. |
| D-015 | O índice não concede aprovação. | Tratar inventário e cache como dados derivados e reconstruíveis. |
| D-016 | A classificação automática é auxiliar. | Separar checagens determinísticas de sugestões semânticas e decisões humanas. |
| D-017 | O nome escolhido pelo usuário é SpecMD. | Usar `specmd` como nome do repositório e da interface proposta. Disponibilidade global de marca ou pacote não foi verificada. |
| D-018 | O suporte inicial precisa contemplar pelo menos Java, Python e Go. | Pesquisar e testar adaptadores reais por linguagem antes de estabilizar a arquitetura; não presumir um parâmetro universal de Cucumber. |
| D-019 | O usuário solicitou investigar sobreposição com Markdown with Gherkin antes de avançar. | A pesquisa encontrou antecedentes adicionais; comparar reutilização e a menor integração necessária, sem presumir novidade ou vantagem de um produto independente. |
| D-020 | O usuário quer testar o SpecMD localmente no Codex com um agente real. | Preparar instalação e ensaios em uma instância de teste do Codex; a presença do CLI não equivale à instalação do adaptador SpecMD nem à validação de seus bloqueios. |
| D-021 | Em 23/10/2026, o usuário redefiniu o produto: o SpecMD é um assistente, não uma auditoria. | Substitui D-005 e D-008 e o aceite assinado de D-006/D-009. A confirmação do dev é uma resposta na conversa; o plugin faz checagens determinísticas e devolve feedback sem encerrar a sessão. Autoridade, trust, assinaturas, revisão no navegador, `verify` protegido e bloqueio de implementação foram removidos. Ver a seção abaixo. |
| D-022 | Em 24/10/2026, o usuário escolheu otimizar o desempenho para projetos com milhares de arquivos, inclusive executando só os cenários afetados. | Cache por documento, impressão digital do código pelo Git e seleção de cenários por cobertura. Proposta, não implementada. |
| D-023 | Avisar quando um cenário confirmado é enfraquecido ou removido. | Diff contra os cenários da última mensagem do dev; devolve ao agente só no sinal forte. Proposta, não implementada. |
| D-024 | Avisar quando um documento ignorado passa a declarar regras. | Só aviso, quando o arquivo muda. Proposta, não implementada. |
| D-025 | Adoção em legado por um comando que parte da documentação existente. | Lista todos os documentos, o dev filtra com o agente e os cenários nascem um documento por vez. Proposta, não implementada. |
| D-026 | Suportar MDG (`.feature.md`) seguindo a especificação oficial. | Conversão para Gherkin em memória, preservando as linhas. Proposta, não implementada. |
| D-027 | Validar o Codex com LLM real e os eventos novos. | Depende de autenticação e da confiança nos hooks pelo usuário. Proposta, não executada. |
| D-028 | Medir o valor do SpecMD num piloto comparativo. | Grupo de comparação forte e avaliação por testes de aceite escondidos. Proposta, não executada. |

## D-021 — Assistente, não auditoria (23/10/2026)

O usuário descreveu o uso esperado com um exemplo: um sistema de pagamentos desenvolvido com agentes. O agente escreve a documentação do projeto; uma checagem confere se ela tem cenários de uso; se não tiver, o agente recebe esse feedback e conversa com o dev para confirmar os requisitos e escrever os cenários no próprio documento. O agente pergunta se está tudo certo, o dev confirma e o agente implementa. Ao final, uma análise confere se os cenários existem e passam; o que faltar volta para o agente.

Consequências:

- A documentação com cenários embutidos é a fonte canônica das regras de negócio; não há `.feature` paralelo para divergir.
- Não há fase de documentação: qualquer trabalho em Markdown dispara a análise. Nem todo Markdown descreve comportamento do sistema; esses ficam fora da análise e o agente pergunta ao dev quando houver dúvida.
- Cenários novos ou alterados desde a última mensagem do dev não são cobrados até que ele os veja; a execução é cobrada quando o código muda.
- O feedback é determinístico e limitado: o mesmo feedback repetido, ou o limite de repetições, deixa o agente parar. Erros internos viram aviso.
- O plugin deve carregar sozinho quando alguém abre o agente no repositório (entrega planejada).

As linhas D-005, D-006, D-008 e D-009 da tabela acima, as escolhas técnicas sobre aceites autenticados e as decisões abertas sobre interface, granularidade e reaproveitamento de aceites ficam como histórico.

## Evoluções escolhidas (24/10/2026)

Com o mínimo de D-021 validado em sessões reais, o usuário escolheu as evoluções D-022 a D-028 e aprovou o detalhamento abaixo, com as correções indicadas. Nada desta seção está implementado. Cada item vira um PR próprio; seus requisitos e cenários entram em [requirements.md](requirements.md) e são confirmados pelo usuário antes da implementação. Ordem combinada:

1. Desempenho (D-022).
2. Cenário enfraquecido ou removido (D-023) e documento ignorado que ganha regra (D-024).
3. Adoção em legado (D-025).
4. MDG (D-026).
5. Codex com LLM real (D-027), quando o usuário puder autenticar e confiar nos hooks.
6. Piloto comparativo (D-028), quando os itens anteriores estiverem estáveis.

### D-022 — Desempenho em projetos grandes

Hoje cada `PostToolUse` relê e reanalisa todos os Markdown, a impressão digital do código faz `lstat` em todos os arquivos e o `Stop` executa todos os cenários. Em projetos com milhares de arquivos isso cresce com o repositório, não com a mudança.

Decidido:

- **Cache por documento** em `.specmd/local/`, local e reconstruível: documento com o mesmo conteúdo reaproveita a análise anterior; só os vínculos entre documentos (IDs duplicados, requisitos sem cenário) são recalculados sobre o conjunto.
- **Impressão digital do código pelo Git:** o commit atual mais os arquivos alterados ou novos, em vez de examinar o repositório inteiro.
- **Só os cenários afetados:** cada execução registra os arquivos exercitados por cenário. Ao concluir, rodam os cenários que tocam arquivos alterados, os novos ou alterados e os que nunca rodaram. Sem cobertura disponível, roda tudo, como hoje; esse é o caso de Java e Go no início, e a cobertura deles (JaCoCo, `go test -cover`) fica para depois.
- **Rede de segurança:** a execução completa continua disponível pelo CLI e no CI. A seleção pode errar (import dinâmico, arquivo de configuração lido em tempo de execução), e o feedback diz quando rodou só parte dos cenários.
- **Benchmark** num repositório sintético da ordem de 5 mil Markdown e 50 mil arquivos, medido antes e depois. Meta: `PostToolUse` abaixo de 300 ms.

Decidido com o usuário em 24/10/2026, com os cenários de [SMD-REQ-027](requirements.md): o `Stop` e `specmd run --affected` executam só os afetados; `specmd run` executa todos. O feedback informa quantos cenários ficaram de fora. A seleção é por função, não por arquivo: todo arquivo importado pelos passos aparece como usado por todos os cenários. Mudança nos passos, no `environment.py`, na configuração ou no nível do módulo executa todos; cenários que iniciam processos ou abrem conexões sempre executam.

### D-023 — Cenário enfraquecido ou removido

Quando o agente apaga um cenário ou muda o valor esperado de um `Então` para o código passar, isso hoje passa calado.

Decidido:

- **Base de comparação:** os cenários como estavam na última mensagem do dev. O hook passa a guardar o conteúdo dos cenários, não só a impressão digital.
- **Mudanças distinguidas:** cenário removido, `Então` alterado, `Dado` ou `Quando` alterado, `@wip` adicionado e requisito removido.
- **Aviso:** depois da edição, o agente recebe o diff exato; ao concluir, o dev vê o mesmo resumo, mesmo que tudo passe. O aviso é informativo, inclusive quando o próprio dev pediu a mudança.
- **Devolução ao agente, uma vez,** só no sinal forte: o cenário falhava na última execução, o agente mudou o valor esperado dele e o código mudou no mesmo turno.

### D-024 — Documento ignorado que ganha regra

Decidido:

- Os arquivos ignorados, pelo `.specmdignore` ou pelos padrões, continuam sendo lidos de leve, só para detectar título `…-REQ-…`, bloco Gherkin ou palavra-chave MDG.
- O aviso sai apenas quando o arquivo muda e passa a ter isso. Um README que sempre teve um exemplo de Gherkin não gera aviso.
- O aviso oferece duas saídas: tirar o arquivo do `.specmdignore` (ou usar `!caminho`) ou mover a regra para um documento de comportamento. Em dúvida, o agente pergunta ao dev.
- Só aviso; não devolve trabalho ao agente ao concluir.

### D-025 — Adoção em legado

O usuário corrigiu a proposta inicial: o plugin não ordena nem filtra documentos por heurística (palavras como "deve" ou "não pode", números, limites). O fluxo decidido:

1. Um comando específico (nome proposto: `/specmd:adopt`) lista todos os Markdown do projeto, menos os ignorados por padrão e as entradas que o time já tenha no `.specmdignore`.
2. O agente apresenta a lista ao dev e separa com ele o que é documentação de comportamento. O que o dev mandar ignorar, o agente grava no `.specmdignore`.
3. Com esse filtro feito, o agente analisa um documento por vez, propõe requisitos e cenários e mostra ao dev para confirmar.
4. Depois da confirmação, segue o loop que já existe: passos, execução e feedback até passar.
5. **Divergência entre documentação e código:** se um cenário falha porque o código faz outra coisa, o agente não corrige sozinho. Ele pergunta ao dev qual dos dois está certo.

Em aberto:

- Se o progresso da adoção precisa de estado próprio. Proposta: o estado da documentação e do `.specmdignore` basta para retomar em outra sessão.
- Se o agente pode marcar com `@wip` os cenários confirmados que ainda não têm passos. Até o usuário decidir, vale a convenção atual: marcar `@wip` é decisão do dev.

### D-026 — MDG (`.feature.md`)

A especificação oficial ([MARKDOWN_WITH_GHERKIN.md](https://github.com/cucumber/gherkin/blob/main/MARKDOWN_WITH_GHERKIN.md)) e o tokenizador de referência em JavaScript foram conferidos em 24/10/2026:

- **Extensão:** `.feature.md` é obrigatória.
- **Prosa:** o formato é um superconjunto do GitHub Flavored Markdown e admite prosa. Linhas que não são Gherkin (parágrafos, imagens, links) são ignoradas pelo parser.
- **Palavras-chave e passos:** palavras-chave como títulos Markdown (`# Funcionalidade`, `## Regra`, `### Cenário`, `Esquema do Cenário`, `Exemplos`, `Contexto`); passos como itens de lista (`*` ou `-`).
- **Tabelas e Doc Strings:** tabelas no formato GFM, indentadas com 2 a 5 espaços; blocos cercados são Doc Strings.
- **Tags:** entre crases, na linha acima da palavra-chave.
- **Estrutura:** uma funcionalidade por arquivo; o título `Funcionalidade` é opcional.
- **Idioma:** não há `# language:`. O idioma é definido de forma global.
- **Suporte:** o parser oficial existe só em JavaScript; Behave, Cucumber-JVM e Godog não leem o formato.

Decidido:

- **Escopo:** `*.feature.md` é lido como MDG; os demais `.md` continuam com blocos cercados marcados como `gherkin`. Num `.feature.md`, um bloco cercado é Doc String, como na especificação, e os dois estilos não se misturam no mesmo arquivo.
- **Conversão:** o SpecMD converte MDG em Gherkin clássico em memória, preservando os números de linha. Motores e bridges não mudam.
- **Idioma:** vem do `gherkin_language` do `specmd.toml`.
- **Requisitos:** títulos que não são palavra-chave, como `## PAG-REQ-001 — Estorno`, são prosa para o MDG e continuam valendo como requisito pela posição.

Em aberto:

- Aceitar o ID de requisito também no título da `Regra`. Proposta: sim.
- Quais idiomas suportar. Proposta: todos os do Gherkin, já que o idioma vem da configuração.

### D-027 — Codex com LLM real

Decidido:

- Conferir na versão instalada do Codex:
  - os eventos disponíveis, inclusive `UserPromptSubmit`;
  - se o `Stop` aceita `decision: block`;
  - se `additionalContext` funciona no início da sessão e depois de ferramentas.
- Testar a raiz do projeto sem `CLAUDE_PROJECT_DIR`.
- Repetir o roteiro de quatro turnos já exercitado no Claude Code.
- Dependências do usuário: a autenticação do Codex na máquina e a confiança nos hooks pelo `/hooks`, que é uma ação humana.

Em aberto: como ativar o SpecMD no Codex sem o `.claude/settings` do projeto (só pelo `specmd.toml`, ou por um mecanismo equivalente do Codex).

### D-028 — Piloto comparativo

Decidido:

- **Tarefas:** de 6 a 10, em dois apps de exemplo (carrinho e pagamentos), com armadilhas plantadas: limite ambíguo, regra que contradiz a documentação e pedido que tenta inventar uma regra.
- **Grupo de comparação forte:** o mesmo repositório, a mesma documentação, os mesmos testes e um `CLAUDE.md` que manda manter a documentação, sem o SpecMD.
- **Dev simulado com intenção escondida:** um roteiro, ou um LLM no papel de dev, responde conforme uma especificação que o agente não vê.
- **Avaliação independente:** testes de aceite escondidos codificam a intenção real.
- **Métricas:**
  - regras inventadas que passaram;
  - omissões;
  - turnos até terminar;
  - falsos bloqueios;
  - latência dos hooks (p50 e p95);
  - tokens e custo.
- **Repetições:** de 3 a 5 por tarefa.

Em aberto:

- Quais modelos usar, o que define o custo.
- As metas, definidas antes de medir.

### Ideias levantadas e não escolhidas agora

Continuam disponíveis para escolhas futuras:

- mudança de comportamento sem documentação ("regra inventada") detectada ao concluir;
- marcador para exemplos de Gherkin que não devem rodar;
- CI e relatório por requisito no PR;
- bug vira cenário de regressão;
- contexto da tarefa com os requisitos relacionados;
- orientação para transformar prosa vaga em cenário;
- Windows;
- reaproveitar o ecossistema (Spec Kit, OpenSpec, Tracey);
- teste de mutação nos cenários;
- verificadores além de Gherkin;
- comparação entre agentes;
- prontidão de release.

## Escolhas técnicas propostas

Estas escolhas são hipóteses de implementação, sujeitas à validação:

- Núcleo CLI independente, com saída estruturada e adaptadores pequenos para cada agente.
- Markdown comum com frontmatter e blocos Gherkin identificados.
- SHA-256 dos bytes dos documentos e manifesto determinístico contendo caminhos e hashes.
- Aceites externos autenticados, ou artefatos assinados cuja autoridade permaneça fora do alcance do agente.
- Evidência de execução vinculada ao contrato, código, testes, configuração e ambiente pertinentes.
- Checagem protegida de integração além dos hooks locais.
- Índice local reconstruível; começar com armazenamento simples antes de otimizar consultas.
- Escopo e política protegidos para impedir autoisenção, exclusões silenciosas ou substituição do verificador.

## Decisões ainda abertas

| Questão | Como decidir |
| --- | --- |
| Licença | Decisão explícita do mantenedor; visibilidade pública não escolhe uma licença automaticamente. |
| Linguagem e distribuição do núcleo | Comparar integração do parser/runner, instalação e manutenção. |
| Runner inicial | Spike demonstrando execução em memória, origem no Markdown e resultados estruturados. |
| Primeiro agente integrado | Priorizar a preparação de testes locais no Codex, verificando versão, APIs, hooks e capacidade real de bloquear eventos antes de anunciar suporte. |
| Interface e armazenamento de aceites | Demonstrar identidade, conteúdo exato revisado, revogação e separação de credenciais. |
| Granularidade dos aceites | Comparar aceite por documento, requisito ou conjunto, sem perder o contexto aprovado. |
| Política de reaproveitamento de aceites | Definir efeitos de renomeação, retorno a conteúdo antigo, mudança de contexto e revogação. |
| Política de bloqueio | Definir o que pausa implementação, conclusão da tarefa ou integração, e o alcance das dependências. |
| Requisitos não funcionais | Escolher adaptadores específicos quando Gherkin não for o mecanismo adequado. |
| Compatibilidade de formato | Encaminhada por D-026: blocos cercados nos `.md` comuns e MDG oficial nos `.feature.md`, sem dialeto concorrente. Faltam os pontos em aberto de D-026. |

## Evoluções a considerar após o núcleo

- Contexto da tarefa preparado a partir dos contratos aplicáveis.
- Revisão de mudanças orientada a requisitos, evidências e alterações de contrato.
- Continuidade entre sessões e agentes com pendências e evidências atuais.
- Conversão de incidentes e bugs em cenários de regressão e justificativas registradas.
- Análise de impacto com cobertura e incertezas explícitas.
- Testes de mutação direcionados para avaliar a força das verificações.
- Comparação de agentes por atendimento aos critérios, retrabalho e esforço de revisão.
- Verificadores de compatibilidade, acessibilidade, arquitetura e desempenho.

Essas capacidades não integram automaticamente o MVP. Sua inclusão depende de demonstrar benefício no [plano de validação](validation-plan.md) e de manter a sequência do [roadmap](roadmap.md).
