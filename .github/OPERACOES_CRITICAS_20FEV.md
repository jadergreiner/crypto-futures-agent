# 🔴 OPERAÇÕES CRÍTICAS — Diagnóstico 20/02/2026

**Referência Principal**: `.github/copilot-instructions.md`

---

## 🎯 Situação Crítica

**Data**: 20/02/2026 20:45 UTC  
**Status**: 🔴 CRÍTICO — Agente em Profit Guardian Mode, 0 sinais novos há 3+ dias

### Causa Raiz

`config/execution_config.py` linha 35:
```python
"allowed_actions": ["CLOSE", "REDUCE_50"]  # ❌ Bloqueia "OPEN"
```

### Impacto

- 21 pares monitorados mas 0 sinais novos gerados
- -$2.670/dia em oportunidades perdidas  
- 21 posições com perdas -42% a -511%

---

## 📚 Documentação Crítica

**LEIA OBRIGATORIAMENTE**:

1. **Reunião Diagnóstica**: `docs/reuniao_diagnostico_profit_guardian.md`
   - 10 rodadas de análise HEAD × Operador
   - Análise completa de problema e oportunidades

2. **Sumário Executivo**: `DIAGNOSTICO_EXECUTIVO_20FEV.md`
   - Insights principais
   - Decisão operacional

3. **Backlog de Ações**: `BACKLOG_ACOES_CRITICAS_20FEV.md`
   - 5 ações críticas com código pronto
   - Dependências explícitas

---

## 🚀 Plano de Ação (5 AÇÕES)

### ACAO-001 — Fechar 5 Maiores Posições (HOJE, 30 min)

**Status**: ⏳ Aguardando aprovação HEAD

**Arquivo**: `BACKLOG_ACOES_CRITICAS_20FEV.md` (linhas ~50-150)

**O que fazer**:
- Fechar BERTAUSDT, BTRUSDT, BCHUSDT, MERLUSDT, AAVEUSDT
- Usar MARKET orders
- Resultado: -$8.500 realizado

**Script**: `scripts/fechar_posicoes_fase1.py` (código pronto em backlog)

**Bloqueadores**: Nenhum (começar HOJE se aprovado)

---

### ACAO-002 — Validar Fechamento (HOJE, 15 min)

**Status**: 🔒 Bloqueado por ACAO-001

**O que fazer**:
- Verificar DB: `SELECT * FROM position_snapshots`
- Verificar Binance: `GET /fapi/v2/positionRisk`
- Confirmar 0 posições para 5 símbolos

**Script**: `scripts/validar_fase1.py` (código pronto em backlog)

**Resultado**: Arquivo `docs/FASE1_VALIDACAO_20FEV.md` criado

---

### ACAO-003 — Reconfigurar allowed_actions (HOJE, 10 min)

**Status**: 🔒 Bloqueado por ACAO-002

**Mudança Exata**:
```python
# Arquivo: config/execution_config.py
# Linha: 35

# ANTES:
"allowed_actions": ["CLOSE", "REDUCE_50"],

# DEPOIS:
"allowed_actions": ["OPEN", "CLOSE", "REDUCE_50"],
```

**Passos**:
1. Editar 1 linha (1 min)
2. Validação: `python -m py_compile config/execution_config.py` (1 min)
3. Reiniciar agente (5 min)

**Verificação**: Script `scripts/validar_allowed_actions.py` passa com sucesso

**Commit**: `[CONFIG] Habilitar 'OPEN' em allowed_actions — fim de Profit Guardian Mode`

---

### ACAO-004 — Executar Primeiro Sinal BTCUSDT LONG (AMANHÃ, 15 min)

**Status**: 🔒 Bloqueado por ACAO-003

**Parâmetros do Trade**:
```
Símbolo:    BTCUSDT
Direção:    LONG
Tamanho:    0.2 BTC
Entry:      ~42.850 (MARKET)
Stop Loss:  41.800 (1.2% risco)
TP:         43.200 (+3.2% reward)
Score:      5.7 (confluência confirmada)
```

**Quando**: AMANHÃ 06:00 UTC (Market Open Binance)

