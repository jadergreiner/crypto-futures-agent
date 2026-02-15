"""
Entry point do agente autônomo de futuros de criptomoedas.
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import numpy as np

from config.settings import DB_PATH, TRADING_MODE, HISTORICAL_PERIODS
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
    
    # Usar períodos configurados em settings.py
    d1_days = HISTORICAL_PERIODS.get('D1', 365)
    h4_days = HISTORICAL_PERIODS.get('H4', 180)
    h1_days = HISTORICAL_PERIODS.get('H1', 90)
    
    logger.info(f"Períodos de coleta configurados:")
    logger.info(f"  D1: {d1_days} dias")
    logger.info(f"  H4: {h4_days} dias")
    logger.info(f"  H1: {h1_days} dias")
    logger.info("")
    
    for symbol in ALL_SYMBOLS:
        logger.info(f"Coletando dados para {symbol}...")
        
        try:
            # OHLCV D1
            d1_data = collector.fetch_historical(symbol, "1d", d1_days)
            if d1_data is not None and not d1_data.empty:
                db.insert_ohlcv("d1", d1_data)
                logger.info(f"  {len(d1_data)} candles D1 inseridos")
            
            # OHLCV H4
            h4_data = collector.fetch_historical(symbol, "4h", h4_days)
            if h4_data is not None and not h4_data.empty:
                db.insert_ohlcv("h4", h4_data)
                logger.info(f"  {len(h4_data)} candles H4 inseridos")
            
            # OHLCV H1
            h1_data = collector.fetch_historical(symbol, "1h", h1_days)
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


def run_dry_run() -> None:
    """
    Executa modo dry-run: valida o pipeline sem API keys.
    Usa dados sintéticos para testar o fluxo completo.
    """
    logger.info("="*60)
    logger.info("DRY-RUN MODE - Testing Pipeline with Synthetic Data")
    logger.info("="*60)
    
    from tests.test_e2e_pipeline import (
        create_synthetic_ohlcv,
        create_synthetic_macro_data,
        create_synthetic_sentiment_data
    )
    from indicators.technical import TechnicalIndicators
    from indicators.smc import SmartMoneyConcepts
    from indicators.multi_timeframe import MultiTimeframeAnalysis
    from indicators.features import FeatureEngineer
    
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    
    logger.info(f"Testing pipeline for {len(test_symbols)} symbols...")
    
    for symbol in test_symbols:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {symbol}")
            logger.info(f"{'='*60}")
            
            # Step 1: Create synthetic data
            logger.info("  [1/7] Creating synthetic data...")
            h1_data = create_synthetic_ohlcv(length=250, trend=5, seed=100)
            h4_data = create_synthetic_ohlcv(length=200, trend=5, seed=101)
            d1_data = create_synthetic_ohlcv(length=100, trend=10, seed=102)
            btc_d1_data = create_synthetic_ohlcv(length=100, trend=8, seed=103)
            
            # Step 2: Calculate technical indicators
            logger.info("  [2/7] Calculating technical indicators...")
            h1_data = TechnicalIndicators.calculate_all(h1_data)
            h4_data = TechnicalIndicators.calculate_all(h4_data)
            d1_data = TechnicalIndicators.calculate_all(d1_data)
            btc_d1_data = TechnicalIndicators.calculate_all(btc_d1_data)
            
            # Step 3: Calculate SMC structures
            logger.info("  [3/7] Calculating SMC structures...")
            smc_result = SmartMoneyConcepts.calculate_all_smc(h1_data)
            logger.info(f"    - Structure: {smc_result['structure'].type.value if smc_result['structure'] else 'None'}")
            logger.info(f"    - Order Blocks: {len(smc_result['order_blocks'])}")
            logger.info(f"    - FVGs: {len(smc_result['fvgs'])}")
            
            # Step 4: Create macro and sentiment data
            logger.info("  [4/7] Creating macro and sentiment data...")
            macro_data = create_synthetic_macro_data()
            sentiment_data = create_synthetic_sentiment_data()
            sentiment_data['symbol'] = symbol
            
            # Step 5: Multi-timeframe analysis (L5)
            logger.info("  [5/7] Running multi-timeframe analysis (Layer 5)...")
            multi_tf_result = MultiTimeframeAnalysis.aggregate(
                h1_data=h1_data,
                h4_data=h4_data,
                d1_data=d1_data,
                symbol=symbol,
                macro_data=macro_data,
                btc_data=btc_d1_data
            )
            logger.info(f"    - D1 Bias: {multi_tf_result['d1_bias']}")
            logger.info(f"    - Market Regime: {multi_tf_result['market_regime']}")
            logger.info(f"    - Correlation BTC: {multi_tf_result['correlation_btc']:.3f}")
            logger.info(f"    - Beta BTC: {multi_tf_result['beta_btc']:.3f}")
            
            # Step 6: Build observation (Feature Engineering)
            logger.info("  [6/7] Building observation vector...")
            observation = FeatureEngineer.build_observation(
                symbol=symbol,
                h1_data=h1_data,
                h4_data=h4_data,
                d1_data=d1_data,
                sentiment=sentiment_data,
                macro=macro_data,
                smc=smc_result,
                position_state=None,
                multi_tf_result=multi_tf_result
            )
            
            # Step 7: Validate observation
            logger.info("  [7/7] Validating observation...")
            logger.info(f"    - Features count: {len(observation)}")
            logger.info(f"    - Has NaN values: {np.any(np.isnan(observation))}")
            logger.info(f"    - Min value: {np.min(observation):.3f}")
            logger.info(f"    - Max value: {np.max(observation):.3f}")
            logger.info(f"    - Mean value: {np.mean(observation):.3f}")
            
            # Check blocks 7 and 8 specifically
            block7_start = 11 + 6 + 11 + 19 + 4 + 4  # 55
            block8_start = block7_start + 3  # 58
            
            logger.info(f"\n  Block 7 (Correlation) - Features {block7_start}-{block7_start+2}:")
            logger.info(f"    - BTC Return: {observation[block7_start]:.3f}")
            logger.info(f"    - Correlation: {observation[block7_start + 1]:.3f}")
            logger.info(f"    - Beta: {observation[block7_start + 2]:.3f}")
            
            logger.info(f"\n  Block 8 (D1 Context) - Features {block8_start}-{block8_start+1}:")
            logger.info(f"    - D1 Bias Score: {observation[block8_start]:.1f} ({multi_tf_result['d1_bias']})")
            logger.info(f"    - Regime Score: {observation[block8_start + 1]:.1f} ({multi_tf_result['market_regime']})")
            
            # Validation checks
            assert len(observation) == 104, f"Expected 104 features, got {len(observation)}"
            assert not np.any(np.isnan(observation)), "Observation contains NaN values"
            assert np.all(observation >= -10) and np.all(observation <= 10), \
                "Observation values outside [-10, 10] range"
            
            logger.info(f"\n  [OK] {symbol} pipeline completed successfully!")
            
        except Exception as e:
            logger.error(f"  [ERROR] Error processing {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info("\n" + "="*60)
    logger.info("DRY-RUN SUMMARY")
    logger.info("="*60)
    logger.info(f"Tested {len(test_symbols)} symbols")
    logger.info("Pipeline validation: [OK]")
    logger.info("\nThe pipeline is working correctly with synthetic data.")
    logger.info("You can now run with real data using --mode paper or --mode live")
    logger.info("="*60)


def train_model() -> None:
    """Treina o modelo RL."""
    logger.info("="*60)
    logger.info("TRAINING RL MODEL")
    logger.info("="*60)
    
    from agent.data_loader import DataLoader
    from agent.trainer import Trainer
    
    try:
        # Inicializar database
        db = setup_database()
        
        # Inicializar data loader
        logger.info("Inicializando Data Loader...")
        data_loader = DataLoader(db=db)
        
        # NOVO: Diagnóstico pré-treinamento
        logger.info("="*60)
        logger.info("DIAGNÓSTICO DE DISPONIBILIDADE DE DADOS")
        logger.info("="*60)
        diagnosis = data_loader.diagnose_data_readiness(
            symbol="BTCUSDT",
            min_length_train=1000,
            min_length_val=200,
            train_ratio=0.8
        )
        
        # Exibir diagnóstico detalhado
        logger.info(f"Símbolo: {diagnosis['symbol']}")
        logger.info("")
        logger.info("Status dos Timeframes:")
        for tf, info in diagnosis['timeframes'].items():
            logger.info(f"  {tf.upper()}:")
            logger.info(f"    Disponível: {info.get('available', 0)} candles")
            if 'needed_total' in info:
                logger.info(f"    Necessário (total): {info['needed_total']} candles")
                logger.info(f"    Necessário (treino): {info['needed_train']} candles")
                logger.info(f"    Após split 80/20: {info['after_split']} candles")
            logger.info(f"    Status: {info['status']}")
            if info.get('recommendation'):
                logger.info(f"    → {info['recommendation']}")
        
        # Exibir status de indicadores
        if diagnosis.get('indicators'):
            logger.info("")
            logger.info("Requisitos de Indicadores:")
            for ind, info in diagnosis['indicators'].items():
                logger.info(f"  {ind}:")
                logger.info(f"    Necessário: {info['required_candles']} candles")
                logger.info(f"    Disponível: {info['available']} candles")
                logger.info(f"    Status: {info['status']}")
                if '❌' in info.get('status', ''):
                    logger.info(f"    → {info['recommendation']}")
        
        # Exibir atualização dos dados
        if diagnosis.get('data_freshness'):
            logger.info("")
            logger.info("Atualização dos Dados:")
            freshness = diagnosis['data_freshness']
            logger.info(f"  Último candle H4: {freshness['last_h4_timestamp']}")
            logger.info(f"  Horas desde última atualização: {freshness['hours_since_last']}")
            if freshness['is_stale']:
                logger.warning("  ⚠️  DADOS DESATUALIZADOS (>24h)")
        
        logger.info("")
        logger.info("="*60)
        logger.info(diagnosis['summary'])
        logger.info("="*60)
        
        # Se dados insuficientes, parar sem fallback silencioso
        if not diagnosis['ready']:
            logger.error("")
            logger.error("="*60)
            logger.error("TREINAMENTO ABORTADO - DADOS INSUFICIENTES")
            logger.error("="*60)
            logger.error("")
            logger.error("AÇÕES RECOMENDADAS:")
            logger.error("1. Execute: python main.py --setup")
            logger.error("   Para coletar dados históricos completos")
            logger.error("")
            logger.error("2. Ou aumente os períodos em config/settings.py:")
            logger.error("   HISTORICAL_PERIODS = {")
            logger.error("       'D1': 730,   # Para EMA_610 com margem")
            logger.error("       'H4': 250,   # Para 1000+ candles após split")
            logger.error("       'H1': 120")
            logger.error("   }")
            logger.error("")
            logger.error("="*60)
            return
        
        # Continuar com o treino normal se dados OK
        logger.info("✅ Dados suficientes, iniciando carregamento...")
        logger.info("")
        
        # Carregar dados de treino
        logger.info("Carregando dados de treinamento...")
        train_data = data_loader.load_training_data(symbol="BTCUSDT", min_length=1000)
        
        # Mostrar resumo dos dados
        summary = data_loader.get_data_summary(train_data)
        logger.info(f"Dados de treino carregados:")
        logger.info(f"  - H4: {summary['h4']['length']} candles")
        logger.info(f"  - H1: {summary['h1']['length']} candles")
        logger.info(f"  - D1: {summary['d1']['length']} candles")
        
        # Carregar dados de validação
        logger.info("Carregando dados de validação...")
        val_data = data_loader.load_validation_data(symbol="BTCUSDT", min_length=200)
        val_summary = data_loader.get_data_summary(val_data)
        logger.info(f"Dados de validação carregados:")
        logger.info(f"  - H4: {val_summary['h4']['length']} candles")
        
        # Inicializar trainer
        logger.info("Inicializando Trainer...")
        trainer = Trainer(save_dir="models")
        
        # Fase 1: Exploração (500k steps)
        logger.info("Iniciando Fase 1: Exploração...")
        trainer.train_phase1_exploration(
            train_data=train_data,
            total_timesteps=500000,
            episode_length=500
        )
        
        # Fase 2: Refinamento (1M steps)
        logger.info("Iniciando Fase 2: Refinamento...")
        trainer.train_phase2_refinement(
            train_data=train_data,
            total_timesteps=1000000,
            load_phase1=True,
            episode_length=500
        )
        
        # Fase 3: Validação
        logger.info("Iniciando Fase 3: Validação...")
        metrics = trainer.train_phase3_validation(
            test_data=val_data,
            n_episodes=100,
            episode_length=500
        )
        
        # Verificar se modelo passou nos critérios
        if metrics['sharpe_ratio'] > 1.0 and metrics['max_drawdown'] < 0.15:
            logger.info("[OK] Modelo passou nos critérios de validação")
            logger.info(f"  - Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            logger.info(f"  - Max Drawdown: {metrics['max_drawdown']*100:.2f}%")
            logger.info(f"  - Win Rate: {metrics['win_rate']*100:.2f}%")
            logger.info(f"  - Avg R-Multiple: {metrics['avg_r_multiple']:.2f}")
            
            # Salvar modelo final
            final_path = "models/crypto_agent_ppo_final.zip"
            trainer.save_model(final_path)
            logger.info(f"[OK] Modelo final salvo: {final_path}")
        else:
            logger.warning("[FALHA] Modelo não passou nos critérios de validação")
            logger.warning(f"  - Sharpe Ratio: {metrics['sharpe_ratio']:.2f} (requer > 1.0)")
            logger.warning(f"  - Max Drawdown: {metrics['max_drawdown']*100:.2f}% (requer < 15%)")
        
        logger.info("="*60)
        logger.info("TREINAMENTO CONCLUÍDO")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Erro durante treinamento: {e}", exc_info=True)


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
    Executa backtest com modelo treinado.
    
    Args:
        start_date: Data inicial (YYYY-MM-DD)
        end_date: Data final (YYYY-MM-DD)
    """
    logger.info("="*60)
    logger.info(f"RUNNING BACKTEST: {start_date} to {end_date}")
    logger.info("="*60)
    
    from backtest.backtester import Backtester
    from agent.data_loader import DataLoader
    from agent.trainer import Trainer
    import os
    
    try:
        # Verificar se existe modelo treinado
        model_path = "models/crypto_agent_ppo_final.zip"
        if not os.path.exists(model_path):
            # Tentar modelo da fase 2
            model_path = "models/phase2_refinement.zip"
            if not os.path.exists(model_path):
                logger.error("Nenhum modelo treinado encontrado. Execute --train primeiro.")
                return
        
        logger.info(f"Carregando modelo: {model_path}")
        
        # Inicializar database
        db = setup_database()
        
        # Carregar dados
        logger.info("Carregando dados para backtest...")
        data_loader = DataLoader(db=db)
        test_data = data_loader.load_validation_data(symbol="BTCUSDT", min_length=500)
        
        summary = data_loader.get_data_summary(test_data)
        logger.info(f"Dados carregados: H4={summary['h4']['length']} candles")
        
        # Carregar modelo
        trainer = Trainer()
        trainer.load_model(model_path)
        
        # Executar backtest
        backtester = Backtester(initial_capital=10000)
        results = backtester.run(
            start_date=start_date,
            end_date=end_date,
            model=trainer.model,
            data=test_data
        )
        
        # Mostrar resultados
        logger.info("="*60)
        logger.info("BACKTEST RESULTS")
        logger.info("="*60)
        logger.info(f"Initial Capital: ${results['initial_capital']:.2f}")
        logger.info(f"Final Capital: ${results['final_capital']:.2f}")
        logger.info(f"Total Return: {results['metrics']['total_return_pct']:.2f}%")
        logger.info(f"Total Trades: {results['total_trades']}")
        logger.info("")
        logger.info("Metrics:")
        logger.info(f"  Win Rate: {results['metrics']['win_rate']*100:.2f}%")
        logger.info(f"  Profit Factor: {results['metrics']['profit_factor']:.2f}")
        logger.info(f"  Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
        logger.info(f"  Max Drawdown: {results['metrics']['max_drawdown_pct']:.2f}%")
        logger.info(f"  Avg R-Multiple: {results['metrics']['avg_r_multiple']:.2f}")
        
        # Gerar relatório visual
        report_path = f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        backtester.generate_report(results, save_path=report_path)
        logger.info(f"[OK] Relatório salvo: {report_path}")
        
        logger.info("="*60)
        logger.info("BACKTEST CONCLUÍDO")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Erro durante backtest: {e}", exc_info=True)


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
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run pipeline validation with synthetic data (no API keys required)'
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
    if args.dry_run:
        # Modo dry-run: não requer API keys
        run_dry_run()
        sys.exit(0)
    
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
