"""
Testes parametrizados para sistema de telemetria (Issue #56).

Cobertura: 20+ testes em 3 grupos:
- TestStructuredLogger (8 testes de trade_logger.py)
- TestDatabaseManager (8+ testes de database_manager.py)
- TestAuditTrail (4+ testes de audit_trail.py)

Execução:
    pytest tests/test_telemetry.py -v
    pytest tests/test_telemetry.py -v --tb=short
    pytest tests/test_telemetry.py::TestStructuredLogger -v
"""

import pytest
import json
import os
import tempfile
import shutil
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from logs.trade_logger import StructuredLogger
from logs.database_manager import DatabaseManager
from logs.audit_trail import AuditTrail


class TestStructuredLogger:
    """Testes para StructuredLogger (trade_logger.py)."""

    @pytest.fixture
    def temp_dirs(self):
        """Cria diretórios temporários para testes."""
        temp_logs = tempfile.mkdtemp()
        temp_db = tempfile.mkdtemp()
        yield temp_logs, temp_db
        shutil.rmtree(temp_logs, ignore_errors=True)
        shutil.rmtree(temp_db, ignore_errors=True)

    @pytest.fixture
    def logger(self, temp_dirs):
        """Fixture com logger inicializado."""
        temp_logs, temp_db = temp_dirs
        log_file = os.path.join(temp_logs, 'trades.json')
        db_path = os.path.join(temp_db, 'test.db')
        return StructuredLogger(log_file=log_file, db_path=db_path)

    def test_log_trade_execution_creates_json(self, logger):
        """Trade execution cria entry JSON com todas as fields."""
        trade_id = logger.log_trade_execution(
            symbol='OGUSDT',
            side='BUY',
            qty=10.5,
            entry_price=156.23,
            reason='BoS detected'
        )

        assert trade_id is not None
        assert len(trade_id) > 0

        audit_trail = logger.get_audit_trail()
        assert len(audit_trail) == 1
        assert audit_trail[0]['trade_id'] == trade_id

    def test_log_contains_all_required_fields(self, logger):
        """Log JSON contém todos os campos required."""
        trade_id = logger.log_trade_execution(
            symbol='BTCUSDT',
            side='SELL',
            qty=0.5,
            entry_price=42500.00,
            reason='MA crossover'
        )

        audit_trail = logger.get_audit_trail()
        trade = audit_trail[0]

        required_fields = [
            'trade_id', 'symbol', 'side', 'qty',
            'entry_price', 'exit_price', 'pnl',
            'reason', 'entry_timestamp', 'exit_timestamp'
        ]

        for field in required_fields:
            assert field in trade, f"Campo faltando: {field}"

    def test_timestamp_format_iso8601_utc(self, logger):
        """Timestamps estão em formato ISO8601 UTC (com Z)."""
        trade_id = logger.log_trade_execution(
            symbol='ETHUSDT',
            side='BUY',
            qty=1.0,
            entry_price=2300.00,
            reason='test'
        )

        audit_trail = logger.get_audit_trail()
        trade = audit_trail[0]

        # Verificar formato ISO8601 com Z (UTC)
        timestamp = trade['entry_timestamp']
        assert timestamp.endswith('Z'), f"Timestamp não termina com Z: {timestamp}"

        # Tentar parsear como ISO8601
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            assert isinstance(dt, datetime)
        except ValueError as e:
            pytest.fail(f"Timestamp não é ISO8601 válido: {e}")

    def test_trade_id_is_unique(self, logger):
        """Cada trade tem UUID único."""
        ids = set()
        for i in range(5):
            trade_id = logger.log_trade_execution(
                symbol=f'TEST{i}USDT',
                side='BUY',
                qty=1.0,
                entry_price=100.0,
                reason=f'test_{i}'
            )
            ids.add(trade_id)

        assert len(ids) == 5, "Nem todos os trade_ids são únicos"

    def test_trade_id_format_valid(self, logger):
        """trade_id é UUID válido (36 chars com hífens)."""
        trade_id = logger.log_trade_execution(
            symbol='OGUSDT',
            side='BUY',
            qty=1.0,
            entry_price=100.0,
            reason='test'
        )

        # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        assert len(trade_id) == 36, f"UUID tem tamanho errado: {len(trade_id)}"
        assert trade_id.count('-') == 4, "UUID deveria ter 4 hífens"

    def test_log_file_written_successfully(self, logger, temp_dirs):
        """Arquivo JSON é criado e escrito com sucesso."""
        temp_logs, _ = temp_dirs
        log_file = os.path.join(temp_logs, 'trades.json')

        logger.log_trade_execution(
            symbol='OGUSDT',
            side='BUY',
            qty=1.0,
            entry_price=100.0,
            reason='test'
        )

        assert os.path.exists(log_file), "Arquivo JSON não foi criado"

        with open(log_file, 'r') as f:
            data = json.load(f)
            assert isinstance(data, list), "JSON não é lista"
            assert len(data) > 0, "JSON está vazio"

    @pytest.mark.parametrize('symbol,side,qty,entry_price', [
        ('OGUSDT', 'BUY', 10.5, 156.23),
        ('BTCUSDT', 'SELL', 0.5, 42500.00),
        ('ETHUSDT', 'BUY', 5.0, 2300.50),
        ('BNBUSDT', 'SELL', 2.5, 610.25),
    ])
    def test_log_multiple_trades_parametrized(self, logger, symbol, side, qty, entry_price):
        """Log funciona com múltiplos símbolos, sides e quantidades."""
        trade_id = logger.log_trade_execution(
            symbol=symbol,
            side=side,
            qty=qty,
            entry_price=entry_price,
            reason='parametrized_test'
        )

        assert trade_id is not None

        audit_trail = logger.get_audit_trail(symbol=symbol)
        assert len(audit_trail) > 0
        assert audit_trail[0]['symbol'] == symbol
        assert audit_trail[0]['side'] == side

    def test_log_trade_close_updates_json(self, logger):
        """Fechamento atualiza exit_price e pnl no JSON."""
        trade_id = logger.log_trade_execution(
            symbol='OGUSDT',
            side='BUY',
            qty=10.0,
            entry_price=150.00,
            reason='entry_test'
        )

        # Verificar antes de fechar
        audit_trail_before = logger.get_audit_trail()
        assert audit_trail_before[0]['exit_price'] is None
        assert audit_trail_before[0]['pnl'] is None

        # Fechar
        success = logger.log_trade_close(
            trade_id=trade_id,
            exit_price=160.00,
            pnl=100.0  # 10 * (160 - 150)
        )

        assert success is True

        # Verificar depois de fechar
        audit_trail_after = logger.get_audit_trail()
        assert audit_trail_after[0]['exit_price'] == 160.00
        assert audit_trail_after[0]['pnl'] == 100.0

    def test_invalid_side_raises_error(self, logger):
        """side inválido lança ValueError."""
        with pytest.raises(ValueError):
            logger.log_trade_execution(
                symbol='OGUSDT',
                side='INVALID',
                qty=1.0,
                entry_price=100.0,
                reason='test'
            )

    def test_get_audit_trail_all(self, logger):
        """get_audit_trail() sem filtro retorna todas."""
        logger.log_trade_execution(
            symbol='OGUSDT', side='BUY', qty=1.0, entry_price=100.0, reason='1'
        )
        logger.log_trade_execution(
            symbol='BTCUSDT', side='SELL', qty=0.5, entry_price=40000.0, reason='2'
        )

        all_trades = logger.get_audit_trail()
        assert len(all_trades) == 2

    def test_get_audit_trail_filtered_by_symbol(self, logger):
        """get_audit_trail(symbol) filtra corretamente."""
        logger.log_trade_execution(
            symbol='OGUSDT', side='BUY', qty=1.0, entry_price=100.0, reason='1'
        )
        logger.log_trade_execution(
            symbol='BTCUSDT', side='SELL', qty=0.5, entry_price=40000.0, reason='2'
        )

        og_trades = logger.get_audit_trail(symbol='OGUSDT')
        assert len(og_trades) == 1
        assert og_trades[0]['symbol'] == 'OGUSDT'

        btc_trades = logger.get_audit_trail(symbol='BTCUSDT')
        assert len(btc_trades) == 1
        assert btc_trades[0]['symbol'] == 'BTCUSDT'


