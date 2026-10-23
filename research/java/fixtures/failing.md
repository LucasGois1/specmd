# Asserção deliberadamente incorreta

```gherkin
# language: pt
@SMD-REQ-JAVA-SUM
Funcionalidade: Detecção de resultado incorreto
  @SMD-SCN-JAVA-FAIL
  Cenário: Uma expectativa errada precisa falhar
    Dado os números 2 e 3
    Quando a aplicação somar os números
    Então o resultado deve ser 6
```
