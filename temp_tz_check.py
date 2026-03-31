import sqlite3
from datetime import datetime
import pytz

tz_brt = pytz.timezone('America/Sao_Paulo')
conn = sqlite3.connect('db/modelo2.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Contar no intervalo de 24h UTC do dia 31
utc_start = 1743379200000  # 31/03/2026 00:00 UTC em ms
utc_end = 1743465600000    # 01/04/2026 00:00 UTC em ms

cursor.execute('''
SELECT symbol, status, created_at FROM signal_executions
WHERE created_at >= ? AND created_at <= ? AND status NOT IN ('BLOCKED', 'CANCELLED')
ORDER BY created_at DESC
LIMIT 20
''', (utc_start, utc_end))

print('[ÚLTIMAS EXECUÇÕES NO PERÍODO UTC 31/03 00:00 - 01/04 00:00]')
for row in cursor.fetchall():
    ms = row['created_at']
    dt_utc = datetime.utcfromtimestamp(ms / 1000)
    dt_brt = pytz.utc.localize(dt_utc).astimezone(tz_brt)
    print(f"  {row['symbol']:10} | {row['status']:12} | UTC: {str(dt_utc):19} | BRT: {str(dt_brt):19}")

# Também verificar no intervalo BRT do dia 31
print('\n[TAMBÉM VERIFICAR: INTERVALO BRT]')
brt_start = tz_brt.localize(datetime(2026, 3, 31, 0, 0, 0))
brt_end = tz_brt.localize(datetime(2026, 3, 31, 23, 59, 59))
brt_start_ms = int(brt_start.timestamp() * 1000)
brt_end_ms = int(brt_end.timestamp() * 1000)

cursor.execute('''
SELECT symbol, status, created_at FROM signal_executions
WHERE created_at >= ? AND created_at <= ? AND status NOT IN ('BLOCKED', 'CANCELLED')
ORDER BY created_at DESC
''', (brt_start_ms, brt_end_ms))

total = 0
for row in cursor.fetchall():
    total += 1
    ms = row['created_at']
    dt_utc = datetime.utcfromtimestamp(ms / 1000)
    dt_brt = pytz.utc.localize(dt_utc).astimezone(tz_brt)
    print(f"  {row['symbol']:10} | {row['status']:12} | UTC: {str(dt_utc):19} | BRT: {str(dt_brt):19}")

print(f'\nTotal no intervalo BRT 31/03: {total}')
conn.close()
