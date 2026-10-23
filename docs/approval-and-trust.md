# Aceite, integridade e rastreabilidade

O ciclo experimental já implementa propostas de revisão com snapshots, decisões Ed25519 vinculadas à versão, verificação de confiança externa, execução de cenários e conferência de evidências. A autoridade inicial é uma demonstração local: não autentica a identidade humana nem comprova que o agente esteja impedido de usar a chave. Não há serviço produtivo de aprovação, autenticação GitHub/OAuth ou instalação automática de uma política protegida no provedor.

Consulte [estado da implementação](implementation-status.md) para separar código disponível, provas executadas e capacidades pendentes. Publicar ou editar estes documentos não equivale ao aceite de seus contratos; decisões sintéticas dos testes pertencem somente aos fixtures descartáveis.

Leia em conjunto com [requisitos](requirements.md), [arquitetura](architecture.md), [formato](format.md), [indexação](indexing.md), [integrações](integrations.md) e [plano de validação](validation-plan.md). Os controles abaixo distinguem o mecanismo implementado das garantias que dependem de implantação externa.

## Garantia pretendida

Com as permissões destinadas ao agente, ele deve poder propor alterações e produzir implementações, mas não aceitar um novo contrato em nome do humano nem integrar sozinho uma mudança que descumpra a política.

Essa garantia depende de uma fronteira de permissões. Se o agente controla a credencial do aprovador, a chave de assinatura, as regras administrativas ou o próprio verificador protegido, um hash não impede o bypass. O desenho não promete impedir toda edição local quando o agente tem escrita irrestrita no workspace; o bloqueio de integração deve continuar sendo aplicado fora desse controle.

Três perguntas precisam ter respostas independentes:

- **Qual conteúdo foi proposto?** Identidade determinística do contrato e diff.
- **Quem concordou com ele?** Decisão humana autenticada e vinculada à versão apresentada.
- **O que foi verificado?** Evidência identificada da execução sobre o código e os testes pertinentes.

No código atual, verificar uma assinatura responde quem controla uma chave autorizada e quais declarações ela assinou. O campo `reviewer` é uma declaração assinada, não resultado de login humano; a verificação retorna `human_authenticated: false`. A identificação humana da segunda pergunta continua dependendo de um canal de aprovação externo adequadamente autenticado.

## Modelo de confiança

| Ator ou componente | Pode fazer | Não deve poder fazer |
| --- | --- | --- |
| Agente de desenvolvimento | Alterar documentos e código; propor classificações; solicitar revisão; executar verificações locais. | Emitir aceite humano, escolher sozinho uma nova raiz de confiança ou remover o gate protegido. |
| Humano autenticado | Revisar o conteúdo apresentado e aceitar, rejeitar ou solicitar ajustes. | Seu aceite não deve ser reaplicado a outro conteúdo sem autorização. |
| Serviço ou canal de aceite | Registrar a decisão sobre um snapshot e manter sua autenticidade verificável. | Executar código arbitrário do projeto com as credenciais do aprovador acessíveis. |
| Runner de testes | Executar o snapshot selecionado e emitir resultados identificados. | Ter acesso às chaves ou permissões de aceite humano. |
| Verificador protegido | Recalcular identidades e conferir política, aceites e evidências. | Confiar apenas em campos de aprovação ou resultados fornecidos pelo agente. |
| Administrador da política | Configurar escopo, identidades e bloqueios por um fluxo controlado. | Essa autoridade não deve estar disponível automaticamente ao agente. |

Separar jobs não basta se um deles executa código do projeto com acesso às chaves dos demais. O canal de aprovação e a execução de código não confiável precisam de isolamento efetivo de credenciais e permissões.

`trust.json` tem modo `local_demo` ou `protected`. O inicializador implementado só cria `local_demo`; a confiança protegida é provisionada separadamente pelo operador. O nome `protected` não inspeciona permissões, autentica uma pessoa nem cria isolamento: o operador precisa controlar a procedência do arquivo, das chaves e do verificador. Um diretório fora do checkout também pode continuar acessível ao agente.

## Identidade determinística do contrato

O núcleo implementado usa SHA-256 dos bytes exatos de cada documento e da configuração. No ciclo schema 2, o manifesto também inclui o hash do mapa explícito de rastreabilidade. A inspeção trabalha sobre o checkout efetivo; o ambiente protegido deve fornecer o snapshot de integração desejado e uma política consistente de checkout e finais de linha.

