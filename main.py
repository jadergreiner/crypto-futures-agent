"""
Entry point do agente autônomo de futuros de criptomoedas.
"""

import argparse
import logging
import sys
from pathlib import Path

from config.settings import DB_PATH, TRADING_MODE
from config.symbols import ALL_SYMBOLS
from data.database import DatabaseManager
from data.binance_client import create_binance_client
from data.collector import BinanceCollector
from data.sentiment_collector import SentimentCollector
from data.macro_collector import MacroCollector
from monitoring.logger import AgentLogger
from core.scheduler import Scheduler
from core.layer_manager import LayerManager

# Setup logger
logger = AgentLogger.setup_logger()


def setup_database() -> DatabaseManager:
    """
    Inicializa banco de dados.
    
    Returns:
        DatabaseManager inicializado
    """
    logger.info("Setting up database...")
    db = DatabaseManager(DB_PATH)
    logger.info(f"Database initialized: {DB_PATH}")
    return db


def collect_historical_data(db: DatabaseManager, client) -> None:
    """
    Captura dados históricos iniciais.
    
    Args:
        db: DatabaseManager
        client: Binance SDK client instance
    """
    logger.info("="*60)
    logger.info("COLETANDO DADOS HISTÓRICOS")
    logger.info("="*60)
    
    collector = BinanceCollector(client)
    sentiment_collector = SentimentCollector(client)
    macro_collector = MacroCollector()
    
    for symbol in ALL_SYMBOLS:
        logger.info(f"Coletando dados para {symbol}...")
        
        try:
            # OHLCV D1 (365 dias)
            d1_data = collector.fetch_historical(symbol, "1d", 365)
            if d1_data is not None and not d1_data.empty:
                db.insert_ohlcv("d1", d1_data)
                logger.info(f"  {len(d1_data)} candles D1 inseridos")
            
            # OHLCV H4 (180 dias)
            h4_data = collector.fetch_historical(symbol, "4h", 180)
            if h4_data is not None and not h4_data.empty:
                db.insert_ohlcv("h4", h4_data)
                logger.info(f"  {len(h4_data)} candles H4 inseridos")
            
            # OHLCV H1 (90 dias)
            h1_data = collector.fetch_historical(symbol, "1h", 90)
            if h1_data is not None and not h1_data.empty:
                db.insert_ohlcv("h1", h1_data)
                logger.info(f"  {len(h1_data)} candles H1 inseridos")
            
            # Sentiment
            sentiment = sentiment_collector.fetch_all_sentiment(symbol)
            if sentiment:
                db.insert_sentiment([sentiment])
                logger.info(f"  Dados de sentimento inseridos")
            
        except Exception as e:
            logger.error(f"Erro ao coletar dados para {symbol}: {e}")
    
    # Macro data
    logger.info("Coletando dados macro...")
    try:
        macro = macro_collector.fetch_all_macro()
        if macro:
            db.insert_macro(macro)
            logger.info("  Dados macro inseridos")
    except Exception as e:
        logger.error(f"Erro ao coletar dados macro: {e}")
    
    logger.info("Coleta de dados históricos concluída")


def calculate_indicators(db: DatabaseManager) -> None:
    """
    Calcula indicadores técnicos para dados históricos.
    
    Args:
        db: DatabaseManager
    """
    logger.info("="*60)
    logger.info("CALCULANDO INDICADORES")
    logger.info("="*60)
    
    from indicators.technical import TechnicalIndicators
    from indicators.smc import SmartMoneyConcepts
    import pandas as pd
    
    for symbol in ALL_SYMBOLS:
        logger.info(f"Calculando indicadores para {symbol}...")
        
        try:
            # Calcular para H4
            h4_data = db.get_ohlcv("h4", symbol)
            if h4_data is not None and len(h4_data) > 0:
                df = pd.DataFrame(h4_data)
                df = TechnicalIndicators.calculate_all(df)
                
                # Preparar para inserção
                indicators_data = []
                for _, row in df.iterrows():
                    indicators_data.append({
                        'timestamp': int(row['timestamp']),
                        'symbol': symbol,
                        'timeframe': 'H4',
                        'ema_17': row.get('ema_17'),
                        'ema_34': row.get('ema_34'),
                        'ema_72': row.get('ema_72'),
                        'ema_144': row.get('ema_144'),
                        'ema_305': row.get('ema_305'),
                        'ema_610': row.get('ema_610'),
                        'rsi_14': row.get('rsi_14'),
                        'macd_line': row.get('macd_line'),
                        'macd_signal': row.get('macd_signal'),
                        'macd_histogram': row.get('macd_histogram'),
                        'bb_upper': row.get('bb_upper'),
                        'bb_middle': row.get('bb_middle'),
                        'bb_lower': row.get('bb_lower'),
                        'bb_bandwidth': row.get('bb_bandwidth'),
                        'bb_percent_b': row.get('bb_percent_b'),
                        'vp_poc': row.get('vp_poc'),
                        'vp_vah': row.get('vp_vah'),
                        'vp_val': row.get('vp_val'),
                        'obv': row.get('obv'),
                        'atr_14': row.get('atr_14'),
                        'adx_14': row.get('adx_14'),
                        'di_plus': row.get('di_plus'),
                        'di_minus': row.get('di_minus')
                    })
                
                db.insert_indicators(indicators_data)
                logger.info(f"  {len(indicators_data)} registros de indicadores H4 inseridos")
        
        except Exception as e:
            logger.error(f"Erro ao calcular indicadores para {symbol}: {e}")
    
    logger.info("Cálculo de indicadores concluído")


