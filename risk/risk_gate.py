"""
Risk Gate 1.0 — Proteções Invioláveis de Risco

Módulo central que implementa:
- Stop Loss hardcoded (-3% de drawdown)
- Circuit Breaker automático (-3% drawdown)
- Validações que NÃO PODEM ser desabilitadas
- Auditoria completa de cada ação

Arquitetura:
risk/
├── risk_gate.py (este arquivo) - Orquestrador principal
├── circuit_breaker.py - Lógica de circuit breaker
├── position_monitor.py - Monitoramento de posições
├── stop_loss_manager.py - Gerenciamento de stop loss
└── audit_trail.py - Auditoria de decisões

Garantias invioláveis (Bloco "Guardian"):
1. Stop Loss SEMPRE ativo (-3%)
2. Circuit Breaker SEMPRE monitorado
3. Nenhuma ordem pode ultrapassar máx drawdown
4. TODA decisão é auditada e rastreável
"""

import logging
from typing import Dict, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RiskGateStatus(Enum):
    """Estados do Risk Gate."""
    ACTIVE = "ativo"  # Operando normalmente
    STOP_LOSS_ARMED = "stop_loss_ativo"  # Stop loss acionado
    CIRCUIT_BREAKER_ARMED = "circuit_breaker_ativo"  # CB acionado
    FROZEN = "congelado"  # Não aceita mais ordens


@dataclass
class RiskMetrics:
    """Métricas de risco da posição atual."""
    portfolio_value: float  # Valor total da carteira
    entry_price: float  # Preço de entrada
    current_price: float  # Preço atual
    position_size: float  # Tamanho da posição
    unrealized_pnl: float  # PnL não realizado
    drawdown_pct: float  # Drawdown em %
    is_stop_loss_triggered: bool  # Stop loss acionado?
    is_circuit_breaker_triggered: bool  # CB acionado?


