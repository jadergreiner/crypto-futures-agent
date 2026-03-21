"""
Entry point do agente autônomo de futuros de criptomoedas.
"""

import argparse
import logging
import os
import sys
import threading
import time
from pathlib import Path
from datetime import datetime
import numpy as np

# Suprimir warnings do TensorFlow/Keras antes de importar qualquer módulo que o use
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Supprime INFO e WARNING (mantém ERROR)
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Evita warnings de oneDNN

from config.settings import (
    DB_PATH, TRADING_MODE, HISTORICAL_PERIODS, M2_EXECUTION_MODE, M2_LIVE_SYMBOLS, M2_LOOP_SECONDS
)
from config.symbols import ALL_SYMBOLS
from data.database import DatabaseManager
from data.binance_client import create_binance_client
from data.collector import BinanceCollector
from data.sentiment_collector import SentimentCollector
from data.macro_collector import MacroCollector
from data.background_data_collector import start_background_collector
from monitoring.logger import AgentLogger
from core.live_cycle_orchestrator import LiveCycleOrchestrator

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
        status = "OK"
        details = []
        try:
            d1_data = collector.fetch_historical(symbol, "1d", d1_days)
            h4_data = collector.fetch_historical(symbol, "4h", h4_days)
            h1_data = collector.fetch_historical(symbol, "1h", h1_days)
            sentiment = sentiment_collector.fetch_all_sentiment(symbol)
            if d1_data is None or d1_data.empty:
                status = "WARNING"
                details.append("D1 missing")
            if h4_data is None or h4_data.empty:
                status = "WARNING"
                details.append("H4 missing")
            if h1_data is None or h1_data.empty:
                status = "WARNING"
                details.append("H1 missing")
            if not sentiment:
                status = "INFO"
                details.append("Sentiment missing")
            if d1_data is not None and not d1_data.empty:
                db.insert_ohlcv("d1", d1_data)
            if h4_data is not None and not h4_data.empty:
                db.insert_ohlcv("h4", h4_data)
            if h1_data is not None and not h1_data.empty:
                db.insert_ohlcv("h1", h1_data)
            if sentiment:
                db.insert_sentiment([sentiment])
        except Exception as e:
            status = "ERROR"
            details.append(str(e))
        logger.info(f"[{symbol}] Data collection status: {status} {'; '.join(details) if details else ''}")
    # Macro data
    try:
        macro = macro_collector.fetch_all_macro()
        if macro:
            db.insert_macro(macro)
    except Exception as e:
        logger.error(f"Macro data error: {e}")
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
        status = "OK"
        details = []
        try:
            h4_data = db.get_ohlcv("h4", symbol)
            if h4_data is None or len(h4_data) == 0:
                status = "WARNING"
                details.append("No H4 data")
            else:
                df = pd.DataFrame(h4_data)
                df = TechnicalIndicators.calculate_all(df)
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
        except Exception as e:
            status = "ERROR"
            details.append(str(e))
        logger.info(f"[{symbol}] Indicator calculation status: {status} {'; '.join(details) if details else ''}")
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


