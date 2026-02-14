"""
Script de exemplo demonstrando o uso do SDK oficial Binance USDS-M Futures.

Este script mostra como:
1. Criar um cliente usando a factory
2. Coletar dados OHLCV
3. Coletar dados de sentimento
4. Validar os dados coletados
"""

import logging
import sys
from data.binance_client import create_binance_client
from data.collector import BinanceCollector
from data.sentiment_collector import SentimentCollector

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Função principal de exemplo."""
    
    logger.info("=" * 60)
    logger.info("Exemplo de uso do SDK Binance USDS-M Futures")
    logger.info("=" * 60)
    
    # 1. Criar cliente (modo paper/testnet por padrão)
    logger.info("\n1. Criando cliente Binance...")
    try:
        client = create_binance_client(mode="paper")
        logger.info("✓ Cliente criado com sucesso!")
    except Exception as e:
        logger.error(f"✗ Erro ao criar cliente: {e}")
        return 1
    
    # 2. Inicializar collectors
    logger.info("\n2. Inicializando collectors...")
    try:
        collector = BinanceCollector(client)
        sentiment_collector = SentimentCollector(client)
        logger.info("✓ Collectors inicializados!")
    except Exception as e:
        logger.error(f"✗ Erro ao inicializar collectors: {e}")
        return 1
    
    # 3. Exemplo: buscar klines
    logger.info("\n3. Testando coleta de klines...")
    try:
        symbol = "BTCUSDT"
        interval = "1h"
        limit = 10
        
        logger.info(f"   Buscando últimos {limit} candles de {symbol} ({interval})...")
        df = collector.fetch_klines(symbol, interval, limit=limit)
        
        if not df.empty:
            logger.info(f"✓ Coletados {len(df)} candles")
            logger.info(f"   Primeiro timestamp: {df['timestamp'].iloc[0]}")
            logger.info(f"   Último close: ${df['close'].iloc[-1]:,.2f}")
            
            # Validar dados
            is_valid, issues = collector.validate_data(df, interval)
            if is_valid:
                logger.info("✓ Dados validados com sucesso!")
            else:
                logger.warning(f"⚠ Problemas encontrados: {issues}")
        else:
            logger.warning("⚠ Nenhum dado retornado")
    except Exception as e:
        logger.error(f"✗ Erro ao coletar klines: {e}")
        logger.error(f"   Detalhes: {type(e).__name__}")
    
    # 4. Exemplo: buscar dados de sentimento
    logger.info("\n4. Testando coleta de sentimento...")
    try:
        symbol = "BTCUSDT"
        logger.info(f"   Buscando dados de sentimento para {symbol}...")
        
        # Buscar long/short ratio
        ls_data = sentiment_collector.fetch_long_short_ratio(symbol, period="4h")
        if ls_data:
            logger.info(f"✓ Long/Short Ratio: {ls_data.get('long_short_ratio', 'N/A')}")
        
        # Buscar open interest
        oi_data = sentiment_collector.fetch_open_interest(symbol)
        if oi_data:
            logger.info(f"✓ Open Interest: {oi_data.get('open_interest', 'N/A')}")
        
        # Buscar funding rate
        funding_data = sentiment_collector.fetch_funding_rate(symbol)
        if funding_data:
            funding_rate = funding_data.get('funding_rate', 0)
            logger.info(f"✓ Funding Rate: {funding_rate:.6f} ({funding_rate * 100:.4f}%)")
        
    except Exception as e:
        logger.error(f"✗ Erro ao coletar sentimento: {e}")
        logger.error(f"   Detalhes: {type(e).__name__}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Exemplo concluído!")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
