"""
Playbook específico para BNB (BNBUSDT).
Token utilitário da Binance com burns trimestrais.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class BNBPlaybook(BasePlaybook):
    """
    Playbook para BNB - Token burns e ecossistema Binance.
    """
    
    def __init__(self):
        super().__init__("BNBUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de confluência para BNB."""
        adjustments = {}
        
        # Bonus pré-burn trimestral
        if 'days_to_burn' in context and 0 < context['days_to_burn'] <= 30:
            adjustments['burn_proximity'] = +1.0
            logger.debug("BNB: +1 confluence for upcoming burn")
        
        # Bonus para alto volume no ecossistema Binance
        if 'binance_volume_rank' in context and context['binance_volume_rank'] == 1:
            adjustments['ecosystem'] = +0.5
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de risco para BNB."""
        adjustments = {
            'position_size_multiplier': 1.0,
            'stop_multiplier': 1.0
        }
        
        # BNB tem beta moderado (1.1)
        adjustments['position_size_multiplier'] = 0.95
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """BNB tem ciclos de burn trimestral."""
        days_to_burn = current_data.get('days_to_burn', 45)
        
        if days_to_burn <= 30:
            return "PRE_BURN"
        elif days_to_burn <= 60:
            return "POST_BURN"
        else:
            return "MID_QUARTER"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """BNB pode operar em qualquer regime."""
        if d1_bias == "NEUTRO":
            return False
        return True
