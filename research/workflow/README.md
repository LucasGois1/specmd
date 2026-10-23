# Validação do ciclo local

Na raiz, após `pip install -e .`:

```sh
python scripts/test_local.py
```

O relatório padrão fica em `.specmd/local/test-report.json`, reconstruível e sem autoridade de aceite. `--output` permite salvar uma evidência da execução em outro caminho.

Os testes usam agente e navegador simulados: nenhum LLM é chamado e nenhuma leitura humana é alegada. Exercitam HTTP de loopback, decisões Ed25519, execução Python/Behave em subprocesso, invalidação, falhas e retomada através dos adaptadores de protocolo. Chaves, recibos e aceites das fixtures são criados em diretórios temporários descartáveis, fora de qualquer contrato real do projeto.

Java e Go possuem validações separadas em [adapters](../../adapters/README.md). Testes de protocolo não comprovam dispatch nativo do Claude (veja [research/claude](../claude/README.md)), confiança humana pela UX do Codex ou isolamento contra outro processo com as mesmas permissões.

Depois de compilar os executáveis de exemplo, é possível reproduzir a integração dos motores reais com o núcleo:

```sh
python research/workflow/probe_bridges.py \
  --go-executable /caminho/specmd-go-example \
  --java-runner adapters/java/run.sh
```

`evidence/native-bridges.json` registra sucesso, falha de asserção e passo indefinido nas duas linguagens. `evidence/local-tests.json` registra a suíte do ciclo, e `evidence/codex-installation.json` identifica o bundle instalado nesta etapa. Nenhum desses arquivos concede aceite aos requisitos do SpecMD.

Para testar a experiência pessoalmente, use o [guia rápido](../../docs/quickstart.md). O comando `specmd demo` cria a proposta e a autoridade local de demonstração, e para antes de conceder qualquer aceite.
