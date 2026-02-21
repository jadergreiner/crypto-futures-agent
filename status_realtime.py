#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard Operacional - Status em Tempo Real
Mostra posições abertas, sinais ativos e status de monitoramento
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import DB_PATH
from config.symbols import ALL_SYMBOLS
from data.database import DatabaseManager
from data.binance_client import create_binance_client
from monitoring.position_monitor import PositionMonitor


def format_timestamp(ts_ms):
    """Convert milliseconds timestamp to readable format"""
    if not ts_ms:
        return "N/A"
    return datetime.fromtimestamp(ts_ms / 1000).strftime("%H:%M:%S")


def get_realtime_status():
    """Obter status em tempo real"""

    print("\n" + "=" * 100)
    print("STATUS EM TEMPO REAL - AGENTE DE TRADING")
    print("=" * 100)
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        client = create_binance_client()
        db = DatabaseManager(DB_PATH)
        monitor = PositionMonitor(client, db, mode="live")
    except Exception as e:
        print(f"[ERRO] Falha ao conectar: {e}")
        return

    # 1. Posições abertas
    print("=" * 100)
    print("POSIÇÕES ABERTAS NA BINANCE")
    print("=" * 100)

    try:
        positions = monitor.fetch_open_positions(symbol=None, log_each_position=False)

        if positions:
            print(f"\n✅ {len(positions)} posição(ões) aberta(s):\n")

            for pos in positions:
                symbol = pos.get('symbol', 'N/A')
                direction = pos.get('direction', 'N/A')
                qty = pos.get('quantity', 0)
                entry_price = pos.get('entry_price', 0)
                mark_price = pos.get('mark_price', 0)
                pnl = pos.get('unrealized_pnl', 0)
                pnl_pct = pos.get('unrealized_pnl_pct', 0)
                margin = pos.get('margin_invested', 0)

                # Símbolo com cor baseado em PnL
                if pnl_pct >= 5:
                    pnl_indicator = "🟢"  # Muito lucrativo
                elif pnl_pct >= 0:
                    pnl_indicator = "🟡"  # Positivo
                else:
                    pnl_indicator = "🔴"  # Negativo

                print(f"  {pnl_indicator} {symbol:12} {direction:6} | "
                      f"Qty: {qty:12.6f} | "
                      f"Entry: {entry_price:12.8f} | "
                      f"Atual: {mark_price:12.8f} | "
                      f"PnL: {pnl:12.4f} USDT ({pnl_pct:6.2f}%) | "
                      f"Margem: {margin:10.2f} USDT")
        else:
            print("\n❌ Nenhuma posição aberta no momento")
    except Exception as e:
        print(f"[AVISO] Erro ao buscar posições abertas: {e}")

    print()

    # 2. Status de monitoramento
    print("=" * 100)
    print("STATUS DE MONITORAMENTO")
    print("=" * 100)

    try:
        # Buscar últimos snapshots (decisões)
        with db.get_connection() as conn:
            cursor = conn.cursor()

            query = """
            SELECT symbol, agent_action, decision_confidence, risk_score,
                    timestamp, unrealized_pnl_pct
            FROM position_snapshots
            ORDER BY timestamp DESC
            LIMIT 25
            """

            cursor.execute(query)
            snapshots = cursor.fetchall()

        if snapshots:
            print(f"\n✅ Últimas {len(snapshots)} decisões:\n")

            for snap in snapshots:
                symbol = snap[0]
                action = snap[1]
                confidence = snap[2]
                risk_score = snap[3]
                timestamp = snap[4]
                pnl_pct = snap[5]

                # Ícone de ação
                if action == 'HOLD':
                    action_icon = "⏸️ "
                elif action == 'REDUCE_50':
                    action_icon = "📉"
                elif action == 'CLOSE':
                    action_icon = "🔒"
                else:
                    action_icon = "❓"

                # Confiança
                if confidence and confidence >= 0.7:
                    conf_icon = "🟢"
                elif confidence and confidence >= 0.5:
                    conf_icon = "🟡"
                else:
                    conf_icon = "🔴"

                # Risco
                if risk_score and risk_score >= 8:
                    risk_icon = "⚠️ "
                elif risk_score and risk_score >= 5:
                    risk_icon = "⚡"
                else:
                    risk_icon = "✓ "

                time_str = format_timestamp(timestamp)
                conf_val = f"{confidence:.2f}" if confidence else "N/A"
                risk_val = f"{risk_score:.1f}/10" if risk_score else "N/A"
                pnl_val = f"{pnl_pct:.2f}%" if pnl_pct else "N/A"

                print(f"  {time_str} | {action_icon} {symbol:12} {action:10} | "
                      f"Conf: {conf_icon} {conf_val:5} | "
                      f"Risco: {risk_icon} {risk_val:6} | "
                      f"PnL: {pnl_val:>7}")
        else:
            print("\n⏳ Aguardando decisões...")
    except Exception as e:
        print(f"[AVISO] Erro ao buscar snapshots: {e}")

    print()

    # 3. Sinais (H4)
    print("=" * 100)
    print("SINAIS GERADOS (LAYER H4)")
    print("=" * 100)

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()

            query = """
            SELECT symbol, direction, confluence_score, status, timestamp
            FROM trade_signals
            WHERE status IN ('ACTIVE', 'EXECUTING')
            ORDER BY timestamp DESC
            LIMIT 10
            """

            cursor.execute(query)
            signals = cursor.fetchall()

        if signals:
            print(f"\n✅ {len(signals)} sinal(ns) ativo(s):\n")

            for signal in signals:
                symbol = signal[0]
                direction = signal[1]
                confluence = signal[2]
                status = signal[3]
                timestamp = signal[4]

                # Indicador de força do sinal
                if confluence and confluence >= 10:
                    signal_strength = "🟢 FORTE"
                elif confluence and confluence >= 7:
                    signal_strength = "🟡 MÉDIO"
                else:
                    signal_strength = "🔴 FRACO"

                time_str = format_timestamp(timestamp)
                conf_val = f"{confluence:.1f}" if confluence else "N/A"

                print(f"  {time_str} | {symbol:12} {direction:6} | "
                      f"Confluência: {conf_val:5}/14 | {signal_strength:15} | {status}")
        else:
            print("\n⏳ Nenhum sinal ativo no momento")
    except Exception as e:
        print(f"[AVISO] Erro ao buscar sinais: {e}")

    print()

    # 4. Estatísticas gerais
    print("=" * 100)
    print("ESTATÍSTICAS")
    print("=" * 100)

    try:
        # Total de símbolos monitorados
        monitored = len(ALL_SYMBOLS)

        # Snapshots totais
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM position_snapshots")
            total_snapshots = cursor.fetchone()[0]

            # Sinais totais
            cursor.execute("SELECT COUNT(*) FROM trade_signals")
            total_signals = cursor.fetchone()[0]

            # Posições monitoradas (estão nas posições abertas da Binance)
            total_opens = len(positions) if positions else 0

        print()
        print(f"  Símbolos monitorados: {monitored}")
        print(f"  Posições abertas: {total_opens}")
        print(f"  Decisões tomadas: {total_snapshots}")
        print(f"  Sinais gerados: {total_signals}")

    except Exception as e:
        print(f"[AVISO] Erro ao calcular estatísticas: {e}")

    print()
    print("=" * 100)
    print()


if __name__ == "__main__":
    get_realtime_status()
