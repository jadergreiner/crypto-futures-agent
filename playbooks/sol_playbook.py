"""
Playbook específico para Solana (SOLUSDT).
High beta, lidera em risk-on.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class SOLPlaybook(BasePlaybook):
    """
    Playbook para SOL - High beta, amplifica movimentos.
    """
    
    def __init__(self):
        super().__init__("SOLUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de confluência para SOL."""
        adjustments = {}
        
        # Bonus forte em regime risk-on
        if 'market_regime' in context and context['market_regime'] == "RISK_ON":
            adjustments['risk_on'] = +1.0
            logger.debug("SOL: +1 confluence for RISK_ON regime")
        
        # Bonus para crescimento de TVL
        if 'tvl_change_pct' in context and context['tvl_change_pct'] > 10:
            adjustments['tvl_growth'] = +0.5
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de risco para SOL."""
        adjustments = {
            'position_size_multiplier': 0.7,  # Reduzir por beta 2.0
            'stop_multiplier': 1.2  # Stop mais largo para volatilidade
        }
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """SOL amplifica fases do BTC."""
        btc_phase = current_data.get('btc_cycle_phase', 'ACCUMULATION')
        
        # SOL exagera as fases
        if btc_phase == "BULL_RUN":
            return "PARABOLIC"
        elif btc_phase == "BEAR_MARKET":
            return "DEEP_CORRECTION"
        else:
            return btc_phase
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """SOL apenas em risk-on."""
        if d1_bias == "NEUTRO":
            return False
        
        # Apenas operar em risk-on
        if market_regime != "RISK_ON":
            logger.debug("SOL: Skipping (not RISK_ON)")
            return False
        
        return True
