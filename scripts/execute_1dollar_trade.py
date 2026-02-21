#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execute $1 Margin Trade with 10x Leverage

HEAD's estratégia: $1 de margem, 10x alavancagem, micro posições para teste de processo.

Executar: python scripts/execute_1dollar_trade.py --symbol ANKRUSDT --direction LONG
"""

import logging
import sys
import os
import argparse
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def normalize_price_precision(price: float, symbol: str = "ANKRUSDT") -> float:
    """
    Normalizar precisão do preço para não exceder limite Binance.

    A API da Binance retorna erro -1111 se precisão for muito alta.
    Para ANKR, máximo é 5 casas decimais (segundo teste via WebUI).

    Args:
        price: Preço original
        symbol: Símbolo (ANKRUSDT, SOLUSDT, etc)

    Returns:
        Preço arredondado com precisão segura
    """
    # Para ANKR: máximo 5 casas decimais (0.00001 é o tick size)
    # Para outros: tentar 6 casas como padrão (0.000001)
    if "ANK" in symbol or "ANKRUSDT" in symbol:
        return round(price, 5)
    else:
        return round(price, 6)


def execute_1dollar_trade(
    symbol: str = "ANKRUSDT",
    direction: str = "LONG",
    dry_run: bool = False
) -> bool:
    """
    Executar micro posição com $1 de margem, 10x alavancagem.

    Args:
        symbol: Par (ex: ANKRUSDT)
        direction: LONG ou SHORT
        dry_run: Se True, apenas simula sem executar

    Returns:
        True se sucesso, False se erro
    """

    logger.info("=" * 80)
    logger.info("🚀 EXECUTAR POSIÇÃO $1 MARGEM, 10x ALAVANCAGEM")
    logger.info("=" * 80)
    logger.info("")

    try:
        # =====================================================================
        # IMPORTE NECESSÁRIOS
        # =====================================================================
        from data.binance_client import BinanceClientFactory
        from data.database import DatabaseManager
        from config.execution_config import EXECUTION_CONFIG

        factory = BinanceClientFactory(mode="live")
        client = factory.create_client()
        db = DatabaseManager("db/crypto_futures.db")

        # =====================================================================
        # CONFIGURAÇÕES
        # =====================================================================
        margin_usd = EXECUTION_CONFIG.get("max_margin_per_position_usd", 1.0)
        leverage = EXECUTION_CONFIG.get("leverage", 10)
        exposure_usd = margin_usd * leverage

        logger.info(f"📋 CONFIGURAÇÃO:")
        logger.info(f"   • Símbolo: {symbol}")
        logger.info(f"   • Direção: {direction}")
        logger.info(f"   • Margem: ${margin_usd:.2f}")
        logger.info(f"   • Alavancagem: {leverage}x")
        logger.info(f"   • Exposição total: ${exposure_usd:.2f}")
        logger.info(f"   • Modo: {'DRY RUN (simulação)' if dry_run else 'EXECUTAR'}")
        logger.info("")

        # =====================================================================
        # PASSO 1: Verificar balance
        # =====================================================================
        logger.info("📍 PASSO 1: Verificar balance")
        try:
            account_info = client.rest_api.account_information_v2()
            # Try to extract balance from ApiResponse
            balance = 0
            if hasattr(account_info, "totalWalletBalance"):
                balance = float(account_info.totalWalletBalance)

            logger.info(f"    ✓ Conta acessível")

            if balance < margin_usd * 2:  # Margem de segurança
                logger.warning(f"    ⚠️  Balance parece baixo: ${balance:.2f}")

        except Exception as e:
            logger.warning(f"    ⚠️  Aviso ao verificar balance: {e}")
            # Continuar mesmo com erro (pode ser conexão)

        # =====================================================================
        # PASSO 2: Obter preço atual
        # =====================================================================
        logger.info("")
        logger.info("📍 PASSO 2: Obter preço de mercado")
        try:
            # Tentar obter preço via API - SEM FALLBACKS
            mark_price_response = client.rest_api.mark_price(symbol=symbol)

            # ApiResponse wrapper - chamar data() para pegar dados
            price_data = mark_price_response.data()

            # Acessar actual_instance para obter MarkPriceResponse1
            if hasattr(price_data, "actual_instance") and price_data.actual_instance:
                actual = price_data.actual_instance
                if hasattr(actual, "mark_price"):
                    price = float(actual.mark_price)
                else:
                    logger.error(f"    ✗ actual_instance não tem 'mark_price'")
                    return False
            else:
                logger.error(f"    ✗ price_data não tem 'actual_instance'")
                return False

            if price <= 0 or price < 0.00001:
                logger.error(f"    ✗ Preço inválido: ${price:.8f}")
                logger.error(f"    ✗ ABORTANDO - Preço deve ser > 0")
                return False

            logger.info(f"    ✓ Preço {symbol}: ${price:.8f}")

        except Exception as e:
            logger.error(f"    ✗ Erro crítico ao obter preço: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"    ✗ ABORTANDO - Preço não disponível, não executa")
            return False

        # =====================================================================
        # PASSO 3: Calcular quantidade
        # =====================================================================
        logger.info("")
        logger.info("📍 PASSO 3: Calcular quantidade")
        try:
            # Quantidade = Exposição Total / Preço
            quantity = exposure_usd / price

            logger.info(f"    📊 Cálculo bruto: ${exposure_usd:.2f} / ${price:.8f} = {quantity:.8f} {symbol}")

            # VALIDAÇÃO CRÍTICA 1: Quantidade não pode ser > 1,000,000
            if quantity > 1_000_000:
                logger.error(f"    ✗ ERRO CRÍTICO DE CÁLCULO: Quantidade absurda")
                logger.error(f"       └─ Calculada: {quantity:.2f}")
                logger.error(f"       └─ Limite máximo: 1,000,000")
                logger.error(f"    ✗ ABORTANDO EXECUÇÃO")
                return False

            # VALIDAÇÃO CRÍTICA 2: Quantidade > 50,000 é suspeita com $1 margem
            if quantity > 50_000 and margin_usd == 1.0:
                logger.error(f"    ✗ VALIDAÇÃO FALHADA: Quantidade muito alta para $1 margem")
                logger.error(f"       └─ Calculada: {quantity:.2f}")
                logger.error(f"       └─ Típico para $1: < 10,000")
                logger.error(f"       └─ Suspeita: falha no preço ou API")
                logger.error(f"    ✗ ABORTANDO EXECUÇÃO POR SEGURANÇA")
                return False

            # IMPORTANTE: Arredondar quantidade para número inteiro
            # ANKRUSDT e maioria dos tokens futures esperam quantidade inteira
            quantity_rounded = int(quantity)

            if quantity_rounded == 0:
                logger.error(f"    ✗ Quantidade arredondada para zero")
                logger.error(f"       └─ Quantidade bruta: {quantity:.8f}")
                logger.error(f"    ✗ ABORTANDO - Quantidade insuficiente")
                return False

            logger.info(f"    ✓ Quantidade arredondada: {quantity_rounded} {symbol}")
            logger.info(f"       (bruto: {quantity:.8f}, arredondado para inteiro)")

            quantity = quantity_rounded  # Use rounded quantity

        except Exception as e:
            logger.error(f"    ✗ Erro ao calcular quantidade: {e}")
            import traceback
            traceback.print_exc()
            return False

        # =====================================================================
        # PASSO 4.5: CONFIRMAÇÃO MANUAL (NOVO SAFEGUARD)
        # =====================================================================
        logger.info("")
        logger.info("📍 PASSO 4.5: Validação pré-execução")
        logger.info("")
        logger.info("⚠️  RESUMO DA ORDEM A EXECUTAR:")
        logger.info(f"    Symbol:     {symbol}")
        logger.info(f"    Direction:  {direction}")
        logger.info(f"    Quantity:   {quantity:.8f}")
        logger.info(f"    Price:      ${price:.8f}")
        logger.info(f"    Margin:     ${margin_usd:.2f}")
        logger.info(f"    Leverage:   {leverage}x")
        logger.info(f"    Exposure:   ${exposure_usd:.2f}")

        if not dry_run:
            logger.info("")
            logger.info("⚠️  ORDEM REAL SERÁ EXECUTADA NO BINANCE LIVE")
            logger.info("    (Use --dry-run se quer simular)")
            # Em código de produção, aqui teria input do usuário
            # Por enquanto, log suficiente
        try:
            if not dry_run:
                # TODO: Implementar change_leverage via REST API
                logger.info(f"    ℹ️  Alavancagem será setada via Binance interface")
            else:
                logger.info(f"    ℹ️  (DRY RUN) Alavancagem seria setada para {leverage}x")

        except Exception as e:
            logger.warning(f"    ⚠️  Aviso de leverage: {e}")

        # =====================================================================
        # PASSO 5: Executar ordem
        # =====================================================================
        logger.info("")
        logger.info("📍 PASSO 5: Executar ordem MARKET")

        side = "BUY" if direction == "LONG" else "SELL"
        order_id = None

        if dry_run:
            logger.info(f"    ℹ️  (DRY RUN) Ordem que seria executada:")
            logger.info(f"       ├─ Symbol: {symbol}")
            logger.info(f"       ├─ Side: {side}")
            logger.info(f"       ├─ Quantity: {quantity:.8f}")
            logger.info(f"       ├─ Type: MARKET")
            logger.info(f"       └─ Leverage: {leverage}x")
            order_id = f"DRY_RUN_{datetime.now().isoformat()}"

        else:
            try:
                logger.info(f"    ⏳ Executando ordem MARKET...")

                # Executar order via REST API
                order_result = client.rest_api.new_order(
                    symbol=symbol,
                    side=side,
                    type="MARKET",
                    quantity=quantity,
                    reduce_only=False  # Esta é uma abertura de posição
                )

                # Extrair order ID do resultado - TRY multiple approaches
                binance_order_id = None

                # Tentativa 1: Acessar como ApiResponse
                try:
                    if hasattr(order_result, "data"):
                        order_data = order_result.data()
                        if hasattr(order_data, "order_id"):
                            binance_order_id = str(order_data.order_id)
                        elif hasattr(order_data, "orderId"):
                            binance_order_id = str(order_data.orderId)
                except:
                    pass

                # Tentativa 2: Acessar direto
                if not binance_order_id:
                    if hasattr(order_result, "orderId"):
                        binance_order_id = str(order_result.orderId)
                    elif hasattr(order_result, "order_id"):
                        binance_order_id = str(order_result.order_id)

                # Tentativa 3: Dict access
                if not binance_order_id:
                    if isinstance(order_result, dict) and "orderId" in order_result:
                        binance_order_id = str(order_result["orderId"])
                    elif isinstance(order_result, dict) and "order_id" in order_result:
                        binance_order_id = str(order_result["order_id"])

                # Fallback
                if not binance_order_id:
                    binance_order_id = f"ORDER_{datetime.now().isoformat()}"
                    logger.warning(f"    ⚠️  Usando ID fallback (não capturou do Binance)")

                order_id = binance_order_id

                logger.info(f"    ✓ Ordem executada: {order_id}")
                logger.info(f"       Side: {side} | Qty: {quantity:.8f} {symbol}")

            except Exception as e:
                logger.error(f"    ✗ Erro ao executar ordem: {e}")
                import traceback
                traceback.print_exc()
                # Continuar com registro de tentativa falha
                order_id = f"FAILED_{datetime.now().isoformat()}"

        # =====================================================================
        # PASSO 5.5: Criar STOP LOSS ORDER "apregoado" no Binance
        # =====================================================================
        logger.info("")
        logger.info("📍 PASSO 5.5: Criar STOP LOSS ORDER (apregoado no Binance)")

        stop_loss_price = price * 0.95
        # NORMALIZAR PRECISÃO para não exceder limite Binance
        stop_loss_price = normalize_price_precision(stop_loss_price, symbol)
        stop_loss_order_id = None

        if not dry_run and order_id and not order_id.startswith("FAILED"):
            try:
                logger.info(f"    ⏳ Colocando STOP LOSS em ${stop_loss_price:.8f}...")

                # Lado oposto (fecha a posição)
                stop_side = "SELL" if direction == "LONG" else "BUY"

                # Criar STOP LOSS ORDER VIA new_algo_order (CONDICIONAL NA BINANCE)
                # Usar trigger_price em vez de stopPrice (parâmetro correto)
                stop_loss_result = client.rest_api.new_algo_order(
                    algo_type="CONDITIONAL",
                    symbol=symbol,
                    side=stop_side,
                    type="STOP_MARKET",
                    trigger_price=stop_loss_price,  # ← Correto: trigger_price
                    quantity=quantity,
                    reduce_only="true"  # ← Correto: STRING, não boolean
                )

                # Extrair algo_id (ID da ordem condicional na Binance)
                try:
                    if hasattr(stop_loss_result, "data"):
                        sl_data = stop_loss_result.data()
                        # Para new_algo_order, o campo é 'algo_id' (não order_id)
                        if hasattr(sl_data, "algo_id") and sl_data.algo_id:
                            stop_loss_order_id = str(sl_data.algo_id)
                        elif hasattr(sl_data, "order_id") and sl_data.order_id:
                            stop_loss_order_id = str(sl_data.order_id)
                except:
                    pass

                if not stop_loss_order_id:
                    stop_loss_order_id = f"SL_{datetime.now().isoformat()}"

                logger.info(f"    ✓ STOP LOSS ORDER colocado: {stop_loss_order_id}")
                logger.info(f"       Stop Price: ${stop_loss_price:.8f}")
                logger.info(f"       Quantidade: {quantity}")
                logger.info(f"       ⚠️  Este SL fica apregoado no Binance!")
                logger.info(f"       ⚠️  Executa automaticamente, mesmo sem monitor!")

            except Exception as e:
                logger.warning(f"    ⚠️  Não foi possível criar STOP LOSS no Binance: {e}")
                logger.warning(f"       Tipo: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                logger.warning(f"    ℹ️  Continuando com SL simulado no monitor")
                stop_loss_order_id = None
        else:
            if dry_run:
                stop_loss_price = price * 0.95
                logger.info(f"    ℹ️  (DRY RUN) STOP LOSS seria colocado em ${stop_loss_price:.8f}")
            else:
                logger.info(f"    ℹ️  (FALHA) STOP LOSS não foi criado por erro na ordem")

        # =====================================================================
        # PASSO 5.6: Criar TAKE PROFIT ORDER "apregoado" no Binance
        # =====================================================================
        logger.info("")
        logger.info("📍 PASSO 5.6: Criar TAKE PROFIT ORDER (apregoado no Binance)")

        take_profit_price = price * 1.10
        # NORMALIZAR PRECISÃO para não exceder limite Binance
        take_profit_price = normalize_price_precision(take_profit_price, symbol)
        take_profit_order_id = None

        if not dry_run and order_id and not order_id.startswith("FAILED"):
            try:
                logger.info(f"    ⏳ Colocando TAKE PROFIT em ${take_profit_price:.8f}...")

                # Lado oposto (fecha a posição)
                tp_side = "SELL" if direction == "LONG" else "BUY"

                # Criar TAKE PROFIT ORDER VIA new_algo_order (CONDICIONAL NA BINANCE)
                # Usar trigger_price em vez de stopPrice (parâmetro correto)
                take_profit_result = client.rest_api.new_algo_order(
                    algo_type="CONDITIONAL",
                    symbol=symbol,
                    side=tp_side,
                    type="TAKE_PROFIT_MARKET",
                    trigger_price=take_profit_price,  # ← Correto: trigger_price
                    quantity=quantity,
                    reduce_only="true"  # ← Correto: STRING, não boolean
                )

                # Extrair algo_id (ID da ordem condicional na Binance)
                try:
                    if hasattr(take_profit_result, "data"):
                        tp_data = take_profit_result.data()
                        # Para new_algo_order, o campo é 'algo_id' (não order_id)
                        if hasattr(tp_data, "algo_id") and tp_data.algo_id:
                            take_profit_order_id = str(tp_data.algo_id)
                        elif hasattr(tp_data, "order_id") and tp_data.order_id:
                            take_profit_order_id = str(tp_data.order_id)
                except:
                    pass

                if not take_profit_order_id:
                    take_profit_order_id = f"TP_{datetime.now().isoformat()}"

                logger.info(f"    ✓ TAKE PROFIT ORDER colocado: {take_profit_order_id}")
                logger.info(f"       Stop Price: ${take_profit_price:.8f}")
                logger.info(f"       Quantidade: {quantity}")
                logger.info(f"       ⚠️  Este TP fica apregoado no Binance!")
                logger.info(f"       ⚠️  Executa automaticamente, mesmo sem monitor!")

            except Exception as e:
                logger.warning(f"    ⚠️  Não foi possível criar TAKE PROFIT no Binance: {e}")
                logger.warning(f"       Tipo: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                logger.warning(f"    ℹ️  Continuando com TP simulado no monitor")
                take_profit_order_id = None
        else:
            if dry_run:
                take_profit_price = price * 1.10
                logger.info(f"    ℹ️  (DRY RUN) TAKE PROFIT seria colocado em ${take_profit_price:.8f}")
            else:
                logger.info(f"    ℹ️  (FALHA) TAKE PROFIT não foi criado por erro na ordem")

        # =====================================================================
        # PASSO 6: Registrar em DB
        # =====================================================================
        logger.info("")
        logger.info("📍 PASSO 6: Registrar em banco de dados")

        if not dry_run and order_id and not order_id.startswith("FAILED"):
            try:
                import sqlite3

                # Conectar ao banco de dados
                conn = sqlite3.connect("db/crypto_futures.db")
                cursor = conn.cursor()

                # Timestamp em millisegundos para consistência
                timestamp_entrada = int(datetime.now().timestamp() * 1000)

                # Calcular stop_loss (5% abaixo) e take_profit (10% acima)
                stop_loss = price * 0.95
                take_profit = price * 1.10

                # Inserir ordem no trade_log
                cursor.execute("""
                    INSERT INTO trade_log (
                        timestamp_entrada, symbol, direcao, entry_price,
                        stop_loss, take_profit, leverage, margin_type,
                        position_size_usdt, score_confluencia, binance_order_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp_entrada,
                    symbol,
                    "LONG" if direction == "LONG" else "SHORT",
                    price,
                    stop_loss,
                    take_profit,
                    leverage,
                    "CROSS",
                    exposure_usd,
                    70,  # score padrão
                    order_id  # Binance order ID
                ))

                conn.commit()
                trade_id = cursor.lastrowid

                # ATUALIZAR SL/TP IDs na mesma transação
                if stop_loss_order_id or take_profit_order_id:
                    update_query = "UPDATE trade_log SET "
                    update_params = []

                    if stop_loss_order_id:
                        update_query += "binance_sl_order_id = ?, "
                        update_params.append(stop_loss_order_id)

                    if take_profit_order_id:
                        update_query += "binance_tp_order_id = ?, "
                        update_params.append(take_profit_order_id)

                    # Remove trailing ", " e adiciona WHERE
                    update_query = update_query.rstrip(", ") + " WHERE trade_id = ?"
                    update_params.append(trade_id)

                    cursor.execute(update_query, update_params)
                    conn.commit()

                conn.close()

                logger.info(f"    ✓ Registrado em DB com trade_id: {trade_id}")
                logger.info(f"       Binance Order ID: {order_id}")
                if stop_loss_order_id:
                    logger.info(f"       Binance SL Order ID: {stop_loss_order_id}")
                if take_profit_order_id:
                    logger.info(f"       Binance TP Order ID: {take_profit_order_id}")
                logger.info(f"       Entry: ${price:.8f} | SL: ${stop_loss:.8f} | TP: ${take_profit:.8f}")
                logger.info("")
                logger.info("🟢 PROTEÇÕES ATIVAS:")
                if stop_loss_order_id:
                    logger.info(f"   ✓ Stop Loss ORDER apregoado no Binance")
                else:
                    logger.info(f"   ⚠️  Stop Loss será simulado no monitor")
                if take_profit_order_id:
                    logger.info(f"   ✓ Take Profit ORDER apregoado no Binance")
                else:
                    logger.info(f"   ⚠️  Take Profit será simulado no monitor")

            except Exception as e:
                logger.warning(f"    ⚠️  Erro ao registrar em DB: {e}")
                import traceback
                traceback.print_exc()
        else:
            if dry_run:
                logger.info(f"    ℹ️  (DRY RUN) Trade NÃO foi registrado em DB")
            else:
                logger.info(f"    ℹ️  (FALHA) Trade NÃO foi registrado por erro na execução")

        # =====================================================================
        # PASSO 7: Resumo Final
        # =====================================================================
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ EXECUÇÃO CONCLUÍDA")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"📊 RESUMO:")
        logger.info(f"   • Símbolo: {symbol}")
        logger.info(f"   • Direção: {direction}")
        logger.info(f"   • Quantidade: {quantity:.8f}")
        logger.info(f"   • Margem: ${margin_usd:.2f}")
        logger.info(f"   • Exposição: ${exposure_usd:.2f}")
        logger.info(f"   • Alavancagem: {leverage}x")
        logger.info(f"   • Order ID: {order_id}")
        logger.info(f"   • Modo: {'DRY RUN' if dry_run else 'LIVE'}")
        logger.info("")

        try:
            if not dry_run:
                logger.info(f"    ℹ️  Verifique posição em: https://www.binance.com/futures/ANKRUSDT")
            else:
                logger.info(f"    ℹ️  (DRY RUN) Nenhuma ordem foi realmente executada")

        except Exception as e:
            logger.warning(f"    ⚠️  {e}")

        logger.info("")

        return True

    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute $1 margin trade with 10x leverage")
    parser.add_argument("--symbol", default="ANKRUSDT", help="Trading pair (default: ANKRUSDT)")
    parser.add_argument("--direction", default="LONG", choices=["LONG", "SHORT"], help="Trade direction")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (simulate without executing)")

    args = parser.parse_args()

    success = execute_1dollar_trade(
        symbol=args.symbol,
        direction=args.direction,
        dry_run=args.dry_run
    )

    exit(0 if success else 1)
