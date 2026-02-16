"""
Calculadora de recompensa multi-componente para o agente RL.
"""

import logging
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Constantes para amplificação e componentes de reward
PNL_AMPLIFICATION_FACTOR = 10  # Fator de amplificação do PnL realizado
UNREALIZED_PNL_FACTOR = 0.1    # Fator de sinal de PnL não realizado (menor que realizado)
INACTIVITY_THRESHOLD = 20      # Steps sem posição antes de aplicar penalidade (~80h em H4)
INACTIVITY_PENALTY_RATE = 0.01 # Taxa de penalidade por step de inatividade
INACTIVITY_MAX_PENALTY_STEPS = 30  # Cap máximo de steps penalizados (penalidade máxima = -0.3)


class RewardCalculator:
    """
    Calcula recompensa multi-componente para treinar o agente.
    Combina PnL, gestão de risco, consistência e penalidades.
    """
    
    def __init__(self):
        """Inicializa reward calculator."""
        self.weights = {
            'r_pnl': 1.0,
            'r_risk': 1.0,
            'r_consistency': 0.5,
            'r_overtrading': 0.5,
            'r_hold_bonus': 0.3,
            'r_invalid_action': 0.2,
            'r_unrealized': 0.3,
            'r_inactivity': 0.3
        }
        logger.info("Reward Calculator initialized")
    
    def calculate(self, trade_result: Optional[Dict[str, Any]] = None,
                  position_state: Optional[Dict[str, Any]] = None,
                  portfolio_state: Optional[Dict[str, Any]] = None,
                  action_valid: bool = True,
                  trades_recent: Optional[list] = None) -> Dict[str, float]:
        """
        Calcula recompensa total e componentes.
        
        Args:
            trade_result: Resultado de trade (se fechado)
            position_state: Estado atual da posição
            portfolio_state: Estado do portfólio
            action_valid: Se a ação foi válida
            trades_recent: Lista de trades recentes para métricas
            
        Returns:
            Dicionário com reward total e componentes
        """
        components = {
            'r_pnl': 0.0,
            'r_risk': 0.0,
            'r_consistency': 0.0,
            'r_overtrading': 0.0,
            'r_hold_bonus': 0.0,
            'r_invalid_action': 0.0,
            'r_unrealized': 0.0,
            'r_inactivity': 0.0
        }
        
        # Componente 1: PnL (normalizado para faixa adequada ao PPO)
        if trade_result:
            pnl_pct = trade_result.get('pnl_pct', 0)
            components['r_pnl'] = pnl_pct * PNL_AMPLIFICATION_FACTOR  # Amplificar sinal
            
            # Bonus para R-multiples positivos (ajustado proporcionalmente)
            r_multiple = trade_result.get('r_multiple', 0)
            if r_multiple > 3.0:
                components['r_pnl'] += 0.5  # Bonus extra para 3R+
            elif r_multiple > 2.0:
                components['r_pnl'] += 0.2  # Bonus para 2R+
        
        # Componente 2: Gestão de Risco
        if position_state:
            # Penalidade se não tem stop loss
            if not position_state.get('has_stop_loss', True):
                components['r_risk'] -= 2.0
            
            # Penalidade se stop foi atingido
            if trade_result and trade_result.get('exit_reason') == 'stop_loss':
                components['r_risk'] -= 0.5
            
            # Penalidade se drawdown alto
            if portfolio_state:
                current_dd = portfolio_state.get('current_drawdown_pct', 0)
                if current_dd > 10:
                    components['r_risk'] -= 5.0
                elif current_dd > 5:
                    components['r_risk'] -= 2.0
        
        # Componente 3: Consistência (Sharpe ratio rolante)
        if trades_recent and len(trades_recent) >= 20:
            returns = [t.get('pnl_pct', 0) for t in trades_recent[-20:]]
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return > 0:
                sharpe = mean_return / std_return
                components['r_consistency'] = sharpe * 0.1
        
        # Componente 4: Overtrading
        if portfolio_state:
            trades_24h = portfolio_state.get('trades_24h', 0)
            if trades_24h > 3:
                excess_trades = trades_24h - 3
                components['r_overtrading'] = -0.3 * excess_trades
        
        # Componente 5: Hold bonus (recompensar holding de posições lucrativas)
        if position_state and position_state.get('has_position', False):
            pnl_pct = position_state.get('pnl_pct', 0)
            if pnl_pct > 0:
                components['r_hold_bonus'] = 0.01  # Pequeno bonus por candle
        
        # Componente 6: Unrealized PnL (sinal contínuo enquanto posição aberta)
        if position_state and position_state.get('has_position', False):
            unrealized_pnl = position_state.get('pnl_pct', 0)
            components['r_unrealized'] = unrealized_pnl * UNREALIZED_PNL_FACTOR
        
        # Componente 7: Penalidade por inatividade prolongada (incentiva exploração)
        if position_state and not position_state.get('has_position', False):
            flat_steps = position_state.get('flat_steps', 0)
            if flat_steps > INACTIVITY_THRESHOLD:
                excess_steps = min(flat_steps - INACTIVITY_THRESHOLD, INACTIVITY_MAX_PENALTY_STEPS)
                components['r_inactivity'] = -INACTIVITY_PENALTY_RATE * excess_steps
        
        # Componente 8: Ação inválida
        if not action_valid:
            components['r_invalid_action'] = -0.1
        
        # Calcular reward total com pesos
        total_reward = sum(
            components[key] * self.weights[key] 
            for key in components.keys()
        )
        
        # Clipar reward total para faixa adequada ao PPO [-10, +10]
        total_reward = np.clip(total_reward, -10.0, 10.0)
        
        result = {
            'total': total_reward,
            **components
        }
        
        logger.debug(f"Reward calculated: total={total_reward:.4f}, "
                    f"pnl={components['r_pnl']:.2f}, "
                    f"risk={components['r_risk']:.2f}")
        
        return result
    
    def calculate_sparse_reward(self, trade_result: Dict[str, Any]) -> float:
        """
        Recompensa esparsa: apenas no fechamento do trade.
        Alternativa mais simples para treinar.
        
        Args:
            trade_result: Resultado do trade
            
        Returns:
            Reward baseado no R-multiple
        """
        r_multiple = trade_result.get('r_multiple', 0)
        return r_multiple
    
    def get_weights(self) -> Dict[str, float]:
        """Retorna pesos dos componentes."""
        return self.weights.copy()
    
    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """
        Atualiza pesos dos componentes.
        
        Args:
            new_weights: Novos pesos
        """
        self.weights.update(new_weights)
        logger.info(f"Reward weights updated: {self.weights}")
