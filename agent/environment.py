"""
Gymnasium Environment customizado para trading de futuros de criptomoedas.
"""

import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import pandas as pd

from .reward import RewardCalculator
from .risk_manager import RiskManager
from indicators.features import FeatureEngineer

logger = logging.getLogger(__name__)


class CryptoFuturesEnv(gym.Env):
    """
    Environment Gymnasium para trading de futuros.
    
    Observation Space: Box(104,) - Features normalizadas
    Action Space: Discrete(5) - 0:HOLD, 1:OPEN_LONG, 2:OPEN_SHORT, 3:CLOSE, 4:REDUCE_50
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(self, 
                 data: Dict[str, pd.DataFrame],
                 initial_capital: float = 10000,
                 risk_params: Optional[Dict[str, Any]] = None,
                 episode_length: int = 500):
        """
        Inicializa environment.
        
        Args:
            data: Dicionário com DataFrames de H1, H4, D1, sentiment, macro, smc
            initial_capital: Capital inicial
            risk_params: Parâmetros de risco customizados
            episode_length: Número de steps por episódio (H4 candles)
        """
        super().__init__()
        
        self.data = data
        self.initial_capital = initial_capital
        self.episode_length = episode_length
        
        # Managers
        self.risk_manager = RiskManager(risk_params)
        self.reward_calculator = RewardCalculator()
        self.feature_engineer = FeatureEngineer()
        
        # Spaces
        self.observation_space = spaces.Box(
            low=-10.0, 
            high=10.0, 
            shape=(104,), 
            dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(5)
        # 0: HOLD
        # 1: OPEN_LONG
        # 2: OPEN_SHORT
        # 3: CLOSE
        # 4: REDUCE_50
        
        # State
        self.start_step = 0
        self.current_step = 0
        self.capital = initial_capital
        self.position = None  # None ou Dict com info da posição
        self.trades_history = []
        self.episode_trades = []
        
        # Portfolio tracking
        self.peak_capital = initial_capital
        self.daily_start_capital = initial_capital
        
        logger.info(f"CryptoFuturesEnv initialized: capital=${initial_capital}, "
                   f"episode_length={episode_length}")
    
    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """
        Reset environment para novo episódio.
        
        Returns:
            (observation, info)
        """
        super().reset(seed=seed)
        
        # Começar após warm-up period para evitar NaN nos indicadores
        warmup_steps = 30  # Pular primeiros 30 candles
        max_start = max(0, len(self.data.get('h4', [])) - self.episode_length - warmup_steps)
        
        if max_start > warmup_steps:
            # Selecionar ponto de início aleatório após warm-up
            self.start_step = np.random.randint(warmup_steps, max_start)
        else:
            self.start_step = warmup_steps
        
        self.current_step = self.start_step
        self.capital = self.initial_capital
        self.position = None
        self.episode_trades = []
        self.peak_capital = self.initial_capital
        self.daily_start_capital = self.initial_capital
        
        observation = self._get_observation()
        info = self._get_info()
        
        logger.debug(f"Environment reset at step {self.start_step}")
        
        return observation, info
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Executa um step no environment.
        
        Args:
            action: Ação a executar (0-4)
            
        Returns:
            (observation, reward, terminated, truncated, info)
        """
        action_valid = True
        trade_result = None
        
        # Executar ação
        if action == 0:  # HOLD
            pass
        
        elif action == 1:  # OPEN_LONG
            if self.position is None:
                action_valid = self._open_position("LONG")
            else:
                action_valid = False
        
        elif action == 2:  # OPEN_SHORT
            if self.position is None:
                action_valid = self._open_position("SHORT")
            else:
                action_valid = False
        
        elif action == 3:  # CLOSE
            if self.position is not None:
                trade_result = self._close_position("manual_close")
            else:
                action_valid = False
        
        elif action == 4:  # REDUCE_50
            if self.position is not None:
                self._reduce_position(0.5)
            else:
                action_valid = False
        
        # Avançar para próximo candle
        self.current_step += 1
        
        # Verificar stops e trailing
        if self.position is not None:
            stop_result = self._check_stops()
            if stop_result:
                trade_result = stop_result
        
        # Calcular reward
        reward_dict = self.reward_calculator.calculate(
            trade_result=trade_result,
            position_state=self._get_position_state(),
            portfolio_state=self._get_portfolio_state(),
            action_valid=action_valid,
            trades_recent=self.episode_trades
        )
        reward = reward_dict['total']
        
        # Verificar término
        terminated = self._check_termination()
        truncated = self.current_step >= self.episode_length
        
        # Próxima observação
        observation = self._get_observation()
        info = self._get_info()
        info['reward_components'] = reward_dict
        
        return observation, reward, terminated, truncated, info
    
    def _open_position(self, direction: str) -> bool:
        """
        Abre uma posição.
        
        Args:
            direction: "LONG" ou "SHORT"
            
        Returns:
            True se posição foi aberta
        """
        try:
            # Pegar dados atuais
            h4_idx = self.current_step
            if h4_idx >= len(self.data['h4']):
                return False
            
            current_candle = self.data['h4'].iloc[h4_idx]
            entry_price = float(current_candle['close'])
            atr = float(current_candle.get('atr_14', entry_price * 0.02))
            
            # Garantir que ATR não seja zero
            if atr == 0 or np.isnan(atr):
                atr = entry_price * 0.02
            
            # Calcular stop e TP
            stop_loss = self.risk_manager.calculate_stop_loss(entry_price, atr, direction)
            take_profit = self.risk_manager.calculate_take_profit(entry_price, atr, direction)
            
            # Calcular tamanho da posição
            stop_distance_pct = abs(entry_price - stop_loss) / entry_price * 100
            
            # Garantir que stop_distance_pct não seja zero
            if stop_distance_pct == 0 or np.isnan(stop_distance_pct):
                stop_distance_pct = 2.0  # Default 2%
            
            # Validar distância do stop
            if stop_distance_pct > self.risk_manager.params['max_stop_distance_pct'] * 100:
                logger.warning(f"Stop too far: {stop_distance_pct:.2f}%")
                return False
            
            position_size = self.risk_manager.calculate_position_size(
                self.capital, entry_price, stop_distance_pct
            )
            
            # Validar com risk manager
            risk_usd = position_size * entry_price * (stop_distance_pct / 100)
            open_positions = [self.position] if self.position else []
            
            allowed, reason = self.risk_manager.validate_new_trade(
                open_positions, "SYMBOL", direction, self.capital, risk_usd
            )
            
            if not allowed:
                logger.debug(f"Trade rejected: {reason}")
                return False
            
            # Criar posição
            self.position = {
                'direction': direction,
                'entry_price': entry_price,
                'entry_step': self.current_step,
                'size': position_size,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'initial_stop': stop_loss,
                'atr': atr
            }
            
            logger.info(f"Position opened: {direction} @ {entry_price:.2f}, "
                       f"size={position_size:.4f}, stop={stop_loss:.2f}, tp={take_profit:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            return False
    
    def _close_position(self, reason: str) -> Optional[Dict[str, Any]]:
        """
        Fecha a posição atual.
        
        Args:
            reason: Razão do fechamento
            
        Returns:
            Dicionário com resultado do trade
        """
        if self.position is None:
            return None
        
        try:
            h4_idx = self.current_step
            if h4_idx >= len(self.data['h4']):
                return None
            
            current_candle = self.data['h4'].iloc[h4_idx]
            exit_price = float(current_candle['close'])
            
            # Calcular PnL
            if self.position['direction'] == "LONG":
                pnl = (exit_price - self.position['entry_price']) * self.position['size']
            else:  # SHORT
                pnl = (self.position['entry_price'] - exit_price) * self.position['size']
            
            pnl_pct = pnl / self.capital * 100
            
            # Calcular R-multiple
            initial_risk = abs(self.position['entry_price'] - self.position['initial_stop']) * self.position['size']
            r_multiple = pnl / initial_risk if initial_risk > 0 else 0
            
            # Atualizar capital
            self.capital += pnl
            
            # Atualizar peak
            if self.capital > self.peak_capital:
                self.peak_capital = self.capital
            
            # Registrar trade
            trade_result = {
                'direction': self.position['direction'],
                'entry_price': self.position['entry_price'],
                'exit_price': exit_price,
                'entry_step': self.position['entry_step'],
                'exit_step': self.current_step,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'r_multiple': r_multiple,
                'exit_reason': reason
            }
            
            self.episode_trades.append(trade_result)
            self.trades_history.append(trade_result)
            
            logger.info(f"Position closed: {reason}, PnL=${pnl:.2f} ({pnl_pct:.2f}%), "
                       f"R={r_multiple:.2f}")
            
            # Limpar posição
            self.position = None
            
            return trade_result
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            self.position = None
            return None
    
    def _reduce_position(self, factor: float) -> None:
        """
        Reduz posição por um fator.
        
        Args:
            factor: Fator de redução (0-1)
        """
        if self.position is None:
            return
        
        # Reduzir tamanho
        self.position['size'] *= (1 - factor)
        
        # Mover stop para breakeven
        self.position['stop_loss'] = self.position['entry_price']
        
        logger.info(f"Position reduced by {factor*100}%, stop moved to breakeven")
    
    def _check_stops(self) -> Optional[Dict[str, Any]]:
        """
        Verifica se stop loss ou take profit foram atingidos.
        
        Returns:
            Resultado do trade se fechado, None caso contrário
        """
        if self.position is None:
            return None
        
        h4_idx = self.current_step
        if h4_idx >= len(self.data['h4']):
            return None
        
        current_candle = self.data['h4'].iloc[h4_idx]
        high = float(current_candle['high'])
        low = float(current_candle['low'])
        close = float(current_candle['close'])
        
        direction = self.position['direction']
        
        # Verificar stop loss
        if direction == "LONG" and low <= self.position['stop_loss']:
            return self._close_position("stop_loss")
        elif direction == "SHORT" and high >= self.position['stop_loss']:
            return self._close_position("stop_loss")
        
        # Verificar take profit
        if direction == "LONG" and high >= self.position['take_profit']:
            return self._close_position("take_profit")
        elif direction == "SHORT" and low <= self.position['take_profit']:
            return self._close_position("take_profit")
        
        # Atualizar trailing stop
        atr = float(current_candle.get('atr_14', self.position['atr']))
        new_stop = self.risk_manager.update_trailing_stop(
            close, self.position['stop_loss'], atr, 
            direction, self.position['entry_price']
        )
        self.position['stop_loss'] = new_stop
        
        return None
    
    def _get_observation(self) -> np.ndarray:
        """
        Constrói observação atual.
        
        Returns:
            Array de 104 features
        """
        try:
            h4_idx = self.current_step
            
            # Pegar dados
            h4_data = self.data.get('h4')
            h1_data = self.data.get('h1')
            d1_data = self.data.get('d1')
            sentiment = self.data.get('sentiment')
            macro = self.data.get('macro')
            smc = self.data.get('smc')
            
            # Window de dados
            if h4_data is not None and h4_idx < len(h4_data):
                h4_window = h4_data.iloc[max(0, h4_idx-30):h4_idx+1]
            else:
                h4_window = None
            
            # Estado da posição
            position_state = self._get_position_state()
            
            # Construir features
            observation = self.feature_engineer.build_observation(
                symbol="SYMBOL",
                h1_data=h1_data,
                h4_data=h4_window,
                d1_data=d1_data,
                sentiment=sentiment,
                macro=macro,
                smc=smc,
                position_state=position_state
            )
            
            # Garantir que não há NaN - substituir por 0
            observation = np.nan_to_num(observation, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Clippar valores extremos para evitar problemas
            observation = np.clip(observation, -10.0, 10.0)
            
            return observation.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error building observation: {e}")
            # Retornar observação zero em caso de erro
            return np.zeros(104, dtype=np.float32)
    
    def _get_position_state(self) -> Optional[Dict[str, Any]]:
        """Retorna estado da posição atual."""
        if self.position is None:
            return {'has_position': False}
        
        h4_idx = self.current_step
        if h4_idx >= len(self.data['h4']):
            return {'has_position': False}
        
        current_price = float(self.data['h4'].iloc[h4_idx]['close'])
        
        # Calcular PnL
        if self.position['direction'] == "LONG":
            pnl = (current_price - self.position['entry_price']) * self.position['size']
        else:
            pnl = (self.position['entry_price'] - current_price) * self.position['size']
        
        pnl_pct = pnl / self.capital * 100
        
        # Tempo na posição
        time_in_pos = (self.current_step - self.position['entry_step']) * 4  # H4 em horas
        
        # Distâncias
        stop_dist_pct = abs(current_price - self.position['stop_loss']) / current_price * 100
        tp_dist_pct = abs(self.position['take_profit'] - current_price) / current_price * 100
        
        return {
            'has_position': True,
            'direction': self.position['direction'],
            'pnl_pct': pnl_pct,
            'time_in_position_hours': time_in_pos,
            'stop_distance_pct': stop_dist_pct,
            'tp_distance_pct': tp_dist_pct,
            'has_stop_loss': True
        }
    
    def _get_portfolio_state(self) -> Dict[str, Any]:
        """Retorna estado do portfólio."""
        current_dd = (self.peak_capital - self.capital) / self.peak_capital * 100 if self.peak_capital > 0 else 0
        
        # Contar trades nas últimas 24h (24 H4 candles = 96h, aproximar para 24 candles = 96/4 = 24h)
        recent_trades = [t for t in self.episode_trades if (self.current_step - t['exit_step']) <= 6]
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.capital,
            'peak_capital': self.peak_capital,
            'daily_start_capital': self.daily_start_capital,
            'current_drawdown_pct': current_dd,
            'trades_24h': len(recent_trades)
        }
    
    def _get_info(self) -> Dict[str, Any]:
        """Retorna informações adicionais."""
        return {
            'step': self.current_step,
            'capital': self.capital,
            'has_position': self.position is not None,
            'trades_count': len(self.episode_trades)
        }
    
    def _check_termination(self) -> bool:
        """
        Verifica condições de término do episódio.
        
        Returns:
            True se deve terminar
        """
        # Término por perda de capital
        if self.capital < self.initial_capital * 0.5:
            logger.warning(f"Episode terminated: capital < 50% (${self.capital:.2f})")
            return True
        
        # Término por fim dos dados
        if self.current_step >= len(self.data.get('h4', [])):
            logger.info("Episode terminated: end of data")
            return True
        
        return False
    
    def render(self) -> None:
        """Renderiza estado atual (opcional)."""
        if self.current_step % 50 == 0:
            print(f"Step: {self.current_step}, Capital: ${self.capital:.2f}, "
                  f"Position: {self.position['direction'] if self.position else 'None'}")
    
    def close(self) -> None:
        """Limpa recursos."""
        pass
