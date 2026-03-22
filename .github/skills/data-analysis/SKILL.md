---
name: data-analysis
description: |
  Especialista em analise e validacao de dados de simbolos.
  Cobre candles, treinamento de modelos, posicoes abertas na Binance
  e conciliacao entre exchange e banco local.
metadata:
  tags:
    - data
    - validacao
    - candles
    - binance
    - reconciliacao
    - modelo2
  focus:
    - evidencias-objetivas
    - diagnostico-direto
    - auditabilidade
user-invocable: true
---

# Skill: data-analysis

## Objetivo

Validar e diagnosticar dados de simbolos com evidencias objetivas e
resposta direta.

Use esta skill para:

- validar qualidade e continuidade de candles OHLCV por simbolo
- diagnosticar dados usados em treinamento de modelos RL
- inspecionar posicoes abertas na Binance e comparar com estado esperado
- conciliar posicoes persistidas no banco com estado real da exchange
- identificar divergencias, lacunas e inconsistencias de dados

## Modo Economico

Regra principal: ler apenas os arquivos necessarios para responder
ao pedido com evidencia objetiva.

Ordem de leitura:

1. Ler o script de diagnostico mais direto para o pedido:
   - `diagnostico_sinais.py`, `check_model2_db.py`, `check_rl_stage.py`,
     `posicoes.py`, `status.py`, `status_realtime.py`.
2. Ler codigo de captura/validacao apenas se o diagnostico nao for
   suficiente:
   - Candles: `core/model2/scanner.py`, `scripts/model2/scan.py`.
   - Treinamento: `agent/data_loader.py`, `core/model2/rl_model_loader.py`.
   - Posicoes Binance: `core/model2/live_exchange.py`.
   - Conciliacao: `core/model2/live_service.py`.
3. Ler schema de banco apenas para validar estrutura ou colunas:
   - `scripts/model2/migrations/` (arquivos 0001 a 0009).
4. Ler `docs/MODELAGEM_DE_DADOS.md` so se houver duvida de contrato
   ou definicao oficial de campo.

Evitar:

- abrir investigacao longa quando o script de diagnostico ja responde
- reler modulos inteiros sem indicio concreto de problema
- executar scripts live sem confirmar modo (shadow/live) com o usuario
- criar artefatos temporarios ou tabelas de teste sem limpar depois

## Areas de Analise

### 1. Candles OHLCV

**Tabelas:** `ohlcv_h4`, `ohlcv_h1`, `ohlcv_d1` em `db/crypto_agent.db`.

**O que validar:**

- Existencia de registros para o simbolo e timeframe solicitados.
- Continuidade: lacunas de timestamp maiores que o esperado para o
  timeframe (H4 = 14400s, H1 = 3600s, D1 = 86400s).
- Consistencia OHLC: `high >= max(open, close)`,
  `low <= min(open, close)`, `low > 0`, `volume >= 0`.
- Cobertura de periodo: primeiro e ultimo candle em relacao ao esperado.
- Quantidade minima para treinamento: 500 candles H4.

**Fontes:**

- `core/model2/scanner.py` → `_load_candles()` para logica de carga.
- `scripts/model2/scan.py` → uso em producao.

**Diagnostico rapido (SQL):**

```sql
-- Contar candles por simbolo e timeframe
SELECT symbol, COUNT(*) AS total,
       MIN(timestamp) AS inicio, MAX(timestamp) AS fim
FROM ohlcv_h4
WHERE symbol = 'BTCUSDT'
GROUP BY symbol;

-- Detectar lacunas H4
SELECT a.timestamp AS fim_bloco, b.timestamp AS inicio_prox,
       (b.timestamp - a.timestamp) AS gap_s
FROM ohlcv_h4 a
JOIN ohlcv_h4 b ON b.timestamp = (
    SELECT MIN(timestamp) FROM ohlcv_h4
    WHERE symbol = a.symbol AND timestamp > a.timestamp
)
WHERE a.symbol = 'BTCUSDT'
  AND (b.timestamp - a.timestamp) > 14400
ORDER BY gap_s DESC
LIMIT 10;
```

---

### 2. Dados de Treinamento RL

**Arquivo principal:** `agent/data_loader.py`.

**O que validar:**

- Minimo de 500 candles H4 por simbolo antes do treino.
- Estrutura esperada: dicionario com chaves `h4`, `h1`, `d1`,
  `sentiment`, `macro`, `smc`, cada um contendo um DataFrame valido.
- Ausencia de NaN ou infinitos em features criticas.
- Split treino/validacao: `train_ratio=0.8` aplicado corretamente.
- Modo fallback ativado: se DB insuficiente, dados sinteticos
  (seed=42) sao usados — checar se isso e intencional.

**Checkpoint RL:**

- `core/model2/rl_model_loader.py` busca artefatos em `checkpoints/`,
  `models/`, com fallback determinista se PPO indisponivel.
- Verificar: timestamp do checkpoint, versao, log em `rl_training_log`.

**Diagnostico rapido:**

```bash
python check_rl_stage.py          # episodios disponiveis, status PPO
python -c "
import sqlite3; conn = sqlite3.connect('db/modelo2.db')
c = conn.cursor()
c.execute(\"SELECT * FROM rl_training_log ORDER BY id DESC LIMIT 5\")
for r in c.fetchall(): print(r)
"
```

---

### 3. Posicoes Abertas na Binance

**Arquivo principal:** `core/model2/live_exchange.py`.

