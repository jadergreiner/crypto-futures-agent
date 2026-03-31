import sqlite3
conn = sqlite3.connect('db/modelo2.db')
cursor = conn.cursor()

print("[DECISION_IDS NO DB]")
cursor.execute('SELECT decision_id, symbol FROM model_decisions WHERE decision_id IN (43337, 43341, 43343) ORDER BY decision_id')
for row in cursor.fetchall():
    print(f"  model_decisions: decision_id={row[0]:6} | {row[1]}")

print("\n[SIGNAL_EXECUTION_IDS NO DB]")
cursor.execute('SELECT decision_id, symbol FROM signal_executions WHERE decision_id IN (43337, 43341, 43343) ORDER BY decision_id')
for row in cursor.fetchall():
    print(f"  signal_executions: decision_id={row[0]:6} | {row[1]}")

print("\n[ÚLTIMAS 10 MODEL_DECISIONS]")
cursor.execute('SELECT decision_id, symbol, inference_result FROM model_decisions ORDER BY decision_id DESC LIMIT 10')
for row in cursor.fetchall():
    result = row[2][:30] if row[2] else 'None'
    print(f"  decision_id={row[0]:6} | {row[1]:10} | {result}")

print("\n[ÚLTIMAS 10 SIGNAL_EXECUTIONS]")
cursor.execute('SELECT decision_id, symbol, status FROM signal_executions ORDER BY decision_id DESC LIMIT 10')
for row in cursor.fetchall():
    print(f"  decision_id={row[0]:6} | {row[1]:10} | {row[2]:15}")

conn.close()
