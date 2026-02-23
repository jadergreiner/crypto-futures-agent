"""
Testes Unitários — Trailing Stop Loss (S2-4)

Test Suite para validar lógica de TSL isoladamente.

Personas: Quality (#12) + Audit (#8)
Data: 2026-02-22
"""

import pytest
from datetime import datetime
from risk.trailing_stop import (
    TrailingStopConfig,
    TrailingStopState,
    TrailingStopManager,
    create_tsl_manager,
    init_tsl_state,
)


class TestTrailingStopActivation:
    """Testes de ativação do TSL."""

    def test_tsl_activation_threshold_reached(self):
        """TSL ativa quando lucro >= threshold."""
        config = TrailingStopConfig(activation_threshold_r=1.5)
        manager = TrailingStopManager(config)
        state = TrailingStopState()

        # Entry: 100, Preço: 115 (profit: 15% = 1.5R com risk 10%)
        state = manager.evaluate(
            current_price=115,
            entry_price=100,
            state=state,
            risk_r=0.10
        )

        assert state.active is True
        assert state.high_price == 115
        assert state.activated_at is not None

    def test_tsl_activation_threshold_not_reached(self):
        """TSL NÃO ativa se lucro < threshold."""
        config = TrailingStopConfig(activation_threshold_r=1.5)
        manager = TrailingStopManager(config)
        state = TrailingStopState()

        # Entry: 100, Preço: 110 (profit: 10% = 1.0R com risk 10%)
        state = manager.evaluate(
            current_price=110,
            entry_price=100,
            state=state,
            risk_r=0.10
        )

        assert state.active is False

    def test_tsl_activation_exact_threshold(self):
        """TSL ativa no exato limite."""
        config = TrailingStopConfig(activation_threshold_r=1.5)
        manager = TrailingStopManager(config)
        state = TrailingStopState()

        # Entry: 100, profit exato de 1.5R (15%)
        state = manager.evaluate(
            current_price=115,
            entry_price=100,
            state=state,
            risk_r=0.10
        )

        assert state.active is True


class TestTrailingHighTracking:
    """Testes de rastreamento do maior preço."""

    def test_trailing_high_update_on_new_high(self):
        """High atualiza quando preço sobe."""
        config = TrailingStopConfig(activation_threshold_r=1.5)
        manager = TrailingStopManager(config)
        state = TrailingStopState()

        # Ativar TSL
        state = manager.evaluate(115, 100, state, risk_r=0.10)
        assert state.high_price == 115

        # Preço sobe para 130
        state = manager.evaluate(130, 100, state, risk_r=0.10)
        assert state.high_price == 130

    def test_trailing_high_not_update_on_lower_price(self):
        """High não muda se preço cai."""
        config = TrailingStopConfig(activation_threshold_r=1.5)
        manager = TrailingStopManager(config)
        state = TrailingStopState()

        # Ativar TSL com preço 130
        state = manager.evaluate(130, 100, state, risk_r=0.10)
        assert state.high_price == 130

        # Preço cai para 125
        state = manager.evaluate(125, 100, state, risk_r=0.10)
        assert state.high_price == 130  # Não muda

    def test_trailing_high_sequence(self):
        """Rastreia corretamente em sequência: 115 → 130 → 125 → 135."""
        config = TrailingStopConfig(activation_threshold_r=1.5)
        manager = TrailingStopManager(config)
        state = TrailingStopState()
        entry = 100

        prices = [115, 130, 125, 135, 120]
        expected_highs = [115, 130, 130, 135, 135]

        for price, expected_high in zip(prices, expected_highs):
            state = manager.evaluate(price, entry, state, risk_r=0.10)
            assert state.high_price == expected_high


