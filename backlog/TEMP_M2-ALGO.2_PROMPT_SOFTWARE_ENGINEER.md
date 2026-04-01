# PROMPT PARA SOFTWARE ENGINEER — M2-ALGO.2

BLID: M2-ALGO.2 — Persistir episodios para retreino incremental de ALGOUSDT
Fase: GREEN-REFACTOR (TDD)
Arquivo alvo: scripts/model2/persist_training_episodes.py

## Contexto da task

ALGOUSDT em shadow acumula pendentes: 0/100 porque flush_deferred_rewards
busca candles M5 exclusivamente em source_db_path (legacy DB), mas os dados
M5 de ALGOUSDT estao em model2_db_path. Os episodios HOLD_DECISION ficam
presos em reward_proxy=NULL indefinidamente.

## Suite de testes RED (ja criada)

Arquivo: tests/test_model2_m2_algo_2_persist_episodes.py

Comando:
pytest -q tests/test_model2_m2_algo_2_persist_episodes.py

Resultado atual esperado (RED): 5 failed, 3 passed.

Falhas que devem virar GREEN:
1. test_flush_deferred_rewards_algousdt_usa_model2_fallback_quando_source_vazio
2. test_latest_candle_fallback_retorna_model2_quando_source_vazio
3. test_latest_candle_usa_source_quando_disponivel_ignora_fallback
4. test_flush_deferred_rewards_close_t_zero_usa_model2_fallback
5. test_collect_training_info_for_symbol_conta_pendentes_apos_flush

## Requisitos a implementar

RF-ALGO.2.1: flush_deferred_rewards preenche reward_proxy para ALGOUSDT M5
usando candle de model2_db quando source_db nao retorna resultado.

RF-ALGO.2.2: _latest_candle com fallback retorna candle de model2_db quando
source_db retorna None para ALGOUSDT, preservando prioridade de source_db.

RF-ALGO.2.3: Episodios HOLD_DECISION de ALGOUSDT transitam de label=pending
para hold_correct ou hold_opportunity_missed apos flush.

RF-ALGO.2.4: Episodios com reward_proxy != NULL, status HOLD_DECISION e
label != context sao contados por collect_training_info_for_symbol.

RF-ALGO.2.5: Sem regressao em BTCUSDT e demais simbolos.

## Guardrails

- Nao tocar em risk_gate.py e circuit_breaker.py.
- Nao alterar decision_id e contratos de idempotencia.
- Nao alterar schema DB.
- Nao alterar daily_pipeline.py e cycle_report.py neste escopo.
- Fallback deve ativar so quando source_db nao retorna candle.

## Implementacao GREEN (unico arquivo)

Arquivo: scripts/model2/persist_training_episodes.py

1) _latest_candle: aceitar fallback_conn opcional

Assinatura esperada:
def _latest_candle(
    conn: sqlite3.Connection,
    symbol: str,
    timeframe: str,
    *,
    fallback_conn: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:

Comportamento:
- Buscar no conn principal.
- Se nao encontrar e fallback_conn existir, buscar no fallback_conn.
- Se ainda nao encontrar, retornar None.
- Se conn principal encontrar, manter prioridade do principal.

2) flush_deferred_rewards: fallback para close_t base

No bloco onde close_t_raw e None ou <= 0:
- Buscar base_row em src_conn.
- Se base_row for None, buscar base_row em m2_conn.
- Preencher close_t_raw com base_row quando existir.

3) flush_deferred_rewards: fallback para candle_row de lookup

No bloco de candle_row:
- Buscar em src_conn.
- Se candle_row for None, buscar em m2_conn.
- So marcar pending quando continuar None nos dois.

4) run_persist_training_episodes: repassar fallback_conn

Nas chamadas de _latest_candle com source_conn, passar
fallback_conn=model2_conn.

Pontos esperados:
- latest_candle no loop de execution_rows
- latest_candle no context_episode
- qualquer outra chamada local equivalente

## Plano Green-Refactor

1. GREEN: implementar os 4 ajustes acima e rodar suite local da task.
2. REFACTOR: se necessario, extrair helper para consulta OHLCV com fallback.
3. Confirmar retrocompatibilidade (source_db mantem prioridade).

## Checklist de aceite

- [ ] pytest -q tests/test_model2_m2_algo_2_persist_episodes.py => 8 passed
- [ ] pytest -q tests/ => sem regressao
- [ ] mypy --strict scripts/model2/persist_training_episodes.py => Success
- [ ] Backlog atualizado para IMPLEMENTADO com evidencias

## Comandos de validacao

pytest -q tests/test_model2_m2_algo_2_persist_episodes.py
pytest -q tests/
mypy --strict scripts/model2/persist_training_episodes.py

## Resultado de negocio esperado

No iniciar.bat, ALGOUSDT deve sair de pendentes 0/100 e passar a acumular
pendentes ate 100 de forma autonoma, disparando retreino sem intervencao
manual e mantendo aud24h.conclusivo=sim.
