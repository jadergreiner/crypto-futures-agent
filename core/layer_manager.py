"""
Layer Manager - Gerencia estado e execução condicional das camadas.
"""

import logging
import math
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from data.collector import BinanceCollector
from data.sentiment_collector import SentimentCollector
from data.macro_collector import MacroCollector
from indicators.technical import TechnicalIndicators
from indicators.smc import SmartMoneyConcepts
from indicators.multi_timeframe import MultiTimeframeAnalysis
from indicators.features import FeatureEngineer
from agent.risk_manager import RiskManager
from config.symbols import ALL_SYMBOLS
from config.risk_params import RISK_PARAMS
from config.execution_config import AUTHORIZED_SYMBOLS

logger = logging.getLogger(__name__)

# Constants for SMC structure types
SMC_BULLISH = "bullish"
SMC_BEARISH = "bearish"

# Constants for liquidity types
LIQUIDITY_BSL = "Buy Side Liquidity"
LIQUIDITY_SSL = "Sell Side Liquidity"

# Default capital for position sizing (TODO: replace with portfolio manager)
DEFAULT_CAPITAL = 10000


class LayerManager:
    """
    Gerencia estado do agente e execução condicional das camadas.
    Rastreia posições, sinais pendentes e decide quando executar cada layer.
    """

    def __init__(self, db=None, client=None):
        """
        Inicializa layer manager.

        Args:
            db: DatabaseManager (opcional)
            client: Binance SDK client (opcional)
        """
        self.db = db
        self.client = client
        self.agent_state = {}  # Estado por símbolo
        self.pending_signals = {}  # Sinais pendentes por símbolo
        self.open_positions = {}  # Posições abertas por símbolo
        self.last_heartbeat = None

        # D1 context storage - populated by Layer 5
        self.d1_context = {}  # Dict[symbol, Dict[str, Any]]

        # Feature history for RL training
        self.feature_history = {}  # Dict[symbol, List[np.ndarray]]

        # SMC cache for recent analysis
        self.smc_cache = {}  # Dict[symbol, Dict[str, Any]]
        self._symbol_precision_cache = {}  # Cache de precision por símbolo
        self.authorized_symbols = set(AUTHORIZED_SYMBOLS)

        # Initialize collectors if client is provided
        if client:
            self.binance_collector = BinanceCollector(client)
            self.sentiment_collector = SentimentCollector(client)
        else:
            self.binance_collector = None
            self.sentiment_collector = None

        # Initialize macro collector (no client needed)
        self.macro_collector = MacroCollector()

        # Initialize risk manager
        self.risk_manager = RiskManager()

        logger.info("Layer Manager initialized with collectors and risk manager")

    def has_open_positions(self) -> bool:
        """Verifica se há posições abertas."""
        return len(self.open_positions) > 0

    def should_execute_h1(self) -> bool:
        """Verifica se deve executar Layer 3 (H1)."""
        return len(self.pending_signals) > 0 or len(self.open_positions) > 0

    def register_signal(self, symbol: str, direction: str, score: int,
                       stop: float, tp: float, size: float,
                       entry_price: Optional[float] = None,
                       signal_id: Optional[int] = None,
                       order_id: Optional[str] = None,
                       execution_mode: str = 'PENDING') -> None:
        """
        Registra um sinal pendente de entrada.

        Args:
            symbol: Símbolo
            direction: "LONG" ou "SHORT"
            score: Score de confluência
            stop: Stop loss
            tp: Take profit
            size: Tamanho da posição
        """
        self.pending_signals[symbol] = {
            'direction': direction,
            'score': score,
            'stop': stop,
            'tp': tp,
            'size': size,
            'entry_price': entry_price,
            'signal_id': signal_id,
            'order_id': order_id,
            'execution_mode': execution_mode,
            'timestamp': datetime.now(timezone.utc),
            'm15_cycles_elapsed': 0,
            'h1_candles_elapsed': 0,
            'mfe_pct': 0.0,
            'mae_pct': 0.0,
        }

        self.agent_state[symbol] = 'pending_entry'

        logger.info(f"Signal registered: {symbol} {direction}, score={score}")

    def _extract_data(self, response):
        """Extrai payload de resposta da API do SDK Binance."""
        if response is None:
            return None
        if hasattr(response, 'data'):
            data = response.data
            if callable(data):
                data = data()
            return data
        return response

    def _get_symbol_precision_info(self, symbol: str) -> Dict[str, Any]:
        """Obtém precision de preço/quantidade para ordens LIMIT."""
        if symbol in self._symbol_precision_cache:
            return self._symbol_precision_cache[symbol]

        default_info = {
            'quantity_precision': 8,
            'price_precision': 8,
            'tick_size': None,
        }

        if not self.client:
            self._symbol_precision_cache[symbol] = default_info
            return default_info

        try:
            response = self.client.rest_api.exchange_information()
            data = self._extract_data(response)
            symbols = None

            if hasattr(data, 'symbols'):
                symbols = data.symbols
            elif isinstance(data, dict):
                symbols = data.get('symbols')

            if not symbols:
                self._symbol_precision_cache[symbol] = default_info
                return default_info

            for symbol_info in symbols:
                if isinstance(symbol_info, dict):
                    symbol_name = symbol_info.get('symbol')
                    quantity_precision = symbol_info.get('quantityPrecision', 8)
                    price_precision = symbol_info.get('pricePrecision', 8)
                    filters = symbol_info.get('filters', [])
                else:
                    symbol_name = getattr(symbol_info, 'symbol', None)
                    quantity_precision = getattr(symbol_info, 'quantity_precision', 8)
                    price_precision = getattr(symbol_info, 'price_precision', 8)
                    filters = getattr(symbol_info, 'filters', [])

                if symbol_name != symbol:
                    continue

                tick_size = None
                for f in filters or []:
                    if isinstance(f, dict):
                        if f.get('filterType') == 'PRICE_FILTER':
                            tick_size = float(f.get('tickSize', 0) or 0)
                            break
                    else:
                        if getattr(f, 'filter_type', None) == 'PRICE_FILTER':
                            tick_size = float(getattr(f, 'tick_size', 0) or 0)
                            break

                info = {
                    'quantity_precision': int(quantity_precision) if quantity_precision is not None else 8,
                    'price_precision': int(price_precision) if price_precision is not None else 8,
                    'tick_size': tick_size if tick_size and tick_size > 0 else None,
                }
                self._symbol_precision_cache[symbol] = info
                return info
        except Exception as e:
            logger.warning(f"Falha ao obter precision para {symbol}: {e}")

        self._symbol_precision_cache[symbol] = default_info
        return default_info

    def _round_quantity(self, symbol: str, quantity: float) -> float:
        """Trunca quantidade para precision do símbolo."""
        precision = self._get_symbol_precision_info(symbol)['quantity_precision']
        multiplier = 10 ** precision
        return math.floor(quantity * multiplier) / multiplier

    def _round_price(self, symbol: str, price: float, direction: str) -> float:
        """Ajusta preço para tick/precision respeitando direção da entrada."""
        info = self._get_symbol_precision_info(symbol)
        tick_size = info.get('tick_size')

        if tick_size:
            if direction == 'LONG':
                return math.floor(price / tick_size) * tick_size
            return math.ceil(price / tick_size) * tick_size

        price_precision = info.get('price_precision', 8)
        return round(price, price_precision)

    def _calculate_strategic_entry_price(
        self,
        direction: str,
        current_price: float,
        atr: float,
        smc_result: Dict[str, Any]
    ) -> float:
        """Calcula preço de entrada posicionada usando regiões estruturais SMC."""
        order_blocks = smc_result.get('order_blocks', [])
        fvgs = smc_result.get('fvgs', [])

        if direction == 'LONG':
            bullish_obs = [ob for ob in order_blocks if ob.type == SMC_BULLISH and ob.zone_high < current_price]
            if bullish_obs:
                nearest = max(bullish_obs, key=lambda ob: ob.zone_high)
                return (nearest.zone_low + nearest.zone_high) / 2

            bullish_fvgs = [fvg for fvg in fvgs if fvg.type == SMC_BULLISH and fvg.zone_high < current_price]
            if bullish_fvgs:
                nearest = max(bullish_fvgs, key=lambda fvg: fvg.zone_high)
                return (nearest.zone_low + nearest.zone_high) / 2

            return current_price - (0.25 * atr)

        bearish_obs = [ob for ob in order_blocks if ob.type == SMC_BEARISH and ob.zone_low > current_price]
        if bearish_obs:
            nearest = min(bearish_obs, key=lambda ob: ob.zone_low)
            return (nearest.zone_low + nearest.zone_high) / 2

        bearish_fvgs = [fvg for fvg in fvgs if fvg.type == SMC_BEARISH and fvg.zone_low > current_price]
        if bearish_fvgs:
            nearest = min(bearish_fvgs, key=lambda fvg: fvg.zone_low)
            return (nearest.zone_low + nearest.zone_high) / 2

        return current_price + (0.25 * atr)

    def _build_trade_signal_payload(
        self,
        symbol: str,
        direction: str,
        confluence_score: int,
        entry_price: float,
        current_price: float,
        stop_loss: float,
        take_profit: float,
        position_size: float,
        h4_last_row: pd.Series,
        smc_result: Dict[str, Any],
        sentiment: Dict[str, Any],
        d1_bias: str,
        market_regime: str,
        execution_mode: str,
    ) -> Dict[str, Any]:
        """Monta payload completo para persistência em trade_signals."""
        risk_distance = abs(entry_price - stop_loss)
        tp1 = entry_price + risk_distance if direction == 'LONG' else entry_price - risk_distance
        tp2 = entry_price + (1.5 * risk_distance) if direction == 'LONG' else entry_price - (1.5 * risk_distance)
        tp3 = take_profit

        rr_ratio = None
        if risk_distance > 0:
            rr_ratio = abs(tp3 - entry_price) / risk_distance

        order_blocks = smc_result.get('order_blocks', [])
        fvgs = smc_result.get('fvgs', [])
        liquidity = smc_result.get('liquidity', [])
        bos_list = smc_result.get('bos_list', [])
        choch_list = smc_result.get('choch_list', [])
        market_structure = smc_result.get('market_structure')
        premium_discount = smc_result.get('premium_discount')

        nearest_ob_distance_pct = None
        if order_blocks:
            nearest_ob_distance_pct = min(
                abs(((ob.zone_low + ob.zone_high) / 2) - entry_price) / entry_price * 100
                for ob in order_blocks
            )

        nearest_fvg_distance_pct = None
        if fvgs:
            nearest_fvg_distance_pct = min(
                abs(((fvg.zone_low + fvg.zone_high) / 2) - entry_price) / entry_price * 100
                for fvg in fvgs
            )

        liquidity_above_pct = None
        liquidity_below_pct = None
        if liquidity:
            above = [((liq.price - entry_price) / entry_price) * 100 for liq in liquidity if liq.price > entry_price]
            below = [((entry_price - liq.price) / entry_price) * 100 for liq in liquidity if liq.price < entry_price]
            liquidity_above_pct = min(above) if above else None
            liquidity_below_pct = min(below) if below else None

        ema_alignment_score = h4_last_row.get('ema_alignment_score', 0)
        if not pd.isna(ema_alignment_score):
            if ema_alignment_score > 0:
                h4_trend = 'BULLISH'
            elif ema_alignment_score < 0:
                h4_trend = 'BEARISH'
            else:
                h4_trend = 'NEUTRO'
        else:
            h4_trend = 'NEUTRO'

        h1_trend = 'NEUTRO'
        if market_structure:
            if market_structure.type.value == SMC_BULLISH:
                h1_trend = 'BULLISH'
            elif market_structure.type.value == SMC_BEARISH:
                h1_trend = 'BEARISH'

        confluence_details = {
            'strategy': 'positioned_entry_smc',
            'score': confluence_score,
            'direction': direction,
            'entry_vs_mark_pct': ((entry_price - current_price) / current_price) * 100,
        }

        return {
            'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000),
            'symbol': symbol,
            'direction': direction,
            'entry_price': float(entry_price),
            'stop_loss': float(stop_loss),
            'take_profit_1': float(tp1),
            'take_profit_2': float(tp2),
            'take_profit_3': float(tp3),
            'position_size_suggested': float(position_size),
            'risk_pct': float(RISK_PARAMS['max_risk_per_trade_pct'] * 100),
            'risk_reward_ratio': float(rr_ratio) if rr_ratio is not None else None,
            'leverage_suggested': int(RISK_PARAMS.get('max_leverage', 10)),
            'confluence_score': float(confluence_score),
            'confluence_details': json.dumps(confluence_details, ensure_ascii=False),
            'rsi_14': h4_last_row.get('rsi_14'),
            'ema_17': h4_last_row.get('ema_17'),
            'ema_34': h4_last_row.get('ema_34'),
            'ema_72': h4_last_row.get('ema_72'),
            'ema_144': h4_last_row.get('ema_144'),
            'macd_line': h4_last_row.get('macd_line'),
            'macd_signal': h4_last_row.get('macd_signal'),
            'macd_histogram': h4_last_row.get('macd_histogram'),
            'bb_upper': h4_last_row.get('bb_upper'),
            'bb_lower': h4_last_row.get('bb_lower'),
            'bb_percent_b': h4_last_row.get('bb_percent_b'),
            'atr_14': h4_last_row.get('atr_14'),
            'adx_14': h4_last_row.get('adx_14'),
            'di_plus': h4_last_row.get('di_plus'),
            'di_minus': h4_last_row.get('di_minus'),
            'market_structure': market_structure.type.value if market_structure else None,
            'bos_recent': 1 if bos_list else 0,
            'choch_recent': 1 if choch_list else 0,
            'nearest_ob_distance_pct': nearest_ob_distance_pct,
            'nearest_fvg_distance_pct': nearest_fvg_distance_pct,
            'premium_discount_zone': premium_discount.zone.value if premium_discount else None,
            'liquidity_above_pct': liquidity_above_pct,
            'liquidity_below_pct': liquidity_below_pct,
            'funding_rate': sentiment.get('funding_rate'),
            'long_short_ratio': sentiment.get('long_short_ratio'),
            'open_interest_change_pct': sentiment.get('open_interest_change_pct'),
            'fear_greed_value': sentiment.get('fear_greed_value'),
            'd1_bias': d1_bias,
            'h4_trend': h4_trend,
            'h1_trend': h1_trend,
            'market_regime': market_regime,
            'execution_mode': execution_mode,
            'executed_at': None,
            'executed_price': None,
            'execution_slippage_pct': None,
            'status': 'ACTIVE',
        }

    def _place_positioned_entry_order(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        quantity: float,
    ) -> Optional[Dict[str, Any]]:
        """Cria ordem LIMIT de entrada posicionada em região estratégica."""
        if not self.client:
            return None

        side = 'BUY' if direction == 'LONG' else 'SELL'
        adj_price = self._round_price(symbol, entry_price, direction)
        adj_qty = self._round_quantity(symbol, quantity)

        if adj_qty <= 0:
            logger.warning(f"H4: Quantidade inválida para entrada posicionada em {symbol}: {adj_qty}")
            return None

        try:
            response = self.client.rest_api.new_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                quantity=adj_qty,
                price=adj_price,
                time_in_force='GTC',
                recv_window=10000,
            )
            data = self._extract_data(response)
            logger.info(
                f"H4: Ordem posicionada criada para {symbol} {direction} "
                f"({side} {adj_qty} @ {adj_price})"
            )
            return data
        except Exception as e:
            logger.error(f"H4: Falha ao criar ordem posicionada para {symbol}: {e}")
            return None

    def _normalize_order_dict(self, order: Any) -> Dict[str, Any]:
        """Converte ordem da API em dict uniforme para leitura defensiva."""
        if isinstance(order, dict):
            return order

        if order is None:
            return {}

        normalized = {}
        for attr in [
            'order_id', 'symbol', 'status', 'type', 'orig_type', 'side',
            'reduce_only', 'close_position', 'time', 'price', 'orig_qty'
        ]:
            if hasattr(order, attr):
                normalized[attr] = getattr(order, attr)
        return normalized

    def _list_open_orders_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Lista ordens abertas do símbolo com fallback entre métodos do SDK."""
        if not self.client:
            return []

        rest_api = self.client.rest_api
        candidates = [
            'current_all_open_orders',
            'current_open_orders',
            'open_orders',
        ]

        for method_name in candidates:
            method = getattr(rest_api, method_name, None)
            if not callable(method):
                continue
            try:
                response = method(symbol=symbol)
                data = self._extract_data(response)
                if data is None:
                    return []
                if not isinstance(data, list):
                    data = [data]
                return [self._normalize_order_dict(o) for o in data]
            except Exception as e:
                logger.debug(f"H4: Método {method_name} falhou ao listar ordens de {symbol}: {e}")
                continue

        logger.warning(f"H4: Não foi possível listar ordens abertas para {symbol}")
        return []

    def _cancel_order_by_id(self, symbol: str, order_id: Any) -> bool:
        """Cancela ordem por ID usando método disponível no SDK."""
        if not self.client:
            return False

        if order_id in (None, ''):
            return False

        rest_api = self.client.rest_api
        candidates = ['cancel_order']

        for method_name in candidates:
            method = getattr(rest_api, method_name, None)
            if not callable(method):
                continue
            try:
                method(symbol=symbol, order_id=order_id, recv_window=10000)
                return True
            except Exception as e:
                logger.warning(f"H4: Falha ao cancelar ordem {order_id} de {symbol}: {e}")
                return False

        logger.warning("H4: SDK sem método de cancelamento de ordem disponível")
        return False

    def _cancel_existing_entry_orders(self, symbol: str) -> int:
        """Cancela ordens de entrada anteriores (LIMIT) para evitar múltiplas operações no ativo."""
        open_orders = self._list_open_orders_for_symbol(symbol)
        if not open_orders:
            return 0

        cancelled = 0
        for order in open_orders:
            order_type = str(order.get('type') or order.get('orig_type') or '').upper()
            reduce_only = order.get('reduce_only')
            close_position = order.get('close_position')

            # Cancelar apenas ordens de entrada LIMIT (não mexer em proteções STOP/TP)
            if order_type != 'LIMIT':
                continue

            if str(reduce_only).lower() == 'true' or reduce_only is True:
                continue

            if str(close_position).lower() == 'true' or close_position is True:
                continue

            order_id = order.get('order_id') or order.get('orderId')
            if self._cancel_order_by_id(symbol, order_id):
                cancelled += 1

        if cancelled > 0:
            logger.warning(
                f"H4: {cancelled} ordem(ns) LIMIT antiga(s) cancelada(s) para {symbol} antes de nova entrada"
            )
        return cancelled

    def _cancel_stale_active_signals(self, symbol: str) -> int:
        """Cancela sinais ativos anteriores no banco ao substituir por novo setup do mesmo ativo."""
        if not self.db:
            return 0

        cancelled = 0
        try:
            active_signals = self.db.get_active_signals(symbol=symbol)
            for row in active_signals:
                signal_id = row.get('id')
                if not signal_id:
                    continue
                self.db.update_signal_status(
                    signal_id=signal_id,
                    status='CANCELLED',
                    execution_mode='CANCELLED',
                    exit_reason='replaced_by_new_signal',
                )
                cancelled += 1
        except Exception as e:
            logger.warning(f"H4: Falha ao cancelar sinais antigos no DB para {symbol}: {e}")

        if cancelled > 0:
            logger.info(f"H4: {cancelled} sinal(is) ativo(s) antigo(s) cancelado(s) para {symbol}")
        return cancelled

    def _record_signal_evolution(
        self,
        symbol: str,
        signal: Dict[str, Any],
        event_type: Optional[str] = None,
        event_details: Optional[str] = None,
    ) -> None:
        """Persiste snapshot de evolução do sinal para aprendizado contínuo."""
        if not self.db:
            return

        signal_id = signal.get('signal_id')
        if not signal_id:
            return

        current_price = signal.get('entry_price')
        rsi_14 = None
        macd_histogram = None
        bb_percent_b = None
        atr_14 = None
        adx_14 = None
        market_structure = None

        try:
            h1_df = self.binance_collector.fetch_historical(symbol, "1h", days=2)
            if not h1_df.empty:
                h1_df = TechnicalIndicators.calculate_all(h1_df)
                last = h1_df.iloc[-1]
                current_price = float(last['close'])
                rsi_14 = last.get('rsi_14')
                macd_histogram = last.get('macd_histogram')
                bb_percent_b = last.get('bb_percent_b')
                atr_14 = last.get('atr_14')
                adx_14 = last.get('adx_14')

            smc = self.smc_cache.get(symbol, {})
            structure = smc.get('market_structure') if smc else None
            if structure:
                market_structure = structure.type.value
        except Exception as e:
            logger.debug(f"H1: Falha ao coletar snapshot de evolução para {symbol}: {e}")

        if current_price is None:
            return

        entry_price = signal.get('entry_price') or current_price
        stop = signal.get('stop')
        tp = signal.get('tp')
        direction = signal.get('direction', 'LONG')

        if direction == 'LONG':
            unrealized = ((current_price - entry_price) / entry_price) * 100 if entry_price else 0.0
            distance_to_stop_pct = ((current_price - stop) / current_price) * 100 if stop else None
            distance_to_tp1_pct = ((tp - current_price) / current_price) * 100 if tp else None
        else:
            unrealized = ((entry_price - current_price) / entry_price) * 100 if entry_price else 0.0
            distance_to_stop_pct = ((stop - current_price) / current_price) * 100 if stop else None
            distance_to_tp1_pct = ((current_price - tp) / current_price) * 100 if tp else None

        signal['mfe_pct'] = max(signal.get('mfe_pct', 0.0), unrealized)
        signal['mae_pct'] = min(signal.get('mae_pct', 0.0), unrealized)

        payload = {
            'signal_id': signal_id,
            'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000),
            'current_price': float(current_price),
            'unrealized_pnl_pct': float(unrealized),
            'distance_to_stop_pct': distance_to_stop_pct,
            'distance_to_tp1_pct': distance_to_tp1_pct,
            'rsi_14': rsi_14,
            'macd_histogram': macd_histogram,
            'bb_percent_b': bb_percent_b,
            'atr_14': atr_14,
            'adx_14': adx_14,
            'market_structure': market_structure,
            'funding_rate': None,
            'long_short_ratio': None,
            'mfe_pct': signal.get('mfe_pct'),
            'mae_pct': signal.get('mae_pct'),
            'event_type': event_type,
            'event_details': event_details,
        }

        try:
            self.db.insert_signal_evolution(payload)
        except Exception as e:
            logger.warning(f"H1: Falha ao persistir evolução do sinal {signal_id}: {e}")

    def execute_entry(self, symbol: str) -> bool:
        """
        Executa entrada em posição.

        Args:
            symbol: Símbolo

        Returns:
            True se executado com sucesso
        """
        if symbol not in self.pending_signals:
            return False

        signal = self.pending_signals[symbol]

        # Simular execução (em produção, executar via API da Binance)
        logger.info(f"Executing entry: {symbol} {signal['direction']}")

        # Mover para posições abertas
        self.open_positions[symbol] = {
            **signal,
            'entry_timestamp': datetime.now(timezone.utc),
            'entry_price': 0.0  # Seria preço de execução
        }

        # Remover sinal pendente
        del self.pending_signals[symbol]
        self.agent_state[symbol] = 'in_position'

        logger.info(f"Position opened: {symbol}")
        return True

    def cancel_signal(self, symbol: str, reason: str) -> None:
        """
        Cancela sinal pendente.

        Args:
            symbol: Símbolo
            reason: Razão do cancelamento
        """
        if symbol in self.pending_signals:
            del self.pending_signals[symbol]
            self.agent_state[symbol] = 'flat'
            logger.info(f"Signal cancelled for {symbol}: {reason}")

    def close_position(self, symbol: str, reason: str) -> None:
        """
        Fecha posição aberta.

        Args:
            symbol: Símbolo
            reason: Razão do fechamento
        """
        if symbol in self.open_positions:
            position = self.open_positions[symbol]
            logger.info(f"Closing position: {symbol}, reason={reason}")

            # Registrar trade (em produção, calcular PnL real)

            # Remover posição
            del self.open_positions[symbol]
            self.agent_state[symbol] = 'flat'

            logger.info(f"Position closed: {symbol}")

    def heartbeat_check(self) -> None:
        """Layer 1: Heartbeat - Health check."""
        self.last_heartbeat = datetime.now(timezone.utc)

        # Verificar conexões
        # - API Binance
        # - Database
        # - WebSocket

        logger.debug("Heartbeat: OK")

    def risk_management(self) -> None:
        """Layer 2: Gestão de risco para posições abertas."""
        for symbol, position in list(self.open_positions.items()):
            logger.debug(f"Risk check: {symbol}")

            # Verificar stops
            # Atualizar trailing stops
            # Verificar drawdown
            # (Implementação real verificaria via API)

    def h1_timing(self) -> None:
        """Layer 3 (legado): timing de entrada por ciclos M15."""
        # Verificar sinais pendentes
        for symbol, signal in list(self.pending_signals.items()):
            elapsed = int(signal.get('m15_cycles_elapsed', signal.get('h1_candles_elapsed', 0))) + 1
            signal['m15_cycles_elapsed'] = elapsed
            signal['h1_candles_elapsed'] = elapsed

            # Timeout após 12 ciclos de 15 minutos (~3 horas)
            if elapsed >= 12:
                if self.db and signal.get('signal_id'):
                    try:
                        self.db.update_signal_status(
                            signal_id=signal['signal_id'],
                            status='CANCELLED',
                            execution_mode='CANCELLED',
                            exit_reason='timeout_m15'
                        )
                    except Exception as e:
                        logger.warning(f"M15: Falha ao cancelar sinal {symbol} no DB: {e}")
                self.cancel_signal(symbol, "timeout")
                continue

            self._record_signal_evolution(
                symbol=symbol,
                signal=signal,
                event_type='M15_TIMING_CHECK',
                event_details=f"elapsed={elapsed}"
            )

            # Verificar se está na zona de entrada
            # (Implementação real verificaria via SMC)
            logger.debug(f"M15 timing check: {symbol}")

    def h4_main_decision(self) -> None:
        """Layer 4: Decisão principal H4."""
        logger.info("H4: Starting main decision logic")

        if not self.binance_collector:
            logger.error("H4: BinanceCollector not initialized")
            return

        successful_count = 0
        signals_generated = 0
        failed_symbols = []

        for symbol in ALL_SYMBOLS:
            try:
                logger.debug(f"H4: Processing {symbol}")

                # Step 1: Collect fresh H4 data and keep only the latest CLOSED H4 context
                h4_raw_df = self.binance_collector.fetch_historical(symbol, "4h", days=30)
                h4_df = self._filter_last_closed_h4_context(h4_raw_df)
                if h4_df.empty:
                    logger.warning(f"H4: No H4 data for {symbol}")
                    continue

                # Step 2: Collect fresh H1 data for confluence/SMC
                h1_df = self.binance_collector.fetch_historical(symbol, "1h", days=7)
                if h1_df.empty:
                    logger.warning(f"H4: No H1 data for {symbol}")
                    continue

                # Step 3: Collect fresh M15 data for refined timing/entry
                m15_df = self.binance_collector.fetch_historical(symbol, "15m", days=3)
                if m15_df.empty:
                    logger.warning(f"H4: No M15 data for {symbol}")
                    continue

                # Step 4: Calculate H4 technical indicators
                h4_df = TechnicalIndicators.calculate_all(h4_df)
                logger.debug(f"H4: Calculated H4 indicators for {symbol}")

                # Step 5: Calculate SMC on H1 (alignment/confluence)
                smc_result = SmartMoneyConcepts.calculate_all_smc(h1_df)
                self.smc_cache[symbol] = smc_result
                logger.debug(f"H4: Calculated SMC structures for {symbol}")

                # Step 6: Calculate SMC on M15 (timing refinement)
                smc_result_m15 = SmartMoneyConcepts.calculate_all_smc(m15_df)

                # Step 7: Get D1 context
                d1_context = self.d1_context.get(symbol, {})
                d1_bias = d1_context.get('d1_bias', 'NEUTRO')
                market_regime = d1_context.get('market_regime', 'NEUTRO')
                d1_data = d1_context.get('d1_data', pd.DataFrame())

                # Step 8: Get sentiment (from D1 context or fetch fresh)
                sentiment = d1_context.get('sentiment', {})
                if not sentiment:
                    try:
                        sentiment = self.sentiment_collector.fetch_all_sentiment(symbol)
                    except Exception as e:
                        logger.warning(f"H4: Failed to fetch sentiment for {symbol}: {e}")
                        sentiment = {}

                macro = d1_context.get('macro', {})

                # Step 9: Get position state if exists
                position_state = self.open_positions.get(symbol)

                # Step 10: Build observation vector
                try:
                    # Build multi_tf_result from d1_context
                    multi_tf_result = {
                        'd1_bias': d1_bias,
                        'market_regime': market_regime,
                        'correlation_btc': d1_context.get('correlation_btc', 0.0),
                        'beta_btc': d1_context.get('beta_btc', 1.0),
                    }

                    observation = FeatureEngineer.build_observation(
                        symbol=symbol,
                        h1_data=h1_df,
                        h4_data=h4_df,
                        d1_data=d1_data,
                        sentiment=sentiment,
                        macro=macro,
                        smc=smc_result,
                        position_state=position_state,
                        multi_tf_result=multi_tf_result
                    )

                    # Store feature vector for RL training
                    if symbol not in self.feature_history:
                        self.feature_history[symbol] = []
                    self.feature_history[symbol].append(observation)

                    # Keep only last 1000 observations
                    if len(self.feature_history[symbol]) > 1000:
                        self.feature_history[symbol] = self.feature_history[symbol][-1000:]

                    logger.debug(f"H4: Built {len(observation)}-feature observation for {symbol}")
                except Exception as e:
                    logger.warning(f"H4: Failed to build observation for {symbol}: {e}")
                    observation = None

                # Step 11: Calculate confluence score (rule-based)
                confluence_score, signal_direction = self._calculate_confluence_score(
                    symbol=symbol,
                    h4_df=h4_df,
                    d1_bias=d1_bias,
                    market_regime=market_regime,
                    smc_result=smc_result,
                    sentiment=sentiment
                )

                logger.info(f"H4: {symbol} - Confluence: {confluence_score}/14, "
                           f"Direction: {signal_direction}, D1: {d1_bias}, Regime: {market_regime}")

                # Step 12: Determine action based on confluence score
                min_score = RISK_PARAMS['confluence_min_score']

                if confluence_score >= min_score and signal_direction in ['LONG', 'SHORT']:
                    # We have a valid signal

                    # Get current M15 price and H4 ATR (closed-candle context)
                    current_price = m15_df['close'].iloc[-1]
                    atr = h4_df['atr_14'].iloc[-1]

                    if pd.isna(atr) or atr == 0:
                        logger.warning(f"H4: Invalid ATR for {symbol}, skipping")
                        continue

                    # Step 13: Calculate stop loss and take profit
                    stop_loss, take_profit = self._calculate_stops_and_targets(
                        symbol=symbol,
                        direction=signal_direction,
                        current_price=current_price,
                        atr=atr,
                        smc_result=smc_result
                    )

                    # Step 12: Validate with risk rules
                    if self._validate_signal_with_risk(
                        symbol=symbol,
                        direction=signal_direction,
                        stop_loss=stop_loss,
                        current_price=current_price,
                        market_regime=market_regime,
                        confluence_score=confluence_score
                    ):
                        # Calculate position size
                        stop_distance_pct = abs(current_price - stop_loss) / current_price * 100
                        position_size = self.risk_manager.calculate_position_size(
                            capital=DEFAULT_CAPITAL,
                            entry_price=current_price,
                            stop_distance_pct=stop_distance_pct
                        )

                        # Adjust size by confluence score
                        position_size = self.risk_manager.adjust_size_by_confluence(
                            position_size, confluence_score
                        )

                        if symbol in self.pending_signals:
                            logger.info(f"H4: {symbol} já possui sinal pendente, mantendo ordem posicionada existente")
                            continue

                        strategic_entry = self._calculate_strategic_entry_price(
                            direction=signal_direction,
                            current_price=current_price,
                            atr=atr,
                            smc_result=smc_result_m15,
                        )

                        # Garantir coerência geométrica entre entry/stop/tp
                        if signal_direction == 'LONG' and not (stop_loss < strategic_entry < take_profit):
                            strategic_entry = current_price
                        if signal_direction == 'SHORT' and not (take_profit < strategic_entry < stop_loss):
                            strategic_entry = current_price

                        strategic_entry = self._round_price(symbol, strategic_entry, signal_direction)

                        execution_mode = 'PENDING'
                        signal_id = None

                        # Proteção de risco: nunca empilhar múltiplas entradas no mesmo ativo
                        # (especialmente após restart, quando pending_signals em memória pode estar vazio)
                        cancelled_orders = 0
                        if symbol in self.authorized_symbols and self.client:
                            cancelled_orders = self._cancel_existing_entry_orders(symbol)

                        cancelled_signals = self._cancel_stale_active_signals(symbol)

                        # Persist signal no DB para aprendizado
                        if self.db:
                            payload = self._build_trade_signal_payload(
                                symbol=symbol,
                                direction=signal_direction,
                                confluence_score=confluence_score,
                                entry_price=strategic_entry,
                                current_price=current_price,
                                stop_loss=stop_loss,
                                take_profit=take_profit,
                                position_size=position_size,
                                h4_last_row=h4_df.iloc[-1],
                                smc_result=smc_result,
                                sentiment=sentiment,
                                d1_bias=d1_bias,
                                market_regime=market_regime,
                                execution_mode=execution_mode,
                            )
                            try:
                                signal_id = self.db.insert_trade_signal(payload)
                            except Exception as e:
                                logger.warning(f"H4: Falha ao persistir trade_signal de {symbol}: {e}")

                        order_id = None
                        if symbol in self.authorized_symbols and self.client:
                            order_response = self._place_positioned_entry_order(
                                symbol=symbol,
                                direction=signal_direction,
                                entry_price=strategic_entry,
                                quantity=position_size,
                            )
                            if order_response:
                                execution_mode = 'AUTOTRADE_LIMIT'
                                order_id = order_response.get('orderId') or order_response.get('order_id')
                                executed_price = float(
                                    order_response.get('price')
                                    or order_response.get('avgPrice')
                                    or order_response.get('avg_price')
                                    or strategic_entry
                                )
                                if self.db and signal_id:
                                    try:
                                        slippage_pct = ((executed_price - strategic_entry) / strategic_entry) * 100
                                        self.db.update_signal_execution(
                                            signal_id=signal_id,
                                            executed_at=int(datetime.now(timezone.utc).timestamp() * 1000),
                                            executed_price=executed_price,
                                            execution_mode=execution_mode,
                                            execution_slippage_pct=slippage_pct,
                                        )
                                    except Exception as e:
                                        logger.warning(f"H4: Falha ao atualizar execução do sinal {signal_id}: {e}")
                            else:
                                logger.warning(f"H4: Ordem posicionada não criada para {symbol}; sinal ficará pendente")
                        else:
                            logger.info(f"H4: {symbol} fora da whitelist/autotrade indisponível; sinal ficará pendente")

                        # Step 14: Register signal em memória
                        self.register_signal(
                            symbol=symbol,
                            direction=signal_direction,
                            score=confluence_score,
                            stop=stop_loss,
                            tp=take_profit,
                            size=position_size,
                            entry_price=strategic_entry,
                            signal_id=signal_id,
                            order_id=order_id,
                            execution_mode=execution_mode,
                        )

                        # Snapshot inicial da evolução
                        self._record_signal_evolution(
                            symbol=symbol,
                            signal=self.pending_signals[symbol],
                            event_type='SIGNAL_REGISTERED',
                            event_details=(
                                f"mode={execution_mode};score={confluence_score};"
                                f"cancelled_orders={cancelled_orders};cancelled_signals={cancelled_signals}"
                            )
                        )

                        signals_generated += 1
                        logger.info(
                            f"H4: [OK] Signal positioned for {symbol} {signal_direction} "
                            f"(score={confluence_score}, entry={strategic_entry:.6f}, size={position_size:.4f}, mode={execution_mode})"
                        )
                    else:
                        logger.info(f"H4: Signal for {symbol} rejected by risk validation")

                # Step 14: Handle existing positions
                if position_state:
                    self._evaluate_existing_position(
                        symbol=symbol,
                        position=position_state,
                        h4_df=h4_df,
                        smc_result=smc_result,
                        confluence_score=confluence_score,
                        d1_bias=d1_bias
                    )

                # Step 15: Persist H4 indicators to database
                if self.db:
                    try:
                        indicator_records = []
                        for idx, row in h4_df.iterrows():
                            record = {
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
                                'di_minus': row.get('di_minus'),
                            }
                            indicator_records.append(record)

                        if indicator_records:
                            self.db.insert_indicators(indicator_records)
                            logger.debug(f"H4: Persisted {len(indicator_records)} H4 indicators for {symbol}")
                    except Exception as e:
                        logger.warning(f"H4: Failed to persist H4 indicators for {symbol}: {e}")

                successful_count += 1

            except Exception as e:
                logger.error(f"H4: Failed to process {symbol}: {e}")
                failed_symbols.append(symbol)
                continue

        logger.info(f"H4: Decision complete - {successful_count}/{len(ALL_SYMBOLS)} processed, "
                   f"{signals_generated} signals generated")
        if failed_symbols:
            logger.warning(f"H4: Failed symbols: {', '.join(failed_symbols)}")

    def _filter_last_closed_h4_context(self, h4_df: pd.DataFrame) -> pd.DataFrame:
        """Retorna dataframe H4 garantindo que a última barra usada esteja fechada."""
        if h4_df is None or h4_df.empty or 'timestamp' not in h4_df.columns:
            return pd.DataFrame()

        filtered = h4_df.sort_values('timestamp').reset_index(drop=True).copy()
        if len(filtered) == 1:
            return filtered

        try:
            last_open_ts = int(filtered['timestamp'].iloc[-1])
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            h4_interval_ms = 4 * 60 * 60 * 1000

            # Se ainda não fechou o candle H4 atual, remover última linha.
            if now_ms < (last_open_ts + h4_interval_ms):
                return filtered.iloc[:-1].reset_index(drop=True)
        except Exception:
            # Em caso de parsing inesperado, manter dataframe original ordenado.
            return filtered

        return filtered

    def _calculate_confluence_score(
        self,
        symbol: str,
        h4_df: pd.DataFrame,
        d1_bias: str,
        market_regime: str,
        smc_result: Dict[str, Any],
        sentiment: Dict[str, Any]
    ) -> tuple:
        """
        Calculate confluence score using rule-based approach.

        Returns:
            Tuple of (score, direction) where score is 0-14 and direction is LONG/SHORT/NONE
        """
        if h4_df.empty:
            return 0, "NONE"

        last = h4_df.iloc[-1]
        score = 0
        bullish_score = 0
        bearish_score = 0

        # 1. D1 Bias alignment (2 points)
        if d1_bias == "BULLISH":
            bullish_score += 2
        elif d1_bias == "BEARISH":
            bearish_score += 2

        # 2. SMC Structure (2 points)
        market_structure = smc_result.get('market_structure')
        if market_structure:
            if market_structure.type.value == SMC_BULLISH:
                bullish_score += 2
            elif market_structure.type.value == SMC_BEARISH:
                bearish_score += 2

        # 3. EMA Alignment (2 points)
        ema_score = last.get('ema_alignment_score', 0)
        if not pd.isna(ema_score):
            if ema_score >= 4:
                bullish_score += 2
            elif ema_score <= -4:
                bearish_score += 2

        # 4. RSI (1 point) - not overbought for LONG, not oversold for SHORT
        rsi = last.get('rsi_14', 50)
        if not pd.isna(rsi):
            if 40 <= rsi <= 70:  # Good for LONG
                bullish_score += 1
            if 30 <= rsi <= 60:  # Good for SHORT
                bearish_score += 1

        # 5. ADX > 25 (trending) (1 point)
        adx = last.get('adx_14', 0)
        if not pd.isna(adx) and adx > 25:
            bullish_score += 1
            bearish_score += 1

        # 6. BOS confirmation (2 points)
        bos_list = smc_result.get('bos_list', [])
        if bos_list:
            last_bos = bos_list[-1]
            if last_bos.direction == SMC_BULLISH:
                bullish_score += 2
            elif last_bos.direction == SMC_BEARISH:
                bearish_score += 2

        # 7. Funding rate not extreme against direction (2 points)
        funding_rate = sentiment.get('funding_rate', 0)
        if funding_rate is not None and not pd.isna(funding_rate):
            # Convert to percentage if needed (funding rate is usually in decimal)
            funding_pct = funding_rate * 100
            threshold = RISK_PARAMS['extreme_funding_rate_threshold']

            if funding_pct < threshold:  # Not extremely positive (good for LONG)
                bullish_score += 2
            if funding_pct > -threshold:  # Not extremely negative (good for SHORT)
                bearish_score += 2
        else:
            # If no funding data, give neutral points
            bullish_score += 1
            bearish_score += 1

        # 8. Market regime (2 points)
        if market_regime == "RISK_ON":
            bullish_score += 2
        elif market_regime == "RISK_OFF":
            bearish_score += 2

        # Determine direction and final score
        if bullish_score > bearish_score and bullish_score >= 8:
            return bullish_score, "LONG"
        elif bearish_score > bullish_score and bearish_score >= 8:
            return bearish_score, "SHORT"
        else:
            return max(bullish_score, bearish_score), "NONE"

    def _calculate_stops_and_targets(
        self,
        symbol: str,
        direction: str,
        current_price: float,
        atr: float,
        smc_result: Dict[str, Any]
    ) -> tuple:
        """Calculate stop loss and take profit prices."""

        # Try to use SMC Order Blocks for structural stops
        order_blocks = smc_result.get('order_blocks', [])
        stop_loss = None
        take_profit = None

        if order_blocks:
            if direction == "LONG":
                # Find nearest bullish OB below current price
                bullish_obs = [ob for ob in order_blocks
                             if ob.type == SMC_BULLISH and ob.zone_high < current_price]
                if bullish_obs:
                    nearest_ob = max(bullish_obs, key=lambda x: x.zone_high)
                    stop_loss = nearest_ob.zone_low - (0.5 * atr)  # 0.5 ATR buffer
            else:  # SHORT
                # Find nearest bearish OB above current price
                bearish_obs = [ob for ob in order_blocks
                             if ob.type == SMC_BEARISH and ob.zone_low > current_price]
                if bearish_obs:
                    nearest_ob = min(bearish_obs, key=lambda x: x.zone_low)
                    stop_loss = nearest_ob.zone_high + (0.5 * atr)  # 0.5 ATR buffer

        # Fallback to ATR-based stop if SMC not available
        if stop_loss is None:
            stop_loss = self.risk_manager.calculate_stop_loss(
                current_price, atr, direction, multiplier=1.5
            )

        # Take profit using liquidity levels (BSL/SSL) or ATR
        liquidity = smc_result.get('liquidity', [])
        if liquidity:
            if direction == "LONG":
                # Target Buy Side Liquidity (highs)
                bsl = [liq for liq in liquidity if liq.type.value == LIQUIDITY_BSL]
                if bsl:
                    nearest_bsl = min(bsl, key=lambda x: abs(x.price - current_price))
                    if nearest_bsl.price > current_price:
                        take_profit = nearest_bsl.price
            else:  # SHORT
                # Target Sell Side Liquidity (lows)
                ssl = [liq for liq in liquidity if liq.type.value == LIQUIDITY_SSL]
                if ssl:
                    nearest_ssl = min(ssl, key=lambda x: abs(x.price - current_price))
                    if nearest_ssl.price < current_price:
                        take_profit = nearest_ssl.price

        # Fallback to ATR-based TP if SMC not available
        if take_profit is None:
            take_profit = self.risk_manager.calculate_take_profit(
                current_price, atr, direction, multiplier=3.0
            )

        return stop_loss, take_profit

    def _validate_signal_with_risk(
        self,
        symbol: str,
        direction: str,
        stop_loss: float,
        current_price: float,
        market_regime: str,
        confluence_score: int
    ) -> bool:
        """Validate signal against risk management rules."""

        # Check if max positions reached
        if len(self.open_positions) >= RISK_PARAMS['max_simultaneous_positions']:
            logger.debug(f"H4: Max positions reached ({len(self.open_positions)})")
            return False

        # Check stop distance
        stop_distance_pct = abs(current_price - stop_loss) / current_price
        if stop_distance_pct > RISK_PARAMS['max_stop_distance_pct']:
            logger.debug(f"H4: Stop distance too wide ({stop_distance_pct*100:.2f}%)")
            return False

        # For high-beta symbols, only trade in RISK_ON
        from config.symbols import SYMBOLS
        symbol_info = SYMBOLS.get(symbol, {})
        beta = symbol_info.get('beta_estimado', 1.0)

        if beta >= 2.0 and market_regime != "RISK_ON":
            logger.debug(f"H4: High-beta {symbol} requires RISK_ON regime")
            return False

        # Check correlation with existing positions
        for existing_symbol, position in self.open_positions.items():
            if existing_symbol == symbol:
                continue

            # Check if both symbols have correlation data
            existing_d1 = self.d1_context.get(existing_symbol, {})
            current_d1 = self.d1_context.get(symbol, {})

            # Simple check: don't open same direction if highly correlated
            if position['direction'] == direction:
                existing_corr = existing_d1.get('correlation_btc', 0)
                current_corr = current_d1.get('correlation_btc', 0)

                # If both are highly correlated to BTC (>0.8), they're likely correlated
                if existing_corr > 0.8 and current_corr > 0.8:
                    logger.debug(f"H4: High correlation with existing position {existing_symbol}")
                    return False

        return True

    def _evaluate_existing_position(
        self,
        symbol: str,
        position: Dict[str, Any],
        h4_df: pd.DataFrame,
        smc_result: Dict[str, Any],
        confluence_score: int,
        d1_bias: str
    ) -> None:
        """Re-evaluate existing position and decide HOLD/REDUCE/CLOSE."""

        direction = position.get('direction', 'LONG')
        entry_price = position.get('entry_price', 0)

        if entry_price == 0:
            logger.warning(f"H4: Invalid entry price for {symbol} position")
            return

        current_price = h4_df['close'].iloc[-1]

        # Calculate unrealized PnL
        if direction == "LONG":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        logger.info(f"H4: Position {symbol} {direction} - PnL: {pnl_pct:.2f}%, "
                   f"Confluence: {confluence_score}/14, D1: {d1_bias}")

        # Decision logic
        close_position = False
        reduce_position = False

        # Close if D1 bias reverses
        if (direction == "LONG" and d1_bias == "BEARISH") or \
           (direction == "SHORT" and d1_bias == "BULLISH"):
            logger.info(f"H4: D1 bias reversed for {symbol}, closing position")
            close_position = True

        # Close if confluence drops below threshold
        elif confluence_score < 6:
            logger.info(f"H4: Confluence too low for {symbol} ({confluence_score}/14), closing")
            close_position = True

        # Reduce if confluence marginal
        elif confluence_score < 8:
            logger.info(f"H4: Marginal confluence for {symbol}, reducing 50%")
            reduce_position = True

        # Execute action
        if close_position:
            self.close_position(symbol, "confluence_breakdown")
        elif reduce_position:
            # Update position size (reduce by 50%)
            position['size'] = position.get('size', 0) * 0.5
            logger.info(f"H4: Reduced position size for {symbol} by 50%")

    def d1_trend_macro(self) -> None:
        """Layer 5: Análise D1 e macro."""
        logger.info("D1: Starting trend and macro analysis")

        if not self.binance_collector:
            logger.error("D1: BinanceCollector not initialized")
            return

        # Step 1: Collect macro data once for all symbols
        try:
            macro_data = self.macro_collector.fetch_all_macro()
            logger.info(f"D1: Collected macro data - Fear&Greed: {macro_data.get('fear_greed_value')}, "
                       f"BTC Dom: {macro_data.get('btc_dominance')}")

            # Persist macro data to database
            if self.db:
                try:
                    self.db.insert_macro(macro_data)
                except Exception as e:
                    logger.warning(f"D1: Failed to persist macro data to DB: {e}")
        except Exception as e:
            logger.error(f"D1: Failed to collect macro data: {e}")
            macro_data = {}

        # Step 2: Collect BTC D1 data for correlation analysis
        btc_d1_df = None
        try:
            btc_d1_df = self.binance_collector.fetch_historical("BTCUSDT", "1d", days=30)
            if not btc_d1_df.empty:
                btc_d1_df = TechnicalIndicators.calculate_all(btc_d1_df)
                logger.info(f"D1: Collected BTC reference data - {len(btc_d1_df)} candles")
        except Exception as e:
            logger.warning(f"D1: Failed to collect BTC reference data: {e}")

        # Step 3: Process each symbol
        successful_count = 0
        failed_symbols = []

        for symbol in ALL_SYMBOLS:
            try:
                logger.info(f"D1: Processing {symbol}")

                # Collect D1 data
                d1_df = self.binance_collector.fetch_historical(symbol, "1d", days=30)

                if d1_df.empty:
                    logger.warning(f"D1: No D1 data for {symbol}")
                    continue

                # Calculate D1 indicators
                d1_df = TechnicalIndicators.calculate_all(d1_df)
                logger.debug(f"D1: Calculated indicators for {symbol}")

                # Collect sentiment data
                sentiment_dict = {}
                try:
                    sentiment_dict = self.sentiment_collector.fetch_all_sentiment(symbol)
                    logger.debug(f"D1: Collected sentiment for {symbol}")

                    # Persist sentiment to database
                    if self.db and sentiment_dict:
                        try:
                            self.db.insert_sentiment([sentiment_dict])
                        except Exception as e:
                            logger.warning(f"D1: Failed to persist sentiment for {symbol}: {e}")
                except Exception as e:
                    logger.warning(f"D1: Failed to collect sentiment for {symbol}: {e}")

                # Run multi-timeframe analysis
                mtf_result = MultiTimeframeAnalysis.aggregate(
                    h1_data=pd.DataFrame(),  # Not needed for D1 analysis
                    h4_data=pd.DataFrame(),  # Not needed for D1 analysis
                    d1_data=d1_df,
                    symbol=symbol,
                    macro_data=macro_data,
                    btc_data=btc_d1_df
                )

                # Store in D1 context
                self.d1_context[symbol] = {
                    'd1_bias': mtf_result.get('d1_bias', 'NEUTRO'),
                    'market_regime': mtf_result.get('market_regime', 'NEUTRO'),
                    'correlation_btc': mtf_result.get('correlation_btc', 0.0),
                    'beta_btc': mtf_result.get('beta_btc', 1.0),
                    'd1_data': d1_df,
                    'macro': macro_data,
                    'sentiment': sentiment_dict,
                }

                # Persist D1 indicators to database
                if self.db:
                    try:
                        # Prepare indicator data for database
                        indicator_records = []
                        for idx, row in d1_df.iterrows():
                            record = {
                                'timestamp': int(row['timestamp']),
                                'symbol': symbol,
                                'timeframe': 'D1',
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
                                'di_minus': row.get('di_minus'),
                            }
                            indicator_records.append(record)

                        if indicator_records:
                            self.db.insert_indicators(indicator_records)
                            logger.debug(f"D1: Persisted {len(indicator_records)} D1 indicators for {symbol}")
                    except Exception as e:
                        logger.warning(f"D1: Failed to persist D1 indicators for {symbol}: {e}")

                logger.info(f"D1: {symbol} - Bias: {mtf_result.get('d1_bias')}, "
                           f"Regime: {mtf_result.get('market_regime')}, "
                           f"Corr BTC: {mtf_result.get('correlation_btc', 0.0):.2f}, "
                           f"Beta: {mtf_result.get('beta_btc', 1.0):.2f}")
                successful_count += 1

            except Exception as e:
                logger.error(f"D1: Failed to process {symbol}: {e}")
                failed_symbols.append(symbol)
                continue

        logger.info(f"D1: Analysis complete - {successful_count}/{len(ALL_SYMBOLS)} symbols processed successfully")
        if failed_symbols:
            logger.warning(f"D1: Failed symbols: {', '.join(failed_symbols)}")

    def weekly_review(self) -> None:
        """Layer 6: Review semanal."""
        logger.info("Weekly: Performance review")

        # 1. Coletar trades da semana
        # 2. Calcular métricas
        # 3. Gerar relatório
        # 4. Verificar degradação

        # (Implementação completa integraria monitoring/performance.py)

    def monthly_retrain(self) -> None:
        """Layer 6: Retreinamento mensal."""
        logger.info("Monthly: Model retrain")

        # 1. Coletar novos dados
        # 2. Walk-forward optimization
        # 3. Retreinar modelo
        # 4. Validar performance

        # (Implementação completa integraria agent/trainer.py)

    def get_state_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo do estado atual.

        Returns:
            Dicionário com resumo
        """
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'open_positions': len(self.open_positions),
            'pending_signals': len(self.pending_signals),
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'agent_states': self.agent_state.copy()
        }
