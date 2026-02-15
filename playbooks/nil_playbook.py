"""
Playbook especifico para Nillion (NILUSDT).
Decentralized privacy compute network with ultra-high beta.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class NILPlaybook(BasePlaybook):
    """
    Playbook para NILUSDT - Nillion privacy compute network.
    """
    
    def __init__(self):
        super().__init__("NILUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de confluencia para NILUSDT."""
        adjustments = {}
        
        # Bonus forte em narrativa privacy/AI compute
        if 'fear_greed_value' in context and context['fear_greed_value'] > 70:
            adjustments['privacy_ai_hype'] = +1.5
            logger.debug("NILUSDT: +1.5 confluence for privacy/AI compute hype")
        
        # Penalidade forte em risk-off/fear
        if 'fear_greed_value' in context and context['fear_greed_value'] < 40:
            adjustments['extreme_risk_off'] = -2.0
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de risco para NILUSDT."""
        adjustments = {
            'position_size_multiplier': 0.35,  # Muito pequeno - beta 4.0 + liquidez extremamente baixa
            'stop_multiplier': 2.5  # Stops mais largos do projeto
        }
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """NILUSDT cycle phases."""
        fear_greed = current_data.get('fear_greed_value', 50)
        
        if fear_greed > 75:
            return "PRIVACY_HYPE"
        elif fear_greed > 50:
            return "BUILDING"
        elif fear_greed < 30:
            return "EXTREME_FEAR"
        else:
            return "DORMANT"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """NILUSDT trading conditions - ultra conservative, only in RISK_ON."""
        if d1_bias == "NEUTRO":
            return False
        
        # Apenas operar em risk-on (beta 4.0 muito alto)
        if market_regime != "RISK_ON":
            logger.debug("NILUSDT: Skipping (not RISK_ON)")
            return False
        
        return True
