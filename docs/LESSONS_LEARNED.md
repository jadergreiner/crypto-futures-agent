# 🎓 Lições Aprendidas — Crypto Futures Agent

## ✅ O que está bom

1. **Arquitetura em camadas bem separada** — cada módulo tem responsabilidade clara (data, indicators, agent, execution, monitoring). Isso facilita evolução independente.

2. **Feature Engineering robusto** — 104 features cobrindo preço, EMAs, indicadores, SMC, sentimento, macro, correlação, contexto e posição. A normalização está bem pensada (z-score, min-max, tanh, clip).

3. **SMC completo** — implementação rara e valiosa de Smart Money Concepts algorítmico. Order Blocks, FVGs, BOS, CHoCH, Liquidity Sweeps, Premium/Discount — tudo integrado.

4. **Dry-run mode** — excelente decisão de ter um modo de validação sem API keys. Permite testar o pipeline inteiro localmente.

5. **Risk Manager como camada independente** — regras "invioláveis" separadas da lógica do agente. Isso é crucial para segurança.

## ⚠️ O que precisa atenção

1. **Placeholders em código de produção** — Blocos 7 e 8 do `build_observation` usam valores hardcoded (`[0.0, 0.0, 1.0]` e `[0.0, 0.0]`), mas o `main.py` já passa `multi_tf_result`. A integração está "quase lá" mas não completa.

2. **Bug silencioso no RewardCalculator** — A lógica `if r_multiple > 2.0` seguida de `elif r_multiple > 3.0` faz com que o bonus de 3R+ nunca seja aplicado. Isso pode distorcer significativamente o aprendizado.

3. **Backtester e Walk-Forward são esqueletos** — Parecem completos pela interface mas não fazem nada de fato. Treinar sem backtest é perigoso.

4. **Sem testes unitários reais** — O `test_e2e_pipeline` é mais um script de integração. Faltam testes para cada componente isolado.

5. **Overfitting potencial** — Sem walk-forward real, qualquer modelo treinado pode estar overfitado nos dados de treino. Priorizar validação out-of-sample antes de qualquer operação real.

## 💡 Insights Estratégicos

1. **Simplifique o action space inicialmente** — 5 ações (HOLD, LONG, SHORT, CLOSE, REDUCE_50) pode ser demais para primeiros treinamentos. Considere começar com 3 (HOLD, LONG, SHORT) e adicionar CLOSE/REDUCE depois.

2. **Curriculum Learning** — Treine primeiro em mercados tendenciais (mais fáceis), depois em range/choppy. O `market_regime` já fornece essa classificação.

3. **Foque em 1-3 símbolos** — BTCUSDT, ETHUSDT e talvez SOLUSDT. Não tente operar todos os símbolos de uma vez. Complexidade mata.

4. **Capital mínimo no live** — Comece com $100-200 em live. O objetivo inicial é validar que as ordens executam corretamente, não ganhar dinheiro.

5. **Log tudo** — Cada decisão do agente, cada observation, cada reward. Sem isso, é impossível debugar por que o agente tomou uma decisão ruim.
