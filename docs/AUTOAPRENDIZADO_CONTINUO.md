# Autoaprendizado Contínuo no Operacional

## Visão Geral

O sistema está configurado para executar automaticamente o ciclo contínuo
de autoaprendizado (coleta → persistência → retreino → reload → decisão).

Sem qualquer intervenção do usuário humano.

## Fluxo Automático em iniciar.bat

```
[LOOP A CADA 5 MINUTOS]
  1. daily_pipeline.py (M5 OHLCV)
  2. live_cycle.py (operação + coleta de episódios)
  3. persist_training_episodes.py (persistência DB)
  4. healthcheck_live_execution.py (validações)
  5. operator_cycle_status.py (relatório por símbolo)

  [ETAPA AUTOMÁTICA - ZERO INTERVENÇÃO]
  6. continuous_learning_controller.py CHECK
      ↓ Verifica: ≥100 novos episódios OU ≥2h?
      ↓
      SIM → Executa continuous_learning_cycle.py
      NÃO → Pula para loop seguinte

  [SAÍDA AUTOMÁTICA DO CICLO]
  - JSON consolidado em results/model2/runtime/{run_id}.json
  - Drift report por símbolo
  - Status de retreino (modelos atualizados)
  - Métricas de decisão (model-first vs signal-first)

  7. continuous_learning_controller.py MARK (registra sucesso)
  8. Aguarda 5 minutos
  9. Volta ao passo 1
```

## Configuração

### Variáveis de Ambiente (.env)

```bash
M2_LEARNING_MIN_EPISODES=100
M2_LEARNING_MIN_HOURS=2.0
M2_LEARNING_ENABLED=true
```

### Thresholds Inteligentes

- **Primeira execução**: Dispara em 100 episódios acumulados
- **Execuções subsequentes**:
  - OU passou ≥ 2 horas desde última execução
  - OU acumulou ≥ 100 novos episódios

Resultado: Em fins de semana com baixo volume, executa no máximo a cada
2h. Em operação intensa, pode executar a cada 30-60 min.

## Logs Integrados

Todos os eventos são registrados em `logs/m2_cycle.log`:

```
[2026-03-31 10:15:00 BRT] [M2][LEARNING] Verificando condicoes...
[2026-03-31 10:15:01 BRT] [M2][LEARNING] Novos episódios: 125
[2026-03-31 10:20:30 BRT] [M2][LEARNING] *** CICLO CONCLUIDO ***
[2026-03-31 10:20:30 BRT] [M2] Aguardando 300s...
```

## Estado e Controle

Persistido em: `results/model2/learning_state.json`

Exemplo:

```json
{
  "last_continuous_run": "2026-03-31T10:20:30.123456",
  "last_episode_count": 1250,
  "runs": [
    {
      "timestamp": "2026-03-31T10:20:30",
      "episode_count": 1250,
      "symbols": ["BTCUSDT", "ETHUSDT"]
    }
  ]
}
```

## Comandos Manuais (OPCIONAL)

Apenas para diagnóstico:

```bash
python scripts/model2/continuous_learning_controller.py check

python scripts/model2/continuous_learning_controller.py status

python scripts/model2/continuous_learning_cycle.py --no-collection \
  --symbol BTCUSDT --symbol ETHUSDT
```

## Segurança e Fail-Safe

1. **Erro no ciclo ≠ Falha operacional**: Se falhar, loop continua.
   - `[M2][LEARNING] WARN: ciclo com erro (nao afeta fluxo)`

2. **Guardrails preservados**:
   - `risk_gate` e `circuit_breaker` NUNCA desabilitados
   - Decisão model-first com fallback signal-first
   - `decision_id` idempotência mantida

3. **Logs auditáveis**: Toda execução registrada em
   `learning_state.json`

## Fluxo de Decisão no Ciclo

Para cada símbolo:

1. Coleta episódios do DB (já feito em live_cycle.py)
2. Treina entry_agent (PPO)
3. Treina protection_head (SL/TP multipliers)
4. Recarrega policy models
5. Executa decision_probe (teste de inferência)
6. Calcula drift (ModelDegradationMonitor)
7. Se drift ≥ threshold → alert (continua operando)

## Saída JSON Consolidada

Arquivo: `results/model2/runtime/continuous_learning_cycle_<ts>.json`

```json
{
  "cycle_id": "2026-03-31T10:20:30_exec",
  "stages": {
    "sync_ohlcv": {"status": "OK", "duration_sec": 2.3},
    "persist_episodes": {"status": "OK", "duration_sec": 1.5},
    "train_entry_agents": {"status": "OK", "duration_sec": 45.2},
    "train_protection_heads": {"status": "OK", "duration_sec": 3.1},
    "decision_probe": {"status": "OK", "duration_sec": 8.9},
    "drift_analysis": {"status": "OK", "duration_sec": 4.2}
  },
  "total_duration_sec": 65.2,
  "decisions_by_symbol": {
    "BTCUSDT": {
      "sample_action": "OPEN_LONG",
      "model_confidence": 0.87,
      "signal_agreement": true
    }
  },
  "drift_report": {
    "BTCUSDT": {
      "status": "healthy",
      "win_rate": 0.62,
      "sharpe": 1.8
    }
  }
}
```

## Zero Intervenção Humana

✅ **O usuário não faz NADA**:

- Não monitora quando ciclo executa
- Não precisa confirmar retreino
- Não interpreta relatórios
- Não toma decisões heurísticas

✅ **O sistema faz TUDO**:

- Coleta dados automaticamente (live_cycle.py)
- Persiste episódios (persist_training_episodes.py)
- Decide quando treinar (continuous_learning_controller.py)
- Treina modelos (continuous_learning_cycle.py)
- Recarrega policies automaticamente
- Registra tudo em logs integrados
- Usa fail-safe em caso de erro

**Resultado**: Sistema operacional autônomo com autoaprendizado contínuo
integrado, completamente transparente e sem risco de falha em cascata.

---

**Última atualização**: 2026-03-31
**Status**: ✅ Implementado e testado
