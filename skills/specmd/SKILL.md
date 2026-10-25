---
name: specmd
description: Convenções do SpecMD para documentação com cenários BDD. Use ao escrever ou alterar documentação de comportamento, requisitos ou cenários Gherkin, ao decidir se um Markdown precisa de cenários, ou quando o SpecMD devolver pendências ou cenários falhando.
---

# Trabalhar com o SpecMD

A documentação Markdown é a fonte canônica das regras de negócio. Os cenários Gherkin ficam no próprio documento e são, ao mesmo tempo, a especificação e o teste de aceitação. Não crie arquivos `.feature`.

## Escrever documentação de comportamento

- Descreva cada regra num documento. Um requisito pode ter ID no título, com prefixo livre: `## PAG-REQ-001 — Estorno em até 7 dias`.
- Logo abaixo do requisito, escreva um bloco ```gherkin com cenários concretos (valores reais, casos de borda). Os cenários abaixo de um título de requisito ficam ligados a ele; uma tag `@PAG-REQ-001` muda a ligação.
- Use `# language: pt` no bloco quando escrever em português.
- Cenários que ainda não devem ser cobrados levam `@wip`, mas só quando o dev decidir. Não marque `@wip` por conta própria: cenários que aguardam confirmação já não são cobrados.

## Confirmar com o dev

- Depois de escrever ou mudar cenários, mostre-os ao dev e pergunte se estão corretos antes de implementar. Aponte ambiguidades (limites, arredondamentos, exceções).
- Não mude um cenário existente para fazer o código passar sem confirmar com o dev: se o código pedido contraria a documentação, pergunte se a regra mudou.

## Markdown que não descreve comportamento

- README, CHANGELOG, guias de setup, notas e ADRs técnicos vão para o `.specmdignore` na raiz (padrões no estilo `.gitignore`).
- Se for claramente o caso, adicione você mesmo. Em dúvida, pergunte ao dev se o documento precisa de cenários; se descrever comportamento, recomende escrevê-los.

## Feedback do SpecMD

- Depois de editar Markdown, o SpecMD aponta documentos sem cenários, requisitos sem cenário e Gherkin inválido.
- Se você remover um cenário, mudar o que ele espera, marcá-lo com `@wip` ou remover um requisito, o SpecMD mostra a mudança para você e para o dev. Se um cenário que falhava teve o valor esperado alterado junto com o código, ele pede para restaurar o cenário, a menos que o dev tenha pedido a mudança.
- Se um documento do `.specmdignore` passar a declarar requisitos ou cenários, mova a regra para um documento de comportamento ou tire o arquivo do `.specmdignore`.
- Num projeto com documentação antiga, `/specmd:adopt` lista os documentos sem cenários. Separe com o dev o que vai para o `.specmdignore` e trate um documento por vez. Se um cenário que nunca passou falha porque o código faz outra coisa, é divergência: pergunte ao dev qual vale antes de mudar qualquer um dos dois.
- Ao concluir uma implementação, ele executa os cenários afetados pela mudança e devolve o cenário, o passo, a linha, a mensagem de erro e, para passos sem implementação, um trecho para começar. Implemente até ficar verde.
- Para conferir a qualquer momento, sem instalar nada, use `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/specmd_cli.py" check --root "$(pwd)"` (pendências e última execução) ou `... run --root "$(pwd)"` (executa todos os cenários; com `--affected`, só os afetados pela mudança). O início da sessão traz o mesmo comando com o caminho completo.
