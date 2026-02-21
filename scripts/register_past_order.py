#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Registrar ordem já executada no Binance
Ordem: No.5412770081 em 2026-02-21 00:24:50
"""

import sqlite3
from datetime import datetime

# Dados da ordem já executada
ORDER_DATA = {
    'timestamp_entrada': int(datetime(2026, 2, 21, 0, 24, 50).timestamp() * 1000),
    'symbol': 'ANKRUSDT',
    'direcao': 'LONG',
    'entry_price': 0.004609,
    'leverage': 10,
    'margin_type': 'CROSS',
    'position_size_usdt': 9.996921,  # valor em USDT
    'score_confluencia': 70,
    'stop_loss': 0.004609 * 0.95,  # 5% de stop
    'take_profit': 0.004609 * 1.10,  # 10% de target
}

try:
    conn = sqlite3.connect("db/crypto_futures.db")
    cursor = conn.cursor()

    print("📋 Registrando ordem já executada no Binance...")
    print(f"   • Order: No.5412770081")
    print(f"   • Symbol: {ORDER_DATA['symbol']}")
    print(f"   • Direção: {ORDER_DATA['direcao']}")
    print(f"   • Preço: ${ORDER_DATA['entry_price']:.8f}")
    print(f"   • Stop Loss: ${ORDER_DATA['stop_loss']:.8f}")
    print(f"   • Take Profit: ${ORDER_DATA['take_profit']:.8f}")
    print(f"   • Valor: ${ORDER_DATA['position_size_usdt']:.2f}")
    print(f"   • Timestamp: {datetime.fromtimestamp(ORDER_DATA['timestamp_entrada']/1000)}")
    print()

    cursor.execute("""
        INSERT INTO trade_log (
            timestamp_entrada, symbol, direcao, entry_price,
            stop_loss, take_profit, leverage, margin_type,
            position_size_usdt, score_confluencia
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ORDER_DATA['timestamp_entrada'],
        ORDER_DATA['symbol'],
        ORDER_DATA['direcao'],
        ORDER_DATA['entry_price'],
        ORDER_DATA['stop_loss'],
        ORDER_DATA['take_profit'],
        ORDER_DATA['leverage'],
        ORDER_DATA['margin_type'],
        ORDER_DATA['position_size_usdt'],
        ORDER_DATA['score_confluencia'],
    ))

    conn.commit()
    trade_id = cursor.lastrowid
    conn.close()

    print(f"✅ Ordem registrada com sucesso!")
    print(f"   Trade ID: {trade_id}")

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
