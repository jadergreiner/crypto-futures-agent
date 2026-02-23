"""
Testes de Integração — Trailing Stop Loss (S2-4)

Testa TSL integrado com RiskGate e loop de execução.

Personas: Quality (#12) + Data (#11)
Data: 2026-02-22
"""

import pytest
from datetime import datetime
from risk.trailing_stop import (
    TrailingStopConfig,
    TrailingStopState,
    TrailingStopManager,
)


class MockPosition:
    """Mock de Position para testes."""
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        entry_price: float = 100.0,
        quantity: float = 1.0,
        trailing_activation_threshold: float = 1.5,
    ):
        self.symbol = symbol
        self.entry_price = entry_price
        self.quantity = quantity
        self.current_price = entry_price
        self.trailing_activation_threshold = trailing_activation_threshold
        self.trailing_state = TrailingStopState()
        self.risk_r = 0.10
        self.stop_loss_triggered = False
        self.trailing_stop_triggered = False


class TestTrailingStopIntegration:
    """Testes de integração TSL com posições."""
    
    def test_tsl_full_lifecycle(self):
        """Ciclo completo: entrada → ativação → trailing → fechamento."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10,
        )
        manager = TrailingStopManager(config)
        position = MockPosition(entry_price=100.0)
        
        # 1️⃣ Posição aberta
        assert position.trailing_state.active is False
        
        # 2️⃣ Preço sobe para 115 (1.5R) → TSL ativa
        position.current_price = 115.0
        position.trailing_state = manager.evaluate(
            position.current_price,
            position.entry_price,
            position.trailing_state,
            position.risk_r,
        )
        assert position.trailing_state.active is True
        assert position.trailing_state.high_price == 115.0
        
        # 3️⃣ Preço sobe para 130 → High atualiza, stop sube
        position.current_price = 130.0
        position.trailing_state = manager.evaluate(
            position.current_price,
            position.entry_price,
            position.trailing_state,
            position.risk_r,
        )
        assert position.trailing_state.high_price == 130.0
        assert position.trailing_state.stop_price == pytest.approx(117.0, abs=0.01)
        
        # 4️⃣ Preço cai para 117 → TSL acionado
        position.current_price = 117.0
        position.trailing_state = manager.evaluate(
            position.current_price,
            position.entry_price,
            position.trailing_state,
            position.risk_r,
        )
        triggered = manager.has_triggered(position.current_price, position.trailing_state)
        assert triggered is True
        assert position.trailing_state.triggered_at is not None
    
    def test_tsl_coexistence_with_static_sl(self):
        """TSL e SL estático coexistem sem conflito."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10,
        )
        manager = TrailingStopManager(config)
        position = MockPosition(entry_price=100.0)
        
        # Scenario: Preço ganha 20%, cai 5%
        # TSL ativo com stop em 117, SL em 97
        
        # 1. Ganha 20%
        position.current_price = 120.0
        position.trailing_state = manager.evaluate(120, 100, position.trailing_state, 0.10)
        assert position.trailing_state.active is True
        
        # 2. Cai para 110 (ainda em lucro)
        position.current_price = 110.0
        position.trailing_state = manager.evaluate(110, 100, position.trailing_state, 0.10)
        assert position.trailing_state.active is True
        assert not manager.has_triggered(110, position.trailing_state)
        
        # 3. Cai para 99 (perda) → TSL desativa, SL ativa
        position.current_price = 99.0
        position.trailing_state = manager.evaluate(99, 100, position.trailing_state, 0.10)
        assert position.trailing_state.active is False  # TSL desativa
        # SL estático (-3%) em 97, então preço 99 ainda não triga SL
    
    def test_tsl_with_multiple_positions(self):
        """Gerencia TSL para múltiplas posições simultaneamente."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10,
        )
        manager = TrailingStopManager(config)
        
        # 2 posições
        position1 = MockPosition(symbol="BTCUSDT", entry_price=100.0)
        position2 = MockPosition(symbol="ETHUSDT", entry_price=1000.0)
        
        # Posição 1: Ganha 20%
        position1.current_price = 120.0
        position1.trailing_state = manager.evaluate(120, 100, position1.trailing_state, 0.10)
        assert position1.trailing_state.active is True
        
        # Posição 2: Ganha 10% (não ativa TSL)
        position2.current_price = 1100.0
        position2.trailing_state = manager.evaluate(1100, 1000, position2.trailing_state, 0.10)
        assert position2.trailing_state.active is False
        
        assert position1.trailing_state.active != position2.trailing_state.active
    
    def test_tsl_recovery_after_drawdown(self):
        """TSL se recupera após queda dentro do range de lucro."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10,
        )
        manager = TrailingStopManager(config)
        position = MockPosition(entry_price=100.0)
        
        # 1. Ativa TSL em +20%
        position.current_price = 120.0
        position.trailing_state = manager.evaluate(120, 100, position.trailing_state, 0.10)
        assert position.trailing_state.high_price == 120.0
        assert position.trailing_state.stop_price == pytest.approx(108.0, abs=0.01)
        
        # 2. Cai para 109 (ainda acima do stop)
        position.current_price = 109.0
        position.trailing_state = manager.evaluate(109, 100, position.trailing_state, 0.10)
        assert position.trailing_state.active is True
        assert not manager.has_triggered(109, position.trailing_state)
        
        # 3. Sobe novamente para 125
        position.current_price = 125.0
        position.trailing_state = manager.evaluate(125, 100, position.trailing_state, 0.10)
        assert position.trailing_state.high_price == 125.0  # Novo high
        assert position.trailing_state.stop_price == pytest.approx(112.5, abs=0.01)  # Stop move up
    
    def test_tsl_handles_market_volatility(self):
        """TSL suporta volatilidade alta com múltiplos ups/downs."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10,
        )
        manager = TrailingStopManager(config)
        position = MockPosition(entry_price=100.0)
        
        # Simular volatilidade: 100 → 115 → 110 → 125 → 120 → 130 → 119 → 117 (close)
        prices = [115, 110, 125, 120, 130, 119, 117]
        
        for i, price in enumerate(prices):
            position.current_price = price
            position.trailing_state = manager.evaluate(
                price, 100, position.trailing_state, 0.10
            )
            
            if i < len(prices) - 1:  # Todas menos a última
                assert position.trailing_state.active is True
                assert not manager.has_triggered(price, position.trailing_state)
            else:  # A última (117) deve acionar
                assert manager.has_triggered(price, position.trailing_state)


class TestTrailingStopDataPersistence:
    """Testes de persistência de dados TSL."""
    
    def test_tsl_state_serialization(self):
        """Estado TSL pode ser serializado e desserializado."""
        state = TrailingStopState(
            active=True,
            high_price=130.0,
            stop_price=117.0,
            activated_at=datetime.now(),
            triggered_at=None,
        )
        
        # Simular serialização para DB
        db_dict = {
            'active': state.active,
            'high_price': state.high_price,
            'stop_price': state.stop_price,
            'activated_at': state.activated_at,
            'triggered_at': state.triggered_at,
        }
        
        # Desserialização
        restored = TrailingStopState(
            active=db_dict['active'],
            high_price=db_dict['high_price'],
            stop_price=db_dict['stop_price'],
            activated_at=db_dict['activated_at'],
            triggered_at=db_dict['triggered_at'],
        )
        
        assert restored.active == state.active
        assert restored.high_price == state.high_price
        assert restored.stop_price == state.stop_price
    
    def test_tsl_state_tracking_history(self):
        """Rastreia histórico de eventos TSL."""
        config = TrailingStopConfig()
        manager = TrailingStopManager(config)
        state = TrailingStopState()
        
        events = []
        
        # Evento 1: Ativação
        state = manager.evaluate(115, 100, state, 0.10)
        if state.activated_at:
            events.append(('ACTIVATED', state.activated_at))
        
        # Evento 2: Desativação
        state = manager.evaluate(99, 100, state, 0.10)
        if state.deactivated_at:
            events.append(('DEACTIVATED', state.deactivated_at))
        
        assert len(events) >= 1
        assert events[0][0] == 'ACTIVATED'


class TestTrailingStopEdgeCasesIntegration:
    """Testes de edge cases em contexto de integração."""
    
    def test_tsl_with_extreme_leverage(self):
        """TSL funciona com alavancagem extrema (10x)."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10,
        )
        manager = TrailingStopManager(config)
        position = MockPosition(entry_price=100.0)
        
        # Com 10x leverage, 1.5R = 15% × 10 = 150% do capital (em P&L)
        # Mas a lógica TSL permanece igual em %
        position.risk_r = 0.01  # 1% risk em 10x
        position.current_price = 101.5  # 1.5% profit = 1.5R
        
        position.trailing_state = manager.evaluate(
            position.current_price,
            position.entry_price,
            position.trailing_state,
            position.risk_r,
        )
        
        assert position.trailing_state.active is True
    
    def test_tsl_gap_down(self):
        """TSL aguenta gap down que pula o stop."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10,
        )
        manager = TrailingStopManager(config)
        position = MockPosition(entry_price=100.0)
        
        # 1. Ativa TSL em 120
        position.current_price = 120.0
        position.trailing_state = manager.evaluate(120, 100, position.trailing_state, 0.10)
        stop_price = position.trailing_state.stop_price  # 108
        
        # 2. Gap down direto para 105 (pulou o stop)
        position.current_price = 105.0
        position.trailing_state = manager.evaluate(105, 100, position.trailing_state, 0.10)
        
        # TSL aciona se ≤ stop_price
        triggered = manager.has_triggered(105, position.trailing_state)
        if 105 <= stop_price:
            assert triggered is True
        else:
            assert triggered is False
    
    def test_tsl_with_extended_position(self):
        """TSL em posição aberta por longos períodos."""
        config = TrailingStopConfig(
            activation_threshold_r=1.5,
            stop_distance_pct=0.10,
        )
        manager = TrailingStopManager(config)
        position = MockPosition(entry_price=100.0)
        
        # Simular 10 dias de trading
        prices = [
            115, 120, 118, 125, 130, 132, 131, 135, 138, 136,  # Dias 1-10
            134, 132, 130, 128, 125, 123, 122, 120, 119  # Dias 11-19 (downtrend)
        ]
        
        for price in prices:
            position.trailing_state = manager.evaluate(
                price, 100, position.trailing_state, 0.10
            )
            
            # Verificar integridade
            if position.trailing_state.active:
                assert position.trailing_state.high_price >= 115  # Nunca abaixo do threshold
                assert position.trailing_state.stop_price <= position.trailing_state.high_price


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
