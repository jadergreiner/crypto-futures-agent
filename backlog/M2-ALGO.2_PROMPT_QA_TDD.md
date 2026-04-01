# HANDOFF DO SOLUTION ARCHITECT — M2-ALGO.2

**Para:** 4.qa-tdd
**Data:** 2026-04-01
**BLID:** M2-ALGO.2 — Persistir episodios para retreino incremental de ALGOUSDT
**Status backlog:** Em analise

---

## Objetivo

ALGOUSDT em shadow acumula `pendentes: 0/100` porque `flush_deferred_rewards`
busca candles M5 exclusivamente em `source_db_path` (legacy DB), mas os dados
M5 de ALGOUSDT foram gravados em `model2_db_path` pelo M2-ALGO.1. Os episodios
HOLD criados por `_persist_hold_decision_episodes` ficam presos em
`label='pending'`/`reward_proxy=NULL` indefinidamente, nunca satisfazendo a
eligibility rule do retreino incremental.

---

## Causa raiz tecnica (confirmada por leitura de codigo)

**Arquivo:** `scripts/model2/persist_training_episodes.py`

1. `flush_deferred_rewards(model2_db_path, source_db_path, now_ms)` (linha 399)
   consulta **somente** `src_conn` para o candle counterfactual:

   ```python
   candle_row = src_conn.execute(
       f"SELECT close FROM {table} WHERE symbol = ? AND timestamp > ? ...",
       (symbol, event_ts, lookup_ms),
   ).fetchone()
   if candle_row is None:
       pending += 1   # ALGOUSDT sempre cai aqui
       continue
   ```

   `src_conn` e a legacy DB (`DB_PATH`), que nao tem candles de ALGOUSDT.
   Os candles de ALGOUSDT estao em `model2_db_path`.

2. `_latest_candle(source_conn, symbol, timeframe)` (linha 133) tambem usa
   exclusivamente `source_conn`, retornando `None` para ALGOUSDT. Isso faz
   `features["close_t"] = 0.0` (linha 740), tornando o reward counterfactual
   invalido mesmo que o flush encontre o candle depois.

---

## Solucao tecnica (MVP minima e segura)

**Unico modulo a modificar:** `scripts/model2/persist_training_episodes.py`

**Mudanca 1 — `flush_deferred_rewards`:**
Apos `candle_row = src_conn.execute(...).fetchone()` retornar `None`,
tentar fallback em `m2_conn` com a mesma query antes de incrementar `pending`:

```python
if candle_row is None:
    # fallback: model2_db pode ter candles bootstrapados (ex: ALGOUSDT)
    candle_row = m2_conn.execute(
        f"SELECT close FROM {table} WHERE symbol = ? "
        f"AND timestamp > ? AND timestamp <= ? "
        f"ORDER BY timestamp DESC LIMIT 1",
        (symbol, event_ts, lookup_ms),
    ).fetchone()
```

Somente se ainda `None` -> `pending += 1`.

**Mudanca 2 — fallback de `close_t` dentro de `flush_deferred_rewards`:**
Mesmo padrao no bloco de fallback de `close_t` (linhas 444-449):

```python
base_row = src_conn.execute(...).fetchone()
```

Adicionar fallback em `m2_conn` quando `base_row is None`.

**Mudanca 3 — `_latest_candle`:**
Aceitar parametro opcional `fallback_conn: sqlite3.Connection | None = None`.
Quando `conn` retorna `None`, tentar `fallback_conn` antes de retornar `None`.

**Mudanca 4 — `run_persist_training_episodes`:**
Passar `model2_conn` como `fallback_conn` nas chamadas de `_latest_candle`
que usam `source_conn` (linhas 741, 854, 984).

**Zero mudancas em:** `daily_pipeline.py`, `cycle_report.py`, schema DB,
`risk_gate`, `circuit_breaker`, `decision_id`.

---

## Requisitos funcionais verificaveis

| ID | Requisito |
|----|-----------|
| RF-ALGO.2.1 | `flush_deferred_rewards` preenche `reward_proxy` para ALGOUSDT M5 usando candle de `model2_db` quando `source_db` nao retorna resultado |
| RF-ALGO.2.2 | `_latest_candle` com fallback retorna candle de `model2_db` quando `source_db` retorna `None` para ALGOUSDT |
| RF-ALGO.2.3 | Episodios HOLD_DECISION de ALGOUSDT transitam de `label='pending'` para `label='hold_correct'` ou `label='hold_opportunity_missed'` apos flush |
| RF-ALGO.2.4 | Episodios de ALGOUSDT com `reward_proxy != NULL`, `status='HOLD_DECISION'`, `label != 'context'` sao contados por `collect_training_info_for_symbol` |
| RF-ALGO.2.5 | Comportamento de BTCUSDT e demais simbolos nao e alterado (fallback nao ativado quando `source_db` ja retorna resultado) |

## Requisitos nao funcionais

| ID | Requisito |
|----|-----------|
| RNF-ALGO.2.1 | `mypy --strict scripts/model2/persist_training_episodes.py` sem erros |
| RNF-ALGO.2.2 | `pytest -q tests/` sem regressoes |
| RNF-ALGO.2.3 | Fallback ativado somente quando `source_db` retorna `None` |
| RNF-ALGO.2.4 | `risk_gate`, `circuit_breaker` e idempotencia `decision_id` preservados |