O manifesto inclui caminhos relativos e hashes, com documentos ordenados e serialização JSON determinística em UTF-8. O digest agregado identifica essa representação. Classificação, justificativa de dispensa e cenários integram os bytes do Markdown; configuração e mapa de vínculos também participam da identidade revisada.

Exemplo ilustrativo do manifesto do ciclo schema 2, com digests abreviados para leitura; não é um recibo nem uma aprovação:

```json
{
  "schema": 1,
  "config_sha256": "<digest da configuração>",
  "traceability_sha256": "<digest do mapa de vínculos>",
  "documents": [
    { "path": "contracts/cancelamento.md", "sha256": "<digest>" },
    { "path": "contracts/cobranca.md", "sha256": "<digest>" }
  ]
}
```

Regras necessárias para o manifesto:

- Caminhos são relativos ao repositório e têm representação canônica; caminhos duplicados ou ambíguos devem ser rejeitados.
- Adicionar, remover ou renomear um documento altera o conjunto identificado. Um rename pode ser tratado inicialmente como remoção e adição.
- O verificador descobre o conjunto efetivo conforme a política autorizada; não aceita cegamente uma lista preparada pelo agente.
- Novos arquivos locais no escopo também são considerados nas verificações de desenvolvimento, inclusive antes do primeiro commit.
- Links simbólicos, submódulos e referências externas precisam de regra explícita. Não devem ampliar silenciosamente o escopo ou introduzir conteúdo mutável não identificado.
- Classificações e justificativas de dispensa fazem parte do conteúdo submetido à revisão, ou são vinculadas por um registro igualmente identificado.
- Recibos de aceite e resultados não entram recursivamente no conteúdo que atestam.
- Mudanças de política que alteram seleção, exclusões ou interpretação também exigem controle de autorização.

O hash identifica conteúdo, não o autor, a aprovação ou a ordem dos acontecimentos. Restaurar bytes antigos pode restaurar um hash e uma proposta antigos. O registro externo de decisões impede reaplicar uma decisão substituída ou rejeitada para aquela proposta; uma aprovação ainda vigente para os mesmos bytes e contexto pode voltar a corresponder a eles. Proibir qualquer retorno a versões antigas exigiria uma política adicional de geração, expiração ou revogação explícita.

## Identidade portátil e fronteira física

Com `repository_id` configurado, a assinatura usa uma identidade lógica `repo:<repository_id>`, como `repo:github.com/LucasGois1/specmd`. Assim, o mesmo contrato pode ser verificado em outro checkout sem depender do caminho absoluto da máquina do desenvolvedor. Sem essa opção, o vínculo usa o caminho absoluto e não é portátil entre diretórios diferentes.

`workspace_root` identifica separadamente a raiz física atual para recusar trust dentro do checkout, inclusive por resolução de links. Esse caminho é metadado de contexto local, não parte da identidade portátil da proposta. Na verificação com identidade `repo:`, a raiz atual é obrigatória; escolher um identificador lógico não dispensa a checagem de localização e permissões.

## Registro de aceite

O usuário deve revisar uma versão fixada, incluindo o diff em relação à versão de referência. O sistema registra uma ação explícita; colaboração prévia na conversa ou ausência de resposta não concede aceite.

O contrato completo pretende identificar pelo menos:

- Repositório e escopo da decisão, sem depender apenas de um nome que possa ser renomeado.
- Identificador da solicitação de revisão e digest do contrato apresentado.
- Revisão Git ou snapshot exato que originou a apresentação.
- Identidade autenticada do aprovador e autoridade que registrou o evento.
- Decisão, data e hora.
- Versão da política pertinente.
- Mecanismo de autenticidade, como assinatura verificável ou referência a um evento protegido do provedor.

O envelope implementado vincula `project_id`, identidade do repositório, `contract_sha256`, manifesto, `proposal_sha256`, decisão `accept`/`reject`, `reviewer` e `issued_at`. A assinatura Ed25519 também protege versão, algoritmo e ID da chave no envelope. A proposta captura o texto UTF-8 exato dos documentos, conferido contra seus hashes. Anotações de apresentação, como o texto anterior para diff, não constituem uma segunda fonte de autorização.

O armazenamento externo contém `private.key` e `trust.json`. O trust declara chaves públicas, autorizações por projeto/repositório, revogação de chave e `latest_decisions`, que associa uma proposta ao hash do envelope vigente. Assinar uma nova decisão atualiza esse registro; uma rejeição posterior impede usar o aceite anterior. No modo protegido, uma decisão não fixada nesse registro é recusada. A criação de chaves ocorre somente na operação explícita de inicialização, nunca durante checks normais.

