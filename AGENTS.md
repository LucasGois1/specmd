# Orientações para agentes

## Estado do repositório

Para continuar o trabalho sem a conversa original, leia [HANDOFF.md](HANDOFF.md). Ele consolida contexto de produto, decisões, evidências, limites e cenários de validação com o agente local. Não constitui aceite dos contratos.

Este projeto implementa um ciclo experimental em Python: inventário Markdown, revisão local, decisões Ed25519 versionadas, execução de cenários, evidência e adaptadores de agentes. Schema1 permanece preflight sem conclusão; schema2 pode produzir demo_passed em demonstração e passed em execução atual sob confiança externa configurada como protegida. O modo local não autentica a identidade humana nem isola a chave do agente. Verificador, configuração e autoridade precisam de uma fronteira de permissões externa para produção. Consulte docs/implementation-status.md. Protótipos em research/ não constituem suporte produtivo. Preserve a distinção entre código, propostas e evidências realmente produzidas.

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
- O opt-in `specmd.toml` e `.specmd/local/status.json` são configuração e observação locais, não aceites. A classificação, a configuração e os vínculos fazem parte do hash revisado. Não transforme estrutura válida em autorização de conclusão.
- Não crie decisões em nome do usuário. Assinaturas e decisões sintéticas em testes devem permanecer em fixtures descartáveis, identificadas como simulação; jamais aplique seus recibos ao produto real.
- Instalação do plugin e trust humano são etapas distintas. Oriente a revisão normal pela UX do host e não fabrique uma ação humana. Em testes já autorizados, uma configuração de confiança restrita à sessão e aos handlers concretos deve ter sua origem documentada; ela não comprova uso da UX nem constitui aceite de requisitos. Não use mecanismos de bypass de trust.
- Gere o pacote por `scripts/build_codex_plugin.py` antes da instalação local. O marketplace aponta para o artefato por allowlist; não empacote o clone inteiro com `.venv`, `.git` ou dados locais.

## Trabalho nos documentos

- Escreva em português; preserve identificadores estáveis e links relativos.
- Mantenha requisitos e seus cenários no mesmo Markdown.
- Use Gherkin em português com a declaração `# language: pt` nos exemplos.
- Registre mudanças normativas e decisões pendentes de forma visível.
- Identifique comandos, schemas e fluxos ainda não implementados como propostas.
- Não adicione licenças, assinaturas, regras de proteção remota ou políticas de aprovação como se já tivessem sido escolhidas ou instaladas.
- Ao relatar verificações, informe somente o que foi efetivamente executado e seu alcance.
