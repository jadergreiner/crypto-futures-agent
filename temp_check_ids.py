import sqlite3
conn = sqlite3.connect('db/modelo2.db')
cursor = conn.cursor()
cursor.execute('SELECT symbol, decision_id, status, created_at FROM signal_executions WHERE decision_id IN (43343, 43341, 42903) ORDER BY created_at')
for row in cursor.fetchall():
    from datetime import datetime
    import pytz
    dt = datetime.utcfromtimestamp(row[3]/1000)
    print(f'{row[0]:10} | decision_id={row[1]:6} | {row[2]:15} | {str(dt)[:19]}')
conn.close()
