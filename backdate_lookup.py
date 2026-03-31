import sqlite3

conn = sqlite3.connect('db/modelo2.db')
cursor = conn.cursor()
cursor.execute("UPDATE training_episodes SET reward_lookup_at_ms = 0 WHERE status='BLOCKED' AND timeframe='M5' AND reward_proxy IS NULL")
print(f"Updated {cursor.rowcount} blocked M5 episodes.")
conn.commit()
conn.close()
