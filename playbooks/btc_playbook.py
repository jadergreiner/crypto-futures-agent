"""
Playbook específico para Bitcoin (BTCUSDT).
Líder de mercado, define ciclos macro.
"""

import logging
from typing import Dict, Any
from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class BTCPlaybook(BasePlaybook):
    """
    Playbook para BTC - Líder de mercado com ciclos de halving.
    """
    
    def __init__(self):
        super().__init__("BTCUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para BTC.
        
        BTC é líder, então peso maior em:
        - Estrutura própria
        - Dados macro (DXY, FGI)
        - Volume institucional
        """
        adjustments = {}
        
        # Bonus em períodos pós-halving (+1 ano)
        cycle_phase = self.get_cycle_phase(context)
        if cycle_phase == "BULL_RUN":
            adjustments['halving_cycle'] = +1.0
            logger.debug("BTC: +1 confluence for Bull Run phase")
        
        # Bonus para ETF flows positivos (se disponível)
        if 'etf_flow' in context and context['etf_flow'] > 0:
            adjustments['etf_flow'] = +0.5
        
        # DXY inverso: DXY caindo = BTC subindo
        if 'dxy_change_pct' in context:
            if context['dxy_change_pct'] < -0.5:  # DXY caindo
                adjustments['dxy_inverse'] = +0.5
                logger.debug("BTC: +0.5 confluence for falling DXY")
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para BTC.
        
        BTC tem risco padrão (beta 1.0).
        """
        adjustments = {
            'position_size_multiplier': 1.0,  # Tamanho padrão
            'stop_multiplier': 1.0  # Stop padrão
        }
        
        # Em high volatility, reduzir tamanho
        if 'atr_pct' in context and context['atr_pct'] > 5:
            adjustments['position_size_multiplier'] = 0.8
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de 4 anos do BTC.
        
        Fases:
        - ACCUMULATION: 6-12 meses pós-halving
        - BULL_RUN: 12-24 meses pós-halving
        - DISTRIBUTION: 24-30 meses pós-halving
        - BEAR_MARKET: 30-48 meses pós-halving
        
        Args:
            current_data: Dados atuais (deveria incluir 'months_since_halving')
            
        Returns:
            Fase do ciclo
        """
        # Simplificado: usar tendência D1 como proxy
        d1_bias = current_data.get('d1_bias', 'NEUTRO')
        ema_alignment = current_data.get('ema_alignment_score', 0)
        
        if ema_alignment >= 5 and d1_bias == "BULLISH":
            return "BULL_RUN"
        elif ema_alignment <= -5 and d1_bias == "BEARISH":
            return "BEAR_MARKET"
        elif ema_alignment >= 2:
            return "ACCUMULATION"
        else:
            return "DISTRIBUTION"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: str = None) -> bool:
        """BTC pode operar em qualquer regime (é o líder)."""
        # Apenas evitar bias neutro
        if d1_bias == "NEUTRO":
            return False
        return True
