# Python: Gherkin em memória com Behave

Pesquisa experimental, não implementação de produção. **Behave é um executor BDD para Python; não é o Cucumber oficial.** Compartilhar Gherkin e depender de pacotes com nome `cucumber-*` não torna esses executores equivalentes.

O experimento usa **Behave 1.3.3**, Python 3.12.14 e **markdown-it-py 4.0.0**. As versões transitivas efetivamente observadas estão em [requirements.lock](requirements.lock). Esse arquivo fixa versões, mas não contém hashes das distribuições e não deve ser apresentado como uma verificação de supply chain.

## Markdown real: resultado ampliado

O [probe_markdown.py](probe_markdown.py) foi executado contra o arquivo canônico [addition.md](addition.md), usando o parser real `MarkdownIt` para localizar cercas Gherkin. Cada bloco selecionado foi parseado como string pelo Behave, com linhas vazias de prefixo para preservar os números de linha do Markdown. A execução usou modelos em memória e implementações reais dos passos, sem gravar `.feature`.

| Caso | Resultado observado | `engine_failed` | Gate experimental |
| --- | --- | --- | --- |
| Dois blocos em português | Dois cenários `passed`, duas chamadas à função de soma | `false` | Permite |
| Esperado 99 para soma 2 + 3 | Cenário `failed`, asserção falha | `true` | Recusa |
| Passo sem implementação | Cenário `error`; passos `passed`, `undefined`, `skipped` | `true` | Recusa |
| Filtro que exclui todos os cenários | Dois cenários `skipped`, nenhuma chamada à função de soma | `false` | Recusa |

As [evidências completas](evidence/results.json) contêm hash SHA-256 do Markdown, hashes dos scripts, IDs esperados e observados, resultados por passo, chamadas da implementação e origem `addition.md#block-N`. Os cenários positivos apontam para as linhas **9 e 21** do documento; os negativos para **33 e 43**. A correspondência com linhas `Cenário:` no arquivo foi conferida no probe.

O caso filtrado é uma evidência importante: o booleano de falha do engine pode ser `false` sem que nenhum comportamento tenha sido executado. O gate experimental também exige o conjunto esperado de IDs aprovados e as chamadas esperadas da implementação. Esses IDs foram fornecidos pelo experimento; não foram inferidos automaticamente da prosa nem aprovados por um mecanismo de aceite humano.

O harness terminou com código **zero**, pois os quatro casos produziram os resultados esperados, incluindo as três recusas. Esse código não significa que os cenários negativos passaram. A evidência não encontrou arquivos `.feature` na árvore pesquisada. O script não contém etapa que escreva esse tipo de arquivo; o levantamento posterior de arquivos não é um monitor completo de todos os syscalls do processo.

## Probe mínimo de string

O [probe mínimo](probe_minimal.py) passou texto Gherkin em português a `behave.parser.parse_feature(text, filename="probe.md")`, registrou implementações reais de passos e executou o modelo com `ModelRunner.run_model()`. A implementação exercitada foi a função real `add(a, b)`. As [evidências mínimas](evidence/minimal.json) preservam os resultados e o hash do script.

| Caso | Resultado do cenário | Retorno `engine_failed` |
| --- | --- | --- |
| Soma 2 + 3, esperado 5 | `passed` | `false` |
| Soma 2 + 3, esperado 99 | `failed` | `true` |

Nenhum arquivo `.feature` foi necessário nesse caminho. O nome `probe.md` é uma identificação de origem fornecida ao parser; o probe mínimo trabalha com uma string e não demonstra, sozinho, extração de um documento Markdown real.

`run_model()` retorna um **booleano de falha**, não um exit status de processo. O processo do probe pode terminar com código zero enquanto exibe uma falha esperada. Isso significa que o programa diagnóstico executou, não que o cenário negativo passou nem que um gate de produto deveria liberá-lo.

## CLI convencional: tentativas efetivamente executadas

O [cli_probe.py](cli_probe.py) executa o módulo Behave em um diretório temporário vazio, fornecendo o mesmo texto de três maneiras:

| Tentativa | Exit status da CLI observado | Comportamento observado |
| --- | --- | --- |
| Texto completo como argumento posicional | `1` | Interpretado como caminho; `ConfigError` procurando diretório de passos. |
| Texto por stdin, sem argumento posicional | `1` | Procura o diretório convencional `features`; não executa o texto fornecido. |
| Texto por stdin, argumento `-` | `1` | Procura o caminho `-`; não executa o texto fornecido. |

