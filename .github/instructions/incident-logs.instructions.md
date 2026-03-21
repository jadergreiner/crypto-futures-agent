---
applyTo: logs/**
---

# Incident Logs - Padrao de Artefatos JSON

Estas regras padronizam artefatos de incidente em `logs/**`.

## Nome de Arquivo

Usar nomes descritivos com timestamp epoch ou UTC:

- `incident_<symbol>_<execution_id>_<ts>.json`
- `reconciliation_<symbol>_<execution_id>_<ts>.json`
- `protection_<symbol>_<execution_id>_<ts>.json`

Evitar nomes genericos como `temp.json`, `dump.json` ou `teste.json`.

## Campos Obrigatorios

Todo JSON de incidente deve conter:

- `timestamp_utc_ms`
- `incident_type`
- `severity` (`SEV-1`, `SEV-2`, `SEV-3`)
- `symbol`
- `execution_id` (ou `null` quando nao houver)
- `source` (script/modulo que gerou)
- `summary`
- `state_expected`
- `state_observed`
- `actions_taken` (lista)
- `next_actions` (lista)

## Qualidade de Conteudo

- Manter payloads minimamente suficientes para auditoria.
- Remover/mascarar segredos e credenciais.
- Usar tipos consistentes (numeros como numero, nao string quando possivel).
- Incluir `order_id` e referencias de eventos quando aplicavel.

## Guardrails

- Nao sobrescrever evidencia antiga sem preservar historico.
- Nao registrar dados sensiveis brutos de autenticacao.
- Nao salvar JSON invalido (sempre serializacao valida).

## Validacao Minima

Antes de concluir incidente, checar:

- arquivo com nome padronizado;
- campos obrigatorios presentes;
- JSON parseavel;
- coerencia basica entre `state_expected` e `state_observed`.
