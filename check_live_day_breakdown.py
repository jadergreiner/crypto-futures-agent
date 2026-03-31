#!/usr/bin/env python3
import sqlite3
from datetime import datetime
import pytz

tz_brt = pytz.timezone('America/Sao_Paulo')
now_brt = tz_brt.localize(datetime(2026, 3, 31, 11, 19, 31))
brt_day_start = now_brt.replace(hour=0, minute=0, second=0, microsecond=0)
brt_day_start_utc = brt_day_start.astimezone(pytz.utc).replace(tzinfo=None)
day_start_ms = int(brt_day_start_utc.timestamp() * 1000)

conn = sqlite3.connect('db/modelo2.db')
cursor = conn.cursor()

print('[TODAS EXECUÇÕES LIVE NO DIA 31/03]')
cursor.execute('''
SELECT symbol, status, execution_mode, COUNT(*) FROM signal_executions
WHERE execution_mode = "live" AND created_at >= ?
GROUP BY symbol, status, execution_mode
ORDER BY status
''', (day_start_ms,))

for symbol, status, mode, qty in cursor.fetchall():
    print(f'  {symbol:10} | {status:15} | {mode:8} | {qty}')

print('\n[ENTRADA_FILLED LIVE]')
cursor.execute('''
SELECT COUNT(*) FROM signal_executions
WHERE execution_mode = "live" AND created_at >= ? AND status = "ENTRY_FILLED"
''', (day_start_ms,))
count = cursor.fetchone()[0]
print(f'  Total ENTRY_FILLED: {count}')

conn.close()