**Script**: `scripts/executar_primeiro_sinal_btc.py` (código pronto em backlog)

**Resultado**: Trade aberto, monitoring 1 hora

**Critério de Sucesso**: Permanece aberto >30 min sem stop hit imediato

---

### ACAO-005 — Reunião Follow-up 24h (AMANHÃ, 30 min)

**Status**: 🔒 Bloqueado por ACAO-004

**Quando**: 2026-02-21 ~16:00 BRT (24h após ACAO-003)

**Participantes**: HEAD + Operador

**Agenda**:
1. [5 min] BTCUSDT resultado (ganho ou perda?)
2. [10 min] Sinais novos gerados (quantos score >5.0?)
3. [5 min] FASES 2-3 aprovação (fechar resto?)
4. [10 min] Scaling decisão (aumentar tamanho?)

**Saída**: Decisão de roadmap + aprovação para scaling

**Arquivo Gerado**: `docs/FOLLOW_UP_20FEV_21H00.md`

---

## ⚡ Checklist de Sincronização Crítica

Sempre que trabalhar com diagnóstico/backlog:

```
□ IDENTIFICAR MUDANÇA
  └─ Qual aspecto do plano foi atualizado?

□ VERIFICAR DEPENDÊNCIAS
  ├─ Qual ACAO é bloqueadora?
  ├─ Qual ACAO depende dessa mudança?
  └─ Há impacto em config/execution_config.py?

□ ATUALIZAR DOCUMENTOS
  ├─ [ ] BACKLOG_ACOES_CRITICAS_20FEV.md
  ├─ [ ] docs/reuniao_diagnostico_profit_guardian.md
  ├─ [ ] DIAGNOSTICO_EXECUTIVO_20FEV.md
  ├─ [ ] docs/SYNCHRONIZATION.md
  ├─ [ ] README.md
  ├─ [ ] CHANGELOG.md
  └─ [ ] .github/OPERACOES_CRITICAS_20FEV.md (este arquivo)

□ EXECUTAR VALIDAÇÃO
  └─ python scripts/validar_allowed_actions.py

□ COMMITAR COM [OPERAÇÃO] TAG
  └─ git commit -m "[OPERAÇÃO] Descrição + qual ACAO"
```

---

## 🛑 Quando Há Bloqueios

### Se ACAO-001 Falhar

1. ❌ Marcar como FALHOU em BACKLOG_ACOES_CRITICAS_20FEV.md
2. ❌ Documentar erro em logs/fechar_posicoes_fase1_ERRO.log
3. ❌ Reportar em README.md seção crítica
4. 🔒 Bloquear ACAO-002 automaticamente
5. ⏸️ NÃO prosseguir para ACAO-003 até resolver

### Se Qualquer ACAO Falhar

1. ❌ Marcar como FALHOU em backlog
2. ❌ Atualizar README com status crítico
3. ⏸️ Aguardar decisão HEAD
4. 🔒 Bloquear qualquer ACAO subsequente

---

## ✅ Próximos Passos Após Sucesso

Se ACAO-005 passar com resultado > 50% win rate:

1. ✅ Aprovar FASES 2-3 (fechar resto posições)
2. ✅ Retreinar modelo com dados fevereiro 13-20
3. ✅ Aumentar tamanho: 0.2 BTC → 0.3-0.5 BTC (gradualmente)
4. ✅ Escalar: 1-2 trades/dia → 5-10 trades/dia
5. ✅ Aprovar co-location infraestrutura ($200/mês)

---

## 📞 Contato & Referências

**Documentos Principais**:
- Reunião diagnóstica: `docs/reuniao_diagnostico_profit_guardian.md`
- Sumário executivo: `DIAGNOSTICO_EXECUTIVO_20FEV.md`
- Backlog completo: `BACKLOG_ACOES_CRITICAS_20FEV.md`
- Sincronização: `docs/SYNCHRONIZATION.md`

**Responsáveis**:
- HEAD de Finanças: Decisão ACAO-001
- Operador: Execução de todas as AÇÕES
- Engenheiro: Reconfiguração ACAO-003

**Próxima Revisão**: 21/02/2026 16:00 UTC (após ACAO-005)

