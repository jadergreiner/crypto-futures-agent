import sqlite3
from datetime import datetime
import pytz
import json

tz_brt = pytz.timezone('America/Sao_Paulo')
conn = sqlite3.connect('db/modelo2.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Intervalo BRT do dia 31
brt_start = tz_brt.localize(datetime(2026, 3, 31, 0, 0, 0))
brt_end = tz_brt.localize(datetime(2026, 3, 31, 23, 59, 59))
brt_start_ms = int(brt_start.timestamp() * 1000)
brt_end_ms = int(brt_end.timestamp() * 1000)

cursor.execute('''
SELECT
    id,
    symbol,
    decision_id,
    status,
    created_at,
    failure_reason,
    execution_mode
FROM signal_executions
WHERE created_at >= ? AND created_at <= ? AND status NOT IN ('BLOCKED', 'CANCELLED')
ORDER BY created_at
''', (brt_start_ms, brt_end_ms))

print('[3 ENTRADAS DO DIA 31/03 BRT]\n')
entradas = cursor.fetchall()
for i, row in enumerate(entradas, 1):
    ms = row['created_at']
    dt_utc = datetime.utcfromtimestamp(ms / 1000)
    dt_brt = pytz.utc.localize(dt_utc).astimezone(tz_brt)

    print(f"{i}. {row['symbol']:10} | decision_id={row['decision_id']:6} | {row['status']:15} | {str(dt_brt)[:19]}")
    print(f"   Mode: {row['execution_mode']:8} | Failure: {row['failure_reason'] or 'None'}")
    print()

# Buscar detalhes adicionais das execuções FAILED
print('[DETALHES DAS EXECUÇÕES FAILED]\n')
cursor.execute('''
SELECT
    se.id,
    se.symbol,
    se.decision_id,
    se.failure_reason,
    see.event_type,
    see.details
FROM signal_executions se
LEFT JOIN signal_execution_events see ON se.id = see.signal_execution_id
WHERE se.created_at >= ? AND se.created_at <= ? AND se.status = 'FAILED'
ORDER BY se.created_at, see.id
''', (brt_start_ms, brt_end_ms))

for row in cursor.fetchall():
    print(f"[exec_id={row['id']:4}] {row['symbol']:10} decision_id={row['decision_id']:6}")
    if row['event_type']:
        print(f"  Event: {row['event_type']}")
        if row['details']:
            try:
                details = json.loads(row['details'])
                for k, v in details.items():
                    if len(str(v)) > 80:
                        print(f"    {k}: {str(v)[:77]}...")
                    else:
                        print(f"    {k}: {v}")
            except:
                print(f"  Details: {row['details'][:100]}")
    print()

conn.close()
