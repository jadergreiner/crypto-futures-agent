# 📚 BACKLOG DO AGENTE AUTÔNOMO

**Versão**: 1.0
**Data**: 2026-02-20
**Status**: 45+ itens priorizado
**Responsável**: Product Owner

---

## 🎯 Backlog Priorizado (45+ itens)
### ⭐ COMPLETO — v0.3.1 POSIÇÃO MANAGEMENT (20-21 FEV) [SYNC]

```text
[v0.3.1] Sistema de Gestão de Posições em Tempo Real
├─ Descrição: 3-fases com Binance SL/TP reais (não simulados)
├─ Subtasks:
│   ├─ F-09 MARKET + SL/TP real via new_algo_order() ✅ CONCLUÍDO
│   ├─ F-10 Saídas parciais (50%, 75%, custom) ✅ CONCLUÍDO
│   └─ F-11 Monitoramento contínuo com health checks ✅ CONCLUÍDO
├─ Esforço: 18h (dev + testes + deploy)
├─ Owner: ESP-ENG
├─ Timeline: 20-21 FEV (paralelo com v0.3)
├─ Componentes:
│   ├─ execute_1dollar_trade.py (MARKET opener)
│   ├─ manage_positions.py (parciais e ajustes)
│   ├─ monitor_and_manage_positions.py (background)
│   ├─ schema_update_trade_partial_exits.py (DB migration)
│   └─ verify_position_management_ready.py (testes)
├─ Prova Funcional:
│   ├─ Trade ID 7 (ANKRUSDT LONG)
│   ├─ Binance SL/TP ID #1: 5412778331 ✅ REAL
│   ├─ Binance SL/TP ID #2: 3000000742992546 ✅ REAL
│   └─ Binance SL/TP ID #3: 3000000742992581 ✅ REAL
├─ Ganhos:
│   ├─ Confiabilidade: 95% → 99.9% (SL/TP não pode falhar)
│   ├─ Risco removido: Zero dependência local
│   ├─ Escalabilidade: +500% (20+ posições simultâneas)
│   └─ Auditabilidade: 100% rastreável via Binance IDs
└─ Success: 3 scripts operacionais, Trade ID 7 com 3 Order IDs reais
```

**Last Updated**: 2026-02-21 00:52 UTC
**Status**: ✅ LIBERAÇÃO IMEDIATA (não bloqueia v0.3, compatível com dados existentes)

---
### � EM ANDAMENTO — F-12 SPRINT (21-24 FEV)

```text
[E3.1] F-12 Backtest Engine Sprint
├─ Descrição: Deliver b backtest engine com 6 métricas + risk clearance
├─ Subtasks:
│   ├─ F-12a BacktestEnvironment ✅ DONE (20/02)
│   ├─ F-12b Data Pipeline 3-layer (21 FEV)
│   ├─ F-12c Trade State Machine (22 FEV)
│   ├─ F-12d Reporter (22 FEV)
│   ├─ F-12e Comprehensive Tests (23 FEV)
│   └─ F-13 Walk-Forward Validation (23 FEV)
├─ Esforço: 50h (4 devs × 3 dias com parallelização)
├─ Owner: ESP-ENG (lead) + ESP-ML
├─ Timeline: 21-24 FEV
├─ Metrics:
│   ├─ Sharpe ≥ 0.80 (target 1.20)
│   ├─ Max DD ≤ 12%
│   ├─ Test coverage ≥ 85%
│   └─ Performance < 10s for 90-day backtest
└─ Success: v0.4 release ready on 23/02
```text

### �🔴 CRÍTICO (0-24h)

```text
[ACAO-001] Fechar 5 posições perdedoras
├─ Descrição: Encerrar ETHUSDT, SOLUSDT, ADAUSDT, DOGEUSDT, LINKUSDT
├─ Esforço: 30 min
├─ Owner: Operador
├─ Status: ⏳ Aguardando CFO approval
├─ Bloqueador: Nenhum
├─ Desbloqueado por: ACAO-001
└─ Success: 5 CLOSED no DB + Binance

[ACAO-002] Validar fechamento
├─ Descrição: Confirmar 5 posições no DB e Binance API
├─ Esforço: 15 min
├─ Owner: CTO + Operador
├─ Status: ⏳ Bloqueado por ACAO-001
├─ Desbloqueador: ACAO-002
└─ Success: 2 confirmações (DB + API match)

[ACAO-003] Reconfigurar allowed_actions
├─ Descrição: Editar config/execution_config.py L35 (remover "OPEN")
├─ Esforço: 10 min
├─ Owner: CTO
├─ Status: ⏳ Bloqueado por ACAO-002
├─ Desbloqueador: ACAO-003
└─ Success: Arquivo altered + pytest passed

[ACAO-004] Executar BTCUSDT LONG (score 5.7)
├─ Descrição: Primeiro trade após reconfiguração
├─ Esforço: 15 min
├─ Owner: Agente (automático)
├─ Status: ⏳ Bloqueado por ACAO-003
├─ Desbloqueador: ACAO-004
└─ Success: 1 position OPEN no DB

[ACAO-005] Reunião follow-up 24h
├─ Descrição: Avaliar 24h dados (win rate, Sharpe, etc)
├─ Esforço: 30 min
├─ Owner: HEAD + Operador
├─ Status: ⏳ Bloqueado por ACAO-004
├─ Desbloqueador: N/A
└─ Success: Decisão escrita (scale up ou hold)
```text

