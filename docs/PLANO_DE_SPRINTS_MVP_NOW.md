# 📅 Plano de Sprints — MVP (Now)

**Versão:** 1.0.0
**Sprint atual:** Sprint 1
**Última atualização:** 2026-02-22 21:30 UTC

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

**Objetivo:** Motor SMC e backtesting inicial.
**Período:** TODO
**Depende de:** Sprint 1 concluída e Gate #1 aprovado.

| Entregável                       | Responsável | Status | Issue  | PR     |
|----------------------------------|-------------|--------|--------|--------|
| Detecção de Order Blocks (SMC)   | TODO        | 🔴     | TODO   | TODO   |
| Detecção de BoS (SMC)            | TODO        | 🔴     | TODO   | TODO   |
| Engine de Backtesting (1 ano)    | TODO        | 🔴     | TODO   | TODO   |
| Trailing Stop Loss               | TODO        | 🔴     | TODO   | TODO   |
| Alertas Telegram                 | TODO        | 🔴     | TODO   | TODO   |

---

*Preencher Issues e PRs conforme forem criados no GitHub.*
