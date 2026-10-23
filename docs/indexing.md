# Inventário e análise incremental

> Estado: proposta inicial para revisão. O índice descrito aqui ainda não foi implementado. Classificações e exemplos não constituem aceite humano.

O SpecMD precisa descobrir os documentos do projeto e manter seu estado sem reinterpretar todo o repositório a cada interação. O inventário fornece os caminhos e relações; o processamento incremental reutiliza resultados que continuam válidos.

O objetivo é economizar leitura, parsing, chamadas a modelos e execução de verificações, preservando a detecção de novos documentos e mudanças que exigem revisão.

## Três responsabilidades separadas

| Responsabilidade | Conteúdo | Autoridade |
| --- | --- | --- |
| Inventário | Caminhos, conteúdo observado, classificação declarada e relações conhecidas. | Descreve o estado encontrado; pode ser reconstruído. |
| Aceite | Identidade autenticada, escopo e versão exata aprovados pelo humano. | Vem do mecanismo protegido de aprovação. |
| Cache de análise | AST, requisitos extraídos, diagnósticos e resultados associados às entradas utilizadas. | Acelera análises; nunca concede aceite. |

Um documento analisado pode continuar sem aprovação. Um documento aprovado pode precisar de nova análise porque uma dependência ou política mudou. Apagar ou editar o índice local não pode transformar uma pendência em aprovação.

Os contratos de confiança são detalhados em [Aceite e confiança](approval-and-trust.md); a composição geral está em [Arquitetura](architecture.md).

## Descoberta e escopo

A política inicial deve definir quais arquivos Markdown próprios do projeto pertencem ao inventário e quais caminhos estão excluídos. A seleção precisa ser aprovada e protegida: o agente não pode excluir um caminho para esconder uma alteração.

O inventário deve considerar:

- Documentos versionados no Git.
- Novos documentos locais, inclusive antes de serem adicionados ao Git.
- Alterações staged e unstaged durante a sessão.
- Remoções e renomeações.
- Mudanças na política de descoberta e nas exclusões.

Dependências vendorizadas, diretórios de pacotes e documentação gerada podem ser excluídos por política explícita. Não é necessário percorrer todos os arquivos de uma dependência excluída a cada hook. A política registra o caminho, a justificativa e a versão da exclusão; o gate confere que a política em vigor é autorizada.

O `.gitignore` serve ao fluxo do Git e não substitui a política do SpecMD. Ignorar um documento no Git não deve conceder uma dispensa contratual. O tratamento de arquivos Markdown não versionados e ignorados dentro de caminhos próprios precisa ser definido na política e verificado no protótipo.

O MVP pode começar com `.md`. Suporte a outras extensões Markdown, normalização de caminhos, links simbólicos e diferenças de caixa entre sistemas de arquivos são decisões explícitas de implementação; não devem ampliar ou reduzir silenciosamente o universo protegido.

## Classificação e custo de análise

| Situação | Monitoramento | Análise necessária |
| --- | --- | --- |
| Comportamental, aceito e inalterado | Conferir identidade e relações relevantes. | Reutilizar resultados compatíveis. |
| Comportamental alterado | Registrar a nova versão e invalidar o aceite aplicável. | Reanalisar obrigações, cenários e relações afetadas. |
| Informativo com dispensa aceita, inalterado | Continuar verificando a identidade do conteúdo. | Dispensar reinterpretação semântica enquanto as entradas continuarem válidas. |
| Informativo alterado | Tornar a nova versão pendente. | Reavaliar classificação e justificativa; o texto pode ter adquirido regras de comportamento. |
| Novo ou sem classificação | Adicionar ao inventário como pendente. | Propor classificação e submeter a decisão ao usuário. |
| Fora do escopo por política autorizada | Conferir a validade da política de exclusão. | Não analisar o conteúdo excluído. |

A dispensa de Gherkin não equivale à exclusão do inventário. Um guia informativo aceito continua monitorado, pois uma edição futura pode introduzir uma regra de negócio.

Documentos mistos exigem vínculos para suas partes comportamentais. A classificação do arquivo inteiro não pode esconder uma obrigação contida em uma seção. O formato dessas declarações é proposto em [Formato documental](format.md).

