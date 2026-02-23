# 📅 Plano de Sprints — MVP (Now)

**Versão:** 1.0.1
**Sprint atual:** Sprint 2 — S2-1/S2-2 ✅ + **S2-5 PARALLELIZABLE: #65 KICKOFF 23 FEV 20:30 + #64 SETUP 24 FEV**
**Última atualização:** 2026-02-23 20:35 UTC — [SYNC] Issue #65 QA Timeline + Issue #64 Parallelização

---

## 🔗 Links Rápidos

- [ROADMAP](ROADMAP.md)
- [Status de Entregas](STATUS_ENTREGAS.md)
- [Critérios de Aceite](CRITERIOS_DE_ACEITE_MVP.md)
- [Changelog](CHANGELOG.md)

---

## 🗺️ Mapa Now → Sprints

| Now (ROADMAP)                   | Sprint   | Issue  | Arquivos-chave                        | Critério de Pronto                               |
|---------------------------------|----------|--------|---------------------------------------|--------------------------------------------------|
| Integração de Conectividade     | Sprint 1 | #55    | `data/`, `config/settings.py`        | [Ver critérios](CRITERIOS_DE_ACEITE_MVP.md#s1-1) |
| Risk Gate 1.0                   | Sprint 1 | #57    | `risk/`, `config/settings.py`        | [Ver critérios](CRITERIOS_DE_ACEITE_MVP.md#s1-2) |
| Módulo de Execução              | Sprint 1 | #58    | `execution/`                          | [Ver critérios](CRITERIOS_DE_ACEITE_MVP.md#s1-3) |
| Telemetria Básica               | Sprint 1 | #56    | `logs/`, `main.py`                   | [Ver critérios](CRITERIOS_DE_ACEITE_MVP.md#s1-4) |

---

## 🏃 Sprint 1 — Fundação e Segurança

**Objetivo:** Entregar o MVP operacional com conectividade, risco e execução básica.
**Período:** TODO (ex.: 2026-02-22 → 2026-03-07)
**Critério de encerramento:** Todos os itens NOW com status ✅ em
[STATUS_ENTREGAS.md](STATUS_ENTREGAS.md).

| Entregável                       | Responsável | Status | Issue  | PR     |
|----------------------------------|-------------|--------|--------|--------|
| Conectividade Binance REST/WS    | TODO        | 🟡     | #55    | WIP    |
| Stop Loss Hardcoded (-3%)        | TODO        | 🟡     | #57    | WIP    |
| Circuit Breaker engine           | TODO        | 🟡     | #57    | WIP    |
| Orquestrador de ordens           | TODO        | 🟡     | #58    | WIP    |
| Tratamento de erros API          | TODO        | 🟡     | #58    | WIP    |
| Logs estruturados de trades      | TODO        | 🟡     | #56    | WIP    |

---

## 🔜 Sprint 2 — Inteligência Básica (Planejamento)

**Objetivo:** Data Strategy + Motor SMC e backtesting inicial.
**Período:** TODO
**Depende de:** Sprint 1 concluída e Gate #1 aprovado.

| Entregável                       | Responsável | Status | Issue  | PR     |
|----------------------------------|-------------|--------|--------|--------|
| Data Strategy (1Y Binance)       | Data (#11)  | 🟡     | #60/#67| READY  |
| Detecção de Order Blocks (SMC)   | Arch (#6)   | 🟢     | #63    | IN PP  |
| Detecção de BoS (SMC)            | Arch (#6)   | ✅     | #63    | MERGED |
| Engine de Backtesting (1 ano)    | Data (#11)  | ✅     | #62    | MERGED |
| Testes Integração SMC (E2E)      | Arch (#6) + Audit (#8) | 🟡 **SQUAD AGORA** | **#65** | **23 FEV 20:40 ATIVADO** |
| Trailing Stop Loss (Integração)  | Arch (#6)   | ✅     | #61    | MERGED |
| Alertas Telegram (Setup)         | The Blueprint (#7) + Quality (#12) | 🟡 | **#64** | **24 FEV ~14:00** |

---

*Preencher Issues e PRs conforme forem criados no GitHub.*
