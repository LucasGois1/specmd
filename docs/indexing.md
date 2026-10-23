# Inventário e análise incremental

> **Histórico, anterior à [D-021](decisions.md).** Este documento descreve o desenho com aceite assinado, autoridade, trust e bloqueio de implementação, removido em 23/10/2026. Para o produto atual, veja [produto](product.md) e [estado da implementação](implementation-status.md).

> Estado: inventário determinístico e snapshots locais implementados experimentalmente. O cache é consultivo e a fonte sempre é reanalisada. Reutilização confiável de parsing, análise semântica incremental e ganhos de desempenho ainda não foram demonstrados. Consulte o [estado de implementação](implementation-status.md).

O SpecMD descobre os documentos do projeto e produz um inventário de caminhos, conteúdo e relações declaradas. A evolução pretendida é evitar reinterpretações desnecessárias; o incremento atual prioriza reconstrução e conferência da fonte antes de qualquer decisão.

O objetivo é economizar leitura, parsing, chamadas a modelos e execução de verificações, preservando a detecção de novos documentos e mudanças que exigem revisão.

## Três responsabilidades separadas

| Responsabilidade | Conteúdo | Autoridade |
| --- | --- | --- |
| Inventário | Caminhos, conteúdo observado, classificação declarada e relações conhecidas. | Descreve o estado encontrado; pode ser reconstruído. |
| Aceite | Identidade autenticada, escopo e versão exata aprovados pelo humano. | Vem do mecanismo protegido de aprovação. |
| Cache de análise | Atualmente, snapshots dos documentos extraídos e diagnósticos com identidade de fonte/parser. | Consultivo: não é usado para omitir a validação da fonte nem para conceder aceite. |

Um documento analisado pode continuar sem aprovação. Um documento aprovado pode precisar de nova análise porque uma dependência ou política mudou. Apagar ou editar o índice local não pode transformar uma pendência em aprovação.

Os contratos de confiança são detalhados em Aceite e confiança (removido por [D-021](decisions.md)); a composição geral está em [Arquitetura](architecture.md).

## Descoberta e escopo

O scanner só é ativado quando existe `specmd.toml` na raiz. A configuração schema 1 preserva o preflight simples e aceita somente `schema = 1`. A configuração schema 2 exige `project_id`, aceita `repository_id` opcional e acrescenta runners, rastreabilidade e política de evidências. O frontmatter de cada documento permanece `specmd.schema: 1`; são esquemas distintos, descritos em [Formato documental](format.md).

No incremento atual, a descoberta usa `os.walk` ordenado, considera `.md` e `.markdown` sem distinguir caixa na extensão e inclui arquivos locais ainda não adicionados ao Git. Não existem exclusões configuráveis pelo agente. São podados os diretórios de nomes fixos:

```text
.git .hg .svn .venv venv node_modules target __pycache__ .specmd
.pytest_cache .mypy_cache .ruff_cache build dist
```

Links simbólicos de documentos e diretórios dentro do escopo são recusados e não seguidos. Essas podas fazem parte da implementação e precisam entrar na revisão do verificador; não são uma política dinâmica de exclusões já aprovada por um humano.

O inventário deve considerar:

- Documentos versionados no Git.
- Novos documentos locais, inclusive antes de serem adicionados ao Git.
- Alterações staged e unstaged durante a sessão.
- Remoções e renomeações.
- Mudanças na política de descoberta e nas exclusões.

Uma política configurável de exclusões com caminho, justificativa, versionamento e aceite é uma evolução de desenho. Ela não está disponível como mecanismo para retirar arquivos da análise neste incremento.

O `.gitignore` serve ao fluxo do Git e não substitui a descoberta do SpecMD. Markdown próprio em diretórios não podados é encontrado mesmo quando não está versionado ou foi ignorado pelo Git. Ignorar um documento no Git não concede dispensa contratual.

Os caminhos do manifesto são relativos e usam separador `/`. O caminho participa do digest: remover ou renomear um documento muda a identidade do conjunto, mesmo se seus bytes permanecerem iguais. Não há uma promessa de equivalência entre caminhos que diferem apenas em caixa em sistemas de arquivos distintos.

## Classificação e custo de análise

