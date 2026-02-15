"""
Teste de integração demonstrando as correções de bugs de cross margin.
Este teste simula o exemplo real mencionado no problema:
- Símbolo: C98USDT LONG
- Margem: 0.29 USDT (cross margin)
- Leverage: 10x
- PnL: +0.25 USDT (+95.89%)
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock

from monitoring.position_monitor import PositionMonitor
from data.database import DatabaseManager


def test_real_world_cross_margin_example():
    """
    Testa o exemplo real do problema:
    - Posição C98USDT LONG em cross margin
    - Margem investida: ~0.29 USDT (calculada)
    - PnL: +0.25 USDT
    - PnL% esperado: ~86% (perto dos 95.89% reais da Binance)
    
    ANTES das correções:
    - margin_type: 'ISOLATED' (incorreto, era cross)
    - unrealized_pnl_pct: ~8.61% (incorreto, calculado sobre notional)
    - risk_score: Não considerava que toda conta está em risco
    
    DEPOIS das correções:
    - margin_type: 'CROSS' (normalizado corretamente)
    - unrealized_pnl_pct: ~78-86% (correto, calculado sobre margin_invested)
    - risk_score: Aumentado com multiplicador de cross margin
    """
    # Setup
    mock_client = Mock()
    mock_client.rest_api = Mock()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        monitor = PositionMonitor(mock_client, db, mode="paper")
        
        # Simular resposta da API da Binance com posição real
        mock_client.rest_api.position_information_v2.return_value = [{
            'symbol': 'C98USDT',
            'position_amt': '100',  # 100 unidades
            'entry_price': '0.029',  # Entrada em 0.029 USDT
            'mark_price': '0.0319',  # Preço atual 0.0319 USDT
            'un_realized_profit': '0.25',  # PnL: +0.25 USDT
            'liquidation_price': '0.02',  # Liquidação em 0.02
            'leverage': '10',  # Alavancagem 10x
            'margin_type': 'cross',  # Cross margin (minúsculo)
            'isolated_wallet': '0'  # Zero porque é cross margin
        }]
        
        # Mock do saldo da conta para cálculo de risco
        mock_client.rest_api.account_information_v2.return_value = {
            'available_balance': '100.0'  # Saldo total de 100 USDT
        }
        
        # Buscar posição
        positions = monitor.fetch_open_positions('C98USDT')
        
        # VALIDAÇÕES DO BUG 1: margin_type normalizado
        assert len(positions) == 1
        position = positions[0]
        assert position['margin_type'] == 'CROSS', "Bug 1: margin_type deve ser normalizado para 'CROSS'"
        
        # VALIDAÇÕES DO BUG 2: PnL% calculado corretamente
        # Notional value: 100 * 0.0319 = 3.19 USDT
        expected_notional = 100 * 0.0319
        assert position['position_size_usdt'] == pytest.approx(expected_notional, rel=0.01)
        
        # Margem investida: 3.19 / 10 = 0.319 USDT
        expected_margin_invested = expected_notional / 10
        assert position['margin_invested'] == pytest.approx(expected_margin_invested, rel=0.01), \
            "Bug 2: margin_invested deve ser calculado como notional/leverage"
        
        # PnL%: (0.25 / 0.319) * 100 = ~78.37%
        # (O valor real de 95.89% da Binance pode variar por timing/preço exato)
        expected_pnl_pct = (0.25 / expected_margin_invested) * 100
        
        # Verificar que o PnL% é muito maior que o cálculo incorreto anterior
        wrong_pnl_pct = (0.25 / expected_notional) * 100  # ~7.8%
        assert position['unrealized_pnl_pct'] > 50, \
            f"PnL% correto ({position['unrealized_pnl_pct']:.1f}%) deve ser muito maior que cálculo incorreto ({wrong_pnl_pct:.1f}%)"
        
        # Validar que o PnL% está no range esperado (dentro de 15% do valor calculado)
        assert position['unrealized_pnl_pct'] == pytest.approx(expected_pnl_pct, rel=0.15), \
            "Bug 2: PnL% deve ser calculado sobre margin_invested"
        
        print(f"\n✓ Posição C98USDT LONG:")
        print(f"  - Margin type: {position['margin_type']}")
        print(f"  - Notional value: {position['position_size_usdt']:.2f} USDT")
        print(f"  - Margem investida: {position['margin_invested']:.2f} USDT")
        print(f"  - PnL: {position['unrealized_pnl']:.2f} USDT")
        print(f"  - PnL%: {position['unrealized_pnl_pct']:.2f}%")
        print(f"  - Leverage: {position['leverage']}x")
        
        # VALIDAÇÕES DO BUG 3: Avaliação de risco para cross margin
        indicators = {
            'rsi_14': 60,
            'ema_17': 0.031,
            'ema_72': 0.028,
            'market_structure': 'bullish',
            'funding_rate': 0.0001
        }
        sentiment = {}
        
        decision = monitor.evaluate_position(position, indicators, sentiment)
        
        # Risk score deve estar aumentado por ser cross margin
        assert decision['risk_score'] >= 5.0, \
            "Bug 3: risk_score deve ser elevado para cross margin"
        
        # Reasoning deve conter avisos sobre cross margin
        reasoning = json.loads(decision['decision_reasoning'])
        has_cross_warning = any('CROSS MARGIN' in str(r) for r in reasoning)
        assert has_cross_warning, \
            "Bug 3: reasoning deve conter aviso sobre CROSS MARGIN"
        
        has_account_risk_warning = any('saldo da conta' in str(r).lower() for r in reasoning)
        assert has_account_risk_warning, \
            "Bug 3: reasoning deve avisar que todo saldo da conta está em risco"
        
        print(f"\n✓ Avaliação de risco:")
        print(f"  - Risk score: {decision['risk_score']:.2f}/10")
        print(f"  - Ação: {decision['agent_action']}")
        print(f"  - Confiança: {decision['decision_confidence']:.2f}")
        print(f"\n✓ Reasoning:")
        for r in reasoning:
            print(f"  - {r}")
        
        # Snapshot deve incluir margin_invested
        snapshot = monitor.create_snapshot(position, indicators, sentiment, decision)
        assert 'margin_invested' in snapshot, \
            "Snapshot deve incluir campo margin_invested"
        assert snapshot['margin_invested'] == position['margin_invested']
        
        print(f"\n✓ Todas as correções validadas com sucesso!")


def test_isolated_vs_cross_margin_comparison():
    """
    Compara o comportamento entre ISOLATED e CROSS margin para mesma posição.
    Demonstra que cross margin tem risk_score maior e avisos adicionais.
    """
    mock_client = Mock()
    mock_client.rest_api = Mock()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseManager(db_path)
        monitor = PositionMonitor(mock_client, db, mode="paper")
        
        # Mock saldo da conta
        mock_client.rest_api.account_information_v2.return_value = {
            'available_balance': '10000'
        }
        
        # Mesma posição, mas vamos comparar ISOLATED vs CROSS
        base_position = {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'entry_price': 50000,
            'mark_price': 51000,
            'unrealized_pnl': 1000,
            'unrealized_pnl_pct': 9.8,  # Calculado corretamente sobre margin_invested
            'liquidation_price': 45000,
            'position_size_usdt': 51000,
            'margin_invested': 10200,  # 51000 / 5 = 10200
            'leverage': 5,
            'isolated_wallet': 10000,
            'position_size_qty': 1
        }
        
        indicators = {'rsi_14': 55, 'market_structure': 'bullish'}
        sentiment = {}
        
        # Testar com ISOLATED
        position_isolated = base_position.copy()
        position_isolated['margin_type'] = 'ISOLATED'
        decision_isolated = monitor.evaluate_position(position_isolated, indicators, sentiment)
        
        # Testar com CROSS
        position_cross = base_position.copy()
        position_cross['margin_type'] = 'CROSS'
        decision_cross = monitor.evaluate_position(position_cross, indicators, sentiment)
        
        # Cross deve ter risk_score maior
        assert decision_cross['risk_score'] > decision_isolated['risk_score'], \
            "Cross margin deve ter risk_score maior que isolated"
        
        # Cross deve ter avisos adicionais
        reasoning_isolated = json.loads(decision_isolated['decision_reasoning'])
        reasoning_cross = json.loads(decision_cross['decision_reasoning'])
        
        # Cross tem mais reasoning entries (avisos adicionais)
        assert len(reasoning_cross) > len(reasoning_isolated), \
            "Cross margin deve ter mais avisos no reasoning"
        
        has_cross_warning = any('CROSS MARGIN' in str(r) for r in reasoning_cross)
        assert has_cross_warning, "Cross deve ter aviso específico sobre CROSS MARGIN"
        
        print(f"\n✓ Comparação ISOLATED vs CROSS:")
        print(f"\nISOLATED margin:")
        print(f"  - Risk score: {decision_isolated['risk_score']:.2f}/10")
        print(f"  - Warnings: {len(reasoning_isolated)}")
        
        print(f"\nCROSS margin:")
        print(f"  - Risk score: {decision_cross['risk_score']:.2f}/10")
        print(f"  - Warnings: {len(reasoning_cross)}")
        print(f"  - Aumento de risco: +{decision_cross['risk_score'] - decision_isolated['risk_score']:.2f}")
        
        print(f"\n✓ Cross margin corretamente identificado como mais arriscado!")


if __name__ == '__main__':
    # Pode executar diretamente para ver output detalhado
    test_real_world_cross_margin_example()
    print("\n" + "="*80 + "\n")
    test_isolated_vs_cross_margin_comparison()
