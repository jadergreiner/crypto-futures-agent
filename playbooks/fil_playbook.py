"""
Playbook especializado para FIL (Filecoin).

Característica: Infraestrutura de armazenamento descentralizado
- Beta: 2.5 (mid-cap, comportamento moderado)
- Classificação: Storage infrastructure
- Sensibilidade: Narrativa de armazenamento Web3, ciclos de adoção
"""

import logging
from typing import Dict, Any, Optional
from playbooks.base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class FILPlaybook(BasePlaybook):
    """
    Playbook para Filecoin (FIL).
    Storage infrastructure com beta moderado (2.5).
    """
    
    def __init__(self):
        super().__init__("FILUSDT")
    
    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para FIL.
        
        Filecoin é sensível a:
        - Narrativa de armazenamento descentralizado
        - Crescimento de TVL em protocolos Web3
        - Ciclos de adoção de infraestrutura
        """
        adjustments = {
            "defi_tvl_growth": 0.5,      # Beneficia de crescimento DeFi
            "storage_narrative": 1.0,    # Sensível a narrativa de armazenamento
            "web3_adoption": 0.5,        # Segue adoção Web3
            "macro_risk_off": -1.0,      # Sofre em risk-off
        }
        
        return adjustments
    
    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para FIL.
        
        Beta 2.5 (mid-cap):
        - 70% de tamanho de posição em relação ao baseline
        - SL mais amplo que moedas de alta cap, TP mais próximo
        """
        adjustments = {
            "position_size_multiplier": 0.70,    # 70% do tamanho padrão
            "sl_atr_multiplier": 1.5,             # SL padrão (ATR 1.5x)
            "tp_atr_multiplier": 3.0,             # TP padrão (ATR 3.0x)
            "max_drawdown_percent": 3.0,          # Max drawdown 3%
        }
        
        return adjustments
    
    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de FIL.
        
        Filecoin passa por:
        - Accumulation: Preparação para crescimento
        - Growth: Expansão de adoção
        - Maturity: Consolidação
        - Decline: Redução de interesse
        """
        price_action = current_data.get("price_action", "neutral")
        volume = current_data.get("volume_profile", "normal")
        
        if price_action == "uptrend" and volume == "high":
            return "growth"
        elif price_action == "downtrend":
            return "decline"
        elif volume == "accumulation":
            return "accumulation"
        else:
            return "consolidation"
    
    def should_trade(self, market_regime: str, d1_bias: str, 
                    btc_bias: Optional[str] = None) -> bool:
        """
        Filecoin (mid-cap, beta 2.5) deve operar em:
        - Risk-on com D1 long
        - Neutro em risk-on forte
        - Avoid em risk-off
        """
        if d1_bias == "NEUTRO":
            return False
        
        if market_regime == "RISK_ON":
            return d1_bias in ["LONG", "STRONG_LONG"]
        elif market_regime == "RISK_OFF":
            return False
        else:  # NEUTRO_MERCADO
            return d1_bias == "STRONG_LONG"
        
        return False
