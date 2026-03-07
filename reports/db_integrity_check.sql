-- Script de Validação de Integridade do Database
-- Executar diariamente ou antes de operações críticas
-- Uso: sqlite3 db/crypto_futures.db < reports/db_integrity_check.sql

.headers on
.mode column

-- Cabeçalho do Relatório
SELECT '═══════════════════════════════════════════' as report;
SELECT 'VALIDAÇÃO DE INTEGRIDADE DO DATABASE' as title;
SELECT datetime('now', 'utc') as timestamp_utc;
SELECT '═══════════════════════════════════════════' as marker;
SELECT '';

-- Relatório 1: Resumo de Contagens
.title "1. CONTAGEM DE REGISTROS POR TABELA"
SELECT
  'trade_log' as tabela,
  COUNT(*) as registros,
  MAX(timestamp_entrada) as ultimo_registro
FROM trade_log
UNION ALL
SELECT
  'execution_log',
  COUNT(*),
  MAX(timestamp)
FROM execution_log
UNION ALL
SELECT
  'position_snapshots',
  COUNT(*),
  MAX(timestamp)
FROM position_snapshots
UNION ALL
SELECT
  'trade_signals',
  COUNT(*),
  MAX(timestamp)
FROM trade_signals;

SELECT '';

-- Relatório 2: Execuções Órfãs (CRÍTICO)
.title "2. CRÍTICO - EXECUÇÕES ÓRFÃS"
SELECT
  COUNT(*) as execucoes_orfas,
  CASE
    WHEN COUNT(*) = 0 THEN '✓ OK'
    WHEN COUNT(*) < 10 THEN '⚠️ MENOR'
    ELSE '🔴 CRÍTICO'
  END as status
FROM execution_log e
WHERE NOT EXISTS (
  SELECT 1 FROM trade_log t
  WHERE t.symbol = e.symbol
);

-- Detalhe dos orfãos (se houver)
SELECT
  e.id,
  e.timestamp,
  e.symbol,
  e.action,
  e.executed
FROM execution_log e
WHERE NOT EXISTS (
  SELECT 1 FROM trade_log t
  WHERE t.symbol = e.symbol
)
LIMIT 5;

SELECT '';

-- Relatório 3: Posições Obsoletas (> 30 dias)
.title "3. ALERTA - POSIÇÕES ABERTAS POR > 30 DIAS"
SELECT
  COUNT(*) as obsoletas,
  CASE
    WHEN COUNT(*) = 0 THEN '✓ OK'
    ELSE '⚠️ REVISÃO'
  END as status
FROM trade_log
WHERE timestamp_saida IS NULL
AND (strftime('%s', 'now') * 1000 -
     timestamp_entrada) > 2592000000;

-- Detalhe
SELECT
  trade_id,
  symbol,
  datetime(timestamp_entrada/1000, 'unixepoch') as aberta,
  ROUND((strftime('%s', 'now') * 1000 -
         timestamp_entrada) / 86400000.0) as dias_aberta
FROM trade_log
WHERE timestamp_saida IS NULL
AND (strftime('%s', 'now') * 1000 -
     timestamp_entrada) > 2592000000
ORDER BY timestamp_entrada ASC;

SELECT '';

-- Relatório 4: Trades Fechados Sem PnL
.title "4. CRÍTICO - TRADES FECHADOS SEM PnL"
SELECT
  COUNT(*) as sem_pnl,
  CASE
    WHEN COUNT(*) = 0 THEN '✓ OK'
    ELSE '🔴 INCONSISTÊNCIA'
  END as status
FROM trade_log
WHERE timestamp_saida IS NOT NULL
AND (pnl_usdt IS NULL OR pnl_pct IS NULL);

-- Detalhe
SELECT
  trade_id,
  symbol,
  datetime(timestamp_entrada/1000, 'unixepoch') as entrada,
  datetime(timestamp_saida/1000, 'unixepoch') as saida,
  pnl_usdt,
  pnl_pct
FROM trade_log
WHERE timestamp_saida IS NOT NULL
AND (pnl_usdt IS NULL OR pnl_pct IS NULL)
LIMIT 5;

SELECT '';

-- Relatório 5: Integridade de Banco de Dados
.title "5. VERIFICAÇÃO DE INTEGRIDADE DO BANCO"
PRAGMA integrity_check;

SELECT '';

-- Relatório 6: Tamanho e Performance
.title "6. TAMANHO DO BANCO E PERFORMANCE"
SELECT
  'Tamanho (MB)' as metrica,
  ROUND((SELECT page_count * page_size / 1024.0 / 1024.0
         FROM pragma_page_count(), pragma_page_size()), 2) as valor
UNION ALL
SELECT
  'Páginas',
  (SELECT page_count FROM pragma_page_count())
UNION ALL
SELECT
  'Último trade_log',
  datetime((SELECT MAX(timestamp_entrada) FROM trade_log)/1000,
          'unixepoch');

SELECT '';

-- Relatório 7: Resumo de Saúde
.title "7. RESUMO DE SAÚDE"
SELECT
  COUNT(*) as trades_abertos,
  ROUND(AVG(ABS(pnl_usdt)), 2) as pnl_medio,
  ROUND(MAX(pnl_usdt), 2) as maior_ganho,
  ROUND(MIN(pnl_usdt), 2) as maior_perda
FROM trade_log
WHERE timestamp_saida IS NOT NULL;

SELECT '';
SELECT '═══════════════════════════════════════════' as end_report;
SELECT 'FIM DA VALIDAÇÃO' as done;
SELECT '═══════════════════════════════════════════' as marker;