---

## Modulos e funcoes afetados

```
scripts/model2/persist_training_episodes.py
  _latest_candle(conn, symbol, timeframe)
    -> adicionar parametro opcional: fallback_conn=None
  flush_deferred_rewards(model2_db_path, source_db_path, now_ms)
    -> fallback candle_row e close_t em m2_conn
  run_persist_training_episodes(...)
    -> passar model2_conn como fallback_conn nas chamadas _latest_candle
```

---

## Suite de testes esperada (RED phase)

Arquivo: `tests/test_model2_m2_algo_2_persist_episodes.py`

Nomenclatura: `test_<funcionalidade>_<condicao>_<resultado>`

### Testes obrigatorios

**test_flush_deferred_rewards_algousdt_usa_model2_fallback_quando_source_vazio**
- source_db sem M5 de ALGOUSDT; model2_db com candle M5 disponivel
- Esperado: `reward_proxy` preenchido, `flushed=1`, `pending=0`
- Cobre: RF-ALGO.2.1

**test_flush_deferred_rewards_btcusdt_nao_usa_fallback_quando_source_tem_candle**
- source_db com M5 de BTCUSDT
- Esperado: fallback nao ativado, comportamento identico ao atual
- Cobre: RF-ALGO.2.5

**test_flush_deferred_rewards_pendente_quando_nenhum_db_tem_candle**
- source_db e model2_db sem candle
- Esperado: `pending=1`, `reward_proxy` permanece `NULL`
- Cobre: RF-ALGO.2.1 (negativo)

**test_latest_candle_fallback_retorna_model2_quando_source_vazio**
- `_latest_candle(source_conn, 'ALGOUSDT', 'M5', fallback_conn=m2_conn)`
  com source_conn vazio
- Esperado: retorna candle de m2_conn
- Cobre: RF-ALGO.2.2

**test_latest_candle_sem_fallback_retorna_none_quando_source_vazio**
- `_latest_candle(source_conn, 'ALGOUSDT', 'M5')` sem fallback_conn
- Esperado: retorna `None` (comportamento atual preservado)
- Cobre: RF-ALGO.2.2 (retrocompatibilidade)

**test_flush_deferred_rewards_close_t_zero_usa_model2_fallback**
- Episodio com `features_json.close_t=0.0`; base candle ausente em source_db
  mas presente em model2_db
- Esperado: `close_t` preenchido via fallback antes de computar reward
- Cobre: RF-ALGO.2.1 (close_t fallback)

**test_run_persist_training_episodes_latest_candle_algousdt_usa_fallback**
- `run_persist_training_episodes` com ALGOUSDT; source_db sem M5;
  model2_db com M5
- Esperado: feature `latest_candle` populada para episodio de contexto
- Cobre: RF-ALGO.2.2

**test_collect_training_info_for_symbol_conta_pendentes_apos_flush**
- Integracao: cria episodio HOLD_DECISION para ALGOUSDT com `reward_proxy=NULL`;
  executa `flush_deferred_rewards` com fallback; verifica que
  `collect_training_info_for_symbol` retorna `pending >= 1`
- Cobre: RF-ALGO.2.4

---

## Guardrails obrigatorios nos testes

- **Nunca mockar** `risk_gate` ou `circuit_breaker`
- Cada teste valida **um unico requisito**
- Usar `sqlite3.connect(':memory:')` para DBs de teste
- `decision_id` nao e alterado — episodios HOLD tem `execution_id=0`
  por contrato existente (nao mudar)
- Nomear arquivo: `tests/test_model2_m2_algo_2_persist_episodes.py`

---

## Plano Green-Refactor para Software Engineer

1. **GREEN**: implementar fallback em `_latest_candle`, em ambos os pontos
   de `flush_deferred_rewards` (candle counterfactual e close_t), e passar
   `fallback_conn` em `run_persist_training_episodes`
2. **REFACTOR**: se a logica de fallback aparecer 3+ vezes, extrair para
   funcao auxiliar `_query_ohlcv_with_fallback`
3. **Validacao final**:
   - `pytest -q tests/test_model2_m2_algo_2_persist_episodes.py` -> todos GREEN
   - `pytest -q tests/` -> sem regressoes
   - `mypy --strict scripts/model2/persist_training_episodes.py` -> Success

---

## Referencia de codigo

- `flush_deferred_rewards` linha 399 `persist_training_episodes.py`
- `_latest_candle` linha 133 `persist_training_episodes.py`
- `_persist_hold_decision_episodes` linha 686 `persist_training_episodes.py`
- `collect_training_info_for_symbol` linha 628 `core/model2/cycle_report.py`
- `TRAINING_EPISODE_ELIGIBLE_STATUSES` linha 30 `core/model2/cycle_report.py`
  (inclui `"HOLD_DECISION"`)

---

**PO:** `pendentes` para ALGOUSDT deve acumular autonomamente ate 100 e o
retreino disparar sem intervencao manual, confirmado por
`aud24h.conclusivo=sim` no `iniciar.bat`.