**O que validar:**

- Resposta de `get_open_position(symbol)` versus estado esperado.
- Campos criticos: `positionAmt`, `entryPrice`, `unrealizedProfit`,
  `leverage`, `marginType`.
- Precisao de quantidade e preco: validar com `quantity_precision`
  e `price_precision` do cache da exchange.
- Posicao "fantasma": `positionAmt == 0` mas com ordem pendente.
- Alavancagem divergente do configurado em `config/risk_params.py`.

**Scripts de diagnostico:**

```bash
python posicoes.py           # resumo rapido com PnL
python status.py             # linha unica executivo
python status_realtime.py    # dashboard em tempo real
```

**Conferencia manual (exemplo):**

```python
from core.model2.live_exchange import LiveExchange
ex = LiveExchange()
pos = ex.get_open_position("BTCUSDT")
print(pos)
# Checar: positionAmt, entryPrice, unrealizedProfit
```

---

### 4. Conciliacao Binance x Banco Local

**Arquivo principal:** `core/model2/live_service.py`.

**Tabelas envolvidas (`db/modelo2.db`):**

| Tabela | Proposito |
|---|---|
| `signal_executions` | Estado local de cada execucao |
| `signal_execution_events` | Trilha de auditoria de transicoes |
| `technical_signals` | Sinais gerados para execucao |

**Ciclo de status da execucao:**

```
READY → ENTRY_SENT → ENTRY_FILLED → PROTECTED → EXITED
       └→ BLOCKED / FAILED / CANCELLED
```

**O que validar:**

- Execucoes com status `ENTRY_FILLED` ou `PROTECTED` sem posicao
  real na Binance (divergencia critica).
- Posicao real na Binance sem `signal_execution` correspondente
  (posicao orfao — risco operacional).
- Eventos de `RECONCILIATION_DIVERGENCE` recentes na tabela
  `signal_execution_events`.
- `filled_qty` e `filled_price` alinhados com fills reais da Binance.
- `stop_order_id` e `take_profit_order_id` validos e visiveis na
  Binance para execucoes `PROTECTED`.

**Diagnostico rapido (SQL):**

```sql
-- Execucoes ativas sem posicao real (requer cruzar com Binance)
SELECT id, symbol, status, filled_qty, filled_price,
       entry_filled_at, protected_at
FROM signal_executions
WHERE status IN ('ENTRY_FILLED', 'PROTECTED')
ORDER BY entry_filled_at DESC;

-- Divergencias registradas recentemente
SELECT se.symbol, see.event_type, see.rule_id,
       see.event_timestamp, see.payload_json
FROM signal_execution_events see
JOIN signal_executions se ON se.id = see.signal_execution_id
WHERE see.event_type LIKE '%DIVERGENCE%'
ORDER BY see.event_timestamp DESC
LIMIT 20;

-- Sinais nao consumidos mais antigos que 1h
SELECT id, symbol, timeframe, signal_side, status, signal_timestamp
FROM technical_signals
WHERE status = 'CREATED'
  AND signal_timestamp < (strftime('%s','now') - 3600) * 1000
ORDER BY signal_timestamp;
```

**Script de diagnostico:**

```bash
python check_model2_db.py    # schema + contagens por tabela
python diagnostico_sinais.py  # por que sinais nao sao gerados
```

---

## Fluxo Operacional

1. Classificar o pedido: candles | treinamento | posicao | conciliacao.
2. Executar o script de diagnostico mais direto para o caso.
3. Se o diagnostico nao for suficiente, ler os arquivos de codigo na
   ordem da secao "Modo Economico".
4. Identificar: lacunas, inconsistencias, divergencias ou erro de
   configuracao.
5. Classificar severidade:
   - `CRITICO` — risco financeiro imediato (posicao orfao, divergencia
     de quantidade, stop ausente).
   - `MODERADO` — dado incorreto sem impacto imediato (candle faltando,
     training fallback ativo).
   - `INFORMATIVO` — aviso de qualidade sem risco operacional.
6. Emitir diagnostico com: evidencia objetiva, severidade, arquivo
   afetado e acao recomendada.
7. Se houver risco `CRITICO`, alertar imediatamente e aguardar
   confirmacao antes de propor correcao automatizada.

## Guardrails

- Nunca executar ordens ou alterar posicoes sem confirmacao explicita.
- Nunca desabilitar `risk_gate.py` ou `circuit_breaker.py`.
- Consultas SQL devem ser `SELECT` (somente leitura) salvo instrucao
  contraria documentada.
- Em caso de divergencia critica banco x exchange: bloquear, registrar
  e escalar antes de agir.
- Dados sinteticos em producao devem gerar alerta — verificar se e
  fallback intencional.

## Formato de Resposta

Use saida estruturada com no minimo:

```
AREA: <candles | treinamento | posicao | conciliacao>
SIMBOLO: <BTCUSDT | todos | ...>
TIMEFRAME: <H4 | H1 | D1 | N/A>
SEVERIDADE: <CRITICO | MODERADO | INFORMATIVO>

EVIDENCIA:
  - <fato objetivo com valor, contagem ou timestamp>

ACHADOS:
  - <item 1>
  - <item 2>

ACAO RECOMENDADA:
  - <passo imediato>
```

Para consultas informativas, a saida pode ser mais curta.
Para riscos criticos, incluir sempre: simbolo, status no banco,
status na Binance, timestamp do ultimo evento e proposta de mitigacao.
