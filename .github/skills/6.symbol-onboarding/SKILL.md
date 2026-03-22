---
name: 6.symbol-onboarding
description: |
  Adiciona ou audita simbolo no M2 com checklist minimo e rastreavel.
  Foca em config, playbook, testes e validacao shadow.
metadata:
  workflow-stage: 6
  focus:
    - checklist-minimo
    - acao-direta
    - auditabilidade
user-invocable: true
---

# Skill: symbol-onboarding

## Objetivo

Adicionar ou validar um simbolo no pipeline M2 sem abrir leitura ampla.

## Leitura Minima

1. `config/symbols.py`
2. `playbooks/__init__.py`
3. um playbook existente em `playbooks/`
4. um teste de integracao existente em `tests/`

## Checklist Obrigatorio

1. Registrar o simbolo em `config/symbols.py` com campos obrigatorios.
2. Criar playbook especifico em `playbooks/`.
3. Registrar import e `__all__` em `playbooks/__init__.py`.
4. Criar teste de integracao para o simbolo.

## Checklist Opcional

1. Sincronizar OHLCV historico.
2. Rodar `scan`, `track` e `validate` em `shadow`.
3. Incluir em `M2_LIVE_SYMBOLS` so depois de validar dados e testes.
4. Rodar treino se o caso exigir.

## Guardrails

- Nao rodar live sem confirmar `M2_EXECUTION_MODE=shadow` primeiro.
- Nao mexer em `core/model2/` sem sintoma concreto.
- Se `config/symbols.py` mudar, sincronizar `README.md` e
  `playbooks/__init__.py`.
- Minimo de treino: 500 candles H4.

## Saida

- simbolo
- itens obrigatorios concluidos ou pendentes
- testes rodados
- risco residual para shadow ou live