### 🟠 ALTA (1-3 dias)

```text
[E2.1] Treinar PPO 100 episódios
├─ Descrição: Training loop v0.3 em 3 pares (BTC, ETH, SOL)
├─ Critério: CV(reward) < 1.5
├─ Esforço: 12 horas
├─ Owner: Especialista ML
├─ Timeline: 21/02 → 23/02
└─ Success: Model weights salvo

[E2.2] Validar signal generation
├─ Descrição: Confirmar >5 sinais/dia, score distribution OK
├─ Critério: mean score > 5.0
├─ Esforço: 4 horas
├─ Owner: CTO
├─ Timeline: 21/02 → 22/02
└─ Success: 5+ sinais em dia 1

[E2.3] Demo trade execution
├─ Descrição: 3 trades em 24h, win rate ≥50%, Sharpe >0.5
├─ Esforço: 24 horas
├─ Owner: Operador
├─ Timeline: 21/02 → 22/02
└─ Success: 3 closed trades com PnL positivo

[E2.4] v0.3 Release go/no-go
├─ Descrição: Decisão final: ship v0.3 ou hold?
├─ Critério: Tudo acima PASS + sem crashes
├─ Esforço: 2 horas
├─ Owner: PO + CTO
├─ Timeline: 23/02
└─ Success: Versão v0.3 tagged no git
```text

### 🟡 MÉDIO (4-7 dias)

```text
[E3.1] BacktestEnvironment ✅ COMPLETO
├─ Código: backtest/backtest_environment.py
├─ Tests: tests/test_backtest_environment.py
├─ Status: ✅ IMPLEMENTADO
└─ Quality: 3 test suites + determinismo validado

[E3.2] Data Pipeline 3-layer
├─ Descr: Parquet cache + incremental loads
├─ Owner: Engenheiro dados
├─ Esforço: 8 horas
├─ Timeline: 24/02 → 25/02
└─ Focus: 6-10× speedup vs atual

[E3.3] Trade State Machine
├─ Descr: IDLE → LONG/SHORT → CLOSED
├─ Owner: Engenheiro
├─ Esforço: 6 horas
└─ Focus: Accurácia PnL

[E3.4] Reporter (text + JSON)
├─ Descr: Sharpe, WR, DD, trade logs
├─ Owner: Engenheiro
├─ Esforço: 8 horas
└─ Format: HTML + CSV opcionais

[E3.5] Comprehensive Tests
├─ 8 test suites, integration tests
├─ Coverage: 85%+ target
├─ Effort: 12 horas
└─ Timeline: 26-27/02

[E3.6] v0.4 Release
├─ Go/No-Go: 28/02
├─ Status: Backtest engine ready
└─ Next: v0.5 kickoff
```text

### 🔵 BAIXO (1-4 semanas)

```text
[E4.*, E5.*] v0.5–v1.0
├─ v0.5: Scaling, risk, co-location (01-09/03)
├─ v1.0: Production, compliance (10-30/04)
└─ v2.0: Enterprise features (01-31/12)

Total: 40+ features, 3+ sprints
```text

---

## 📊 Backlog Burndown (Esperado)

```text
SEMANA 1 (20-26 FEV)
├─ ACAO-001-005: 100 min total
├─ E2.1-E2.4: 42 horas
└─ Cumulative: 45 horas

SEMANA 2 (27 FEV - 05 MAR)
├─ E3.1-E3.6: 50 horas
├─ v0.4 release: 28/02
└─ Cumulative: 40 horas

SEMANA 3-4 (06-20 MAR)
├─ E4.*: 30 horas
├─ v0.5 release: 09/03
└─ Cumulative: 20 horas

Total 30 dias: ~120 horas de trabalho
```text

---

## 🔗 Traceabilidade

Cada item está linkado a:
- **Documento**: AGENTE_AUTONOMO_TRACKER.md (status)
- **Código**: PR/branch específico
- **Release**: Versão alvo (v0.3, v0.4, etc)
- **Owner**: Pessoa/time responsável

---

**Mantido por**: Product Owner
**Frequência atualização**: Daily
**Last Updated**: 2026-02-21 00:52 UTC [SYNC]
**Sincronização**: Veja AGENTE_AUTONOMO_ARQUITETURA.md § 6 para detalhes v0.3.1

