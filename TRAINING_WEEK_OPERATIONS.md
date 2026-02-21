# TRAINING WEEK OPERATIONS MANUAL — 23-27 FEV 2026

Framework operacional para monitoramento de treinamento PPO Phase 4.

**Período:** 23 FEV 14:00 UTC → 27 FEV 16:00 UTC (~4 dias)
**Objetivo:** Treinar até convergência, validar 6 risk gates
**Owner:** ML Team
**Escalation:** CTO (decisão final)

---

## Dia 1: 23 FEV — Launch Day

### 08:00 UTC — Final Pre-Training Setup

**Responsável:** ML Engineer

Executar [ML_PRE_FLIGHT_CHECKLIST.md](ML_PRE_FLIGHT_CHECKLIST.md):
- [ ] Todos 6 checks completados
- [ ] Sem blockers
- [ ] Sistema pronto para treino

### 14:00 UTC — START TRAINING

**Comando:**
```bash
python scripts/start_ppo_training.py \
  --symbol OGNUSDT \
  --mode paper \
  --tag "F12-phase4-final" \
  --timestamp
```

**Esperado:**
```
[INFO] Starting PPO training...
[INFO] Model initialized
[INFO] Training loop started
[INFO] Step 1/500000
```

**Monitor paralelo:**
```bash
tensorboard --logdir=logs/ppo_training/tensorboard --port=6006
```
- Abrir: http://localhost:6006
- Visualizar: Rewards, Losses, KL divergence

### 14:00-19:00 UTC — FIRST 4 HOURS MONITORING (Hourly)

**Check @15:00 UTC (+1h):**
- [ ] Reward > 0?
- [ ] Loss diminuindo?
- [ ] Sem crashes?
- [ ] Speed OK? (1000+ steps/sec)

**Check @16:00 UTC (+2h):**
- [ ] Mesmos checks
- [ ] Policy loss < 1.0?

**Check @17:00 UTC (+3h):**
- [ ] Reward trend INCREASING ou STABLE?
- [ ] KL divergence < 0.01?

**Check @18:00 UTC (+4h):**
- [ ] Nenhuma anomalia até agora?
- [ ] Training still running?

**Log location:**
- Primary: `logs/ppo_training/training.log`
- Daily: `logs/ppo_training/daily_summaries/2026-02-23.json`

---

## Dias 2-4: 24-26 FEV — Daily Operations

### Daily Check-In (10:00 UTC)

**Duração:** ~2 minutos
**Responsável:** On-call ML Engineer
**Ferramenta:** `scripts/daily_training_check.py`

**Executar:**
```bash
python scripts/daily_training_check.py --date 2026-02-24
```

**Output esperado:**
```json
{
  "date": "2026-02-24",
  "training_status": "RUNNING",
  "time_elapsed_hours": 10,
  "estimated_time_remaining_hours": 60,
  "reward_trend": "INCREASING",
  "last_reward": 45.3,
  "approx_sharpe": 0.15,
  "kl_divergence_last": 0.008,
  "no_issues": true,
  "checklist": "✅ ✅ ✅ ✅ ✅"
}
```

**Checklist interpretação:**

| Métrica | Check | OK? | Ação se ✗ |
|---------|-------|-----|-----------|
| Training still running? | 1/5 | Status=RUNNING | Investigar hanging |
| Reward trend OK? | 2/5 | INCREASING ou STABLE | Check reward function |
| Sharpe estimate > 0.0? | 3/5 | approx_sharpe >= 0.0 | Não é zero? OK por agora |
| No KL spikes? | 4/5 | kl_divergence_last < 0.01 | Reduzir LR se spike |
| No crashes? | 5/5 | no_issues=true | Check logs |

### Optional Second Check (16:00 UTC)

Apenas se observado anomalia no check de 10:00 UTC.

**Investigar:**
- Logs: `tail -100 logs/ppo_training/training.log`
- Tensorboard: trends em últimas 2h
- Disk space: `du -sh models/ppo_phase4/`

### Logs location

