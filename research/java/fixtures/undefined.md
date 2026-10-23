# Passo sem definição

```gherkin
# language: pt
@SMD-REQ-JAVA-SUM
Funcionalidade: Detecção de implementação de passo ausente
  @SMD-SCN-JAVA-UNDEFINED
  Cenário: Uma ação inexistente não é um teste satisfeito
    Dado os números 2 e 3
    Quando uma operação sem definição for solicitada
    Então o resultado deve ser 5
```
