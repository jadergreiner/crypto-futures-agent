#!/usr/bin/env python3
"""Diagnosticar dados históricos disponíveis para aceleração de treinamento."""

import json
import sqlite3
from pathlib import Path

print("="*60)
print("DIAGNÓSTICO: Dados Históricos para Aceleração de Treinamento")
print("="*60)

# 1. Learning state
learning_state_path = Path('results/model2/learning_state.json')
if learning_state_path.exists():
    with open(learning_state_path) as f:
        state = json.load(f)
    print("\n[LEARNING STATE]")
    print(f"  Ciclos executados: {state.get('cycles_run', 0)}")
    print(f"  Episódios persistidos: {state.get('episodes_persisted', 0)}")
    print(f"  Acumulados para retreino: {state.get('episodes_accumulated', 0)}/100")
    print(f"  Último retreino: {state.get('last_retraining_at', 'nunca')}")

# 2. Schema e dados em modelo2.db
db2 = sqlite3.connect('db/modelo2.db')
cursor2 = db2.cursor()

# Tabelas disponíveis
cursor2.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%'"
)
tables = [t[0] for t in cursor2.fetchall()]
print(f"\n[MODELO2.DB - Tabelas: {len(tables)}]")
print(f"  Tabelas: {', '.join(tables)}")

# Oportunidades
try:
    cursor2.execute('''
        SELECT COUNT(*) as total,
               COUNT(DISTINCT symbol) as symbols
        FROM opportunities
    ''')
    opp_total, opp_symbols = cursor2.fetchone()
    print(f"  Oportunidades total: {opp_total} (símbolos: {opp_symbols})")
except Exception as e:
    print(f"  Oportunidades: erro {e}")

# Technical signals
try:
    cursor2.execute('''
        SELECT COUNT(*) as total,
               COUNT(DISTINCT signal_state) as states
        FROM technical_signals
    ''')
    sig_total, sig_states = cursor2.fetchone()
    print(f"  Technical signals: {sig_total} (states: {sig_states})")
except Exception as e:
    print(f"  Technical signals: erro {e}")

# Signal executions
try:
    cursor2.execute('''
        SELECT COUNT(*) as total,
               COUNT(DISTINCT outcome) as outcomes
        FROM signal_executions
    ''')
    exec_total, exec_outcomes = cursor2.fetchone()
    print(f"  Signal executions: {exec_total} (outcomes: {exec_outcomes})")
except Exception as e:
    print(f"  Signal executions: erro {e}")

# Training episodes
try:
    cursor2.execute('SELECT COUNT(*) FROM training_episodes')
    episodes_total = cursor2.fetchone()[0]
    print(f"  Training episodes: {episodes_total}")
except Exception as e:
    print(f"  Training episodes: erro {e}")

db2.close()

# 3. Oportunidades por outcome em crypto_agent.db (candles históricos)
db1 = sqlite3.connect('db/crypto_agent.db')
cursor1 = db1.cursor()

try:
    # Candles disponíveis
    cursor1.execute('''
        SELECT COUNT(*) as total,
               COUNT(DISTINCT timeframe) as timeframes,
               COUNT(DISTINCT symbol) as symbols
        FROM candles_1h
    ''')
    candles_total, timeframes, symbols = cursor1.fetchone()
    print(f"\n[CRYPTO_AGENT.DB - Candles]")
    print(f"  Total candles: {candles_total}")
    print(f"  Timeframes: {timeframes}, Símbolos: {symbols}")
except Exception as e:
    print(f"  Candles: erro {e}")

db1.close()

print("\n" + "="*60)
print("CONCLUSÃO: Há dados históricos suficientes?")
print("="*60)

if opp_total > 1000 and episodes_total < 100:
    print("✅ SIM - Usar oportunidades históricas para gerar episódios rápido")
    print(f"   {opp_total} oportunidades → gerar ~{min(100, opp_total//10)} episódios")
elif episodes_total >= 100:
    print("⚠️  Episódios já suficientes para retreino!")
else:
    print("❌ Dados insuficientes")
