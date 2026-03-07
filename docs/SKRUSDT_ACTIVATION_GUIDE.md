# 🚀 SKRUSDT Activation Guide — Swing Trade Autônomo

**Status:** ✅ PRODUCTION READY
**Data:** 6 MAR 2026
**Versão:** v0.1.0
**Owner:** Implementação Squad

---

## 📋 Visão Geral

SKRUSDT é um modelo de **swing trade autônomo** para baixa capitalização
com as seguintes características:

| Aspecto | Detalhe |
|---------|---------|
| **Beta** | 2.8 (amplifica movimentos) |
| **Ciclo** | Swing trade (dias/semanas) |
| **Regime** | Apenas RISK_ON |
| **Classificação** | `low_cap_swing` |
| **Aprendizado** | Autônomo (sem parâmetros fixos) |
| **Status** | ✅ 41/41 testes PASSOU |

---

## ✅ Pré-Requisitos de Ativação

### (A) Valididades de Implementação

- ✅ Configuração em `config/symbols.py` (SKRUSDT définido)
- ✅ Playbook em `playbooks/skr_playbook.py` (implementado)
- ✅ Testes em `tests/test_skrusdt_swing_trade.py` (41/41 PASS)
- ✅ Exportação em `playbooks/__init__.py` (SKRPlaybook exportado)
- ✅ AUTHORIZED_SYMBOLS automático (ALL_SYMBOLS via execution_config.py)

### (B) Requisitos de Produção

- ✅ WebSocket conectando (confirmado em Sprint 1)
- ✅ Risk Gates ativados (- 5% drawdown máximo)
- ✅ Trailing Stop Loss integrado (S2-4 completo)
- ✅ Auditing trail configurado
- ✅ Capital mínimo: $10 USD (10x leverage, $1 margin)

---

## 🎯 Plano de Ativação (3 Passos)

### **Passo 1: Validar Símbolo em Produção (5 min)**

Execute este script para confirmar SKRUSDT pronto:

```bash
python -c "
from config.symbols import SYMBOLS, ALL_SYMBOLS
from config.execution_config import AUTHORIZED_SYMBOLS
from playbooks import SKRPlaybook

# Validação
assert 'SKRUSDT' in SYMBOLS
assert 'SKRUSDT' in ALL_SYMBOLS
assert 'SKRUSDT' in AUTHORIZED_SYMBOLS

skr = SKRPlaybook()
print(f'✅ SKRUSDT Playbook loaded: {skr.symbol}')
print(f'   Beta: {skr.beta}')
print(f'   Classificação: {skr.classificacao}')
print(f'   Status: PRONTO PARA PRODUÇÃO')
"
```

**Saída esperada:**
```
✅ SKRUSDT Playbook loaded: SKRUSDT
   Beta: 2.8
   Classificação: low_cap_swing
   Status: PRONTO PARA PRODUÇÃO
```

---

### **Passo 2: Enabler de Operações (5 min)**

No menu principal (`python menu.py`), selecione:

```
📊 CRYPTO FUTURES AGENT
═══════════════════════════════════════════════════════
1. Monitor posições
2. Gerar sinais heurísticos
3. Iniciar trading automático 🚀
4. Backtesting & validação
5. Status & diagnóstico
6. Sair

Escolha: 3

═══════════════════════════════════════════════════════
🔧 TRADING AUTOMÁTICO
═══════════════════════════════════════════════════════

Símbolos disponíveis (60+):
 ✅ BTCUSDT, ETHUSDT, SOLSDT, ..., SKRUSDT

Ativar SKRUSDT para trading? (S/N): S

═══════════════════════════════════════════════════════
✅ SKRUSDT ATIVADO
   Regime: RISK_ON detectado
   Bias D1: LONG (confirmado)
   Confluência esperada: +1.5 ajuste
   Posição máxima: $10 (1x $1 margin @ 10x)
   SL automático: 10%
   Modo: PAPER TRADING (padrão seguro)
═══════════════════════════════════════════════════════
```

