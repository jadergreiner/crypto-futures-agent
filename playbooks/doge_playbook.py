"""
Playbook específico para Dogecoin (DOGEUSDT).
Memecoin líder, sentiment-driven.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class DOGEPlaybook(BasePlaybook):
    """
    Playbook para DOGE - Memecoin com alta influência social.
    """
    
    def __init__(self):
        super().__init__("DOGEUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de confluência para DOGE."""
        adjustments = {}
        
        # Bonus forte em social sentiment positivo
        if 'social_sentiment' in context and context['social_sentiment'] > 0.7:
            adjustments['social'] = +1.5
            logger.debug("DOGE: +1.5 confluence for high social sentiment")
        
        # Bonus em Fear & Greed extremo (hype)
        if 'fear_greed_value' in context and context['fear_greed_value'] > 75:
            adjustments['hype'] = +1.0
        
        # Penalidade sem hype
        if 'fear_greed_value' in context and context['fear_greed_value'] < 40:
            adjustments['no_hype'] = -1.0
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de risco para DOGE."""
        adjustments = {
            'position_size_multiplier': 0.6,  # Muito reduzido por beta 2.5
            'stop_multiplier': 1.5  # Stop bem largo
        }
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """DOGE tem ciclos de hype."""
        social_sentiment = current_data.get('social_sentiment', 0.5)
        
        if social_sentiment > 0.8:
            return "HYPE_PEAK"
        elif social_sentiment > 0.6:
            return "HYPE_BUILDING"
        elif social_sentiment < 0.3:
            return "FORGOTTEN"
        else:
            return "NEUTRAL"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """DOGE apenas em risk-on extremo."""
        if d1_bias == "NEUTRO":
            return False
        
        # Apenas operar em risk-on
        if market_regime != "RISK_ON":
            logger.debug("DOGE: Skipping (not RISK_ON)")
            return False
        
        return True
