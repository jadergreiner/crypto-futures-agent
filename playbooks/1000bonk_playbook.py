"""
Playbook específico para 1000BONK (1000BONKUSDT).
Memecoin com dinâmica comunitária elevada.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class BONKPlaybook(BasePlaybook):
    """
    Playbook para 1000BONK - Memecoin de dinâmica comunitária extrema.
    Beta extremo (4.5), requer confluência máxima e regras rigorosas.
    """

    def __init__(self):
        super().__init__("1000BONKUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para 1000BONK.

        1000BONK beneficia de:
        - Breakouts muito claros acima de resistência forte
        - Hype comunitário e social sentiment extremo
        - Altseason extreme
        """
        adjustments = {}

        # Very strong bonus para breakout maior
        if 'breakout_confirmed' in context and context['breakout_confirmed']:
            adjustments['breakout'] = +1.8
            logger.debug("1000BONK: +1.8 confluence for confirmed breakout")

        # Strong bonus para social sentiment extremo
        if 'social_sentiment' in context and context['social_sentiment'] > 0.80:
            adjustments['social_sentiment'] = +1.2

        # Strong bonus para altseason extrema
        if 'altseason_intensity' in context and context['altseason_intensity'] > 0.80:
            adjustments['extreme_altseason'] = +1.5

        # Devastating penalty em períodos de risco baixo/médio
        if 'market_fear_index' in context and context['market_fear_index'] > 65:
            adjustments['fear_penalty'] = -2.0

        return adjustments

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para 1000BONK.

        Beta extremo absoluto (4.5) - posições mínimas. APENAS breakouts muito claros.
        """
        adjustments = {
            'position_size_multiplier': 0.40,  # 40% do tamanho padrão (muito reduzido)
            'stop_multiplier': 0.75  # Stop extremamente apertado
        }

        # Em consolidação, praticamente não operar
        if context.get('market_regime') == "CONSOLIDATION":
            adjustments['position_size_multiplier'] = 0.15

        # Em downtrend, NUNCA operar
        if context.get('market_regime') == "DOWNTREND":
            adjustments['position_size_multiplier'] = 0.0  # Bloquear operação

        # Em uptrend suave, reduzir bastante
        if context.get('market_regime') == "MILD_UPTREND":
            adjustments['position_size_multiplier'] = 0.25

        return adjustments

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo para 1000BONK.

        Memecoin extremo: apenas pump ou dump ou dormência.
        """
        breakout = current_data.get('breakout_confirmed', False)
        social = current_data.get('social_sentiment', 0)
        altseason = current_data.get('altseason_intensity', 0)

        if breakout and social > 0.80 and altseason > 0.80:
            return "EXTREME_PUMP_PHASE"
        elif current_data.get('d1_bias') == "BEARISH":
            return "EXTREME_DUMP_PHASE"
        else:
            return "DEAD"

    def should_trade(self, market_regime: str, d1_bias: str,
                    btc_bias: str = None) -> bool:
        """
        1000BONK APENAS em breakouts em altseason extrema.
        Regime deve ser strong uptrend ou altseason.
        """
        if d1_bias != "BULLISH":
            return False
        if market_regime not in ["STRONG_UPTREND", "ALTSEASON"]:
            return False
        # Exigir breakout confirmado além de regime
        return True

    def get_confluence_requirements(self) -> Dict[str, Any]:
        """Requisitos de confluência para 1000BONK - MÁXIMO."""
        return {
            "min_confluence_score": 12,  # Exigir confluência MÁXIMA
            "preferred_confluence_score": 13,  # Idealmente acima do máximo
            "breakout_required": True,  # Breakout é obrigatório
        }
