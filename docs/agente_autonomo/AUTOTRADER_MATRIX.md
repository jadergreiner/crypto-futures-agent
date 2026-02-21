# ⚙️ AUTOTRADER MATRIX — DECISÕES E AUTOMAÇÃO

**Versão**: 1.0
**Data**: 2026-02-20
**Status**: Decision matrix para agente autônomo
**Responsável**: CTO + Head Tradinf

---

## 🎯 MundoMatriz de Decisão

### Nível 1: Governança (Decisões Estratégicas)

```text
┌──────────────────────────────────────────────────────────┐
│           DECISÃO ESTRATÉGICA EXECUTIVA                   │
│  (Quem? O quê? Quando? Por quê? Como? Quanto tempo?)    │
└──────────────────────┬───────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
    ┌───▼────┐    ┌────▼────┐   ┌────▼────┐
    │  CFO   │    │   CTO   │   │   PO    │
    │(Budget)│    │(Técnico)│   │(Produto)│
    └───┬────┘    └────┬────┘   └────┬────┘
        │              │            │

DECISÕES:
│
├─ ACAO-001 approval (CFO) ← Bloqueador CRÍTICO
├─ v0.3 release (CTO) ← Validação
├─ Backlog prioritization (PO) ← Roadmap
└─ Budget expansion (CFO) ← Scaling
```text

### Nível 2: Operacional (Decisões Táticas)

```text
AGENTE RL:
├─ Sinais gerados? (decisão automática)
│  ├─ SIM: Passar para F-03 (Live Trading)
│  └─ NÃO: Investigar (logging + alert)
│
├─ Score do sinal? (limiar)
│  ├─ >5.5: Executar LONG automaticamente
│  ├─ 4.0-5.5: Hold (avisar operador)
│  └─ <4.0: Não executar
│
└─ Risk constraints OK? (validação)
   ├─ Max DD < 20%? → SIM: executar
   └─ Else: BLOQUEAR + alert
```text

### Nível 3: Automação (Decisões de Tempo Real)

```text
EXECUTOR (Order Builder):
├─ Posição existe? ──→ SIM: UPDATE (reduce/close)
│                  └─→ NÃO: CREATE (new)
│
├─ Stop location? ──→ 2% below entry
├─ Profit target? ──→ 5% above entry
├─ Amount? ────────→ 0.2 BTC (fixed allocation)
└─ Execute? ──────→ SIM: Send to Binance
```text

---

## 📊 Decision Matrix (Tabulado)

### Trading Decision

```text
SITUAÇÃO                    AÇÃO              OWNER         TEMPO
─────────────────────────────────────────────────────────────────
Sinal gerado (score >5.5)   Executar LONG     Agente        <5 min
Sinal gerado (score 4-5.5)  Avisar operador   Alert bot     <1 min
Sinal gerado (score <4.0)   Ignorar           (None)        (N/A)
Posição no vermelho (-5%)   Aplicar stop      Executor      imediato
Posição com lucro (+3%)     Mover SL para 0   Executor      <10 min
Max DD atingido (20%)       FECHAR todas      Risk mgmt     imediato
Market crash (>-15%)        Emergency stop    CTO + ops     imediato
```text

### Release Decision

```text
MÉTRICA           TARGET    STATUS    DECISION    TIMELINE
──────────────────────────────────────────────────────────
v0.3:
├─ Win rate       >50%      ?         GO/NO-GO    23/02
├─ Sharpe         >0.5      ?         GO/NO-GO    23/02
├─ Crashes        0         ?         GO/NO-GO    23/02
└─ Tests pass     100%      ?         GO/NO-GO    23/02

v0.4:
├─ Test cov.      85%+      ?         Release     28/02
├─ Regression     <5%       ?         Release     28/02
└─ Backtest time  <10s      ?         Release     28/02

v0.5:
├─ Uptime         99.9%     ?         Deploy      09/03
├─ Latency        <1ms      ?         Deploy      09/03
└─ Concurrent     20+       ?         Deploy      09/03
```text

---

## 🔮 Decision Tree (IF/THEN)

### Trade Execution

```text
START
  │
  ├─ Signal generated?
  │  NO  → Wait (next cycle)
  │  YES → Continue
  │
  ├─ Score > 4.0?
  │  NO  → Ignore
  │  YES → Continue
  │
  ├─ Risk constraints OK?
  │  NO  → BLOCK + Alert (operador decisão)
  │  YES → Continue
  │
  ├─ Existing position?
  │  YES → Manage entry/exit
  │  NO  → Create new
  │
  ├─ Place order?
  │  YES → Send to Binance
  │  NO  → Reason logged
  │
  └─ Trade open?
     YES → Monitor (SL/TP/DD)
     NO  → Log error + retry
```text

### Release Decision

