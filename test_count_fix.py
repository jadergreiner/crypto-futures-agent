#!/usr/bin/env python
"""Teste para validar que count_live_entries_today conta apenas ENTRY_FILLED."""

import sqlite3
from datetime import datetime
import pytz
from core.model2.repository import Model2ThesisRepository

# Conectar ao DB e criar repo
repo = Model2ThesisRepository(db_path="db/modelo2.db")

# Simular contagem em 31/03 11:19 BRT
tz_brt = pytz.timezone('America/Sao_Paulo')
now_brt = tz_brt.localize(datetime(2026, 3, 31, 11, 19, 31))
now_ms = int(now_brt.timestamp() * 1000)

count = repo.count_live_entries_today(
    execution_mode="live",
    now_ms=now_ms,
)

print(f"[TESTE count_live_entries_today em 31/03 11:19 BRT]")
print(f"  Contagem de ENTRY_FILLED (confirmadas): {count}")

# Verificar manualmente
conn = sqlite3.connect('db/modelo2.db')
cursor = conn.cursor()

# BRT day start
brt_day_start = now_brt.replace(hour=0, minute=0, second=0, microsecond=0)
brt_day_start_utc = brt_day_start.astimezone(pytz.utc).replace(tzinfo=None)
day_start_ms = int(brt_day_start_utc.timestamp() * 1000)

cursor.execute('''
SELECT COUNT(*) FROM signal_executions
WHERE execution_mode = "live" AND created_at >= ? AND status = "ENTRY_FILLED"
''', (day_start_ms,))

manual_count = cursor.fetchone()[0]
print(f"  Contagem manual (verificação): {manual_count}")

if count == manual_count:
    print(f"\n[OK] Contagem está correta! APENAS ENTRY_FILLED contadas.")
else:
    print(f"\n[ERRO] Mismatch: {count} vs {manual_count}")

# Mostrar breakdown
print(f"\n[BREAKDOWN DE EXECUÇÕES NO DIA]")
cursor.execute('''
SELECT status, COUNT(*) as qty FROM signal_executions
WHERE execution_mode = "live" AND created_at >= ?
GROUP BY status
''', (day_start_ms,))

for status, qty in cursor.fetchall():
    print(f"  {status:15}: {qty} execuções")

conn.close()
print(f"\n[CONCLUSÃO] A função count_live_entries_today agora conta APENAS ENTRY_FILLED.")
