"""
Playbook especializado para LINK (Chainlink).

Característica: Oracle descentralizado líder em infraestrutura DeFi
- Beta: 2.3 (mid-cap, comportamento moderado-alto)
- Classificação: Oracle infrastructure
- Sensibilidade: DeFi TVL, adoção de smart contracts, inovação em oracles
"""

import logging
from typing import Dict, Any, Optional
from playbooks.base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class LINKPlaybook(BasePlaybook):
    """
    Playbook para Chainlink (LINK).
    Oracle infrastructure token com beta 2.3 (moderado-alto).
    """

    def __init__(self):
        super().__init__("LINKUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para LINK.

        Chainlink é sensível a:
        - Crescimento de DeFi TVL e smart contracts
        - Adoção institucional de oracles
        - Inovação em cross-chain solutions
        """
        adjustments = {
            "defi_tvl_growth": 1.0,       # Altamente sensível a DeFi TVL
            "oracle_adoption": 1.0,       # Core: adoção de oracles
            "smart_contract_activity": 0.8, # Sensível a atividade de contratos
            "macro_risk_off": -1.0,       # Afetado em risk-off
        }

        return adjustments

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para LINK.

        Beta 2.3 (mid-cap, moderado-alto):
        - 68% de tamanho de posição em relação ao baseline
        - SL padrão, TP padrão
        """
        adjustments = {
            "position_size_multiplier": 0.68,    # 68% do tamanho padrão
            "sl_atr_multiplier": 1.5,             # SL padrão (ATR 1.5x)
            "tp_atr_multiplier": 3.0,             # TP padrão (ATR 3.0x)
            "max_drawdown_percent": 3.0,          # Max drawdown 3.0%
        }

        return adjustments

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de LINK.

        Chainlink passa por:
        - Accumulation: Preparação para crescimento
        - Growth: Fase de expansão DeFi
        - Maturity: Consolidação
        - Decline: Redução de atividade
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
        LINK (mid-cap, beta 2.3) deve operar em:
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