```text
START (Release candidate)
  │
  ├─ All tests PASS?
  │  NO  → Fix bugs → retry
  │  YES → Continue
  │
  ├─ Coverage >= 85%?
  │  NO  → Add tests → retry
  │  YES → Continue
  │
  ├─ No critical bugs?
  │  NO  → Fix → retry
  │  YES → Continue
  │
  ├─ Docs synchronized?
  │  NO  → Sync → retry
  │  YES → Continue
  │
  ├─ Go/No-Go approval?
  │  NO  → BLOCK (decision committee)
  │  YES → Continue
  │
  ├─ Rollback plan tested?
  │  NO  → Test → retry
  │  YES → Continue
  │
  └─ RELEASE ✅
```text

---

## 🎛️ Automação Níveis

### ✅ Nível 1: Full Automation (Agora)

```text
DECISÕES AUTOMÁTICAS (Sem aprovação):
├─ Signal generation (se score OK)
├─ Trade execution (se risk OK)
├─ Stop loss enforcement
├─ Position closing (quando target)
└─ Logging + alerting

GATILHOS AUTOMÁTICOS (<100ms):
├─ Position update (real-time)
├─ Risk monitoring (1s)
├─ Alert notifications (real-time)
└─ Emergency stops (imediato)
```text

### ⏳ Nível 2: Semi-Automation (v0.5+)

```text
DECISÕES COM INPUT (Operador confirmação):
├─ Trade size adjustment (operador)
├─ Strategy modification (CTO)
├─ Risk parameter changes (CFO)
└─ Position management override (operador)

SLA: <30 min para resposta esperada
```text

### 🔐 Nível 3: Manual (Crítico)

```text
DECISÕES ESTRATÉGICAS (Aprovação explícita):
├─ ACAO-001-005 (head approval, CFO sign-off)
├─ Release decisions (CTO + PO gate)
├─ Budget expansions (CFO decision)
├─ Regulatory changes (legal + compliance)
└─ Major architecture changes (CTO + diretoria)

SLA: 1-24 horas (dependendo criticidade)
```text

---

## 🚨 Escalação Automática

```text
EVENTO                    NÍVEL    AÇÃO                SLA
──────────────────────────────────────────────────────────
Signal score < 0          AUTO     Log + ignore        N/A
Risk constraints fail     AUTO     Block + alert       <1 min
Crash detected            AUTO     Emergency stop      <5 min
Max DD reached            AUTO     Close all           imediato
>3 erros em 1h            MAN      Slack alert @CTO    <30 min
>5 erros em 1h            EXEC     Operador intervention<15 min
Market halt               MAN      Operador decision   <5 min
Regulatory issue          EXEC     Legal + diretoria   SLA nego
```text

---

## 📋 Matriz de Responsabilidades

### Quem Decidir Quê?

```text
           CFO    CTO    PO    OPS    AGENTE
Sinais     ─      ─      ─     Y      ✅
Trade exec ─      ─      ─     Y      ✅
Stop loss  ─      ─      ─     Y      ✅
Position sz Y      ─      ─     Y      ─
Risk param Y      Y      ─     ─      ✅(enforced)
Release    ─      ✅     ✅    ─      ─
Budget     ✅     ─      ─     ─      ─
Roadmap    ─      Y      ✅    ─      ─
Compliance Y      ─      ─     Y      ─
Emergency  Y      ✅     ─     ✅     ✅(auto)

Legend: ✅ = Primary | Y = Secondary | ─ = Not involved
```text

---

## 🔄 Ciclo de Decisão (48 horas)

```text
HOJE (20/02 22:00)
├─ CFO: Decisão ACAO-001 ← CRÍTICO
├─ PO: Comunicação RCA se rejeitado
└─ OPS: Standby

AMANHÃ (21/02 08:00 - 16:00)
├─ OPS: Executar ACAO-001-005
├─ CTO: Validar sinals/trades
├─ PO: Monitorar métricas
└─ OPS: Comunicação updates

AMANHÃ NOITE (21/02 20:00)
├─ HEAD: Reunião checkpoint
├─ Equipe: Status relatório
└─ PO: Ajustes para dia 2

23 FEV (09:00)
├─ CTO: Análise 24h dados
├─ HEAD: Decisão v0.3 release
├─ PO: Comunicação stakeholders
└─ OPS: Preparação v0.4 kickoff
```text

---

## ✅ Validação de Integridade

Toda decisão automática DEVE ter:

```text
[ ] IF condition clearly defined
[ ] THEN action unambiguous
[ ] ELSE fallback specified
[ ] Timeout defined
[ ] Error logging implemented
[ ] Alert threshold set
[ ] SLA compliance enforced
[ ] Owner assigned
[ ] Tested with data
```text

---

**Mantido por**: CTO + Head Trading
**Frequência**: Atualizado por mudança governance
**Last Updated**: 2026-02-20 22:40 UTC

