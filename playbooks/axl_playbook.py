"""
Playbook especifico para Axelar (AXLUSDT).
Cross-chain interoperability protocol.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class AXLPlaybook(BasePlaybook):
    """
    Playbook para AXLUSDT - Axelar cross-chain protocol.
    """
    
    def __init__(self):
        super().__init__("AXLUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de confluencia para AXLUSDT."""
        adjustments = {}
        
        # Bonus para narrativa cross-chain/interop
        if 'fear_greed_value' in context and context['fear_greed_value'] > 65:
            adjustments['interop_narrative'] = +1.0
            logger.debug("AXLUSDT: +1.0 confluence for cross-chain narrative")
        
        # Bonus em contexto DeFi TVL growth (usar social_sentiment como proxy)
        if 'social_sentiment' in context and context['social_sentiment'] > 0.65:
            adjustments['defi_growth'] = +0.5
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de risco para AXLUSDT."""
        adjustments = {
            'position_size_multiplier': 0.5,  # Reduzido - beta 2.5
            'stop_multiplier': 1.5  # Stops largos
        }
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """AXLUSDT cycle phases."""
        fear_greed = current_data.get('fear_greed_value', 50)
        social_sentiment = current_data.get('social_sentiment', 0.5)
        
        if fear_greed > 70 or social_sentiment > 0.7:
            return "INTEROP_EXPANSION"
        elif fear_greed > 55:
            return "INTEGRATION_GROWTH"
        elif fear_greed < 40:
            return "LOW_ACTIVITY"
        else:
            return "CONSOLIDATION"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """AXLUSDT trading conditions - only in RISK_ON."""
        if d1_bias == "NEUTRO":
            return False
        
        # Apenas operar em risk-on (beta 2.5)
        if market_regime != "RISK_ON":
            logger.debug("AXLUSDT: Skipping (not RISK_ON)")
            return False
        
        return True
