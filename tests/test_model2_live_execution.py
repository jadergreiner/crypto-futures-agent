import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from core.model2.model_decision import (
    ACTION_CLOSE,
    ACTION_HOLD,
    ACTION_OPEN_LONG,
    ACTION_REDUCE,
    ModelDecision,
)
from core.model2.model_inference_service import InferenceServiceResult
from core.model2.model_state_builder import M2_020_3_SCHEMA_VERSION, StateBuilderResult
from core.model2.repository import Model2ThesisRepository
from core.model2.scanner import DetectionResult, M2_002_RULE_ID, M2_002_THESIS_TYPE
from risk.circuit_breaker import CircuitBreaker
from risk.risk_gate import RiskGate, RiskGateStatus
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


class SequencedBalanceExchange(FakeExchange):
    def __init__(self, balances: list[float], *, protection_works: bool = True) -> None:
        super().__init__(available_balance=float(balances[0]), protection_works=protection_works)
        self._balances = [float(value) for value in balances]
        self._cursor = 0

    def get_available_balance(self) -> float | None:
        index = min(self._cursor, len(self._balances) - 1)
        value = self._balances[index]
        self._cursor += 1
        return value


def _forced_inference_result(model_input, *, action: str, reason: str) -> InferenceServiceResult:
    if action == ACTION_OPEN_LONG:
        sl_target = 95.0
        tp_target = 110.0
        size_fraction = 0.4
    else:
        sl_target = None
        tp_target = None
        size_fraction = 0.0

    return InferenceServiceResult(
        accepted=True,
        decision=ModelDecision(
            action=action,
            confidence=0.88 if action != ACTION_HOLD else 0.62,
            size_fraction=size_fraction,
            sl_target=sl_target,
            tp_target=tp_target,
            reason_code=reason,
            decision_timestamp=int(model_input.decision_timestamp),
            symbol=str(model_input.symbol),
            model_version=str(model_input.model_version),
            metadata={"origin": "test"},
        ),
        model_version=str(model_input.model_version),
        inference_latency_ms=1,
        reason=reason,
        rule_id="TEST-M2-020.4",
        details={"origin": "test"},
    )


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
    assert summary["staged"][0]["decision_id"] > 0
    assert summary["staged"][0]["model_version"] == "m2-inference-v1"
    assert summary["staged"][0]["inference_latency_ms"] >= 0
    assert summary["staged"][0]["status"] == "READY"
    assert summary["processed_ready"][0]["reason"] == "shadow_mode_no_order_sent"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT execution_mode, status, decision_id FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()
        decision_row = conn.execute(
            "SELECT model_version, inference_latency_ms FROM model_decisions WHERE id = ?",
            (int(row[2]),),
        ).fetchone()

    assert row is not None
    assert row[0] == "shadow"
    assert row[1] == "READY"
    assert int(row[2]) > 0
    assert decision_row is not None
    assert decision_row[0] == "m2-inference-v1"
    assert int(decision_row[1]) >= 0


def test_run_live_execute_persists_complete_inference_state_in_model_decisions(tmp_path: Path) -> None:
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

    decision_id = int(summary["staged"][0]["decision_id"])
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT input_json FROM model_decisions WHERE id = ?",
            (decision_id,),
        ).fetchone()

    assert row is not None
    input_payload = json.loads(row[0])
    assert input_payload["market_state"]["signal_side"] == "SHORT"
    assert input_payload["market_state"]["market_context"]["market_regime"] == "UNKNOWN"
    assert input_payload["position_state"]["has_open_position"] is False
    assert input_payload["risk_state"]["max_daily_entries"] == 10
    assert input_payload["state_builder"]["success"] is True
    assert input_payload["state_schema_version"] == M2_020_3_SCHEMA_VERSION

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()
    assert row == ("READY",)


