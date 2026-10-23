# SpecMD

Documentação canônica em Markdown, aceite humano versionado e evidências de execução para desenvolvimento com agentes de IA.

> **Estado do projeto:** implementação experimental do ciclo completo para experimentar localmente: contratos Markdown, revisão no navegador, decisões assinadas por versão, execução de cenários, invalidação e hooks para agentes. A autoridade criada pela demonstração é local e não autentica uma pessoa nem isola suas permissões das do agente. O [guia rápido](docs/quickstart.md) permite testar a experiência; o [estado da implementação](docs/implementation-status.md) separa funcionamento, evidência e limitações. Publicar documentação não constitui aceite contratual.

```bash
git clone https://github.com/LucasGois1/specmd.git
cd specmd
git switch main
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
specmd demo --dest /tmp/specmd-cart
export SPECMD_TRUST_STORE=/tmp/specmd-cart-authority/trust.json
specmd review --root /tmp/specmd-cart --authority /tmp/specmd-cart-authority --trust "$SPECMD_TRUST_STORE"
```

Revise o contrato no navegador e registre sua decisão. Em outro terminal, com a mesma instalação e variável de confiança, execute `specmd run --root /tmp/specmd-cart` e `specmd check --root /tmp/specmd-cart`. O resultado local esperado é `demo_passed`. Os cenários Python executam código real; a garantia do aceite permanece uma demonstração local. Nenhum comando acima emite aceite automaticamente.

## O problema

Agentes podem deixar de atender requisitos documentados, interpretar uma regra incorretamente ou introduzir comportamentos que ninguém solicitou. Um teste escrito pelo agente pode proteger uma suposição indevida e passar a funcionar como uma especificação implícita. Código, testes e documentação podem concordar entre si e ainda divergir da intenção do usuário.

O projeto propõe tornar explícita a relação entre **intenção reconhecida, contrato aceito, comportamento implementado e evidência atual de verificação**.

## A proposta

- Escrever explicações, requisitos e cenários Gherkin no mesmo Markdown.
- Executar os cenários a partir desse Markdown, sem depender de arquivos `.feature` mantidos pelo usuário ou de sua geração como etapa obrigatória.
- Identificar cada documento e requisito, mantendo vínculos com cenários e mudanças de comportamento.
- Exigir aceite humano autenticado para uma versão específica do contrato, inclusive suas classificações e dispensas.
- Detectar alterações por hashes determinísticos e invalidar aceites ou evidências conforme o que mudou.
- Impedir a conclusão de tarefas quando faltarem aceites ou verificações exigidas pela política.
- Integrar o mecanismo ao trabalho de agentes por adaptadores e hooks, com uma checagem protegida de integração.
- Manter um inventário incremental para evitar análises repetidas sem ignorar mudanças relevantes.

Gherkin é a linguagem dos cenários; Cucumber é um possível mecanismo de execução. **Não se presume suporte nativo de Cucumber a qualquer Markdown.** O núcleo executa Python/Behave diretamente e conecta [bridges Java e Go](adapters/README.md) pelo mesmo protocolo JSON em memória, preservando a origem no `.md`. Os [protótipos anteriores](docs/runner-feasibility.md) registram a pesquisa que fundamentou essas integrações.

Python, Java e Go usam motores e integração próprios. Não se exige arquivo `.feature` nem sua geração temporária. Consulte os limites de formato e integração de cada bridge antes de configurar um projeto.

Documentação executável e vários mecanismos de rastreabilidade e gates já têm antecedentes. A [pesquisa de posicionamento](docs/positioning.md) registra a sobreposição e recomenda comparar integrações existentes antes de construir novos subsistemas. O possível benefício do SpecMD é uma hipótese a validar, sem alegação de novidade ou exclusividade.

## Fluxo implementado para experimentação

1. Descobrir os documentos próprios do projeto e aplicar a política de escopo.
2. Propor a classificação de documentos novos ou alterados.
3. Discutir ambiguidades e escrever cenários para os requisitos comportamentais.
4. Apresentar a versão e seu diff ao usuário para aceite.
5. Implementar o comportamento acordado e executar as verificações.
6. Relacionar resultados ao contrato e à revisão de código efetivamente verificados.
7. Liberar a conclusão somente quando as condições aplicáveis forem atendidas.

