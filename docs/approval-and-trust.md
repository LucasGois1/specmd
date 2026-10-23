# Aceite, integridade e rastreabilidade

Esta é uma proposta de desenho para revisão. Não existe neste repositório uma autoridade de aceite, assinatura de usuário ou política de integração já implementada. A autorização para publicar estes documentos não equivale ao aceite de todos os contratos aqui propostos.

Leia em conjunto com [requisitos](requirements.md), [arquitetura](architecture.md), [formato](format.md), [indexação](indexing.md), [integrações](integrations.md) e [plano de validação](validation-plan.md).

## Garantia pretendida

Com as permissões destinadas ao agente, ele deve poder propor alterações e produzir implementações, mas não aceitar um novo contrato em nome do humano nem integrar sozinho uma mudança que descumpra a política.

Essa garantia depende de uma fronteira de permissões. Se o agente controla a credencial do aprovador, a chave de assinatura, as regras administrativas ou o próprio verificador protegido, um hash não impede o bypass. O desenho não promete impedir toda edição local quando o agente tem escrita irrestrita no workspace; o bloqueio de integração deve continuar sendo aplicado fora desse controle.

Três perguntas precisam ter respostas independentes:

- **Qual conteúdo foi proposto?** Identidade determinística do contrato e diff.
- **Quem concordou com ele?** Decisão humana autenticada e vinculada à versão apresentada.
- **O que foi verificado?** Evidência identificada da execução sobre o código e os testes pertinentes.

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

## Identidade determinística do contrato

O desenho inicial usa SHA-256 dos bytes exatos de cada documento. Para verificações protegidas, os bytes devem vir do snapshot Git selecionado, evitando diferenças de checkout e conversão de finais de linha entre máquinas.

Um manifesto inclui os caminhos dos documentos e seus hashes. A ordenação, a normalização dos caminhos e a serialização precisam ser definidas por um esquema versionado. O digest agregado é calculado sobre essa representação determinística.

Exemplo ilustrativo, sem formato final aprovado:

```json
{
  "schema": 1,
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

O hash identifica conteúdo, não o autor, a aprovação ou a ordem dos acontecimentos. Restaurar bytes antigos pode restaurar um hash antigo. O histórico e a política de reaproveitamento de aceites devem distinguir esse evento de uma aprovação nova; o padrão inicial recomendado é não reaplicar automaticamente uma decisão fora da solicitação e do contexto em que foi emitida.

## Registro de aceite

O usuário deve revisar uma versão fixada, incluindo o diff em relação à versão de referência. O sistema registra uma ação explícita; colaboração prévia na conversa ou ausência de resposta não concede aceite.

O recibo verificável deve identificar pelo menos:

- Repositório e escopo da decisão, sem depender apenas de um nome que possa ser renomeado.
- Identificador da solicitação de revisão e digest do contrato apresentado.
- Revisão Git ou snapshot exato que originou a apresentação.
- Identidade autenticada do aprovador e autoridade que registrou o evento.
- Decisão, data e hora.
- Versão da política pertinente.
- Mecanismo de autenticidade, como assinatura verificável ou referência a um evento protegido do provedor.

Expiração, revogação e associação à versão anterior devem ter regras explícitas. Um recibo historicamente autêntico pode não ser mais aplicável à mudança atual.

O recibo pode estar no repositório. Nesse caso, seu conteúdo permanece não confiável até a validação da autenticidade e do escopo. As chaves públicas aceitas, identidades autorizadas e regras de confiança não podem ser substituídas pelo agente junto com o recibo.

Um campo `approved: true`, uma caixa marcada ou um commit atribuído ao usuário não satisfazem essa exigência. A chave privada, token de revisão ou canal de confirmação não pode estar acessível ao agente. Se a integração usa a mesma identidade para ações humanas e do agente, ela não estabelece a separação pretendida.

## Experiência de revisão

A apresentação deve permitir ver o texto completo e o diff original, além de um resumo de requisitos e cenários adicionados, removidos ou alterados. Ações de aceite devem se referir explicitamente ao snapshot exibido.

O agente pode redigir os cenários; o usuário revisa os comportamentos e exemplos. Uma aprovação por conjunto coerente de mudanças reduz interrupções, sem esconder quais documentos e dispensas foram incluídos.

Se o conteúdo muda durante a revisão, uma decisão sobre o snapshot anterior não deve ser associada ao novo. A interface pode recusar uma solicitação desatualizada ou registrar o aceite antigo e manter a proposta atual pendente. Em nenhum caso deve aprovar silenciosamente o conteúdo que o usuário não viu.

O sistema registra a declaração de leitura e concordância. Não consegue comprovar que o usuário leu atentamente ou compreendeu todas as consequências.

## Invalidação e execução

Há dois controles distintos: aceitar a intenção e verificar a execução dos cenários.

- Alterar documento ou cenário protegido cria uma versão que exige novo aceite.
- Alterar código, passos, asserções, configuração ou ferramenta relevante exige renovar as evidências pertinentes, sem necessariamente exigir novo aceite de um contrato inalterado.
- Um cenário ignorado, pendente, indefinido ou excluído por filtro não conta como cenário executado com sucesso.
- Bloqueios de ambiente precisam aparecer como pendência, sem serem convertidos em resultado verde.
- Alterar a implementação de um passo pode enfraquecer a verificação sem modificar o Gherkin; essa alteração deve permanecer visível na revisão técnica.

Uma evidência deve vincular resultados ao digest do contrato, snapshot do código, versão dos passos e testes, configuração e versões das ferramentas. Deve também registrar o conjunto esperado e o conjunto efetivamente executado, para que filtros e omissões sejam identificáveis.

O gate protegido deve verificar o estado que será integrado. Validar um snapshot e depois permitir substituí-lo por outro cria uma inconsistência entre revisão e integração. Alterações posteriores exigem nova avaliação antes de usar o resultado como autorização.

## Histórico e autoria

Git fornece versões e diffs, mas o campo `author` é uma afirmação configurável. A auditoria deve distinguir:

1. Autor e committer declarados no commit.
2. Identidade autenticada que submeteu ou publicou a alteração.
3. Identidade humana que aceitou o contrato.
4. Identidade do executor que produziu a evidência.
5. Conteúdos e revisões aos quais cada ação se refere.

Assinaturas comprovam o controle da credencial usada conforme a política de confiança; não demonstram por si só que uma pessoa digitou a alteração. A retenção de eventos de aprovação precisa sobreviver a reescritas do histórico do repositório ou tornar essas alterações detectáveis por uma fonte protegida.

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
- Qual serialização e esquema de manifesto serão adotados, com vetores de teste determinísticos.
- Como são autorizadas e auditadas alterações de política e raízes de confiança.
- Como expiração, revogação, restauração de conteúdo antigo e revisão substituída afetam aceites.
- Qual é o alcance configurável de cada bloqueio: tarefa, trabalho dependente ou projeto.
- Como evidências são emitidas, retidas e verificadas sem expor credenciais ao código em teste.
- Quais capacidades reais de cada plataforma permitem interromper implementação e conclusão, além do bloqueio protegido de integração.

Os experimentos devem testar essas fronteiras com tentativas deliberadas de bypass, sem apresentar ausência de falhas observadas como garantia absoluta. O mecanismo evidencia concordância e verificação dos cenários declarados; a cobertura integral da intenção continua sendo uma questão de qualidade dos contratos, testes e revisão.
