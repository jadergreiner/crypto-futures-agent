# RELATÓRIO EXECUTIVO — AGENTE AUTÔNOMO CRYPTO USDT-M

Data: 2026-02-17 (UTC)

Exchange: Binance USDT-M Futures
Moeda Base: USDT

## 0. Validação de Suficiência da Modelagem de Dados

Status: PARCIALMENTE SUFICIENTE para o formato esperado.

Cobertura disponível (OK):

- wallet_balance, available_balance, margin_used, unrealized_pnl (via API Binance)
- realized_pnl_24h e funding_paid_24h (via income history)
- posições abertas (side, notional, margin, leverage, entry, mark, pnl, liquidation)
- aprendizado por símbolo (outcomes e reward por ativo em 24h)
- confiança média por símbolo (via snapshots)

Lacunas de modelagem (N/D no relatório):

- equity_24h_ago (não há série histórica de equity persistida)
- max_drawdown_current (não há métrica consolidada persistida no banco)
- duration_minutes e rr_ratio confiáveis para trades fechados (não há fechamento consolidado por trade no schema atual)

## 1. Resumo Executivo

Nas últimas 24h, o agente apresentou alta atividade operacional, com geração intensa de snapshots e captura de aprendizado por ativo. Houve lucro realizado modesto (+0.95 USDT), porém P&L em aberto fortemente negativo, resultando em patrimônio líquido (equity) negativo no instante do relatório. O risco agregado permanece elevado pela combinação de alta alavancagem média e quantidade de posições abertas.

## 2. Performance Financeira

Equity Total Atual: -46.28 USDT
Equity 24h Anteriores: N/D

Variação Absoluta: N/D
Retorno Diário: N/D

P&L Realizado (24h): +0.95 USDT
P&L em Aberto: -213.04 USDT

Funding Pago/Recebido: -0.82 USDT

Retorno Sobre Patrimônio Total: N/D

Observação: Total P&L (realizado + aberto) = -212.09 USDT.

## 3. Capital e Margem

Margem Utilizada: 164.86 USDT
Capital Disponível (HOLD): 22.39 USDT

Percentual Alocado: N/D (equity atual negativo distorce a razão)
Percentual em HOLD: N/D (mesma limitação)

Indicadores auxiliares sobre wallet balance:

- Alocação sobre wallet balance: 98.85%
- HOLD sobre wallet balance: 13.42%

Alavancagem Média (posições abertas): 10.68x

## 4. Estatísticas Operacionais (24h)

Trades Fechados: 5 (fonte: execution_log, ação CLOSE executada)

Proxy de resultado de fechamento (income REALIZED_PNL, 24h):

- Entradas de resultado: 26
- Taxa de acerto (proxy): 65.38% (17 ganhos / 9 perdas)
- P&L Médio por entrada realizada: +0.0366 USDT
- Relação Risco/Retorno Média: N/D (não há RR por trade consolidado)

Melhor Trade (proxy): KAVAUSDT +1.1502 USDT
Pior Trade (proxy): ETCUSDT -1.6509 USDT

## 5. Posições Abertas Relevantes

Principais posições por impacto de P&L em aberto:

- BTRUSDT | SHORT | Notional 96.98 USDT | PnL -52.22 USDT | Liq 0.495635 | Distância liq 155.02%
- BROCCOLI714USDT | LONG | Notional 122.70 USDT | PnL -40.53 USDT | Liq N/D | Distância liq N/D
- PTBUSDT | LONG | Notional 153.95 USDT | PnL -33.22 USDT | Liq N/D | Distância liq N/D
- 1000PEPEUSDT | SHORT | Notional 60.38 USDT | PnL -9.39 USDT | Liq 0.016104 | Distância liq 259.76%
- AAVEUSDT | SHORT | Notional 64.17 USDT | PnL -8.22 USDT | Liq 440.931148 | Distância liq 243.56%
- ZECUSDT | SHORT | Notional 44.52 USDT | PnL -7.46 USDT | Liq 1295.615564 | Distância liq 351.03%
- MERLUSDT | SHORT | Notional 25.11 USDT | PnL -5.50 USDT | Liq 0.477396 | Distância liq 622.32%
- OGNUSDT | SHORT | Notional 40.75 USDT | PnL -5.12 USDT | Liq 0.120415 | Distância liq 381.66%

## 6. Aprendizado do Modelo por Ativo

ICPUSDT:

- Aprendizado dominante e consistente no período (53 outcomes em 24h).
- Taxa de acerto observada: 100% (53 wins, 0 losses).
- Reward médio elevado (+9.6657), indicando sinal recorrente favorável no contexto observado.

BARDUSDT:

- Sequência de resultados adversos no período (7 losses em 24h).
- Reward médio negativo (-5.8780), sugerindo baixa robustez no regime atual.
- Indica necessidade de reduzir exposição/ajustar critérios de entrada para este ativo.

BELUSDT:

- Amostra pequena, porém negativa (2 losses em 24h).
- Reward médio negativo (-5.0254).
- Requer mais dados antes de concluir padrão estrutural estável.

KNCUSDT:

- Amostra mínima, positiva (1 win).
- Reward médio +7.7691.
- Ainda sem significância estatística para decisão de escala.

NILUSDT:

- Amostra mínima, negativa (1 loss).
- Reward médio -0.6164.
- Necessário ampliar janela para validar comportamento.

Confiança Atual do Modelo (média em snapshots 24h, top recorrentes):

- GMTUSDT: 0.1725 (~1.73/10)
- OPUSDT: 0.1689 (~1.69/10)
- ICPUSDT: 0.2031 (~2.03/10)

## 7. Avaliação de Risco

Drawdown Atual: N/D (não consolidado no schema atual)
Exposição Total: N/D oficial; proxy notional aberto ~1908.32 USDT em snapshots recentes

Risco de Liquidação: MODERATE (com base nos dados disponíveis)

Comentário executivo de risco:

- Há 66 posições abertas com alavancagem média alta (10.68x).
- Equity negativo no momento do relatório é sinal crítico de capital sob estresse.
- Distâncias até liquidação disponíveis não mostram concentração em faixa crítica <20% (0/52), porém há ativos sem preço de liquidação reportado, o que limita a precisão da leitura.

## 8. Evolução do Sistema de Aprendizagem

Ajustes Detectados:

- Forte concentração de aprendizado em ICPUSDT (dominância de outcomes positivos).
- Padrão de aprendizado adverso em BARDUSDT e BELUSDT nas últimas 24h.

Melhorias Observadas:

- Persistência contínua de snapshots e outcomes (64 labels em 24h).
- Captura de sinais com reward alto em ativos específicos (ICPUSDT).

Itens pendentes de modelagem para elevar qualidade executiva do relatório:

- Persistir equity histórico em série temporal para retorno diário e drawdown exatos.
- Persistir ciclo completo de trade (abertura/fechamento) com duração e RR por trade.
- Consolidar exposição percentual oficial por carteira em tempo real.

## 9. Conclusão Executiva

Eficiência financeira (24h): fraca no estado atual da carteira, pois o lucro realizado não compensa o forte P&L negativo em aberto.
Controle de risco: pressionado; a estrutura atual de alavancagem e quantidade de posições exige redução de exposição.
Evolução do modelo: presente e mensurável, porém concentrada em poucos ativos; há sinais de sobredependência de ICPUSDT.
Sustentabilidade da estratégia: requer ajuste imediato de risco e melhoria de modelagem de dados para governança financeira robusta.
Perspectiva próximas 24h: priorizar desalavancagem, reduzir ativos com aprendizado adverso recorrente e manter monitoramento reforçado de capital/equity.
