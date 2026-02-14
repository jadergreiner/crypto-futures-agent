"""
Playbook específico para Ethereum (ETHUSDT).
Segunda maior, ecossistema DeFi/NFT.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class ETHPlaybook(BasePlaybook):
    """
    Playbook para ETH - Segunda maior, segue BTC com lag.
    """
    
    def __init__(self):
        super().__init__("ETHUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de confluência para ETH."""
        adjustments = {}
        
        # Bonus se BTC está bullish (correlação forte)
        if 'btc_bias' in context and context['btc_bias'] == "BULLISH":
            adjustments['btc_alignment'] = +0.5
        
        # Bonus para network upgrades (se disponível)
        if 'network_upgrade_proximity' in context and context['network_upgrade_proximity']:
            adjustments['network_upgrade'] = +1.0
        
        # Bonus para alto staking yield
        if 'staking_yield' in context and context['staking_yield'] > 4.0:
            adjustments['staking'] = +0.5
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajustes de risco para ETH."""
        adjustments = {
            'position_size_multiplier': 1.0,
            'stop_multiplier': 1.0
        }
        
        # ETH tem beta ~1.2, ajustar tamanho
        adjustments['position_size_multiplier'] = 0.9
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        ETH segue ciclo do BTC com lag de 2-6 semanas.
        """
        btc_phase = current_data.get('btc_cycle_phase', 'ACCUMULATION')
        
        # ETH tende a seguir BTC
        return btc_phase
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """ETH deve ter alinhamento com BTC."""
        if d1_bias == "NEUTRO":
            return False
        
        # Preferir quando BTC também está alinhado
        if btc_bias and btc_bias != d1_bias:
            logger.debug("ETH: Skipping due to BTC misalignment")
            return False
        
        return True
