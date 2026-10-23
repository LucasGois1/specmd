# Contrato de experimento Go

Este documento é a fonte de todos os cenários do experimento. Não há arquivo
`.feature`. Os exemplos negativos são deliberados para medir o bloqueio.

## Soma — SG-GO-REQ-001

Somar dois inteiros deve retornar sua soma matemática.

```gherkin
# language: pt
Funcionalidade: Soma de inteiros

  @pass @sum @SG-GO-SCN-001
  Cenário: Somar dois números
    Dado os números 2 e 3
    Quando eu somar os números
    Então o resultado deve ser 5

  @failure @SG-GO-SCN-003
  Cenário: Demonstrar uma asserção incorreta
    Dado os números 2 e 3
    Quando eu somar os números
    Então o resultado deve ser 99

  @undefined @SG-GO-SCN-004
  Cenário: Demonstrar um passo indefinido
    Dado os números 2 e 3
    Quando um passo não registrado é solicitado
    Então o resultado deve ser 5

  @pending @SG-GO-SCN-005
  Cenário: Demonstrar uma integração pendente
    Dado uma integração ainda pendente
    Quando eu somar os números
    Então o resultado deve ser 5
```

## Cancelamento — SG-GO-REQ-002

Reprocessar a cobrança de um pedido já cancelado não deve criar uma cobrança.
Este segundo bloco testa extração de múltiplos blocos em um Markdown real.

```gherkin
# language: pt
Funcionalidade: Cobrança depois do cancelamento

  @pass @cancellation @SG-GO-SCN-002
  Cenário: Reprocessar cobrança de um pedido cancelado
    Dado um pedido cancelado sem cobranças
    Quando o evento de cobrança for reprocessado
    Então nenhuma cobrança deve ser criada
```
