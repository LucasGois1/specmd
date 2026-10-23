---
specmd:
  schema: 1
  id: SMD-EX-DOC-001
  kind: behavioral
---

# Exemplo: cobrança de pedidos cancelados

Este é um exemplo fictício do formato proposto para o SpecMD. Não é uma regra de produto aceita pelo usuário, não possui recibo de aceite e não indica que existam implementações de passos ou testes executados neste repositório.

O Markdown é a fonte canônica deste exemplo. Os cenários abaixo devem poder ser interpretados a partir deste arquivo, sem exigir um arquivo `.feature` paralelo ou uma etapa obrigatória de gravação desse arquivo.

## SMD-EX-REQ-001 — Não gerar cobranças para pedidos cancelados

Um pedido cancelado não deve gerar uma nova cobrança quando seu evento de cobrança for processado. A regra também se aplica a tentativas repetidas de processar o mesmo evento.

Este exemplo verifica pedidos cancelados que ainda não possuem cobranças. Não decide políticas de estorno, cancelamento de pedidos pagos ou autorização para cancelar: essas decisões precisariam de requisitos próprios, caso fossem necessárias ao produto real.

```gherkin
# language: pt
@SMD-EX-REQ-001
Funcionalidade: Impedir novas cobranças de pedidos cancelados

  @SMD-EX-SCN-001
  Cenário: Processar evento de cobrança após cancelamento
    Dado um pedido cancelado que não possui cobranças
    Quando o evento de cobrança desse pedido for processado
    Então nenhuma cobrança deve ser criada para esse pedido

  @SMD-EX-SCN-002
  Cenário: Repetir o processamento do evento de cobrança
    Dado um pedido cancelado que não possui cobranças
    Quando o mesmo evento de cobrança desse pedido for processado duas vezes
    Então nenhuma cobrança deve ser criada para esse pedido
```

## Revisão e evidências esperadas

Antes de implementar esse comportamento em um produto real, o usuário precisaria revisar a regra, os limites explicitados e os dois cenários. O aceite seria registrado por um canal protegido e vinculado ao hash, caminho e escopo desta versão.

Depois do aceite, o runner precisaria encontrar implementações dos passos e produzir evidências vinculadas ao contrato e ao código efetivamente executados. Passos indefinidos, cenários ignorados ou resultados antigos não atenderiam ao critério de conclusão.

Uma implementação que simplesmente não faz asserções ainda poderia produzir uma aparência de sucesso. A força da verificação exige avaliação adicional; a sintaxe válida dos cenários não estabelece essa garantia.

Se um agente introduzir outro limite, como um prazo máximo para cancelamento, essa mudança precisará aparecer como proposta de comportamento. Escrever um teste para esse limite não o transforma em requisito aceito.

Consulte o [formato proposto](../docs/format.md), o [mecanismo de aceite](../docs/approval-and-trust.md) e o [plano de validação](../docs/validation-plan.md).
