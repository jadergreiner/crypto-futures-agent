"""
Playbook específico para Litecoin (LTCUSDT).
Silver to Bitcoin's gold, halving próprio.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class LTCPlaybook(BasePlaybook):
    """
    Playbook para LTC - Correlação forte com BTC, halving próprio.
    """
    
    def __init__(self):
        super().__init__("LTCUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de confluência para LTC."""
        adjustments = {}
        
        # Bonus pré-halving (LTC tem halving próprio)
        if 'months_to_ltc_halving' in context and 0 < context['months_to_ltc_halving'] <= 6:
            adjustments['halving'] = +1.0
            logger.debug("LTC: +1 confluence for upcoming halving")
        
        # Bonus para forte correlação com BTC
        if 'btc_correlation' in context and context['btc_correlation'] > 0.85:
            if 'btc_bias' in context and context['btc_bias'] != "NEUTRO":
                adjustments['btc_alignment'] = +0.5
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de risco para LTC."""
        adjustments = {
            'position_size_multiplier': 1.0,  # Beta moderado 1.1
            'stop_multiplier': 1.0
        }
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """LTC segue ciclo de BTC + halving próprio."""
        months_to_halving = current_data.get('months_to_ltc_halving', 24)
        
        if months_to_halving <= 6:
            return "PRE_HALVING"
        elif months_to_halving <= 12:
            return "POST_HALVING"
        else:
            return "MID_CYCLE"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """LTC pode operar em qualquer regime, preferir alinhamento com BTC."""
        if d1_bias == "NEUTRO":
            return False
        
        # Preferir quando BTC está alinhado
        if btc_bias and btc_bias == d1_bias:
            return True
        
        # Mas pode operar mesmo sem BTC se tendência forte
        return True
