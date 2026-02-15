"""
Playbook especifico para Kaia (KAIAUSDT).
Layer 1 focused on messaging/social integration (ex-Klaytn+LINE).
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class KAIAPlaybook(BasePlaybook):
    """
    Playbook para KAIAUSDT - Kaia messaging/social Layer 1.
    """
    
    def __init__(self):
        super().__init__("KAIAUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de confluencia para KAIAUSDT."""
        adjustments = {}
        
        # Bonus para adocao Asia (usar social_sentiment como proxy)
        if 'social_sentiment' in context and context['social_sentiment'] > 0.65:
            adjustments['asia_adoption'] = +1.0
            logger.debug("KAIAUSDT: +1.0 confluence for Asia adoption/social activity")
        
        # Bonus em narrativa messaging/social
        if 'fear_greed_value' in context and context['fear_greed_value'] > 60:
            adjustments['social_narrative'] = +0.5
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de risco para KAIAUSDT."""
        adjustments = {
            'position_size_multiplier': 0.5,  # Reduzido - beta 2.8
            'stop_multiplier': 1.5  # Stops largos
        }
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """KAIAUSDT cycle phases."""
        social_sentiment = current_data.get('social_sentiment', 0.5)
        fear_greed = current_data.get('fear_greed_value', 50)
        
        if social_sentiment > 0.75 or fear_greed > 70:
            return "ADOPTION_WAVE"
        elif social_sentiment > 0.6:
            return "PARTNERSHIP_HYPE"
        elif social_sentiment < 0.35:
            return "DORMANT"
        else:
            return "CONSOLIDATION"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """KAIAUSDT trading conditions - only in RISK_ON."""
        if d1_bias == "NEUTRO":
            return False
        
        # Apenas operar em risk-on (beta 2.8)
        if market_regime != "RISK_ON":
            logger.debug("KAIAUSDT: Skipping (not RISK_ON)")
            return False
        
        return True