Essas observações documentam os comandos testados, no contexto descrito. Não provam a impossibilidade de um runner customizado ou de outra configuração de CLI. O caminho bem-sucedido deste experimento foi a API de modelo em memória, não um suporte nativo da CLI a Markdown.

As [evidências da CLI](evidence/cli.json) distinguem o exit status real do engine e o exit status do harness. O harness termina com zero quando observa as três rejeições esperadas e nenhum `.feature` no diretório temporário. Caminhos temporários foram substituídos por `<TMPDIR>`; nenhuma credencial é coletada.

## Reprodução

Em um ambiente com acesso ao índice de pacotes, a instalação reproduzível por versões pode ser feita com:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.lock
.venv/bin/python probe_minimal.py
.venv/bin/python probe_markdown.py
.venv/bin/python cli_probe.py --output evidence/cli.json
```

Neste ambiente, o executor principal provisionou as dependências fora do repositório em `/tmp/specmd-python-probe`. Os comandos realmente executados para os probes foram:

```sh
PYTHONPATH=/tmp/specmd-python-probe python3 probe_minimal.py
PYTHONPATH=/tmp/specmd-python-probe python3 probe_markdown.py
PYTHONPATH=/tmp/specmd-python-probe python3 cli_probe.py --output evidence/cli.json
```

O diretório `.venv`, bytecode e caches estão ignorados. Não é necessário publicar o ambiente de execução nem arquivos temporários.

## Superfícies de integração e fragilidade

- `parse_feature()` aceita texto Unicode e um nome de origem. Isso está confirmado no código da versão fixada e no probe executado.
- `ModelRunner` executa objetos de modelo já construídos. A classe e `run_model()` estão disponíveis no módulo `behave.runner`, sem prefixo privado; isso não constitui uma promessa de estabilidade do acoplamento usado aqui entre versões.
- `StepRegistry.add_step_definition()` permite registrar passos para esse modelo sem criar uma árvore convencional de arquivos de features. O probe usa um registro isolado por caso.
- A configuração, os modelos, seus estados e os hooks continuam pertencendo à implementação do Behave. Um adaptador de produção precisa de testes de compatibilidade e versões suportadas explícitas.
- A classe `Runner` convencional inclui descoberta de caminhos, carregamento de passos e parsing de arquivos. O experimento usa `ModelRunner` para não depender dessa descoberta.
- Um parser Gherkin oficial produz representações do documento; ele não equivale, por si só, a um executor de passos. Nenhum parser oficial substituiu o engine Behave neste probe.

O suporte Markdown with Gherkin descrito pelo projeto Cucumber é uma proposta de sintaxe diferente das cercas Gherkin discutidas no SpecMD. A existência dessa documentação não demonstra suporte Markdown no Behave.

## Fontes primárias

As fontes de Behave abaixo foram consultadas no tag **v1.3.3**, correspondente à versão executada:

1. [Parser: `parse_feature(text, language=None, filename=None)`](https://github.com/behave/behave/blob/v1.3.3/behave/parser.py#L77).
2. [Modelo de execução: `ModelRunner`](https://github.com/behave/behave/blob/v1.3.3/behave/runner.py#L657).
3. [Execução de modelos e cálculo do booleano de falha: `run_model`](https://github.com/behave/behave/blob/v1.3.3/behave/runner.py#L915).
4. [Runner convencional e descoberta de caminhos](https://github.com/behave/behave/blob/v1.3.3/behave/runner.py#L996).
5. [Projeto oficial markdown-it-py, tag v4.0.0](https://github.com/executablebooks/markdown-it-py/tree/v4.0.0). O tag consultado aponta para o commit `c62983f1554124391b47170180e6c62df4d476ca`.
6. [Markdown with Gherkin, no repositório oficial Cucumber](https://github.com/cucumber/gherkin/blob/main/MARKDOWN_WITH_GHERKIN.md). Essa referência em `main` é contextual e não uma dependência fixada do experimento.

## Alcance

Os probes confirmam a viabilidade limitada de extrair blocos de Markdown real e executar modelos Behave em memória, incluindo asserção falha, passo indefinido e recusa de uma execução totalmente filtrada, sem `.feature`. Não estabelecem compatibilidade universal com Cucumber, suporte estável a todas as construções Gherkin, aceite humano autenticado ou suficiência das verificações de um produto real. Regras, backgrounds, scenario outlines, um documento sem cenários e hooks que marcam cenários como ignorados não foram exercitados nesta matriz Python. A seleção de cenários, os filtros e os estados não executados precisam continuar explícitos em qualquer adaptador posterior.
