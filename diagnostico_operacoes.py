#!/usr/bin/env python3
"""
Diagnóstico de por que o agente não está gerando operações.
"""

import sqlite3
from pathlib import Path
from data.database import DatabaseManager
from config.settings import DB_PATH

print("=" * 90)
print("🔍 DIAGNÓSTICO: Por que o agente não gera operações?")
print("=" * 90)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. Trades
print("\n📊 1. TRADE LOG (Operações)")
print("-" * 90)
cursor.execute('SELECT COUNT(*) FROM trade_log WHERE timestamp_saida IS NOT NULL')
trades_fechados = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM trade_log WHERE timestamp_saida IS NULL')
trades_abertos = cursor.fetchone()[0]
print(f"  • Trades fechados: {trades_fechados}")
print(f"  • Trades abertos: {trades_abertos}")
print(f"  • TOTAL: {trades_fechados + trades_abertos}")

# 2. Sinais de trade
print("\n📈 2. TRADE SIGNALS (Sinais Identificados)")
print("-" * 90)
cursor.execute('SELECT COUNT(*) FROM trade_signals')
total_sinais = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM trade_signals WHERE status = "ACTIVE"')
sinais_ativos = cursor.fetchone()[0]
print(f"  • Total de sinais: {total_sinais}")
print(f"  • Sinais ativos: {sinais_ativos}")

# Distribuição de status
try:
    cursor.execute('SELECT status, COUNT(*) FROM trade_signals GROUP BY status')
    status_dist = cursor.fetchall()
    if status_dist:
        print(f"  • Distribuição por status:")
        for status, count in status_dist:
            print(f"      - {status}: {count}")
except:
    pass

# 3. Execuções
print("\n⚡ 3. EXECUTION LOG (Tentativas de Execução)")
print("-" * 90)
cursor.execute('SELECT COUNT(*) FROM execution_log')
total_exec = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM execution_log WHERE executed = 1')
exec_ok = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM execution_log WHERE executed = 0')
exec_falha = cursor.fetchone()[0]
print(f"  • Total de tentativas: {total_exec}")
print(f"  • Executadas com sucesso: {exec_ok}")
print(f"  • Falhadas: {exec_falha}")

# 4. Position Snapshots
print("\n📷 4. POSITION SNAPSHOTS (Snapshots de Posições)")
print("-" * 90)
cursor.execute('SELECT COUNT(*) FROM position_snapshots')
snapshots = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(DISTINCT symbol) FROM position_snapshots')
pares_monitorados = cursor.fetchone()[0]
print(f"  • Total de snapshots: {snapshots}")
print(f"  • Pares monitorados: {pares_monitorados}")

# 5. Últimas operações (se houver)
print("\n🕐 5. OPERAÇÕES MAIS RECENTES")
print("-" * 90)
cursor.execute('''
    SELECT symbol, direcao, entry_price, exit_price, pnl_usdt,
           datetime(timestamp_entrada/1000, 'unixepoch') as entrada
    FROM trade_log
    ORDER BY timestamp_entrada DESC
    LIMIT 5
''')
operacoes_recentes = cursor.fetchall()
if operacoes_recentes:
    for op in operacoes_recentes:
        print(f"  • {op[0]}: {op[1]} @ {op[2]:.2f} → {op[3] or 'ABERTO'} | PnL: {op[4] or 'N/A'} | {op[5]}")
else:
    print("  ❌ Nenhuma operação registrada!")

# 6. Erros e avisos recentes
print("\n⚠️  6. EVENTOS RECENTES NOS LOGS")
print("-" * 90)
import glob
from datetime import datetime, timedelta

cutoff = (datetime.now() - timedelta(hours=24)).timestamp()
log_files = glob.glob("logs/*.log")

erros_total = 0
avisos_total = 0
erros_unicos = {}

for log_file in log_files:
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'ERROR' in line or 'error' in line:
                    erros_total += 1
                    # Capturar tipo de erro
                    if 'reward' in line.lower():
                        erros_unicos['Reward'] = erros_unicos.get('Reward', 0) + 1
                    elif 'execution' in line.lower():
                        erros_unicos['Execution'] = erros_unicos.get('Execution', 0) + 1
                    elif 'signal' in line.lower():
                        erros_unicos['Signal'] = erros_unicos.get('Signal', 0) + 1

                if 'WARNING' in line or 'warning' in line:
                    avisos_total += 1
    except:
        pass

if erros_total > 0:
    print(f"  • Erros detectados: {erros_total}")
    for tipo, count in erros_unicos.items():
        print(f"      - {tipo}: {count}")
else:
    print("  • Nenhum erro crítico detectado nos logs (24h)")

if avisos_total > 0:
    print(f"  • Avisos: {avisos_total}")

# 7. Configuração do agente
print("\n⚙️  7. CONFIGURAÇÃO DO AGENTE")
print("-" * 90)
from config.execution_config import AUTHORIZED_SYMBOLS
from config.execution_config import EXECUTION_CONFIG

print(f"  • Símbolos autorizados: {len(AUTHORIZED_SYMBOLS)}")
print(f"    {AUTHORIZED_SYMBOLS}")
print(f"  • Modo de trading: {EXECUTION_CONFIG.get('MODE', 'N/A')}")
print(f"  • Máximo de posições: {EXECUTION_CONFIG.get('MAX_CONCURRENT_POSITIONS', 'N/A')}")
print(f"  • MIN_ENTRY_SCORE: {EXECUTION_CONFIG.get('MIN_ENTRY_SCORE', 'N/A')}")
print(f"  • Risco por trade: {EXECUTION_CONFIG.get('RISK_PCT_PER_TRADE', 'N/A')}%")

conn.close()

# 8. Diagnóstico final
print("\n" + "=" * 90)
print("🔎 DIAGNÓSTICO FINAL")
print("=" * 90)

if trades_fechados + trades_abertos == 0:
    print("❌ PROBLEMA IDENTIFICADO: Nenhuma operação foi executada!")
    print("\nPossíveis causas:")
    print("  1️⃣  MIN_ENTRY_SCORE muito alto (sem confluência atingir threshold)")
    print("  2️⃣  Modo 'Profit Guardian' ativo (apenas gerencia posições abertas)")
    print("  3️⃣  Nenhum sinal com score suficiente foi gerado")
    print("  4️⃣  Símbolos autorizados muito restritos")
    print("  5️⃣  Agente em modo PAPER sem executar efetivamente")
    print("\n✅ SOLUÇÃO:")
    print("  → Reduzir MIN_ENTRY_SCORE para 3.5-4.0 (teste)")
    print("  → Liberar mais símbolos em AUTHORIZED_SYMBOLS")
    print("  → Executar em modo LIVE (controlado) para testes reais")
    print("  → Revisar logs para identificar por que sinais não atingem threshold")
else:
    print(f"✅ Sistema operacional: {trades_fechados + trades_abertos} operações registradas")

print("\n" + "=" * 90)
