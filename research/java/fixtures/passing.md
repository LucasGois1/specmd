# Soma documentada em Markdown

Este fixture de pesquisa contém dois blocos executáveis e prosa fora deles.
Não é um contrato de produto aprovado por usuário.

## Primeiro exemplo

```gherkin
# language: pt
@SMD-REQ-JAVA-SUM
Funcionalidade: Soma de dois inteiros
  @SMD-SCN-JAVA-PASS1
  Cenário: Somar dois e três
    Dado os números 2 e 3
    Quando a aplicação somar os números
    Então o resultado deve ser 5
```

## Segundo exemplo independente

A segunda funcionalidade preserva seu próprio bloco e linhas do Markdown.

```gherkin
# language: pt
@SMD-REQ-JAVA-SUM
Funcionalidade: Soma com inteiro negativo
  @SMD-SCN-JAVA-PASS2
  Cenário: Somar menos dois e cinco
    Dado os números -2 e 5
    Quando a aplicação somar os números
    Então o resultado deve ser 3
```
