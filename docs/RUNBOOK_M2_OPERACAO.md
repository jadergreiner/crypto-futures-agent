# Runbook - Operacao M2 (Daily Pipeline e Live)

## Objetivo

Padronizar a operacao do Modelo 2.0 em dois trilhos:

1. Pipeline diario de tese/sinal.
2. Execucao real nativa live/shadow.

## Escopo

Cobertura deste runbook:

1. M2-008.1, M2-008.2 e M2-008.3.
2. M2-009, M2-010, M2-011 e M2-012.

Componentes do pipeline diario:

1. `scripts/model2/daily_pipeline.py`
2. `scripts/model2/schedule_daily_pipeline.py`
3. `scripts/model2/healthcheck_daily_schedule.py`

Componentes do live:

1. `scripts/model2/live_execute.py`
2. `scripts/model2/live_reconcile.py`
3. `scripts/model2/live_dashboard.py`
4. `scripts/model2/healthcheck_live_execution.py`
5. `scripts/model2/live_cycle.py`
6. `scripts/model2/go_live_preflight.py`
7. `iniciar.bat` (entry point unificado Windows)

Artefatos esperados em `results/model2/runtime/`:

1. `model2_daily_pipeline_*.json`
2. `model2_daily_schedule_*.json`
3. `model2_daily_healthcheck_*.json`
4. `model2_live_execute_*.json`
5. `model2_live_reconcile_*.json`
6. `model2_live_dashboard_*.json`
7. `model2_live_healthcheck_*.json`
8. `model2_go_live_preflight_*.json`

## Pre-flight do live

Comando oficial de preflight (Windows, auto-fix por padrao):

```bash
python scripts/model2/go_live_preflight.py --live-symbol BTCUSDT
```

Modo validacao somente (sem auto-fix):

```bash
python scripts/model2/go_live_preflight.py --live-symbol BTCUSDT --no-apply
```

Comportamento esperado:

1. Valida os 10 itens do checklist de go-live da Fase 2.
2. Emite `model2_go_live_preflight_*.json` em `results/model2/runtime/`.
3. Retorna exit code `0` quando `status=ok` e `1` quando `status=alert`.
4. Mantem `next_actions` com itens manuais pendentes (ex.: revisao final do runbook).

## Operacao do daemon de coleta de features (Fases D.2-D.3)

O enriquecimento de episodios com dados de mercado (taxas de financiamento,
interesse aberto) requer um daemon background coletando dados da API.

### Inicie o daemon de funding rates

```bash
python scripts/model2/daemon_funding_rates.py --symbols BTCUSDT,ETHUSDT --interval 30
```

Parametros:

```
--symbols        Lista de pares separados por vírgula (default: BTCUSDT,ETHUSDT)
--interval       Intervalo de coleta em segundos (default: 30)
--max-age-hours  Descarta dados com mais de X horas (default: 24)
--db-path        Caminho do banco de dados (default: db/modelo2.db)
```

Comportamento esperado:

```
[INFO] Daemon iniciado: BTCUSDT, ETHUSDT
[INFO] Coleta a cada 30s
[INFO] 2026-03-14 10:30:45 | BTCUSDT: FR=0.000315 (bullish), OI=+2.1% (accum)
[INFO] 2026-03-14 10:31:15 | ETHUSDT: FR=-0.000041 (bearish), OI=-0.8% (dist)
```

Parar o daemon:

```bash
# (Ctrl+C na terminal ou kill o processo)
kill -TERM $(pgrep -f "daemon_funding_rates")
```

Monitorar coleta:

```bash
sqlite3 db/modelo2.db "SELECT COUNT(*), MAX(timestamp) FROM funding_rates_api;"
```

Esperado: >= 1000 registros/dia por par, com `MAX(timestamp)` recente.

### Verificar features enriquecidas em episodios

Uma vez com daemon rodando e pipeline executando (ver proxima secao):

```bash
sqlite3 db/modelo2.db \
  "SELECT COUNT(*), COUNT(CASE WHEN features_json LIKE '%funding%' THEN 1 END) \
   FROM training_episodes;"
```

Interpretacao:

- Primeira coluna: total de episodios.
- Segunda coluna: quantos com features de funding enriquecidas.
- Esperado >= 90% de episodios enriquecidos.

Se < 90%, o daemon nao conectou a tempo. Verifique:

