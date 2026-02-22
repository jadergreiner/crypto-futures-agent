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

### 🚀 AGORA (Now) - Fundação e Segurança
*Foco: Estabilidade Operacional e MVP (Minimum Viable Product)*
- [ ] **Integração de Conectividade:** Finalizar conectividade robusta com Binance Futures (REST + WebSockets).
- [ ] **Risk Gate 1.0:** Implementação de Stop Loss Hardcoded e Circuit Breaker de -3% no nível do motor.
- [ ] **Módulo de Execução:** Orquestrador de ordens com tratamento de erros de API e Rate Limits.
- [ ] **Telemetria Básica:** Logs estruturados para auditoria de trades em tempo real.

### 📈 PRÓXIMO (Next) - Inteligência e Performance
*Foco: Otimização de Ganhos e Análise T��cnica*
- [ ] **Motor de Estratégia SMC:** Implementação de detecção automática de Order Blocks e Break of Structure (BoS).
- [ ] **Sistema de Backtesting:** Engine para testar estratégias contra dados históricos de 1 ano.
- [ ] **Gestão Dinâmica de Risco:** Trailing Stop Loss e ajuste de alavancagem baseado na volatilidade (ATR).
- [ ] **Alertas Externos:** Integração com Telegram para notificações de execução e status do agente.

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

## 📑 Sincronização (Doc Advocate)
- Este documento deve ser atualizado ao final de cada Sprint.
- Alterações críticas exigem quórum de 12 membros conforme `board_16_members_data.json`.
- Tag obrigatória de commit: `[SYNC] ROADMAP atualizado`.