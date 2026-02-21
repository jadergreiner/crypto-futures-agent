"""
Calculadora de recompensa simplificada para o agente RL.
Round 5: Agora com recompensa por "ficar fora do mercado" em condições ruins.
"""

import logging
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Constantes de reward
PNL_SCALE = 10.0          # Fator de escala do PnL realizado
R_BONUS_THRESHOLD_HIGH = 3.0  # Threshold para bonus alto de R-multiple
R_BONUS_THRESHOLD_LOW = 2.0   # Threshold para bonus baixo de R-multiple
R_BONUS_HIGH = 1.0        # Bonus para R > 3.0
R_BONUS_LOW = 0.5          # Bonus para R > 2.0
HOLD_BASE_BONUS = 0.05    # Bonus base por step segurando posição lucrativa
HOLD_SCALING = 0.1         # Fator de escala proporcional ao lucro
HOLD_LOSS_PENALTY = -0.02  # Penalidade por segurar posição perdedora
INVALID_ACTION_PENALTY = -0.5  # Penalidade por ação inválida (inclui CLOSE prematuro)

# Constantes para recompensa por "ficar fora do mercado"
OUT_OF_MARKET_THRESHOLD_DD = 2.0  # Drawdown % acima do qual fica fora é recompensado
OUT_OF_MARKET_BONUS = 0.10         # Bonus diário por manter capital em segurança
OUT_OF_MARKET_LOSS_AVOIDANCE = 0.15  # Bonus por evitar operações ruins
EXCESS_INACTIVITY_PENALTY = 0.03   # Penalidade por ficar fora quando não deveria (valor positivo, será subtraído)

REWARD_CLIP = 10.0         # Limite de clipping do reward total


