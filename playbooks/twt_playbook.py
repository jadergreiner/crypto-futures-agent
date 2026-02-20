"""
Playbook especializado para TWT (Trust Wallet Token).

Característica: Token de utilidade de wallet com integração Binance
- Beta: 2.0 (mid-cap, comportamento moderado)
- Classificação: Wallet ecosystem utility token
- Sensibilidade: Adoção de wallet, dinâmica Binance ecosystem
"""

import logging
from typing import Dict, Any, Optional
from playbooks.base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class TWTPlaybook(BasePlaybook):
    """
    Playbook para Trust Wallet Token (TWT).
    Wallet ecosystem token com beta 2.0 (moderado).
    """

    def __init__(self):
        super().__init__("TWTUSDT")

    def get_confluence_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de confluência para TWT.

        Trust Wallet Token é sensível a:
        - Adoção de wallet e integração Binance
        - Crescimento de usuários em crypto
        - Dinâmica de utility tokens
        """
        adjustments = {
            "binance_ecosystem": 1.0,     # Forte exposição ao ecossistema Binance
            "adoption_narrative": 0.7,    # Sensível a adoção de wallets
            "defi_tvl_growth": 0.4,       # Segue parcialmente TVL growth
            "macro_risk_off": -0.8,       # Moderadamente afetado em risk-off
        }

        return adjustments

    def get_risk_adjustments(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Ajustes de risco para TWT.

        Beta 2.0 (mid-cap):
        - 75% de tamanho de posição em relação ao baseline
        - SL padrão, TP padrão
        """
        adjustments = {
            "position_size_multiplier": 0.75,    # 75% do tamanho padrão
            "sl_atr_multiplier": 1.5,             # SL padrão (ATR 1.5x)
            "tp_atr_multiplier": 3.0,             # TP padrão (ATR 3.0x)
            "max_drawdown_percent": 3.5,          # Max drawdown 3.5%
        }

        return adjustments

    def get_cycle_phase(self, current_data: Dict[str, Any]) -> str:
        """
        Identifica fase do ciclo de TWT.

        Trust Wallet passa por:
        - Accumulation: Preparação para crescimento
        - Growth: Fase de adoção
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
        TWT (mid-cap, beta 2.0) deve operar em:
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
