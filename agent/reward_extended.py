"""
Extended reward function for M2-016.3.

Adiciona componentes de Sharpe ratio, drawdown e recovery time à RewardCalculator.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class RewardCalculatorExtended:
    """
    Calculadora de recompensa estendida com componentes de Sharpe, drawdown e recovery.

    Componentes:
    1. r_pnl: PnL realizado (base)
    2. r_hold_bonus: Incentivo para manter posições lucrativas
    3. r_sharpe: Bonus por Sharpe > 1.0
    4. r_drawdown: Penalidade por drawdown > 10%
    5. r_recovery: Bonus/penalidade por velocidade de recuperação
    6. r_invalid_action: Penalidade para ações inválidas
    """

    def __init__(self):
        """Inicializa calculadora com pesos dos componentes."""
        self.weights = {
            'r_pnl': 1.0,               # Base (não mudar)
            'r_hold_bonus': 1.0,        # Equalizado
            'r_sharpe': 0.5,            # Metade do peso base
            'r_drawdown': 0.7,          # Penalidade moderada
            'r_recovery': 0.3,          # Incentivo leve
            'r_invalid_action': 1.0,    # Full penalidade
        }

        # Thresholds e bounds
        self.pnl_scale = 10.0
        self.hold_base_bonus = 0.05
        self.hold_scaling = 0.1
        self.hold_loss_penalty = -0.02
        self.invalid_action_penalty = -0.5
        self.reward_clip = 10.0

    def calculate_sharpe(self, returns: list[float], periods: int = 20) -> float:
        """Calcula Sharpe ratio sobre janela de retornos recentes."""
        if len(returns) < periods:
            returns_window = returns
        else:
            returns_window = returns[-periods:]

        if len(returns_window) == 0:
            return 0.0

        mean_return = np.mean(returns_window)
        std_return = np.std(returns_window)

        # Evitar divisão por zero
        if std_return < 1e-8:
            sharpe = 0.0 if mean_return <= 0 else 100.0
        else:
            sharpe = mean_return / std_return

        return float(sharpe)

    def calculate_drawdown(
        self, capital_history: list[float]
    ) -> tuple[float, float, float]:
        """Calcula drawdown máximo e recuperação."""
        if len(capital_history) == 0:
            return 0.0, 0.0, 0.0

        capital_array = np.array(capital_history)
        running_max = np.maximum.accumulate(capital_array)
        drawdown = (capital_array - running_max) / running_max

        # Drawdown máximo
        max_dd = float(np.min(drawdown)) if len(drawdown) > 0 else 0.0

        # Índices de trough e recuperação subsequente
        trough_idx = np.argmin(drawdown) if len(drawdown) > 0 else 0
        peak_before_trough = running_max[trough_idx]

        # Encontrar ponto de recuperação (volta ao pico anterior)
        recovery_idx = None
        for i in range(trough_idx + 1, len(capital_array)):
            if capital_array[i] >= peak_before_trough:
                recovery_idx = i
                break

        recovery_steps = recovery_idx - trough_idx if recovery_idx is not None else float('inf')

        return float(abs(max_dd)), float(max_dd), float(recovery_steps)

    def calculate_recovery_bonus(self, recovery_steps: float) -> float:
        """Calcula bonus por velocidade de recuperação."""
        if np.isinf(recovery_steps):
            # Ainda não se recuperou
            return -0.1

        if recovery_steps < 20:  # Recuperação rápida
            return 0.2
        elif recovery_steps < 50:  # Recuperação moderada
            return 0.1
        else:  # Recuperação lenta
            return -0.1

    def calculate_reward_extended(
        self,
        traded: bool,
        pnl: float,
        capital_history: list[float],
        returns_history: list[float],
        action_valid: bool = True,
    ) -> dict[str, float]:
        """
        Calcula reward estendido com todos os componentes.

        Args:
            traded: Se houve trade
            pnl: PnL do trade
            capital_history: Histórico de capital
            returns_history: Histórico de retornos
            action_valid: Se a ação foi válida

        Returns:
            Dict com componentes e total
        """
        components = {}

        # 1. PnL
        components['r_pnl'] = self.pnl_scale * pnl if traded else 0.0

        # 2. Hold bonus
        if traded and pnl > 0:
            components['r_hold_bonus'] = (
                self.hold_base_bonus + (self.hold_scaling * pnl)
            )
        elif traded and pnl < 0:
            components['r_hold_bonus'] = self.hold_loss_penalty
        else:
            components['r_hold_bonus'] = 0.0

        # 3. Sharpe
        sharpe = self.calculate_sharpe(returns_history, periods=20)
        components['r_sharpe'] = 0.5 if sharpe > 1.0 else (sharpe / 2.0 if sharpe > 0 else 0.0)

        # 4. Drawdown
        max_dd_abs, max_dd_pct, recovery_steps = self.calculate_drawdown(capital_history)
        # Penaliza drawdown forte
        if max_dd_abs > 0.10:  # > 10%
            components['r_drawdown'] = -0.3 * max_dd_abs
        else:
            components['r_drawdown'] = 0.0

        # 5. Recovery
        components['r_recovery'] = self.calculate_recovery_bonus(recovery_steps)

        # 6. Invalid action
        components['r_invalid_action'] = self.invalid_action_penalty if not action_valid else 0.0

        # Calcular total com pesos
        total_reward = sum(
            components.get(key, 0.0) * self.weights.get(key, 1.0)
            for key in self.weights.keys()
        )

        # Clip
        total_reward = np.clip(total_reward, -self.reward_clip, self.reward_clip)

        components['total'] = float(total_reward)
        components['sharpe'] = float(sharpe)
        components['max_dd_pct'] = float(max_dd_pct * 100)  # Em %
        components['recovery_steps'] = float(recovery_steps) if not np.isinf(recovery_steps) else -1.0

        return components

    def get_weights(self) -> dict[str, float]:
        """Retorna dict com pesos atuais para logging."""
        return dict(self.weights)

    def set_weights(self, weights: dict[str, float]) -> None:
        """Atualiza pesos dos componentes."""
        for key, value in weights.items():
            if key in self.weights:
                self.weights[key] = float(value)
                logger.info(f"Peso {key} atualizado para {value}")
