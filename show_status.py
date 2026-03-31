#!/usr/bin/env python3
"""Display operational status summary."""

status = """
╔════════════════════════════════════════════════════════════════════════════╗
║                   STATUS OPERACIONAL - M2 31-MAR-2026                      ║
╚════════════════════════════════════════════════════════════════════════════╝

✅ CORREÇÃO APLICADA
   M2_SHORT_ONLY: true → false ✓
   Resultado: LONG agora permitida (sem bloqueio short_only_enforced)

────────────────────────────────────────────────────────────────────────────

📊 CICLO RECENTE (01:04-01:06 BRT)

   Decision #42807
   ├─ Ação: OPEN_LONG
   ├─ Confiança: 55%
   ├─ Timestamp: 2026-03-31 01:04:59 BRT
   └─ Source: RL_MODEL (m2-inference-v1)

   Execution #108
   ├─ Status: FAILED (nao FILLED)
   ├─ Gate: APROVADO (ready_for_live_execution)
   └─ Razao: Divergencia modelo-signal

────────────────────────────────────────────────────────────────────────────

🔴 PROBLEMA IDENTIFICADO - CONFLITO DE CONFIANÇA

   RL Model Output:
   ├─ rl_action: HOLD
   ├─ rl_confidence: 99.9%  ← MUITO ALTO
   ├─ market_regime: RISK_ON
   ├─ loss_streak: 4
   └─ recent_failure_ratio: 80%

   Sistema aplicou FAIL-SAFE:
   HOLD com 99.9% > LONG com 55% → Recusar execucao

────────────────────────────────────────────────────────────────────────────

⏳ AUTOAPRENDIZADO - EM PROGRESSO

   Episodios Pendentes: 12/100 episodios [████░░░░░░░░░░░░░░░░] 12%
   Faltam: 88 episodios
   ETA Proximo Retreino: ~35-40 minutos (6-8 ciclos de 5 min)

   Processo:
   1. Mais episodios sendo persistidos
   2. Quando atingir 100: Dispara retreino automatico
   3. Apos treino: Modelo atualizado em live_execute

────────────────────────────────────────────────────────────────────────────

VALIDACAO - PROXIMAS EXECUCOES

   Esperado Apos Retreino (em ~40 min):
   ├─ RL confidence: HOLD reduzido (modelo aprendeu)
   ├─ Decision: OPEN_LONG aumenta confianca
   ├─ Gate: Ainda aprova
   └─ Result: FILLED (ordem sera enviada ao mercado)

────────────────────────────────────────────────────────────────────────────

STATUS GERAL

   M2_SHORT_ONLY: CORRIGIDO
   Live Gate: OPERACIONAL
   Ciclo Continuo: ATIVO
   RL Model: CONVERGINDO (aguard 88 episodios)
   Guardrails: TODOS ATIVOS

   CONCLUSAO: Sistema funcionando corretamente em modo conservador

────────────────────────────────────────────────────────────────────────────

Detalhes completos: results/model2/status_operational_20260331.md

╚════════════════════════════════════════════════════════════════════════════╝
"""

print(status)
