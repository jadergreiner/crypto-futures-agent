---
applyTo: core/model2/**
---

# Model2 Live - Regras Extras

Estas regras se aplicam a mudancas em execucao live do Modelo 2.0.

## Prioridade Absoluta

- Seguranca operacional vem antes de desempenho.
- Em duvida, falhar fechado (fail-safe) e bloquear operacao.
- Nunca desabilitar validacoes em `risk/risk_gate.py` e
  `risk/circuit_breaker.py`.

## Protecoes de Posicao

- Nenhuma entrada live deve permanecer sem protecao ativa.
- Apos fill de entrada, armar `STOP_MARKET` e `TAKE_PROFIT_MARKET`.
- Se o armamento falhar, aplicar retry com backoff e registrar evento.
- Nao seguir para estado de sucesso sem evidencia de protecao ou motivo
  explicito de bloqueio.

## Reconciliacao e Estado

- Tratar exchange como fonte externa sujeita a atraso e inconsistencias.
- Reconciliar ordens, fills e posicoes antes de concluir estado final.
- Registrar trilha auditavel em eventos (`reason`, `status`, `timestamp`,
  `metadata`).
- Preservar idempotencia: evitar ordem duplicada para o mesmo sinal.

## Fail-safe Operacional

- Se houver divergencia entre banco e exchange, priorizar estado seguro.
- Ao detectar risco nao classificado, cancelar/pausar em vez de assumir
  continuidade.
- Evitar fallback permissivo para ordem de mercado em fluxo de protecao.

## Escopo de Mudanca

- Mudancas devem ser pequenas, localizadas e sem alterar arquitetura global.
- Preferir ajustes em `live_exchange.py`, `live_service.py` e
  `live_execution.py` com compatibilidade retroativa.
- Manter logs e comentarios em portugues (pt-BR).

## Validacao Minima Antes de Entregar

- Executar testes relevantes: `pytest -q tests/`.
- Se alterar docs, atualizar `docs/SYNCHRONIZATION.md`.
- Em alteracoes de tipagem, rodar `mypy --strict` nos arquivos alterados.
