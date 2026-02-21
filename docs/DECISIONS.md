# 📋 DECISIONS — Board Meeting Archive

Registo de decisões estratégicas tomadas em reuniões de Board.

**Primeira Reunião Formal:** 22 FEV 2026

---

## 🔔 DECISÃO #1 — GOVERNANÇA DE DOCUMENTAÇÃO

**Data:** 22 FEV 2026 21:45 UTC  
**Reunião:** Board Strategic Decision  
**Investidor:** [Aprovado]  
**Facilitador:** Registrado  

### O Problema
- 100+ arquivos markdown/json/txt no root
- Duplicação: Features em README vs docs/FEATURES.md
- Status em 3 formatos diferentes
- Cada mudança criava NOVO arquivo em vez de ATUALIZAR

### A Decisão
**Opção A — IMPLEMENTAR AGORA (24h)**
- Criar hierarquia única em /docs/
- Portal centralizado: STATUS_ATUAL.md
- 6 documentos oficiais apenas
- Protocolo [SYNC] em commits

### Ações Aprovadas
1. ✅ Criar /docs/STATUS_ATUAL.md (portal)
2. ✅ Criar /docs/DECISIONS.md (este arquivo)
3. ⏳ Revisar & limpar /docs/FEATURES.md
4. ⏳ Revisar & limpar /docs/ROADMAP.md
5. ⏳ Revisar & limpar /docs/RELEASES.md
6. ⏳ Atualizar /docs/SYNCHRONIZATION.md
7. ⏳ Listar & deletar duplicados do root
8. ⏳ Atualizar README.md (hyperlinks para /docs/)
9. ⏳ Criar protocolo de commit [SYNC]

### Timeline
- **Hoje (22 FEV):** Setup + prototipagem
- **Domingo (23 FEV):** Review + aprovação final
- **Semana (24+ FEV):** Implementação incremental

### Responsável
- **Owner:** Facilitador
- **Executor:** Git Master / SWE Lead
- **Review:** Investidor (antes de deletar)

### Status
🟡 **IN PROGRESS** — Portal criado, protocolos em andamento

---

## 🟡 DECISÃO PENDENTE #2 — MACHINE LEARNING

**Data:** Aguardando reunião domingo (23 FEV)

### Contexto
Backtest com ações aleatórias falhou em 4 de 6 risk gates:
- Sharpe Ratio: 0.06 (need 1.0)
- Max Drawdown: 17.24% (need ≤15%)
- Profit Factor: 0.75 (need 1.5)
- Calmar Ratio: 0.10 (need 2.0)

### Opções em Discussão

**Option A:** Heurísticas + limites conservadores
- Timeline: 1-2 dias
- Risco: Baixo upside
- Approach: Hard rules, sem RL

**Option B:** Treinar PPO 5-7 dias
- Timeline: 5-7 dias (até 28 FEB)
- Risco: Alto (parâmetros, convergência)
- Upside: Sharpe 1.0+, PF 1.5+

**Option C:** Híbrido (Layer 0: heurísticas + Layer 1-6: PPO)
- Timeline: 3-4 dias
- Risco: Médio
- Upside: Rápido + melhor

### Recomendação do Facilitador
🔵 **Option C** (híbrido) — balanço de risco vs reward vs timeline

### Voto Esperado
Investidor → decidir em 23 FEV

### Status
⏳ **AWAITING INPUT** — Reunião no domingo

---

## 🟡 DECISÃO PENDENTE #3 — POSIÇÕES UNDERWATER

**Data:** Aguardando reunião domingo (23 FEV)

### Contexto
21 posições abertas com perdas extremas:
- ETHUSDT: -511%
- BTCUSDT: -42%
- Etc.

Agente em Profit Guardian Mode (defensivo desde 17 FEV).

### Impacto Financeiro
- **Inação:** -$2.670/dia
- **Agir hoje:** +$3.000 upside + redução risco

### Opções

**Option A:** Liquidar todas (seca o mercado)
- Risco: Perda realizada imediata
- Upside: Limpa capital para operações novas

**Option B:** Hedge gradual (protective puts)
- Risco: Custo de hedging
- Upside: Mantém upside, limita downside

**Option C:** Liquidar 50%, hedge 50%
- Risco: Médio
- Upside: Balanço

### Recomendação do Facilitador
🔵 **Option A** (liquidar) — risk, limpar o mercado e recomeçar

### Voto Esperado
Risk Manager + Investidor → 23 FEV

### Status
⏳ **AWAITING APPROVAL** — Risk Manager precisa assinar

---

## 🟡 DECISÃO PENDENTE #4 — ESCALABILIDADE

**Data:** Aguardando reunião domingo (23 FEV)

### Contexto
F-12b Parquet Cache pronto para iniciar (22 FEV).

Universo atual: 60 pares  
Capacidade potencial: 200+ pares com Parquet

### Opções

**Option A:** Expandir para 200 pares imediatamente
- Timeline: 2-3 dias
- Risco: Baixo (dados já coletados)
- Upside: +30% capacity

**Option B:** Manter 60, otimizar profundidade
- Timeline: 1 dia
- Risco: Muito baixo
- Upside: Estabilidade

### Recomendação do Facilitador
🔵 **Option A** — melhor ROI se governança docs OK

### Status
⏳ **AWAITING INPUT** — Investidor decide se combina com ML

---

## 📝 TEMPLATE PARA PRÓXIMAS DECISÕES

```markdown
## 🟡 DECISÃO PENDENTE #N — [TÍTULO]

**Data:** [Quando decidiu]  
**Reunião:** [Qual reunião]  
**Investidor:** [Aprovado / Rejeitado / Pendente]  
**Facilitador:** [Status]  

### Contexto
[Explicar problema]

### Opções
- **Option A:** [Descrição], Timeline: X, Risco: Y
- **Option B:** [Descrição], Timeline: X, Risco: Y
- **Option C:** [Descrição], Timeline: X, Risco: Y

### Recomendação do Facilitador
[Qual é melhor e por quê]

### Voto Esperado
[Quem vota e quando]

### Status
[⏳ AWAITING / 🔵 DECISION / ✅ APPROVED / ❌ REJECTED]
```

---

## 📊 SUMÁRIO DE DECISÕES

| # | Título | Data | Status | Owner |
|---|--------|------|--------|-------|
| 1 | Governança Docs | 22 FEV | 🟡 IN PROGRESS | Facilitador |
| 2 | Machine Learning | 23 FEV | ⏳ AWAITING | Investidor |
| 3 | Posições | 23 FEV | ⏳ AWAITING | Risk Mgr |
| 4 | Escalabilidade | 23 FEV | ⏳ AWAITING | Investidor |

---

**Última atualização:** 22 FEV 21:50 UTC  
**Próxima reunião:** 23 FEV 20:00 UTC  
**Adicionadas:** 4 decisões (1 aprovada, 3 pendentes)