1. Daemon esta rodando? `ps aux | grep daemon_funding_rates`
2. API Binance acessivel? `curl https://fapi.binance.com/fapi/v1/fundingRate`
3. Banco com permissoes? `ls -l db/modelo2.db`

## Operacao diaria do pipeline

### 1) Execucao do scheduler (once)

Comando recomendado para infraestrutura:

```bash
python scripts/model2/schedule_daily_pipeline.py --once --timeframe H4
```

### 2) Healthcheck pos-execucao

```bash
python scripts/model2/healthcheck_daily_schedule.py --runtime-dir results/model2/runtime --timezone UTC --require-today --expected-status ok
```

Interpretacao:

1. Exit `0`: operacao saudavel.
2. Exit `1`: alerta operacional.

## Operacao via iniciar.bat (estado atual)

No ambiente Windows, o entry point operacional recomendado e `iniciar.bat`.

1. Opcao `1`: fluxo legado (`menu.py`).
2. Opcao `2`: fluxo M2 continuo, executando por ciclo:
   - `daily_pipeline` (gera/atualiza sinais)
   - `live_cycle` (execucao/reconcile/dashboard)
   - `healthcheck_live_execution` (gate de saude)
3. O loop repete ate interrupcao manual (`Ctrl+C`).
4. Parametros operacionais:
   - `M2_LOOP_SECONDS` (default `300`)
   - `M2_RUN_ONCE=1` (executa apenas um ciclo)

## Operacao de treinamento do modelo PPO

### Fase 1: Coleta de episodios (continua no pipeline)

A cada ciclo do pipeline, automaticamente:

```bash
python scripts/model2/daily_pipeline.py --once
```

1. Coleta contexto de mercado (OHLCV, indicadores, estruturas).
2. Cria episodio com label `context` (amostra neutra para dataset).
3. Persiste em `training_episodes` da `db/modelo2.db`.

**Crescimento esperado:** ~8 episodios/ciclo × 288 ciclos/dia = 2.3k episodios/dia

### Fase 2: Treinamento incremental (semanal)

Quando tiver >= 500 episodios acumulados:

```bash
python scripts/model2/train_ppo_incremental.py --timesteps 500000 --device cuda
```

Parametros principais:

```
--timesteps       Numero de timesteps de treinamento (default: 500000)
--learning-rate   Taxa de aprendizado PPO (default: 1e-4)
--batch-size      Tamanho do batch (default: 128)
--device          CPU ou CUDA (default: CPU, mais lento)
--checkpoint-path Caminho do checkpoint anterior (para fine-tune)
```

Comportamento esperado:

```
[INFO] Carregando episodios...
  Total: 547 episodios
  Timeframe H4: 287
  Timeframe M5: 260
  Simbolos: 6 unicos

[INFO] Preparando dataset...
  Amostras: 547
  Shape observacao: (547, 5)
  Shape recompensa: (547,)
  Media de recompensa: 0.08

[INFO] Iniciando treinamento PPO...
  Batch size: 128
  Learning rate: 0.0001
  Epochs: 10
  Entropy coeff: 0.01

[INFO] Marcos de convergencia:
  Dia 1: Sharpe = 0.4 (baseline)
  Dia 2: Sharpe = 0.7 (melhoria)
  Dia 3: Sharpe = 1.0+ (pronto para producao)

[INFO] Salvando checkpoint...
  Arquivo: checkpoints/ppo_training/ppo_model.pkl
  Metadata: checkpoints/ppo_training/ppo_training_metadata_*.json
```

Verificar convergencia:

```bash
cat results/model2/training_metrics_*.json | jq '.sharpe_ratio'
```

Se `sharpe_ratio < 0.5`, nao usar modelo em producao. Reexperimentar com parametros.

### Fase 2.5: Monitoramento de Correlacoes (D.4)

Opcionalmente, analise a correlacao entre sentimento de taxas de financiamento
e performance de RL:

```bash
python scripts/model2/phase_d4_correlation_analysis.py --db-path db/modelo2.db --output-dir results/model2/analysis/
```

Interprete o resultado em `phase_d4_correlation_*.json`:

