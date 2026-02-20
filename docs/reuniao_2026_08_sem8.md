# REUNIÃO SEMANAL — Semana 8, 2026

**Data**: 2026-02-20 20:01:32.884831
**Head**: Roberto Silva
**Operador**: v0.3
**Status**: em_andamento

---

## 🎙️ Diálogos

### HEAD 🧠:

Vi que você executou DOGEUSDT LONG com score 4.2. Isso está abaixo do threshold de 5.0. Por quê?

**Dados**: {"par": "DOGEUSDT", "tipo": "LONG", "score": 4.2, "pnl": -320, "threshold_esperado": 5.0}

### OPERADOR 🤖:

O modelo apontou confluência SMC (liquidity sweep) + sentimento bullish no Telegram. No entanto, reconheço que a taxa de acerto em scores <5.0 foi apenas 35% (vs 62% geral). Operação precipitada. Peço que aumentemos o threshold.

**Dados**: {"taxa_acerto_lowscore": 0.35, "taxa_acerto_geral": 0.62, "razao": "Conflu\u00eancia fraca, execu\u00e7\u00e3o por sentimento"}

### HEAD 🧠:

Concordo. Score abaixo de 5.0 não têm edge estatístico. Ação: elevar MIN_ENTRY_SCORE de 4.0 para 5.5 em reward.py. Vamos reduzir volume mas aumentar taxa de acerto.

---

## 📋 Feedbacks

### ✅ Força
BTCUSDT LONG com score 8.7 — entrada perfeita, TP atingido (Impacto: 9.5/10)

### ❌ Fraqueza
3 operações com score <5.0 — taxa de acerto 35% (Impacto: 8.0/10)

### 🔄 Oportunidade
0GUSDT teve BOS confirmado. Limite de 10 ordens impediu execução. (Impacto: 7.5/10)

---

## 🚀 Ações

### [ALTA] Investigar causa de latência em 3 rejeições de ordem
- **Status**: pendente
- **Responsável**: OPERADOR
- **Alvo**: monitoring/critical_monitor_opção_c.py
- **Impacto**: Identificar gargalo de rede/API

### [CRÍTICA] Aumentar MIN_ENTRY_SCORE de 4.0 para 5.5
- **Status**: pendente
- **Responsável**: OPERADOR
- **Alvo**: agent/reward.py
- **Impacto**: +3% taxa acerto, -5% volume

---

## 💰 Investimentos

### Infraestrutura
Nobreak 1500W + gerador 5kW
- **Custo**: $1200.0
- **ROI Esperado**: -5.0%
- **Status**: proposto

### Computação
+32GB RAM para análise paralela de 20+ pares
- **Custo**: $800.0
- **ROI Esperado**: 12.0%
- **Status**: proposto

### Rede
Conexão dedicada co-location Binance (IP fixo)
- **Custo**: $200.0
- **ROI Esperado**: 1.5%
- **Status**: proposto