| Situação | Monitoramento | Análise necessária |
| --- | --- | --- |
| Comportamental, aceito e inalterado | Conferir identidade e relações relevantes. | O scanner atual refaz o parsing; reutilização confiável é uma evolução. |
| Comportamental alterado | Registrar a nova versão e invalidar o aceite aplicável. | Reanalisar obrigações, cenários e relações afetadas. |
| Informativo com dispensa aceita, inalterado | Continuar verificando a identidade do conteúdo. | Não exige Gherkin; o scanner ainda confere metadados e conteúdo explícito. Não há análise semântica por IA implementada. |
| Informativo alterado | Tornar a nova versão pendente. | Reavaliar classificação e justificativa; o texto pode ter adquirido regras de comportamento. |
| Novo ou sem classificação | Adicionar ao inventário como pendente. | Propor classificação e submeter a decisão ao usuário. |
| Fora do escopo pelas podas fixas atuais | A política está na versão do verificador. | Não percorrer o conteúdo podado. Exclusões configuráveis aceitas ainda são desenho futuro. |

A dispensa de Gherkin não equivale à exclusão do inventário. Um guia informativo aceito continua monitorado, pois uma edição futura pode introduzir uma regra de negócio.

Documentos mistos exigem vínculos para suas partes comportamentais. A classificação do arquivo inteiro não pode esconder uma obrigação contida em uma seção. O formato dessas declarações é proposto em [Formato documental](format.md).

Um documento `reference` com cabeçalho explícito de requisito ou cerca Gherkin produz conflito de classificação e bloqueio estrutural. O aceite da dispensa integra o fluxo versionado de revisão e assinatura, não uma propriedade autoatribuída no índice.

## Entrada de inventário

Uma entrada implementada pelo scanner contém caminho, SHA-256, ID, classificação, requisitos com linhas e cenários com IDs, blocos, linhas, vínculos e contagem de passos. Essa contagem não indica execução. No schema 2, Outline gera instâncias `<base_id>:row:<exemplo>:<linha de dados>`; cada uma mantém sua identidade-base e a linha da declaração, além da linha concreta da tabela. Requisitos herdados por Rule e Examples continuam explícitos nos registros.

O lifecycle associa separadamente aceites e evidências. A evolução do inventário pretende permitir recuperar também:

- Identificador estável do documento e caminho observado.
- Hash do conteúdo observado e referência ao snapshot de origem.
- Classificação declarada, versão aceita e situação de revisão.
- Identificadores dos requisitos e cenários encontrados.
- Referências a outros documentos, regras compartilhadas e componentes conhecidos.
- Versões de política, parser e analisadores usadas nos resultados derivados.
- Diagnósticos e evidências relacionados, com suas entradas de validade.

Referências a aceites são resolvidas no mecanismo confiável; um campo local como `approved: true` não é prova. Uma relação inferida por IA deve ser distinguida de uma relação declarada ou confirmada. A ausência de uma relação no índice não demonstra ausência de impacto.

## Identidade do conteúdo

A identidade contratual segue a regra descrita em Aceite e confiança (removido por [D-021](decisions.md)). A implementação calcula SHA-256 dos bytes efetivamente lidos do checkout, sem normalizar finais de linha ou reinterpretar o significado do Markdown. O manifesto do scanner tem `schema: 1`, `config_sha256` e a lista ordenada de pares `path`/`sha256`, serializada como JSON UTF-8 com chaves ordenadas e separadores compactos.

No schema 2, o workflow inclui ainda `traceability_sha256`, vinculado ao mapa por padrão em `.specmd/traceability.json`. A pasta `.specmd` fica fora da descoberta de Markdown, mas esse mapa é lido explicitamente pelo lifecycle: sua alteração muda a versão contratual e invalida as evidências correspondentes. O caminho pode ser definido em `traceability.map`; a política estrita exige vínculos de código/testes com requisitos e cenários conhecidos.

`repository_id` permite vincular os recibos a uma identidade lógica estável entre checkouts, sem usar o caminho absoluto como identidade principal. Esse campo não comprova propriedade do repositório nem torna um cache confiável.

Data de modificação, tamanho do arquivo e eventos do sistema podem reduzir trabalho durante uma sessão, mas são indícios. O gate protegido precisa conferir identidades de conteúdo sobre o snapshot efetivo, sem depender exclusivamente desses metadados.

Uma renomeação altera caminho e possivelmente escopo. Mesmo uma futura reutilização de parsing por conteúdo não poderá reutilizar automaticamente o aceite.

## Cache implementado e seus limites

`inspect_project(root)` não escreve cache. A opção explícita `use_cache=True` permite snapshots em `.specmd/cache`. A chave atual inclui SHA-256 do documento, caminho, schema da configuração e fingerprint da versão do scanner/Behave/MarkdownIt/PyYAML.

Esses arquivos são editáveis localmente pelo agente. Por isso, o scanner **sempre lê e reanalisa a fonte** antes de decidir. Conteúdo adulterado ou JSON inválido no cache não remove diagnósticos, não concede aprovação e não marca cenários como executados. O snapshot é atualizado quando difere da análise reconstruída; falhas de cache não mudam o resultado da inspeção. Diretórios de cache simbólicos não são usados para escrita.