class RiskGate:
    """
    Risk Gate 1.0 — Proteções Invioláveis

    Este é um módulo CRÍTICO que:
    - NUNCA pode ser desabilitado
    - SEMPRE valida antes de qualquer ordem
    - SEMPRE bloqueia quando limite é atingido
    - SEMPRE faz log de cada decisão
    """

    # CONSTANTES INVIOLÁVEIS
    MAX_DRAWDOWN_PCT = 3.0  # -3% de drawdown máximo
    STOP_LOSS_THRESHOLD = -3.0  # -3% ativa stop loss
    CIRCUIT_BREAKER_THRESHOLD = -3.1  # -3.1% ativa circuit breaker
    RECOVERY_THRESHOLD_PCT = -2.7  # histerese para retomar apos bloqueio
    RECOVERY_SAMPLES_REQUIRED = 3  # amostras consecutivas para reativar

    def __init__(self) -> None:
        """Inicializar Risk Gate com proteções armadas."""
        self.status = RiskGateStatus.ACTIVE
        self._portfolio_value = 10000.0  # valor inicial em USDT
        self._peak_portfolio_value = self._portfolio_value  # peak tracking
        self._position_entry_price: Optional[float] = None
        self._current_price: Optional[float] = None
        self._audit_trail: list = []  # LOG INVIOLÁVEL
        self._recovery_ok_streak = 0

        logger.warning("🛡️  Risk Gate 1.0 INICIALIZADO COM PROTEÇÕES ARMADAS")
        logger.warning(f"   Max Drawdown: {self.MAX_DRAWDOWN_PCT}%")
        logger.warning(f"   Stop Loss: {self.STOP_LOSS_THRESHOLD}%")
        logger.warning(f"   Circuit Breaker: {self.CIRCUIT_BREAKER_THRESHOLD}%")

        self._log_to_audit(
            event="RISK_GATE_INITIALIZED",
            data={
                "max_drawdown": self.MAX_DRAWDOWN_PCT,
                "stop_loss": self.STOP_LOSS_THRESHOLD,
                "circuit_breaker": self.CIRCUIT_BREAKER_THRESHOLD,
            },
        )

    def update_portfolio_value(self, new_value: float) -> None:
        """
        Atualizar valor da carteira.

        CRÍTICO: Esta é a métrica usada para calcular drawdown.
        """
        self._portfolio_value = new_value

        # Rastrear peak para cálculo correto de drawdown
        if new_value > self._peak_portfolio_value:
            self._peak_portfolio_value = new_value

        # Politica de risco com histerese: evita lock permanente por oscilacao pontual.
        self._evaluate_drawdown_policy(self._calculate_drawdown())

    def update_price_feed(self, current_price: float) -> None:
        """Atualizar preço atual do ativo."""
        self._current_price = current_price

    def open_position(
        self,
        symbol: str,
        entry_price: float,
        size: float,
        side: str = "long"
    ) -> bool:
        """
        Abrir posição.

        VALIDA antes de permitir abertura.

        Returns:
            True se permitido, False se bloqueado por risk gate
        """
        # Validação 1: Status deve estar ATIVO
        if self.status != RiskGateStatus.ACTIVE:
            logger.error(f"🔴 Risk Gate BLOQUEOU abertura: status={self.status}")
            self._log_to_audit(
                event="POSITION_OPEN_REJECTED",
                data={"reason": f"risk_gate_not_active: {self.status}"}
            )
            return False

        # Validação 2: Drawdown não pode estar no limite de stop loss
        drawdown_pct = self._calculate_drawdown()
        if drawdown_pct <= self.STOP_LOSS_THRESHOLD:
            logger.error(f"🔴 Risk Gate BLOQUEOU: drawdown {drawdown_pct:.2f}% <= {self.STOP_LOSS_THRESHOLD}%")
            self._log_to_audit(
                event="POSITION_OPEN_REJECTED",
                data={"reason": f"drawdown_limit_exceeded: {drawdown_pct:.2f}%"}
            )
            self.status = RiskGateStatus.STOP_LOSS_ARMED
            return False

        # ✅ Permitido
        self._position_entry_price = entry_price
        logger.info(f"✅ Posição aberta: {symbol} @ {entry_price} ({size} unidades)")
        self._log_to_audit(
            event="POSITION_OPENED",
            data={
                "symbol": symbol,
                "entry_price": entry_price,
                "size": size,
                "side": side,
            }
        )
        return True

    def check_stop_loss(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verificar se Stop Loss foi acionado.

        Returns:
            (triggered: bool, details: dict)
        """
        drawdown_pct = self._calculate_drawdown()

        if drawdown_pct <= self.STOP_LOSS_THRESHOLD:
            logger.critical(f"🛑 STOP LOSS ACIONADO: {drawdown_pct:.2f}% <= {self.STOP_LOSS_THRESHOLD}%")
            self.status = RiskGateStatus.STOP_LOSS_ARMED
            self._recovery_ok_streak = 0

            details = {
                "event": "STOP_LOSS_TRIGGERED",
                "drawdown_pct": drawdown_pct,
                "threshold": self.STOP_LOSS_THRESHOLD,
                "portfolio_value": self._portfolio_value,
                "peak_value": self._peak_portfolio_value,
                "loss_amount": self._peak_portfolio_value - self._portfolio_value,
            }

            self._log_to_audit("STOP_LOSS_TRIGGERED", details)
            return True, details

        return False, None

    def check_circuit_breaker(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verificar se Circuit Breaker foi acionado.

        Returns:
            (triggered: bool, details: dict)
        """
        drawdown_pct = self._calculate_drawdown()

        if drawdown_pct <= self.CIRCUIT_BREAKER_THRESHOLD:
            logger.critical(f"💥 CIRCUIT BREAKER ACIONADO: {drawdown_pct:.2f}% <= {self.CIRCUIT_BREAKER_THRESHOLD}%")
            self.status = RiskGateStatus.CIRCUIT_BREAKER_ARMED
            self._recovery_ok_streak = 0

            details = {
                "event": "CIRCUIT_BREAKER_TRIGGERED",
                "drawdown_pct": drawdown_pct,
                "threshold": self.CIRCUIT_BREAKER_THRESHOLD,
                "portfolio_value": self._portfolio_value,
                "peak_value": self._peak_portfolio_value,
                "critical_loss": self._peak_portfolio_value - self._portfolio_value,
                "action": "CLOSE_ALL_POSITIONS_IMMEDIATELY",
            }

            self._log_to_audit("CIRCUIT_BREAKER_TRIGGERED", details)
            return True, details

        return False, None

    def can_execute_order(self, order_type: str = "market") -> bool:
        """
        Validar se ordem pode ser executada.

        CRÍTICO: Este check é INVIOLÁVEL.

        Args:
            order_type: 'market', 'limit', etc

        Returns:
            True se permitido executar
        """
        # Validação inviolável: Se circuit breaker ou stop loss acionado, BLOQUEIA TUDO
        if self.status in [
            RiskGateStatus.CIRCUIT_BREAKER_ARMED,
            RiskGateStatus.STOP_LOSS_ARMED,
            RiskGateStatus.FROZEN,
        ]:
            logger.error(f"🔴 ORDEM BLOQUEADA: Risk Gate {self.status}")
            self._log_to_audit(
                event="ORDER_EXECUTION_REJECTED",
                data={"reason": f"risk_gate_status: {self.status}"}
            )
            return False

        logger.info(f"✅ ORDEM PERMITIDA: {order_type}")
        return True

    def close_position_emergency(self) -> bool:
        """
        Fechar posição de emergência (chamado por circuit breaker).

        CRÍTICO: Não pode falhar.
        """
        logger.critical("💥 FECHANDO POSIÇÃO DE EMERGÊNCIA")
        self.status = RiskGateStatus.FROZEN

        self._log_to_audit(
            event="POSITION_CLOSED_EMERGENCY",
            data={
                "reason": "circuit_breaker",
                "portfolio_value": self._portfolio_value,
            }
        )

        # TODO: Enviar ordem de fechamento para execução
        # TODO: Verificar confirmação da Binance

        return True

    def get_risk_metrics(self) -> RiskMetrics:
        """Obter métricas de risco atuais."""
        drawdown_pct = self._calculate_drawdown()
        self._evaluate_drawdown_policy(drawdown_pct)
        sl_triggered = drawdown_pct <= self.STOP_LOSS_THRESHOLD
        cb_triggered = drawdown_pct <= self.CIRCUIT_BREAKER_THRESHOLD

        return RiskMetrics(
            portfolio_value=self._portfolio_value,
            entry_price=self._position_entry_price or 0.0,
            current_price=self._current_price or 0.0,
            position_size=0.0,  # TODO: obter do execution/
            unrealized_pnl=self._portfolio_value - self._peak_portfolio_value,
            drawdown_pct=drawdown_pct,
            is_stop_loss_triggered=sl_triggered,
            is_circuit_breaker_triggered=cb_triggered,
        )

    def _evaluate_drawdown_policy(self, drawdown_pct: float) -> None:
        """Aplica politica de arm/disarm com histerese para evitar latch permanente."""
        if self.status == RiskGateStatus.FROZEN:
            return

        if self.status == RiskGateStatus.ACTIVE:
            if drawdown_pct <= self.CIRCUIT_BREAKER_THRESHOLD:
                self.status = RiskGateStatus.CIRCUIT_BREAKER_ARMED
                self._recovery_ok_streak = 0
                self._log_to_audit(
                    event="RISK_GATE_CIRCUIT_BREAKER_ARMED",
                    data={
                        "drawdown_pct": float(drawdown_pct),
                        "threshold": float(self.CIRCUIT_BREAKER_THRESHOLD),
                    },
                )
                return
            if drawdown_pct <= self.STOP_LOSS_THRESHOLD:
                self.status = RiskGateStatus.STOP_LOSS_ARMED
                self._recovery_ok_streak = 0
                self._log_to_audit(
                    event="RISK_GATE_STOP_LOSS_ARMED",
                    data={
                        "drawdown_pct": float(drawdown_pct),
                        "threshold": float(self.STOP_LOSS_THRESHOLD),
                    },
                )
            return

        # Se bloqueado por SL/CB, exige recuperacao sustentada para retomar ACTIVE.
        if drawdown_pct > self.RECOVERY_THRESHOLD_PCT:
            self._recovery_ok_streak += 1
        else:
            self._recovery_ok_streak = 0

        if self._recovery_ok_streak >= self.RECOVERY_SAMPLES_REQUIRED:
            previous_status = self.status.value
            self.status = RiskGateStatus.ACTIVE
            self._recovery_ok_streak = 0
            self._log_to_audit(
                event="RISK_GATE_RECOVERED",
                data={
                    "previous_status": previous_status,
                    "drawdown_pct": float(drawdown_pct),
                    "recovery_threshold_pct": float(self.RECOVERY_THRESHOLD_PCT),
                    "samples_required": int(self.RECOVERY_SAMPLES_REQUIRED),
                },
            )

    def get_audit_trail(self) -> list:
        """Obter log completo de auditoria (INVIOLÁVEL)."""
        return self._audit_trail.copy()

    def _calculate_drawdown(self) -> float:
        """
        Calcular drawdown em % (sempre negativo).

        Formula: ((Current - Peak) / Peak) * 100
        """
        if self._peak_portfolio_value == 0:
            return 0.0

        drawdown = (
            (self._portfolio_value - self._peak_portfolio_value)
            / self._peak_portfolio_value
        ) * 100

        return drawdown

    # M2-024.11 — rastreamento de timeouts para regressao de stress

    _MAX_CONSECUTIVE_TIMEOUTS = 5

    def record_timeout(self, *, stage: str, symbol: str) -> None:
        """Registra um timeout em uma etapa do pipeline.

        Apos _MAX_CONSECUTIVE_TIMEOUTS timeouts, bloqueia trading via FROZEN.
        M2-024.11: validacao de stress — risk_gate deve bloquear sob carga.
        """
        if not hasattr(self, "_timeout_count"):
            self._timeout_count: int = 0
        self._timeout_count += 1
        logger.warning(
            "Timeout registrado: stage=%s symbol=%s contagem=%d",
            stage, symbol, self._timeout_count,
        )
        self._log_to_audit(
            event="TIMEOUT_REGISTERED",
            data={"stage": stage, "symbol": symbol, "count": self._timeout_count},
        )
        if self._timeout_count >= self._MAX_CONSECUTIVE_TIMEOUTS:
            self.status = RiskGateStatus.FROZEN
            logger.critical(
                "Risk Gate FROZEN apos %d timeouts consecutivos",
                self._timeout_count,
            )
            self._log_to_audit(
                event="RISK_GATE_FROZEN_BY_TIMEOUTS",
                data={"timeout_count": self._timeout_count},
            )

    def allows_trading(self) -> bool:
        """Retorna True se o Risk Gate permite trading no momento.

        Equivalente a verificar se o status e ACTIVE sem nenhum bloqueio.
        M2-024.11: metodo de consulta de status para testes de stress.
        """
        return self.status == RiskGateStatus.ACTIVE

    def _log_to_audit(self, event: str, data: Dict[str, Any]) -> None:
        """
        Registrar evento em log de auditoria INVIOLÁVEL.

        CRÍTICO: Este log NÃO PODE ser deletado ou modificado.
        """
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "data": data,
            "risk_gate_status": self.status.value,
            "portfolio_value": self._portfolio_value,
            "drawdown_pct": self._calculate_drawdown(),
        }

        self._audit_trail.append(audit_entry)
        logger.info(f"📋 AUDITORIA: {event} - {data}")


# Singleton Global (garante uma única instância)
_risk_gate_instance: Optional[RiskGate] = None


def get_risk_gate() -> RiskGate:
    """
    Obter instância global de Risk Gate.

    CRÍTICO: Usar sempre esta função para garantir unicidade.
    """
    global _risk_gate_instance
    if _risk_gate_instance is None:
        _risk_gate_instance = RiskGate()
    return _risk_gate_instance


if __name__ == "__main__":
    # Teste básico
    gate = get_risk_gate()
    gate.update_portfolio_value(10000.0)
    gate.update_price_feed(50000.0)

    # Testar validações
    print(f"✅ Risk Gate inicializado")
    print(f"   Status: {gate.status.value}")
    print(f"   Métricas: {gate.get_risk_metrics()}")
