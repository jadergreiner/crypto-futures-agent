import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.model2.repository import Model2ThesisRepository
from core.model2.scanner import DetectionResult, M2_002_RULE_ID, M2_002_THESIS_TYPE
from scripts.model2.live_execute import run_live_execute
from scripts.model2.live_reconcile import run_live_reconcile
from scripts.model2.migrate import run_up


def _build_detection_result(symbol: str = "BTCUSDT", rejection_ts: int = 1_700_000_000_000) -> DetectionResult:
    metadata = {
        "rule_id": M2_002_RULE_ID,
        "rule_version": "1.0.0",
        "technical_zone": {
            "source": "order_block",
            "zone_id": 7,
            "timestamp": 1_699_999_999_000,
            "zone_low": 100.0,
            "zone_high": 110.0,
            "status": "FRESH",
        },
        "rejection_candle": {
            "timestamp": rejection_ts,
            "open": 100.0,
            "high": 111.0,
            "low": 97.0,
            "close": 98.0,
        },
        "context": {"market_structure": "range", "is_non_bullish_context": True},
        "parameters": {
            "requires_zone_intersection": True,
            "requires_visible_rejection": True,
            "requires_trigger_break": True,
        },
    }
    return DetectionResult(
        detected=True,
        symbol=symbol,
        timeframe="H4",
        side="SHORT",
        thesis_type=M2_002_THESIS_TYPE,
        zone_low=100.0,
        zone_high=110.0,
        trigger_price=97.0,
        invalidation_price=110.0,
        metadata=metadata,
        rule_id=M2_002_RULE_ID,
    )


def _prepare_model2_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "db" / "modelo2.db"
    output_dir = tmp_path / "results" / "model2" / "runtime"
    run_up(db_path=db_path, output_dir=output_dir)
    return db_path


def _create_consumed_signal(db_path: Path, symbol: str = "BTCUSDT") -> tuple[Model2ThesisRepository, int]:
    repository = Model2ThesisRepository(str(db_path))
    base_now_ms = int(datetime.now(timezone.utc).timestamp() * 1000) - 60_000
    detection = _build_detection_result(symbol=symbol, rejection_ts=base_now_ms - 10_000)
    created = repository.create_initial_thesis(detection, now_ms=base_now_ms)
    repository.transition_to_monitoring(opportunity_id=created.opportunity_id, now_ms=base_now_ms + 10_000)
    repository.transition_to_validated(opportunity_id=created.opportunity_id, now_ms=base_now_ms + 20_000)
    signal = repository.create_standard_signal_from_validated(
        opportunity_id=created.opportunity_id,
        now_ms=base_now_ms + 30_000,
    )
    assert signal.signal_id is not None
    repository.consume_created_signal_for_order_layer(
        signal_id=int(signal.signal_id),
        now_ms=base_now_ms + 40_000,
    )
    return repository, int(signal.signal_id)


class FakeExchange:
    def __init__(self, *, available_balance: float = 100.0, protection_works: bool = True) -> None:
        self.available_balance = available_balance
        self.protection_works = protection_works
        self.market_calls = 0
        self.protection_calls = 0
        self.close_calls = 0
        self.positions: dict[str, dict] = {}
        self.protection: dict[str, dict] = {}

    def get_available_balance(self) -> float | None:
        return self.available_balance

    def get_open_position(self, symbol: str):
        return self.positions.get(symbol)

    def calculate_entry_quantity(self, symbol: str, entry_price: float, margin_usd: float, leverage: int) -> float:
        return round((margin_usd * leverage) / entry_price, 6)

    def place_market_entry(self, *, symbol: str, signal_side: str, quantity: float, client_order_id: str):
        self.market_calls += 1
        entry_price = 97.0
        self.positions[symbol] = {
            "symbol": symbol,
            "direction": signal_side,
            "position_size_qty": quantity,
            "entry_price": entry_price,
            "mark_price": entry_price,
        }
        return {
            "orderId": f"entry-{symbol}",
            "clientOrderId": client_order_id,
            "avgPrice": str(entry_price),
            "executedQty": str(quantity),
        }

    def get_protection_state(self, *, symbol: str, signal_side: str):
        current = self.protection.get(symbol, {})
        return {
            "has_sl": bool(current.get("sl")),
            "has_tp": bool(current.get("tp")),
            "sl_order_id": current.get("sl"),
            "tp_order_id": current.get("tp"),
        }

    def place_protective_order(self, *, symbol: str, signal_side: str, trigger_price: float, order_type: str):
        self.protection_calls += 1
        if not self.protection_works:
            raise RuntimeError("protection failed")
        current = self.protection.setdefault(symbol, {})
        if order_type == "STOP_MARKET":
            current["sl"] = f"sl-{symbol}"
            return {"algoId": current["sl"]}
        current["tp"] = f"tp-{symbol}"
        return {"algoId": current["tp"]}

    @staticmethod
    def extract_order_identifier(order: dict) -> str | None:
        return str(order.get("orderId") or order.get("algoId") or "")

    @staticmethod
    def is_existing_protection_error(error: Exception) -> bool:
        return False

    def close_position_market(self, *, symbol: str, signal_side: str, quantity: float):
        self.close_calls += 1
        self.positions.pop(symbol, None)
        return {"orderId": f"close-{symbol}", "executedQty": str(quantity)}


