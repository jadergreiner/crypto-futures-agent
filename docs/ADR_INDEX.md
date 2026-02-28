# 📋 ADR Index — Crypto Futures Agent

**Versão:** 0.3.0
**Data:** 28 FEV 2026
**Proprietário:** Arquiteto (#6)

---

## Propósito

ADRs (Architecture Decision Records) documentam as **decisões críticas** de
arquitetura, os **contextos** que levaram a elas e as **consequências** esperadas.

Evita revisões futuras desnecessárias e garante rastreabilidade.

---

## 📚 Index de ADRs

### ADR-001: Seleção de Intervalo de Candlestick (4h)

**Status:** ✅ APROVADA | **Date:** 15 FEV 2026
**Champion:** Data (#11)

**Contexto:**
- Objetivo: 1 ano de dados históricos para backtesting
- Restrição: Latência <100ms de leitura em produção
- Questão: Qual intervalo (1h, 4h, 1d)?

**Decisão:**
**4h candles** (6 por dia = 2.190 candles/ano/símbolo)

**Consequências:**
- ✅ 1Y de dados = 131.400 candles (60 símbolos) = 650 KB SQLite
- ✅ Granularidade suficiente para validação diária
- ❌ Frequency menor que intraday (trade-off aceitável)

**Alternativas Consideradas:**
- 1h: 8.760 candles/ano = 2 MB (descartado: muito grande)
- 1d: 365 candles/ano (descartado: falta granularidade)

**Referência:** [Issue #67](ISSUE_67_DATA_STRATEGY_SPEC.md)

---

### ADR-002: Dual Cache Strategy (SQLite + Parquet)

**Status:** ✅ APROVADA | **Date:** 20 FEV 2026
**Champion:** Architect (#6)

**Contexto:**
- Problema: Dados históricos precisam ser rápidos (READ) + duráveis (WRITE)
- Restrição: Produção + backup em local finito
- Questão: SQLite, Parquet, Redis, ou Hybrid?

**Decisão:**
**SQLite (hot cache) + Parquet (snapshots)**

**Consequências:**
- ✅ SQLite: ACID transactions, queries estruturadas, <100ms reads
- ✅ Parquet: Compressão columnar, snapshots diários, backup S3-ready
- ❌ Dois sistemas = manutenção dupla
- ❌ Sincronização eventual (não realtime)

**Alternativas Consideradas:**
- Redis Only: Rápido mas sem persistência
- PostgreSQL: Maior overhead, overkill para 650 KB
- CSV: Sem índices, lento para 131K registros

**Referência:** [ISSUE_67_DATA_STRATEGY_SPEC.md](ISSUE_67_DATA_STRATEGY_SPEC.md)

---

### ADR-003: LIFO Position Management

**Status:** ✅ APROVADA | **Date:** 18 FEV 2026
**Champion:** Executor (#9)

**Contexto:**
- Problema: 5 posições abertas simultâneas precisam ser fechadas
- Questão: LIFO (Last-In-First-Out), FIFO, ou por P&L?

**Decisão:**
**LIFO Determinístico** — Última aberta fecha primeira.

**Consequências:**
- ✅ Simplicidade: Orden determinística, sem ambiguidade
- ✅ Fairness: Sem viés para posições antigas
- ❌ Possível priorização não-ótima de P&L
- ⚠️ Requer logging preciso de timestamps

**Alternativas Consideradas:**
- FIFO: Favorece posições antigas (favorecimento)
- By P&L: Complexo, pode induzir over-trading
- By Duration: Close de 48h+ (pode gerar debt manual)

**Referência:** [PositionManager](../execution/position_manager.py#L1)

---

### ADR-004: Maximum 3× Leverage (Margin Ratio ≥ 300%)

**Status:** ✅ APROVADA | **Date:** 22 FEV 2026 (Decision #3)
**Champion:** Risk (#13)

**Contexto:**
- Problema: Bloquear de risco de liquidação
- Questão: 2×, 3×, 5×, ou 10× leverage?

**Decisão:**
**Máximo 3× leverage** (margin ratio ≥ 300%)

**Justificativa:**
- Capital inicial: $10,000
- Margin usado máximo: ~$3,000 (3 posições × $500 × 2)
- Buffer: >60% (liquidação típica Binance: 100%)

**Consequências:**
- ✅ Margem de segurança 60%+ contra liquidação
- ✅ Upside limitado mas dowside protegido
- ❌ ROI menor (max 3× retorno)

**Alternativas Consideradas:**
- 2×: Muito conservador, ROI ~66%
- 5×: Perigoso (buffer < 20%, risco crescente)
- 10×: Liquidação quase certa em volatilidade normal

**Referência:** [DECISIONS.md#Decision_3](DECISIONS.md#decision-3-hedge-or-liquidation-strategy)

---

### ADR-005: Deterministic Backtesting (Bar-by-Bar OHLC)

**Status:** ✅ APROVADA | **Date:** 24 FEV 2026
**Champion:** Architect (#6)

**Contexto:**
- Problema: Validar estratégia em histórico sem lookahead bias
- Questão: Event-driven, bar-by-bar, ou stochastic?

**Decisão:**
**Bar-by-bar OHLC replay determinístico**

**Fluxo:**
```
Para cada barra no histórico:
  1. Open price → Strategy execute
  2. High/Low → Check stop loss/take profit
  3. Close price → Fill ordem se acionada
  4. Next barra
```

**Consequências:**
- ✅ Sem lookahead bias (aberto não vê futuro)
- ✅ Determinístico (mesmos dados = mesmos resultados)
- ✅ Reproduzível (não há aleatoriedade)
- ❌ Fills no abrio/fechamento (real world: más)

**Alternativas Consideradas:**
- Event-driven: Complexo com dados comprimidos
- Stochastic: Realista mas não reproduzível

**Reference:** [backtester.py](../backtest/backtester.py#L1)

---

### ADR-006: Paper Trading Mode for Risk Practice

**Status:** ✅ APROVADA | **Date:** 25 FEV 2026
**Champion:** Operações (#15)

**Contexto:**
- Problema: Treinar disciplina de risco sem perder capital real
- Questão: Paper mode opcional vs. obrigatório antes de live?

**Decisão:**
**Paper mode obrigatório** — Simulação 100%, sem ordens reais.

**Ativação:**
```python
# config/params.yaml
mode: "paper"  # ou "live"
```

**Consequências:**
- ✅ Simula fluxo completo (real cache, real gates)
- ✅ Zero risco de capital
- ✅ Logs idênticos (facilita debug)
- ❌ Fills menos realistas (sem slippage real)

**Alternativas Consideradas:**
- Pequeno volume live: 10% capital (ainda risco)
- Sandbox Binance: Possível, mas desatualizado

**Referência:** [execution/order_executor.py](../execution/order_executor.py#L1)

---

### ADR-007: [SYNC] Protocol for Documentation

**Status:** ✅ APROVADA | **Date:** 22 FEV 2026 (Decision #1)
**Champion:** Doc Advocate (#17)

**Contexto:**
- Problema: Documentação fica desatualizada vs. código
- Questão: Como manter síncrono?

**Decisão:**
**[SYNC] tag em commits** + audit trail em `SYNCHRONIZATION.md`

**Padrão:**
```
[SYNC] Descrição breve
- Arquivo1.md: mudança X
- Arquivo2.py: mudança Y
```

**Consequências:**
- ✅ Commit message sinaliza intenção de sync
- ✅ Auditoria em `SYNCHRONIZATION.md`
- ✅ Git history rastreável
- ❌ Manual (não automatizado)

**Alternativas Consideradas:**
- Splinx auto-generation: Adiciona overhead (ignorado)
- GitHub Actions pre-commit: Complexo (rejeitado)

**Referência:** [SYNCHRONIZATION.md](SYNCHRONIZATION.md)

---

### ADR-008: Telegram Bot para Observabilidade Operacional (Issue #64)

**Status:** ✅ APROVADA | **Date:** 28 FEV 2026
**Champion:** The Blueprint (#7)

**Contexto:**

Operador precisa monitorar trading 24/7. Abordagem anterior:
- ❌ Console local insuficiente (operador offline = blind)
- ❌ Sem notificações em tempo real (perda de eventos)
- ❌ Sem persistência de histórico
- ❌ Auditoria manual e demorada

**Questão:** Como notificar operador sobre eventos críticos em tempo real?

**Decisão:**

**Usar Telegram Bot API para envio de alertas em tempo real.**

7 tipos de alertas: execution, pnl, risk, error, daily_summary, custom_message, connection_test.

**Consequências:**

✅ **Positivas:**
- Latência ultra-baixa (<3 segundos)
- Multi-plataforma (mobile, desktop, web)
- Persistência de histórico (searchable)
- Free tier com high rate limits (30 msg/s)
- Sem infraestrutura complexa (token + chat_id)
- HMAC-SHA256 webhook signature validation
- Operador pode estar offline, recebe alerts depois
- Auditoria automática (histórico Telegram)

❌ **Negativas:**
- Dependência de Telegram (SLA ~99.9%)
- API token é credencial crítica (.gitignore obrigatório)
- Rate limit 10 msg/min (implementar queue com backoff)

**Alternativas Consideradas:**

| Alternativa | Pros | Cons | Score |
|---|---|---|---|
| Telegram Bot | Low latency, free, mobile | Requer bot setup | 9.5 |
| Email Alerts | Formal, persistent | 30s+ latency, sem real-time | 4.0 |
| Slack Webhooks | Native business UX | Paid, sem free history | 6.5 |
| Mobile App | Custom, full control | 6+ meses dev | 2.0 |
| Web Dashboard | Live UI, fancy | Requer 24/7 uptime | 5.0 |

**Trade-offs Resolvidos:**

- **Latência vs Throughput:** 2-3s/alert, max 10/min → aceitável para trading
- **Segurança vs UX:** HMAC validation + .gitignore → tradeoff resolvido
- **Cost vs Reliability:** Free tier adequado para MVP

**Implementação:**

- `notifications/telegram_client.py` — 7 métodos de alerta
- `notifications/telegram_webhook.py` — Flask webhook handler com queue
- `config/telegram_config.py` — Config centralizada (rate limit, levels, quiet hours)
- 18 testes: 8 unitários (client) + 10 integração (webhook)
- Coverage 92%+

**Referência:** [Issue #64](ISSUE_64_TELEGRAM_SETUP_SPEC.md) | [Impacto](ISSUE_64_TELEGRAM_IMPACT.md)

---

## 📊 Matriz de Decisões

| ADR | Área | Status | Impact | Revisão |
|-----|------|--------|--------|---------|
| ADR-001 | Data | Aprovada | 🟢 Alto | Anual |
| ADR-002 | Data | Aprovada | 🟢 Alto | Semestral |
| ADR-003 | Execution | Aprovada | 🟡 Média | Trimestral |
| ADR-004 | Risk | Aprovada | 🔴 Crítica | Mensal |
| ADR-005 | Backtesting | Aprovada | 🟢 Alto | Trimestral |
| ADR-006 | Operations | Aprovada | 🟡 Média | Ad-hoc |
| ADR-007 | Documentation | Aprovada | 🟡 Média | Semestral |

---

## 🔄 Processo de Mudança

### Propor Nova ADR

1. **Criar issue** com título `[ADR] <Tópico>`
2. **Discussão:** Contextoー→ Opções → Decisão
3. **Review:** Arquiteto + especialista da área
4. **Merge:** Tag `[SYNC]` + adicionar ao index
5. **Arquivo:** Issue → `docs/ADR_<número>_<título>.md` (opcional)

### Revisão Periódica

- **Mensal:** ADR-004 (Risk/Leverage) — impacto crítico
- **Trimestral:** ADR-003, ADR-005 — possível evolução
- **Anual:** ADR-001, ADR-002 — mudanças externas

---

## 🔗 Referências Cruzadas

| ADR | Relacionados | Docs |
|-----|-------------|------|
| ADR-001/002 | Issue #67 | [C4_MODEL.md](C4_MODEL.md#nível-4-código-class-diagrams--data-flows) |
| ADR-003/004 | TASK-009 | [PositionManager](../execution/position_manager.py) |
| ADR-005 | S2-3 Backtesting | [backtest/](../backtest/) |
| ADR-006 | Paper Mode | [execution/order_executor.py](../execution/order_executor.py) |
| ADR-007 | Documentation | [SYNCHRONIZATION.md](SYNCHRONIZATION.md) |
| ADR-008 | Issue #64 | [notifications/README.md](../notifications/README.md) |

---

## 📚 Como Usar Este Índice

1. **Novo membro?** → Leia ADRs na ordem de importância (004 → 001 → 002)
2. **Quer mudar algo?** → Verifique se já existe ADR relacionada
3. **Revisão técnica?** → Use matriz de decisões (filtrar por área)
4. **Auditoria?** → SYNCHRONIZATION.md tem histórico de mudanças

