---
applyTo: core/model2/live_service.py
---

# M2 Reconciliation - Regras de Idempotencia

Estas regras se aplicam a mudancas em `core/model2/live_service.py`.

## Objetivo

Reforcar reconciliacao de estado e idempotencia no ponto critico de execucao.

## Regras de Reconciliacao

- Reconciliar banco e exchange antes de concluir estado final.
- Tratar dados da exchange como fonte externa sujeita a atraso.
- Se estado divergir, priorizar caminho seguro e registrar evento.

## Regras de Idempotencia

- Evitar envio duplicado para o mesmo `technical_signal_id`.
- Antes de enviar ordem, validar se ja existe execucao ativa equivalente.
- Em retries, usar chaves/identificadores estaveis para evitar duplicidade.

## Fail-safe

- Se faltarem dados criticos de fill/protecao, nao marcar sucesso final.
- Em inconsistencias nao classificadas, bloquear continuidade.
- Nunca contornar validacoes de risco para "destravar" fluxo.

## Evidencia e Auditoria

Registrar eventos com:

- `reason`
- `status`
- `timestamp`
- `metadata` (order_id, symbol, execution_id, origem da decisao)

## Escopo de Mudanca

- Fazer ajustes pequenos e localizados.
- Evitar refatoracao ampla durante incidente.
- Preservar compatibilidade do contrato atual do servico.

## Validacao Minima

- Validar cenarios de divergencia banco/exchange.
- Validar que retry nao gera ordem duplicada.
- Validar que posicao nao fica sem protecao por transicao de estado incorreta.
