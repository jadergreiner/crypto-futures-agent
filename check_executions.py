import sqlite3

conn = sqlite3.connect('db/modelo2.db')
cursor = conn.cursor()
print("Executions:")
cursor.execute("SELECT id, technical_signal_id, symbol, timeframe, status, signal_side FROM signal_executions WHERE symbol='BTCUSDT' ORDER BY id DESC LIMIT 5")
for row in cursor.fetchall():
    print(row)

print("Decisions:")
cursor.execute("SELECT id, symbol, timeframe, action, reason_code FROM model_decisions WHERE symbol='BTCUSDT' ORDER BY id DESC LIMIT 5")
for row in cursor.fetchall():
    print(row)
conn.close()
