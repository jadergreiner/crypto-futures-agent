"""
Playbook específico para HYPER (HYPERUSDT).
Token com dinâmica de alta volatilidade e narrativa em desenvolvimento.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class HYPERPlaybook(BasePlaybook):
    """
    Playbook para HYPER - Token especulativo de alta volatilidade.
    Beta muito elevado (3.5), requer confluência alta.
    """

    def __init__(self):
        super().__init__("HYPERUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para HYPER.

        HYPER beneficia de:
        - Breakouts e estrutura técnica clara
        - Altseason forte
        - Volume crescente
        """
        adjustments = {}

        # Strong bonus para breakout
        if 'breakout_confirmed' in context and context['breakout_confirmed']:
            adjustments['breakout'] = +1.2
            logger.debug("HYPER: +1.2 confluence for breakout")

        # Bonus para altseason
        if 'altseason_intensity' in context and context['altseason_intensity'] > 0.65:
            adjustments['altseason'] = +1.0

        # Bonus para EMA alignment forte
        if 'ema_alignment_score' in context and context['ema_alignment_score'] >= 4:
            adjustments['ema_alignment'] = +0.5

        # Heavy penalty em períodos de fraco risco
        if 'market_fear_index' in context and context['market_fear_index'] > 70:
            adjustments['fear_penalty'] = -1.2

        return adjustments

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para HYPER.

        Beta elevado (3.5) - posições reduzidas. Volatilidade extrema.
        """
        adjustments = {
            'position_size_multiplier': 0.60,  # 60% do tamanho padrão
            'stop_multiplier': 0.85  # Stop bem apertado
        }

        # Em consolidação, reduzir muito
        if context.get('market_regime') == "CONSOLIDATION":
            adjustments['position_size_multiplier'] = 0.40

        # Em downtrend, praticamente não operar
        if context.get('market_regime') == "DOWNTREND":
            adjustments['position_size_multiplier'] = 0.25

        return adjustments

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo para HYPER.

        HYPER é especulativo: fase de breakout ou dormência.
        """
        breakout = current_data.get('breakout_confirmed', False)
        ema_alignment = current_data.get('ema_alignment_score', 0)
        altseason = current_data.get('altseason_intensity', 0)

        if breakout and altseason > 0.65 and ema_alignment >= 4:
            return "BREAKOUT_PHASE"
        elif ema_alignment <= -3:
            return "BREAKDOWN_PHASE"
        else:
            return "DORMANT"

    def should_trade(self, market_regime: str, d1_bias: str,
                    btc_bias: str = None) -> bool:
        """
        HYPER só é viável em uptrends fortes e altseason.
        """
        if d1_bias == "BEARISH":
            return False
        if market_regime not in ["STRONG_UPTREND", "ALTSEASON"]:
            return False
        return True

    def get_confluence_requirements(self) -> Dict[str, Any]:
        """Requisitos de confluência para HYPER."""
        return {
            "min_confluence_score": 10,  # Confluência alta
            "preferred_confluence_score": 12,  # Preferir máxima confluência
        }
