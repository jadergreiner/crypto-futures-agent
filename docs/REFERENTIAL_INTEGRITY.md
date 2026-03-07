# Integridade Referencial do Database

## Relacionamentos de Entidades

### Ciclo de Vida de Trade (trade_log)

```
Evento de Entrada:
  timestamp_entrada → agente abre posição
       ↓
  Entrada registrada em trade_log
       ↓
  execution_log criado (action="OPEN")

Evento de Saída:
  agente_action = "CLOSE" OU SL/TP acionado
       ↓
  execution_log.executed = 1 (ordem preenchida)
       ↓
  monitor_positions.py detecta → UPDATE trade_log
       ↓
  timestamp_saida + pnl_usdt registrados
```

### Rastreamento de Execução (execution_log)

```
Decisão (position_monitor.py)
       ↓
order_executor.execute() → INSERT execution_log
       │
       └─ Antes do envio: action, executed=0
                ↓
          Resposta Binance:
          - Ordem aceita/rejeitada
          - Se preenchida: fill_price, fill_qty
                ↓
          UPDATE execution_log: executed=1, fill_price
```

## Regras de Integridade Críticas

### Regra 1: Toda Execução CLOSE Precisa de Trade

**Invariante:** Se execution_log.action = "CLOSE", deve existir
trade_log com mesmo símbolo e timestamp_entrada anterior.

**Validação:**

```sql
SELECT e.* FROM execution_log e
WHERE e.action IN ('CLOSE', 'REDUCE_50')
AND NOT EXISTS (
  SELECT 1 FROM trade_log t
  WHERE t.symbol = e.symbol
  AND t.timestamp_entrada < e.timestamp
);
```

**Se encontrado:** Investigar falha de sincronização

### Regra 2: Nenhuma Execução Órfã

**Definição:** execution_log sem correspondente em trade_log

**Detecção:**

```sql
SELECT COUNT(*) FROM execution_log e
WHERE NOT EXISTS (
  SELECT 1 FROM trade_log t
  WHERE t.symbol = e.symbol
);
```

**Ação se encontrado:** Auditoria e limpeza manual

### Regra 3: Trades Abertos Devem Ter Limite

**Regra:** Nenhuma posição aberta por > 30 dias sem revisão manual

**Detecção:**

```sql
SELECT * FROM trade_log
WHERE timestamp_saida IS NULL
AND (strftime('%s', 'now') * 1000 -
     timestamp_entrada) > 2592000000;
```

**Ação:** Avaliação e liquidação manual ou automática

### Regra 4: Trades Fechados Precisam Ter PnL

**Invariante:** Se timestamp_saida IS NOT NULL,
então pnl_usdt e pnl_pct devem ser NOT NULL

**Detecção:**

```sql
SELECT COUNT(*) FROM trade_log
WHERE timestamp_saida IS NOT NULL
AND (pnl_usdt IS NULL OR pnl_pct IS NULL);
```

**Se > 0:** Inconsistência crítica, requer auditoria

### Regra 5: PnL Deve Bater com Execução

**Invariante:** execute_log.executed=1 com action='CLOSE'
deve resultar em trade_log.timestamp_saida dentro de 60s

**Buffer:** 60 segundos para monitor_positions.py processar
e atualizar trade_log

## Procedimentos de Validação

### Validação Diária (Recomendada)

```bash
#!/bin/bash
# Executar diariamente às 00:00 UTC

sqlite3 db/crypto_futures.db << EOF

.headers on
.mode column

-- Verificação 1: Orfãos
SELECT 'ORFÃOS' as check,
  COUNT(*) as problemas
FROM execution_log e
WHERE NOT EXISTS (
  SELECT 1 FROM trade_log t
  WHERE t.symbol = e.symbol
);

-- Verificação 2: Trades Obsoletas
SELECT 'OBSOLETAS' as check,
  COUNT(*) as problemas
FROM trade_log
WHERE timestamp_saida IS NULL
AND (strftime('%s', 'now') * 1000 -
     timestamp_entrada) > 2592000000;

-- Verificação 3: PnL Faltando
SELECT 'PnL_FALTANDO' as check,
  COUNT(*) as problemas
FROM trade_log
WHERE timestamp_saida IS NOT NULL
AND (pnl_usdt IS NULL OR pnl_pct IS NULL);

-- Verificação 4: Integridade BD
PRAGMA integrity_check;

EOF
```

### Verificação Manual de Integridade

```bash
# Executar em demanda
sqlite3 db/crypto_futures.db "PRAGMA integrity_check;"
```

### Limpeza de Orfãos (Quando Necessário)

```sql
-- CUIDADO: Backup primeiro!
-- Lista orfãos para revisão
SELECT * FROM execution_log e
WHERE NOT EXISTS (
  SELECT 1 FROM trade_log t
  WHERE t.symbol = e.symbol
)
ORDER BY e.timestamp DESC;

-- Se confirmado como falso positivo:
-- DELETE FROM execution_log WHERE id IN (...);
```

## Requisitos de Auditoria

Ao fechar trade manualmente ou corrigir dados:

1. **Documentar mudança** com timestamp
2. **Registrar motivo** (SL_HIT, TP_HIT, MANUAL_OVERRIDE, etc.)
3. **Atualizar** trade_log.motivo_saida
4. **Criar execution_log** (se falta)
5. **Atualizar docs/SYNCHRONIZATION.md** com tag [FIX]

Exemplo:

```markdown
## [FIX] 2026-03-07 - Trade Manual Close

- Trade ID: 42
- Symbol: OGUSDT
- Entry: 2026-02-21 14:30 UTC
- Close: 2026-03-07 13:45 UTC
- Motivo: Revisão de risco (obsoleta > 30d)
- PnL: $-150.25 (-2.1%)
```

---

**Última atualização:** 2026-03-07
**Responsável:** Database Integrity Lead
**Frequência Check:** Diária (00:00 UTC)
