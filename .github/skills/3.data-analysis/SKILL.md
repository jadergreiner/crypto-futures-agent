---
name: data-analysis
description: |
  Diagnostica candles, treino, posicoes e conciliacao com evidencia minima.
  Prioriza scripts de diagnostico e leitura localizada.
metadata:
  workflow-stage: 3
  focus:
    - evidencias-objetivas
    - leitura-minima
    - auditabilidade
user-invocable: true
---

# Skill: data-analysis

## Objetivo

Validar dados e estados operacionais com resposta curta, objetiva e auditavel.

## Modos

- `candles`: continuidade, consistencia OHLCV e cobertura.
- `treinamento`: volume minimo, NaN, fallback e checkpoint.
- `posicao`: estado real na Binance e precisao operacional.
- `conciliacao`: banco x exchange x trilha de eventos.

## Leitura Minima

1. Executar primeiro o diagnostico mais direto:
   `diagnostico_sinais.py`, `check_model2_db.py`, `check_rl_stage.py`,
   `posicoes.py`, `status.py`, `status_realtime.py`.
2. Ler codigo apenas se o diagnostico nao bastar:
   - candles: `core/model2/scanner.py`, `scripts/model2/scan.py`
   - treino: `agent/data_loader.py`, `core/model2/rl_model_loader.py`
   - exchange: `core/model2/live_exchange.py`
   - conciliacao: `core/model2/live_service.py`
3. Ler migrations ou `docs/MODELAGEM_DE_DADOS.md` so se houver duvida de
   schema ou contrato.

## Checklists Minimos

- Candles: gaps, OHLC invalido, volume negativo, cobertura e minimo H4.
- Treino: dados suficientes, split correto, NaN ou infinito, fallback ativo.
- Posicao: `positionAmt`, `entryPrice`, `leverage`, ordens pendentes.
- Conciliacao: execucao ativa sem posicao real, posicao orfa, eventos de
  divergencia e protecoes ausentes.

## Severidade

- `CRITICO`: risco financeiro imediato ou posicao desprotegida.
- `MODERADO`: dado incorreto sem risco imediato.
- `INFORMATIVO`: desvio de qualidade ou contexto.

## Guardrails

- Nunca executar ordens ou alterar posicoes sem confirmacao explicita.
- Nunca desabilitar `risk_gate.py` ou `circuit_breaker.py`.
- Consultas SQL devem ser `SELECT` salvo instrucao contraria.
- Em divergencia critica banco x exchange: bloquear, registrar e escalar.

## Saida

- escopo analisado
- evidencias minimas
- severidade
- causa provavel
- acao imediata

Limite alvo: 6-10 linhas.