"""
Layer Manager - Gerencia estado e execução condicional das camadas.
"""

import logging
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
                       stop: float, tp: float, size: float) -> None:
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
            'timestamp': datetime.now(timezone.utc),
            'h1_candles_elapsed': 0
        }
        
        self.agent_state[symbol] = 'pending_entry'
        
        logger.info(f"Signal registered: {symbol} {direction}, score={score}")
    
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
        """Layer 3: Timing de entrada H1."""
        # Verificar sinais pendentes
        for symbol, signal in list(self.pending_signals.items()):
            signal['h1_candles_elapsed'] += 1
            
            # Timeout após 12 H1 candles
            if signal['h1_candles_elapsed'] >= 12:
                self.cancel_signal(symbol, "timeout")
                continue
            
            # Verificar se está na zona de entrada
            # (Implementação real verificaria via SMC)
            logger.debug(f"H1 timing check: {symbol}")
    
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
                logger.info(f"H4: Processing {symbol}")
                
                # Step 1: Collect fresh H4 data
                h4_df = self.binance_collector.fetch_historical(symbol, "4h", days=30)
                if h4_df.empty:
                    logger.warning(f"H4: No H4 data for {symbol}")
                    continue
                
                # Step 2: Collect fresh H1 data for SMC
                h1_df = self.binance_collector.fetch_historical(symbol, "1h", days=7)
                if h1_df.empty:
                    logger.warning(f"H4: No H1 data for {symbol}")
                    continue
                
                # Step 3: Calculate H4 technical indicators
                h4_df = TechnicalIndicators.calculate_all(h4_df)
                logger.debug(f"H4: Calculated H4 indicators for {symbol}")
                
                # Step 4: Calculate SMC on H1
                smc_result = SmartMoneyConcepts.calculate_all_smc(h1_df)
                self.smc_cache[symbol] = smc_result
                logger.debug(f"H4: Calculated SMC structures for {symbol}")
                
                # Step 5: Get D1 context
                d1_context = self.d1_context.get(symbol, {})
                d1_bias = d1_context.get('d1_bias', 'NEUTRO')
                market_regime = d1_context.get('market_regime', 'NEUTRO')
                d1_data = d1_context.get('d1_data', pd.DataFrame())
                
                # Step 6: Get sentiment (from D1 context or fetch fresh)
                sentiment = d1_context.get('sentiment', {})
                if not sentiment:
                    try:
                        sentiment = self.sentiment_collector.fetch_all_sentiment(symbol)
                    except Exception as e:
                        logger.warning(f"H4: Failed to fetch sentiment for {symbol}: {e}")
                        sentiment = {}
                
                macro = d1_context.get('macro', {})
                
                # Step 7: Get position state if exists
                position_state = self.open_positions.get(symbol)
                
                # Step 8: Build observation vector
                try:
                    observation = FeatureEngineer.build_observation(
                        symbol=symbol,
                        h1_data=h1_df,
                        h4_data=h4_df,
                        d1_data=d1_data,
                        sentiment=sentiment,
                        macro=macro,
                        smc=smc_result,
                        position_state=position_state
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
                
                # Step 9: Calculate confluence score (rule-based)
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
                
                # Step 10: Determine action based on confluence score
                min_score = RISK_PARAMS['confluence_min_score']
                
                if confluence_score >= min_score and signal_direction in ['LONG', 'SHORT']:
                    # We have a valid signal
                    
                    # Get current price and ATR
                    current_price = h4_df['close'].iloc[-1]
                    atr = h4_df['atr_14'].iloc[-1]
                    
                    if pd.isna(atr) or atr == 0:
                        logger.warning(f"H4: Invalid ATR for {symbol}, skipping")
                        continue
                    
                    # Step 11: Calculate stop loss and take profit
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
                        
                        # Step 13: Register signal
                        self.register_signal(
                            symbol=symbol,
                            direction=signal_direction,
                            score=confluence_score,
                            stop=stop_loss,
                            tp=take_profit,
                            size=position_size
                        )
                        
                        signals_generated += 1
                        logger.info(f"H4: [OK] Signal registered for {symbol} {signal_direction} "
                                   f"(score={confluence_score}, size={position_size:.4f})")
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
