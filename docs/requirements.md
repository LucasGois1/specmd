# Requisitos e cenários do SpecMD

**Estado:** requisitos da direção definida em [D-021](decisions.md) (23/10/2026). O SpecMD ajuda o agente a manter a documentação canônica e o software alinhados; ele não audita nem aprova. Requisitos marcados como **proposta** ainda não estão implementados; o [estado da implementação](implementation-status.md) distingue o que existe.

Os IDs `SMD-REQ-*` e `SMD-SCN-*` são estáveis. Requisitos do desenho anterior (aceite assinado, autoridade, revisão no navegador, gate protegido) foram removidos por D-021 e permanecem no histórico do Git.

## SMD-REQ-001 — Markdown canônico e execução sem `.feature`

Requisitos e cenários residem no mesmo Markdown, que é a fonte canônica das regras de negócio. A execução lê os cenários do Markdown e os entrega ao motor em memória, sem exigir arquivos `.feature` no projeto nem gerá-los temporariamente.

```gherkin
# language: pt
Funcionalidade: Documentação como fonte canônica

  @SMD-REQ-001 @SMD-SCN-101
  Cenário: Executar cenários escritos no Markdown
    Dado um documento com um requisito e seu cenário Gherkin
    Quando os cenários do projeto são executados
    Então o resultado aponta o caminho e a linha do cenário no Markdown
    E nenhum arquivo .feature é criado
```

## SMD-REQ-002 — Descoberta dos documentos

Qualquer Markdown do projeto entra na análise, inclusive arquivos novos ainda não versionados. Arquivos de projeto comuns (README, CHANGELOG, LICENSE, instruções de agentes) ficam fora por padrão. Outros documentos que não descrevem comportamento do sistema (guias de setup, notas) ficam fora pelo `.specmdignore` opcional na raiz, com padrões no estilo `.gitignore`. O agente adiciona entradas quando é claro e pergunta ao dev quando há dúvida.

```gherkin
# language: pt
Funcionalidade: Descoberta de documentos

  @SMD-REQ-002 @SMD-SCN-102
  Cenário: Documento novo entra na análise
    Dado um projeto com o SpecMD ativo
    Quando o agente cria um Markdown que não está versionado
    Então o documento aparece na análise da documentação

  @SMD-REQ-002 @SMD-SCN-103
  Cenário: Documento de referência não exige cenários
    Dado um guia de setup listado no .specmdignore
    Quando a documentação é analisada
    Então o guia não gera pendência de cenários
```

## SMD-REQ-021 — Feedback sobre documentação sem cenários

Depois de qualquer trabalho em Markdown, o agente recebe as pendências do documento alterado: requisito sem cenário, documento comportamental sem bloco Gherkin, Gherkin inválido ou IDs duplicados. O feedback orienta a confirmar os requisitos com o dev e escrever os cenários, a adicionar o documento ao `.specmdignore` quando não descreve comportamento, ou a perguntar ao dev em caso de dúvida.

```gherkin
# language: pt
Funcionalidade: Documentação sem cenários

  @SMD-REQ-021 @SMD-SCN-104
  Cenário: Requisito sem cenário logo após a edição
    Dado que o agente escreveu um requisito sem cenário
    Quando a ferramenta de edição termina
    Então o agente recebe o requisito e a linha que precisam de cenário
    E a orientação para confirmar o comportamento com o dev

  @SMD-REQ-021 @SMD-SCN-105
  Cenário: Pendência lembrada uma vez ao concluir
    Dado que a documentação continua com um requisito sem cenário
    Quando o agente tenta concluir
    Então o agente recebe a pendência uma vez
    E pode concluir se tentar novamente sem mudanças
```

## SMD-REQ-022 — Cenários novos aguardam o dev

Cenários novos ou alterados desde a última mensagem do dev podem não ter sido vistos por ele. O agente é orientado a mostrá-los e pedir confirmação antes de implementar. Quando só a documentação mudou, os cenários não são executados ao concluir e o dev vê um aviso de que há cenários aguardando sua confirmação. Quando o código também mudou, os cenários são executados (ver SMD-REQ-023) e o feedback lembra o agente de confirmá-los, caso ainda não tenha feito. A confirmação é uma mensagem do dev, sem assinatura nem registro formal; marcar cenários como `@wip` também é decisão do dev.