def test_run_live_execute_uses_model_action_as_execution_origin(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _, signal_id = _create_consumed_signal(db_path)

    def _force_open_long(self, model_input):
        return _forced_inference_result(
            model_input,
            action=ACTION_OPEN_LONG,
            reason="force_open_long",
        )

    monkeypatch.setattr(
        "core.model2.live_service.ModelInferenceService.infer",
        _force_open_long,
    )

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
    assert summary["staged"][0]["action"] == ACTION_OPEN_LONG
    assert summary["staged"][0]["signal_side"] == "LONG"
    assert summary["staged"][0]["status"] == "READY"
    assert summary["processed_ready"][0]["reason"] == "shadow_mode_no_order_sent"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT signal_side, gate_reason, payload_json FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()

    assert row is not None
    payload = json.loads(row[2])
    assert row[0] == "LONG"
    assert row[1] == "ready_for_live_execution"
    assert payload["signal_snapshot"]["signal_side"] == "LONG"
    assert payload["signal_snapshot"]["source_signal_side"] == "SHORT"
    assert payload["model_decision"]["action"] == ACTION_OPEN_LONG


def test_run_live_execute_accepts_hold_without_order(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _, signal_id = _create_consumed_signal(db_path)

    def _force_hold(self, model_input):
        return _forced_inference_result(
            model_input,
            action=ACTION_HOLD,
            reason="force_hold",
        )

    monkeypatch.setattr(
        "core.model2.live_service.ModelInferenceService.infer",
        _force_hold,
    )

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
    assert summary["staged"][0]["action"] == ACTION_HOLD
    assert summary["staged"][0]["status"] == "BLOCKED"
    assert summary["staged"][0]["reason"] == "model_action_hold"
    assert summary["processed_ready"] == []

    with sqlite3.connect(db_path) as conn:
        decision_row = conn.execute(
            "SELECT action, reason_code FROM model_decisions WHERE id = ?",
            (int(summary["staged"][0]["decision_id"]),),
        ).fetchone()
        execution_row = conn.execute(
            "SELECT status, gate_reason FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()

    assert decision_row == (ACTION_HOLD, "force_hold")
    assert execution_row == ("BLOCKED", "model_action_hold")


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
    assert summary["staged"][0]["decision_id"] > 0
    assert summary["staged"][0]["model_version"] == "m2-inference-v1"
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


def test_run_live_execute_blocks_when_risk_gate_is_not_allowing_orders(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _, signal_id = _create_consumed_signal(db_path)
    exchange = FakeExchange(available_balance=100.0, protection_works=True)
    risk_gate = RiskGate()
    risk_gate.status = RiskGateStatus.FROZEN

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
        risk_gate=risk_gate,
        circuit_breaker=CircuitBreaker(),
    )

    assert summary["status"] == "ok"
    assert summary["staged"][0]["status"] == "BLOCKED"
    assert summary["staged"][0]["reason"] == "risk_gate_blocked"
    assert summary["processed_ready"] == []

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, gate_reason FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()

    assert row == ("BLOCKED", "risk_gate_blocked")


def test_run_live_execute_revalidates_guardrails_before_market_order(tmp_path: Path) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _, signal_id = _create_consumed_signal(db_path)
    exchange = SequencedBalanceExchange([100.0, 100.0, 96.8], protection_works=True)

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
        risk_gate=RiskGate(),
        circuit_breaker=CircuitBreaker(),
    )

    assert summary["status"] == "ok"
    assert summary["staged"][0]["status"] == "READY"
    assert summary["processed_ready"][0]["status"] == "FAILED"
    assert summary["processed_ready"][0]["reason"] == "risk_gate_blocked"
    assert exchange.market_calls == 0

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, failure_reason FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()

    assert row == ("FAILED", "risk_gate_blocked")


def test_run_live_execute_emits_alert_when_risk_gate_blocks(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _create_consumed_signal(db_path)
    exchange = SequencedBalanceExchange([100.0, 100.0, 96.8], protection_works=True)
    captured: list[tuple[str, dict]] = []

    def _capture_alert(self, event_type: str, details: dict) -> bool:
        captured.append((event_type, details))
        return True

    monkeypatch.setattr(
        "core.model2.live_service.Model2LiveAlertPublisher.publish_critical",
        _capture_alert,
    )

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
        risk_gate=RiskGate(),
        circuit_breaker=CircuitBreaker(),
    )

    assert summary["processed_ready"][0]["reason"] == "risk_gate_blocked"
    assert any(event == "risk_gate_blocked" for event, _ in captured)


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


def test_run_live_execute_blocks_when_inference_state_is_invalid(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _, signal_id = _create_consumed_signal(db_path)

    def _always_invalid_builder(**kwargs):
        return StateBuilderResult(
            success=False,
            model_input=None,
            error_code="invalid_inference_state",
            error_message="builder_forcado_para_teste",
            diagnostics={"origin": "test"},
            generated_at_ms=1_700_000_000_000,
            schema_version=M2_020_3_SCHEMA_VERSION,
        )

    monkeypatch.setattr(
        "core.model2.live_service.build_model_decision_input",
        _always_invalid_builder,
    )

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
    assert summary["staged"][0]["status"] == "BLOCKED"
    assert summary["staged"][0]["reason"] == "invalid_model_inference_state"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, gate_reason FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()

    assert row == ("BLOCKED", "invalid_model_inference_state")


def test_run_live_execute_protection_failure_is_deferred_without_failing_entry(tmp_path: Path) -> None:
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
    assert summary["processed_ready"][0]["status"] == "ENTRY_FILLED"
    assert summary["processed_ready"][0]["reason"] == "protection_not_armed_deferred"
    assert exchange.market_calls == 1
    assert exchange.close_calls == 0
    assert exchange.get_open_position("BTCUSDT") is not None

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT status, failure_reason, stop_order_id, take_profit_order_id
            FROM signal_executions
            WHERE technical_signal_id = ?
            """,
            (signal_id,),
        ).fetchone()
    assert row == ("ENTRY_FILLED", None, None, None)


def test_run_live_execute_emits_alert_when_protection_is_not_armed(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _create_consumed_signal(db_path)
    exchange = FakeExchange(available_balance=100.0, protection_works=False)
    captured: list[tuple[str, dict]] = []

    def _capture_alert(self, event_type: str, details: dict) -> bool:
        captured.append((event_type, details))
        return True

    monkeypatch.setattr(
        "core.model2.live_service.Model2LiveAlertPublisher.publish_critical",
        _capture_alert,
    )

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

    assert summary["processed_ready"][0]["reason"] == "protection_not_armed_deferred"
    assert any(event == "protection_not_armed" for event, _ in captured)


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
    from core.model2 import live_service as live_service_module

    live_service_module.time.sleep = lambda _: None

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

    assert second_reconcile["reconciled"][0]["status"] == "PROTECTED"
    assert second_reconcile["reconciled"][0]["reason"] != "external_close_detected"

    third_reconcile = run_live_reconcile(
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
    assert third_reconcile["reconciled"][0]["status"] == "EXITED"
    assert third_reconcile["reconciled"][0]["reason"] == "external_close_detected"

    execution = repository.list_signal_executions(limit=10)[0]
    assert int(execution["technical_signal_id"]) == signal_id
    assert execution["status"] == "EXITED"


def test_live_reconcile_external_close_does_not_emit_critical_alert(tmp_path: Path, monkeypatch) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _repository, _signal_id = _create_consumed_signal(db_path)
    exchange = FakeExchange(available_balance=100.0, protection_works=True)
    captured: list[tuple[str, dict]] = []

    def _capture_alert(self, event_type: str, details: dict) -> bool:
        captured.append((event_type, details))
        return True

    monkeypatch.setattr(
        "core.model2.live_service.Model2LiveAlertPublisher.publish_critical",
        _capture_alert,
    )

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

    exchange.positions.pop("BTCUSDT", None)
    from core.model2 import live_service as live_service_module

    live_service_module.time.sleep = lambda _: None

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

    assert reconcile_summary["reconciled"][0]["status"] == "PROTECTED"
    assert reconcile_summary["reconciled"][0]["reason"] != "external_close_detected"

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
    assert second_reconcile["reconciled"][0]["reason"] == "external_close_detected"
    assert not any(event == "reconciliation_critical_divergence" for event, _ in captured)


def test_log_operational_status_redispara_treino_incremental_apos_termino_sem_duplicar_concorrencia(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from core.model2.live_service import Model2LiveExecutionService

    class ProcessoFake:
        def __init__(self, pid: int) -> None:
            self.pid = pid
            self.returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

    processos: list[ProcessoFake] = []
    comandos: list[tuple[object, ...]] = []

    def _capture_subprocess(*args, **kwargs):
        comandos.append(args)
        processo = ProcessoFake(pid=1234 + len(processos))
        processos.append(processo)
        return processo

    monkeypatch.setattr(
        "core.model2.live_service.collect_training_info",
        lambda db_path: ("2026-03-15 17:22:40", 100),
    )
    monkeypatch.setattr(
        "core.model2.live_service.collect_position_info",
        lambda symbol, exchange_client=None: {
            "has_position": False,
            "position_side": "",
            "position_qty": 0.0,
            "position_entry_price": 0.0,
            "position_mark_price": 0.0,
            "position_pnl_pct": 0.0,
            "position_pnl_usd": 0.0,
        },
    )
    monkeypatch.setattr(
        "core.model2.live_service.format_symbol_report",
        lambda report: "ok",
    )
    monkeypatch.setattr(
        "core.model2.live_service.subprocess",
        SimpleNamespace(Popen=_capture_subprocess, run=_capture_subprocess),
        raising=False,
    )

    service = Model2LiveExecutionService(
        repository=SimpleNamespace(),
        config=SimpleNamespace(execution_mode="shadow", db_path=str(tmp_path / "modelo2.db")),
    )

    service._log_operational_status(
        "BTCUSDT",
        ModelDecision(
            action=ACTION_HOLD,
            confidence=0.5,
            size_fraction=0.0,
            sl_target=None,
            tp_target=None,
            reason_code="test",
            decision_timestamp=1_700_000_000_000,
            symbol="BTCUSDT",
            model_version="m2-inference-v1",
            metadata={},
        ),
    )

    assert len(processos) == 1

    service._log_operational_status(
        "BTCUSDT",
        ModelDecision(
            action=ACTION_HOLD,
            confidence=0.5,
            size_fraction=0.0,
            sl_target=None,
            tp_target=None,
            reason_code="test",
            decision_timestamp=1_700_000_000_000,
            symbol="BTCUSDT",
            model_version="m2-inference-v1",
            metadata={},
        ),
    )

    assert len(processos) == 1

    processos[0].returncode = 0

    service._log_operational_status(
        "BTCUSDT",
        ModelDecision(
            action=ACTION_HOLD,
            confidence=0.5,
            size_fraction=0.0,
            sl_target=None,
            tp_target=None,
            reason_code="test",
            decision_timestamp=1_700_000_000_000,
            symbol="BTCUSDT",
            model_version="m2-inference-v1",
            metadata={},
        ),
    )

    assert len(processos) == 2
    assert comandos[0] == comandos[1]


def _forced_action_result(action: str) -> "InferenceServiceResult":
    """Gera InferenceServiceResult forçado com a acao especificada (helper para testes M2-020.5)."""
    from core.model2.model_decision import ModelDecision

    return InferenceServiceResult(
        accepted=True,
        decision=ModelDecision(
            action=action,
            confidence=0.70,
            size_fraction=0.0,
            sl_target=None,
            tp_target=None,
            reason_code=f"force_{action.lower()}",
            decision_timestamp=1_700_000_000_000,
            symbol="BTCUSDT",
            model_version="m2-inference-v1",
            metadata={"origin": "test_m2_020_5"},
        ),
        model_version="m2-inference-v1",
        inference_latency_ms=1,
        reason=f"force_{action.lower()}",
        rule_id="TEST-M2-020.5",
        details={"origin": "test"},
    )


def test_model_action_reduce_blocks_without_order_and_no_strategy_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    """M2-020.5: REDUCE nao gera entrada e nao reativa estrategia externa."""
    db_path = _prepare_model2_db(tmp_path)
    _, signal_id = _create_consumed_signal(db_path)

    def _force_reduce(self, model_input):
        return _forced_action_result(ACTION_REDUCE)

    monkeypatch.setattr(
        "core.model2.live_service.ModelInferenceService.infer",
        _force_reduce,
    )

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
    staged = summary["staged"][0]
    assert staged["action"] == ACTION_REDUCE
    assert staged["status"] == "BLOCKED"
    assert staged["reason"] == "model_action_reduce_no_entry"
    assert summary["processed_ready"] == []

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, gate_reason FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()
    assert row == ("BLOCKED", "model_action_reduce_no_entry")


def test_model_action_close_blocks_without_order_and_no_strategy_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    """M2-020.5: CLOSE nao gera entrada e nao reativa estrategia externa."""
    db_path = _prepare_model2_db(tmp_path)
    _, signal_id = _create_consumed_signal(db_path)

    def _force_close(self, model_input):
        return _forced_action_result(ACTION_CLOSE)

    monkeypatch.setattr(
        "core.model2.live_service.ModelInferenceService.infer",
        _force_close,
    )

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
    staged = summary["staged"][0]
    assert staged["action"] == ACTION_CLOSE
    assert staged["status"] == "BLOCKED"
    assert staged["reason"] == "model_action_close_no_entry"
    assert summary["processed_ready"] == []

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, gate_reason FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()
    assert row == ("BLOCKED", "model_action_close_no_entry")
