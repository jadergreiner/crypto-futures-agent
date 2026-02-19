"""
Playbook específico para ZK (ZKUSDT).
Token de infraestrutura zero-knowledge commitment.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class ZKPlaybook(BasePlaybook):
    """
    Playbook para ZK - Infraestrutura de privacidade/escalabilidade.
    """
    
    def __init__(self):
        super().__init__("ZKUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para ZK.
        
        ZK beneficia de:
        - Narrativa de infraestrutura de privacidade
        - Ciclos de altseason
        - Desenvolvimento de protocolo
        """
        adjustments = {}
        
        # Bonus em altseason forte (BTC corrigindo, altcoins subindo)
        if 'altseason_intensity' in context and context['altseason_intensity'] > 0.6:
            adjustments['altseason'] = +1.0
            logger.debug("ZK: +1.0 confluence for strong altseason")
        
        # Bonus para ema alignment positivo intraday
        if 'ema_alignment_score' in context and context['ema_alignment_score'] >= 3:
            adjustments['ema_alignment'] = +0.5
        
        # Penalty em períodos de risk-off muito forte
        if 'market_fear_index' in context and context['market_fear_index'] > 75:
            adjustments['fear_penalty'] = -0.8
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para ZK.
        
        ZK tem beta elevado (3.2) - posições reduzidas.
        """
        adjustments = {
            'position_size_multiplier': 0.70,  # 70% do tamanho padrão
            'stop_multiplier': 0.90  # Stop mais apertado
        }
        
        # Em consolidação, manter reduzido
        if context.get('market_regime') == "CONSOLIDATION":
            adjustments['position_size_multiplier'] = 0.55
        
        # Em downtrend, muito reduzido
        if context.get('market_regime') == "DOWNTREND":
            adjustments['position_size_multiplier'] = 0.40
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo para ZK.
        
        ZK segue narrativa de infraestrutura, sensível a ciclos de altseason.
        """
        ema_alignment = current_data.get('ema_alignment_score', 0)
        altseason = current_data.get('altseason_intensity', 0)
        
        if altseason > 0.6 and ema_alignment >= 3:
            return "ALTSEASON_UPTREND"
        elif ema_alignment <= -3:
            return "DOWNTREND"
        elif ema_alignment >= 2:
            return "UPTREND"
        else:
            return "CONSOLIDATION"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """
        ZK é melhor em uptrends e altseason.
        Evitar em downtrends e períodos de aversão ao risco.
        """
        if d1_bias == "BEARISH":
            return False
        if market_regime in ["STRONG_UPTREND", "ALTSEASON"]:
            return True
        if market_regime == "CONSOLIDATION" and d1_bias == "BULLISH":
            return True
        return False
    
    def get_confluence_requirements(self) -> Dict[str, Any]:
        """Requisitos de confluência para ZK."""
        return {
            "min_confluence_score": 9,  # Maior pela volatilidade
            "preferred_confluence_score": 11,  # Prefere alta confluência
        }