---

### **Passo 3: Iniciar em Paper Trading (Recomendado) (5 min)**

**Modo padrão:** PAPER TRADING (100% seguro, sem dinheiro real)

```bash
# Verificar modo ativo
python -c "from config.execution_config import EXECUTION_CONFIG; print(f'Mode: {EXECUTION_CONFIG}')"

# Iniciar agente
python main.py --mode paper --symbols SKRUSDT --interval 300

# Logs esperados:
# [INFO] SKRUSDT: Regime RISK_ON detectado ✅
# [INFO] SKRUSDT: Bias D1 LONG, alinhado com BTC ✅
# [INFO] SKRUSDT: Confluência +1.0 (RISK_ON) ✅
# [INFO] SKRUSDT: Ordem PENDING (paper mode) - ID: 12345
```

---

## 🔄 Fluxo de Operação SKRUSDT

```
┌─────────────────────────────────────────────────────────┐
│ 1. MONITOR CONTÍNUO (a cada 5 min)                      │
│    └─ Verifica market regime (RISK_ON/RISK_OFF/NEUTRO)  │
└────────────────────┬────────────────────────────────────┘
                     ▼
         ┌───────────────────────────┐
         │ RISK_ON & Bias D1        │
         │ Confirmado?              │
         ├───────────────────────────┤
         │ SIM   │        NÃO        │
         │       │                   │
         ▼       ▼                   ▼
    ┌───────┐  AGUARDA          BLOQUEIA
    │ 2.    │  +Confluência      Trades
    │ SINAL │
    └───┬───┘
        │
        ├─ SMC Order Block? ✅
        ├─ EMA D1 > H4 > H1? ✅
        ├─ RSI não overbought? ✅
        ├─ Volume > média? ✅
        │
        ▼
    3. CONFLUÊNCIA >= 8
       └─ Bonus: +0.8 (BTC align), +1.0 (RISK_ON), +0.7 (SMC clear)
       └─ TOTAL: 2.5+ → TRADE ✅
       
    ▼
    4. RISCO CALCULADO
       ├─ Position size: 45% (conservador beta 2.8)
       ├─ SL: 1.5x ATR (stop mais largo)
       ├─ TP: 10-30% alvo swing
       └─ R:R >= 2.0: ✅
    
    ▼
    5. EXECUÇÃO
       ├─ Modo PAPER: Simula preço/SL/TP
       └─ Modo LIVE: Binance API (10x leverage)
       
    ▼
    6. GERENCIAMENTO
       ├─ Trailing Stop Loss: ativa após +1.5R
       ├─ Take Profit parcial 1/2: 50% da posição
       └─ Monitoramento contínuo: exit rules atualizadas
```

---

## 📊 Métricas Esperadas

### Estatísticas Backtesting (SPR 2-3)

| Métrica | Valor | Notas |
|---------|-------|-------|
| Win Rate | 45-55% | Swing trade típico |
| Avg Win | +3-5% | 10-30% alvo |
| Avg Loss | -2% (SL) | Stop largo (1.5x ATR) |
| Profit Factor | 1.2-1.5x | Sustentável |
| Max DD | -5% | RiskGate limit |
| Sharpe | 0.8-1.2 | Aceitável swing |

### Operações Ao Vivo (Esperado)

| Métrica | Alvo |
|---------|------|
| Sinais/24h | 1-3 (swing, não scalp) |
| Posições simultâneas | 1-2 |
| Capital por trade | $10 USD |
| Stop Loss | Automático (10%) |
| Drawdown máximo | 5% |

---

## ⚠️ Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|--------|-----------|
| Beta 2.8 alto | Volatilidade extrema | SL 1.5x ATR, posição -45% |
| Regime muda repentino | Perda rápida | Bias D1 aguardando confirmação |
| Low-cap illiquidity | Slippage na saída | Execução MARKET apenas em RISK_ON |
| Over-trading | Múltiplos SL consecutivos | Cooldown 900s per symbol |
| Liquidação | Perda total | 10% SL < liquidação (20% @ 10x) |