class TestTrailingStopCalculation:
    """Testes de cálculo do nível de stop."""

    def test_trailing_stop_price_calculation(self):
        """Stop price = high × (1 - distância)."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10
        )
        manager = TrailingStopManager(config)
        state = TrailingStopState()

        # High: 130, distância: 10% → Stop: 117
        state = manager.evaluate(130, 100, state, risk_r=0.10)
        assert state.high_price == 130
        assert state.stop_price == pytest.approx(130 * 0.9, abs=0.01)  # 117

    def test_trailing_stop_price_with_different_distances(self):
        """Stop price com diferentes distâncias."""
        entry = 100
        high = 150

        test_cases = [
            (0.05, 142.5),    # 5% distância → 142.5
            (0.10, 135.0),    # 10% distância → 135.0
            (0.20, 120.0),    # 20% distância → 120.0
        ]

        for distance, expected_stop in test_cases:
            config = TrailingStopConfig(
                activation_threshold_r=1.5,
                stop_distance_pct=distance
            )
            manager = TrailingStopManager(config)
            state = TrailingStopState()

            state = manager.evaluate(high, entry, state, risk_r=0.10)
            assert state.stop_price == pytest.approx(expected_stop, abs=0.01)

    def test_stop_price_adjusts_with_high(self):
        """Stop price se ajusta conforme high muda."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10
        )
        manager = TrailingStopManager(config)
        state = TrailingStopState()
        entry = 100

        # High 130 → Stop 117
        state = manager.evaluate(130, entry, state, risk_r=0.10)
        stop_1 = state.stop_price

        # High sobe para 150 → Stop 135
        state = manager.evaluate(150, entry, state, risk_r=0.10)
        stop_2 = state.stop_price

        assert stop_1 == pytest.approx(117, abs=0.01)
        assert stop_2 == pytest.approx(135, abs=0.01)
        assert stop_2 > stop_1


