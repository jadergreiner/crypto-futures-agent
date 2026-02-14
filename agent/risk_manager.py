"""
Gerenciador de risco - Regras INVIOLÁVEIS de gestão de capital e posições.
"""

import logging
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
from config.risk_params import RISK_PARAMS

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Aplica regras invioláveis de gestão de risco.
    Calcula position sizing, stops, targets e valida trades.
    """
    
    def __init__(self, risk_params: Optional[Dict[str, Any]] = None):
        """
        Inicializa risk manager.
        
        Args:
            risk_params: Parâmetros customizados (opcional, usa config se None)
        """
        self.params = risk_params or RISK_PARAMS
        logger.info("Risk Manager initialized with inviolable rules")
    
    def calculate_position_size(self, capital: float, entry_price: float, 
                                stop_distance_pct: float, 
                                risk_pct: Optional[float] = None) -> float:
        """
        Calcula tamanho da posição baseado no risco.
        
        Args:
            capital: Capital disponível
            entry_price: Preço de entrada
            stop_distance_pct: Distância do stop em %
            risk_pct: Risco desejado (default usa max_risk_per_trade_pct)
            
        Returns:
            Tamanho da posição em unidades base
        """
        if risk_pct is None:
            risk_pct = self.params['max_risk_per_trade_pct']
        
        # Capital arriscado
        risk_capital = capital * risk_pct
        
        # Valor arriscado por unidade
        risk_per_unit = entry_price * (stop_distance_pct / 100)
        
        if risk_per_unit == 0:
            logger.warning("Risk per unit is zero, returning minimum position")
            return 0.001
        
        # Posição em unidades
        position_size = risk_capital / risk_per_unit
        
        logger.debug(f"Position size: {position_size:.4f} units "
                    f"(capital: ${capital:.2f}, risk: {risk_pct*100}%, "
                    f"stop: {stop_distance_pct}%)")
        
        return position_size
    
    def calculate_stop_loss(self, entry_price: float, atr: float, 
                           direction: str, multiplier: Optional[float] = None) -> float:
        """
        Calcula stop loss baseado em ATR.
        
        Args:
            entry_price: Preço de entrada
            atr: Average True Range
            direction: "LONG" ou "SHORT"
            multiplier: Multiplicador do ATR (default usa config)
            
        Returns:
            Preço do stop loss
        """
        if multiplier is None:
            multiplier = self.params['stop_loss_atr_multiplier']
        
        stop_distance = atr * multiplier
        
        if direction == "LONG":
            stop_loss = entry_price - stop_distance
        else:  # SHORT
            stop_loss = entry_price + stop_distance
        
        logger.debug(f"{direction} stop loss: {stop_loss:.4f} "
                    f"(entry: {entry_price:.4f}, ATR: {atr:.4f}, mult: {multiplier})")
        
        return stop_loss
    
    def calculate_take_profit(self, entry_price: float, atr: float, 
                             direction: str, multiplier: Optional[float] = None) -> float:
        """
        Calcula take profit baseado em ATR.
        
        Args:
            entry_price: Preço de entrada
            atr: Average True Range
            direction: "LONG" ou "SHORT"
            multiplier: Multiplicador do ATR (default usa config)
            
        Returns:
            Preço do take profit
        """
        if multiplier is None:
            multiplier = self.params['take_profit_atr_multiplier']
        
        tp_distance = atr * multiplier
        
        if direction == "LONG":
            take_profit = entry_price + tp_distance
        else:  # SHORT
            take_profit = entry_price - tp_distance
        
        logger.debug(f"{direction} take profit: {take_profit:.4f} "
                    f"(entry: {entry_price:.4f}, ATR: {atr:.4f}, mult: {multiplier})")
        
        return take_profit
    
    def calculate_structural_stop(self, entry_price: float, order_block: Any, 
                                  direction: str) -> Optional[float]:
        """
        Calcula stop baseado em Order Block (SMC).
        
        Args:
            entry_price: Preço de entrada
            order_block: Order Block SMC
            direction: "LONG" ou "SHORT"
            
        Returns:
            Preço do stop estrutural ou None se inválido
        """
        if order_block is None:
            return None
        
        if direction == "LONG":
            # Stop abaixo do OB bullish
            stop_loss = order_block.zone_low
        else:  # SHORT
            # Stop acima do OB bearish
            stop_loss = order_block.zone_high
        
        # Validar distância
        stop_distance_pct = abs(entry_price - stop_loss) / entry_price * 100
        
        if stop_distance_pct > self.params['max_stop_distance_pct'] * 100:
            logger.warning(f"Structural stop too far: {stop_distance_pct:.2f}% > "
                         f"{self.params['max_stop_distance_pct']*100}%")
            return None
        
        logger.debug(f"Structural stop: {stop_loss:.4f} (distance: {stop_distance_pct:.2f}%)")
        
        return stop_loss
    
    def update_trailing_stop(self, current_price: float, current_stop: float, 
                            atr: float, direction: str, entry_price: float) -> float:
        """
        Atualiza trailing stop (só move a favor).
        
        Args:
            current_price: Preço atual
            current_stop: Stop atual
            atr: ATR atual
            direction: "LONG" ou "SHORT"
            entry_price: Preço de entrada original
            
        Returns:
            Novo stop (pode ser igual ao atual)
        """
        # Calcular R-multiple atual
        if direction == "LONG":
            initial_risk = entry_price - current_stop
            current_profit = current_price - entry_price
        else:  # SHORT
            initial_risk = current_stop - entry_price
            current_profit = entry_price - current_price
        
        if initial_risk <= 0:
            return current_stop
        
        r_multiple = current_profit / initial_risk
        
        # Ativar trailing após atingir activation_r
        if r_multiple < self.params['trailing_stop_activation_r']:
            return current_stop
        
        # Calcular novo trailing stop
        trailing_distance = atr * self.params['trailing_stop_atr_multiplier']
        
        if direction == "LONG":
            new_stop = current_price - trailing_distance
            # Só move para cima
            if new_stop > current_stop:
                logger.debug(f"Trailing stop updated: {current_stop:.4f} -> {new_stop:.4f}")
                return new_stop
        else:  # SHORT
            new_stop = current_price + trailing_distance
            # Só move para baixo
            if new_stop < current_stop:
                logger.debug(f"Trailing stop updated: {current_stop:.4f} -> {new_stop:.4f}")
                return new_stop
        
        return current_stop
    
    def validate_new_trade(self, open_positions: List[Dict[str, Any]], 
                          new_symbol: str, new_direction: str,
                          capital: float, new_position_risk_usd: float) -> Tuple[bool, str]:
        """
        Valida se novo trade pode ser aberto.
        
        Args:
            open_positions: Lista de posições abertas
            new_symbol: Símbolo do novo trade
            new_direction: Direção do novo trade
            capital: Capital total
            new_position_risk_usd: Risco do novo trade em USD
            
        Returns:
            (allowed: bool, reason: str)
        """
        # Regra 1: Máximo de posições simultâneas
        if len(open_positions) >= self.params['max_simultaneous_positions']:
            return False, f"Max simultaneous positions reached ({self.params['max_simultaneous_positions']})"
        
        # Regra 2: Risco total
        total_risk = sum(pos.get('risk_usd', 0) for pos in open_positions)
        total_risk += new_position_risk_usd
        max_risk = capital * self.params['max_simultaneous_risk_pct']
        
        if total_risk > max_risk:
            return False, f"Total risk exceeds limit: ${total_risk:.2f} > ${max_risk:.2f}"
        
        # Regra 3: Não abrir posições opostas no mesmo ativo
        for pos in open_positions:
            if pos['symbol'] == new_symbol:
                if pos['direction'] != new_direction:
                    return False, f"Opposite position already open on {new_symbol}"
                else:
                    return False, f"Position already open on {new_symbol}"
        
        # Regra 4: Correlação (simplificado - assumir BTCUSDT vs outros)
        # Em implementação real, calcular correlação dinâmica
        if new_symbol != "BTCUSDT":
            btc_positions = [p for p in open_positions if p['symbol'] == "BTCUSDT"]
            if btc_positions and len(open_positions) >= 2:
                # Já tem BTC + outra posição, verificar correlação
                logger.warning("Correlation check skipped (simplified implementation)")
        
        # Regra 5: Exposição em um único ativo
        # (Esta regra é coberta pela regra 3 - não permite múltiplas posições no mesmo ativo)
        
        logger.info(f"Trade validation passed for {new_symbol} {new_direction}")
        return True, "OK"
    
    def check_drawdown(self, portfolio: Dict[str, Any]) -> Tuple[str, str]:
        """
        Verifica níveis de drawdown e determina ação.
        
        Args:
            portfolio: Estado do portfólio com 'initial_capital', 'current_capital', 
                      'peak_capital', 'daily_start_capital'
            
        Returns:
            (level: str, action: str)
            level: "OK", "WARNING", "CRITICAL", "DAILY_LIMIT"
            action: "NONE", "REDUCE", "CLOSE_ALL", "PAUSE"
        """
        initial_capital = portfolio.get('initial_capital', 10000)
        current_capital = portfolio.get('current_capital', initial_capital)
        peak_capital = portfolio.get('peak_capital', initial_capital)
        daily_start_capital = portfolio.get('daily_start_capital', initial_capital)
        
        # Drawdown total desde o pico
        if peak_capital > 0:
            total_dd = (peak_capital - current_capital) / peak_capital
        else:
            total_dd = 0
        
        # Drawdown diário
        if daily_start_capital > 0:
            daily_dd = (daily_start_capital - current_capital) / daily_start_capital
        else:
            daily_dd = 0
        
        # Verificar limites
        max_daily_dd = self.params['max_daily_drawdown_pct']
        max_total_dd = self.params['max_total_drawdown_pct']
        
        # Drawdown diário atingido
        if daily_dd >= max_daily_dd:
            logger.critical(f"⚠️  DAILY DRAWDOWN LIMIT: {daily_dd*100:.2f}% >= {max_daily_dd*100}%")
            return "DAILY_LIMIT", "CLOSE_ALL"
        
        # Drawdown total crítico
        if total_dd >= max_total_dd:
            logger.critical(f"⚠️  TOTAL DRAWDOWN CRITICAL: {total_dd*100:.2f}% >= {max_total_dd*100}%")
            return "CRITICAL", "PAUSE"
        
        # Warning em 75% do limite total
        if total_dd >= max_total_dd * 0.75:
            logger.warning(f"⚠️  Drawdown warning: {total_dd*100:.2f}% (limit: {max_total_dd*100}%)")
            return "WARNING", "REDUCE"
        
        return "OK", "NONE"
    
    def check_overtrading(self, trades_24h: int) -> Tuple[bool, str]:
        """
        Verifica se está overtrading.
        
        Args:
            trades_24h: Número de trades nas últimas 24h
            
        Returns:
            (is_overtrading: bool, message: str)
        """
        max_trades = self.params['overtrading_max_trades_24h']
        
        if trades_24h >= max_trades:
            return True, f"Overtrading detected: {trades_24h} trades in 24h (max: {max_trades})"
        
        return False, "OK"
    
    def adjust_size_by_confluence(self, base_size: float, confluence_score: int) -> float:
        """
        Ajusta tamanho da posição baseado no score de confluência.
        
        Args:
            base_size: Tamanho base da posição
            confluence_score: Score de confluência (0-14)
            
        Returns:
            Tamanho ajustado
        """
        min_score = self.params['confluence_min_score']
        full_score = self.params['confluence_full_size_score']
        
        if confluence_score < min_score:
            logger.warning(f"Confluence score too low: {confluence_score} < {min_score}")
            return 0.0
        
        if confluence_score >= full_score:
            return base_size
        
        # Escala linear entre min e full
        scale = (confluence_score - min_score) / (full_score - min_score)
        adjusted_size = base_size * (0.5 + 0.5 * scale)  # 50-100%
        
        logger.debug(f"Position size adjusted by confluence: {base_size:.4f} -> {adjusted_size:.4f} "
                    f"(score: {confluence_score}/{full_score})")
        
        return adjusted_size
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo dos parâmetros de risco.
        
        Returns:
            Dicionário com parâmetros
        """
        return {
            'max_risk_per_trade': f"{self.params['max_risk_per_trade_pct']*100}%",
            'max_simultaneous_risk': f"{self.params['max_simultaneous_risk_pct']*100}%",
            'max_daily_drawdown': f"{self.params['max_daily_drawdown_pct']*100}%",
            'max_total_drawdown': f"{self.params['max_total_drawdown_pct']*100}%",
            'max_positions': self.params['max_simultaneous_positions'],
            'max_leverage': self.params['max_leverage'],
            'stop_loss_atr': self.params['stop_loss_atr_multiplier'],
            'take_profit_atr': self.params['take_profit_atr_multiplier'],
            'trailing_activation_r': self.params['trailing_stop_activation_r'],
            'min_confluence': self.params['confluence_min_score']
        }