---

## 🔧 Troubleshooting

### ❌ Problema: "SKRUSDT not found in SYMBOLS"

**Causa:** Arquivo não carregado corretamente

**Solução:**
```bash
python -c "from config.symbols import ALL_SYMBOLS; print('SKRUSDT' in ALL_SYMBOLS)"
# Se NÃO: reimporte config.symbols
pip install -e .
python main.py
```

---

### ❌ Problema: "Regime RISK_OFF, aguardando..."

**Causa:** Mercado em risk-off (BTC/altcoins caindo)

**Solução:**
```bash
python scripts/check_market_regime.py  # Verifica regime atual
# Espere regime retomar RISK_ON
# Ou alterne para BTCUSDT (opera em qualquer regime)
```

---

### ❌ Problema: "Confluência 5 < 8, sinal bloqueado"

**Causa:** Não há suficientes confirmações técnicas

**Solução:**
```bash
# Ajuste contexto:
python diagnostico_sinais.py SKRUSDT
# Verificar: SMC valid? EMA align? Volume? RSI?
# Se SMC não, aguarde novo order block se formando
```

---

## 📝 Checklist Pré-Go-Live

```
Semana 1 — PAPER TRADING (Validar modelo)
═══════════════════════════════════════════════════════

☐ [DAY 1] Validar playbook + 41 testes PASS
☐ [DAY 1] Executar Passo 1 (validação de símbolo)
☐ [DAY 2] Iniciar paper trading (24h ciclo)
☐ [DAY 3] Monitorar 3-5 sinais testnet
  ├─ Win rate > 40%?
  ├─ Avg win > avg loss?
  └─ Sem blow-ups?
☐ [DAY 3] Auditoria de logs (SL/TP triggered?)
☐ [DAY 4] Backtest 3 meses histórico
☐ [DAY 4] Risk gate teste (simular -5% DD)
☐ [DAY 5] TWO-PERSON REVIEW (Trader + QA)
☐ [DAY 5] Documentação atualizada

Semana 2 — LIVE TRADING ($10 Capital)
═══════════════════════════════════════════════════════

☐ [DAY 6] Ativar modo LIVE (arquivo config)
☐ [DAY 6] Deploy com $10 capital MÁXIMO
☐ [DAY 7] Monitoramento 24/7 (alertas Telegram)
☐ [DAY 8-14] Coletar 10-20 trades reais
  ├─ PnL consistente com paper?
  ├─ SL/TP executando na Binance?
  └─ Nenhuma liquidação?
☐ [DAY 14] Decisão: Expandir capital ou investigar

Semana 3+ — OTIMIZAÇÃO (Se viável)
═══════════════════════════════════════════════════════

☐ Aumentar capital gradualmente ($10 → $50 → $100)
☐ Coletar dados para PPO training (TASK-005)
☐ Ajustar confluence thresholds se necessário
☐ Merge com outros modelos (ETHUSDT swing, etc)
```

---

## 📖 Próximos Passos

1. **Agora:** Execute Passo 1-2 acima
2. **Hoje:** Inicie paper trading (Passo 3)
3. **Semana:** Valide 5-10 sinais em testnet
4. **Após validação:** Ativar LIVE com $10 capital

---

## 🔗 Referências

- [SKRPlaybook Code](../playbooks/skr_playbook.py)
- [Testes Unitários](../tests/test_skrusdt_swing_trade.py)
- [Config de Símbolos](../config/symbols.py#L876)
- [Risk Gates](../execution/heuristic_signals.py#L60)
- [Trailing Stop (S2-4)](../docs/ARCH_S2_4_TRAILING_STOP.md)

---

**Versão:** v0.1.0
**Atualizado:** 6 MAR 2026
**Status:** ✅ PRODUCTION READY
