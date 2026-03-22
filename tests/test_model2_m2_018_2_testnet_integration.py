import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.model2.repository import Model2ThesisRepository
from core.model2.scanner import DetectionResult, M2_002_RULE_ID, M2_002_THESIS_TYPE
from scripts.model2.healthcheck_live_execution import run_live_healthcheck
from scripts.model2.live_dashboard import run_live_dashboard
from scripts.model2.go_live_preflight import run_go_live_preflight
from scripts.model2.live_execute import run_live_execute
from scripts.model2.live_reconcile import run_live_reconcile
from scripts.model2.migrate import run_up


class FakeExchangeTestnet:
    def __init__(self, *, available_balance: float = 100.0, protection_works: bool = True) -> None:
        self.available_balance = available_balance
        self.protection_works = protection_works
        self.market_calls = 0
        self.protection_calls = 0
        self.positions: dict[str, dict] = {}
        self.protection: dict[str, dict] = {}

    def get_available_balance(self) -> float | None:
        return self.available_balance

    def get_open_position(self, symbol: str):
        return self.positions.get(symbol)

    def calculate_entry_quantity(
        self,
        symbol: str,
        entry_price: float,
        margin_usd: float,
        leverage: int,
    ) -> float:
        _ = symbol
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
        _ = signal_side
        current = self.protection.get(symbol, {})
        return {
            "has_sl": bool(current.get("sl")),
            "has_tp": bool(current.get("tp")),
            "sl_order_id": current.get("sl"),
            "tp_order_id": current.get("tp"),
        }

    def place_protective_order(self, *, symbol: str, signal_side: str, trigger_price: float, order_type: str):
        _ = signal_side
        _ = trigger_price
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
        _ = error
        return False

    def close_position_market(self, *, symbol: str, signal_side: str, quantity: float):
        _ = signal_side
        self.positions.pop(symbol, None)
        return {"orderId": f"close-{symbol}", "executedQty": str(quantity)}


def _build_detection_result(symbol: str = "BNBUSDT", rejection_ts: int = 1_700_000_000_000) -> DetectionResult:
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


def _create_consumed_signal(db_path: Path, symbol: str = "BNBUSDT") -> tuple[Model2ThesisRepository, int]:
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


