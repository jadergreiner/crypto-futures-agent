#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema Update - Create trade_partial_exits table if not exists

Executar:
  python schema_update.py
"""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def ensure_partial_exits_table(db_path: str = "db/crypto_futures.db"):
    """Create trade_partial_exits table if not exists."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='trade_partial_exits'
    """)

    if cursor.fetchone() is not None:
        logger.info("✓ Tabela trade_partial_exits já existe")
        conn.close()
        return

    # Create table
    logger.info("📋 Criando tabela trade_partial_exits...")

    cursor.execute("""
        CREATE TABLE trade_partial_exits (
            partial_id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id INTEGER NOT NULL,
            partial_number INTEGER,
            quantity_closed REAL,
            quantity_remaining REAL,
            exit_price REAL,
            exit_time INTEGER,
            binance_order_id_close TEXT,
            binance_sl_order_id_new TEXT,
            binance_tp_order_id_new TEXT,
            reason TEXT,
            FOREIGN KEY (trade_id) REFERENCES trade_log(trade_id)
        )
    """)

    conn.commit()
    conn.close()

    logger.info("✓ Tabela trade_partial_exits criada com sucesso")
    logger.info("")
    logger.info("Campos:")
    logger.info("  • partial_id: ID único de cada parcial")
    logger.info("  • trade_id: Referência ao trade_log")
    logger.info("  • partial_number: Ordem do fechamento (1, 2, 3, ...)")
    logger.info("  • quantity_closed: Quantidade vendida nesta parcial")
    logger.info("  • quantity_remaining: Quantidade que ficou aberta")
    logger.info("  • exit_price: Preço de saída da parcial")
    logger.info("  • exit_time: Timestamp de saída")
    logger.info("  • binance_order_id_close: ID da ordem de fechamento na Binance")
    logger.info("  • binance_sl_order_id_new: Novo SL Algo ID após parcial")
    logger.info("  • binance_tp_order_id_new: Novo TP Algo ID após parcial")
    logger.info("  • reason: Razão do fechamento (MANUAL, TP_TRIGGER, SL, etc)")
    logger.info("")


def main():
    logger.info("=" * 80)
    logger.info("SCHEMA UPDATE - Criar tabela de parciais")
    logger.info("=" * 80)
    logger.info("")

    db_path = "db/crypto_futures.db"

    # Check if DB exists
    if not Path(db_path).exists():
        logger.error(f"✗ Banco de dados não encontrado: {db_path}")
        logger.error("  Execute setup.bat primeiro para criar o banco")
        return

    # Create table
    ensure_partial_exits_table(db_path)

    logger.info("=" * 80)
    logger.info("✅ UPDATE CONCLUÍDO")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
