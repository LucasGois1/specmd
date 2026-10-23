---
specmd:
  schema: 1
  id: SMD-EX-DOC-002
  kind: reference
  exemption_reason: "Orientações sobre o editor do colaborador; não estabelece comportamentos do produto desenvolvido."
---

# Exemplo: configuração do editor

Este documento ilustra uma proposta de classificação como referência. A justificativa no frontmatter foi escrita pelo agente e precisa de aceite humano vinculado a esta versão. Não há dispensa aprovada nem recibo de aceite neste exemplo.

## Sugestões locais

Para facilitar a leitura da documentação, o colaborador pode:

- Habilitar números de linha.
- Usar a pré-visualização de Markdown do editor.
- Exibir espaços e quebras de linha durante a revisão de um diff.
- Manter uma aba com o documento completo enquanto consulta suas alterações.

Essas sugestões são preferências de edição. Não definem entradas, respostas, permissões ou efeitos externos do software que será desenvolvido.

## Por que não há Gherkin

Não foram incluídos cenários artificiais para verificar preferências de editor. A dispensa depende de o usuário concordar que o conteúdo revisado não estabelece obrigações comportamentais do produto.

Depois de aceita, essa classificação permite reutilizar a análise enquanto o conteúdo e o contexto aplicável permanecerem válidos. O arquivo continua no inventário e suas alterações continuam sendo detectadas.

Se alguém acrescentar aqui uma regra de negócio, o hash mudará e a classificação deverá ser reavaliada. O agente poderá propor transformar o documento em misto ou mover a regra para um contrato apropriado; não poderá manter uma dispensa antiga para o conteúdo novo.

Consulte o [formato proposto](../docs/format.md), o [índice incremental](../docs/indexing.md) e o mecanismo de aceite (removido por [D-021](../docs/decisions.md)).