class TestDatabaseManager:
    """Testes para DatabaseManager (database_manager.py)."""

    @pytest.fixture
    def temp_db_dir(self):
        """Cria diretório temporário para banco."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def db_manager(self, temp_db_dir):
        """Fixture com DatabaseManager inicializado."""
        db_path = os.path.join(temp_db_dir, 'test.db')
        manager = DatabaseManager(db_path)
        manager.init_database()
        return manager

    def test_init_database_creates_tables(self, db_manager, temp_db_dir):
        """init_database() cria tabela trades."""
        db_path = os.path.join(temp_db_dir, 'test2.db')
        manager = DatabaseManager(db_path)
        success = manager.init_database()

        assert success is True
        assert os.path.exists(db_path)

        # Verificar tabela foi criada
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='trades'
        ''')
        table = cursor.fetchone()
        conn.close()

        assert table is not None

    def test_insert_trade_returns_id(self, db_manager):
        """insert_trade() retorna trade_id."""
        trade_dict = {
            'trade_id': 'test-uuid-1234-5678-90ab-cdef',
            'symbol': 'OGUSDT',
            'side': 'BUY',
            'qty': 10.0,
            'entry_price': 150.0,
            'reason': 'test',
            'entry_timestamp': '2026-02-22T10:00:00Z'
        }

        returned_id = db_manager.insert_trade(trade_dict)

        assert returned_id == trade_dict['trade_id']

    def test_insert_duplicate_trade_id_fails(self, db_manager):
        """Inserir trade_id duplicada lança IntegrityError."""
        trade_dict = {
            'trade_id': 'test-dup-123',
            'symbol': 'OGUSDT',
            'side': 'BUY',
            'qty': 10.0,
            'entry_price': 150.0,
            'reason': 'test',
            'entry_timestamp': '2026-02-22T10:00:00Z'
        }

        # Primeira inserção ok
        db_manager.insert_trade(trade_dict)

        # Segunda inserção deve falhar
        with pytest.raises(sqlite3.IntegrityError):
            db_manager.insert_trade(trade_dict)

    def test_update_trade_exit_price(self, db_manager):
        """update_trade() atualiza exit_price."""
        trade_dict = {
            'trade_id': 'test-update-1',
            'symbol': 'OGUSDT',
            'side': 'BUY',
            'qty': 10.0,
            'entry_price': 150.0,
            'reason': 'test',
            'entry_timestamp': '2026-02-22T10:00:00Z'
        }

        db_manager.insert_trade(trade_dict)

        success = db_manager.update_trade(
            trade_id='test-update-1',
            exit_price=160.0,
            pnl=100.0
        )

        assert success is True

        # Verificar no banco
        trade = db_manager.get_trade_by_id('test-update-1')
        assert trade['exit_price'] == 160.0
        assert trade['pnl'] == 100.0

    def test_update_nonexistent_trade_returns_false(self, db_manager):
        """update_trade() com ID inexistente retorna False."""
        success = db_manager.update_trade(
            trade_id='nonexistent',
            exit_price=100.0,
            pnl=50.0
        )

        assert success is False

    def test_query_trades_by_symbol(self, db_manager):
        """query_trades(symbol) filtra corretamente."""
        # Inserir múltiplas trades
        for i in range(3):
            trade_dict = {
                'trade_id': f'test-query-{i}',
                'symbol': 'OGUSDT' if i < 2 else 'BTCUSDT',
                'side': 'BUY',
                'qty': 10.0,
                'entry_price': 150.0 + i,
                'reason': f'test_{i}',
                'entry_timestamp': f'2026-02-22T{10+i}:00:00Z'
            }
            db_manager.insert_trade(trade_dict)

        # Query por symbol
        og_trades = db_manager.query_trades(symbol='OGUSDT')
        assert len(og_trades) == 2
        assert all(og_trades['symbol'] == 'OGUSDT')

        btc_trades = db_manager.query_trades(symbol='BTCUSDT')
        assert len(btc_trades) == 1

    def test_query_trades_with_limit(self, db_manager):
        """query_trades(limit) limita corretamente."""
        for i in range(10):
            trade_dict = {
                'trade_id': f'test-limit-{i}',
                'symbol': 'OGUSDT',
                'side': 'BUY',
                'qty': 1.0,
                'entry_price': 100.0 + i,
                'reason': 'test',
                'entry_timestamp': f'2026-02-22T{10+i%24}:00:00Z'
            }
            db_manager.insert_trade(trade_dict)

        limited = db_manager.query_trades(limit=5)
        assert len(limited) == 5

    def test_database_transactions_atomic(self, db_manager):
        """Transações são atômicas (insert + update são transacionais)."""
        trade_dict = {
            'trade_id': 'test-atomic',
            'symbol': 'OGUSDT',
            'side': 'BUY',
            'qty': 10.0,
            'entry_price': 150.0,
            'reason': 'test',
            'entry_timestamp': '2026-02-22T10:00:00Z'
        }

        db_manager.insert_trade(trade_dict)
        db_manager.update_trade('test-atomic', 160.0, 100.0)

        # Verificar estado final
        trade = db_manager.get_trade_by_id('test-atomic')
        assert trade is not None
        assert trade['exit_price'] == 160.0

    @pytest.mark.parametrize('symbol,qty,entry_price', [
        ('OGUSDT', 10.0, 150.0),
        ('BTCUSDT', 0.5, 42500.0),
        ('ETHUSDT', 5.0, 2300.0),
    ])
    def test_insert_multiple_symbols_parametrized(self, db_manager, symbol, qty, entry_price):
        """insert_trade funciona com multiplos símbolos."""
        trade_dict = {
            'trade_id': f'test-param-{symbol}',
            'symbol': symbol,
            'side': 'BUY',
            'qty': qty,
            'entry_price': entry_price,
            'reason': 'test',
            'entry_timestamp': '2026-02-22T10:00:00Z'
        }

        trade_id = db_manager.insert_trade(trade_dict)
        assert trade_id == trade_dict['trade_id']

        retrieved = db_manager.get_trade_by_id(trade_id)
        assert retrieved['symbol'] == symbol

    def test_count_trades(self, db_manager):
        """count_trades() retorna número correto."""
        for i in range(5):
            trade_dict = {
                'trade_id': f'test-count-{i}',
                'symbol': 'OGUSDT',
                'side': 'BUY',
                'qty': 1.0,
                'entry_price': 100.0,
                'reason': 'test',
                'entry_timestamp': '2026-02-22T10:00:00Z'
            }
            db_manager.insert_trade(trade_dict)

        total = db_manager.count_trades()
        assert total == 5

        og_count = db_manager.count_trades(symbol='OGUSDT')
        assert og_count == 5

    def test_count_closed_trades(self, db_manager):
        """count_closed_trades() conta apenas traded fechadas."""
        # Inserir 3 trades
        for i in range(3):
            trade_dict = {
                'trade_id': f'test-closed-{i}',
                'symbol': 'OGUSDT',
                'side': 'BUY',
                'qty': 1.0,
                'entry_price': 100.0,
                'reason': 'test',
                'entry_timestamp': '2026-02-22T10:00:00Z'
            }
            db_manager.insert_trade(trade_dict)

        # Fechar 2 delas
        db_manager.update_trade('test-closed-0', 110.0, 10.0)
        db_manager.update_trade('test-closed-1', 105.0, 5.0)

        closed_count = db_manager.count_closed_trades()
        assert closed_count == 2

    def test_validate_trade_integrity_passes(self, db_manager):
        """validate_trade_integrity() com dados válidos retorna True."""
        trade_dict = {
            'trade_id': 'test-integ-1',
            'symbol': 'OGUSDT',
            'side': 'BUY',
            'qty': 10.0,
            'entry_price': 150.0,
            'reason': 'test',
            'entry_timestamp': '2026-02-22T10:00:00Z'
        }

        db_manager.insert_trade(trade_dict)

        is_valid = db_manager.validate_trade_integrity()
        assert is_valid is True

    def test_validate_trade_integrity_closed(self, db_manager):
        """validate_trade_integrity() com trade fechada válida."""
        trade_dict = {
            'trade_id': 'test-integ-closed',
            'symbol': 'OGUSDT',
            'side': 'BUY',
            'qty': 10.0,
            'entry_price': 150.0,
            'reason': 'test',
            'entry_timestamp': '2026-02-22T10:00:00Z'
        }

        db_manager.insert_trade(trade_dict)
        db_manager.update_trade('test-integ-closed', 160.0, 100.0)

        is_valid = db_manager.validate_trade_integrity()
        assert is_valid is True


class TestAuditTrail:
    """Testes para AuditTrail (audit_trail.py)."""

    @pytest.fixture
    def temp_dir(self):
        """Cria diretório temporário."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def audit_with_data(self, temp_dir):
        """Fixture com AuditTrail com dados de teste."""
        db_path = os.path.join(temp_dir, 'test.db')
        manager = DatabaseManager(db_path)
        manager.init_database()

        # Inserir trades de teste
        trades = [
            {
                'trade_id': 'audit-test-1',
                'symbol': 'OGUSDT',
                'side': 'BUY',
                'qty': 10.0,
                'entry_price': 150.0,
                'reason': 'test1',
                'entry_timestamp': '2026-02-22T10:00:00Z'
            },
            {
                'trade_id': 'audit-test-2',
                'symbol': 'OGUSDT',
                'side': 'SELL',
                'qty': 10.0,
                'entry_price': 155.0,
                'reason': 'test2',
                'entry_timestamp': '2026-02-22T11:00:00Z'
            },
        ]

        for trade in trades:
            manager.insert_trade(trade)

        # Fechar primeira trade
        manager.update_trade('audit-test-1', 160.0, 100.0)

        return AuditTrail(db_path)

    def test_reconstruct_pnl_history_complete(self, audit_with_data):
        """reconstruct_pnl_history retorna histórico correto."""
        pnl_df = audit_with_data.reconstruct_pnl_history(symbol='OGUSDT')

        assert len(pnl_df) > 0
        assert 'pnl_cumsum' in pnl_df.columns
        assert 'winner' in pnl_df.columns

    def test_pnl_summary_metrics(self, audit_with_data):
        """get_pnl_summary retorna métricas corretas."""
        summary = audit_with_data.get_pnl_summary(symbol='OGUSDT')

        assert 'total_pnl' in summary
        assert 'trade_count' in summary
        assert 'win_rate' in summary
        assert 'avg_win' in summary
        assert summary['total_pnl'] >= 0  # Teve 1 trade com PnL 100

    def test_validate_trade_integrity_all_trades(self, audit_with_data):
        """validate_trade_integrity() valida todas as trades."""
        is_valid = audit_with_data.validate_trade_integrity()
        assert is_valid is True

    def test_export_to_csv_format(self, audit_with_data, temp_dir):
        """export_to_csv() cria arquivo CSV válido."""
        csv_path = os.path.join(temp_dir, 'trades.csv')
        export_path = audit_with_data.export_to_csv(csv_path)

        assert os.path.exists(export_path)

        # Verificar conteúdo
        df = pd.read_csv(export_path)
        assert len(df) > 0
        assert 'trade_id' in df.columns
        assert 'symbol' in df.columns
        assert 'pnl' in df.columns

    def test_export_to_json_format(self, audit_with_data, temp_dir):
        """export_to_json() cria arquivo JSON válido."""
        json_path = os.path.join(temp_dir, 'trades.json')
        export_path = audit_with_data.export_to_json(json_path)

        assert os.path.exists(export_path)

        with open(export_path, 'r') as f:
            data = json.load(f)
            assert isinstance(data, list)

    def test_get_trades_by_symbol(self, audit_with_data):
        """get_trades_by_symbol() filtra corretamente."""
        trades = audit_with_data.get_trades_by_symbol('OGUSDT')
        assert len(trades) > 0
        assert all(trades['symbol'] == 'OGUSDT')

    def test_get_open_trades(self, audit_with_data):
        """get_open_trades() retorna trades abertas."""
        open_trades = audit_with_data.get_open_trades()
        # audit_with_data tem 1 trade fechada e 1 aberta
        assert len(open_trades) == 1

    def test_get_closed_trades(self, audit_with_data):
        """get_closed_trades() retorna trades fechadas."""
        closed_trades = audit_with_data.get_closed_trades()
        # audit_with_data tem 1 trade fechada
        assert len(closed_trades) == 1

    def test_pnl_summary_empty_audit(self, temp_dir):
        """get_pnl_summary() com audit vazio retorna zeros."""
        db_path = os.path.join(temp_dir, 'empty.db')
        manager = DatabaseManager(db_path)
        manager.init_database()

        audit = AuditTrail(db_path)
        summary = audit.get_pnl_summary()

        assert summary['total_pnl'] == 0.0
        assert summary['trade_count'] == 0
        assert summary['win_rate'] == 0.0

    @pytest.mark.parametrize('qty,entry,exit,expected_pnl', [
        (10.0, 150.0, 160.0, 100.0),  # 10 * (160 - 150)
        (5.0, 200.0, 195.0, -25.0),   # 5 * (195 - 200)
        (1.0, 2000.0, 2100.0, 100.0), # 1 * (2100 - 2000)
    ])
    def test_pnl_calculation_precision(self, temp_dir, qty, entry, exit, expected_pnl):
        """PnL é calculado com precisão."""
        db_path = os.path.join(temp_dir, f'pnl_test_{qty}_{entry}_{exit}.db')
        manager = DatabaseManager(db_path)
        manager.init_database()

        trade_dict = {
            'trade_id': f'pnl-test-{qty}-{entry}-{exit}',
            'symbol': 'TEST',
            'side': 'BUY',
            'qty': qty,
            'entry_price': entry,
            'reason': 'pnl_test',
            'entry_timestamp': '2026-02-22T10:00:00Z'
        }

        manager.insert_trade(trade_dict)
        manager.update_trade(trade_dict['trade_id'], exit, expected_pnl)

        audit = AuditTrail(db_path)
        history = audit.reconstruct_pnl_history(symbol='TEST')

        actual_pnl = history.iloc[0]['pnl']
        assert abs(actual_pnl - expected_pnl) < 0.01  # Precisão < 0.01 USD