## Entrada de inventário

Uma entrada deve permitir recuperar, pelo menos:

- Identificador estável do documento e caminho observado.
- Hash do conteúdo observado e referência ao snapshot de origem.
- Classificação declarada, versão aceita e situação de revisão.
- Identificadores dos requisitos e cenários encontrados.
- Referências a outros documentos, regras compartilhadas e componentes conhecidos.
- Versões de política, parser e analisadores usadas nos resultados derivados.
- Diagnósticos e evidências relacionados, com suas entradas de validade.

Referências a aceites são resolvidas no mecanismo confiável; um campo local como `approved: true` não é prova. Uma relação inferida por IA deve ser distinguida de uma relação declarada ou confirmada. A ausência de uma relação no índice não demonstra ausência de impacto.

## Identidade do conteúdo

A identidade contratual deve seguir a regra descrita em [Aceite e confiança](approval-and-trust.md). Para revisões Git, a referência recomendada é o conteúdo exato do snapshot, evitando que conversões de finais de linha do checkout produzam decisões diferentes entre máquinas.

Data de modificação, tamanho do arquivo e eventos do sistema podem reduzir trabalho durante uma sessão, mas são indícios. O gate protegido precisa conferir identidades de conteúdo sobre o snapshot efetivo, sem depender exclusivamente desses metadados.

Uma renomeação pode reaproveitar o parsing do conteúdo, mas altera caminho e possivelmente escopo. Reutilizar o AST não significa reutilizar automaticamente o aceite.

## Invalidação do cache

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

No MVP, invalidar todo o cache semântico após uma mudança de política é uma escolha conservadora aceitável. Otimizações posteriores precisam preservar a mesma decisão do processamento completo.

O cache de parsing documental e o cache de execução de testes são distintos. Um documento inalterado não torna atual um resultado de teste executado contra outra versão do código, ambiente ou runner.

## Ciclo incremental

1. Descobrir diferenças desde o último estado observado.
2. Atualizar inventário, removendo entradas obsoletas e adicionando arquivos novos.
3. Recalcular as identidades necessárias.
4. Localizar resultados afetados por conteúdo, contexto ou dependências.
5. Reutilizar somente resultados cujas entradas continuem válidas.
6. Executar análises novas e apresentar pendências ao adaptador do agente.

Watchers são gatilhos úteis, mas eventos podem ser perdidos. Uma escrita por shell, outra ferramenta ou outro agente também pode modificar o projeto. Por isso, inicialização, fechamento da tarefa e CI exigem reconciliação com o estado real do escopo.

A reconciliação completa é do inventário protegido. Ela não exige executar novamente toda análise semântica: resultados compatíveis podem continuar sendo reutilizados depois da conferência de identidade.

## Determinismo e assistência por IA

São verificações determinísticas: descobrir arquivos pela política, comparar hashes, validar referências e IDs, conferir sintaxe Gherkin e relacionar evidências aos snapshots declarados.

São análises heurísticas: sugerir classificação, encontrar possíveis requisitos em prosa, apontar lacunas entre texto e cenários e sugerir relações de impacto. Essas sugestões apoiam a revisão, sem estabelecer automaticamente a completude do contrato ou conceder dispensa.

Markdown permanece a fonte canônica. Parsing e indexação não devem exigir arquivos `.feature`, inclusive como etapa temporária obrigatória da execução. O índice pode guardar uma representação derivada dos blocos Gherkin em memória ou cache reconstruível, mantendo a origem no `.md`.

## Medição e evolução

O protótipo deve comparar processamento completo e incremental sobre os mesmos snapshots. A decisão de aprovação/bloqueio precisa ser equivalente para as verificações determinísticas.

Medir tempo de descoberta, leitura e parsing, taxa de reutilização, chamadas a modelos evitadas, duração de reconciliação e divergências entre as duas formas de processamento. Casos de teste e experimentos estão em [Plano de validação](validation-plan.md).

O MVP pode usar um índice local simples. O formato persistido e a necessidade de banco local devem ser escolhidos após observar volume, concorrência e custo de reconstrução. São dados derivados; a história contratual e os aceites precisam continuar recuperáveis sem esse cache.