Documentos informativos podem receber dispensa de Gherkin, mas essa classificação também exige aceite e continua sendo monitorada. Um agente pode aguardar uma decisão humana sem declarar a tarefa concluída.

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [Handoff para o agente local](HANDOFF.md) | Contexto completo da conversa, decisões, implementação, lacunas e roteiro de validação com Lucas. |
| [Guia rápido](docs/quickstart.md) | Demonstração, revisão, execução e instalação local. |
| [Estado da implementação](docs/implementation-status.md) | Recursos implementados e limites de confiança/validação. |
| [Produto](docs/product.md) | Problema, público, proposta, limites e oportunidades. |
| [Requisitos e cenários](docs/requirements.md) | Obrigações identificadas e critérios de aceite em Gherkin no próprio Markdown. |
| [Formato documental](docs/format.md) | Proposta de metadados, IDs, blocos e documentos mistos. |
| [Arquitetura](docs/architecture.md) | Componentes, fluxos e vínculos entre contrato, aceite e evidência. |
| [Aceite e confiança](docs/approval-and-trust.md) | Hashes, identidades, permissões, auditoria e proteção contra bypass. |
| [Indexação](docs/indexing.md) | Inventário, cache, invalidação e reconciliação. |
| [Integrações](docs/integrations.md) | Núcleo CLI e adaptadores propostos para agentes e CI. |
| [Plano de implementação](docs/roadmap.md) | Marcos, dependências e entregas verificáveis. |
| [Plano de validação](docs/validation-plan.md) | Experimentos, casos negativos e métricas. |
| [Pesquisa dos runners](research/README.md) | Hipóteses, protótipos e evidências por linguagem. |
| [Resultados de viabilidade](docs/runner-feasibility.md) | Execuções reais em Java, Python, Go e baseline MDG em JavaScript. |
| [Preflight experimental no Codex](docs/experimental-codex.md) | Instalação local por clone e build, opt-in, CLI, hooks e limites do primeiro incremento. |
| [Pesquisa do host Codex](research/codex/README.md) | Interfaces, descoberta, trust e evidências da investigação anterior à validação completa do adaptador. |
| [Posicionamento e antecedentes](docs/positioning.md) | MDG, rastreabilidade, gates existentes e critérios para reduzir ou integrar a solução. |
| [Decisões e pendências](docs/decisions.md) | Diretrizes da discussão e escolhas ainda abertas. |

Exemplos de formato: [contrato comportamental](examples/cancellation.contract.md) e [documento informativo](examples/editor-setup.reference.md). São ilustrações sem aceite autenticado ou execução implementada.

## Limites das garantias

- Hash identifica conteúdo; autenticação e separação de permissões estabelecem quem pode aceitá-lo.
- Um bloco Gherkin presente não demonstra que todos os requisitos foram identificados.
- Testes passando demonstram os cenários exercitados, sem comprovar toda a intenção do usuário.
- Análise com IA pode sugerir lacunas e contradições; suas inferências não concedem aceite.
- Hooks locais ajudam a orientar o agente. Bloqueios contra bypass precisam de uma fronteira de permissões que o agente não possa alterar.
- A autoria declarada em um commit Git não substitui a identidade autenticada de quem submeteu ou aprovou a mudança.

## Testes e limites

Execute `python -m unittest discover -s tests -v`. Há testes com protocolos de agentes simulados, HTTP local real, assinaturas reais e execução real de passos Python. Os testes não inventam uma leitura humana: decisões automáticas pertencem apenas às fixtures. Os bridges nativos possuem suas próprias verificações e instruções em `adapters/`.

`python scripts/test_local.py` executa a suíte e grava um relatório JSON reproduzível; veja [o escopo da validação](research/workflow/README.md).

`schema = 1` preserva o preflight anterior, que nunca autoriza conclusão. `schema = 2` habilita o ciclo de revisão e execução. `demo_passed` serve à validação local; `verify --require-real` exige uma decisão de uma autoridade externa configurada como protegida e execução real nova. A implantação precisa proteger o verificador, a configuração e a autoridade das permissões do agente; esse isolamento não é instalado por um flag ou por um hook.

O [guia do Codex](docs/experimental-codex.md) registra instalação e trust. O CLI nativo já foi instalado e seus hooks exercitados com backend determinístico. A tentativa anterior com o serviço de modelo retornou `401`. No Claude Code, sessões headless com modelo real despacharam os quatro hooks e o bloqueio de código antes do aceite ([evidência](research/claude/README.md)); a experiência interativa e a instalação por marketplace permanecem sem validação. A utilidade do produto continua dependendo de um piloto comparativo; funcionalidades existentes não demonstram superioridade sobre ferramentas anteriores.
