"""
Playbook especifico para IOTA (IOTAUSDT).
Foco em IoT, economia de maquinas e infraestrutura DLT sem taxas.
"""

import logging
from typing import Any

from .base_playbook import BasePlaybook

logger = logging.getLogger(__name__)


class IOTAPlaybook(BasePlaybook):
    """Playbook para IOTAUSDT com foco em IoT e economia de maquinas."""

    def __init__(self) -> None:
        super().__init__("IOTAUSDT")

    def get_confluence_adjustments(
        self, context: dict[str, Any]
    ) -> dict[str, float]:
        """Ajustes de confluencia para IOTAUSDT."""
        ajustes: dict[str, float] = {}

        # Narrativa IoT/industria 4.0 impulsiona IOTA diretamente
        if context.get("iot_narrative"):
            ajustes["iot_narrative"] = 0.9
            logger.debug("IOTA: +0.9 confluencia por narrativa IoT ativa")

        # Parcerias industriais e adocao institucional
        if context.get("industrial_adoption"):
            ajustes["industrial_adoption"] = 0.7
            logger.debug("IOTA: +0.7 confluencia por adocao industrial")

        # Alinhamento com BTC reforça tendencia em mid-caps L1
        btc_bias = context.get("btc_bias")
        d1_bias = context.get("d1_bias")
        if btc_bias and d1_bias and btc_bias == d1_bias and btc_bias != "NEUTRO":
            ajustes["btc_alignment"] = 0.5
            logger.debug(
                f"IOTA: +0.5 confluencia — alinhamento BTC/D1 {btc_bias}"
            )

        # Altseason amplifica mid-caps DAG
        if context.get("altseason_active"):
            ajustes["altseason_amplifier"] = 0.6
            logger.debug("IOTA: +0.6 confluencia — altseason ativa")

        # Penalidade: mercado risk-off suprime mid-caps com beta > 2
        market_regime = context.get("market_regime", "")
        if market_regime == "RISK_OFF":
            ajustes["risk_off_penalty"] = -0.8
            logger.debug("IOTA: -0.8 confluencia — regime RISK_OFF")

        return ajustes

    def get_risk_adjustments(
        self, context: dict[str, Any]
    ) -> dict[str, float]:
        """Ajustes de risco para IOTAUSDT (mid-cap, beta 2.2)."""
        ajustes: dict[str, float] = {
            "position_size_multiplier": 0.8,
            "stop_multiplier": 1.2,
        }

        atr_pct = float(context.get("atr_pct", 3.0))
        if atr_pct > 6.0:
            # Alta volatilidade: reduzir exposicao
            ajustes["position_size_multiplier"] = 0.6
            ajustes["stop_multiplier"] = 1.5
            logger.debug(
                f"IOTA: ATR% {atr_pct:.1f} — posicao 60%, stop 1.5x"
            )
        elif atr_pct < 2.0:
            # Volatilidade baixa: mercado comprimido, pode aumentar
            ajustes["position_size_multiplier"] = 0.9
            logger.debug(
                f"IOTA: ATR% {atr_pct:.1f} — posicao 90% (baixa vol)"
            )

        return ajustes

    def get_cycle_phase(self, current_data: dict[str, Any]) -> str:
        """Identifica fase de ciclo de IOTAUSDT."""
        narrative = current_data.get("market_narrative", "")
        d1_bias = current_data.get("d1_bias", "NEUTRO")
        btc_phase = current_data.get("btc_cycle_phase", "ACCUMULATION")

        if narrative in ("IOT", "MACHINE_ECONOMY") and d1_bias == "LONG":
            return "IOTA_NARRATIVA_EXPANSION"
        if btc_phase == "BULL_RUN" and d1_bias == "LONG":
            return "IOTA_ALTSEASON_IMPULSO"
        if d1_bias == "SHORT":
            return "IOTA_CONTRACAO"
        if d1_bias == "LONG":
            return "IOTA_ACUMULACAO"
        return "IOTA_LATERALIZACAO"