Esse mecanismo fornece registros derivados para evolução incremental, mas **não entrega ainda o ganho de evitar parsing**. Não há cache semântico por IA, dependências inferidas, watcher persistente ou limpeza automática de entradas antigas implementados como otimização.

## Invalidação planejada para reutilização confiável

Cada tipo de análise deve declarar suas entradas. Uma chave conceitual pode incluir:

```text
conteúdo + contexto relevante + política + analisador + dependências
```

Isso não fixa um esquema de serialização. A implementação deve documentar quais entradas cada cache usa e produzir resultados reproduzíveis para as verificações determinísticas.

| Mudança | Resultados a invalidar |
| --- | --- |
| Texto do documento | Parsing e análises dependentes do conteúdo; aceite da nova versão fica pendente. |
| Caminho ou escopo | Seleção e análises sensíveis ao contexto; reavaliar vínculo de aceite. |
| Documento referenciado | Análises que utilizaram aquela referência. |
| Classificação ou exclusão | Decisões de aplicabilidade e resultados afetados. |
| Política ou versão de analisador | Resultados calculados sob a versão anterior, conforme suas entradas. |
| Código, steps, fixtures ou configuração de execução | Evidências de teste afetadas, mesmo que os documentos estejam intactos. |

Quando houver reutilização confiável, invalidar todo o cache semântico após uma mudança de política é uma escolha conservadora aceitável. Otimizações posteriores precisam preservar a mesma decisão do processamento completo; a versão atual evita esse risco reanalisando a fonte.

O cache de parsing documental e o cache de execução de testes são distintos. Um documento inalterado não torna atual um resultado de teste executado contra outra versão do código, ambiente ou runner.

## Ciclo incremental pretendido

O fluxo abaixo descreve a evolução desejada, não uma otimização já demonstrada:

1. Descobrir diferenças desde o último estado observado.
2. Atualizar inventário, removendo entradas obsoletas e adicionando arquivos novos.
3. Recalcular as identidades necessárias.
4. Localizar resultados afetados por conteúdo, contexto ou dependências.
5. Reutilizar somente resultados cujas entradas continuem válidas.
6. Executar análises novas e apresentar pendências ao adaptador do agente.

Watchers são gatilhos úteis, mas eventos podem ser perdidos. Uma escrita por shell, outra ferramenta ou outro agente também pode modificar o projeto. Por isso, inicialização, fechamento da tarefa e CI exigem reconciliação com o estado real do escopo.

A implementação atual reconcilia o inventário e refaz o parsing estrutural. Antes da extração para execução, `extract_features` confere uma inspeção fresca, rejeita um manifesto anterior que ficou desatualizado e entrega os blocos em memória com linhas preenchidas para preservar a origem no `.md`.

## Determinismo e assistência por IA

São verificações determinísticas: descobrir arquivos pela política, comparar hashes, validar referências e IDs, conferir sintaxe Gherkin e relacionar evidências aos snapshots declarados.

São análises heurísticas planejadas: sugerir classificação, encontrar possíveis requisitos em prosa, apontar lacunas entre texto e cenários e sugerir relações de impacto. O scanner atual não executa um modelo para realizar essas inferências. Quando disponíveis, tais sugestões apoiarão a revisão, sem estabelecer automaticamente a completude do contrato ou conceder dispensa.

Markdown permanece a fonte canônica. Parsing e indexação não devem exigir arquivos `.feature`, inclusive como etapa temporária obrigatória da execução. O índice pode guardar uma representação derivada dos blocos Gherkin em memória ou cache reconstruível, mantendo a origem no `.md`.

## Medição e evolução

Uma otimização futura deve comparar processamento completo e incremental sobre os mesmos snapshots. A decisão de aprovação/bloqueio precisa ser equivalente para as verificações determinísticas. Os testes atuais verificam que o cache adulterado não muda a decisão e que conteúdo novo, alterado, removido ou renomeado muda o inventário quando aplicável; não constituem um benchmark de performance.

Medir tempo de descoberta, leitura e parsing, taxa de reutilização, chamadas a modelos evitadas, duração de reconciliação e divergências entre as duas formas de processamento. Casos de teste e experimentos estão em [Plano de validação](validation-plan.md).

O formato de uma reutilização confiável e a necessidade de banco local devem ser escolhidos após observar volume, concorrência e custo de reconstrução. São dados derivados; a história contratual e os aceites precisam continuar recuperáveis sem esse cache. O [estado de implementação](implementation-status.md) registra os limites operacionais do lifecycle e dos verificadores atuais.