```gherkin
# language: pt
Funcionalidade: Confirmação do dev

  @SMD-REQ-022 @SMD-SCN-106
  Cenário: Documentação nova aguarda a confirmação
    Dado que o agente escreveu um cenário novo sem alterar o código
    Quando o agente conclui
    Então os cenários não são executados
    E o dev é avisado de que há cenários aguardando sua confirmação

  @SMD-REQ-022 @SMD-SCN-117
  Cenário: Cenário escrito junto com o código é verificado
    Dado que o dev confirmou no chat os cenários propostos pelo agente
    Quando o agente escreve os cenários e o código no turno seguinte e conclui
    Então os cenários são executados
    E o feedback lembra de confirmar com o dev os cenários que mudaram no turno

  @SMD-REQ-022 @SMD-SCN-107
  Cenário: Mensagem do dev torna os cenários vistos
    Dado que o dev respondeu depois de ver os cenários
    Quando o agente altera o código e conclui
    Então os cenários são executados
```

## SMD-REQ-023 — Execução após mudança de código e feedback acionável

Quando arquivos que não são Markdown mudaram desde a última execução, a conclusão executa os cenários afetados pela mudança (ver SMD-REQ-027), inclusive os escritos no mesmo turno. Cada cenário que não passa volta ao agente com o caminho, a linha, o passo, a mensagem de erro e, para passos sem implementação, um trecho pronto para começar. Sem mudança de código na sessão, nenhuma execução é cobrada.

```gherkin
# language: pt
Funcionalidade: Execução após mudança de código

  @SMD-REQ-023 @SMD-SCN-108
  Cenário: Código que contraria a documentação
    Dado cenários confirmados que passavam
    Quando o agente altera o código e um cenário passa a falhar
    Então o agente recebe o cenário, o passo e a mensagem de erro

  @SMD-REQ-023 @SMD-SCN-109
  Cenário: Passo sem implementação
    Dado um cenário confirmado com um passo sem implementação
    Quando o agente conclui depois de alterar o código
    Então o agente recebe o passo e um trecho de implementação para começar

  @SMD-REQ-023 @SMD-SCN-110
  Cenário: Conversa sem mudança de código
    Dado uma sessão em que o código não mudou
    Quando o agente conclui
    Então nenhum cenário é executado
```

## SMD-REQ-027 — Só os cenários afetados pela mudança

Em projetos grandes, rodar todos os cenários a cada conclusão leva minutos. Ao concluir, o plugin executa só os cenários que a mudança pode afetar: os que executaram uma função alterada, os que leram um arquivo alterado, os novos ou alterados, os que falhavam e os que nunca rodaram. O feedback diz quantos cenários ficaram de fora. Executa todos quando muda o nível do módulo de um arquivo Python usado pelos cenários (imports, constantes, decorators, assinaturas), os passos ou a configuração, e quando não há cobertura: Java, Go, Python anterior a 3.12 ou projeto sem Git. Cenários que iniciam processos ou abrem conexões de rede são sempre executados. Dependências fora do código Python, como variáveis de ambiente ou estado de banco, podem escapar da seleção; `specmd run` executa todos os cenários e serve de rede de segurança no CI, e `specmd run --affected` aplica a mesma seleção da conclusão. Origem: [D-022](decisions.md), confirmado pelo usuário em 24/10/2026.

```gherkin
# language: pt
Funcionalidade: Execução só dos cenários afetados

  @SMD-REQ-027 @SMD-SCN-118
  Cenário: Mudança numa função executa só quem a usa
    Dado cenários verificados de duas regras implementadas em funções diferentes
    Quando o agente altera o corpo de uma das funções e conclui
    Então só os cenários que executaram essa função são executados
    E o feedback informa quantos cenários ficaram de fora

  @SMD-REQ-027 @SMD-SCN-119
  Cenário: Mudança no nível do módulo executa todos
    Dado cenários verificados
    Quando o agente altera uma constante, um import ou a assinatura de uma função e conclui
    Então todos os cenários são executados

  @SMD-REQ-027 @SMD-SCN-120
  Cenário: Cenário que falhava volta a ser executado
    Dado um cenário que falhou na última execução
    Quando o agente altera um arquivo que esse cenário não executa e conclui
    Então o cenário que falhava é executado de novo

  @SMD-REQ-027 @SMD-SCN-121
  Cenário: Sem cobertura, executa todos
    Dado um projeto Go com o bridge Godog configurado
    Quando o agente altera o código e conclui
    Então todos os cenários são executados

  @SMD-REQ-027 @SMD-SCN-122
  Cenário: CLI executa todos
    Dado cenários verificados
    Quando o dev executa specmd run
    Então todos os cenários são executados
```

