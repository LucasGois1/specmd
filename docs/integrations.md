---
specmd:
  schema: 1
  id: SMD-DOC-INTEGRATIONS
  kind: reference
  exemption_reason: "Guia de integração e limites; requisitos canônicos permanecem em requirements.md."
---

# Integrações com agentes e CI

O núcleo experimental compartilha inventário, revisão, execução e decisão entre CLI e adaptadores. Comece pelo [quickstart](quickstart.md) e consulte o [estado de implementação](implementation-status.md).

| Componente | Responsabilidade |
| --- | --- |
| Scanner | Inventário Markdown, classificação declarada, IDs/Gherkin e manifesto determinístico. |
| Revisão | Snapshot, texto integral, diffs e decisão explícita vinculada à versão. |
| Autoridade | Assinatura e verificação usando confiança externa ao projeto; modo local demonstrativo. |
| Runners | Blocos em memória, subprocessos e correspondência exata das instâncias esperadas. |
| Lifecycle | Associação de aceite, contrato, código, testes, configuração, rastreabilidade e execução. |
| Adaptador | Tradução dos estados para eventos e respostas do host. |
| CI | `verify --require-real` com confiança externa e verificador protegido pelo operador. |

A separação entre autoridade e código do agente depende de permissões externas. Uma assinatura válida prova posse de chave e integridade do conteúdo assinado; não prova, sozinha, identidade humana, leitura ou correção dos requisitos.

## Execução canônica

O Markdown mantém requisitos e cenários juntos. O scanner entrega blocos com caminho, bloco, linha e conteúdo; a ponte executa sua representação em memória. Nenhuma etapa exige gravar `.feature`, inclusive temporário.

Python usa Behave real e steps do projeto em subprocesso. Não carrega automaticamente `behave.ini`, filtros, dry-run ou `environment.py`. Java e Go usam comandos de ponte configurados explicitamente. Confira o subconjunto de cada executor: aceitar `Rule` ou Outline no scanner não garante execução universal.

O protocolo JSON da ponte usa `schema: 1`, `features` e `expected_scenarios`. A saída informa modo, dry-run, falha do motor, instâncias, origem e passos. O núcleo recusa JSON inválido, timeout, processo não zero, IDs ausentes/duplicados/desconhecidos, origem divergente e cenários ou passos pendentes, indefinidos ou ignorados. Zero cenários não satisfaz o contrato.

`language: "mock"` exige `evidence.allow_mock: true` e mantém resultado simulado. Uma ponte pode mentir sobre a execução: seu código, os steps e o verificador também precisam de revisão e proteção operacional.

## CLI e estados

Schema 1 preserva o scanner inicial; schema 2 habilita revisão, rastreabilidade e execução. A CLI oferece `inventory`, `review`, `run`, `check`, `status`, `audit` e `verify`; `demo` prepara um projeto descartável. `review --prepare` gera uma proposta sem aceitá-la.

| Estado | Interpretação |
| --- | --- |
| `inactive` | Sem opt-in e sem decisão de conclusão. |
| `error` | Verificação ou configuração não pôde ser determinada. |
| `blocked` | Estrutura, vínculos, política ou execução insatisfatórios. |
| `waiting_human_review` | A versão exige decisão válida; devolver controle ao responsável. |
| `awaiting_evidence` | Falta execução atual para o snapshot aceito. |
| `demo_passed` | Fluxo demonstrativo satisfeito; modo `demo`, assurance `local_demo`. |
| `passed` | Execução real fresca, confiança externa protegida e rastreabilidade estrita. |

O JSON também expõe `may_complete`. Em `demo_passed`, esse campo vale no contexto demonstrativo e não libera integração produtiva. O encerramento de um turno pelo host não substitui o veredito do núcleo.

## Codex e Claude Code

O pacote Codex declara `SessionStart`, `PreToolUse`, `PostToolUse` e `Stop`. Início e pós-ferramenta apresentam o estado; pré-ferramenta consulta autorização; a parada fornece feedback ou devolve o controle. O [guia do Codex](experimental-codex.md) cobre build, instalação e revisão dos handlers em `/hooks`.

No CLI `0.163.0`, ensaios com executável e pacote instalados observaram dispatch, alteração por ferramenta e retomada após bloqueio. As respostas vieram de backend HTTP determinístico simulado. O serviço de modelo real retornou `401`; interpretação por LLM e concessão humana de trust pela UX ainda exigem provas próprias. Evidências identificam seus bundles; mudanças no lifecycle precisam ser revalidadas.

As provas nativas anteriores cobrem `SessionStart`, `PostToolUse` e `Stop`. O novo `PreToolUse` possui testes de protocolo e requer comprovação separada no host; não se atribui a ele a cobertura daqueles ensaios.

Confiar o hook e aceitar o contrato são decisões distintas. O plugin não deve conceder seu próprio aceite. O hash nativo do handler não garante automaticamente os bytes de todo script chamado.

Claude Code possui manifesto e adaptação de protocolo com testes locais. Eles não comprovam instalação ou dispatch no produto. Payloads efetivos, trust, retomada e alcance do bloqueio precisam de ensaio no host; não se presume equivalência com o Codex.

## Revisão no navegador

A interface local mostra texto integral, classificações, justificativas de dispensa, requisitos, cenários, hashes e diffs para o último snapshot aceito. A decisão exige identificador declarado e confirmação explícita. Uma proposta alterada durante a revisão deve ser recarregada.

Loopback e token de sessão protegem a interação local; não autenticam uma pessoa contra outro processo do mesmo usuário. A autoridade fora do projeto pode continuar acessível ao agente por permissões do sistema. Esse fluxo não declara `human_authenticated`.

A experiência completa de uma pessoa lendo, decidindo e retomando o agente continua uma validação necessária. Testes HTTP da interface não demonstram que alguém leu o contrato.

## CI e fronteira protegida

O workflow de exemplo chama `specmd verify --require-real` para projetos ativados, usando trust externo provisionado pelo operador. Esse caminho exige aprovação válida para o snapshot, execução real fresca e rastreabilidade estrita. Cache e mock não bastam.

O comando não constitui uma implantação segura por si só. O agente ou a mudança revisada não pode controlar o verificador confiável, a chave, o trust store ou as regras que tornam o check obrigatório. A proteção de branches e a separação operacional precisam de revisão na plataforma escolhida.

Veja [Arquitetura](architecture.md), [Aceite e confiança](approval-and-trust.md), [Requisitos](requirements.md) e [Plano de validação](validation-plan.md).
