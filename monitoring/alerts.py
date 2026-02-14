"""
Sistema de alertas para eventos críticos.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AlertManager:
    """Gerencia alertas para eventos críticos."""
    
    @staticmethod
    def alert_drawdown(level: str, current_dd: float, limit: float) -> None:
        """Alerta de drawdown."""
        logger.critical(f"⚠️  DRAWDOWN ALERT [{level}]: {current_dd*100:.2f}% (limit: {limit*100:.2f}%)")
    
    @staticmethod
    def alert_flash_crash(symbol: str, change_pct: float, minutes: int) -> None:
        """Alerta de flash crash/pump."""
        direction = "PUMP" if change_pct > 0 else "CRASH"
        logger.critical(f"⚠️  FLASH {direction} ALERT: {symbol} moved {abs(change_pct)*100:.2f}% in {minutes} minutes")
    
    @staticmethod
    def alert_funding_extreme(symbol: str, funding_rate: float) -> None:
        """Alerta de funding rate extremo."""
        logger.warning(f"⚠️  EXTREME FUNDING: {symbol} funding rate = {funding_rate*100:.4f}%")
    
    @staticmethod
    def alert_liquidation_cascade(symbol: str, volume: float, threshold: float) -> None:
        """Alerta de cascade de liquidações."""
        logger.warning(f"⚠️  LIQUIDATION CASCADE: {symbol} volume = ${volume:,.0f} (threshold: ${threshold:,.0f})")
    
    @staticmethod
    def alert_system_error(component: str, error: str) -> None:
        """Alerta de erro do sistema."""
        logger.critical(f"⚠️  SYSTEM ERROR [{component}]: {error}")
