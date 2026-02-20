"""
Playbook especializado para GRT (The Graph).

Característica: Protocolo de indexação descentralizada
- Beta: 2.8 (mid-cap, comportamento ativo)
- Classificação: DeFi infrastructure
- Sensibilidade: Crescimento de protocolos indexados, ciclos de adoção DeFi
"""

import logging
from typing import Dict, Any, Optional
from playbooks.base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class GRTPlaybook(BasePlaybook):
    """
    Playbook para The Graph (GRT).
    DeFi infrastructure com beta 2.8 (mid-cap ativo).
    """

    def __init__(self):
        super().__init__("GRTUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para GRT.

        The Graph é sensível a:
        - TVL em protocolos DeFi indexados
        - Crescimento de dApps usando The Graph
        - Ciclos de altseason
        """
        adjustments = {
            "defi_tvl_growth": 1.0,      # Forte sensibilidade a DeFi TVL
            "dapp_adoption": 0.75,       # Cresce com adoção de dApps
            "altseason_signal": 1.0,     # Sensível a ciclos de altseason
            "macro_risk_off": -1.5,      # Sofre mais em risk-off que FIL
        }

        return adjustments

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para GRT.

        Beta 2.8 (mid-cap, mais ativo que FIL):
        - 65% de tamanho de posição
        - SL similar, TP similar (beta moderado)
        """
        adjustments = {
            "position_size_multiplier": 0.65,    # 65% do tamanho padrão
            "sl_atr_multiplier": 1.5,             # SL padrão
            "tp_atr_multiplier": 3.0,             # TP padrão
            "max_drawdown_percent": 2.8,          # Max drawdown 2.8%
        }

        return adjustments

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de GRT.

        GRT passa por:
        - Accumulation: Builders acumulando
        - Expansion: Crescimento de uso
        - Peak: Máxima utilização DeFi
        - Contraction: Redução de fluxo
        """
        defi_tvl = current_data.get("defi_tvl_trend", "neutral")
        price_action = current_data.get("price_action", "neutral")

        if defi_tvl == "increasing" and price_action == "uptrend":
            return "expansion"
        elif price_action == "downtrend":
            return "contraction"
        elif defi_tvl == "stable" and price_action == "sideways":
            return "consolidation"
        else:
            return "accumulation"

    def should_trade(self, market_regime: str, d1_bias: str,
                    btc_bias: Optional[str] = None) -> bool:
        """
        GRT (mid-cap 2.8) deve operar em:
        - Risk-on com D1 long (principal regime)
        - Neutro apenas com D1 strong long
        - Avoid risk-off
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
