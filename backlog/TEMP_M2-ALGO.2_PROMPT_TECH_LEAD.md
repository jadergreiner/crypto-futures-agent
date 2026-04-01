PROMPT PARA 6.TECH-LEAD

BLID: M2-ALGO.2
Titulo: Persistir episodios para retreino incremental de ALGOUSDT
Status esperado no backlog: REVISADO_APROVADO ou DEVOLVIDO_PARA_REVISAO

Objetivo revisado
Implementacao GREEN-REFACTOR concluida para desbloquear acumulacao de episodios
eligiveis de ALGOUSDT no ciclo de treino incremental, com fallback de OHLCV no
DB canonico somente quando o DB source nao retorna candle.

Arquivos alterados neste pacote
- scripts/model2/persist_training_episodes.py
- tests/test_model2_m2_algo_2_persist_episodes.py
- docs/BACKLOG.md

Mapeamento requisito -> codigo -> teste

1. RF-ALGO.2.1 (flush usa fallback model2 quando source vazio)
- Codigo: fallback em consulta de candle de lookup e close_t base em
  scripts/model2/persist_training_episodes.py
- Testes:
  - tests/test_model2_m2_algo_2_persist_episodes.py
    caso test_flush_deferred_rewards_algousdt_usa_model2_fallback_quando_source_vazio
  - tests/test_model2_m2_algo_2_persist_episodes.py
    caso test_flush_deferred_rewards_close_t_zero_usa_model2_fallback
  - tests/test_model2_m2_algo_2_persist_episodes.py
    caso test_flush_deferred_rewards_pendente_quando_nenhum_db_tem_candle
    (fail-safe)

2. RF-ALGO.2.2 (_latest_candle com fallback opcional, mantendo prioridade source)
- Codigo: assinatura e comportamento de fallback em
  scripts/model2/persist_training_episodes.py
- Codigo adicional: chamadas em run_persist_training_episodes e
  _persist_hold_decision_episodes agora passam fallback_conn=model2_conn em
  scripts/model2/persist_training_episodes.py
- Testes:
  - tests/test_model2_m2_algo_2_persist_episodes.py
    caso test_latest_candle_fallback_retorna_model2_quando_source_vazio
  - tests/test_model2_m2_algo_2_persist_episodes.py
    caso test_latest_candle_sem_fallback_retorna_none_quando_source_vazio
  - tests/test_model2_m2_algo_2_persist_episodes.py
    caso test_latest_candle_usa_source_quando_disponivel_ignora_fallback

3. RF-ALGO.2.3 (transicao pending -> hold_correct/hold_opportunity_missed)
- Codigo: fluxo de flush mantido, agora com dados para calcular reward quando
  source nao tem candle em scripts/model2/persist_training_episodes.py
- Teste indireto: preenchimento de reward_proxy e label validado nos asserts
  dos casos de flush em tests/test_model2_m2_algo_2_persist_episodes.py

4. RF-ALGO.2.4 (contagem elegivel em collect_training_info_for_symbol)
- Codigo habilitador: reward_proxy passa a ser preenchido no flush em
  scripts/model2/persist_training_episodes.py
- Teste:
  - tests/test_model2_m2_algo_2_persist_episodes.py
    caso test_collect_training_info_for_symbol_conta_pendentes_apos_flush

5. RF-ALGO.2.5 (sem regressao para outros simbolos)
- Codigo: fallback so ativa quando source retorna vazio em
  scripts/model2/persist_training_episodes.py
- Teste:
  - tests/test_model2_m2_algo_2_persist_episodes.py
    caso test_flush_deferred_rewards_btcusdt_nao_usa_fallback_quando_source_tem_candle

Evidencias de validacao executadas

1. pytest focado da task
- Comando: pytest -q tests/test_model2_m2_algo_2_persist_episodes.py
- Resultado: 8 passed

2. mypy strict no modulo alterado
- Comando: mypy --strict scripts/model2/persist_training_episodes.py
- Resultado: Success, no issues found in 1 source file

3. regressao global
- Comando: pytest -q tests/
- Resultado: 361 passed in 112.64s

Guardrails verificados
1. risk_gate e circuit_breaker nao foram alterados
2. idempotencia por decision_id nao foi alterada
3. fail-safe preservado quando nenhum DB possui candle
4. retrocompatibilidade adicionada para ausencia de tabela no fallback
   (tratamento de sqlite OperationalError sem quebrar fluxo legado)

Atualizacao de backlog
- Item M2-ALGO.2 atualizado para IMPLEMENTADO com registro SE e evidencias em
  docs/BACKLOG.md

Impacto documental para handoff Doc Advocate
1. docs/BACKLOG.md atualizado com trilha PO/SA/QA/SE e evidencias tecnicas
2. Nao houve alteracao de regra de negocio, arquitetura global ou schema
3. Avaliar se precisa registrar trilha adicional em SYNCHRONIZATION na etapa
   documental final, conforme governanca vigente do fluxo

Pedido de decisao TL
Reproduzir os comandos de evidencia acima e decidir:
- APROVADO, se reproduzir verde, guardrails intactos e sem regressao
- DEVOLVIDO_PARA_REVISAO, se qualquer evidencia nao reproduzir ou houver risco
  operacional residual
