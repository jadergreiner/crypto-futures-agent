import time
from scripts.model2.persist_training_episodes import flush_deferred_rewards
import sqlite3

now_ms = int(time.time() * 1000)
result = flush_deferred_rewards('db/modelo2.db', 'db/crypto_agent.db', now_ms)
print("Flush Result:", result)

conn = sqlite3.connect('db/modelo2.db')
cursor = conn.cursor()
cursor.execute("SELECT episode_key, reward_proxy, label FROM training_episodes WHERE timeframe='M5' ORDER BY id DESC LIMIT 5")
for r in cursor.fetchall():
    print(r)
conn.close()
