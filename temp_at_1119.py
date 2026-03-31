import sqlite3
from datetime import datetime
import pytz

tz_brt = pytz.timezone('America/Sao_Paulo')
conn = sqlite3.connect('db/modelo2.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Simular contagem em 11:19 BRT (quando a saída foi gerada)
now_brt_11_19 = tz_brt.localize(datetime(2026, 3, 31, 11, 19, 31))
now_ms = int(now_brt_11_19.timestamp() * 1000)

day_start_ms = (int(now_ms) // 86_400_000) * 86_400_000

print("[EXECUÇÕES ATÉ 11:19 BRT]")
print("(simulando count_live_entries_today naquele momento)\n")

cursor.execute('''
SELECT
    symbol,
    status,
    created_at
FROM signal_executions
WHERE execution_mode = 'live'
  AND created_at >= ?
  AND created_at <= ?
  AND status NOT IN ('BLOCKED', 'CANCELLED')
ORDER BY created_at
''', (day_start_ms, now_ms))

results = cursor.fetchall()
for row in results:
    ms = row['created_at']
    dt_utc = datetime.utcfromtimestamp(ms / 1000)
    dt_brt = pytz.utc.localize(dt_utc).astimezone(tz_brt)
    print(f"  {row['symbol']:10} | {row['status']:15} | {str(dt_brt)[:19]} BRT")

print(f"\nTotal não-BLOCKED/CANCELLED até 11:19 BRT: {len(results)}")

# Também contar SE incluíssemos FAILED attempts
cursor.execute('''
SELECT COUNT(*) FROM signal_executions
WHERE execution_mode = 'live'
  AND created_at >= ?
  AND created_at <= ?
  AND status NOT IN ('BLOCKED', 'CANCELLED')
''', (day_start_ms, now_ms))

count_without_blocked = cursor.fetchone()[0]

cursor.execute('''
SELECT COUNT(*) FROM signal_executions
WHERE execution_mode = 'live'
  AND created_at >= ?
  AND created_at <= ?
''', (day_start_ms, now_ms))

count_all = cursor.fetchone()[0]

print(f"Contagem (sem BLOCKED): {count_without_blocked}")
print(f"Contagem (todos): {count_all}")

conn.close()
