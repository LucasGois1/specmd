# Orientações para agentes

## Estado do repositório

Este projeto está na etapa de documentação e pesquisa técnica. O núcleo e os plugins não estão implementados. Protótipos em `research/` não constituem suporte produtivo. Preserve a distinção entre diretrizes da conversa, desenho técnico proposto, decisões pendentes e evidências realmente produzidas.

A autorização para criar ou editar documentação não deve ser apresentada como um recibo de aceite contratual. Nunca fabrique aprovação, assinatura, execução de testes ou suporte de integração.

## Regras centrais do desenho

- O Markdown é a fonte canônica de requisitos e cenários.
- A solução não deve exigir arquivos `.feature`, nem sua geração como etapa obrigatória de execução. Integração por parser/adaptador em memória exige validação técnica.
- Alterações de comportamento relevantes precisam de uma origem identificável; escrever um teste ou documentar depois não autoriza uma nova regra de produto.
- Aceite humano, classificação documental e dispensa devem estar vinculados ao conteúdo revisado e a uma autoridade fora do alcance do agente.
- Mudança de contrato exige revisão do aceite; mudança de código exige renovar as evidências pertinentes.
- Cache e inventário são reconstruíveis e não constituem autoridade de aprovação.
- Aguardar decisão humana é diferente de declarar uma tarefa concluída.
- Hooks disponíveis e capacidade de bloqueio devem ser verificados por plataforma e versão. Não invente nomes de eventos ou APIs como se estivessem confirmados.

## Trabalho nos documentos

- Escreva em português; preserve identificadores estáveis e links relativos.
- Mantenha requisitos e seus cenários no mesmo Markdown.
- Use Gherkin em português com a declaração `# language: pt` nos exemplos.
- Registre mudanças normativas e decisões pendentes de forma visível.
- Identifique comandos, schemas e fluxos ainda não implementados como propostas.
- Não adicione licenças, assinaturas, regras de proteção remota ou políticas de aprovação como se já tivessem sido escolhidas ou instaladas.
- Ao relatar verificações, informe somente o que foi efetivamente executado e seu alcance.
