"""
Playbook especifico para 0G (0GUSDT).
AI/Data infrastructure token with very high beta.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class ZeroGPlaybook(BasePlaybook):
    """
    Playbook para 0GUSDT - Zero Gravity AI/Data infrastructure.
    """
    
    def __init__(self):
        super().__init__("0GUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de confluencia para 0GUSDT."""
        adjustments = {}
        
        # Bonus forte em narrativa AI (fear_greed > 70 = hype)
        if 'fear_greed_value' in context and context['fear_greed_value'] > 70:
            adjustments['ai_hype'] = +1.5
            logger.debug("0GUSDT: +1.5 confluence for AI hype (fear_greed > 70)")
        
        # Penalidade em risk-off
        if 'fear_greed_value' in context and context['fear_greed_value'] < 35:
            adjustments['risk_off'] = -1.5
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de risco para 0GUSDT."""
        adjustments = {
            'position_size_multiplier': 0.4,  # Muito pequeno - beta 3.5 + baixa liquidez
            'stop_multiplier': 2.0  # Stops muito largos
        }
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """0GUSDT cycle phases."""
        fear_greed = current_data.get('fear_greed_value', 50)
        social_sentiment = current_data.get('social_sentiment', 0.5)
        
        if fear_greed > 75 or social_sentiment > 0.75:
            return "AI_HYPE"
        elif fear_greed > 55:
            return "BUILDING"
        elif fear_greed < 35:
            return "FORGOTTEN"
        else:
            return "CONSOLIDATION"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """0GUSDT trading conditions - only in RISK_ON."""
        if d1_bias == "NEUTRO":
            return False
        
        # Apenas operar em risk-on (beta 3.5 + baixa liquidez)
        if market_regime != "RISK_ON":
            logger.debug("0GUSDT: Skipping (not RISK_ON)")
            return False
        
        return True
