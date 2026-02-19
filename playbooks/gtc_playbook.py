"""
Playbook específico para GTC (GTCUSDT).
Token de infraestrutura/governança focado em funding público.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class GTCPlaybook(BasePlaybook):
    """
    Playbook para GTC - Web3 infrastructure e governança.
    """
    
    def __init__(self):
        super().__init__("GTCUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para GTC.
        
        GTC beneficia de:
        - Narrativa web3/governance
        - Ciclos de funding e eventos no protocolo
        - Altseason
        """
        adjustments = {}
        
        # Bonus para altseason
        if 'altseason_intensity' in context and context['altseason_intensity'] > 0.55:
            adjustments['altseason'] = +0.8
            logger.debug("GTC: +0.8 confluence for altseason")
        
        # Bonus para suporte técnico testado
        if 'support_proximity' in context and context['support_proximity'] < 0.025:
            adjustments['support'] = +0.4
        
        # Bonus para volume crescente
        if 'volume_trend' in context and context['volume_trend'] == "INCREASING":
            adjustments['volume_trend'] = +0.3
        
        # Penalty em divergência
        if 'divergence' in context and context['divergence']:
            adjustments['divergence_penalty'] = -0.5
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para GTC.
        
        GTC tem beta moderado-alto (2.8).
        """
        adjustments = {
            'position_size_multiplier': 0.78,  # 78% do tamanho padrão
            'stop_multiplier': 0.93  # Stop moderadamente apertado
        }
        
        # Em consolidação, reduzir ligeiramente
        if context.get('market_regime') == "CONSOLIDATION":
            adjustments['position_size_multiplier'] = 0.63
        
        # Em downtrend, reduzir muito
        if context.get('market_regime') == "DOWNTREND":
            adjustments['position_size_multiplier'] = 0.45
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo para GTC.
        
        GTC segue ciclos de governança e altseason.
        """
        altseason = current_data.get('altseason_intensity', 0)
        ema_alignment = current_data.get('ema_alignment_score', 0)
        
        if altseason > 0.55 and ema_alignment >= 3:
            return "ALTSEASON_UPTREND"
        elif ema_alignment <= -3:
            return "DOWNTREND"
        else:
            return "CONSOLIDATION"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """
        GTC é viável em uptrends e altseason.
        """
        if d1_bias == "BEARISH":
            return False
        if market_regime in ["STRONG_UPTREND", "ALTSEASON"]:
            return True
        if market_regime == "CONSOLIDATION" and d1_bias == "BULLISH":
            return True
        return False
    
    def get_confluence_requirements(self) -> Dict[str, Any]:
        """Requisitos de confluência para GTC."""
        return {
            "min_confluence_score": 8,
            "preferred_confluence_score": 10,
        }
