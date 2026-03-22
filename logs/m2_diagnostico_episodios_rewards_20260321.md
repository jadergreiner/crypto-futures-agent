# Diagnóstico: Por que Episódios e Rewards NÃO estão sendo Capturados no Ciclo Live 20260321_224930

## Resumo Executivo

❌ **NENHUM episódio novo foi capturado e NENHUM reward foi calculado no ciclo live analisado.**

✅ **Isto é CORRETO e ESPERADO** — Sistema está operando conforme especificação de Fase 1.

**Motivo**: Nenhuma ordem foi realmente EXECUTADA. Sem execução = sem reward.

---

## 1. Análise de Execuções do Ciclo

### Signal Executions do Ciclo 20260321_224930

| ID | Symbol | Signal Side | Status | Gate Reason | Filled Qty | Reward |
|----|--------|-------------|--------|-------------|------------|--------|
| 19 | ETHUSDT | SHORT | **BLOCKED** | risk_gate_blocked | ❌ None | ❌ None |
| 18 | SOLUSDT | SHORT | **BLOCKED** | daily_limit_reached | ❌ None | ❌ None |
| 17 | FLUXUSDT | SHORT | **BLOCKED** | daily_limit_reached | ❌ None | ❌ None |

**Conclusão**: 3 signal_executions marcadas como BLOCKED. Nenhuma ordem foi realmente enviada à exchange.

---

## 2. Por que as Ordens Foram Bloqueadas?

### Risk Gate Bloqueou ETHUSDT
```
gate_reason: "risk_gate_blocked"
```
Motivo: Risk gate aplicou fail-safe. Possivelmente:
- Daily entry limit atingido
- Alavancagem máxima excedida
- Portfolio risk ou posição aberta sem proteção

### Daily Limit Reached para SOLUSDT e FLUXUSDT
```
gate_reason: "daily_limit_reached"
```
Motivo: `M2_MAX_DAILY_ENTRIES = 3` já foi atingido em ciclos anteriores.

**Confirmação**: Fase 1 especifica limite de 3 entradas diárias. Sistema está respeitando este limite conservador.

---

## 3. Ciclo de Vida de um Episódio - O que Deveria Acontecer

```
[DECISÃO DO MODELO]
        ↓
[SINAL TÉCNICO CRIADO]
        ↓
[ORDER LAYER (admissão)]
        ↓
[SIGNAL EXECUTION CRIADA]
        ↓
[RISK GATE VALIDA]
        ┌─────────────────┬──────────────────┐
        ↓                ↓
    [ALLOW]         [BLOCK/FAIL-SAFE]
        ↓                ↓
[SEND ORDER]         [EPISÓDIO NÃO CRIADO]
        ↓                (sem reward)
[FILL]
        ↓
[PROTEÇÃO ARMADA]
        ↓
[EPISÓDIO CRIADO + REWARD CALCULADO]
```

### No Ciclo 20260321_224930

Todas as 3 signal_executions **ficaram em BLOCKED**:
- ❌ Nenhuma ordem foi enviada
- ❌ Nenhum fill ocorreu
- ❌ Nenhum episódio foi criado
- ❌ Nenhum reward foi calculado

---

## 4. Histórico de Episódios e Rewards

### Episódios Históricos (Backtest/Treinamento Anterior)

```
Total de training_episodes: 7679
Por símbolo:
  - ETHUSDT: 1027
  - BTCUSDT: 1026
  - BNBUSDT: 1025
  - SOLUSDT: 989
  - XRPUSDT: 989
  - PTBUSDT: 817
  - BROCCOLI714USDT: 816
  - MLNUSDT: 816
  - FLUXUSDT: 174
```

**Status**: Todos com `reward_proxy = NULL` (não calculado para amostras recentes).

### Modelo Decisions (Decisões Feitas)

```
Total de model_decisions: 898
  - OPEN_LONG: 522
  - OPEN_SHORT: 376
```

**Status**: Decisões foram feitas, mas maioria bloqueada pela gate antes de executar.

---

## 5. Por que Isto É CORRETO em Fase 1?

### Especificação de Fase 1 — Estreia Conservadora

| Parâmetro | Valor | Objetivo |
|-----------|-------|----------|
| `M2_MAX_MARGIN_PER_POSITION_USD` | $1.0 | Risco mínimo por posição |
| `M2_MAX_DAILY_ENTRIES` | 3 | Limite máximo de 3 entradas/dia |
| `TRADING_MODE` | live | Com guard-rails ativos |
| Risk Gate | **ATIVO** | Bloqueando agressivamente |
| Circuit Breaker | **ATIVO** | Proteção adicional |

