#!/usr/bin/env python3
"""Verificar captura de episodios durante ciclo live."""

import sqlite3
from pathlib import Path

DB_PATH = Path("db/modelo2.db")

def check_episodes():
    """Verificar episódios no banco."""
    if not DB_PATH.exists():
        print(f"❌ Banco não encontrado: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Verificar tabelas
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in c.fetchall()]
    print(f"\n📊 Tabelas encontradas ({len(tables)}):")
    for table in tables:
        print(f"  - {table}")

    # Verificar episódios
    try:
        c.execute("SELECT COUNT(*) FROM training_episodes;")
        total_episodes = c.fetchone()[0]
        print(f"\n✅ Total de episódios de treinamento: {total_episodes}")
    except Exception as e:
        print(f"\n❌ Erro ao contar episódios: {e}")
        total_episodes = 0

    # Episódios por símbolo
    if total_episodes > 0:
        try:
            c.execute("""
                SELECT symbol, COUNT(*) as count
                FROM training_episodes
                GROUP BY symbol
                ORDER BY count DESC
            """)
            print(f"\n📈 Episódios de treinamento por símbolo:")
            for symbol, count in c.fetchall():
                print(f"  - {symbol}: {count}")
        except Exception as e:
            print(f"❌ Erro: {e}")

        # Rewards capturados
        try:
            c.execute("SELECT COUNT(*) FROM training_episodes WHERE reward IS NOT NULL;")
            episodes_with_reward = c.fetchone()[0]
            print(f"\n💰 Episódios com Reward: {episodes_with_reward} / {total_episodes}")
        except Exception as e:
            print(f"⚠️ Erro ao verificar rewards: {e}")

    # Verificar signal_executions
    try:
        c.execute("SELECT COUNT(*) FROM signal_executions;")
        total_executions = c.fetchone()[0]
        print(f"\n📋 Total de signal_executions: {total_executions}")
    except Exception as e:
        print(f"⚠️ signal_executions não encontrado: {e}")

    # Verificar signal_execution_events
    try:
        c.execute("SELECT COUNT(*) FROM signal_execution_events;")
        total_events = c.fetchone()[0]
        print(f"📋 Total de signal_execution_events: {total_events}")
    except Exception as e:
        print(f"⚠️ signal_execution_events não encontrado: {e}")

    # Verificar model_decisions (decisões do modelo)
    try:
        c.execute("SELECT COUNT(*) FROM model_decisions;")
        total_decisions = c.fetchone()[0]
        print(f"\n🎯 Total de decisões do modelo: {total_decisions}")

        if total_decisions > 0:
            c.execute("""
                SELECT action, COUNT(*) as count
                FROM model_decisions
                GROUP BY action
                ORDER BY count DESC
            """)
            print(f"   Ações por tipo:")
            for action, count in c.fetchall():
                print(f"   - {action}: {count}")
    except Exception as e:
        print(f"⚠️ model_decisions não encontrado: {e}")

    conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Verificação de Captura de Episódios - Ciclo Live")
    print("=" * 60)
    check_episodes()