## SMD-REQ-028 — Cenários confirmados protegidos

Os cenários da última mensagem do dev são a base de comparação. Quando o agente remove um deles, muda um `Então` (o valor esperado), muda um `Dado` ou `Quando`, marca um com `@wip` ou remove um requisito, ele recebe o diff exato logo após a edição, e o dev vê o mesmo resumo quando o agente conclui, mesmo que tudo passe. O aviso é informativo, inclusive quando o próprio dev pediu a mudança. A conclusão volta ao agente, uma vez, só no sinal forte de ajustar o teste ao código: o cenário falhava na última execução e o agente mudou o valor esperado dele e o código no mesmo turno. Origem: [D-023](decisions.md), confirmado pelo usuário em 24/10/2026.

```gherkin
# language: pt
Funcionalidade: Cenários confirmados protegidos

  @SMD-REQ-028 @SMD-SCN-123
  Cenário: Valor esperado alterado aparece para o agente e para o dev
    Dado um cenário que existia na última mensagem do dev
    Quando o agente muda o valor esperado no Então
    Então o agente recebe o cenário com o valor anterior e o novo logo após a edição
    E o dev vê o mesmo resumo quando o agente conclui, mesmo com tudo passando

  @SMD-REQ-028 @SMD-SCN-124
  Cenário: Cenário removido, marcado como @wip ou requisito removido
    Dado cenários e requisitos que existiam na última mensagem do dev
    Quando o agente remove um cenário, marca outro com @wip e remove um requisito
    Então o agente e o dev veem o cenário removido, o cenário marcado e o requisito removido

  @SMD-REQ-028 @SMD-SCN-125
  Cenário: Expectativa ajustada para o código passar volta ao agente
    Dado um cenário que falhou na última execução
    Quando o agente muda o valor esperado dele e o código no mesmo turno e conclui
    Então o agente recebe uma vez o pedido para restaurar o cenário se o dev não pediu a mudança

  @SMD-REQ-028 @SMD-SCN-126
  Cenário: Mudança num cenário que passava é só informada
    Dado um cenário que passava
    Quando o agente muda o valor esperado dele e o código e conclui
    Então o dev vê o resumo da mudança
    E o agente conclui sem nova devolução
```

## SMD-REQ-029 — Documento ignorado que ganha regra

Documentos ignorados, pelo `.specmdignore` ou pelos padrões, continuam sendo lidos de leve. Quando um deles muda e passa a ter um título de requisito (`…-REQ-…`), um bloco Gherkin ou um título com palavra-chave Gherkin (MDG), o agente é avisado logo após a edição, com as duas saídas: mover a regra para um documento de comportamento ou tirar o documento do `.specmdignore` (ou usar `!caminho`), perguntando ao dev em dúvida. Um documento que já tinha esses elementos não gera aviso quando outra parte dele muda. É só aviso: a conclusão não é bloqueada por isso. Origem: [D-024](decisions.md), confirmado pelo usuário em 24/10/2026.

```gherkin
# language: pt
Funcionalidade: Documento ignorado que ganha regra

  @SMD-REQ-029 @SMD-SCN-127
  Cenário: Requisito escrito num documento ignorado
    Dado um guia de setup listado no .specmdignore
    Quando o agente adiciona ao guia um título de requisito ou um bloco Gherkin
    Então o agente é avisado de que o documento está ignorado
    E recebe as saídas: mover a regra ou tirar o documento do .specmdignore, perguntando ao dev em dúvida

  @SMD-REQ-029 @SMD-SCN-128
  Cenário: Exemplo antigo não gera aviso
    Dado um README ignorado que sempre teve um exemplo de Gherkin
    Quando o agente edita outra parte do README
    Então nenhum aviso é dado

  @SMD-REQ-029 @SMD-SCN-129
  Cenário: Aviso não bloqueia a conclusão
    Dado um documento ignorado que ganhou um requisito
    Quando o agente conclui
    Então a conclusão não é bloqueada por isso
```