def _stub_ok(**kwargs):
    output_dir = Path(kwargs["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / "stub_ok.json"
    out.write_text("{}", encoding="utf-8")
    return {"status": "ok", "output_file": str(out)}


def test_m2_018_2_live_cycle_registers_protected_execution(tmp_path: Path) -> None:
    """Requisito R1: ciclo live controlado deve produzir status PROTECTED."""
    db_path = _prepare_model2_db(tmp_path)
    repository, signal_id = _create_consumed_signal(db_path, symbol="BNBUSDT")
    exchange = FakeExchangeTestnet(available_balance=100.0, protection_works=True)

    summary = run_live_execute(
        model2_db_path=db_path,
        symbol="BNBUSDT",
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
    assert summary["processed_ready"][0]["status"] == "PROTECTED"

    execution = repository.list_signal_executions(limit=10)[0]
    assert int(execution["technical_signal_id"]) == signal_id
    assert execution["status"] == "PROTECTED"


def test_m2_018_2_reconcile_external_close_marks_exited(tmp_path: Path) -> None:
    """Requisito R2 (RED): EXITED exige ausencia confirmada em 2 checks."""
    db_path = _prepare_model2_db(tmp_path)
    repository, signal_id = _create_consumed_signal(db_path, symbol="BNBUSDT")
    exchange = FakeExchangeTestnet(available_balance=100.0, protection_works=True)

    execute_summary = run_live_execute(
        model2_db_path=db_path,
        symbol="BNBUSDT",
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

    exchange.positions.pop("BNBUSDT", None)
    from core.model2 import live_service as live_service_module

    live_service_module.time.sleep = lambda _: None

    reconcile_summary = run_live_reconcile(
        model2_db_path=db_path,
        symbol="BNBUSDT",
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
        symbol="BNBUSDT",
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

    execution = repository.list_signal_executions(limit=10)[0]
    assert int(execution["technical_signal_id"]) == signal_id
    assert execution["status"] == "EXITED"


def test_m2_018_2_healthcheck_pos_ciclo_sem_divergencias_criticas(
    tmp_path: Path,
) -> None:
    db_path = _prepare_model2_db(tmp_path)
    _repository, _signal_id = _create_consumed_signal(db_path, symbol="BNBUSDT")
    exchange = FakeExchangeTestnet(available_balance=100.0, protection_works=True)

    execute_summary = run_live_execute(
        model2_db_path=db_path,
        symbol="BNBUSDT",
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

    dashboard_summary = run_live_dashboard(
        model2_db_path=db_path,
        output_dir=tmp_path / "results" / "model2" / "runtime",
        retention_days=30,
    )

    healthcheck_summary = run_live_healthcheck(
        runtime_dir=tmp_path / "results" / "model2" / "runtime",
        output_dir=tmp_path / "results" / "model2" / "runtime",
        max_age_hours=2,
        max_unprotected_filled=0,
        max_stale_entry_sent=0,
        max_position_mismatches=0,
        alert_command=None,
    )

    assert dashboard_summary["status"] == "ok"
    assert healthcheck_summary["status"] == "ok"


def test_m2_018_2_preflight_modo_live_nao_exige_credenciais_testnet(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "db" / "modelo2.db"
    env_file = tmp_path / ".env"
    env_file.write_text(
        "TRADING_MODE=live\n"
        "M2_EXECUTION_MODE=live\n"
        "M2_LIVE_SYMBOLS=BNBUSDT\n",
        encoding="utf-8",
    )

    summary = run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        env_file=env_file,
        apply_fixes=True,
        continue_on_error=True,
        live_symbols=("BNBUSDT",),
        db_write_probe=lambda _: None,
        migrate_fn=_stub_ok,
        live_execute_fn=_stub_ok,
        live_reconcile_fn=_stub_ok,
        live_dashboard_fn=_stub_ok,
        live_healthcheck_fn=_stub_ok,
    )

    credential_alerts = [
        item
        for item in summary["checks"]
        if "BINANCE_API_KEY" in str(item.get("error", ""))
        or "BINANCE_API_SECRET" in str(item.get("error", ""))
    ]

    assert credential_alerts == []


def test_m2_018_2_preflight_requires_testnet_credentials_when_paper_mode(tmp_path: Path) -> None:
    """Requisito R4 (RED): preflight deve bloquear sem credenciais testnet em paper."""
    db_path = tmp_path / "db" / "modelo2.db"
    env_file = tmp_path / ".env"
    env_file.write_text(
        "TRADING_MODE=paper\n"
        "M2_EXECUTION_MODE=shadow\n"
        "M2_LIVE_SYMBOLS=BNBUSDT\n",
        encoding="utf-8",
    )

    summary = run_go_live_preflight(
        model2_db_path=db_path,
        output_dir=tmp_path / "results",
        env_file=env_file,
        apply_fixes=True,
        continue_on_error=True,
        live_symbols=("BNBUSDT",),
        db_write_probe=lambda _: None,
        migrate_fn=_stub_ok,
        live_execute_fn=_stub_ok,
        live_reconcile_fn=_stub_ok,
        live_dashboard_fn=_stub_ok,
        live_healthcheck_fn=_stub_ok,
    )

    assert summary["status"] == "alert"
    missing_credentials = [
        item
        for item in summary["checks"]
        if "BINANCE_API_KEY" in str(item.get("error", ""))
        or "BINANCE_API_SECRET" in str(item.get("error", ""))
    ]
    assert missing_credentials, "Preflight deveria acusar ausencia de credenciais testnet."


def test_m2_018_2_retry_same_decision_does_not_duplicate_execution(tmp_path: Path) -> None:
    """Requisito R6: idempotencia por decision_id em retries do mesmo sinal."""
    db_path = _prepare_model2_db(tmp_path)
    _repository, signal_id = _create_consumed_signal(db_path, symbol="BNBUSDT")
    exchange = FakeExchangeTestnet(available_balance=100.0, protection_works=True)

    first_summary = run_live_execute(
        model2_db_path=db_path,
        symbol="BNBUSDT",
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
        symbol="BNBUSDT",
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
    assert second_summary["processed_ready"] == []

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM signal_executions WHERE technical_signal_id = ?",
            (signal_id,),
        ).fetchone()

    assert count is not None
    assert int(count[0]) == 1