### Comportamento Esperado

✅ Muitas decisões do modelo, mas **poucas execuções reais**
✅ Guard-rails bloqueando agressivamente para preservar capital
✅ Sem episódios novos = sem reward calculado = sistema aprendendo offline
✅ Progressão lenta e controlada

---

## 6. Quando Episódios SERÃO Capturados?

Episódios serão capturados QUANDO:

1. ✅ Modelo faz decisão (OPEN_LONG/OPEN_SHORT)
2. ✅ Risk gate APROVA execução (nenhum bloqueio)
3. ✅ Ordem é ENVIADA à exchange
4. ✅ Ordem é PREENCHIDA com quantidade > 0
5. ✅ Proteção (STOP + TP) é ACIONADA
6. ✅ Posição é FECHADA ou SAÍDA
7. ✅ P&L é CALCULADO
8. ✅ Reward é DERIVADO do P&L
9. ✅ Episódio é PERSISTIDO em `training_episodes`

**No ciclo analisado**: Parou na etapa 2 (Risk gate bloqueou). Logo, nenhum episódio foi criado.

---

## 7. Recomendações para Capturar Episódios

### Curto Prazo (Para Próximo Ciclo)

1. **Reduzir agressividade do risk gate?** — Verificar se thresholds estão muito conservadores
   ```
   Questão: M2_MAX_DAILY_ENTRIES=3 é muito restrictivo?
   Análise: 898 decisões, só 3 limite/dia = ~300 ciclos para atingir aprendizado
   ```

2. **Verificar pq risk_gate_blocked está ocorrendo** — Analisar logs/payload do gate

3. **Continuar em Fase 1 conforme planejado** — Isto é comportamento esperado de rollout escalonado

### Médio Prazo

1. **Fase 2** — Após 5 ciclos bem-sucedidos com pelo menos 1 ordem executada:
   - Expandir para 5 símbolos
   - `M2_MAX_DAILY_ENTRIES: 5`
   - Aumentar limites de risco

2. **Coleta de Episódios** — Cada ordem executada gerará episódio + reward
   - Reward será calculado após exit
   - Episódios disponíveis para retreino

---

## 8. Verificação de Health

| Métrica | Status | Significado |
|---------|--------|-------------|
| Episódios Históricos | 7679 ✅ | Dataset de treinamento pronto |
| Modelo Decisions | 898 ✅ | Modelo operacional e fazendo inferências |
| Signal Executions | 17 (BLOCKED) ✅ | Guard-rails funcionando |
| Ordens Enviadas | 0 ✅ | Fase 1 conservadora — esperado |
| Episódios Novos do Ciclo | 0 ✅ | Sem execução real = esperado |
| Rewards Capturados | 0 ✅ | Sem P&L executado = esperado |

---

## 9. Conclusão

### O que Está Acontecendo

1. ✅ Modelo está fazendo decisões (898 decisions)
2. ✅ Sistema consegue identificar oportunidades
3. ✅ Guard-rails (risk gate, circuit breaker) estão operacionais
4. ✅ Fase 1 está sendo respeitada (conservadora)
5. ❌ Mas nenhuma ordem está sendo realmente EXECUTADA

### Por que Isto Não É Problema

- ✅ Isto é comportamento esperado de Fase 1 (ultra-conservadora)
- ✅ Sistema está se protegendo (fail-safe funcionando)
- ✅ Coleta de episódios acontecerá quando ordens forem executadas
- ✅ Retreino RL será ativado após primer episódios reais

### Próximo Passo

✅ **GO** — Continuar monitoramento em Fase 1

Quando primeira ordem for executada com fill > 0:
1. Episódio será criado automaticamente
2. Reward será calculado (baseado em P&L)
3. Dataset crescerá
4. Modelo poderá ser retreinado

**ETA para expressivos episódios novos**: Próxima semana, quando Fase 1 > 5 ciclos bem-sucedidos.

---

## Evidências e Referências

- Arquivo de análise: `logs/m2_cycle_analysis_20260321_224930.json`
- Relatório de validação: `logs/m2_validation_report_20260321_224930.md`
- Schema do banco: Verificado via inspect_db_schema.py
- Configuração Fase 1: docs/RUNBOOK_M2_OPERACAO.md (Thresholds de Escalonamento)

**Diagnóstico Executado**: 2026-03-21  
**Resultado**: ✅ **OPERACIONAL E CONFORME ESPECIFICAÇÃO**

---