## SMD-REQ-030 — Adoção em projeto legado

Num projeto que já tem documentação, `/specmd:adopt` (ou `specmd adopt`) lista todos os documentos analisados que ainda não têm cenários ou têm requisitos sem cenário, em ordem de caminho, sem palpite sobre quais parecem ter regras. Ficam fora os ignorados por padrão e os que o time já colocou no `.specmdignore`. O agente apresenta a lista ao dev, que diz quais não descrevem comportamento; o agente grava esses no `.specmdignore`. Depois o agente trata um documento por vez: propõe requisitos e cenários, pede confirmação e segue o ciclo normal de passos, execução e feedback. Não há estado próprio da adoção: rodar a lista de novo mostra o que falta. Quando um cenário que nunca passou falha, o feedback lembra que, se o código já existia e faz outra coisa, é uma divergência entre documentação e código, e o agente pergunta ao dev qual dos dois vale antes de mudar qualquer um. Marcar `@wip` continua sendo decisão do dev. Origem: [D-025](decisions.md), confirmado pelo usuário em 24/10/2026.

```gherkin
# language: pt
Funcionalidade: Adoção em projeto legado

  @SMD-REQ-030 @SMD-SCN-130
  Cenário: Lista de documentos para adoção
    Dado um projeto com documentos sem cenários, um README e um .specmdignore do time
    Quando o dev pede a adoção
    Então o agente recebe todos os documentos sem cenários em ordem de caminho
    E a lista não traz os ignorados por padrão nem os que estão no .specmdignore

  @SMD-REQ-030 @SMD-SCN-131
  Cenário: Dev escolhe o que ignorar
    Dado a lista de documentos para adoção
    Quando o dev diz que um guia de setup não descreve comportamento
    Então o agente adiciona o guia ao .specmdignore
    E o guia sai da lista

  @SMD-REQ-030 @SMD-SCN-132
  Cenário: Um documento por vez
    Dado documentos de comportamento sem cenários
    Quando o agente conduz a adoção
    Então ele propõe requisitos e cenários de um documento e pede confirmação antes do próximo

  @SMD-REQ-030 @SMD-SCN-133
  Cenário: Divergência entre documentação e código
    Dado um cenário confirmado que nunca passou e falha porque o código faz outra coisa
    Quando o agente recebe a falha
    Então o feedback orienta a perguntar ao dev qual dos dois vale, sem corrigir sozinho
```

## SMD-REQ-031 — Markdown with Gherkin (`.feature.md`)

Arquivos `*.feature.md` são lidos no formato oficial Markdown with Gherkin (MDG) do Cucumber: palavras-chave como títulos Markdown, passos como itens de lista, tabelas GFM indentadas de 2 a 5 espaços, tags entre crases na linha acima da palavra-chave e prosa livre entre eles. O SpecMD converte o arquivo em Gherkin em memória, linha a linha, e os motores executam sem arquivo `.feature`. Num `.feature.md`, um bloco cercado logo após um passo é o texto (Doc String) do passo; os demais Markdown continuam com blocos cercados `gherkin`. O MDG não tem `# language:`: o idioma vem de `gherkin_language` no `specmd.toml`, e um arquivo cujas palavras-chave não estão no idioma configurado gera um aviso dizendo isso. Títulos com ID de requisito ligam os cenários abaixo deles, inclusive o da `Regra` (`## Regra: PAG-REQ-001 — Estorno`). Origem: [D-026](decisions.md), confirmado pelo usuário em 24/10/2026.

```gherkin
# language: pt
Funcionalidade: Markdown with Gherkin

  @SMD-REQ-031 @SMD-SCN-134
  Cenário: Documento MDG executado com origem no Markdown
    Dado um arquivo .feature.md com prosa, títulos de cenário e passos em lista
    E gherkin_language definido no specmd.toml
    Quando os cenários são executados
    Então cada resultado aponta a linha do cenário no arquivo .feature.md
    E nenhum arquivo .feature é criado

  @SMD-REQ-031 @SMD-SCN-135
  Cenário: Regra com ID vira requisito
    Dado um título "## Regra: PAG-REQ-001 — Estorno" num arquivo .feature.md
    Quando a documentação é analisada
    Então os cenários da regra ficam ligados a PAG-REQ-001

  @SMD-REQ-031 @SMD-SCN-136
  Cenário: Bloco cercado é argumento de passo
    Dado um passo seguido de um bloco cercado num arquivo .feature.md
    Quando o cenário é executado
    Então o passo recebe o conteúdo do bloco como texto

  @SMD-REQ-031 @SMD-SCN-137
  Cenário: Idioma ausente é apontado
    Dado um arquivo .feature.md em português sem gherkin_language configurado
    Quando a documentação é analisada
    Então o agente é avisado de que em MDG o idioma vem do specmd.toml
```

