"""
Testes de Integração S2-4 — TSL + OrderExecutor

[S2-4 INTEGRAÇÃO] Valida que TrailingStopManager integrado em OrderExecutor
funciona corretamente no loop de execução e persiste estado por símbolo.

Personas: Quality (#12) + Arch (#6)
Data: 2026-02-23
Objetivo: Desbloquear testnet + Issue #65 (SMC Integration Tests)
"""

import pytest
from execution.order_executor import OrderExecutor


class TestTrailingStopOrderExecutorIntegration:
    """
    Testes de integração TSL + OrderExecutor.
    
    [S2-4] Valida que o TrailingStopManager integrado em OrderExecutor
    funciona corretamente com o loop de execução.
    """

    def test_order_executor_has_tsl_manager(self):
        """OrderExecutor deve ter TrailingStopManager inicializado."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # Verificar que TrailingStopManager está presente
        assert hasattr(executor, 'tsl_manager')
        assert hasattr(executor, '_tsl_states')
        assert executor._tsl_states == {}

    def test_order_executor_tsl_evaluation(self):
        """OrderExecutor avalia TSL corretamente via evaluate_trailing_stop()."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # Avaliar TSL em uma posição
        tsl_result = executor.evaluate_trailing_stop(
            symbol="BTCUSDT",
            current_price=120.0,
            entry_price=100.0,
            direction="LONG",
            risk_r=0.10
        )

        # Verificar retorno
        assert tsl_result['symbol'] == "BTCUSDT"
        assert tsl_result['active'] is True
        assert tsl_result['high_price'] == 120.0
        assert tsl_result['triggered'] is False
        assert 'status_msg' in tsl_result

    def test_order_executor_multiple_symbols_independent_tsl(self):
        """OrderExecutor gerencia TSL para múltiplos símbolos independentemente."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # Avaliar 2 símbolos diferentes
        tsl1 = executor.evaluate_trailing_stop("BTCUSDT", 120.0, 100.0, "LONG", 0.10)
        tsl2 = executor.evaluate_trailing_stop("ETHUSDT", 1100.0, 1000.0, "LONG", 0.10)

        assert tsl1['symbol'] == "BTCUSDT"
        assert tsl2['symbol'] == "ETHUSDT"
        assert tsl1['active'] is True
        assert tsl2['active'] is False  # Não atingiu 1.5R threshold

        # Estados devem estar em caches separados
        assert "BTCUSDT" in executor._tsl_states
        assert "ETHUSDT" in executor._tsl_states
        assert executor._tsl_states["BTCUSDT"].active is True
        assert executor._tsl_states["ETHUSDT"].active is False

    def test_order_executor_tsl_cache_persistence(self):
        """Cachê de TSL persiste entre chamadas para o mesmo símbolo."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # Primeira chamada: ativa TSL
        tsl1 = executor.evaluate_trailing_stop("BTCUSDT", 120.0, 100.0, "LONG", 0.10)
        assert tsl1['active'] is True
        high1 = tsl1['high_price']

        # Segunda chamada: preço sobe para 130
        tsl2 = executor.evaluate_trailing_stop("BTCUSDT", 130.0, 100.0, "LONG", 0.10)
        assert tsl2['active'] is True
        assert tsl2['high_price'] == 130.0
        assert tsl2['high_price'] > high1

        # Terceira chamada: preço cai para 125 (ainda acima do stop ~117)
        tsl3 = executor.evaluate_trailing_stop("BTCUSDT", 125.0, 100.0, "LONG", 0.10)
        assert tsl3['active'] is True
        assert tsl3['high_price'] == 130.0  # High não volta
        assert tsl3['triggered'] is False

        # Validar que o estado foi preservado no cache
        assert executor._tsl_states["BTCUSDT"].high_price == 130.0

    def test_order_executor_tsl_activation_threshold(self):
        """TSL ativa apenas quando profit >= 1.5R (padrão)."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # Preço sobe 10% (menos que 1.5R com risk 10%)
        tsl1 = executor.evaluate_trailing_stop("BTCUSDT", 110.0, 100.0, "LONG", 0.10)
        assert tsl1['active'] is False

        # Preço sobe 15% (exatamente 1.5R com risk 10%)
        tsl2 = executor.evaluate_trailing_stop("BTCUSDT", 115.0, 100.0, "LONG", 0.10)
        assert tsl2['active'] is True

    def test_order_executor_tsl_trigger_detection(self):
        """OrderExecutor detecta corretamente quando TSL é acionado."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # Step 1: Ativa TSL em +20% (entry 100, preço 120)
        executor.evaluate_trailing_stop("BTCUSDT", 120.0, 100.0, "LONG", 0.10)
        # Stop deve estar em 120 * 0.9 = 108

        # Step 2: Preço sobe para 130 (novo high)
        executor.evaluate_trailing_stop("BTCUSDT", 130.0, 100.0, "LONG", 0.10)
        # Stop deve estar em 130 * 0.9 = 117

        # Step 3: Preço cai para 117 (no stop)
        tsl_result = executor.evaluate_trailing_stop("BTCUSDT", 117.0, 100.0, "LONG", 0.10)

        # TSL deve estar acionado
        assert tsl_result['triggered'] is True
        assert tsl_result['trigger_timestamp'] is not None

    def test_order_executor_tsl_short_position(self):
        """OrderExecutor funciona corretamente para posições SHORT."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # SHORT: entry em 100, preço cai para 85 (ganhou 15%, 1.5R)
        tsl_result = executor.evaluate_trailing_stop(
            "BTCUSDT",
            current_price=85.0,
            entry_price=100.0,
            direction="SHORT",
            risk_r=0.10
        )

        # TSL deve ativar (agnóstico a direção)
        assert tsl_result['active'] is True
        assert tsl_result['high_price'] == 85.0

    def test_order_executor_tsl_multiple_cycles(self):
        """TSL funciona corretamente em múltiplos ciclos de preço."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # Simular ciclo: 100 → 120 → 110 → 125 → 118
        prices = [120.0, 110.0, 125.0, 118.0]
        expected_actives = [True, True, True, True]
        expected_triggered = [False, False, False, False]

        for price, exp_active, exp_triggered in zip(prices, expected_actives, expected_triggered):
            tsl = executor.evaluate_trailing_stop("BTCUSDT", price, 100.0, "LONG", 0.10)
            assert tsl['active'] == exp_active, f"Price {price}: active mismatch"
            assert tsl['triggered'] == exp_triggered, f"Price {price}: triggered mismatch"

    def test_order_executor_tsl_recovery_in_profit_zone(self):
        """TSL se recupera de queda dentro da zona de lucro."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # 1. Ativa TSL em 120 (high=120, stop=108)
        executor.evaluate_trailing_stop("BTCUSDT", 120.0, 100.0, "LONG", 0.10)

        # 2. Cai para 110 (acima do stop=108)
        tsl_mid = executor.evaluate_trailing_stop("BTCUSDT", 110.0, 100.0, "LONG", 0.10)
        assert tsl_mid['active'] is True
        assert tsl_mid['triggered'] is False

        # 3. Sobe para 135 (novo high, stop sobe para ~121.5)
        tsl_up = executor.evaluate_trailing_stop("BTCUSDT", 135.0, 100.0, "LONG", 0.10)
        assert tsl_up['high_price'] == 135.0
        assert tsl_up['stop_price'] > 120.0

    def test_order_executor_tsl_state_deactivation_on_loss(self):
        """TSL se desativa quando posição volta a perda."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # 1. Ativa TSL em 120
        executor.evaluate_trailing_stop("BTCUSDT", 120.0, 100.0, "LONG", 0.10)

        # 2. Preço cai para 99 (prejuízo)
        tsl_loss = executor.evaluate_trailing_stop("BTCUSDT", 99.0, 100.0, "LONG", 0.10)

        # TSL deve estar inativo após volta a prejuízo
        assert tsl_loss['active'] is False

    def test_order_executor_tsl_with_different_risk_r(self):
        """TSL funciona com diferentes valores de risk_r."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # Com risk_r = 0.05 (5%), 1.5R = 7.5% profit
        tsl_high_risk = executor.evaluate_trailing_stop(
            "BTCUSDT",
            current_price=107.0,  # 7% profit
            entry_price=100.0,
            direction="LONG",
            risk_r=0.05
        )
        assert tsl_high_risk['active'] is False

        # Com risk_r = 0.05, 7.5% profit = 1.5R
        tsl_high_risk_exact = executor.evaluate_trailing_stop(
            "BTCUSDT",
            current_price=107.5,  # 7.5% profit = 1.5R
            entry_price=100.0,
            direction="LONG",
            risk_r=0.05
        )
        assert tsl_high_risk_exact['active'] is True


class TestTrailingStopOrderExecutorNoRegression:
    """Garantir que a integração S2-4 não causa regressão em testes Sprint 1."""

    def test_existing_order_executor_functionality_preserved(self):
        """OrderExecutor mantém funcionalidades existentes após S2-4."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # Verificar atributos base
        assert hasattr(executor, '_client')
        assert hasattr(executor, '_db')
        assert hasattr(executor, '_mode')
        assert hasattr(executor, 'config')
        assert hasattr(executor, 'authorized_symbols')

        # Verificar métodos base
        assert hasattr(executor, 'execute_decision')
        assert hasattr(executor, '_check_safety_guards')
        assert callable(executor.execute_decision)
        assert callable(executor._check_safety_guards)

    def test_tsl_manager_does_not_break_existing_methods(self):
        """TrailingStopManager não interfere com métodos existentes."""
        class MockClient:
            pass

        class MockDB:
            pass

        executor = OrderExecutor(MockClient(), MockDB(), mode="paper")

        # Chamar método existente deve funcionar sem erro
        try:
            guards_passed, reason = executor._check_safety_guards(
                symbol="INVALID",
                action="HOLD",
                confidence=0.5
            )
            # Deve falhar na validação de ação (esperado)
            assert guards_passed is False
        except Exception as e:
            pytest.fail(f"_check_safety_guards quebrou: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
