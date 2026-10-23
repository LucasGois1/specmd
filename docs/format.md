# Formato da documentação

A documentação é Markdown comum. O SpecMD lê os blocos ```gherkin de cada documento e os executa em memória; não há arquivo `.feature` para manter.

## Quais documentos entram

Todo Markdown do projeto (`.md` e `.markdown`), inclusive arquivos novos ainda não versionados, exceto:

- arquivos ignorados pelo Git;
- diretórios de dependências e builds (`node_modules`, `.venv`, `build`, `dist` e semelhantes) e o estado `.specmd/`;
- o que casar com o `.specmdignore` na raiz.

O `.specmdignore` usa padrões no estilo `.gitignore`: comentários com `#`, `!` para negar, `/` no fim para diretórios, `/` no início ou no meio para ancorar na raiz, `*`, `?` e `**`. Ele lista o Markdown que não descreve comportamento do sistema:

```gitignore
README.md
CHANGELOG.md
docs/setup/
notes/**/*.md
```

`specmd init` cria um `.specmdignore` com os casos óbvios. O agente adiciona entradas quando é claro que o documento não descreve comportamento e pergunta ao dev quando há dúvida.

## O que um documento precisa ter

Pelo menos um bloco ```gherkin com cenários. Frontmatter é opcional e ignorado.

Requisitos com ID são opcionais e recomendados. Um título que começa com um ID terminado em `-REQ-…` declara o requisito; o prefixo é livre:

````markdown
## PAG-REQ-001 — Estorno em até 7 dias

Um pagamento pode ser estornado em até 7 dias corridos.

```gherkin
# language: pt
Funcionalidade: Estorno

  Cenário: Estorno no sexto dia
    Dado um pagamento feito há 6 dias
    Quando o cliente pedir o estorno
    Então o estorno deve ser aprovado
```
````

## Ligação entre cenário e requisito

- Um cenário fica ligado ao requisito do título mais próximo acima do seu bloco. Subtítulos dentro da seção (por exemplo `### Cenários`) mantêm a ligação.
- Uma tag `@…-REQ-…` no cenário, na regra ou na funcionalidade substitui a ligação pela posição.
- Cenários antes de qualquer requisito são do documento como um todo.
- Requisito sem cenário é uma pendência, e tag que aponta para um requisito inexistente também.

## Identidade dos cenários

- Sem tag, o ID é `caminho::nome do cenário`. Nomes repetidos no mesmo documento recebem `#2`, `#3` e assim por diante.
- Uma tag `@…-SCN-…` define um ID estável, que precisa ser único no projeto. Um cenário aceita no máximo uma.
- Cada linha de `Exemplos` de um `Esquema do Cenário` vira uma instância `ID:row:<exemplo>:<linha>`.

## Linguagem e cenários em andamento

- `# language: pt` no bloco define o idioma do Gherkin; `gherkin_language = "pt"` no `specmd.toml` define o padrão do projeto.
- Cenários com uma tag de `wip_tags` (padrão `@wip`) aparecem na documentação mas não são executados nem cobrados.

## specmd.toml

Todas as chaves são opcionais; o arquivo só precisa existir para ativar o SpecMD.

```toml
gherkin_language = "pt"
wip_tags = ["wip"]

[run]
on_stop = true      # executar os cenários ao concluir, quando o código mudou
timeout = 120

[[runners]]
id = "python"
language = "python"
steps = "tests/steps"            # environment.py fica no diretório pai
python = ".venv/bin/python"      # opcional
```

- O runner Python usa, nesta ordem: `python` do runner, `$VIRTUAL_ENV`, `.venv` ou `venv` do projeto, desde que consiga importar `behave`. Se nenhum servir, usa o interpretador do plugin.
- Com vários runners, cada cenário vai para o primeiro cujo `paths` casar com o documento.
- Java e Go usam `command` com o bridge; veja [adapters](../adapters/README.md).
- Chaves do desenho anterior (`project_id`, `repository_id`, `traceability`, `evidence`) são aceitas e ignoradas.