```
logs/ppo_training/
├── training.log           # Main log (streaming)
├── daily_summaries/
│   ├── 2026-02-24.json
│   ├── 2026-02-25.json
│   └── 2026-02-26.json
└── tensorboard/
    └── events.out.tfevents.* (auto-generated)
```

---

## Dia 5: 27 FEV — Revalidation Day

### 14:00 UTC — Final Preparation

**Responsável:** ML Lead

- [ ] Confirmar training completou 500k steps
- [ ] Backup modelo: `cp -r models/ppo_phase4 models/ppo_phase4_BACKUP_27FEV`
- [ ] Confirmar dados de revalidação disponíveis
- [ ] Sistema pronto para rodar revalidação

### 16:00 UTC — EXECUTE REVALIDATION

**Comando:**
```bash
python scripts/revalidate_model.py \
  --model-path models/ppo_phase4/best_model \
  --backtest-data-dir data/backtest/ \
  --num-episodes 10 \
  --save-report
```

**Esperado:**
```
[INFO] Loading model...
[INFO] Running backtest...
[INFO] Computing metrics...
[INFO] Decision: GO / PARTIAL / NO-GO
```

**Report output:**
- `reports/revalidation/2026-02-27_decision.json`
- `reports/revalidation/2026-02-27_metrics.csv`

### 16:30 UTC — Parse Results

**Validação dos 6 gates:**

```
Gate 1: Sharpe Ratio ≥ 1.0
  Resultado: X.XX
  Status: ✅ PASS / ❌ FAIL

Gate 2: Max DD ≤ 15.0%
  Resultado: Y.Y%
  Status: ✅ PASS / ❌ FAIL

Gate 3: Win Rate ≥ 45.0%
  Resultado: Z.Z%
  Status: ✅ PASS / ❌ FAIL

Gate 4: Profit Factor ≥ 1.5
  Resultado: W.WW
  Status: ✅ PASS / ❌ FAIL

Gate 5: Consecutive Losses ≤ 5
  Resultado: N
  Status: ✅ PASS / ❌ FAIL

Gate 6: Calmar Ratio ≥ 2.0
  Resultado: V.VV
  Status: ✅ PASS / ❌ FAIL
```

**Decisão:**
- **GO:** 6/6 gates passed → Deploy para produção
- **PARTIAL:** 4-5/6 gates passed → CTO review + conditional deploy
- **NO-GO:** < 4/6 gates passed → Backtrack, investigar, retrain

### 17:00 UTC — ESCALATE TO CTO

**Entregar:**
- [ ] Decision document (GO/PARTIAL/NO-GO)
- [ ] 6 gates metrics
- [ ] Training logs summary
- [ ] Revalidation backtest report
- [ ] Recomendação (deploy / tune / retrain)

**Formato:**
```
═══════════════════════════════════════════════════════════
  REVALIDATION DECISION — 27 FEV 2026
═══════════════════════════════════════════════════════════

DECISION: [GO / PARTIAL / NO-GO]

GATES PASSED: N/6
  ✅ Gate 1: Sharpe
  ✅ Gate 2: Max DD
  ...

RECOMMENDATION: [Deploy / Tune / Retrain]

NEXT STEPS: 27 FEV 17:30 UTC (CTO Approval)

═══════════════════════════════════════════════════════════
```

---

## Troubleshooting Guide

### Cenário 1: Reward achatado (não muda)

**Sintoma:**
- Reward oscilando, mas média não muda após 2h

**Causa provável:**
- Reward function não diferencia ações
- Ou política já saturada

**Ações:**
1. Verificar tensorboard: `Reward` trend
2. Checar `agent/reward.py`: componentes estão diferentes?
3. Se continuar: aumentar `ent_coef` de 0.001 → 0.005 (mais exploração)
4. Log: `[ISSUE] Reward achatado, investigando componentes`

### Cenário 2: KL divergence explodindo

**Sintoma:**
- KL divergence > 0.5 (saltando)
- Policy mudando radicalmente

