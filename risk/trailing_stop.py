"""
Trailing Stop Loss Manager — Core Logic

Módulo que implementa lógica de trailing stop loss dinâmico.
Gerencia ativação, rastreamento de high e cálculo de stop price.

Autor: Senior Engineer + The Brain (Personas 1 e 3)
Data: 2026-02-22
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


@dataclass
class TrailingStopConfig:
    """Configuração de Trailing Stop Loss."""

    activation_threshold_r: float = 1.5
    """Quantos R de lucro precisam ser atingidos para ativar TSL. Padrão: 1.5R"""

    stop_distance_pct: float = 0.10
    """Distância percentual do stop em relação ao high. Padrão: 10%"""

    update_interval_ms: int = 100
    """Intervalo de atualização em millisegundos"""

    enabled: bool = True
    """Se trailing stop loss está globalmente habilitado"""

    dry_run: bool = False
    """Se True, loga mas não executa ordens"""


@dataclass
class TrailingStopState:
    """Estado de Trailing Stop para uma posição."""

    active: bool = False
    """Se o trailing stop está ativo"""

    high_price: float = 0.0
    """Maior preço atingido desde ativação"""

    stop_price: float = 0.0
    """Nível de stop (dinâmico)"""

    activated_at: Optional[datetime] = None
    """Data/hora de ativação"""

    deactivated_at: Optional[datetime] = None
    """Data/hora de desativação (se ocorreu)"""

    triggered_at: Optional[datetime] = None
    """Data/hora que foi acionado"""


class TrailingStopManager:
    """
    Gerenciador de Trailing Stop Loss.

    Implementa lógica de:
    - Ativar TSL quando lucro atinge threshold
    - Rastrear maior preço desde ativação
    - Calcular nível de stop dinamicamente
    - Detectar acionamento do TSL
    """

    def __init__(self, config: TrailingStopConfig):
        """
        Inicializa o gerenciador com configuração.

        Args:
            config: TrailingStopConfig com parâmetros
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def evaluate(
        self,
        current_price: float,
        entry_price: float,
        state: TrailingStopState,
        risk_r: float = 0.03,
    ) -> TrailingStopState:
        """
        Avalia e atualiza estado do TSL.

        Args:
            current_price: Preço atual
            entry_price: Preço de entrada
            state: Estado atual do TSL
            risk_r: Risk por operação em % (usado para normalizar threshold)

        Returns:
            TrailingStopState atualizado
        """
        if not self.config.enabled:
            return state

        # Calcular lucro atual
        profit_pct = self._calculate_profit_pct(current_price, entry_price)
        profit_r = self._normalize_to_r(profit_pct, risk_r)

        # 1. Verificar ativação (com tolerância de ponto flutuante)
        threshold_tolerance = 1e-9
        if not state.active and profit_r >= (self.config.activation_threshold_r - threshold_tolerance):
            self.logger.info(
                f"🔔 TSL ATIVADO — profit={profit_r:.2f}R, "
                f"threshold={self.config.activation_threshold_r:.2f}R"
            )
            state.active = True
            state.high_price = current_price
            state.activated_at = datetime.now()

        # 2. Se ativo, atualizar high e calcular stop
        if state.active:
            # Rastrear maior preço
            if current_price > state.high_price:
                state.high_price = current_price
                self.logger.debug(
                    f"📈 Novo high no TSL: {state.high_price:.8f} "
                    f"(preço atual: {current_price:.8f})"
                )

            # Calcular nível de stop (mantém distância %)
            state.stop_price = self._calculate_stop_price(
                state.high_price,
                self.config.stop_distance_pct
            )

        # 3. Se lucro volta negativo ou break-even, desativar TSL
        if state.active and profit_pct <= 0:
            self.logger.warning(
                f"⚠️  TSL DESATIVADO — Posição voltou a perda (profit={profit_pct:.2%})"
            )
            state.active = False
            state.deactivated_at = datetime.now()

        return state

    def has_triggered(
        self,
        current_price: float,
        state: TrailingStopState
    ) -> bool:
        """
        Verifica se o TSL foi acionado.

        Args:
            current_price: Preço atual
            state: Estado do TSL

        Returns:
            True se preço caiu abaixo do stop, False caso contrário
        """
        if not state.active:
            return False

        triggered = current_price <= state.stop_price

        if triggered:
            self.logger.warning(
                f"🚨 TSL ACIONADO! Preço {current_price:.8f} "
                f"≤ Stop {state.stop_price:.8f}"
            )
            state.triggered_at = datetime.now()

        return triggered

    @staticmethod
    def _calculate_profit_pct(current_price: float, entry_price: float) -> float:
        """
        Calcula lucro em percentual.

        Fórmula: ((preço_atual - entry) / entry) * 100

        Args:
            current_price: Preço atual
            entry_price: Preço de entrada

        Returns:
            Lucro em percentual (-1.0 = -100%, 0.5 = 50%, etc)
        """
        if entry_price <= 0:
            return 0.0

        return (current_price - entry_price) / entry_price

    @staticmethod
    def _normalize_to_r(profit_pct: float, risk_r: float = 0.03) -> float:
        """
        Normaliza lucro para unidades de R.

        Fórmula: profit_pct / risk_r
        Exemplo: profit=15%, risk=3% → 15/3 = 5R

        Args:
            profit_pct: Lucro em percentual (0.15 = 15%)
            risk_r: Risk por operação em percentual (padrão 3%)

        Returns:
            Lucro em R units
        """
        if risk_r <= 0:
            return 0.0

        return profit_pct / risk_r

    @staticmethod
    def _calculate_stop_price(high_price: float, stop_distance_pct: float) -> float:
        """
        Calcula nível de stop dinamicamente.

        Fórmula: high_price × (1 - stop_distance_pct)
        Exemplo: high=130, distância=10% → 130 × 0.9 = 117

        Args:
            high_price: Maior preço atingido
            stop_distance_pct: Distância em % (0.10 = 10%)

        Returns:
            Preço de stop
        """
        if high_price <= 0:
            return 0.0

        return high_price * (1 - stop_distance_pct)

    def get_status_string(self, state: TrailingStopState) -> str:
        """
        Gera string de status legível.

        Args:
            state: Estado do TSL

        Returns:
            String formatada com status
        """
        if not state.active:
            return "TSL: INATIVO"

        return (
            f"TSL: ATIVO | High={state.high_price:.8f} | "
            f"Stop={state.stop_price:.8f} | "
            f"Distância={(state.high_price - state.stop_price) / state.high_price * 100:.2f}%"
        )


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def create_tsl_manager(enabled: bool = True, dry_run: bool = False) -> TrailingStopManager:
    """
    Factory para criar gerenciador TSL com config padrão.

    Args:
        enabled: Se deve estar habilitado
        dry_run: Se deve rodar em modo simulação

    Returns:
        TrailingStopManager configurado
    """
    config = TrailingStopConfig(
        activation_threshold_r=1.5,
        stop_distance_pct=0.10,
        update_interval_ms=100,
        enabled=enabled,
        dry_run=dry_run,
    )
    return TrailingStopManager(config)


