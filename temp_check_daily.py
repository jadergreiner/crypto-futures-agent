import sqlite3
from datetime import datetime
import pytz

conn = sqlite3.connect('db/modelo2.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

tz = pytz.timezone('America/Sao_Paulo')
today_start = tz.localize(datetime(2026, 3, 31, 0, 0, 0))
today_end = tz.localize(datetime(2026, 3, 31, 23, 59, 59))

cursor.execute('''
SELECT symbol, status, COUNT(*) as qty FROM signal_executions
WHERE created_at >= ? AND created_at <= ?
GROUP BY symbol, status ORDER BY symbol, status
''', (today_start.isoformat(), today_end.isoformat()))

print('[EXECUÇÕES SIGNAL DO DIA 31/03]')
for row in cursor.fetchall():
    print(f"  {row['symbol']:10} | {row['status']:12} | {row['qty']} execuções")

cursor.execute('''
SELECT symbol, status, decision_id, created_at FROM signal_executions
WHERE created_at >= ? AND created_at <= ?
ORDER BY created_at
''', (today_start.isoformat(), today_end.isoformat()))

print('\n[DETALHE CRONOLÓGICO]')
for row in cursor.fetchall():
    print(f"  {row['symbol']:10} | {row['status']:12} | decision_id={row['decision_id']:6} | {row['created_at']}")

# Verificar qual é M2_MAX_DAILY_ENTRIES
with open('.env', 'r') as f:
    for line in f:
        if 'M2_MAX_DAILY_ENTRIES' in line:
            print(f'\n[CONFIG] {line.strip()}')

conn.close()