class RewardCalculator:
    """
    Calcula recompensa simplificada para treinar o agente.
    
    Round 5: 4 componentes principais:
    1. r_pnl: PnL realizado (fechamento de trade)
    2. r_hold_bonus: Incentivo assimétrico para manter posições lucrativas
    3. r_invalid_action: Penalidade por ações inválidas
    4. r_out_of_market: Recompensa por ficar fora em condições ruins (NOVO)
    """
    
    def __init__(self):
        """Inicializa reward calculator com componente de "out of market"."""
        self.weights = {
            'r_pnl': 1.0,
            'r_hold_bonus': 1.0,
            'r_invalid_action': 1.0,
            'r_out_of_market': 1.0  # NOVO: Apendre a ficar fora prudentemente
        }
        logger.info("Reward Calculator initialized (Round 5 - com aprendizado de 'ficar fora')")
    
    def calculate(self, trade_result: Optional[Dict[str, Any]] = None,
                  position_state: Optional[Dict[str, Any]] = None,
                  portfolio_state: Optional[Dict[str, Any]] = None,
                  action_valid: bool = True,
                  trades_recent: Optional[list] = None,
                  flat_steps: int = 0) -> Dict[str, float]:
        """
        Calcula recompensa total e componentes.
        
        Args:
            trade_result: Resultado de trade (se fechado)
            position_state: Estado atual da posição
            portfolio_state: Estado do portfólio
            action_valid: Se a ação foi válida
            trades_recent: Lista de trades recentes para métricas
            flat_steps: Número de candles sem posição aberta
            
        Returns:
            Dicionário com reward total e componentes
        """
        components = {
            'r_pnl': 0.0,
            'r_hold_bonus': 0.0,
            'r_invalid_action': 0.0,
            'r_out_of_market': 0.0
        }
        
        # Componente 1: PnL realizado (apenas quando trade é fechado)
        if trade_result:
            pnl_pct = trade_result.get('pnl_pct', 0)
            components['r_pnl'] = pnl_pct * PNL_SCALE
            
            # Bonus para R-multiples altos (incentiva deixar lucros correr)
            r_multiple = trade_result.get('r_multiple', 0)
            if r_multiple > R_BONUS_THRESHOLD_HIGH:
                components['r_pnl'] += R_BONUS_HIGH
            elif r_multiple > R_BONUS_THRESHOLD_LOW:
                components['r_pnl'] += R_BONUS_LOW
        
        # Componente 2: Hold bonus assimétrico
        if position_state and position_state.get('has_position', False):
            pnl_pct = position_state.get('pnl_pct', 0)
            momentum = position_state.get('pnl_momentum', 0)
            
            if pnl_pct > 0:
                # Bonus proporcional ao lucro + momentum positivo extra
                components['r_hold_bonus'] = HOLD_BASE_BONUS + pnl_pct * HOLD_SCALING
                if momentum > 0:
                    components['r_hold_bonus'] += momentum * 0.05  # Bonus extra se momentum positivo
            elif pnl_pct < -2.0:
                # Penalidade leve por segurar posição muito perdedora
                components['r_hold_bonus'] = HOLD_LOSS_PENALTY
        
        # Componente 3: Ação inválida (inclui tentativa de CLOSE prematuro)
        if not action_valid:
            components['r_invalid_action'] = INVALID_ACTION_PENALTY
        
        # Componente 4 (NOVO): Recompensa por "ficar fora do mercado" prudentemente
        # O agente aprende que às vezes ficar fora é melhor do que operar
        if portfolio_state and not (position_state and position_state.get('has_position', False)):
            current_dd = portfolio_state.get('current_drawdown_pct', 0)
            trades_24h = portfolio_state.get('trades_24h', 0)
            
            # Suprimento 1: Ficar fora em drawdown
            # Se drawdown > threshold, recompensar por não abrir nova posição
            if current_dd >= OUT_OF_MARKET_THRESHOLD_DD:
                components['r_out_of_market'] = OUT_OF_MARKET_LOSS_AVOIDANCE
                logger.debug(f"Out-of-market bonus (drawdown protection): DD={current_dd:.2f}% > {OUT_OF_MARKET_THRESHOLD_DD}%")
            
            # Suprimento 2: Ficar fora após operações ruins
            # Se múltiplos trades perdedores nas últimas 24h, recompensar por descansar
            if trades_24h >= 3 and trade_result is None:
                # Agente está sendo cauteloso após operações ruins
                components['r_out_of_market'] += OUT_OF_MARKET_BONUS * (trades_24h / 10.0)
                logger.debug(f"Out-of-market bonus (rest after losses): {trades_24h} trades recentes")
            
            # Penalidade leve: Ficar muito fora pode ser ruim (ótimo = estar operando quando há oportunidade)
            if flat_steps > 96:  # Mais de 96 H4 candles = ~16 dias
                components['r_out_of_market'] -= EXCESS_INACTIVITY_PENALTY * (flat_steps / 100.0)
                logger.debug(f"Excess inactivity penalty: {flat_steps} candles sem posição")
        
        # Calcular reward total com pesos
        total_reward = sum(
            components[key] * self.weights[key] 
            for key in components.keys()
        )
        
        # Clipar reward total para faixa adequada ao PPO
        total_reward = np.clip(total_reward, -REWARD_CLIP, REWARD_CLIP)
        
        result = {
            'total': total_reward,
            **components
        }
        
        logger.debug(f"Reward calculated: total={total_reward:.4f}, "
                    f"pnl={components['r_pnl']:.2f}, "
                    f"hold={components['r_hold_bonus']:.3f}, "
                    f"out_of_market={components['r_out_of_market']:.3f}")
        
        return result
    
    def calculate_sparse_reward(self, trade_result: Dict[str, Any]) -> float:
        """
        Recompensa esparsa: apenas no fechamento do trade.
        
        Args:
            trade_result: Dicionário com resultado do trade fechado
            
        Returns:
            R-multiple do trade (pnl / initial_risk)
        """
        r_multiple = trade_result.get('r_multiple', 0)
        return r_multiple
    
    def get_weights(self) -> Dict[str, float]:
        """Retorna pesos dos componentes."""
        return self.weights.copy()
    
    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """Atualiza pesos dos componentes."""
        self.weights.update(new_weights)
        logger.info(f"Reward weights updated: {self.weights}")