**Causa provável:**
- Learning rate muito alta
- Ou policy instável

**Ações:**
1. Verificar tensorboard: `KL Divergence` trend
2. Reduzir learning rate: 3e-4 → 1e-4 (config)
3. Reiniciar training com LR reduzido
4. Log: `[ISSUE] KL spike, reduzindo LR`

### Cenário 3: Training hung (sem progresso 2h)

**Sintoma:**
- Logs param de atualizar
- Não há novos checkpoints

**Causa provável:**
- Deadlock na data loading
- Ou crash silencioso

**Ações:**
1. Verificar processo: `ps aux | grep train_ppo`
2. Check logs: `tail -50 logs/ppo_training/training.log`
3. Kill e reiniciar: `kill -9 PID && python scripts/start_ppo_training.py`
4. Log: `[ISSUE] Training hung, restarted`

### Cenário 4: Metrics não sendo logged

**Sintoma:**
- tensorboard vazio
- logs/ppo_training/tensorboard/ sem eventos

**Causa provável:**
- TensorBoard writer não inicializado
- Ou permissão de escrita

**Ações:**
1. Verificar dir: `ls -la logs/ppo_training/tensorboard/`
2. Checar permissões: `chmod 755 logs/ppo_training/tensorboard/`
3. Verificar código: callback de logging em trainer.py
4. Log: `[ISSUE] Metrics not logging, checking writer`

### Cenário 5: Modelo não converge (esperado)

**Sintoma:**
- Após 12h, loss ainda flutuando muito
- Reward oscilando sem tendência clara

**Status:**
- **NORMAL** para PPO (especialmente primeiras 12h)
- Continuar monitorando
- Convergência pode levar 2-3 dias

**Ações:**
1. Não intervir (deixar treinar)
2. Log: `[CHECK] Training in initial phase, monitoring`
3. Verificar daily checks continuam OK

---

## Escalation Procedures

### Critical Issue (CRASH)

**Escalation Path:** ML Engineer → ML Lead → SWE Lead

**Ações:**
1. [ ] Parar training: `pkill -f train_ppo`
2. [ ] Backup logs: `cp logs/ppo_training/training.log logs/ppo_training/CRASH_backup.log`
3. [ ] Investigar: últimas 100 linhas de log
4. [ ] Contact SWE: "Critical crash in RL training loop"
5. [ ] Não reiniciar até investigação

### Performance Degradation (Reward plateauing)

**Escalation Path:** ML Engineer → ML Lead

**Ações:**
1. [ ] Confirmar reward realmente está achatado (não é visual)
2. [ ] Verificar reward function (alterou recentemente?)
3. [ ] Se persistir após 2h: contact ML Lead
4. [ ] Possível: Parar, ajustar params, retrain
5. [ ] Log: `[PERFORMANCE] Reward plateau detected`

### Data Issue (Gaps, NaN values)

**Escalation Path:** ML Engineer → SWE Lead

**Ações:**
1. [ ] Stop training imediatamente
2. [ ] Verificar dados: `python scripts/check_data_availability.py`
3. [ ] Backup checkpoint: `cp models/ppo_phase4/best_model.zip models/ppo_phase4/backup_before_bad_data.zip`
4. [ ] Contact SWE: "Data integrity issue detected"
5. [ ] Aguardar fix + restart

---

## Timeline Summary

| Dia | Horário | Ação | Status |
|-----|---------|------|--------|
| 23 | 08:00 | Pre-flight checks | ⬜ |
| 23 | 14:00 | **START TRAINING** | ⬜ |
| 23 | 15:00-19:00 | Hourly monitoring | ⬜ |
| 24 | 10:00 | Daily check-in | ⬜ |
| 25 | 10:00 | Daily check-in | ⬜ |
| 26 | 10:00 | Daily check-in | ⬜ |
| 27 | 14:00 | Final prep | ⬜ |
| 27 | 16:00 | **REVALIDATION** | ⬜ |
| 27 | 17:00 | CTO decision | ⬜ |

