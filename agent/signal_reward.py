"""
Calculadora de reward para Signal-Driven RL.
Calcula recompensa baseada nos outcomes reais de trades executados.
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Constantes de reward
PNL_REWARD_SCALE = 1.0          # Escala base do reward por PnL
R_MULTIPLE_BONUS_HIGH = 2.0     # Bonus para R > 3.0
R_MULTIPLE_BONUS_MID = 1.0      # Bonus para R > 2.0
R_MULTIPLE_BONUS_LOW = 0.5      # Bonus para R > 1.0
PARTIAL_BONUS = 0.5             # Bonus por executar parcial no momento certo
TIMING_REWARD_SCALE = 0.3       # Escala do reward por timing de entrada
QUALITY_REWARD_SCALE = 0.5      # Escala do reward por qualidade (MFE/MAE)
MANAGEMENT_REWARD_SCALE = 0.3   # Escala do reward por gestão (trailing, parciais)
STOP_LOSS_PENALTY_BASE = -1.0   # Penalidade base por stop loss
MAX_REWARD = 10.0               # Limite máximo de reward
MIN_REWARD = -10.0              # Limite mínimo de reward


class SignalRewardCalculator:
    """
    Calcula reward rico baseado em outcomes reais de trades.
    
    Componentes de reward:
    1. PnL realizado (proporcional ao R-multiple)
    2. Bonus por parciais executadas no momento certo
    3. Penalidade proporcional por stop loss
    4. Reward por qualidade do sinal (MFE/MAE ratio)
    5. Reward por timing de entrada
    6. Reward por gestão (trailing stop, parciais que protegeram lucro)
    """
    
    def __init__(self):
        """Inicializa calculadora de reward para sinais."""
        logger.info("SignalRewardCalculator inicializado")
    
    def calculate_signal_reward(self, signal: Dict[str, Any], 
                               evolutions: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calcula reward rico baseado no resultado REAL do trade.
        Usa os snapshots de evolução para avaliar qualidade da gestão.
        
        Args:
            signal: Dicionário com dados do sinal completo (incluindo outcome)
            evolutions: Lista de snapshots de evolução do sinal
            
        Returns:
            Dicionário com reward total e componentes detalhados
        """
        components = {
            'r_pnl': 0.0,
            'r_partial_bonus': 0.0,
            'r_stop_penalty': 0.0,
            'r_quality': 0.0,
            'r_timing': 0.0,
            'r_management': 0.0
        }
        
        # Componente 1: Reward por PnL realizado (baseado em R-multiple)
        r_multiple = signal.get('r_multiple', 0.0)
        if r_multiple is not None:
            components['r_pnl'] = self._calculate_pnl_reward(r_multiple)
        
        # Componente 2: Bonus por parciais
        exit_reason = signal.get('exit_reason', '')
        if 'take_profit' in exit_reason.lower():
            components['r_partial_bonus'] = self._calculate_partial_bonus(
                signal, evolutions, exit_reason
            )
        
        # Componente 3: Penalidade por stop loss
        if exit_reason == 'stop_loss':
            components['r_stop_penalty'] = self._calculate_stop_penalty(
                signal, evolutions
            )
        
        # Componente 4: Reward por qualidade do sinal (MFE/MAE ratio)
        mfe = signal.get('max_favorable_excursion_pct', 0.0)
        mae = signal.get('max_adverse_excursion_pct', 0.0)
        if mfe is not None and mae is not None:
            components['r_quality'] = self._calculate_quality_reward(mfe, mae)
        
        # Componente 5: Reward por timing de entrada
        if evolutions and len(evolutions) > 0:
            components['r_timing'] = self._calculate_timing_reward(
                signal, evolutions
            )
        
        # Componente 6: Reward por gestão (trailing stop, parciais)
        components['r_management'] = self._calculate_management_reward(
            signal, evolutions
        )
        
        # Calcular reward total
        total_reward = sum(components.values())
        total_reward = np.clip(total_reward, MIN_REWARD, MAX_REWARD)
        
        result = {
            'total': total_reward,
            **components
        }
        
        logger.debug(f"Signal reward calculado: total={total_reward:.2f}, "
                    f"pnl={components['r_pnl']:.2f}, "
                    f"quality={components['r_quality']:.2f}, "
                    f"timing={components['r_timing']:.2f}")
        
        return result
    
    def _calculate_pnl_reward(self, r_multiple: float) -> float:
        """
        Calcula reward baseado no R-multiple realizado.
        
        Args:
            r_multiple: R-multiple do trade
            
        Returns:
            Reward por PnL
        """
        # Reward base proporcional ao R-multiple
        reward = r_multiple * PNL_REWARD_SCALE
        
        # Bonus progressivo para R-multiples altos (incentiva deixar lucros correr)
        if r_multiple > 3.0:
            reward += R_MULTIPLE_BONUS_HIGH
        elif r_multiple > 2.0:
            reward += R_MULTIPLE_BONUS_MID
        elif r_multiple > 1.0:
            reward += R_MULTIPLE_BONUS_LOW
        
        return reward
    
    def _calculate_partial_bonus(self, signal: Dict[str, Any], 
                                 evolutions: List[Dict[str, Any]],
                                 exit_reason: str) -> float:
        """
        Calcula bonus por executar parciais no momento certo.
        
        Args:
            signal: Dados do sinal
            evolutions: Snapshots de evolução
            exit_reason: Motivo de saída
            
        Returns:
            Bonus por parcial
        """
        # Verificar se houve parciais nos snapshots
        partial_events = [
            ev for ev in evolutions 
            if ev.get('event_type') in ['PARTIAL_1', 'PARTIAL_2']
        ]
        
        if not partial_events:
            return 0.0
        
        # Bonus por cada parcial executada
        bonus = len(partial_events) * PARTIAL_BONUS
        
        # Bonus extra se a parcial foi executada próximo ao MFE
        mfe = signal.get('max_favorable_excursion_pct', 0.0)
        if mfe and mfe > 0:
            for partial in partial_events:
                unrealized_pnl = partial.get('unrealized_pnl_pct', 0.0)
                if unrealized_pnl and abs(unrealized_pnl - mfe) < 1.0:  # Dentro de 1%
                    bonus += 0.3  # Bonus extra por timing perfeito
        
        return bonus
    
    def _calculate_stop_penalty(self, signal: Dict[str, Any],
                               evolutions: List[Dict[str, Any]]) -> float:
        """
        Calcula penalidade por stop loss, proporcional ao quão longe o preço foi.
        
        Args:
            signal: Dados do sinal
            evolutions: Snapshots de evolução
            
        Returns:
            Penalidade por stop
        """
        mfe = signal.get('max_favorable_excursion_pct', 0.0)
        
        # Penalidade base
        penalty = STOP_LOSS_PENALTY_BASE
        
        # Penalidade extra se o trade esteve muito no lucro antes de virar
        # (indica má gestão ou falta de trailing stop)
        if mfe and mfe > 2.0:  # Esteve 2%+ no lucro
            penalty -= mfe * 0.2  # Penalidade proporcional
        
        return penalty
    
    def _calculate_quality_reward(self, mfe: float, mae: float) -> float:
        """
        Calcula reward baseado na qualidade do sinal (ratio MFE/MAE).
        
        Args:
            mfe: Max Favorable Excursion (%)
            mae: Max Adverse Excursion (%)
            
        Returns:
            Reward por qualidade
        """
        if mae == 0 or mae is None:
            # Trade perfeito que nunca foi contra
            if mfe and mfe > 0:
                return QUALITY_REWARD_SCALE * 2.0
            return 0.0
        
        # Ratio MFE/MAE indica qualidade do sinal
        # Alto ratio = sinal foi fortemente a favor vs. contra
        ratio = abs(mfe) / abs(mae) if mae != 0 else 0
        
        # Normalizar para escala de reward
        # Ratio > 3.0 é excelente, ratio < 1.0 é ruim
        if ratio > 3.0:
            reward = QUALITY_REWARD_SCALE * 1.5
        elif ratio > 2.0:
            reward = QUALITY_REWARD_SCALE * 1.0
        elif ratio > 1.0:
            reward = QUALITY_REWARD_SCALE * 0.5
        else:
            reward = QUALITY_REWARD_SCALE * -0.5  # Penalidade leve
        
        return reward
    
    def _calculate_timing_reward(self, signal: Dict[str, Any],
                                evolutions: List[Dict[str, Any]]) -> float:
        """
        Calcula reward por timing de entrada (comparar entry vs melhor preço).
        
        Args:
            signal: Dados do sinal
            evolutions: Snapshots de evolução
            
        Returns:
            Reward por timing
        """
        if not evolutions:
            return 0.0
        
        entry_price = signal.get('entry_price', 0.0)
        direction = signal.get('direction', 'LONG')
        
        if not entry_price:
            return 0.0
        
        # Encontrar melhor preço possível na janela
        prices = [ev.get('current_price', 0.0) for ev in evolutions if ev.get('current_price')]
        
        if not prices:
            return 0.0
        
        if direction == 'LONG':
            best_price = min(prices)  # Menor preço seria melhor para LONG
            timing_quality = (entry_price - best_price) / entry_price * 100
        else:  # SHORT
            best_price = max(prices)  # Maior preço seria melhor para SHORT
            timing_quality = (best_price - entry_price) / entry_price * 100
        
        # Reward proporcional à qualidade do timing
        # timing_quality < 0 = entrada ótima, timing_quality > 0 = poderia ser melhor
        if timing_quality <= 0:
            reward = TIMING_REWARD_SCALE * 1.0  # Entrada perfeita
        elif timing_quality < 1.0:
            reward = TIMING_REWARD_SCALE * 0.5  # Boa entrada
        elif timing_quality < 2.0:
            reward = TIMING_REWARD_SCALE * 0.2  # Entrada ok
        else:
            reward = 0.0  # Entrada ruim, sem reward
        
        return reward
    
    def _calculate_management_reward(self, signal: Dict[str, Any],
                                    evolutions: List[Dict[str, Any]]) -> float:
        """
        Calcula reward por gestão do trade (trailing stop, parciais).
        
        Args:
            signal: Dados do sinal
            evolutions: Snapshots de evolução
            
        Returns:
            Reward por gestão
        """
        if not evolutions:
            return 0.0
        
        reward = 0.0
        
        # Verificar eventos de gestão nos snapshots
        trailing_events = [
            ev for ev in evolutions 
            if ev.get('event_type') in ['STOP_MOVED', 'TRAILING_ACTIVATED']
        ]
        
        # Bonus por usar trailing stop
        if trailing_events:
            reward += MANAGEMENT_REWARD_SCALE * 1.0
            
            # Bonus extra se trailing stop protegeu lucro
            exit_reason = signal.get('exit_reason', '')
            if 'trailing' in exit_reason.lower():
                pnl_pct = signal.get('pnl_pct', 0.0)
                if pnl_pct and pnl_pct > 0:
                    reward += MANAGEMENT_REWARD_SCALE * 0.5
        
        # Verificar se parciais foram usadas para proteger lucro
        partial_events = [
            ev for ev in evolutions 
            if ev.get('event_type') in ['PARTIAL_1', 'PARTIAL_2']
        ]
        
        if partial_events:
            # Verificar se houve eventos após a parcial
            last_partial_idx = max(
                i for i, ev in enumerate(evolutions)
                if ev.get('event_type') in ['PARTIAL_1', 'PARTIAL_2']
            )
            
            # Se trade durou após parcial e finalizou positivo, bonus extra
            if last_partial_idx < len(evolutions) - 2:
                pnl_pct = signal.get('pnl_pct', 0.0)
                if pnl_pct and pnl_pct > 0:
                    reward += MANAGEMENT_REWARD_SCALE * 0.3
        
        return reward
