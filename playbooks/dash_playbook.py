"""
Playbook específico para DASH (DASHUSDT).
Token legacy com liquidez moderada e dinâmica própria.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class DASHPlaybook(BasePlaybook):
    """
    Playbook para DASH - Payment token com liquidez estável.
    """
    
    def __init__(self):
        super().__init__("DASHUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para DASH.
        
        DASH é um token de pagamento mais estável, beneficia de:
        - Suporte de nível técnico
        - Volume moderado
        - Tendência macro positiva
        """
        adjustments = {}
        
        # Bonus para suportes técnicos bem definidos
        if 'support_proximity' in context and context['support_proximity'] < 0.02:
            adjustments['support_proximity'] = +0.5
            logger.debug("DASH: +0.5 confluence for proximity to support")
        
        # Bonus para volume acima da média
        if 'volume_sma_ratio' in context and context['volume_sma_ratio'] > 1.2:
            adjustments['volume_strength'] = +0.3
        
        # Penalty em divergências
        if 'divergence' in context and context['divergence']:
            adjustments['divergence_penalty'] = -0.5
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para DASH.
        
        DASH tem beta moderado (2.0) - posições ligeiramente menores que BTC.
        """
        adjustments = {
            'position_size_multiplier': 0.85,  # 85% do tamanho padrão
            'stop_multiplier': 0.95  # Stop ligeiramente mais apertado
        }
        
        # Em alta volatilidade, reduzir mais
        if 'atr_pct' in context and context['atr_pct'] > 4:
            adjustments['position_size_multiplier'] = 0.65
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo para DASH.
        
        DASH segue o ciclo geral do mercado com menor amplitude.
        """
        d1_bias = current_data.get('d1_bias', 'NEUTRO')
        ema_alignment = current_data.get('ema_alignment_score', 0)
        
        if ema_alignment >= 4 and d1_bias == "BULLISH":
            return "UPTREND"
        elif ema_alignment <= -4 and d1_bias == "BEARISH":
            return "DOWNTREND"
        else:
            return "CONSOLIDATION"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """
        DASH é operável em uptrends e em consolidações com bom setup.
        Evitar em downtrends fortes.
        """
        if d1_bias == "BEARISH":
            return False
        if market_regime == "STRONG_UPTREND":
            return True
        if market_regime in ["CONSOLIDATION", "MILD_UPTREND"] and d1_bias == "BULLISH":
            return True
        return False
    
    def get_confluence_requirements(self) -> Dict[str, Any]:
        """Requisitos de confluência para DASH."""
        return {
            "min_confluence_score": 8,  # Mesmo que base
            "preferred_confluence_score": 10,  # Ligeiramente maior pela estabilidade
        }
