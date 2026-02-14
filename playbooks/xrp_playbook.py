"""
Playbook específico para Ripple (XRPUSDT).
Foco institucional, sensível a regulação.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class XRPPlaybook(BasePlaybook):
    """
    Playbook para XRP - Sensível a regulação e adoção institucional.
    """
    
    def __init__(self):
        super().__init__("XRPUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de confluência para XRP."""
        adjustments = {}
        
        # Bonus para notícias regulatórias positivas
        if 'regulatory_news' in context and context['regulatory_news'] == "POSITIVE":
            adjustments['regulation'] = +2.0
            logger.debug("XRP: +2 confluence for positive regulatory news")
        
        # Penalidade para notícias negativas
        if 'regulatory_news' in context and context['regulatory_news'] == "NEGATIVE":
            adjustments['regulation'] = -2.0
        
        # Bonus para adoção em pagamentos
        if 'payment_adoption' in context and context['payment_adoption']:
            adjustments['adoption'] = +0.5
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de risco para XRP."""
        adjustments = {
            'position_size_multiplier': 0.85,  # Reduzir por beta 1.3
            'stop_multiplier': 1.1
        }
        
        # Risco maior em incerteza regulatória
        if 'regulatory_uncertainty' in context and context['regulatory_uncertainty']:
            adjustments['position_size_multiplier'] = 0.6
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """XRP tem ciclos regulatórios."""
        regulatory_status = current_data.get('regulatory_status', 'NEUTRAL')
        
        if regulatory_status == "POSITIVE":
            return "CLARITY"
        elif regulatory_status == "NEGATIVE":
            return "UNCERTAINTY"
        else:
            return "NEUTRAL"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """XRP pode operar em qualquer regime se tendência clara."""
        if d1_bias == "NEUTRO":
            return False
        
        # Evitar em alta incerteza regulatória (implementar em contexto)
        return True
