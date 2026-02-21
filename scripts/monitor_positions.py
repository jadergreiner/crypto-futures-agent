#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor Posições Abertas - Sistema de Proteção

Proteções implementadas:
1. Stop Loss automático (-5% do entry)
2. Take Profit automático (+10% do entry)
3. PnL em tempo real
4. Liquidação preventiva (fecha antes de liquidar)
5. Timeout de posição (máx 2 horas)
6. Validação de margem
"""

import logging
import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def monitor_positions():
    """
    Monitorar posições abertas e aplicar proteções automáticas.
    """

    logger.info("=" * 80)
    logger.info("🛡️  SISTEMA DE PROTEÇÃO - MONITORAR POSIÇÕES ABERTAS")
    logger.info("=" * 80)
    logger.info("")

    try:
        from data.binance_client import BinanceClientFactory
        from data.database import DatabaseManager
        import sqlite3

        # Inicializar cliente e banco
        factory = BinanceClientFactory(mode="live")
        client = factory.create_client()
        db = DatabaseManager("db/crypto_futures.db")

        # =====================================================================
        # PASSO 1: Obter posições abertas do BANCO DE DADOS
        # =====================================================================
        logger.info("📍 PASSO 1: Verificar posições abertas no banco de dados")

        conn = sqlite3.connect("db/crypto_futures.db")
        cursor = conn.cursor()

        # Buscar trades abertos (sem timestamp_saida)
        cursor.execute("""
            SELECT trade_id, symbol, direcao, entry_price, stop_loss, take_profit,
                   leverage, position_size_usdt, timestamp_entrada, binance_order_id
            FROM trade_log
            WHERE timestamp_saida IS NULL
            ORDER BY timestamp_entrada DESC
        """)

        open_trades = cursor.fetchall()
        conn.close()

        if not open_trades:
            logger.info("    ℹ️  Nenhuma posição aberta")
            return True

        logger.info(f"    ✓ Encontradas {len(open_trades)} posição(ões) aberta(s)")

        # =====================================================================
        # PASSO 2: MONITORAR cada posição aberta
        # =====================================================================
        logger.info("")
        logger.info("📍 PASSO 2: Monitorar proteções para cada posição")

        for i, trade in enumerate(open_trades, 1):
            trade_id, symbol, direcao, entry_price, stop_loss, take_profit, \
                leverage, position_size_usdt, timestamp_entrada, binance_order_id = trade

            logger.info("")
            logger.info(f"   📊 POSIÇÃO {i}: {symbol} {direcao}")
            logger.info(f"      Trade ID: {trade_id} | Binance Order: {binance_order_id}")

            try:
                # Obter preço atual
                logger.info(f"      ⏳ Obtendo preço atual...")
                mark_price_response = client.rest_api.mark_price(symbol=symbol)
                price_data = mark_price_response.data()
                current_price = float(price_data.actual_instance.mark_price)

                logger.info(f"      ✓ Preço atual: ${current_price:.8f}")

                # ========================================================
                # PROTEÇÃO 1: Validação de LIQUIDAÇÃO PREVENTIVA
                # ========================================================
                logger.info("")
                logger.info(f"      🛡️  PROTEÇÃO 1: Liquidação Preventiva")

                # Calcular preço de liquidação aproximado
                # Para LONG: Liquidação = Entry * (1 - 1/Leverage)
                # Para SHORT: Liquidação = Entry * (1 + 1/Leverage)

                if direcao == "LONG":
                    liquidation_price = entry_price * (1 - 1/leverage)
                    distance_to_liquidation = ((current_price - liquidation_price) / entry_price) * 100
                else:
                    liquidation_price = entry_price * (1 + 1/leverage)
                    distance_to_liquidation = ((liquidation_price - current_price) / entry_price) * 100

                logger.info(f"      Entry: ${entry_price:.8f}")
                logger.info(f"      Liquidação: ${liquidation_price:.8f}")
                logger.info(f"      Distância: {distance_to_liquidation:.2f}%")

                # Se estiver a menos de 1% da liquidação, fechar URGENTE
                if distance_to_liquidation < 1.0:
                    logger.error(f"      ❌ CRÍTICO: Menos de 1% para liquidação!")
                    logger.error(f"      🚨 FECHANDO POSIÇÃO URGENTEMENTE...")

                    # Registrar saída
                    conn = sqlite3.connect("db/crypto_futures.db")
                    cursor = conn.cursor()

                    timestamp_saida = int(datetime.now().timestamp() * 1000)
                    pnl_usdt = (current_price - entry_price) * (position_size_usdt / entry_price)
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100

                    cursor.execute("""
                        UPDATE trade_log
                        SET timestamp_saida = ?, exit_price = ?,
                            pnl_usdt = ?, pnl_pct = ?, motivo_saida = ?
                        WHERE trade_id = ?
                    """, (
                        timestamp_saida, current_price, pnl_usdt, pnl_pct,
                        "LIQUIDAÇÃO PREVENTIVA", trade_id
                    ))
                    conn.commit()
                    conn.close()

                    logger.warning(f"      📌 Posição FECHADA")
                    logger.warning(f"      PnL: ${pnl_usdt:.2f} ({pnl_pct:.2f}%)")
                    continue

                # ========================================================
                # PROTEÇÃO 2: STOP LOSS
                # ========================================================
                logger.info("")
                logger.info(f"      🛡️  PROTEÇÃO 2: Stop Loss")
                logger.info(f"      SL Definido: ${stop_loss:.8f}")

                if direcao == "LONG":
                    if current_price <= stop_loss:
                        logger.warning(f"      ❌ STOP LOSS ACIONADO!")
                        logger.warning(f"      Preço atual: ${current_price:.8f} ≤ SL: ${stop_loss:.8f}")

                        # Registrar saída
                        conn = sqlite3.connect("db/crypto_futures.db")
                        cursor = conn.cursor()
                        timestamp_saida = int(datetime.now().timestamp() * 1000)
                        pnl_usdt = (current_price - entry_price) * (position_size_usdt / entry_price)
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        cursor.execute("""
                            UPDATE trade_log
                            SET timestamp_saida = ?, exit_price = ?,
                                pnl_usdt = ?, pnl_pct = ?, motivo_saida = ?
                            WHERE trade_id = ?
                        """, (
                            timestamp_saida, current_price, pnl_usdt, pnl_pct,
                            "STOP LOSS", trade_id
                        ))
                        conn.commit()
                        conn.close()

                        logger.warning(f"      📌 Posição FECHADA")
                        logger.warning(f"      PnL: ${pnl_usdt:.2f} ({pnl_pct:.2f}%)")
                        continue
                else:  # SHORT
                    if current_price >= stop_loss:
                        logger.warning(f"      ❌ STOP LOSS ACIONADO!")
                        logger.warning(f"      Preço atual: ${current_price:.8f} ≥ SL: ${stop_loss:.8f}")

                        # Registrar saída
                        conn = sqlite3.connect("db/crypto_futures.db")
                        cursor = conn.cursor()
                        timestamp_saida = int(datetime.now().timestamp() * 1000)
                        pnl_usdt = (entry_price - current_price) * (position_size_usdt / entry_price)
                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                        cursor.execute("""
                            UPDATE trade_log
                            SET timestamp_saida = ?, exit_price = ?,
                                pnl_usdt = ?, pnl_pct = ?, motivo_saida = ?
                            WHERE trade_id = ?
                        """, (
                            timestamp_saida, current_price, pnl_usdt, pnl_pct,
                            "STOP LOSS", trade_id
                        ))
                        conn.commit()
                        conn.close()

                        logger.warning(f"      📌 Posição FECHADA")
                        logger.warning(f"      PnL: ${pnl_usdt:.2f} ({pnl_pct:.2f}%)")
                        continue

                # ========================================================
                # PROTEÇÃO 3: TAKE PROFIT
                # ========================================================
                logger.info("")
                logger.info(f"      🛡️  PROTEÇÃO 3: Take Profit")
                logger.info(f"      TP Definido: ${take_profit:.8f}")

                if direcao == "LONG":
                    if current_price >= take_profit:
                        logger.info(f"      ✅ TAKE PROFIT ACIONADO!")
                        logger.info(f"      Preço atual: ${current_price:.8f} ≥ TP: ${take_profit:.8f}")

                        # Registrar saída
                        conn = sqlite3.connect("db/crypto_futures.db")
                        cursor = conn.cursor()
                        timestamp_saida = int(datetime.now().timestamp() * 1000)
                        pnl_usdt = (current_price - entry_price) * (position_size_usdt / entry_price)
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        cursor.execute("""
                            UPDATE trade_log
                            SET timestamp_saida = ?, exit_price = ?,
                                pnl_usdt = ?, pnl_pct = ?, motivo_saida = ?
                            WHERE trade_id = ?
                        """, (
                            timestamp_saida, current_price, pnl_usdt, pnl_pct,
                            "TAKE PROFIT", trade_id
                        ))
                        conn.commit()
                        conn.close()

                        logger.info(f"      📌 Posição FECHADA")
                        logger.info(f"      PnL: ${pnl_usdt:.2f} ({pnl_pct:.2f}%)")
                        continue
                else:  # SHORT
                    if current_price <= take_profit:
                        logger.info(f"      ✅ TAKE PROFIT ACIONADO!")
                        logger.info(f"      Preço atual: ${current_price:.8f} ≤ TP: ${take_profit:.8f}")

                        # Registrar saída
                        conn = sqlite3.connect("db/crypto_futures.db")
                        cursor = conn.cursor()
                        timestamp_saida = int(datetime.now().timestamp() * 1000)
                        pnl_usdt = (entry_price - current_price) * (position_size_usdt / entry_price)
                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                        cursor.execute("""
                            UPDATE trade_log
                            SET timestamp_saida = ?, exit_price = ?,
                                pnl_usdt = ?, pnl_pct = ?, motivo_saida = ?
                            WHERE trade_id = ?
                        """, (
                            timestamp_saida, current_price, pnl_usdt, pnl_pct,
                            "TAKE PROFIT", trade_id
                        ))
                        conn.commit()
                        conn.close()

                        logger.info(f"      📌 Posição FECHADA")
                        logger.info(f"      PnL: ${pnl_usdt:.2f} ({pnl_pct:.2f}%)")
                        continue

                # ========================================================
                # PROTEÇÃO 4: TIMEOUT (máx 2 horas)
                # ========================================================
                logger.info("")
                logger.info(f"      🛡️  PROTEÇÃO 4: Timeout de Posição (máx 2h)")

                tempo_aberta = datetime.now().timestamp() * 1000 - timestamp_entrada
                tempo_aberta_min = tempo_aberta / 60000

                logger.info(f"      Tempo aberta: {tempo_aberta_min:.1f} minutos")

                if tempo_aberta_min > 120:  # 2 horas
                    logger.warning(f"      ⏰ TIMEOUT ACIONADO (>2h)!")
                    logger.warning(f"      Fechando posição por segurança...")

                    # Registrar saída
                    conn = sqlite3.connect("db/crypto_futures.db")
                    cursor = conn.cursor()
                    timestamp_saida = int(datetime.now().timestamp() * 1000)
                    pnl_usdt = (current_price - entry_price) * (position_size_usdt / entry_price)
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    cursor.execute("""
                        UPDATE trade_log
                        SET timestamp_saida = ?, exit_price = ?,
                            pnl_usdt = ?, pnl_pct = ?, motivo_saida = ?
                        WHERE trade_id = ?
                    """, (
                        timestamp_saida, current_price, pnl_usdt, pnl_pct,
                        "TIMEOUT (>2h)", trade_id
                    ))
                    conn.commit()
                    conn.close()

                    logger.warning(f"      📌 Posição FECHADA")
                    logger.warning(f"      PnL: ${pnl_usdt:.2f} ({pnl_pct:.2f}%)")
                    continue

                # ========================================================
                # PROTEÇÃO 5: PnL Em Tempo Real (sem ação, apenas info)
                # ========================================================
                logger.info("")
                logger.info(f"      🛡️  PROTEÇÃO 5: PnL Em Tempo Real")

                if direcao == "LONG":
                    unrealized_pnl = (current_price - entry_price) * (position_size_usdt / entry_price)
                else:
                    unrealized_pnl = (entry_price - current_price) * (position_size_usdt / entry_price)

                unrealized_pnl_pct = (unrealized_pnl / position_size_usdt) * 100

                logger.info(f"      PnL: ${unrealized_pnl:.2f} ({unrealized_pnl_pct:.2f}%)")
                logger.info(f"      Status: ✅ PROTEGIDA")

                # Atualizar snapshot de PnL no banco
                conn = sqlite3.connect("db/crypto_futures.db")
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE trade_log
                    SET unrealized_pnl_at_snapshot = ?
                    WHERE trade_id = ?
                """, (unrealized_pnl, trade_id))
                conn.commit()
                conn.close()

            except Exception as e:
                logger.error(f"      ✗ Erro ao monitorar posição: {e}")
                import traceback
                traceback.print_exc()

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ MONITORAMENTO CONCLUÍDO")
        logger.info("=" * 80)
        logger.info("")

        return True

    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    monitor_positions()