Um recibo pode incluir `previous_approval_sha256` para ligar decisões da mesma proposta. Esse encadeamento e as assinaturas não implementam, por si, um log externo imutável ou retenção garantida. Expiração do aceite, rotação operacional de chaves, recuperação e política para revisões substituídas ainda exigem definição de implantação. A validade temporal da evidência de execução é um controle separado.

O recibo pode estar no repositório. Nesse caso, seu conteúdo permanece não confiável até a validação da autenticidade e do escopo. As chaves públicas aceitas, identidades autorizadas e regras de confiança não podem ser substituídas pelo agente junto com o recibo.

Um campo `approved: true`, uma caixa marcada ou um commit atribuído ao usuário não satisfazem essa exigência. A chave privada, token de revisão ou canal de confirmação não pode estar acessível ao agente. Se a integração usa a mesma identidade para ações humanas e do agente, ela não estabelece a separação pretendida.

## Experiência de revisão

A apresentação deve permitir ver o texto completo e o diff original, além de um resumo de requisitos e cenários adicionados, removidos ou alterados. Ações de aceite devem se referir explicitamente ao snapshot exibido.

O agente pode redigir os cenários; o usuário revisa os comportamentos e exemplos. Uma aprovação por conjunto coerente de mudanças reduz interrupções, sem esconder quais documentos e dispensas foram incluídos.

Se o conteúdo muda durante a revisão, uma decisão sobre o snapshot anterior não deve ser associada ao novo. A interface pode recusar uma solicitação desatualizada ou registrar o aceite antigo e manter a proposta atual pendente. Em nenhum caso deve aprovar silenciosamente o conteúdo que o usuário não viu.

O sistema registra a declaração de leitura e concordância. Não consegue comprovar que o usuário leu atentamente ou compreendeu todas as consequências.

Na interface local implementada, a pessoa pode inspecionar a proposta e acionar a decisão assinada. O nome informado continua sendo autodeclarado. Não há sessão autenticada por provedor de identidade; não se deve apresentar essa interface ou uma assinatura de demonstração como prova de uma identidade humana autenticada.

## Invalidação e execução

Há dois controles distintos: aceitar a intenção e verificar a execução dos cenários.

- Alterar documento ou cenário protegido cria uma versão que exige novo aceite.
- Alterar código, passos, asserções, configuração ou ferramenta relevante exige renovar as evidências pertinentes, sem necessariamente exigir novo aceite de um contrato inalterado.
- Um cenário ignorado, pendente, indefinido ou excluído por filtro não conta como cenário executado com sucesso.
- Bloqueios de ambiente precisam aparecer como pendência, sem serem convertidos em resultado verde.
- Alterar a implementação de um passo pode enfraquecer a verificação sem modificar o Gherkin; essa alteração deve permanecer visível na revisão técnica.

Uma evidência deve vincular resultados ao digest do contrato, snapshot do código, versão dos passos e testes, configuração e versões das ferramentas. Deve também registrar o conjunto esperado e o conjunto efetivamente executado, para que filtros e omissões sejam identificáveis.

O gate protegido deve verificar o estado que será integrado. Validar um snapshot e depois permitir substituí-lo por outro cria uma inconsistência entre revisão e integração. Alterações posteriores exigem nova avaliação antes de usar o resultado como autorização.

### Estados implementados e limites do resultado

| Situação | Resultado do ciclo experimental |
| --- | --- |
| Schema 1 | Preflight estrutural; nunca autoriza conclusão. |
| Schema 2 sem decisão válida | `waiting_human_review`; proposta, classificação ou versão ainda pendentes. |
| Decisão válida sem evidência atual | `awaiting_evidence`; requer execução. |
| Falha estrutural, de vínculos ou de cenários | `blocked` ou `error`, conforme a causa. |
| Ciclo local consistente ou evidência reaproveitada localmente | Pode produzir `demo_passed`; demonstra o fluxo, não satisfaz o gate protegido. |
| Execução atual real, confiança externa configurada como protegida e rastreabilidade estrita | Pode produzir `passed`, sujeito à fronteira operacional descrita abaixo. |

`specmd verify` exige execução real atual por padrão. Um arquivo em `.specmd/local/evidence.json`, ainda que internamente coerente, não satisfaz sozinho essa verificação protegida. Uma simulação ou um resultado `demo_passed` também não é promovido a `passed` por ter JSON ou hashes válidos.