```json
{
  "fr_sentiment_vs_label": {
    "pearson_r": 0.2738,
    "p_value": 0.0058,
    "verdict": "SIGNIFICANTE (fraco positivo)",
    "win_rate_by_sentiment": {
      "bullish": 0.2581,    // 25.81% ganho
      "neutral": 0.3714,    // 37.14% ganho
      "bearish": 0.0        // 0% ganho - SINAL FORTE DE PERDA!
    }
  }
}
```

Acao recomendada:

1. Se `bearish` win_rate < 10%: Considere rejeitar sinais com FR extremamente
   bearish.
2. Se `bullish` win_rate > median+10%: Aumentar reward para sinais bullish.
3. Executar `phase_d4_...` toda semana para monitorar drift de correlacao.

### Fase 2.6: Treinamento com Politica LSTM (Fases E.1-E.3)

O treinamento PPO customizado para comparar desempenho já está implementado
(a partir de 15 MAR 2026). Para utilizar a nova política LSTM contra o
baseline MLP, utilize o script `train_ppo_lstm.py`.

```bash
# Treinar com rede MLP (Baseline Backward Compatible)
python scripts/model2/train_ppo_lstm.py --policy mlp --timesteps 50000

# Treinar usando arquitetura LSTM com histórico temporal
python scripts/model2/train_ppo_lstm.py --policy lstm --timesteps 50000
```

Este script encapsula de maneira transparente o `LSTMSignalEnvironment`, 
configurando `seq_len=10`, a rede customizada de Extração de Features, 
além de instanciar corretamente a `LSTMPolicy` do agente.

Pode-se verificar os modelos salvos em `checkpoints/ppo_training/lstm` ou
`checkpoints/ppo_training/mlp` gerados pela rotina.

### Fase 3: Validacao shadow (48-72h)

Uma vez com modelo pronto (`sharpe_ratio >= 0.5`):

```bash
M2_EXECUTION_MODE=shadow python scripts/model2/daily_pipeline.py --once
python scripts/model2/live_cycle.py
```

Monitorar:

1. Taxa de sinais com RL enhancement (esperado: >= 60%)
2. Divergencias entre RL prediction vs resultado real
3. Latencias do pipeline (esperado: < 5s)

Comando de inspecao:

```bash
cat results/model2/signal_enhancement_report_*.json | jq '.total_signals_enhanced_percent'
```

### Fase 4: Fine-tune iterativo (opcional)

Se observar problemas em shadow:

```bash
python scripts/model2/train_ppo_incremental.py --timesteps 100000 --checkpoint-path checkpoints/ppo_training/ppo_model.pkl
```

Opcoes de ajuste:

1. **Taxa de confianca baixa**: Aumentar `learning_rate` ou coletar mais dados.
2. **Overfitting**: Reduzir `batch_size` ou aumentar `entropy_coeff`.
3. **Divergencia vs manual**: Revisar features em `scripts/model2/rl_signal_generation.py`.
## Operacao do live

### 1) Ciclo manual recomendado

Staging e entrada:

```bash
python scripts/model2/live_execute.py --timeframe H4 --execution-mode shadow
```

Reconciliacao:

```bash
python scripts/model2/live_reconcile.py --timeframe H4 --execution-mode live
```

Dashboard:

```bash
python scripts/model2/live_dashboard.py --retention-days 30
```

Healthcheck:

```bash
python scripts/model2/healthcheck_live_execution.py --runtime-dir results/model2/runtime --max-age-hours 2 --max-unprotected-filled 0 --max-stale-entry-sent 0 --max-position-mismatches 0
```

### 2) Ciclo combinado

```bash
python scripts/model2/live_cycle.py --timeframe H4 --execution-mode shadow
```

### 3) Sequencia de rollout

1. Rodar em `shadow`.
2. Validar `model2_live_dashboard_*.json` e `model2_live_healthcheck_*.json`.
3. Ativar `M2_EXECUTION_MODE=live` com whitelist restrita.
4. Ampliar `M2_LIVE_SYMBOLS` progressivamente.

## Agendamento recomendado

### Linux (cron)

Exemplo diario em UTC:

```bash
5 0 * * * cd /path/repo && python scripts/model2/schedule_daily_pipeline.py --once --timeframe H4 >> logs/model2_schedule.log 2>&1
10 0 * * * cd /path/repo && python scripts/model2/healthcheck_daily_schedule.py --runtime-dir results/model2/runtime --timezone UTC --require-today --expected-status ok >> logs/model2_healthcheck.log 2>&1
```