## SMD-REQ-024 — Feedback que não trava a sessão

O plugin nunca encerra a sessão do agente. O mesmo feedback repetido sem mudança, ou o limite de quatro devoluções seguidas, deixa o agente concluir; a contagem recomeça a cada mensagem do dev. Erros internos do plugin viram aviso.

```gherkin
# language: pt
Funcionalidade: Feedback limitado

  @SMD-REQ-024 @SMD-SCN-111
  Cenário: Mesma falha não prende o agente
    Dado que o agente recebeu uma falha ao concluir
    Quando ele tenta concluir de novo com a mesma falha
    Então ele pode concluir e o dev vê um resumo

  @SMD-REQ-024 @SMD-SCN-112
  Cenário: Erro interno vira aviso
    Dado que a verificação falha por um erro interno
    Quando qualquer hook é executado
    Então a sessão continua e um aviso é exibido
```

## SMD-REQ-025 — Contexto no início da sessão

Ao abrir uma sessão, o agente recebe um resumo da documentação canônica (documentos com cenários, pendências, última execução) e as convenções de trabalho: onde escrever requisitos e cenários, quando pedir confirmação ao dev e o que fazer com documentos que não descrevem comportamento.

```gherkin
# language: pt
Funcionalidade: Contexto inicial

  @SMD-REQ-025 @SMD-SCN-113
  Cenário: Resumo ao abrir a sessão
    Dado um projeto com documentação e cenários
    Quando uma sessão do agente começa
    Então o agente recebe a quantidade de documentos e cenários
    E as convenções de trabalho do SpecMD
```

## SMD-REQ-015 — Estado local reconstruível

O plugin guarda apenas observações locais em `.specmd/local/`: a última execução, os cenários vistos pelo dev, a contagem de devoluções e um cache da análise dos documentos. Apagar esse estado é seguro; ele é reconstruído na próxima sessão.

```gherkin
# language: pt
Funcionalidade: Estado local

  @SMD-REQ-015 @SMD-SCN-114
  Cenário: Estado corrompido é ignorado
    Dado um arquivo de estado local inválido
    Quando a documentação é analisada
    Então a análise funciona como em um projeto sem estado
```

## SMD-REQ-026 — Instalação por repositório

Instalar o plugin no escopo do projeto ou local já ativa o SpecMD no repositório, com os padrões; `specmd.toml` e `.specmdignore` são opcionais. `specmd init` (ou `/specmd:init`) declara o marketplace do SpecMD e habilita o plugin na configuração compartilhada do projeto, para que cada pessoa do time só precise aceitar a confiança da pasta. As dependências vêm com o plugin; a máquina precisa de Python 3.11 ou superior.

```gherkin
# language: pt
Funcionalidade: Instalação por repositório

  @SMD-REQ-026 @SMD-SCN-115
  Cenário: Plugin carregado ao abrir o repositório
    Dado um repositório preparado pelo comando de início
    Quando um dev abre o agente na pasta e confia nela
    Então o plugin SpecMD é carregado sem instalação manual
```

## SMD-REQ-020 — Execução em Java, Python e Go

Os cenários executam com motores existentes: Behave em Python, Cucumber-JVM em Java e Godog em Go, cada um recebendo o Gherkin em memória com a origem no Markdown. Cada bridge declara o subconjunto de Gherkin que suporta.

```gherkin
# language: pt
Funcionalidade: Motores por linguagem

  @SMD-REQ-020 @SMD-SCN-116
  Cenário: Bridge executa cenário com origem no Markdown
    Dado um projeto Go com o bridge Godog configurado
    Quando os cenários são executados
    Então cada resultado aponta o caminho e a linha do cenário no Markdown
```
