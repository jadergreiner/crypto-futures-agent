"""
Playbook especifico para Fogo (FOGOUSDT).
High performance Layer 1 (SUI fork) with focus on speed.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class FOGOPlaybook(BasePlaybook):
    """
    Playbook para FOGOUSDT - Fogo high performance Layer 1.
    """
    
    def __init__(self):
        super().__init__("FOGOUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de confluencia para FOGOUSDT."""
        adjustments = {}
        
        # Bonus em narrativa L1 performance
        if 'fear_greed_value' in context and context['fear_greed_value'] > 68:
            adjustments['l1_performance'] = +1.2
            logger.debug("FOGOUSDT: +1.2 confluence for L1 performance narrative")
        
        # Bonus em correlacao com SUI ecosystem (usar social como proxy)
        if 'social_sentiment' in context and context['social_sentiment'] > 0.7:
            adjustments['sui_correlation'] = +0.8
        
        # Penalidade em risk-off
        if 'fear_greed_value' in context and context['fear_greed_value'] < 38:
            adjustments['risk_off'] = -1.5
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de risco para FOGOUSDT."""
        adjustments = {
            'position_size_multiplier': 0.4,  # Muito pequeno - beta 3.8 + baixa liquidez
            'stop_multiplier': 2.0  # Stops muito largos
        }
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """FOGOUSDT cycle phases."""
        fear_greed = current_data.get('fear_greed_value', 50)
        social_sentiment = current_data.get('social_sentiment', 0.5)
        
        if fear_greed > 72 or social_sentiment > 0.75:
            return "PERFORMANCE_HYPE"
        elif fear_greed > 55:
            return "ECOSYSTEM_GROWTH"
        elif fear_greed < 35:
            return "LOW_INTEREST"
        else:
            return "CONSOLIDATION"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """FOGOUSDT trading conditions - only in RISK_ON."""
        if d1_bias == "NEUTRO":
            return False
        
        # Apenas operar em risk-on (beta 3.8 muito alto)
        if market_regime != "RISK_ON":
            logger.debug("FOGOUSDT: Skipping (not RISK_ON)")
            return False
        
        return True
