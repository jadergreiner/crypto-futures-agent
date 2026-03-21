---
applyTo: scripts/model2/go_live_preflight.py
---

# Preflight Gates - Regras de Liberacao Live

Estas regras se aplicam a alteracoes em `go_live_preflight.py`.

## Objetivo

Assegurar que a promocao para live permaneça fail-safe, auditavel e
bloqueante quando houver risco relevante.

## Gates obrigatorios

- Validar ambiente e configuracao critica antes de qualquer liberacao.
- Validar controles de risco ativos (`risk_gate`, `circuit_breaker`).
- Validar prontidao de protecao obrigatoria (SL/TP) apos fill.
- Validar reconciliacao minima entre estado esperado e estado observavel.

## Politica de decisao

- Se houver incerteza relevante, retornar `NO_GO`.
- Sem evidencia minima, nao liberar promocao.
- Nao permitir fallback permissivo para contornar bloqueios.

## Evidencias minimas

- Resultado de checagens com timestamp UTC.
- Lista de bloqueios e motivo objetivo.
- Estado final consolidado: `GO`, `GO_COM_RESTRICOES` ou `NO_GO`.

## Guardrails

- Nao reduzir cobertura de validacao para ganhar velocidade.
- Nao acoplar logica de negocio fora do escopo do preflight.
- Nao mascarar erro critico como aviso.

## Validacao minima

- Cobrir caminho feliz e caminho bloqueante.
- Garantir mensagens de saida claras e acionaveis.
- Preservar compatibilidade com automacoes existentes.