class TestTrailingStopTrigger:
    """Testes de acionamento do TSL."""

    def test_tsl_triggered_when_crosses_below_stop(self):
        """TSL aciona quando preço cai abaixo do stop."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10
        )
        manager = TrailingStopManager(config)
        state = TrailingStopState()
        entry = 100

        # Ativar: 130 → Stop: 117
        state = manager.evaluate(130, entry, state, risk_r=0.10)
        assert not manager.has_triggered(130, state)

        # Cair para 117 → Triga
        state = manager.evaluate(117, entry, state, risk_r=0.10)
        assert manager.has_triggered(117, state)

    def test_tsl_not_triggered_above_stop(self):
        """TSL não aciona acima do stop."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10
        )
        manager = TrailingStopManager(config)
        state = TrailingStopState()
        entry = 100

        # Ativar: 130 → Stop: 117
        state = manager.evaluate(130, entry, state, risk_r=0.10)

        # Preço em 118 (acima do stop) → Não triga
        state = manager.evaluate(118, entry, state, risk_r=0.10)
        assert not manager.has_triggered(118, state)

    def test_tsl_triggered_exact_stop_price(self):
        """TSL aciona no preço exato do stop."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10
        )
        manager = TrailingStopManager(config)
        state = TrailingStopState()
        entry = 100

        state = manager.evaluate(130, entry, state, risk_r=0.10)
        stop_price = state.stop_price

        # Preço cai exatamente ao stop
        state = manager.evaluate(stop_price, entry, state, risk_r=0.10)
        assert manager.has_triggered(stop_price, state)


class TestTrailingStopDeactivation:
    """Testes de desativação do TSL."""

    def test_tsl_deactivates_on_loss(self):
        """TSL desativa se lucro < 0."""
        config = TrailingStopConfig(activation_threshold_r=1.5)
        manager = TrailingStopManager(config)
        state = TrailingStopState()
        entry = 100

        # Ativar: lucro +15%
        state = manager.evaluate(115, entry, state, risk_r=0.10)
        assert state.active is True

        # Voltar a perda: -1%
        state = manager.evaluate(99, entry, state, risk_r=0.10)
        assert state.active is False
        assert state.deactivated_at is not None

    def test_tsl_deactivation_exact_zero(self):
        """TSL desativa em break-even."""
        config = TrailingStopConfig(activation_threshold_r=1.5)
        manager = TrailingStopManager(config)
        state = TrailingStopState()
        entry = 100

        state = manager.evaluate(115, entry, state, risk_r=0.10)
        assert state.active is True

        # Voltar ao entry price (lucro = 0)
        state = manager.evaluate(100, entry, state, risk_r=0.10)
        assert state.active is False

    def test_tsl_reactivation_after_deactivation(self):
        """TSL pode reativar após desativação."""
        config = TrailingStopConfig(activation_threshold_r=1.5)
        manager = TrailingStopManager(config)
        state = TrailingStopState()
        entry = 100

        # 1. Ativar
        state = manager.evaluate(115, entry, state, risk_r=0.10)
        assert state.active is True
        high_1 = state.high_price

        # 2. Desativar
        state = manager.evaluate(99, entry, state, risk_r=0.10)
        assert state.active is False

        # 3. Reativar
        state = manager.evaluate(116, entry, state, risk_r=0.10)
        assert state.active is True
        assert state.high_price == 116  # Reset do high


class TestHelperFunctions:
    """Testes de funções auxiliares."""

    def test_calculate_profit_pct(self):
        """Calcula lucro percentual corretamente."""
        assert TrailingStopManager._calculate_profit_pct(110, 100) == pytest.approx(0.10)
        assert TrailingStopManager._calculate_profit_pct(100, 100) == 0.0
        assert TrailingStopManager._calculate_profit_pct(90, 100) == pytest.approx(-0.10)

    def test_normalize_to_r(self):
        """Normaliza para R units corretamente."""
        # profit 15%, risk 10% → 1.5R
        assert TrailingStopManager._normalize_to_r(0.15, 0.10) == pytest.approx(1.5)
        # profit 30%, risk 10% → 3R
        assert TrailingStopManager._normalize_to_r(0.30, 0.10) == pytest.approx(3.0)
        # profit 5%, risk 10% → 0.5R
        assert TrailingStopManager._normalize_to_r(0.05, 0.10) == pytest.approx(0.5)

    def test_calculate_stop_price(self):
        """Calcula stop price corretamente."""
        assert TrailingStopManager._calculate_stop_price(130, 0.10) == pytest.approx(117)
        assert TrailingStopManager._calculate_stop_price(150, 0.10) == pytest.approx(135)
        assert TrailingStopManager._calculate_stop_price(100, 0.05) == pytest.approx(95)


class TestEdgeCases:
    """Testes de casos extremos."""

    def test_zero_entry_price(self):
        """Previne divisão por zero."""
        config = TrailingStopConfig()
        manager = TrailingStopManager(config)
        state = TrailingStopState()

        result = manager.evaluate(100, 0, state, risk_r=0.10)
        assert result.active is False

    def test_disabled_tsl(self):
        """TSL desabilitado via config."""
        config = TrailingStopConfig(enabled=False)
        manager = TrailingStopManager(config)
        state = TrailingStopState()

        state = manager.evaluate(115, 100, state, risk_r=0.10)
        assert state.active is False

    def test_very_high_activation_threshold(self):
        """Threshold muito alto (5R) requer muito lucro."""
        config = TrailingStopConfig(activation_threshold_r=5.0)
        manager = TrailingStopManager(config)
        state = TrailingStopState()

        # 50% lucro = 5R com risk 10% → Ativa
        state = manager.evaluate(150, 100, state, risk_r=0.10)
        assert state.active is True

        # 30% lucro = 3R → Não ativa
        state = TrailingStopState()
        state = manager.evaluate(130, 100, state, risk_r=0.10)
        assert state.active is False


class TestFactory:
    """Testes de factory functions."""

    def test_create_tsl_manager_default(self):
        """Factory cria manager com defaults."""
        manager = create_tsl_manager()
        assert manager.config.enabled is True
        assert manager.config.activation_threshold_r == 1.5
        assert manager.config.stop_distance_pct == 0.10

    def test_create_tsl_manager_disabled(self):
        """Factory pode criar manager desabilitado."""
        manager = create_tsl_manager(enabled=False)
        assert manager.config.enabled is False

    def test_init_tsl_state(self):
        """Factory inicializa state vazio."""
        state = init_tsl_state()
        assert state.active is False
        assert state.high_price == 0.0
        assert state.stop_price == 0.0
        assert state.activated_at is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