O predicado implementado para `passed` confere essas condições; ele não comprova que a instalação do verificador, do trust e dos runners esteja protegida. É necessário executar um pacote/verificador confiável com política aplicada fora do alcance do agente. Rodar código do próprio PR como verificador autoritativo, ou aceitar um relatório de bridge executável arbitrário controlado pelo agente, não estabelece essa garantia. A assinatura do contrato e o campo de execução `real` não tornam um produtor de resultados automaticamente confiável.

## Histórico e autoria

Git fornece versões e diffs, mas o campo `author` é uma afirmação configurável. A auditoria deve distinguir:

1. Autor e committer declarados no commit.
2. Identidade autenticada que submeteu ou publicou a alteração.
3. Identidade humana que aceitou o contrato.
4. Identidade do executor que produziu a evidência.
5. Conteúdos e revisões aos quais cada ação se refere.

Assinaturas comprovam o controle da credencial usada conforme a política de confiança; não demonstram por si só que uma pessoa digitou a alteração. A retenção de eventos de aprovação precisa sobreviver a reescritas do histórico do repositório ou tornar essas alterações detectáveis por uma fonte protegida.

O mapa de rastreabilidade implementado relaciona arquivos e IDs de requisitos/cenários. A política estrita recusa arquivos de código/teste sem vínculo declarado, mas não prova que a associação é semanticamente correta nem que o software implementa toda a intenção aceita. Essa avaliação continua dependendo da qualidade das verificações e da revisão humana.

## Bypasses a exercitar na validação

| Tentativa | Controle proposto | Limite que precisa ficar explícito |
| --- | --- | --- |
| Marcar a própria documentação como informativa. | Dispensa aceita para um conteúdo específico; proposta do agente não concede dispensa. | A qualidade da classificação continua dependendo de revisão. |
| Remover arquivo do manifesto ou mudar a exclusão. | Descoberta independente e política de escopo protegida. | Não basta validar a lista fornecida pelo agente. |
| Escrever recibo de aprovação no repositório. | Verificação da autoridade, autenticidade, conteúdo e escopo. | Chave ou canal acessível ao agente elimina a separação. |
| Reutilizar recibo antigo, revogado ou de outro projeto. | Vincular repositório, solicitação, digest, política e validade. | Reaproveitamento deve ser uma decisão explícita, não coincidência de hashes. |
| Alterar conteúdo após a revisão ou execução. | Snapshot fixado e nova conferência antes da integração. | O resultado não autoriza outro estado do projeto. |
| Desativar hook ou mudar workflow. | Gate protegido e credencial sem poder de alterar a regra autoritativa. | Hook local sozinho não impõe essa garantia. |
| Ocultar cenários com filtros, `skip` ou estados pendentes. | Comparar cenários esperados e executados; estados distintos de sucesso. | A política pode tratar exceções justificadas, mas sem sucesso silencioso. |
| Substituir asserções por passos vazios. | Revisão de testes e evidência da versão executada; avaliações de força dos testes como expansão. | Executar e passar não prova a suficiência da asserção. |
| Forjar cache ou resultado local. | Cache reconstruível; evidência e gate provenientes de execução protegida. | A autoridade não pode aceitar estado local como fonte única. |

## Decisões que ainda precisam ser tomadas

- Qual canal registra o aceite e como mantém a identidade humana separada da automação.
- Como evoluir os schemas experimentais de manifesto e envelopes sem invalidar silenciosamente contratos e decisões anteriores.
- Como são autorizadas e auditadas alterações de política e raízes de confiança.
- Como expiração de aceites, rotação de chaves, restauração de conteúdo antigo e revisões substituídas serão administradas além do registro de decisão vigente já implementado.
- Qual é o alcance configurável de cada bloqueio: tarefa, trabalho dependente ou projeto.
- Como implantar emissão e retenção de evidências e um verificador protegido sem expor credenciais ao código em teste.
- Quais capacidades reais de cada plataforma permitem interromper implementação e conclusão, além do bloqueio protegido de integração.

Os experimentos devem testar essas fronteiras com tentativas deliberadas de bypass, sem apresentar ausência de falhas observadas como garantia absoluta. O mecanismo evidencia concordância e verificação dos cenários declarados; a cobertura integral da intenção continua sendo uma questão de qualidade dos contratos, testes e revisão.
