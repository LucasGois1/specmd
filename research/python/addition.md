# Contrato fictício de soma

Fixture experimental, sem aceite humano do produto. A narrativa e os quatro blocos são a fonte desta execução.

```gherkin
# language: pt
Funcionalidade: Primeira soma
  @SMD-PY-SCN-001
  Cenário: Somar dois e três
    Dado os números 2 e 3
    Quando a soma for calculada
    Então o resultado deve ser 5
```

A segunda execução vem de outro bloco do mesmo documento.

```gherkin
# language: pt
Funcionalidade: Segunda soma
  @SMD-PY-SCN-002
  Cenário: Somar quatro e cinco
    Dado os números 4 e 5
    Quando a soma for calculada
    Então o resultado deve ser 9
```

Os dois blocos seguintes são casos negativos deliberados.

```gherkin
# language: pt
Funcionalidade: Expectativa incorreta
  @SMD-PY-SCN-003
  Cenário: Rejeitar uma expectativa errada
    Dado os números 2 e 3
    Quando a soma for calculada
    Então o resultado deve ser 99
```

```gherkin
# language: pt
Funcionalidade: Implementação ausente
  @SMD-PY-SCN-004
  Cenário: Expor um passo indefinido
    Dado os números 2 e 3
    Quando uma operação ainda não implementada ocorrer
    Então o resultado deve ser 5
```