def _train_single_symbol(
    symbol: str,
    data_loader,
    trainer,
    symbol_index: int,
    total_symbols: int,
    train_logger=None
) -> bool:
    """
    Treina um símbolo único.

    Args:
        symbol: Símbolo a treinar
        data_loader: DataLoader instance
        trainer: Trainer instance
        symbol_index: Índice do símbolo (1-based para exibição)
        total_symbols: Total de símbolos
        train_logger: Logger para treinamento (opcional)

    Returns:
        True se modelo passou na validação, False caso contrário
    """
    if train_logger is None:
        train_logger = logger

    train_logger.info("")
    train_logger.info("="*60)
    train_logger.info(f"[{symbol_index}/{total_symbols}] TREINANDO: {symbol}")
    train_logger.info("="*60)

    # Diagnóstico de dados
    diagnosis = data_loader.diagnose_data_readiness(
        symbol=symbol,
        min_length_train=1000,
        min_length_val=200,
        train_ratio=0.8
    )

    if not diagnosis['ready']:
        train_logger.error(f"[FALHA] Dados insuficientes para {symbol}")
        train_logger.error(diagnosis['summary'])
        return False

    # Carregar dados
    train_logger.info(f"Carregando dados de treinamento para {symbol}...")
    train_data = data_loader.load_training_data(symbol=symbol, min_length=1000)
    summary = data_loader.get_data_summary(train_data)
    train_logger.info(f"  - H4: {summary['h4']['length']} candles")
    train_logger.info(f"  - H1: {summary['h1']['length']} candles")
    train_logger.info(f"  - D1: {summary['d1']['length']} candles")

    train_logger.info(f"Carregando dados de validação para {symbol}...")
    val_data = data_loader.load_validation_data(symbol=symbol, min_length=200)

    # Fase 1: Exploração
    train_logger.info(f"Fase 1: Exploração para {symbol}...")
    trainer.train_phase1_exploration(
        train_data=train_data,
        total_timesteps=500000,
        episode_length=500
    )

    # Fase 2: Refinamento
    train_logger.info(f"Fase 2: Refinamento para {symbol}...")
    trainer.train_phase2_refinement(
        train_data=train_data,
        total_timesteps=1000000,
        load_phase1=True,
        episode_length=500
    )

    # Fase 3: Validação
    train_logger.info(f"Fase 3: Validação para {symbol}...")
    metrics = trainer.train_phase3_validation(
        test_data=val_data,
        n_episodes=100,
        episode_length=500
    )

    # Verificar se passou
    passed = metrics['sharpe_ratio'] > 1.0 and metrics['max_drawdown'] < 0.15

    if passed:
        train_logger.info(f"[OK] {symbol} passou na validação")
        train_logger.info(f"  - Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        train_logger.info(f"  - Max Drawdown: {metrics['max_drawdown']*100:.2f}%")
        train_logger.info(f"  - Win Rate: {metrics['win_rate']*100:.2f}%")
        train_logger.info(f"  - Avg R-Multiple: {metrics['avg_r_multiple']:.2f}")

        # Salvar modelo final específico do símbolo
        final_path = f"models/crypto_agent_ppo_{symbol}_final.zip"
        trainer.save_model(final_path)
        train_logger.info(f"[OK] Modelo salvo: {final_path}")
    else:
        train_logger.warning(f"[FALHA] {symbol} não passou na validação")
        train_logger.warning(f"  - Sharpe Ratio: {metrics['sharpe_ratio']:.2f} (requer > 1.0)")
        train_logger.warning(f"  - Max Drawdown: {metrics['max_drawdown']*100:.2f}% (requer < 15%)")

    return passed


def train_model(symbols: list = None) -> None:
    """
    Treina o modelo RL para múltiplos símbolos.

    Args:
        symbols: Lista de símbolos a treinar. Default = 4 high-caps
    """
    # Default: treinar os 4 high-caps
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

    # Configurar logger separado para treinamento (evita conflito com agent.log)
    from monitoring.logger import AgentLogger
    train_logger = AgentLogger.setup_context_logger(context="training", name="crypto_agent_training")

    train_logger.info("="*60)
    train_logger.info("TRAINING RL MODELS - MÚLTIPLOS SÍMBOLOS")
    train_logger.info("="*60)
    train_logger.info(f"Símbolos a treinar: {', '.join(symbols)}")
    train_logger.info("")

    from agent.data_loader import DataLoader
    from agent.trainer import Trainer

    try:
        # Inicializar database e data loader
        db = setup_database()
        train_logger.info("Inicializando Data Loader...")
        data_loader = DataLoader(db=db)

        # Diagnóstico pré-treinamento para todos
        train_logger.info("="*60)
        train_logger.info("DIAGNÓSTICO DE DISPONIBILIDADE DE DADOS")
        train_logger.info("="*60)
        diagnoses = data_loader.diagnose_multi_symbols(symbols=symbols)

        # Exibir resumo diagnóstico
        ready_symbols = [s for s in symbols if diagnoses[s]['ready']]
        failed_symbols = [s for s in symbols if not diagnoses[s]['ready']]

        if failed_symbols:
            train_logger.warning(f"Símbolos com dados insuficientes: {', '.join(failed_symbols)}")
            train_logger.warning("Estes símbolos serão pulados. Execute: python main.py --setup")

        if not ready_symbols:
            train_logger.error("Nenhum símbolo pronto para treinamento. Abortando.")
            return

        train_logger.info(f"Símbolos prontos para treinamento: {', '.join(ready_symbols)}")
        train_logger.info("")

        # Inicializar trainer uma vez
        train_logger.info("Inicializando Trainer...")
        trainer = Trainer(save_dir="models")

        # Treinar cada símbolo pronto
        results = {}
        for idx, symbol in enumerate(ready_symbols, 1):
            passed = _train_single_symbol(
                symbol=symbol,
                data_loader=data_loader,
                trainer=trainer,
                symbol_index=idx,
                total_symbols=len(ready_symbols),
                train_logger=train_logger
            )
            results[symbol] = passed

        # Resumo final
        train_logger.info("")
        train_logger.info("="*60)
        train_logger.info("RESUMO FINAL DO TREINAMENTO")
        train_logger.info("="*60)
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        train_logger.info(f"Modelos bem-sucedidos: {passed}/{total}")
        for symbol, passed_val in results.items():
            status = "[OK]" if passed_val else "[FALHA]"
            train_logger.info(f"  {status} {symbol}")
        train_logger.info("="*60)

    except Exception as e:
        train_logger.error(f"Erro durante treinamento: {e}", exc_info=True)


def start_operation(
    mode: str,
    client,
    db: DatabaseManager,
    enable_integrated_monitor: bool = False,
    integrated_interval_seconds: int = 300,
    enable_concurrent_training: bool = False,
    training_interval_seconds: int = 14400,
    enable_background_collector: bool = True,
    background_collector_interval_seconds: int = 300,
) -> None:
    """
    Inicia operação do agente.

    Args:
        mode: Modo de operação ("paper" ou "live")
        client: Binance SDK client instance
        db: DatabaseManager instance
        enable_integrated_monitor: Se deve monitorar posições abertas em paralelo
        integrated_interval_seconds: Intervalo de monitoramento em segundos
        enable_concurrent_training: Se deve treinar modelos em paralelo durante operação
        training_interval_seconds: Intervalo de treinamento em segundos (default 4 horas)
        enable_background_collector: Se deve coletar dados de ALL_SYMBOLS em background
        background_collector_interval_seconds: Intervalo de coleta em background (default 300s = 5min)
    """
    logger.info("="*60)
    logger.info(f"STARTING OPERATION - MODE: {mode.upper()}")
    logger.info("="*60)

    from core.layer_manager import LayerManager
    from core.scheduler import Scheduler
    from core.agent_scheduler import start_agent_training_scheduler

    # Inicializar layer manager com db e client
    layer_manager = LayerManager(db=db, client=client)

    # Inicializar scheduler principal
    scheduler = Scheduler(layer_manager)

    # Inicializar scheduler de treino de agentes (em background) - apenas se habilitado
    agent_training_scheduler = None
    if enable_concurrent_training:
        agent_training_scheduler = start_agent_training_scheduler(interval_hours=training_interval_seconds / 3600)
        logger.info(
            f"CONCURRENT TRAINING ENABLED: Modelos serão treinados a cada "
            f"{training_interval_seconds / 60:.0f} minutos em paralelo"
        )
    else:
        logger.info("Concurrent training is disabled")

    monitor = None
    monitor_thread = None

    if enable_integrated_monitor:
        from monitoring.position_monitor import PositionMonitor

        monitor = PositionMonitor(client, db, mode=mode)
        monitor_thread = threading.Thread(
            target=monitor.run_continuous,
            kwargs={
                'symbol': None,
                'interval_seconds': integrated_interval_seconds,
            },
            daemon=True,
            name='position-monitor-thread',
        )
        monitor_thread.start()
        logger.info(
            f"INTEGRATED MODE ENABLED: monitor de posições ativo em paralelo "
            f"(intervalo={integrated_interval_seconds}s)"
        )

    # Iniciar background data collector
    background_collector = None
    if enable_background_collector:
        background_collector = start_background_collector(
            db=db, interval_seconds=background_collector_interval_seconds
        )
        logger.info(
            f"BACKGROUND COLLECTOR ENABLED: coleta contínua de {len(ALL_SYMBOLS)} símbolos "
            f"(intervalo={background_collector_interval_seconds}s)"
        )

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
    finally:
        if agent_training_scheduler:
            agent_training_scheduler.stop()
        if monitor:
            monitor.stop()
        if monitor_thread and monitor_thread.is_alive():
            monitor_thread.join(timeout=5)
        if background_collector:
            background_collector.stop()


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
        '--symbols',
        type=str,
        default=None,
        help='Comma-separated symbols to train (default: BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT). Example: --symbols "BTCUSDT,ETHUSDT"'
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
        '--adopt-position',
        type=str,
        default=None,
        help='Assume management of an already open Binance position for a specific symbol (e.g., BTCUSDT).'
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

    parser.add_argument(
        '--integrated',
        action='store_true',
        help='Run unified mode: seek opportunities + manage open positions in parallel'
    )

    parser.add_argument(
        '--integrated-interval',
        type=int,
        default=300,
        help='Interval in seconds for integrated position monitoring (default: 300)'
    )

    parser.add_argument(
        '--concurrent-training',
        action='store_true',
        help='Enable concurrent RL model training while trading live'
    )

    parser.add_argument(
        '--training-interval',
        type=int,
        default=14400,  # 4 horas por padrão
        help='Interval in seconds for concurrent training cycles (default: 14400 = 4 hours)'
    )

    parser.add_argument(
        '--run-m2-cycle',
        action='store_true',
        help='Run the M2 model-driven orchestration cycle continuously'
    )

    parser.add_argument(
        '--m2-loop-seconds',
        type=int,
        default=M2_LOOP_SECONDS,
        help=f'Loop time in seconds for the M2 cycle (default: {M2_LOOP_SECONDS})'
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
    if args.run_m2_cycle:
        logger.info("Starting M2 model-driven cycle execution.")
        try:
            orchestrator = LiveCycleOrchestrator(
                execution_mode=M2_EXECUTION_MODE,
                symbols=M2_LIVE_SYMBOLS
            )
            while True:
                orchestrator.run_cycle()
                logger.info(f"M2 cycle finished. Waiting for {args.m2_loop_seconds} seconds...")
                time.sleep(args.m2_loop_seconds)
        except KeyboardInterrupt:
            logger.info("M2 cycle interrupted by user.")
        except Exception as e:
            logger.critical(f"A critical error occurred in the M2 cycle orchestrator: {e}", exc_info=True)
        sys.exit(0)
        
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
        # Parse símbolos a treinar
        symbols = None
        if args.symbols:
            symbols = [s.strip().upper() for s in args.symbols.split(',')]
        train_model(symbols=symbols)
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

    if args.adopt_position:
        # Modo de adoção: usuário escolhe uma posição já aberta na Binance
        from monitoring.position_monitor import PositionMonitor

        symbol = args.adopt_position.upper().strip()
        client = create_binance_client(mode=args.mode)
        logger.info(f"Binance client created in {args.mode} mode")

        monitor = PositionMonitor(client, db, mode=args.mode)
        open_positions = monitor.fetch_open_positions(symbol=symbol)

        if not open_positions:
            logger.error(
                f"Nenhuma posição aberta encontrada para {symbol}. "
                f"Abra uma posição na Binance antes de solicitar gerenciamento do agente."
            )
            sys.exit(1)

        logger.info("="*60)
        logger.info(f"ADOPT POSITION MODE - {symbol}")
        logger.info(
            f"Posição(ões) detectada(s): {len(open_positions)} | "
            f"Iniciando gerenciamento contínuo pelo agente"
        )
        logger.info("="*60)

        # Bootstrap de adoção: gerar snapshot inicial e criar SL/TP reais de proteção
        protection_result = monitor.adopt_position_with_protection(symbol)
        if protection_result.get('ok'):
            logger.info(
                f"Proteções criadas para {symbol}: "
                f"SL={'OK' if protection_result.get('sl_created') else 'NÃO'} | "
                f"TP={'OK' if protection_result.get('tp_created') else 'NÃO'}"
            )
        else:
            logger.warning(
                f"Bootstrap de proteção para {symbol} falhou/foi parcial: "
                f"{protection_result.get('reason', 'sem detalhes')}"
            )

        monitor.run_continuous(symbol=symbol, interval_seconds=args.monitor_interval)
        sys.exit(0)

    # Modo operacional padrão - criar client para operação
    client = create_binance_client(mode=args.mode)
    logger.info(f"Binance client created in {args.mode} mode")
    start_operation(
        args.mode,
        client,
        db,
        enable_integrated_monitor=args.integrated,
        integrated_interval_seconds=args.integrated_interval,
        enable_concurrent_training=args.concurrent_training,
        training_interval_seconds=args.training_interval,
    )


if __name__ == "__main__":
    main()
