# 🗺️ Product Roadmap - Crypto Futures Agent

**Status:** Rascunho Estratégico
**Versão:** 1.0.0
**Owner:** [Product](#)
**Guardião:** [Board Member](#)

---

## 🎯 Visão do Produto
Ser o agente de trading de futuros mais resiliente e seguro do mercado, focando em preservação de capital e execução precisa de estratégias baseadas em Smart Money Concepts (SMC).

---

## 📅 Ciclo de Evolução (Now-Next-Later)

### 🚀 AGORA (Now) - Fundação e Segurança ✅ COMPLETO
*Foco: Estabilidade Operacional e MVP (Minimum Viable Product)*
- [x] **Integração de Conectividade:** ✅ COMPLETO #55 (8/8 testes PASS)
- [x] **Risk Gate 1.0:** ✅ COMPLETO #57 (10/10 testes PASS)
- [x] **Módulo de Execução:** ✅ COMPLETO #58 (11/11 testes PASS)
- [x] **Telemetria Básica:** ✅ COMPLETO #56 (41 testes PASS)

### 📈 PRÓXIMO (Next) - Inteligência e Performance 🔵 EM PLANEJAMENTO (Sprint 2)
*Foco: Backtesting + SMC + Risco Dinâmico. Bloqueio: S2-3 valida SMC antes do Go-Live*
- [x] **Data Strategy (1Y):** [S2-0] #60 Design ✅ COMPLETO — Pipeline 1Y validado
- [ ] **Sistema de Backtesting:** [S2-3] #59 Design ✅ PRONTO, implementação Sprint 2-3
- [ ] **Motor de Estratégia SMC:** [S2-1/S2-2] Order Blocks + BoS (Bloqueador: S2-3)
- [ ] **Gestão Dinâmica de Risco:** [S2-4] Trailing Stop Loss (Independente)
- [ ] **Alertas Externos:** [S2-5] Telegram (Bloqueador: SMC)

### 🌌 DEPOIS (Later) - Escala e Autonomia
*Foco: Machine Learning e Descentralização*
- [ ] **Otimização via ML:** Uso de modelos PPO (Proximal Policy Optimization) para ajuste fino de entradas.
- [ ] **Multi-Exchange:** Suporte para Bybit e OKX para arbitragem de taxas de funding.
- [ ] **Dashboard Web:** Interface visual para monitoramento de múltiplos agentes simultâneos.
- [ ] **Auto-Hedge:** Módulo de proteção automática em mercados spot para neutralizar riscos de cauda.

---

## 🛡️ Princípios Guia
1. **Segurança sobre Lucro:** Nunca comprometer o Risk Gate por performance.
2. **Dados sobre Intuição:** Todas as mudanças no Roadmap devem ser baseadas em resultados de Backtesting.
3. **Simplicidade de Código:** O código de execução deve ser "boring" (simples e previsível).

---

## 🔗 Execução / Visibilidade

> Bloco mantido pelo Copilot via `docs_sync_policy`. Não editar manualmente.

**Sprint atual:** Sprint 1 ✅ COMPLETA | Sprint 2 🔵 EM EXECUÇÃO (S2-0 Design ✅ + S2-3 Squad Kickoff 22 FEV 🚀)
**Última atualização:** 2026-02-22 14:30 UTC
**Progresso NOW:** 4/4 itens 100% completo ✅
**Progresso NEXT:** S2-0 Design ✅ COMPLETO (#60). S2-3 Squad Kickoff 🚀 (ARCH + Audit + Data + Quality + Doc Advocate). Implementação Sprint 2-3 com 4 Gates definidos.

| Documento                | Link                                           |
|--------------------------|------------------------------------------------|
| Status de Entregas       | [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md)       |
| Plano de Sprints         | [PLANO_DE_SPRINTS_MVP_NOW.md](PLANO_DE_SPRINTS_MVP_NOW.md) |
| Critérios de Aceite      | [CRITERIOS_DE_ACEITE_MVP.md](CRITERIOS_DE_ACEITE_MVP.md)   |
| Runbook Operacional      | [RUNBOOK_OPERACIONAL.md](RUNBOOK_OPERACIONAL.md)           |
| Changelog                | [CHANGELOG.md](CHANGELOG.md)                  |

---

## 📑 Sincronização (Doc Advocate)
- Este documento deve ser atualizado ao final de cada Sprint.
- Alterações críticas exigem quórum de 12 membros conforme `board_16_members_data.json`.
- Tag obrigatória de commit: `[SYNC] ROADMAP atualizado`.