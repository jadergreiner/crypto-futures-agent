"""
Environment de replay para treino com dados reais de Signal-Driven RL.
Replica trades reais como episódios para aprendizado offline.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import gymnasium as gym
from gymnasium import spaces

logger = logging.getLogger(__name__)

# Ações disponíveis
ACTION_HOLD = 0
ACTION_CLOSE = 1
ACTION_REDUCE_50 = 2
ACTION_MOVE_STOP_BE = 3
ACTION_TIGHTEN_STOP = 4


class SignalReplayEnv(gym.Env):
    """
    Environment que reproduz trades reais para treino offline.
    
    Cada episódio = 1 trade real com seus snapshots de evolução a cada 15 min.
    
    O agente aprende a GERENCIAR posição (hold/reduce/close) dado:
    - Contexto dos indicadores em cada snapshot
    - PnL não-realizado
    - Distância ao stop/TP
    - Evolução dos indicadores
    
    Observation Space: Box(20,) - Features normalizadas do estado atual
    Action Space: Discrete(5) - 0:HOLD, 1:CLOSE, 2:REDUCE_50, 3:MOVE_STOP_BE, 4:TIGHTEN_STOP
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(self, signals: List[Dict[str, Any]], 
                 evolutions_dict: Dict[int, List[Dict[str, Any]]]):
        """
        Inicializa environment de replay.
        
        Args:
            signals: Lista de sinais com outcomes preenchidos
            evolutions_dict: Dicionário {signal_id: [evolutions]} com snapshots
        """
        super().__init__()
        
        self.signals = signals
        self.evolutions_dict = evolutions_dict
        self.current_signal_idx = 0
        self.current_step = 0
        self.current_signal = None
        self.current_evolutions = []
        self.position_closed = False
        self.position_size = 1.0  # Tamanho normalizado da posição
        
        # Observation space: 20 features normalizadas
        # [unrealized_pnl_pct, distance_to_stop_pct, distance_to_tp1_pct,
        #  rsi_14, macd_histogram, bb_percent_b, atr_14, adx_14,
        #  mfe_pct, mae_pct, position_size, steps_elapsed,
        #  market_structure_encoded, funding_rate, long_short_ratio,
        #  pnl_momentum, stop_distance_momentum, rsi_momentum,
        #  volume_momentum, time_in_position_normalized]
        self.observation_space = spaces.Box(
            low=-10.0,
            high=10.0,
            shape=(20,),
            dtype=np.float32
        )
        
        # Action space: 5 ações discretas
        self.action_space = spaces.Discrete(5)
        
        logger.info(f"SignalReplayEnv inicializado com {len(signals)} sinais")
    
    def reset(self, seed: Optional[int] = None, 
              options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Reseta environment para novo episódio (novo sinal).
        
        Args:
            seed: Seed para reproducibilidade
            options: Opções adicionais
            
        Returns:
            Observação inicial e info dict
        """
        super().reset(seed=seed)
        
        # Selecionar próximo sinal
        if self.current_signal_idx >= len(self.signals):
            self.current_signal_idx = 0  # Recomeçar do início
        
        self.current_signal = self.signals[self.current_signal_idx]
        signal_id = self.current_signal['id']
        self.current_evolutions = self.evolutions_dict.get(signal_id, [])
        
        self.current_step = 0
        self.position_closed = False
        self.position_size = 1.0
        
        self.current_signal_idx += 1
        
        # Observação inicial (primeiro snapshot ou dados do sinal)
        obs = self._get_observation()
        info = self._get_info()
        
        logger.debug(f"Episode iniciado: sinal {signal_id}, "
                    f"{len(self.current_evolutions)} snapshots")
        
        return obs, info
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Executa uma ação e avança para o próximo snapshot.
        
        Args:
            action: Ação a executar (0-4)
            
        Returns:
            (observação, reward, terminated, truncated, info)
        """
        if self.position_closed:
            # Posição já fechada, episódio termina
            obs = self._get_observation()
            return obs, 0.0, True, False, self._get_info()
        
        # Executar ação
        reward = 0.0
        
        if action == ACTION_CLOSE:
            # Fechar posição agora
            reward = self._calculate_close_reward()
            self.position_closed = True
            terminated = True
            
        elif action == ACTION_REDUCE_50:
            # Reduzir posição em 50%
            if self.position_size > 0.5:
                self.position_size = 0.5
                reward = self._calculate_partial_reward()
            else:
                reward = -0.1  # Penalidade por tentar reduzir posição já pequena
            terminated = False
            
        elif action == ACTION_MOVE_STOP_BE:
            # Mover stop para breakeven
            reward = self._calculate_stop_move_reward('breakeven')
            terminated = False
            
        elif action == ACTION_TIGHTEN_STOP:
            # Apertar stop (trailing)
            reward = self._calculate_stop_move_reward('tighten')
            terminated = False
            
        else:  # ACTION_HOLD
            # Segurar posição
            reward = self._calculate_hold_reward()
            terminated = False
        
        # Avançar para próximo snapshot
        self.current_step += 1
        
        # Verificar se chegou ao fim dos snapshots (trade fechou naturalmente)
        if self.current_step >= len(self.current_evolutions):
            terminated = True
            # Reward final baseado no outcome real
            if not self.position_closed:
                reward += self._calculate_final_reward()
        
        # Observação do próximo estado
        obs = self._get_observation()
        info = self._get_info()
        
        truncated = False  # Não usamos truncation neste env
        
        return obs, reward, terminated, truncated, info
    
    def _get_observation(self) -> np.ndarray:
        """
        Constrói observação do estado atual.
        
        Returns:
            Array numpy com 20 features normalizadas
        """
        if self.current_step >= len(self.current_evolutions):
            # Fim dos snapshots, retornar observação zero
            return np.zeros(20, dtype=np.float32)
        
        evolution = self.current_evolutions[self.current_step]
        
        # Extrair features
        obs = np.zeros(20, dtype=np.float32)
        
        # 0: PnL não-realizado (%)
        obs[0] = self._normalize(evolution.get('unrealized_pnl_pct', 0.0), -10, 10)
        
        # 1: Distância ao stop (%)
        obs[1] = self._normalize(evolution.get('distance_to_stop_pct', 0.0), -5, 5)
        
        # 2: Distância ao TP1 (%)
        obs[2] = self._normalize(evolution.get('distance_to_tp1_pct', 0.0), -5, 5)
        
        # 3: RSI
        obs[3] = self._normalize(evolution.get('rsi_14', 50.0), 0, 100)
        
        # 4: MACD Histogram
        obs[4] = self._normalize(evolution.get('macd_histogram', 0.0), -1, 1)
        
        # 5: BB Percent B
        obs[5] = self._normalize(evolution.get('bb_percent_b', 0.5), 0, 1)
        
        # 6: ATR (normalizado)
        obs[6] = self._normalize(evolution.get('atr_14', 0.0), 0, 5)
        
        # 7: ADX
        obs[7] = self._normalize(evolution.get('adx_14', 25.0), 0, 100)
        
        # 8: MFE acumulado
        obs[8] = self._normalize(evolution.get('mfe_pct', 0.0), -10, 10)
        
        # 9: MAE acumulado
        obs[9] = self._normalize(evolution.get('mae_pct', 0.0), -10, 10)
        
        # 10: Tamanho da posição
        obs[10] = self.position_size
        
        # 11: Steps decorridos (normalizado)
        obs[11] = self._normalize(self.current_step, 0, max(len(self.current_evolutions), 1))
        
        # 12: Market structure (encoded: bullish=1, bearish=-1, range=0)
        market_struct = evolution.get('market_structure', 'range')
        if 'bullish' in market_struct.lower():
            obs[12] = 1.0
        elif 'bearish' in market_struct.lower():
            obs[12] = -1.0
        else:
            obs[12] = 0.0
        
        # 13: Funding rate
        obs[13] = self._normalize(evolution.get('funding_rate', 0.0), -0.1, 0.1)
        
        # 14: Long/Short ratio
        obs[14] = self._normalize(evolution.get('long_short_ratio', 1.0), 0, 2)
        
        # 15-19: Momentum features (diferença com snapshot anterior)
        if self.current_step > 0:
            prev_evolution = self.current_evolutions[self.current_step - 1]
            
            # 15: PnL momentum
            pnl_now = evolution.get('unrealized_pnl_pct', 0.0)
            pnl_prev = prev_evolution.get('unrealized_pnl_pct', 0.0)
            obs[15] = self._normalize(pnl_now - pnl_prev, -2, 2)
            
            # 16: Stop distance momentum
            stop_now = evolution.get('distance_to_stop_pct', 0.0)
            stop_prev = prev_evolution.get('distance_to_stop_pct', 0.0)
            obs[16] = self._normalize(stop_now - stop_prev, -1, 1)
            
            # 17: RSI momentum
            rsi_now = evolution.get('rsi_14', 50.0)
            rsi_prev = prev_evolution.get('rsi_14', 50.0)
            obs[17] = self._normalize(rsi_now - rsi_prev, -20, 20)
            
            # 18: Volume momentum (placeholder)
            obs[18] = 0.0
            
            # 19: Time in position (horas, normalizado)
            if self.current_signal:
                duration_minutes = self.current_step * 15  # Assumindo 15 min por snapshot
                obs[19] = self._normalize(duration_minutes / 60, 0, 48)  # Max 48h
        
        return obs
    
    def _normalize(self, value: float, min_val: float, max_val: float) -> float:
        """
        Normaliza valor para range [-1, 1].
        
        Args:
            value: Valor a normalizar
            min_val: Valor mínimo esperado
            max_val: Valor máximo esperado
            
        Returns:
            Valor normalizado
        """
        if max_val == min_val:
            return 0.0
        normalized = 2 * (value - min_val) / (max_val - min_val) - 1
        return np.clip(normalized, -1.0, 1.0)
    
    def _get_info(self) -> Dict[str, Any]:
        """
        Retorna informações adicionais do estado atual.
        
        Returns:
            Dicionário com metadados
        """
        info = {
            'signal_id': self.current_signal['id'] if self.current_signal else None,
            'step': self.current_step,
            'total_steps': len(self.current_evolutions),
            'position_size': self.position_size,
            'position_closed': self.position_closed
        }
        
        if self.current_signal:
            info['symbol'] = self.current_signal.get('symbol')
            info['direction'] = self.current_signal.get('direction')
            info['outcome_label'] = self.current_signal.get('outcome_label')
        
        return info
    
    def _calculate_hold_reward(self) -> float:
        """Calcula reward por segurar posição."""
        if self.current_step >= len(self.current_evolutions):
            return 0.0
        
        evolution = self.current_evolutions[self.current_step]
        pnl_pct = evolution.get('unrealized_pnl_pct', 0.0)
        
        # Reward leve por segurar posição lucrativa
        if pnl_pct > 0:
            return 0.01 * pnl_pct
        elif pnl_pct < -2.0:
            return -0.02  # Penalidade leve por segurar posição muito perdedora
        
        return 0.0
    
    def _calculate_close_reward(self) -> float:
        """Calcula reward por fechar posição agora."""
        if self.current_step >= len(self.current_evolutions):
            return 0.0
        
        evolution = self.current_evolutions[self.current_step]
        current_pnl = evolution.get('unrealized_pnl_pct', 0.0)
        
        # Comparar com PnL final real
        final_pnl = self.current_signal.get('pnl_pct', 0.0)
        
        # Se fechar agora seria melhor que o resultado final, reward positivo
        if current_pnl > final_pnl:
            return (current_pnl - final_pnl) * 0.5
        else:
            return (current_pnl - final_pnl) * 0.2  # Penalidade menor por fechar cedo
    
    def _calculate_partial_reward(self) -> float:
        """Calcula reward por realizar parcial."""
        if self.current_step >= len(self.current_evolutions):
            return 0.0
        
        evolution = self.current_evolutions[self.current_step]
        current_pnl = evolution.get('unrealized_pnl_pct', 0.0)
        mfe = evolution.get('mfe_pct', 0.0)
        
        # Reward se parcial próxima ao MFE (timing bom)
        if mfe > 0 and abs(current_pnl - mfe) < 1.0:
            return 0.5
        elif current_pnl > 2.0:
            return 0.3  # Reward por realizar lucro > 2%
        
        return 0.1  # Reward mínimo por gestão
    
    def _calculate_stop_move_reward(self, move_type: str) -> float:
        """Calcula reward por mover stop."""
        if self.current_step >= len(self.current_evolutions):
            return 0.0
        
        evolution = self.current_evolutions[self.current_step]
        current_pnl = evolution.get('unrealized_pnl_pct', 0.0)
        
        # Reward se mover stop com posição lucrativa (proteger lucro)
        if move_type == 'breakeven' and current_pnl > 1.0:
            return 0.3
        elif move_type == 'tighten' and current_pnl > 2.0:
            return 0.4
        
        return 0.0
    
    def _calculate_final_reward(self) -> float:
        """Calcula reward final baseado no outcome real do trade."""
        if not self.current_signal:
            return 0.0
        
        r_multiple = self.current_signal.get('r_multiple', 0.0)
        
        # Reward proporcional ao R-multiple, ajustado pelo tamanho da posição mantida
        return r_multiple * self.position_size
    
    def render(self):
        """Renderiza estado atual (placeholder)."""
        if self.current_signal and self.current_step < len(self.current_evolutions):
            evolution = self.current_evolutions[self.current_step]
            print(f"Signal {self.current_signal['id']} - Step {self.current_step}/{len(self.current_evolutions)}")
            print(f"  PnL: {evolution.get('unrealized_pnl_pct', 0.0):.2f}%")
            print(f"  Position: {self.position_size * 100:.0f}%")
            print(f"  Closed: {self.position_closed}")
    
    def close(self):
        """Limpa recursos do environment."""
        pass
