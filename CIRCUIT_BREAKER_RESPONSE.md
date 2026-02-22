# 🔌 CIRCUIT BREAKER — GUIA DE RESPOSTA

**Documento:** Procedimento de Resposta ao Circuit Breaker  
**Audiência:** Operador/Risk Manager  
**Status:** ✅ OPERACIONAL | **Versão:** 1.0  
**Data:** 22 FEV 2026

---

## ⚡ O QUE É CIRCUIT BREAKER?

Sistema de **proteção automática** que bloqueia NOVAS ORDENS quando:

```
Drawdown diário atinge:  -3.0%
(ou -5.0% em cenário extremo)

Estado: BLOQUEIA
  ✅ Não abre posições novas
  ✅ Permite fechar posições (stop loss)
  ❌ Não permite aumentar risk
```

**Objetivo:** Evitar cascata de perdas

---

## 🔴 CIRCUIT BREAKER DISPARADO — O QUE SIGNIFICA

### Status no Dashboard

```
Você vê no dashboard:
  "🔴 Circuit Breaker: DISPARADO"

Interpretação:
  - Drawdown (-X%) ≤ -3.0%
  - Sistema PAROU de abrir posições
  - Proteção está ATIVA
```

### Impacto no Trading

```
ANTES (CB não ativo):
  Sistema abre posições normalmente
  
DEPOIS (CB dispara):
  ✅ Stop Loss ATIVA (fecha posições em pânico)
  ✅ Take Profit ATIVA (fecha parciais)
  ❌ NOVOS sinais IGNORADOS
  ❌ Novas posições NÃO ABERTAS
```

---

## 📊 CENÁRIOS & RESPOSTAS

### Cenário 1: CB dispara, depois RECUPERA

```
Timeline:
  14:00 → Drawdown -2.8% (NORMAL)
  14:05 → Drawdown -3.1% (CB DISPARA) 🔌
  14:15 → Drawdown -3.05% (P&L melhora um pouco)
  14:30 → Drawdown -2.9% (CB DESATIVA) ✅

Ação do operador:
  1. MONITORAR (não fazer nada)
  2. Deixar sistema recuperar
  3. CB vai sair automaticamente
  4. Sistema retoma trading quando -3% < drawdown
```

### Cenário 2: CB dispara, depois PIORA

```
Timeline:
  14:00 → Drawdown -2.8% (NORMAL)
  14:05 → Drawdown -3.5% (CB DISPARA) 🔌
  14:15 → Drawdown -4.2% (piorando...)
  14:30 → Drawdown -4.8% (CRÍTICO - próx: -5% hard stop)

Ação do operador:
  1. EXECUTAR: python posicoes.py
     (salvar estado completo)
  2. CONTATAR: Angel + Dr. Risk IMEDIATAMENTE
  3. PREPARAR: Opções de ação
     - Fechar 50% de posições?
     - Ativar alavancagem reduzida?
     - PARAR completo?
```

### Cenário 3: CB dispara, FICA TRAVADO

```
Timeline:
  14:05 → Drawdown -3.1% (CB DISPARA) 🔌
  14:30 → Drawdown -3.2% (TRAVADO em -3%)
  15:00 → Drawdown -3.1% (oscila perto de -3%)
  
O que está acontecendo:
  - Sistema alcançou limite de proteção
  - Oscila perto do threshold
  - Stop losses ativam periodicamente
  
Ação do operador:
  1. NÃO ADORMECA (monitor contínuo)
  2. Aguarde decisão de Risk Manager
  3. Prepare: PARADA EMERGENCIAL se piorar
  4. Reporte: Estado para os membros críticos
```

---

## 🛠️ AÇÕES DISPONÍVEIS QUANDO CB ATIVO

### Ação 1: MONITORAR (Passivo)

```
O quê fazer:
  - Deixar sistema com CB ativo
  - Monitorar drawdown a cada 5 minutos
  - NÃO intervir
  
Quando usar:
  - Drawdown oscila perto de -3%
  - Histórico mostra recuperação
  - Confiança em que vai melhorar
  
Risco:
  - Se piorar para -5%, liquidação acelerada
```

### Ação 2: REDUZIR RISCO (Médio)

```
O quê fazer:
  1. Parar agente (Ctrl+C)
  2. Fechar 25-50% das posições manualmente
  3. Reduzir alavancagem
  4. Reiniciar com parâmetros conservadores
  
Quando usar:
  - CB permanece >10 minutos
  - Drawdown em tendência de piora
  - Board autoriza redução de exposição
  
Risco:
  - Realiza perdas (converte P&L negativo em PERDIDO)
  - Pode desativar CB e retomar trading com menos capital
```

### Ação 3: PARADA TOTAL (Agressivo)

```
O quê fazer:
  1. Executar: python posicoes.py (diagnostics)
  2. PARAR AGENTE: Ctrl+C
  3. CONTATAR: Angel para decisão final
  4. SE AUTORIZADO: Fechar tudo (todas posições)
  5. Log de auditoria criado
  
Quando usar:
  - Drawdown cai abaixo de -4%
  - Circuit breaker permanece >30 minutos
  - Board decide: risco não é mais aceitável
  - Recuperação parece improvável (<20% probabilidade)
  
Risco:
  - REALIZA todas as perdas
  - Capital remanescente fica "seguro"
  - Phase 2 encerrado
```

---

## 📋 CHECKLIST DE RESPOSTA

Quando você VÊ "Circuit Breaker: DISPARADO":

- [ ] 1. Dashboard confirma CB ativo?
- [ ] 2. Desenho está em -3% a -5%?
- [ ] 3. Registre timestamp exato (auditoria)
- [ ] 4. Execute: python posicoes.py (backup)
- [ ] 5. Envie snapshot para Risk Manager
- [ ] 6. Decida: Monitorar / Reduzir / Parar?
- [ ] 7. Implemente ação
- [ ] 8. Log tudo em: reports/cb_response_*.txt
- [ ] 9. Notifique team em 2 minutos

---

## 🔗 DOCUMENTAÇÃO RELACIONADA

- [EMERGENCY_STOP_PROCEDURE.md](EMERGENCY_STOP_PROCEDURE.md)
  — Como parar sistema seguramente
- [DASHBOARD_OPERATOR_ALERTS.md](DASHBOARD_OPERATOR_ALERTS.md)
  — Interpretar alertas visuais
- [PHASE2_RISCO_ALTO_AVISOS.md](PHASE2_RISCO_ALTO_AVISOS.md)
  — Riscos do Phase 2

---

## 🎯 RESUMO RÁPIDO

| Status | Significado | Ação |
|--------|-------------|------|
| Normal | Drawdown > -3% | Continuar operando |
| ⚠️ Warning | Drawdown -3% ≤ X < -4% | Monitorar |
| 🔴 Critical | Drawdown ≤ -4% | Reduzir / Parar |
| 🚨 Liquidation | Drawdown < -5% | Parada automática |

---

**Doc Advocate Note:** Documento sincronizado com:
- `risk/risk_manager.py` (linhas 45-67)
- `execution/gate.py` (linhas 89-105)
- Dashboard alerts: `dashboard_data.json`

**Commit Tag:** `[DOCS]`

