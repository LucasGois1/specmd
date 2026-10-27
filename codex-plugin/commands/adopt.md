---
description: Adota o SpecMD num projeto que já tem documentação, um documento por vez
---

Conduza a adoção do SpecMD neste repositório com o dev. A documentação Markdown que já existe vira a fonte canônica, com cenários Gherkin no próprio documento.

1. Na raiz do projeto, liste o que falta:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/specmd_cli.py" adopt --root "$(pwd)"
   ```

   O resultado traz, em ordem de caminho, os documentos sem cenários e os requisitos sem cenário. Os ignorados por padrão (README, CHANGELOG, instruções de agentes) e os do `.specmdignore` já ficam fora. Não ordene nem descarte documentos por palpite.

2. Mostre a lista ao dev e pergunte quais documentos não descrevem comportamento do sistema (guias de setup, notas, decisões técnicas). Grave no `.specmdignore` da raiz exatamente os que ele indicar. Os demais são documentação de comportamento.

3. Trate um documento por vez. Leia o documento, proponha os requisitos (título com ID, como `## PAG-REQ-001 — Estorno`) e os cenários Gherkin que expressam as regras escritas nele, com exemplos concretos. Aponte ambiguidades (limites, arredondamentos, exceções). Mostre ao dev e só siga depois da confirmação dele; então passe ao próximo documento.

4. Depois da confirmação, escreva os cenários no documento e implemente os passos. Ao concluir, o SpecMD executa os cenários e devolve o que falta ou falha.

5. Se um cenário falha porque o código faz outra coisa, isso é uma divergência entre documentação e código. Não corrija sozinho: mostre ao dev o que a documentação diz e o que o código faz, e pergunte qual dos dois vale.

Para saber o que ainda falta, em qualquer sessão, rode o comando do passo 1 de novo: o progresso é o próprio estado da documentação e do `.specmdignore`. Marcar cenários com `@wip` é decisão do dev.
