import sqlite3
from datetime import datetime
import pytz

tz_brt = pytz.timezone('America/Sao_Paulo')
conn = sqlite3.connect('db/modelo2.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Intervalo BRT 31/03
brt_start = tz_brt.localize(datetime(2026, 3, 31, 0, 0, 0))
brt_end = tz_brt.localize(datetime(2026, 3, 31, 23, 59, 59))
brt_start_ms = int(brt_start.timestamp() * 1000)
brt_end_ms = int(brt_end.timestamp() * 1000)

print("[TODAS AS EXECUÇÕES BRT 31/03]")
cursor.execute('''
SELECT
    id,
    symbol,
    decision_id,
    status,
    created_at,
    failure_reason
FROM signal_executions
WHERE created_at >= ? AND created_at <= ?
ORDER BY created_at
''', (brt_start_ms, brt_end_ms))

results = cursor.fetchall()
print(f"Total: {len(results)} execuções\n")

for i, row in enumerate(results, 1):
    ms = row['created_at']
    dt_utc = datetime.utcfromtimestamp(ms / 1000)
    dt_brt = pytz.utc.localize(dt_utc).astimezone(tz_brt)
    print(f"{i}. {row['symbol']:10} | status={row['status']:15} | {str(dt_brt)[:19]} BRT | failure={row['failure_reason']}")

# Agora contar como a função count_live_entries_today faria
print("\n[CONTAGEM COMO EM count_live_entries_today]")

# Simular o cálculo com now = 11:12 BRT (quando ETHUSDT executou)
now_brt_11_12 = tz_brt.localize(datetime(2026, 3, 31, 11, 12, 0))
now_ms = int(now_brt_11_12.timestamp() * 1000)

day_start_ms = (int(now_ms) // 86_400_000) * 86_400_000
day_start_dt = datetime.utcfromtimestamp(day_start_ms / 1000)

print(f"now_ms = {now_ms} ({now_brt_11_12})")
print(f"day_start_ms = {day_start_ms} (UTC: {day_start_dt})")

cursor.execute('''
SELECT COUNT(*)
FROM signal_executions
WHERE execution_mode = 'live'
  AND created_at >= ?
  AND status NOT IN ('BLOCKED', 'CANCELLED')
''', (day_start_ms,))

count = cursor.fetchone()[0]
print(f"\nContagem em 11:12 BRT: {count} execuções")

conn.close()
