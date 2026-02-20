"""
Playbook específico para POLYX (POLYXUSDT).
Token de infraestrutura para tokens de segurança.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class POLYXPlaybook(BasePlaybook):
    """
    Playbook para POLYX - Infraestrutura de securities tokens.
    """

    def __init__(self):
        super().__init__("POLYXUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para POLYX.

        POLYX beneficia de:
        - Narrativa de regulatory compliance e securities
        - Ciclos de altseason
        - Notícias positivas de regulação
        """
        adjustments = {}

        # Bonus para altseason
        if 'altseason_intensity' in context and context['altseason_intensity'] > 0.55:
            adjustments['altseason'] = +0.8
            logger.debug("POLYX: +0.8 confluence for altseason")

        # Bonus para estrutura técnica
        if 'structure_clarity' in context and context['structure_clarity'] > 0.65:
            adjustments['structure'] = +0.4

        # Bonus para volume crescente
        if 'volume_trend' in context and context['volume_trend'] == "INCREASING":
            adjustments['volume_trend'] = +0.3

        # Penalty especial em períodos de regulatory FUD
        if 'regulatory_fud' in context and context['regulatory_fud']:
            adjustments['regulatory_penalty'] = -1.0

        return adjustments

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para POLYX.

        POLYX tem beta moderado-alto (2.8). Adicional sensibilidade regulatória.
        """
        adjustments = {
            'position_size_multiplier': 0.78,  # 78% do tamanho padrão
            'stop_multiplier': 0.93  # Stop moderadamente apertado
        }

        # Em consolidação, reduzir
        if context.get('market_regime') == "CONSOLIDATION":
            adjustments['position_size_multiplier'] = 0.63

        # Em downtrend, reduzir muito
        if context.get('market_regime') == "DOWNTREND":
            adjustments['position_size_multiplier'] = 0.45

        # Em altura de FUD regulatório, fechar posições
        if context.get('regulatory_fud'):
            adjustments['position_size_multiplier'] = 0.20

        return adjustments

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo para POLYX.

        POLYX é sensível a regulação e ciclos de compliance.
        """
        regulatory_fud = current_data.get('regulatory_fud', False)
        altseason = current_data.get('altseason_intensity', 0)
        ema_alignment = current_data.get('ema_alignment_score', 0)

        if regulatory_fud:
            return "REGULATORY_FUD_PHASE"
        elif altseason > 0.55 and ema_alignment >= 3:
            return "COMPLIANCE_UPTREND"
        else:
            return "CONSOLIDATION"

    def should_trade(self, market_regime: str, d1_bias: str,
                    btc_bias: str = None) -> bool:
        """
        POLYX é viável em uptrends e altseason.
        Evitar em períodos de regulatory FUD.
        """
        if d1_bias == "BEARISH":
            return False
        if market_regime in ["STRONG_UPTREND", "ALTSEASON"]:
            return True
        if market_regime == "CONSOLIDATION" and d1_bias == "BULLISH":
            return True
        return False

    def get_confluence_requirements(self) -> Dict[str, Any]:
        """Requisitos de confluência para POLYX."""
        return {
            "min_confluence_score": 8,
            "preferred_confluence_score": 10,
        }
