# 🟢 Issue #64 — Telegram Alerts Setup Specification

**Sprint:** 2-3 | **Lead:** The Blueprint (#7) | **Squad:** Blueprint (#7) + Quality (#12) + Doc Advocate (#17)
**Deadline:** 25 FEV 18:00 UTC (parallelizable) | **Blocker:** Issue #65 QA (soft dependency)
**Status:** 📋 QUEUE → Kick-off 24 FEV ~14:00 UTC | **GitHash:** 9e8dd1c

---

## 📋 Objetivo

Implementar scaffolding de Telegram Alerts para operações 24/7:
- ✅ Bot setup + webhook estrutura
- ✅ Alert types: P&L, Risk triggers, Execution logs
- ✅ Deployment readiness (não requer live Telegram yet)
- ✅ Integration point para TASK-005 PPO + Issue #67

**Critério Aceite:** Setup completo + 5+ testes + scaffolding docs + integração ready

---

## 🎬 Timeline — 2 Fases (6–8h)

| Phase | Lead | Time | Output | Bloqueio |
|-------|------|------|--------|----------|
| **1: Setup & Infrastructure** | Blueprint (#7) | 24 FEV 14:00–18:00 (4h) | Telegram client + webhook + config | Issue #65 Phase 1 ✅ |
| **2: Integration & Tests** | Quality (#12) | 24 FEV 18:00–25 FEV 02:00 (8h) | 5+ tests + integration stubs + docs | Phase 1 ✅ |

---

## 📝 Phase 1: Setup & Infrastructure (24 FEV 14:00–18:00 UTC)

**Lead:** The Blueprint (#7)

### Tasks

- [ ] **Telegram Bot Creation**
  - [ ] Create bot via BotFather → save token + chat_id
  - [ ] Store credentials in `.env` (git-ignored)
  - [ ] Test connectivity: curl to Telegram API
  
- [ ] **Webhook Infrastructure**
  - [ ] HTTP server setup (Flask minimal or async)
  - [ ] Route: `POST /alerts/telegram` → payload handler
  - [ ] Signature verification (security layer)
  - [ ] Logging: all webhook calls
  
- [ ] **Alert Message Templates**
  - [ ] Template 1: P&L Update (PnL, Win%, Symbol)
  - [ ] Template 2: Risk Trigger (Stop Loss hit, CB triggered)
  - [ ] Template 3: Execution Confirm (Order placed, filled)
  - [ ] Template 4: Error Alert (API error, connection lost)
  
- [ ] **Configuration Management**
  - [ ] `config/telegram_config.py` → settings
  - [ ] Alert level: DEBUG, INFO, CRITICAL
  - [ ] Rate limiting: max 10 alerts/min
  - [ ] Quiet hours: optional silence 22:00–06:00 UTC

### Output Files
- ✅ `notifications/telegram_client.py` — Bot client class
- ✅ `notifications/telegram_webhook.py` — HTTP webhook handler
- ✅ `config/telegram_config.py` — Configuration
- ✅ `.env.example` — Template para credentials
- ✅ `infra/telegram_setup_guide.md` — Deployment checklist

**Deliverable:** Phase 1 complete checklist signed by Blueprint (#7)

---

## 🧪 Phase 2: Integration & Tests (24 FEV 18:00–25 FEV 02:00 UTC)

**Lead:** Quality (#12)

### 5 Core Tests

| # | Test | Input | Expected | Type |
|---|------|-------|----------|------|
| 1 | Telegram Client Connect | Valid token | Connection OK | Unit |
| 2 | PnL Alert Send | {"pnl": 100, "symbol": "BTCUSDT"} | Message formatted + sent | Integration |
| 3 | Risk Trigger Alert | {"event": "stoploss", "price": 50000} | CB alert dispatched | Integration |
| 4 | Webhook Signature Validation | Valid + Invalid payload | Accept only valid | Security |
| 5 | Rate Limiting | 15 alerts / 60s | Only 10 sent, queue rest | Performance |

### Implementation Checklist

- [ ] **Test File:** `tests/test_telegram_*.py` (5 tests)
  - [ ] Unit tests: 2 (client connect, message format)
  - [ ] Integration tests: 2 (webhook, alerts)
  - [ ] Security test: 1 (signature validation)
  
- [ ] **Integration Stubs**
  - [ ] Hook point in `execution/order_executor.py` (notifications on fill)
  - [ ] Hook point in `risk/circuit_breaker.py` (notifications on trigger)
  - [ ] Hook point in `backtest/metrics.py` (daily summary alert)
  - [ ] No logic change in core modules — only imports + notify call
  
- [ ] **Documentation**
  - [ ] `notifications/README.md` — Architecture + usage
  - [ ] Telegram setup guide (step-by-step)
  - [ ] Alert message examples
  - [ ] Troubleshooting section
  
- [ ] **Git & Code Quality**
  - [ ] No hardcoded tokens (all → `.env`)
  - [ ] pylint score ≥ 8.0
  - [ ] 5/5 tests PASS
  - [ ] Coverage ≥ 75% in `notifications/`

### Output Files
- ✅ `tests/test_telegram_client.py`
- ✅ `tests/test_telegram_webhook.py`
- ✅ `notifications/README.md`
- ✅ `test_results_telegram_phase2_24FEV.json`

**Sign-off:** Quality (#12) + Blueprint (#7)

---

## 🔌 Integration Points (Ready for #67 + TASK-005)

### Stub Locations (Add Later)

```python
# execution/order_executor.py
from notifications import telegram_client

def execute_order(...):
    # ... existing code ...
    telegram_client.notify_execution(order_id, symbol, status)

# risk/circuit_breaker.py
def trigger_circuit_breaker(...):
    # ... existing code ...
    telegram_client.notify_risk_event("circuit_breaker", details)

# backtest/metrics.py
def daily_summary(...):
    # ... existing code ...
    telegram_client.notify_daily_pnl(daily_pnl, sharpe)
```

---

## 🚀 Next Steps (Post #67 Data Strategy)

- [ ] Live Telegram testing (stage environment)
- [ ] Alert forwarding to Angel #1 (critical alerts only)
- [ ] Dashboard integration (metrics into Telegram channel)
- [ ] Mobile notification bridge (optional Future)

---

## 📊 Success Metrics

| Métrica | Target | Verificação |
|---------|--------|------------|
| Test Pass Rate | 5/5 = 100% | CI logs |
| Code Coverage | ≥ 75% in notifications/ | pytest --cov |
| Webhook Latency | < 500ms | webhook logs |
| Integration Points | 3/3 stubs added | code review |
| Documentation | 100% complete | README + examples |
| Security | Token not hardcoded | .env verified |

---

## 🔗 Referências

- **Runbook:** [docs/RUNBOOK_OPERACIONAL.md](RUNBOOK_OPERACIONAL.md)
- **Operations 24/7:** [docs/OPERATIONS_24_7_INFRASTRUCTURE.md](OPERATIONS_24_7_INFRASTRUCTURE.md)
- **Config Pattern:** [config/settings.py](../config/settings.py)
- **Best Practices:** [.github/copilot-instructions.md](../.github/copilot-instructions.md)

---

**Squad Ready:** ✅ Blueprint (#7) + Quality (#12) + Doc Advocate (#17)
**Kick-off:** 24 FEV ~14:00 UTC (pós Issue #65 Phase 1)
**Deadline:** 25 FEV 18:00 UTC (soft — parallelizable)
**Status:** 📋 QUEUED & READY
