# SpecMD — produto

**Estado:** direção definida em [D-021](decisions.md) (23/10/2026). O [estado da implementação](implementation-status.md) separa o que já existe do que está planejado.

## Problema

No desenvolvimento com agentes de IA, a intenção do dev, a documentação, o código e os testes divergem com facilidade. O agente esquece uma condição, interpreta uma regra de outro jeito ou inventa uma regra que ninguém pediu e escreve testes que a protegem. Quando os testes ficam em arquivos `.feature` separados, a divergência ganha mais um lugar para acontecer: o `.feature` muda e a documentação não, ou o requisito muda e os cenários ficam para trás.

## Proposta

O SpecMD é um plugin para agentes de programação (Claude Code e Codex), instalado no repositório, que mantém a documentação canônica e o software alinhados por meio da colaboração entre o agente e o dev.

- A documentação Markdown, com cenários Gherkin embutidos, é a fonte canônica das regras de negócio. Requisito e teste de aceitação ficam no mesmo arquivo.
- O plugin faz checagens determinísticas em momentos-chave e devolve feedback objetivo ao agente, estimulando-o a iterar e conferir antes de seguir.
- Quem define o que é certo é o dev, pela documentação que confirmou na conversa. O plugin não aprova nem audita; ele verifica se documentação e código concordam.

## Fluxo

1. O dev conversa com o agente, e o agente escreve a documentação no repositório.
2. Qualquer trabalho em Markdown dispara a análise. Documento sem cenários volta ao agente, que confirma os requisitos com o dev e escreve os cenários, adiciona o documento ao `.specmdignore` quando ele não descreve comportamento, ou pergunta ao dev em caso de dúvida.
3. O agente mostra os cenários e pergunta se está tudo certo. A confirmação é a resposta do dev.
4. O agente implementa. Ao concluir, os cenários são executados; os que estão sem implementação ou falhando voltam ao agente com o passo e o erro, até ficar tudo verde.

## Limites

- Os cenários verificam o que descrevem. Eles não provam que a documentação cobre toda a intenção do dev nem que as asserções dos passos são fortes; isso continua na revisão humana, normalmente no PR.
- O plugin ajuda um agente bem-intencionado a não errar; ele não impede um agente determinado a contorná-lo.
- Hooks não são equivalentes entre hosts; cada integração é verificada por plataforma e versão.

## Antecedentes

Documentação executável, rastreabilidade e gates já existem em outras ferramentas ([pesquisa](positioning.md)). O valor a demonstrar é a experiência integrada: a documentação como fonte única e o feedback no momento certo durante o trabalho do agente.
