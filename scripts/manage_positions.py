#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manage Open Positions - Administrate partial exits and position management

Executar:
  python scripts/manage_positions.py --help
  python scripts/manage_positions.py --list
  python scripts/manage_positions.py --partial --id 7 --pct 50
  python scripts/manage_positions.py --breakeven --id 7
"""

import logging
import sys
import os
import argparse
import sqlite3
from datetime import datetime
from typing import Dict, Optional, List
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class PositionManager:
    """Gerencia posições abertas, parciais e realizações."""

    def __init__(self, db_path: str = "db/crypto_futures.db"):
        """
        Initialize position manager.

        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create trade_partial_exits table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='trade_partial_exits'
        """)

        if cursor.fetchone() is None:
            # Create table
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
            logger.info("✓ Tabela trade_partial_exits criada")

        conn.close()

    def list_open_positions(self) -> List[Dict]:
        """
        List all open positions.

        Returns:
            List of open position dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                trade_id, symbol, direcao, entry_price, stop_loss, take_profit,
                binance_order_id, binance_sl_order_id, binance_tp_order_id,
                timestamp_entrada
            FROM trade_log
            WHERE timestamp_saida IS NULL
            ORDER BY trade_id DESC
        """)

        positions = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return positions

    def get_position(self, trade_id: int) -> Optional[Dict]:
        """Get details of a specific position."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                trade_id, symbol, direcao, entry_price, stop_loss, take_profit,
                position_size_usdt, leverage, binance_order_id,
                binance_sl_order_id, binance_tp_order_id, timestamp_entrada
            FROM trade_log
            WHERE trade_id = ?
        """, (trade_id,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def close_partial(
        self,
        trade_id: int,
        percentage: float,
        reason: str = "MANUAL"
    ) -> bool:
        """
        Close a partial position.

        Args:
            trade_id: Trade ID to close
            percentage: Percentage to close (0.5 = 50%)
            reason: Reason for closing (MANUAL, TP_TRIGGER, etc)

        Returns:
            True if successful, False otherwise
        """
        position = self.get_position(trade_id)

        if not position:
            logger.error(f"✗ Trade ID {trade_id} não encontrado")
            return False

        if position['timestamp_saida'] is not None:
            logger.error(f"✗ Trade ID {trade_id} já foi fechado")
            return False

        # Calculate quantities
        position_size = position['position_size_usdt'] / position['entry_price']
        quantity_to_close = position_size * percentage
        quantity_remaining = position_size * (1 - percentage)

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"🔄 FECHAR PARCIAL - Trade ID: {trade_id}")
        logger.info("=" * 80)
        logger.info("")

        logger.info(f"Posição atual: {position['symbol']} {position['direcao']}")
        logger.info(f"Quantidade atual: {position_size:.8f}")
        logger.info(f"Percentual a fechar: {percentage*100:.0f}%")
        logger.info(f"Quantidade a fechar: {quantity_to_close:.8f}")
        logger.info(f"Quantidade que fica: {quantity_remaining:.8f}")
        logger.info(f"Razão: {reason}")
        logger.info("")

        logger.info("⚠️  PASSO 1: Cancelar SL/TP antigas")
        if position['binance_sl_order_id']:
            logger.info(f"  └─ SL (Algo ID: {position['binance_sl_order_id']})")
            logger.info(f"     ℹ️  (simulado) Cancelar ordem")
        if position['binance_tp_order_id']:
            logger.info(f"  └─ TP (Algo ID: {position['binance_tp_order_id']})")
            logger.info(f"     ℹ️  (simulado) Cancelar ordem")

        logger.info("")
        logger.info("⚠️  PASSO 2: VENDER quantidade parcial")
        current_price = position['entry_price'] * 1.05  # Simulado: +5%
        logger.info(f"  ├─ Símbolo: {position['symbol']}")
        logger.info(f"  ├─ Stack: SELL")
        logger.info(f"  ├─ Quantidade: {quantity_to_close:.8f}")
        logger.info(f"  ├─ Preço (simulado): ${current_price:.8f}")
        logger.info(f"  └─ Type: MARKET (ordem real na Binance)")
        logger.info(f"     ✓ (simulado) Ordem executada")

        logger.info("")
        logger.info("⚠️  PASSO 3: Recrear SL/TP com quantidade reduzida")
        new_sl = position['entry_price'] * 0.95
        new_tp = position['entry_price'] * 1.10
        logger.info(f"  ├─ SL novo: ${new_sl:.8f} (com {quantity_remaining:.8f})")
        logger.info(f"  └─ TP novo: ${new_tp:.8f} (com {quantity_remaining:.8f})")
        logger.info(f"     ✓ (simulado) Ordens criadas")

        logger.info("")
        logger.info("⚠️  PASSO 4: Registrar em BD")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get current partial number
            cursor.execute(
                "SELECT COUNT(*) FROM trade_partial_exits WHERE trade_id = ?",
                (trade_id,)
            )
            partial_number = cursor.fetchone()[0] + 1

            # Insert partial exit record
            cursor.execute("""
                INSERT INTO trade_partial_exits (
                    trade_id, partial_number, quantity_closed, quantity_remaining,
                    exit_price, exit_time, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                partial_number,
                quantity_to_close,
                quantity_remaining,
                current_price,
                int(datetime.now().timestamp() * 1000),
                reason
            ))

            conn.commit()
            conn.close()

            logger.info(f"  ✓ Parcial {partial_number} registrado em trade_partial_exits")

        except Exception as e:
            logger.error(f"  ✗ Erro ao registrar: {e}")
            return False

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ PARCIAL EXECUTADO COM SUCESSO")
        logger.info("=" * 80)
        logger.info("")

        return True

    def breakeven_sl(self, trade_id: int) -> bool:
        """
        Move SL to breakeven (entry price).

        Args:
            trade_id: Trade ID

        Returns:
            True if successful
        """
        position = self.get_position(trade_id)

        if not position:
            logger.error(f"✗ Trade ID {trade_id} não encontrado")
            return False

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"🔄 MOVER SL PARA BREAKEVEN - Trade ID: {trade_id}")
        logger.info("=" * 80)
        logger.info("")

        logger.info(f"SL antigo: ${position['stop_loss']:.8f}")
        logger.info(f"SL novo (breakeven): ${position['entry_price']:.8f}")
        logger.info(f"Ganho protegido: +{(position['entry_price'] - position['stop_loss']) * 100:.2f}%")
        logger.info("")

        logger.info("Ações:")
        logger.info(f"  1. Cancelar SL antigo (Algo ID: {position['binance_sl_order_id']})")
        logger.info(f"  2. Criar novo SL @ ${position['entry_price']:.8f}")
        logger.info("")
        logger.info("✓ (simulado) SL movido para breakeven")

        return True

    def close_all(self, trade_id: int) -> bool:
        """
        Close entire position.

        Args:
            trade_id: Trade ID

        Returns:
            True if successful
        """
        position = self.get_position(trade_id)

        if not position:
            logger.error(f"✗ Trade ID {trade_id} não encontrado")
            return False

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"❌ FECHAR POSIÇÃO INTEIRA - Trade ID: {trade_id}")
        logger.info("=" * 80)
        logger.info("")

        logger.info(f"Símbolo: {position['symbol']} {position['direcao']}")
        logger.info(f"Entry: ${position['entry_price']:.8f}")
        logger.info(f"Quantidade: (calculada no BD)")
        logger.info("")

        logger.info("Ações:")
        logger.info(f"  1. Cancelar SL (Algo ID: {position['binance_sl_order_id']})")
        logger.info(f"  2. Cancelar TP (Algo ID: {position['binance_tp_order_id']})")
        logger.info(f"  3. Executar SELL na posição inteira")
        logger.info(f"  4. Registrar saída em trade_log")
        logger.info("")
        logger.info("✓ (simulado) Posição fechada")

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Gerenciar posições abertas"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Comando")

    # List command
    subparsers.add_parser("--list", help="Listar posições abertas")

    # Partial command
    partial_parser = subparsers.add_parser("--partial", help="Fechar parcial")
    partial_parser.add_argument("--id", type=int, required=True, help="Trade ID")
    partial_parser.add_argument("--pct", type=float, default=0.5, help="Percentual (0.5 = 50%)")
    partial_parser.add_argument("--reason", default="MANUAL", help="Razão do fechamento")

    # Breakeven command
    be_parser = subparsers.add_parser("--breakeven", help="Mover SL para breakeven")
    be_parser.add_argument("--id", type=int, required=True, help="Trade ID")

    # Close all command
    close_parser = subparsers.add_parser("--close-all", help="Fechar posição inteira")
    close_parser.add_argument("--id", type=int, required=True, help="Trade ID")

    args = parser.parse_args()

    manager = PositionManager()

    if args.command == "--list":
        positions = manager.list_open_positions()

        if not positions:
            logger.info("\n✓ Nenhuma posição aberta no momento\n")
        else:
            logger.info("")
            logger.info("=" * 80)
            logger.info("POSIÇÕES ABERTAS")
            logger.info("=" * 80)
            logger.info("")

            for pos in positions:
                logger.info(f"📊 Trade ID: {pos['trade_id']} | {pos['symbol']} {pos['direcao']}")
                logger.info(f"   Entry: ${pos['entry_price']:.8f}")
                logger.info(f"   SL: ${pos['stop_loss']:.8f}")
                logger.info(f"   TP: ${pos['take_profit']:.8f}")
                logger.info(f"   Status: ABERTA")
                logger.info("")

    elif args.command == "--partial":
        manager.close_partial(args.id, args.pct, args.reason)

    elif args.command == "--breakeven":
        manager.breakeven_sl(args.id)

    elif args.command == "--close-all":
        manager.close_all(args.id)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