Exemplo de loop live curto:

```bash
*/5 * * * * cd /path/repo && python scripts/model2/live_reconcile.py --timeframe H4 --execution-mode live >> logs/model2_live_reconcile.log 2>&1
*/10 * * * * cd /path/repo && python scripts/model2/live_dashboard.py >> logs/model2_live_dashboard.log 2>&1
*/10 * * * * cd /path/repo && python scripts/model2/healthcheck_live_execution.py --runtime-dir results/model2/runtime >> logs/model2_live_healthcheck.log 2>&1
```

### Windows (Task Scheduler)

Criar tarefas separadas:

1. `schedule_daily_pipeline.py --once --timeframe H4`
2. `healthcheck_daily_schedule.py --runtime-dir results/model2/runtime --timezone UTC --require-today --expected-status ok`
3. `live_reconcile.py --timeframe H4 --execution-mode live`
4. `live_dashboard.py`
5. `healthcheck_live_execution.py --runtime-dir results/model2/runtime`

## Sinais de incidente

Alertar quando qualquer condicao ocorrer:

1. Nao existe `model2_daily_schedule_*.json` do dia.
2. `status` do ultimo schedule diferente de `ok`.
3. Ultimo dashboard live acima do limite de recencia.
4. `unprotected_filled_count > 0`.
5. `stale_entry_sent_count > 0`.
6. `open_position_mismatches_count > 0`.

## Resposta a incidentes

### Incidente A: sem execucao no dia

1. Verificar logs do host (cron/Task Scheduler).
2. Executar manualmente:

```bash
python scripts/model2/schedule_daily_pipeline.py --once --timeframe H4
```

3. Reexecutar o healthcheck diario.

### Incidente B: entrada enviada e fill nao reconciliado

1. Abrir o ultimo `model2_live_reconcile_*.json`.
2. Confirmar se a execucao esta em `ENTRY_SENT`.
3. Validar ordem/posicao na exchange.
4. Reexecutar:

```bash
python scripts/model2/live_reconcile.py --timeframe H4 --execution-mode live
```

### Incidente C: posicao sem protecao

1. Abrir o ultimo `model2_live_dashboard_*.json`.
2. Confirmar `unprotected_filled_count`.
3. Executar reconciliacao imediatamente.
4. Se a protecao nao puder ser recriada, encerrar a posicao manualmente e abrir incidente.

### Incidente D: divergencia Binance x banco

1. Revisar `model2_live_dashboard_*.json` e `model2_live_healthcheck_*.json`.
2. Conferir `signal_executions` e `signal_execution_events` no banco.
3. Conferir ordens abertas, protecoes e posicoes na exchange.
4. Reexecutar `live_reconcile.py`.
5. Se persistir, congelar o rollout (`M2_EXECUTION_MODE=shadow`) ate correção.

## Evidencias minimas por dia

1. `model2_daily_schedule_*.json` com `status=ok`.
2. `model2_daily_healthcheck_*.json` com `status=ok`.
3. `model2_live_dashboard_*.json` atualizado.
4. `model2_live_healthcheck_*.json` com `status=ok`.
5. Logs do host sem falhas criticas.

## Atualizacao do loop via iniciar.bat (2026-03-14)

No ambiente Windows, opcao `2` do `iniciar.bat` executa por ciclo:

1. `sync_market_context` H4 para `M2_SYMBOLS`.
2. `sync_market_context` M5 para `M2_SYMBOLS`.
3. `daily_pipeline` H4 para `M2_SYMBOLS`.
4. `live_cycle` H4 para `M2_SYMBOLS`.
5. `persist_training_episodes` (dataset incremental).
6. `healthcheck_live_execution`.

Observacoes operacionais:

1. `M2_LIVE_SYMBOLS` define a fonte unica `M2_SYMBOLS` e filtra igualmente coleta/pipeline/live.
2. Deduplicacao de candle e aplicada por (`symbol`, `timestamp`).
3. O resumo do sync publica `candles_duplicated_skipped` por ciclo.

Artefatos adicionais em `results/model2/runtime/`:

1. `model2_market_context_*.json`
2. `model2_training_episodes_*.json`
3. `model2_training_episodes_*.jsonl`
4. `model2_training_episodes_cursor.json`

