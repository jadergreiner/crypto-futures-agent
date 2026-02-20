"""
Playbook específico para CELO (CELOUSDT).
Layer 1 orientado a pagamentos móveis.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class CELOPlaybook(BasePlaybook):
    """
    Playbook para CELO - Layer 1 com foco em mobile payments.
    """

    def __init__(self):
        super().__init__("CELOUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para CELO.

        CELO beneficia de:
        - Narrativa de Layer 1 e pagamentos móveis
        - Ciclos de altseason
        - Adoção em mercados emergentes
        """
        adjustments = {}

        # Bonus para altseason
        if 'altseason_intensity' in context and context['altseason_intensity'] > 0.55:
            adjustments['altseason'] = +0.8
            logger.debug("CELO: +0.8 confluence for altseason")

        # Bonus para estrutura técnica clara
        if 'structure_clarity' in context and context['structure_clarity'] > 0.6:
            adjustments['structure'] = +0.4

        # Bonus para ema alignment
        if 'ema_alignment_score' in context and context['ema_alignment_score'] >= 3:
            adjustments['ema_alignment'] = +0.3

        # Penalty em medo extremo
        if 'market_fear_index' in context and context['market_fear_index'] > 75:
            adjustments['fear_penalty'] = -0.7

        return adjustments

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para CELO.

        CELO tem beta moderado-alto (2.7).
        """
        adjustments = {
            'position_size_multiplier': 0.80,  # 80% do tamanho padrão
            'stop_multiplier': 0.93  # Stop moderadamente apertado
        }

        # Em consolidação, manter posição
        if context.get('market_regime') == "CONSOLIDATION":
            adjustments['position_size_multiplier'] = 0.65

        # Em downtrend, reduzir
        if context.get('market_regime') == "DOWNTREND":
            adjustments['position_size_multiplier'] = 0.48

        return adjustments

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo para CELO.

        CELO segue ciclos de Layer 1 e altseason.
        """
        altseason = current_data.get('altseason_intensity', 0)
        ema_alignment = current_data.get('ema_alignment_score', 0)

        if altseason > 0.55 and ema_alignment >= 3:
            return "L1_UPTREND"
        elif ema_alignment <= -3:
            return "DOWNTREND"
        else:
            return "CONSOLIDATION"

    def should_trade(self, market_regime: str, d1_bias: str,
                    btc_bias: str = None) -> bool:
        """
        CELO é viável principalmente em uptrends e altseason.
        """
        if d1_bias == "BEARISH":
            return False
        if market_regime in ["STRONG_UPTREND", "ALTSEASON"]:
            return True
        if market_regime == "CONSOLIDATION" and d1_bias == "BULLISH":
            return True
        return False

    def get_confluence_requirements(self) -> Dict[str, Any]:
        """Requisitos de confluência para CELO."""
        return {
            "min_confluence_score": 8,
            "preferred_confluence_score": 10,
        }
