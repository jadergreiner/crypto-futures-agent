# Prompt Otimizado para Copilot (Pos-task no M2 model-driven)

Contexto: Finalizei a task [NOME_DA_TASK] no projeto crypto-futures-agent.

Acoes de Arquiteto:

1. Coerencia arquitetural

- Verifique se a mudanca respeita o fluxo model-driven:
  estado -> inferencia -> safety envelope -> execucao/reconciliacao ->
  aprendizado.
- Garanta que a decisao de trade permanece no modelo
  (OPEN_LONG, OPEN_SHORT, HOLD, REDUCE, CLOSE).

1. Guard-rails e risco

- Confirme que `risk/risk_gate.py` e `risk/circuit_breaker.py` permanecem
  ativos nos caminhos alterados.
- Em caso de ambiguidade operacional, confirmar comportamento fail-safe.

1. Qualidade de codigo e testes

- Verifique padrao Python (PEP 8) e type hints nas funcoes novas.
- Garanta testes relevantes em pytest para o comportamento alterado.

1. Sincronizacao de docs

- Se houve impacto em arquitetura/regras/dados, sincronize:
  `docs/ARQUITETURA_ALVO.md`, `docs/REGRAS_DE_NEGOCIO.md`,
  `docs/MODELAGEM_DE_DADOS.md`.
- Registre alteracoes em `docs/SYNCHRONIZATION.md` com tag `[SYNC]`.

1. Saida obrigatoria

- Liste os arquivos alterados.
- Informe riscos de regressao.
- Indique testes executados e resultado.
- Diga se esta pronto para commit (`[SYNC]`, `[FIX]`, `[FEAT]`, etc.).