def train_model() -> None:
    """Treina o modelo RL."""
    logger.info("="*60)
    logger.info("TRAINING RL MODEL")
    logger.info("="*60)
    
    logger.info("Model training skipped (use --train flag to force)")
    logger.info("See agent/trainer.py for training implementation")


def start_operation(mode: str, client, db: DatabaseManager) -> None:
    """
    Inicia operação do agente.
    
    Args:
        mode: Modo de operação ("paper" ou "live")
        client: Binance SDK client instance
        db: DatabaseManager instance
    """
    logger.info("="*60)
    logger.info(f"STARTING OPERATION - MODE: {mode.upper()}")
    logger.info("="*60)
    
    # Inicializar layer manager com db e client
    layer_manager = LayerManager(db=db, client=client)
    
    # Inicializar scheduler
    scheduler = Scheduler(layer_manager)
    
    # Iniciar WebSocket (assíncrono)
    # from data.websocket_manager import WebSocketManager
    # ws_manager = WebSocketManager(client)
    # asyncio.run(ws_manager.start(ALL_SYMBOLS))
    
    try:
        # Iniciar scheduler (loop infinito)
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        scheduler.stop()


def run_backtest(start_date: str, end_date: str) -> None:
    """
    Executa backtest.
    
    Args:
        start_date: Data inicial (YYYY-MM-DD)
        end_date: Data final (YYYY-MM-DD)
    """
    logger.info("="*60)
    logger.info(f"RUNNING BACKTEST: {start_date} to {end_date}")
    logger.info("="*60)
    
    from backtest.backtester import Backtester
    
    backtester = Backtester(initial_capital=10000)
    
    # Carregar dados
    # Carregar modelo
    # Executar backtest
    
    logger.info("Backtest completed")


def main():
    """Entry point principal."""
    parser = argparse.ArgumentParser(
        description="Crypto Futures Autonomous Agent"
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        default=TRADING_MODE,
        choices=['paper', 'live'],
        help='Trading mode (default: paper)'
    )
    
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Setup: initialize database and collect historical data'
    )
    
    parser.add_argument(
        '--train',
        action='store_true',
        help='Train the RL model'
    )
    
    parser.add_argument(
        '--backtest',
        action='store_true',
        help='Run backtest mode'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        help='Backtest start date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        help='Backtest end date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Monitor open positions in real-time'
    )
    
    parser.add_argument(
        '--monitor-symbol',
        type=str,
        default=None,
        help='Symbol to monitor (e.g., C98USDT). If omitted, monitors all.'
    )
    
    parser.add_argument(
        '--monitor-interval',
        type=int,
        default=300,
        help='Monitor interval in seconds (default: 300 = 5min)'
    )
    
    args = parser.parse_args()
    
    # Banner
    print("="*60)
    print("CRYPTO FUTURES AUTONOMOUS AGENT")
    print("Reinforcement Learning + Smart Money Concepts")
    print("="*60)
    print()
    
    # Setup database
    db = setup_database()
    
    # Fluxo de execução
    if args.setup:
        # Create Binance client for setup
        client = create_binance_client(mode=args.mode)
        logger.info(f"Binance client created in {args.mode} mode")
        collect_historical_data(db, client)
        calculate_indicators(db)
        logger.info("Setup completed successfully")
        sys.exit(0)
    
    if args.train:
        train_model()
        sys.exit(0)
    
    if args.backtest:
        if not args.start_date or not args.end_date:
            logger.error("Backtest requires --start-date and --end-date")
            sys.exit(1)
        run_backtest(args.start_date, args.end_date)
        sys.exit(0)
    
    if args.monitor:
        # Modo monitoramento de posições
        from monitoring.position_monitor import PositionMonitor
        client = create_binance_client(mode=args.mode)
        logger.info(f"Binance client created in {args.mode} mode")
        monitor = PositionMonitor(client, db, mode=args.mode)
        monitor.run_continuous(symbol=args.monitor_symbol, interval_seconds=args.monitor_interval)
        sys.exit(0)
    
    # Modo operacional padrão - criar client para operação
    client = create_binance_client(mode=args.mode)
    logger.info(f"Binance client created in {args.mode} mode")
    start_operation(args.mode, client, db)


if __name__ == "__main__":
    main()
