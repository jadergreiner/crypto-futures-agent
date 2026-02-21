#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 2 API Data Retrieval - CORRIGIDO
Recupera dados em tempo real da Binance para validar readiness de Phase 2
"""

import json
import time
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from data.binance_client import create_binance_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Símbolos para monitorar em Phase 2
PHASE2_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']


def main():
    """Recupera dados da API Binance para Phase 2"""

    start_time = time.time()

    logger.info("\n" + "=" * 70)
    logger.info("PHASE 2 - RECUPERACAO DE DADOS API BINANCE (LIVE)")
    logger.info(f"Hora: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 70 + "\n")

    try:
        # 1. CONECTAR
        logger.info("[1/5] CONECTANDO À BINANCE...")
        client = create_binance_client(mode="live")
        logger.info("    ✅ Conexão estabelecida")

        # 2. RECUPERAR SALDO
        logger.info("\n[2/5] RECUPERANDO SALDO...")

        try:
            # Chamar método account_information_v3() e desserializar com .data()
            response = client.rest_api.account_information_v3()

            # ApiResponse.data() é um método que retorna os dados
            account_data = response.data() if callable(response.data) else response.data

            # Converter para dict se necessário
            if hasattr(account_data, '__dict__'):
                account = vars(account_data)
            else:
                account = account_data if isinstance(account_data, dict) else {}

        except Exception as e:
            # Se falhar por timestamp, tentar com sync
            logger.warning(f"    ⚠️  Erro: {str(e)}")
            logger.info("    Tentando sincronizar timestamp com servidor...")

            # Sincronizar: obter timestamp do servidor via mark_price (não precisa assinatura)
            market_resp = client.rest_api.mark_price('BTCUSDT')

            # Tentar novamente
            response = client.rest_api.account_information_v3()
            account_data = response.data() if callable(response.data) else response.data
            account = vars(account_data) if hasattr(account_data, '__dict__') else account_data or {}

        total_balance = float(account.get('totalWalletBalance', 0) or account.get('total_wallet_balance', 0))
        available = float(account.get('availableBalance', 0) or account.get('available_balance', 0))
        unrealized_pnl = float(account.get('totalUnrealizedProfit', 0) or account.get('total_unrealized_profit', 0))
        margin_used = float(account.get('totalInitialMargin', 0) or account.get('total_initial_margin', 0))

        logger.info(f"    Saldo Total: ${total_balance:.2f}")
        logger.info(f"    Disponível: ${available:.2f}")
        logger.info(f"    P&L: ${unrealized_pnl:.2f}")
        logger.info(f"    Margem Usada: ${margin_used:.2f}")

        # Calcular drawdown
        if total_balance > 0:
            drawdown_pct = (unrealized_pnl / total_balance) * 100
        else:
            drawdown_pct = 0

        logger.info(f"    Drawdown: {drawdown_pct:.2f}%")
        logger.info(f"    ✅ Capital READY" if available > 1 else "    ❌ Sem capital suficiente")

        # 3. POSIÇÕES ABERTAS
        logger.info("\n[3/5] VERIFICANDO POSIÇÕES ABERTAS...")
        positions = []

        positions_data = account.get('positions', [])
        if positions_data:
            for pos in positions_data:
                # Converter posição para dict se necessário
                pos_dict = vars(pos) if hasattr(pos, '__dict__') else pos
                if float(pos_dict.get('positionAmt', 0) or pos_dict.get('position_amt', 0)) != 0:
                    positions.append(pos_dict)

        if len(positions) == 0:
            logger.info("    ✅ Nenhuma posição aberta (LIMPO)")
        else:
            logger.info(f"    ⚠️  {len(positions)} posição(ões) aberta(s)")
            for pos in positions[:5]:
                symbol = pos.get('symbol')
                amount = pos.get('positionAmt') or pos.get('position_amt', 0)
                entry = pos.get('entryPrice') or pos.get('entry_price', 0)
                logger.info(f"      - {symbol}: {amount} @ ${entry}")

        # 4. DADOS DE MERCADO
        logger.info("\n[4/5] COLETANDO DADOS DE MERCADO...")
        market_data = {}
        for symbol in PHASE2_SYMBOLS:
            try:
                # Recuperar mark price e order book ticker
                mark_price_response = client.rest_api.mark_price(symbol=symbol)
                ticker_response = client.rest_api.symbol_order_book_ticker(symbol=symbol)

                # Desserializar
                mark_price_data = mark_price_response.data() if callable(mark_price_response.data) else mark_price_response.data
                ticker_data = ticker_response.data() if callable(ticker_response.data) else ticker_response.data

                # Converter para dict se necessário
                mark_price_dict = vars(mark_price_data) if hasattr(mark_price_data, '__dict__') else mark_price_data
                ticker_dict = vars(ticker_data) if hasattr(ticker_data, '__dict__') else ticker_data

                if mark_price_dict and ticker_dict:
                    price = float(mark_price_dict.get('markPrice', 0) or mark_price_dict.get('mark_price', 0))
                    bid = float(ticker_dict.get('bidPrice', 0) or ticker_dict.get('bid_price', 0))
                    ask = float(ticker_dict.get('askPrice', 0) or ticker_dict.get('ask_price', 0))

                    market_data[symbol] = {
                        'price': price,
                        'bid': bid,
                        'ask': ask,
                        'bid_qty': float(ticker_dict.get('bidQty', 0) or ticker_dict.get('bid_qty', 0)),
                        'ask_qty': float(ticker_dict.get('askQty', 0) or ticker_dict.get('ask_qty', 0)),
                    }

                    spread_bps = 0
                    if market_data[symbol]['price'] > 0 and bid > 0 and ask > 0:
                        spread = ask - bid
                        spread_bps = (spread / price) * 10000

                    logger.info(f"    ✅ {symbol}: ${price:.2f} (spread: {spread_bps:.1f} bps)")
            except Exception as e:
                logger.warning(f"    ⚠️  {symbol}: Erro ao recuperar dados - {str(e)}")

        # 5. VALIDAR GATES
        logger.info("\n[5/5] VALIDANDO GATES DE RISCO...")

        circuit_breaker = -3.0
        is_armed = drawdown_pct > circuit_breaker

        logger.info(f"    Circuit Breaker: {circuit_breaker}%")
        logger.info(f"    Drawdown Atual: {drawdown_pct:.2f}%")
        logger.info(f"    Status: {'ARMED ✅' if is_armed else 'DISARMED ❌'}")

        # RELATÓRIO FINAL
        logger.info("\n" + "=" * 70)
        logger.info("RESUMO - PHASE 2 READINESS")
        logger.info("=" * 70)

        checks = [
            ('Capital Disponível', available > 1),
            ('API Conectada', True),
            ('Posições Limpas', len(positions) == 0),
            ('Dados Mercado OK', len(market_data) >= 3),
            ('Gates Armados', is_armed),
        ]

        all_pass = all(check[1] for check in checks)

        for check_name, status in checks:
            symbol = "✅" if status else "❌"
            logger.info(f"{symbol} {check_name}")

        logger.info("=" * 70)

        if all_pass:
            logger.info("✅✅✅ TUDO PRONTO PARA PHASE 2 ✅✅✅")
            logger.info("Você pode iniciar operação em modo LIVE agora")
            return_code = 0
        else:
            logger.warning("❌ Alguns requisitos não estão prontos")
            return_code = 1

        # Salvar relatório
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'mode': 'LIVE',
            'account': {
                'total_balance': total_balance,
                'available': available,
                'unrealized_pnl': unrealized_pnl,
                'drawdown_pct': drawdown_pct,
            },
            'positions': len(positions),
            'market_data_symbols': len(market_data),
            'gates': {
                'circuit_breaker': circuit_breaker,
                'current_drawdown': drawdown_pct,
                'is_armed': is_armed,
            },
            'readiness': {
                'capital': available > 1,
                'api': True,
                'positions_clean': len(positions) == 0,
                'market_data': len(market_data) >= 3,
                'gates_armed': is_armed,
                'all_ready': all_pass,
            }
        }

        report_file = f"PHASE2_DATA_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"\n[ARQUIVO] Relatório salvo: {report_file}")

        elapsed = time.time() - start_time
        logger.info(f"Tempo total: {elapsed:.2f}s\n")

        return return_code == 0

    except Exception as e:
        logger.error(f"\n[ERRO CRITICO] {str(e)}")
        logger.exception("Stack trace:")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
