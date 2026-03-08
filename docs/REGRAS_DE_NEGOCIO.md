# 📋 Regras de Negócio — Crypto Futures Agent

**Versão:** 0.1.0
**Data:** 07 MAR 2026
**Linguagem:** Português (não-técnico)
**Responsável:** Business Analyst, Gestor de Risco

---

## 🎯 Propósito

Documentar as **regras operacionais da negócio** em linguagem clara e não-técnica, sem jargão técnico. Estas regras são invioláveis e devem ser observadas em toda decisão de design e implementação.

---

## 📌 ESTRUTURA DE CAPITAL

### R1: Limite de Alavancagem

**Regra:** O agente nunca pode operar com alavancagem superior a **5x** em qualquer posição.

**Motivo:** Proteção contra liquidação acidental e eventos de cisne negro.

**Aplicação:**
- Cada posição aberta deve ter tamanho ≤ 20% do capital (equivalente a 5x risco)
- Sistema deve validar antes de enviar ordem para Binance
- Se capital cair, posições devem ser redimensionadas automaticamente

**Referência:** [C4_MODEL.md nível 3 — Risk Manager](C4_MODEL.md), [ADR-003](ADR_INDEX.md#adr-003)

---

### R2: Capital Mínimo Operacional

**Regra:** Operações param se capital cair abaixo de **50% do capital inicial**.

**Motivo:** Preservar capital para recuperação e evitar gestão de contas muito pequenas.

**Aplicação:**
- Diariamente, ao abrir primeira operação, validar capital
- Se capital < 50% inicial, enviar alerta e parar novas operações
- Apenas fechar posições abertas (não abrir novas)

**Referência:** [MODELAGEM_DE_DADOS.md — Account State](MODELAGEM_DE_DADOS.md)

---

## 🛑 GESTÃO DE RISCO

### R3: Stop Loss Obrigatório

**Regra:** Toda posição aberta **deve ter** um stop loss definido antes da execução.

**Motivo:** Limitar perdas em cada operação e evitar surpresas de market gap.

**Aplicação:**
- Stop loss = Entrada ± Risco (tipicamente 1-2% do capital por operação)
- Sistema bloqueia ordem se SL não estiver configurado
- SL é colocado junto com a ordem inicial

**Referência:** [REGRAS_DE_NEGOCIO.md — R6: Take Profit](REGRAS_DE_NEGOCIO.md)

---

### R4: Take Profit Recomendado

**Regra:** Todas as posições devem ter **alvo de lucro** (take profit). Trailing stop permitido.

**Motivo:** Garantir que ganhos sejam capturados e evitar "ficar esperando mais".

**Aplicação:**
- TP padrão = Entrada + (SL distance × 2.0) — Ratio 1:2 Risk:Reward
- Trailing stop ativado quando P&L > +0.5% (acompanha preço)
- Possibilidade de TP manual (operador pode ajustar)

**Referência:** [R3: Stop Loss Obrigatório](REGRAS_DE_NEGOCIO.md#r3-stop-loss-obrigatório)

---

### R5: Limite de Drawdown

**Regra:** Se drawdown MÁXIMO > **8%** em 24h ou **-15%** cumulativo no mês, operações param.

**Motivo:** Proteção psicológica e financeira contra sequências de perdas.

**Aplicação:**
- Monitoramento em tempo real do drawdown
- Alerta em -5%, -8%, -12%, -15%
- Parada automática em -15% com comunicação (Telegram)
- Reset do contador ao fim do dia/mês (movendo o benchmark)

**Referência:** [MODELAGEM_DE_DADOS.md — Performance Metrics](MODELAGEM_DE_DADOS.md)

---

### R6: Limite de Posições Abertas

**Regra:** Máximo de **4 posições simultâneas** em qualquer momento.

**Motivo:** Diversificação, gestão de risco, e evitar corridas contra o capital.

**Aplicação:**
- Sistema conta posições abertas (long + short)
- Se 4 posições abertas, agenda não aceita nova ordem
- Posições podem ser em pares diferentes (BTC, ETH, etc.)

**Referência:** [C4_MODEL.md nível 3 — Order Executor](C4_MODEL.md)

---

## 📊 REGRAS DE OPERAÇÃO

### R7: Tamanho Mínimo de Operação

**Regra:** Nenhuma operação pode ter **valor < USD 100** (notional).

**Motivo:** Minimizar overhead de taxa e operações irrelevantes.

**Aplicação:**
- Antes de enviar ordem, validar: `posição_notional >= 100 USD`
- Se operação resultaria em < 100 USD, rejeitar ou aumentar tamanho

**Referência:** [MODELAGEM_DE_DADOS.md — Order Schema](MODELAGEM_DE_DADOS.md)

---

### R8: Intervalo Mínimo Entre Operações

**Regra:** Não abrir nova posição em mesmo par antes de **12 horas** após fechamento anterior.

**Motivo:** Evitar over-trading, permitir reflexão, preservar capital.

**Aplicação:**
- Sistema registra timestamp de fechamento
- Antes de aceitar nova ordem no mesmo par, valida: `agora - timestamp_fechamento >= 12h`
- Pares diferentes não têm restrição

**Referência:** [MODELAGEM_DE_DADOS.md — Trade History](MODELAGEM_DE_DADOS.md)

---

### R9: Corte de Viés (Bias Control)

**Regra:** Se agente perder **3 operações seguidas**, ativa "modo cauteloso" por 4 horas.

**Motivo:** Quebra sequências de perdas; evita "retaliation trading".

**Aplicação:**
- Contador de trades perdedores consecutivos
- Se contador = 3, parar operações por 4 horas (mas manter existentes)
- Reset contador ao ganhar

**Referência:** [REGRAS_DE_NEGOCIO.md — R13: Gestão de Emoção](REGRAS_DE_NEGOCIO.md#r13-pausa-pós-sequência-de-perdas)

---

## 💡 REGRAS DE INTELIGÊNCIA

### R10: Validação de Sinal Mínimo

**Regra:** Não abrir posição se confiança do sinal < **0.65** (65%).

**Motivo:** Filtrar sinais fracos; focar em operações de alta probabilidade.

**Aplicação:**
- Modelo PPO retorna probabilidade de confiança
- Se confiança ≤ 0.65, sinal é descartado
- Logging de sinais rejeitados para análise posterior

**Referência:** [FEATURES.md — F-ML1: Model Inference](FEATURES.md)

---

### R11: Consenso Multi-Timeframe

**Regra:** Operações de longo prazo (>1 dia) requerem **"bullish" em D1 + H4**.

**Motivo:** Reduzir whipsaws; aumentar probabilidade de sucesso.

**Aplicação:**
- Antes de abrir, verificar bias em D1 (diário) e H4 (4 horas)
- Se D1 "bearish" e H4 "neutral", não operar long
- Operações short exigem consenso inverso

**Referência:** [C4_MODEL.md nível 3 — SMC Analyzer](C4_MODEL.md)

---

### R12: Descanso Pós-Múltiplas Operações

**Regra:** Se 3+ operações fechadas em 24h, agente "descansa" por 2 horas.

**Motivo:** Evitar fadiga de decisão e over-trading.

**Aplicação:**
- Contador de operações fechadas em 24h rolling window
- Se contador ≥ 3, parar novos sinais por 2 horas
- Contador reset a cada 24h

**Referência:** [README.md — Round 5 Stay-Out Learning](../README.md)

---

## 🔄 REGRAS DE CICLO DE VIDA

### R13: Pausa Pós-Sequência de Perdas

**Regra:** Se **2+ dias consecutivos** com saldo negativo, operações param por 1 dia.

**Motivo:** Permitir recalibração; evitar "chasing losses".

**Aplicação:**
- Log de PnL diário (ganho/perdido)
- Se P&L dia 1 < 0 E P&L dia 2 < 0, parar operações dia 3
- Contador reset ao ganhar positivo

**Referência:** [REGRAS_DE_NEGOCIO.md — R9: Corte de Viés](REGRAS_DE_NEGOCIO.md#r9-corte-de-viés-bias-control)

---

### R14: Revisão Semanal (Manual)

**Regra:** Operador **deve revisar** semanalmente: P&L, trades, métricas, anomalias.

**Motivo:** Detectar falhas, recalibração necessária, oportunidades.

**Aplicação:**
- Dashboard com resumo semanal (script `weekly_report.py`)
- Revisão de 15-30 minutos com operador
- Ajustes de parâmetros registrados em DECISIONS.md

**Referência:** [USER_MANUAL.md — Rotate Checkpoint](USER_MANUAL.md)

---

### R15: Reset de Modelo

**Regra:** Se Sharpe < 0.5 por **2 semanas consecutivas**, modelo deve ser retreinado.

**Motivo:** Adaptar a mudanças de regime de mercado; evitar degradação de performance.

**Aplicação:**
- Monitoramento de Sharpe rolling 14-dias
- Alertar ao atingir < 0.5
- Task de retreinamento gerada automaticamente
- Executar TASK-005 nova rodada

**Referência:** [ROADMAP.md — v0.4 Continuous Learning](ROADMAP.md)

---

## Governança Operacional (TASK-005 v2)

### Política de Métricas de Aceite (PPO)

**Regra operacional:** `shaped_reward` é sinal interno de aprendizado e não pode ser usado para GO/NO-GO.

**Aplicação obrigatória:**
- Critérios de aceite do modelo (Sharpe, Win Rate, Profit Factor, Drawdown, perdas consecutivas) devem usar `raw_pnl/equity`.
- Treino e validação final devem usar a mesma fórmula (fonte única em `agent/rl/metrics_utils.py`).
- Relatórios devem incluir `metric_sanity_passed`, `vol_floor`, `num_trades_evaluated` e `stop_reason`.

**Motivo:** Evitar métricas artificiais e divergência entre treino e validação.

---

## 🔐 REGRAS INVIOLÁVEIS (NÃO PODEM SER DESABILITADAS)

Estas 5 regras são **críticas** e **nunca** podem ser desabilitadas, mesmo manualmente:

| # | Regra | Por quê | Verificação |
|---|-------|--------|-----------|
| **R3** | Stop Loss Obrigatório | Perda unbounded é existencial | Cada ordem bloqueada sem SL |
| **R4** | Capital Mínimo > 50% | Recuperação impossível abaixo | Parada automática invariante |
| **R5** | Limite de Drawdown -15% | Conta é destruída | Circuit breaker no bootstrap |
| **R1** | Alavancagem ≤ 5x | Liquidação força-close | Validador pré-ordem |
| **R6** | Max 4 posições | Insolvência de capital | Contador de posições |

---

## 🗂️ Mapeamento: Regras → Documentação Técnica

| Regra | Implementação Técnica | Arquivo | Função/Classe |
|-------|----------------------|---------|---------------|
| R1-R2 | Risk Manager | `risk/risk_manager.py` | `RiskValidator.validate_order()` |
| R3-R4 | Order Executor | `execution/order_executor.py` | `OrderExecutor.place_order()` |
| R5 | Performance Monitor | `monitoring/performance.py` | `DrawdownMonitor` |
| R6 | Position Tracker | `monitoring/position_tracker.py` | `PositionManager.count_open()` |
| R7-R8 | Trade State Machine | `execution/trade_state.py` | `TradeState.validate()` |
| R9-R12 | Heuristics Engine | `agent/heuristics.py` | `HeuristicFilter` |
| R13-R15 | Agent Loop | `agent/agent.py` | `CryptoAgent.step()` |

---

## 📍 Impactos Históricos de Mudanças

Quando uma nova feature impacta regras:

- ✅ **TASK-011** (F-12b Symbols) → Validou R1, R6, R7 em 200 símbolos
- ✅ **Issue #64** (Telegram Alerts) → Implementou notificação de R5 (drawdown alerts)
- 🔄 **TASK-005** (PPO Training) → Impacta R10, R11, R12 e governança de métricas (v2)

---

## 🚀 Próximos Passos

- [ ] Integrar checklist de regras no template de PR
- [ ] Criar testes unitários para cada regra em `tests/test_rules.py`
- [ ] Treinamento de squad em regras de negócio (1h workshop)
