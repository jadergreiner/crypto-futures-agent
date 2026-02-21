#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sincronizar com Binance - Verificar Status de SL/TP Orders
Verificar se as proteções no Binance foram acionadas e registrar no banco local
"""

import logging
import sys
import os
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def sync_with_binance():
    """
    Sincronizar ordens com Binance.
    Verificar se SL ou TP foram acionados.
    """

    logger.info("=" * 80)
    logger.info("🔄 SINCRONIZAR COM BINANCE - Verificar Status SL/TP")
    logger.info("=" * 80)
    logger.info("")

    try:
        from data.binance_client import BinanceClientFactory

        factory = BinanceClientFactory(mode="live")
        client = factory.create_client()

        # Conectar ao banco de dados
        conn = sqlite3.connect("db/crypto_futures.db")
        cursor = conn.cursor()

        # =====================================================================
        # PASSO 1: Buscar posições abertas no banco
        # =====================================================================
        logger.info("📍 PASSO 1: Buscar posições abertas")

        cursor.execute("""
            SELECT trade_id, symbol, direcao, entry_price,
                   binance_order_id, binance_sl_order_id, binance_tp_order_id
            FROM trade_log
            WHERE timestamp_saida IS NULL
        """)

        open_trades = cursor.fetchall()

        if not open_trades:
            logger.info("   ℹ️  Nenhuma posição aberta")
            return True

        logger.info(f"   ✓ Encontradas {len(open_trades)} posição(ões) aberta(s)")

        # =====================================================================
        # PASSO 2: Verificar cada ordem no Binance
        # =====================================================================
        logger.info("")
        logger.info("📍 PASSO 2: Verificar ordens no Binance")

        for trade_id, symbol, direcao, entry_price, order_id, sl_order_id, tp_order_id in open_trades:
            logger.info("")
            logger.info(f"   📊 Trade ID {trade_id}: {symbol} {direcao}")

            try:
                # Buscar todas as ordens abertas para este símbolo
                open_orders_response = client.rest_api.current_all_open_orders(symbol=symbol)

                if hasattr(open_orders_response, "data"):
                    orders_data = open_orders_response.data()
                else:
                    orders_data = open_orders_response

                # Verificar SL
                if sl_order_id:
                    logger.info(f"      STOP LOSS Order {sl_order_id}:")
                    sl_found = False

                    if isinstance(orders_data, list):
                        for order in orders_data:
                            order_id_value = None
                            if hasattr(order, "order_id"):
                                order_id_value = str(order.order_id)
                            elif hasattr(order, "orderId"):
                                order_id_value = str(order.orderId)

                            if order_id_value and str(order_id_value) == str(sl_order_id):
                                sl_found = True
                                logger.info(f"         Status: ABERTA ✅")
                                break

                    if not sl_found:
                        logger.info(f"         Status: EXECUTADO/CANCELADO ⚠️ (não em open orders)")
                else:
                    logger.info(f"      STOP LOSS: Não foi criado no Binance")

                # Verificar TP
                if tp_order_id:
                    logger.info(f"      TAKE PROFIT Order {tp_order_id}:")
                    tp_found = False

                    if isinstance(orders_data, list):
                        for order in orders_data:
                            order_id_value = None
                            if hasattr(order, "order_id"):
                                order_id_value = str(order.order_id)
                            elif hasattr(order, "orderId"):
                                order_id_value = str(order.orderId)

                            if order_id_value and str(order_id_value) == str(tp_order_id):
                                tp_found = True
                                logger.info(f"         Status: ABERTA ✅")
                                break

                    if not tp_found:
                        logger.info(f"         Status: EXECUTADO/CANCELADO ⚠️ (não em open orders)")
                else:
                    logger.info(f"      TAKE PROFIT: Não foi criado no Binance")

                # Obter posição atual
                logger.info(f"      Posição no Binance:")
                pos_response = client.rest_api.position_information_v2(symbol=symbol)

                if hasattr(pos_response, "data"):
                    pos_data = pos_response.data()
                    if isinstance(pos_data, list) and len(pos_data) > 0:
                        pos = pos_data[0]
                    else:
                        pos = pos_data
                else:
                    pos = pos_response

                if hasattr(pos, "position_amt"):
                    qty = float(pos.position_amt)
                    if qty == 0:
                        logger.warning(f"         ⚠️  Position qty = 0 (foi fechada!)")
                    else:
                        logger.info(f"         ✓ Qty aberta: {qty}")

            except Exception as e:
                logger.warning(f"      ⚠️  Erro ao verificar: {e}")

        conn.close()
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ SINCRONIZAÇÃO CONCLUÍDA")
        logger.info("=" * 80)
        logger.info("")

        return True

    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sync_with_binance()
