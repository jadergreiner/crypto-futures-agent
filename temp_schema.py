import sqlite3
conn = sqlite3.connect('db/modelo2.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(signal_executions)")
cols = cursor.fetchall()
print('[COLUNAS signal_executions]')
for col in cols:
    print(f"  {col[1]:30} {col[2]}")

# Também verificar signal_execution_events
print('\n[COLUNAS signal_execution_events]')
cursor.execute("PRAGMA table_info(signal_execution_events)")
cols = cursor.fetchall()
for col in cols:
    print(f"  {col[1]:30} {col[2]}")
conn.close()