def init_tsl_state() -> TrailingStopState:
    """
    Inicializa novo estado TSL (usado ao abrir posição).

    Returns:
        TrailingStopState vazio
    """
    return TrailingStopState(
        active=False,
        high_price=0.0,
        stop_price=0.0,
        activated_at=None,
        deactivated_at=None,
        triggered_at=None,
    )


if __name__ == "__main__":
    # Exemplo de uso
    logging.basicConfig(level=logging.INFO)

    config = TrailingStopConfig(
        activation_threshold_r=1.5,
        stop_distance_pct=0.10,
    )

    manager = TrailingStopManager(config)
    state = TrailingStopState()

    # Simular entrada em 100
    entry = 100.0

    # Preço sobe para 115 (15% lucro = 1.5R com risk 10%)
    print("\n1️⃣ Preço sobe para 115 (ativa TSL):")
    state = manager.evaluate(current_price=115, entry_price=entry, state=state, risk_r=0.10)
    print(f"  {manager.get_status_string(state)}")

    # Preço sobe para 130
    print("\n2️⃣ Preço sobe para 130:")
    state = manager.evaluate(current_price=130, entry_price=entry, state=state, risk_r=0.10)
    print(f"  {manager.get_status_string(state)}")

    # Preço cai para 117 (ativa TSL)
    print("\n3️⃣ Preço cai para 117 (TSL acionado):")
    state = manager.evaluate(current_price=117, entry_price=entry, state=state, risk_r=0.10)
    triggered = manager.has_triggered(current_price=117, state=state)
    print(f"  {manager.get_status_string(state)}")
    print(f"  TSL Triggered: {triggered}")
