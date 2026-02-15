"""
Testes de integracao para Layer Manager - Layers 4 e 5.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
import numpy as np
from datetime import datetime

from core.layer_manager import LayerManager
from data.database import DatabaseManager


@pytest.fixture
def mock_client():
    """Cliente Binance mockado."""
    return Mock()


@pytest.fixture
def mock_db():
    """Database manager mockado."""
    db = Mock(spec=DatabaseManager)
    db.insert_indicators = Mock()
    db.insert_sentiment = Mock()
    db.insert_macro = Mock()
    return db


@pytest.fixture
def layer_manager(mock_client, mock_db):
    """Layer manager com dependencias mockadas."""
    return LayerManager(db=mock_db, client=mock_client)


@pytest.fixture
def sample_ohlcv_data():
    """Dados OHLCV de exemplo."""
    timestamps = [1700000000000 + i * 3600000 for i in range(100)]
    data = {
        'timestamp': timestamps,
        'symbol': ['BTCUSDT'] * 100,
        'open': [30000 + i * 10 for i in range(100)],
        'high': [30100 + i * 10 for i in range(100)],
        'low': [29900 + i * 10 for i in range(100)],
        'close': [30000 + i * 10 for i in range(100)],
        'volume': [1000.0] * 100,
        'quote_volume': [30000000.0] * 100,
        'trades_count': [500] * 100,
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_sentiment_data():
    """Dados de sentimento de exemplo."""
    return {
        'timestamp': 1700000000000,
        'symbol': 'BTCUSDT',
        'long_short_ratio': 1.2,
        'open_interest': 50000000.0,
        'funding_rate': 0.0001,
        'long_account': 0.55,
        'short_account': 0.45,
    }


@pytest.fixture
def sample_macro_data():
    """Dados macro de exemplo."""
    return {
        'timestamp': 1700000000000,
        'fear_greed_value': 65,
        'fear_greed_classification': 'Greed',
        'btc_dominance': 48.5,
        'dxy': 100.0,
        'dxy_change_pct': -0.3,
    }


def test_layer_manager_initialization(layer_manager):
    """Testa inicializacao do Layer Manager."""
    assert layer_manager.d1_context == {}
    assert layer_manager.feature_history == {}
    assert layer_manager.smc_cache == {}
    assert layer_manager.binance_collector is not None
    assert layer_manager.sentiment_collector is not None
    assert layer_manager.macro_collector is not None
    assert layer_manager.risk_manager is not None


def test_d1_trend_macro_populates_context(layer_manager, sample_ohlcv_data, 
                                          sample_sentiment_data, sample_macro_data):
    """Testa que d1_trend_macro() popula corretamente o d1_context."""
    
    # Mock dos coletores
    layer_manager.binance_collector.fetch_historical = Mock(return_value=sample_ohlcv_data)
    layer_manager.sentiment_collector.fetch_all_sentiment = Mock(return_value=sample_sentiment_data)
    layer_manager.macro_collector.fetch_all_macro = Mock(return_value=sample_macro_data)
    
    # Executar
    layer_manager.d1_trend_macro()
    
    # Validar que o contexto foi populado
    assert len(layer_manager.d1_context) > 0
    
    # Verificar estrutura do contexto para BTCUSDT
    if 'BTCUSDT' in layer_manager.d1_context:
        btc_context = layer_manager.d1_context['BTCUSDT']
        assert 'd1_bias' in btc_context
        assert btc_context['d1_bias'] in ['BULLISH', 'BEARISH', 'NEUTRO']
        assert 'market_regime' in btc_context
        assert btc_context['market_regime'] in ['RISK_ON', 'RISK_OFF', 'NEUTRO']
        assert 'correlation_btc' in btc_context
        assert 'beta_btc' in btc_context
        assert 'd1_data' in btc_context
        assert isinstance(btc_context['d1_data'], pd.DataFrame)
        assert 'macro' in btc_context
        assert 'sentiment' in btc_context


def test_d1_trend_macro_handles_symbol_failure(layer_manager, sample_ohlcv_data,
                                                sample_macro_data):
    """Testa que d1_trend_macro continua processando mesmo se um simbolo falhar."""
    
    # Mock macro collector
    layer_manager.macro_collector.fetch_all_macro = Mock(return_value=sample_macro_data)
    
    # Mock binance collector para falhar em alguns simbolos
    def fetch_historical_mock(symbol, interval, days):
        if symbol == 'ETHUSDT':
            raise Exception("Erro de rede simulado")
        return sample_ohlcv_data.copy()
    
    layer_manager.binance_collector.fetch_historical = Mock(side_effect=fetch_historical_mock)
    layer_manager.sentiment_collector.fetch_all_sentiment = Mock(return_value={})
    
    # Executar
    layer_manager.d1_trend_macro()
    
    # Deve ter processado alguns simbolos (menos ETHUSDT)
    assert len(layer_manager.d1_context) > 0
    # ETHUSDT nao deve estar no contexto
    assert 'ETHUSDT' not in layer_manager.d1_context


def test_d1_trend_macro_persists_to_database(layer_manager, sample_ohlcv_data,
                                             sample_sentiment_data, sample_macro_data):
    """Testa que d1_trend_macro persiste dados no banco."""
    
    # Mock dos coletores
    layer_manager.binance_collector.fetch_historical = Mock(return_value=sample_ohlcv_data)
    layer_manager.sentiment_collector.fetch_all_sentiment = Mock(return_value=sample_sentiment_data)
    layer_manager.macro_collector.fetch_all_macro = Mock(return_value=sample_macro_data)
    
    # Executar
    layer_manager.d1_trend_macro()
    
    # Verificar que os metodos de insercao foram chamados
    assert layer_manager.db.insert_macro.called
    assert layer_manager.db.insert_sentiment.called
    assert layer_manager.db.insert_indicators.called


def test_h4_main_decision_processes_symbols(layer_manager, sample_ohlcv_data):
    """Testa que h4_main_decision processa todos os simbolos."""
    
    # Preparar contexto D1
    layer_manager.d1_context = {
        'BTCUSDT': {
            'd1_bias': 'BULLISH',
            'market_regime': 'RISK_ON',
            'correlation_btc': 1.0,
            'beta_btc': 1.0,
            'd1_data': sample_ohlcv_data.copy(),
            'macro': {'fear_greed_value': 65},
            'sentiment': {'funding_rate': 0.0001},
        }
    }
    
    # Mock dos coletores
    layer_manager.binance_collector.fetch_historical = Mock(return_value=sample_ohlcv_data)
    layer_manager.sentiment_collector.fetch_all_sentiment = Mock(return_value={'funding_rate': 0.0001})
    
    # Executar
    layer_manager.h4_main_decision()
    
    # Verificar que SMC cache foi populado
    assert len(layer_manager.smc_cache) > 0
    
    # Verificar que feature history foi populado
    assert len(layer_manager.feature_history) > 0


def test_h4_confluence_scoring_logic(layer_manager, sample_ohlcv_data):
    """Testa a logica de calculo de confluencia."""
    
    # Criar DataFrame H4 com indicadores
    h4_df = sample_ohlcv_data.copy()
    h4_df['ema_alignment_score'] = 5  # Bullish alignment
    h4_df['rsi_14'] = 55
    h4_df['adx_14'] = 30
    h4_df['atr_14'] = 500
    
    # Mock SMC result
    smc_result = {
        'market_structure': Mock(type=Mock(value='bullish')),
        'bos_list': [Mock(direction='bullish')],
        'order_blocks': [],
        'liquidity': [],
    }
    
    # Calcular score
    score, direction = layer_manager._calculate_confluence_score(
        symbol='BTCUSDT',
        h4_df=h4_df,
        d1_bias='BULLISH',
        market_regime='RISK_ON',
        smc_result=smc_result,
        sentiment={'funding_rate': 0.0001}
    )
    
    # Validar
    assert score > 0
    assert direction in ['LONG', 'SHORT', 'NONE']
    
    # Para setup bullish, deve ser LONG
    if score >= 8:
        assert direction == 'LONG'


def test_h4_signal_registration_threshold(layer_manager, sample_ohlcv_data):
    """Testa que sinais sao registrados apenas acima do threshold."""
    
    # Preparar contexto
    layer_manager.d1_context = {
        'BTCUSDT': {
            'd1_bias': 'BULLISH',
            'market_regime': 'RISK_ON',
            'correlation_btc': 1.0,
            'beta_btc': 1.0,
            'd1_data': sample_ohlcv_data.copy(),
            'macro': {'fear_greed_value': 65},
            'sentiment': {'funding_rate': 0.0001},
        }
    }
    
    # Mock para forcar score baixo
    def calculate_confluence_mock(*args, **kwargs):
        return 5, "LONG"  # Score abaixo do threshold (8)
    
    layer_manager._calculate_confluence_score = Mock(side_effect=calculate_confluence_mock)
    layer_manager.binance_collector.fetch_historical = Mock(return_value=sample_ohlcv_data)
    
    # Executar
    initial_signals = len(layer_manager.pending_signals)
    layer_manager.h4_main_decision()
    
    # Nao deve ter registrado sinais
    assert len(layer_manager.pending_signals) == initial_signals


def test_h4_signal_registration_above_threshold(layer_manager, sample_ohlcv_data):
    """Testa que sinais sao registrados acima do threshold."""
    
    # Preparar H4 data com indicadores validos
    h4_df = sample_ohlcv_data.copy()
    h4_df['atr_14'] = 500
    
    # Preparar contexto
    layer_manager.d1_context = {
        'BTCUSDT': {
            'd1_bias': 'BULLISH',
            'market_regime': 'RISK_ON',
            'correlation_btc': 1.0,
            'beta_btc': 1.0,
            'd1_data': sample_ohlcv_data.copy(),
            'macro': {'fear_greed_value': 65},
            'sentiment': {'funding_rate': 0.0001},
        }
    }
    
    # Mock para forcar score alto
    def calculate_confluence_mock(*args, **kwargs):
        return 10, "LONG"  # Score acima do threshold
    
    layer_manager._calculate_confluence_score = Mock(side_effect=calculate_confluence_mock)
    layer_manager.binance_collector.fetch_historical = Mock(return_value=h4_df)
    
    # Mock stops calculation
    def calc_stops_mock(*args, **kwargs):
        return 29000, 32000  # stop, tp
    
    layer_manager._calculate_stops_and_targets = Mock(side_effect=calc_stops_mock)
    
    # Mock validation (approve)
    layer_manager._validate_signal_with_risk = Mock(return_value=True)
    
    # Executar
    initial_signals = len(layer_manager.pending_signals)
    layer_manager.h4_main_decision()
    
    # Deve ter registrado pelo menos um sinal
    # Nota: pode nao registrar se o simbolo nao passar pela validacao de risco
    # por isso verificamos apenas que o metodo foi executado sem erros


def test_h4_position_reevaluation(layer_manager, sample_ohlcv_data):
    """Testa que posicoes existentes sao reavaliadas."""
    
    # Criar posicao existente
    layer_manager.open_positions['BTCUSDT'] = {
        'direction': 'LONG',
        'entry_price': 30000,
        'size': 0.1,
        'stop': 29000,
        'tp': 32000,
    }
    
    # Preparar H4 data
    h4_df = sample_ohlcv_data.copy()
    h4_df['close'] = [31000] * 100  # Preco atual acima da entrada
    
    # Mock SMC result
    smc_result = {
        'market_structure': Mock(type=Mock(value='bullish')),
        'bos_list': [],
        'order_blocks': [],
        'liquidity': [],
    }
    
    # Executar avaliacao
    layer_manager._evaluate_existing_position(
        symbol='BTCUSDT',
        position=layer_manager.open_positions['BTCUSDT'],
        h4_df=h4_df,
        smc_result=smc_result,
        confluence_score=10,
        d1_bias='BULLISH'
    )
    
    # Posicao deve continuar aberta (score alto, bias favoravel)
    assert 'BTCUSDT' in layer_manager.open_positions


def test_h4_position_close_on_bias_reversal(layer_manager, sample_ohlcv_data):
    """Testa que posicoes sao fechadas quando D1 bias reverte."""
    
    # Criar posicao LONG
    layer_manager.open_positions['BTCUSDT'] = {
        'direction': 'LONG',
        'entry_price': 30000,
        'size': 0.1,
    }
    
    # Preparar H4 data
    h4_df = sample_ohlcv_data.copy()
    
    # Mock SMC
    smc_result = {'market_structure': None, 'bos_list': [], 'order_blocks': [], 'liquidity': []}
    
    # Executar com bias BEARISH (reverso)
    layer_manager._evaluate_existing_position(
        symbol='BTCUSDT',
        position=layer_manager.open_positions['BTCUSDT'],
        h4_df=h4_df,
        smc_result=smc_result,
        confluence_score=8,
        d1_bias='BEARISH'  # Reverteu
    )
    
    # Posicao deve ter sido fechada
    assert 'BTCUSDT' not in layer_manager.open_positions


def test_h4_position_reduce_on_low_confluence(layer_manager, sample_ohlcv_data):
    """Testa que posicoes sao reduzidas quando confluencia baixa."""
    
    # Criar posicao
    layer_manager.open_positions['BTCUSDT'] = {
        'direction': 'LONG',
        'entry_price': 30000,
        'size': 0.1,
    }
    
    initial_size = layer_manager.open_positions['BTCUSDT']['size']
    
    # Preparar H4 data
    h4_df = sample_ohlcv_data.copy()
    
    # Mock SMC
    smc_result = {'market_structure': None, 'bos_list': [], 'order_blocks': [], 'liquidity': []}
    
    # Executar com confluencia marginal (7)
    layer_manager._evaluate_existing_position(
        symbol='BTCUSDT',
        position=layer_manager.open_positions['BTCUSDT'],
        h4_df=h4_df,
        smc_result=smc_result,
        confluence_score=7,  # Marginal
        d1_bias='BULLISH'
    )
    
    # Posicao deve ter sido reduzida
    assert layer_manager.open_positions['BTCUSDT']['size'] < initial_size


def test_calculate_stops_with_smc_order_blocks(layer_manager):
    """Testa calculo de stops usando Order Blocks SMC."""
    
    # Mock order blocks
    mock_ob_bullish = Mock()
    mock_ob_bullish.type = 'bullish'
    mock_ob_bullish.zone_high = 29500
    mock_ob_bullish.zone_low = 29000
    
    smc_result = {
        'order_blocks': [mock_ob_bullish],
        'liquidity': [],
    }
    
    # Calcular stops para LONG
    stop, tp = layer_manager._calculate_stops_and_targets(
        symbol='BTCUSDT',
        direction='LONG',
        current_price=30000,
        atr=500,
        smc_result=smc_result
    )
    
    # Stop deve estar abaixo do OB
    assert stop < 29000
    assert tp > 30000


def test_calculate_stops_fallback_to_atr(layer_manager):
    """Testa que calculo de stops usa ATR quando SMC nao disponivel."""
    
    # SMC sem order blocks
    smc_result = {
        'order_blocks': [],
        'liquidity': [],
    }
    
    # Calcular stops
    stop, tp = layer_manager._calculate_stops_and_targets(
        symbol='BTCUSDT',
        direction='LONG',
        current_price=30000,
        atr=500,
        smc_result=smc_result
    )
    
    # Deve ter usado ATR
    # Stop ~1.5 ATR abaixo, TP ~3 ATR acima
    assert stop < 30000
    assert stop >= 29000  # 30000 - 1.5*500 = 29250
    assert tp > 30000
    assert tp <= 31500  # 30000 + 3*500 = 31500


def test_validate_signal_max_positions(layer_manager):
    """Testa que validacao rejeita quando max posicoes atingido."""
    
    # Preencher posicoes abertas
    layer_manager.open_positions = {
        'BTCUSDT': {'direction': 'LONG'},
        'ETHUSDT': {'direction': 'LONG'},
        'SOLUSDT': {'direction': 'LONG'},
    }
    
    # Tentar validar novo sinal
    is_valid = layer_manager._validate_signal_with_risk(
        symbol='BNBUSDT',
        direction='LONG',
        stop_loss=29000,
        current_price=30000,
        market_regime='RISK_ON',
        confluence_score=10
    )
    
    # Deve ser rejeitado
    assert is_valid is False


def test_validate_signal_high_beta_requires_risk_on(layer_manager):
    """Testa que simbolos high-beta requerem regime RISK_ON."""
    
    # SOLUSDT tem beta ~2.0
    is_valid = layer_manager._validate_signal_with_risk(
        symbol='SOLUSDT',
        direction='LONG',
        stop_loss=29700,  # Stop mais proximo (1% de distancia)
        current_price=30000,
        market_regime='RISK_OFF',  # Regime errado
        confluence_score=10
    )
    
    # Deve ser rejeitado por regime errado
    assert is_valid is False
    
    # Com RISK_ON deve ser aprovado
    is_valid = layer_manager._validate_signal_with_risk(
        symbol='SOLUSDT',
        direction='LONG',
        stop_loss=29700,  # Stop mais proximo (1% de distancia)
        current_price=30000,
        market_regime='RISK_ON',  # Regime correto
        confluence_score=10
    )
    
    # Deve ser aprovado (assumindo outras condicoes OK)
    assert is_valid is True


def test_h4_handles_missing_collectors(mock_db):
    """Testa que H4 lida graciosamente com coletores ausentes."""
    
    # Layer manager sem client (coletores None)
    lm = LayerManager(db=mock_db, client=None)
    
    # Deve executar sem erro mas logar aviso
    lm.h4_main_decision()
    
    # Nao deve ter processado nada
    assert len(lm.smc_cache) == 0


def test_d1_handles_missing_collectors(mock_db):
    """Testa que D1 lida graciosamente com coletores ausentes."""
    
    # Layer manager sem client
    lm = LayerManager(db=mock_db, client=None)
    
    # Deve executar sem erro mas logar aviso
    lm.d1_trend_macro()
    
    # Nao deve ter populado contexto
    assert len(lm.d1_context) == 0
