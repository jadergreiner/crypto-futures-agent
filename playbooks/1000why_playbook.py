"""
Playbook específico para 1000WHY (1000WHYUSDT).
Token meme/comunidade com dinâmica especulativa.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class WHYPlaybook(BasePlaybook):
    """
    Playbook para 1000WHY - Memecoin de dinâmica comunitária.
    Beta muito elevado (4.2), requer confluência máxima.
    """

    def __init__(self):
        super().__init__("1000WHYUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para 1000WHY.

        Memecoins beneficiam de:
        - Hype comunitário (social sentiment)
        - Breakouts técnicos claros
        - Altseason extrema
        """
        adjustments = {}

        # Strong bonus para breakout acima de resistência
        if 'breakout_confirmed' in context and context['breakout_confirmed']:
            adjustments['breakout'] = +1.5
            logger.debug("1000WHY: +1.5 confluence for breakout")

        # Bonus para sentimento social positivo
        if 'social_sentiment' in context and context['social_sentiment'] > 0.7:
            adjustments['social_sentiment'] = +1.0

        # Bonus em altseason muito forte
        if 'altseason_intensity' in context and context['altseason_intensity'] > 0.75:
            adjustments['extreme_altseason'] = +1.2

        # Heavy penalty em períodos de risco reduzido
        if 'market_fear_index' in context and context['market_fear_index'] > 70:
            adjustments['fear_penalty'] = -1.5

        return adjustments

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para 1000WHY.

        Beta extremo (4.2) - posições muito reduzidas. Use com cautela.
        """
        adjustments = {
            'position_size_multiplier': 0.50,  # 50% do tamanho padrão
            'stop_multiplier': 0.80  # Stop bem apertado
        }

        # Em consolidação, praticamente não operar
        if context.get('market_regime') == "CONSOLIDATION":
            adjustments['position_size_multiplier'] = 0.30

        # Em downtrend, não operar
        if context.get('market_regime') == "DOWNTREND":
            adjustments['position_size_multiplier'] = 0.0  # Não operar

        return adjustments

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo para 1000WHY.

        Memecoin puro: fase de pump ou dump.
        """
        breakout = current_data.get('breakout_confirmed', False)
        social = current_data.get('social_sentiment', 0)
        altseason = current_data.get('altseason_intensity', 0)

        if breakout and social > 0.7 and altseason > 0.7:
            return "PUMP_PHASE"
        elif current_data.get('d1_bias') == "BEARISH":
            return "DUMP_PHASE"
        else:
            return "DORMANT"

    def should_trade(self, market_regime: str, d1_bias: str,
                    btc_bias: str = None) -> bool:
        """
        1000WHY só é viável em altseason extrema com breakouts claros.
        """
        if d1_bias == "BEARISH":
            return False
        if market_regime not in ["STRONG_UPTREND", "ALTSEASON"]:
            return False
        return True

    def get_confluence_requirements(self) -> Dict[str, Any]:
        """Requisitos de confluência para 1000WHY."""
        return {
            "min_confluence_score": 11,  # Exigir confluência muito alta
            "preferred_confluence_score": 12,  # Preferir máxima confluência
        }