def test_run_live_execute_shadow_creates_ready_candidate_without_real_order(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _, signal_id = _create_consumed_signal(db_path)

    summary = run_live_execute(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=tmp_path / "results",
        execution_mode="shadow",
        live_symbols=(),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
    )

    assert summary["status"] == "ok"
    assert summary["staged"][0]["technical_signal_id"] == signal_id
    assert summary["staged"][0]["status"] == "READY"
    assert summary["processed_ready"][0]["reason"] == "shadow_mode_no_order_sent"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT execution_mode, status FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()
    assert row == ("shadow", "READY")


def test_run_live_execute_live_happy_path_transitions_to_protected(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _, signal_id = _create_consumed_signal(db_path)
    exchange = FakeExchange(available_balance=100.0, protection_works=True)

    summary = run_live_execute(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=tmp_path / "results",
        execution_mode="live",
        live_symbols=(),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        exchange=exchange,
    )

    assert summary["status"] == "ok"
    assert exchange.market_calls == 1
    assert exchange.protection_calls == 2
    assert summary["processed_ready"][0]["status"] == "PROTECTED"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT status, exchange_order_id, stop_order_id, take_profit_order_id, filled_qty, filled_price
            FROM signal_executions
            WHERE technical_signal_id = ?
            """,
            (signal_id,),
        ).fetchone()
        events = conn.execute(
            "SELECT COUNT(*) FROM signal_execution_events WHERE signal_execution_id = (SELECT id FROM signal_executions WHERE technical_signal_id = ?)",
            (signal_id,),
        ).fetchone()[0]

    assert row is not None
    assert row[0] == "PROTECTED"
    assert row[1] == "entry-BTCUSDT"
    assert row[2] == "sl-BTCUSDT"
    assert row[3] == "tp-BTCUSDT"
    assert float(row[4]) > 0
    assert float(row[5]) == 97.0
    assert events == 4


def test_run_live_execute_is_idempotent_for_same_consumed_signal(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _, signal_id = _create_consumed_signal(db_path)
    exchange = FakeExchange(available_balance=100.0, protection_works=True)

    first_summary = run_live_execute(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=tmp_path / "results",
        execution_mode="live",
        live_symbols=(),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        exchange=exchange,
    )
    second_summary = run_live_execute(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=tmp_path / "results",
        execution_mode="live",
        live_symbols=(),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        exchange=exchange,
    )

    assert first_summary["processed_ready"][0]["status"] == "PROTECTED"
    assert second_summary["staged"][0]["technical_signal_id"] == signal_id
    assert second_summary["staged"][0]["reason"] == "already_exists"
    assert second_summary["processed_ready"] == []
    assert exchange.market_calls == 1

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()
    assert row == (1,)


def test_run_live_execute_blocks_signal_outside_live_gates_without_order_call(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _, signal_id = _create_consumed_signal(db_path)
    exchange = FakeExchange(available_balance=100.0)

    summary = run_live_execute(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=tmp_path / "results",
        execution_mode="live",
        live_symbols=("ETHUSDT",),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        exchange=exchange,
    )

    assert summary["staged"][0]["status"] == "BLOCKED"
    assert summary["staged"][0]["reason"] == "symbol_not_enabled"
    assert exchange.market_calls == 0
    assert summary["processed_ready"] == []

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, gate_reason FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()
    assert row == ("BLOCKED", "symbol_not_enabled")


def test_run_live_execute_protection_failure_triggers_emergency_close(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _, signal_id = _create_consumed_signal(db_path)
    exchange = FakeExchange(available_balance=100.0, protection_works=False)

    summary = run_live_execute(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=tmp_path / "results",
        execution_mode="live",
        live_symbols=(),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        exchange=exchange,
    )

    assert summary["status"] == "ok"
    assert summary["processed_ready"][0]["status"] == "FAILED"
    assert summary["processed_ready"][0]["reason"] == "protection_not_armed"
    assert exchange.market_calls == 1
    assert exchange.close_calls == 1
    assert exchange.get_open_position("BTCUSDT") is None

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT status, failure_reason, stop_order_id, take_profit_order_id
            FROM signal_executions
            WHERE technical_signal_id = ?
            """,
            (signal_id,),
        ).fetchone()
    assert row == ("FAILED", "protection_not_armed", None, None)


def test_live_reconcile_restores_protection_and_detects_manual_exit(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    repository, signal_id = _create_consumed_signal(db_path)
    exchange = FakeExchange(available_balance=100.0, protection_works=True)

    execute_summary = run_live_execute(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=tmp_path / "results",
        execution_mode="live",
        live_symbols=(),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        exchange=exchange,
    )
    assert execute_summary["processed_ready"][0]["status"] == "PROTECTED"

    exchange.protection["BTCUSDT"] = {}
    reconcile_summary = run_live_reconcile(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=tmp_path / "results",
        execution_mode="live",
        live_symbols=(),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        exchange=exchange,
    )
    assert reconcile_summary["reconciled"][0]["reason"] == "protection_armed"

    exchange.positions.pop("BTCUSDT", None)
    second_reconcile = run_live_reconcile(
        model2_db_path=db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=tmp_path / "results",
        execution_mode="live",
        live_symbols=(),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        exchange=exchange,
    )
    assert second_reconcile["reconciled"][0]["status"] == "EXITED"

    execution = repository.list_signal_executions(limit=10)[0]
    assert int(execution["technical_signal_id"]) == signal_id
    assert execution["status"] == "EXITED"
