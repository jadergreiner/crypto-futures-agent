"""
Playbook especializado para IMX (Immutable X).

Característica: Layer 2 para NFTs/gaming, escalabilidade Ethereum
- Beta: 3.0 (low-cap especulativo)
- Classificação: Layer 2 NFT/Gaming
- Sensibilidade: Narrativa NFT/gaming, adoção de Layer 2 solutions
"""

import logging
from typing import Dict, Any, Optional
from playbooks.base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class IMXPlaybook(BasePlaybook):
    """
    Playbook para Immutable X (IMX).
    Layer 2 NFT/gaming token com beta 3.0 (especulativo).
    """

    def __init__(self):
        super().__init__("IMXUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para IMX.

        Immutable X é sensível a:
        - Narrativa de NFT e gaming em Layer 2
        - Adoção de soluções de escalabilidade Ethereum
        - Ciclos de momentum em altcoins de gaming
        """
        adjustments = {
            "nft_gaming_narrative": 1.0,   # Core: narrativa NFT/gaming
            "layer2_adoption": 0.8,        # Sensível a adoção de Layer 2
            "ethereum_scaling": 0.7,       # Segue narrativa de scaling
            "altcoin_momentum": 0.7,       # Segue momentum geral de altcoins
            "macro_risk_off": -1.1,        # Fortemente afetado em risk-off
        }

        return adjustments

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para IMX.

        Beta 3.0 (low-cap especulativo):
        - 52% de tamanho de posição em relação ao baseline
        - SL mais apertado, TP mais próximo
        """
        adjustments = {
            "position_size_multiplier": 0.52,    # 52% do tamanho padrão
            "sl_atr_multiplier": 1.4,             # SL apertado (ATR 1.4x)
            "tp_atr_multiplier": 2.6,             # TP próximo (ATR 2.6x)
            "max_drawdown_percent": 2.5,          # Max drawdown 2.5%
        }

        return adjustments

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de IMX.

        Immutable X passa por:
        - Accumulation: Preparação para crescimento
        - Growth: Fase de expansão NFT/gaming
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
        IMX (low-cap, beta 3.0) deve operar em:
        - Risk-on com D1 LONG ou STRONG_LONG
        - Avoid em risk-off
        - Mais restritivo que mid-caps
        """
        if d1_bias == "NEUTRO":
            return False

        if market_regime == "RISK_ON":
            return d1_bias in ["LONG", "STRONG_LONG"]
        else:
            # RISK_OFF ou NEUTRO_MERCADO: não operar
            return False
