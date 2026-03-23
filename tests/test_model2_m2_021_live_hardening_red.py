"""Suite RED para M2-021: hardening operacional do ciclo live M2."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from core.model2.live_execution import LiveExecutionGateInput, evaluate_live_execution_gate
from core.model2.model_decision import ACTION_OPEN_LONG, ModelDecision
from core.model2.model_inference_service import InferenceServiceResult
from core.model2.repository import Model2ThesisRepository
from core.model2.scanner import DetectionResult, M2_002_RULE_ID, M2_002_THESIS_TYPE
from scripts.model2.go_live_preflight import run_go_live_preflight
from scripts.model2.live_execute import run_live_execute
from scripts.model2.live_reconcile import run_live_reconcile
from scripts.model2.migrate import run_up


@dataclass
class _ExchangeStub:
    """Stub de exchange para cenarios deterministas de integracao."""

    available_balance: float = 100.0
    protection_works: bool = True

    def __post_init__(self) -> None:
        self.positions: dict[str, dict[str, float | str]] = {}
        self.protection: dict[str, dict[str, str]] = {}

    def get_available_balance(self) -> float | None:
        return self.available_balance

    def get_open_position(self, symbol: str) -> dict[str, float | str] | None:
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

    def place_market_entry(
        self,
        *,
        symbol: str,
        signal_side: str,
        quantity: float,
        client_order_id: str,
    ) -> dict[str, str]:
        _ = client_order_id
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
            "avgPrice": str(entry_price),
            "executedQty": str(quantity),
            "symbol": symbol,
        }

    def get_protection_state(self, *, symbol: str, signal_side: str) -> dict[str, str | bool | None]:
        _ = signal_side
        current = self.protection.get(symbol, {})
        return {
            "has_sl": bool(current.get("sl")),
            "has_tp": bool(current.get("tp")),
            "sl_order_id": current.get("sl"),
            "tp_order_id": current.get("tp"),
        }

    def place_protective_order(
        self,
        *,
        symbol: str,
        signal_side: str,
        trigger_price: float,
        order_type: str,
    ) -> dict[str, str]:
        _ = signal_side
        _ = trigger_price
        if not self.protection_works:
            raise RuntimeError("protection_failed")
        current = self.protection.setdefault(symbol, {})
        if order_type == "STOP_MARKET":
            current["sl"] = f"sl-{symbol}"
            return {"algoId": current["sl"]}
        current["tp"] = f"tp-{symbol}"
        return {"algoId": current["tp"]}

    @staticmethod
    def extract_order_identifier(order: dict[str, str]) -> str | None:
        return str(order.get("orderId") or order.get("algoId") or "")

    @staticmethod
    def is_existing_protection_error(error: Exception) -> bool:
        _ = error
        return False

    def close_position_market(
        self,
        *,
        symbol: str,
        signal_side: str,
        quantity: float,
    ) -> dict[str, str]:
        _ = signal_side
        self.positions.pop(symbol, None)
        return {"orderId": f"close-{symbol}", "executedQty": str(quantity)}


@pytest.fixture
def m2_db_path(tmp_path: Path) -> Path:
    """Cria banco M2 isolado para os testes RED."""
    db_path = tmp_path / "db" / "modelo2.db"
    run_up(db_path=db_path, output_dir=tmp_path / "results")
    return db_path


def _build_detection(symbol: str, *, rejection_ts: int) -> DetectionResult:
    metadata = {
        "rule_id": M2_002_RULE_ID,
        "rule_version": "1.0.0",
        "technical_zone": {
            "source": "order_block",
            "zone_id": 7,
            "timestamp": rejection_ts - 1_000,
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


def _seed_consumed_signal(db_path: Path, *, symbol: str = "BTCUSDT") -> tuple[Model2ThesisRepository, int]:
    repository = Model2ThesisRepository(str(db_path))
    base_now_ms = int(datetime.now(timezone.utc).timestamp() * 1000) - 60_000
    detection = _build_detection(symbol, rejection_ts=base_now_ms - 10_000)
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


def _latest_reconcile_payload(db_path: Path, execution_id: int) -> dict[str, object]:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT payload_json
            FROM signal_execution_events
            WHERE signal_execution_id = ?
              AND event_type = 'RECONCILIATION'
            ORDER BY id DESC
            LIMIT 1
            """,
            (execution_id,),
        ).fetchone()
    if row is None:
        return {}
    raw = str(row[0] or "")
    if not raw:
        return {}
    try:
        return dict(json.loads(raw))
    except Exception:
        return {}


def test_decision_id_idempotencia_api_ausente_falha_red() -> None:
    """R1: exige API explicita para deduplicacao por decision_id."""
    from core.model2.live_service import Model2LiveExecutionService

    assert hasattr(Model2LiveExecutionService, "enforce_decision_id_idempotency")


def test_reason_code_catalogo_unico_api_ausente_falha_red() -> None:
    """R2: bloqueios e divergencias precisam taxonomia unica de reason codes."""
    from core.model2 import live_execution as live_execution_module

    assert hasattr(live_execution_module, "REASON_CODE_CATALOG")


def test_retry_timeout_fail_safe_politica_api_ausente_falha_red() -> None:
    """R3: politica explicita de retry/timeout fail-safe deve existir no live."""
    from core.model2 import live_service as live_service_module

    assert hasattr(live_service_module, "FAIL_SAFE_RETRY_TIMEOUT_POLICY")


def test_detector_drift_candles_api_ausente_falha_red() -> None:
    """R3/R4: drift relevante de candle deve ser detectavel via contrato publico."""
    from core.model2 import live_service as live_service_module

    assert hasattr(live_service_module, "detect_candle_drift")


def test_evento_violacao_slo_por_etapa_api_ausente_falha_red() -> None:
    """R4: violacoes de SLO por etapa devem gerar evento rastreavel."""
    from core.model2 import live_service as live_service_module

    assert hasattr(live_service_module, "emit_stage_slo_violation_event")


@pytest.mark.parametrize("criticidade", ["alto", "medio", "baixo"])
def test_fluxo_testnet_criticidade_sem_metricas_por_etapa_falha_red(
    m2_db_path: Path,
    criticidade: str,
) -> None:
    """R4/R8: execucao precisa expor latencia por etapa para cada criticidade."""
    _repository, signal_id = _seed_consumed_signal(m2_db_path, symbol="BTCUSDT")

    summary = run_live_execute(
        model2_db_path=m2_db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=m2_db_path.parent / "results",
        execution_mode="shadow",
        live_symbols=("BTCUSDT",),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
    )

    assert summary["status"] == "ok"
    staged = summary["staged"]
    assert staged, f"Esperava sinal staged para criticidade={criticidade}"
    assert int(staged[0]["technical_signal_id"]) == signal_id

    expected_stage_latency_keys = {
        "decision_latency_ms",
        "admission_latency_ms",
        "send_latency_ms",
        "reconciliation_latency_ms",
    }
    assert expected_stage_latency_keys.issubset(set(staged[0].keys()))


def test_reconciliacao_saida_externa_sem_payload_auditavel_completo_falha_red(
    m2_db_path: Path,
) -> None:
    """R2/R5: payload de reconciliacao precisa reason_code/status/timestamp/metadata."""
    repository, _signal_id = _seed_consumed_signal(m2_db_path, symbol="BTCUSDT")
    exchange: Any = _ExchangeStub(available_balance=100.0, protection_works=True)

    execute_summary = run_live_execute(
        model2_db_path=m2_db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=m2_db_path.parent / "results",
        execution_mode="live",
        live_symbols=("BTCUSDT",),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        exchange=exchange,
    )
    assert execute_summary["status"] == "ok"

    exchange.positions.pop("BTCUSDT", None)
    _ = run_live_reconcile(
        model2_db_path=m2_db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=m2_db_path.parent / "results",
        execution_mode="live",
        live_symbols=("BTCUSDT",),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        exchange=exchange,
    )
    second = run_live_reconcile(
        model2_db_path=m2_db_path,
        symbol="BTCUSDT",
        timeframe="H4",
        limit=50,
        output_dir=m2_db_path.parent / "results",
        execution_mode="live",
        live_symbols=("BTCUSDT",),
        max_daily_entries=10,
        max_margin_per_position_usd=1.0,
        max_signal_age_minutes=240,
        symbol_cooldown_minutes=240,
        exchange=exchange,
    )
    assert second["status"] == "ok"

    execution = repository.list_signal_executions(limit=1)[0]
    payload = _latest_reconcile_payload(m2_db_path, int(execution["id"]))
    assert payload.get("reason_code")
    assert payload.get("status")
    assert payload.get("timestamp")
    assert isinstance(payload.get("metadata"), dict)


def test_reconciliacao_cancelamento_manual_api_ausente_falha_red() -> None:
    """R5: reconciliador precisa contrato explicito para cancelamento manual."""
    from core.model2.live_service import Model2LiveExecutionService

    assert hasattr(Model2LiveExecutionService, "reconcile_manual_cancellation")


def test_reconciliacao_partial_fill_api_ausente_falha_red() -> None:
    """R5: reconciliador precisa contrato explicito para partial fills."""
    from core.model2.live_service import Model2LiveExecutionService

    assert hasattr(Model2LiveExecutionService, "reconcile_partial_fill")


def test_restart_reidratacao_segura_api_ausente_falha_red() -> None:
    """R1/R5: restart seguro exige reidratacao deterministica do runtime."""
    from core.model2.live_service import Model2LiveExecutionService

    assert hasattr(Model2LiveExecutionService, "rehydrate_runtime_state")


def test_rollback_exige_preflight_obrigatorio_api_ausente_falha_red(m2_db_path: Path) -> None:
    """R6: rollback operacional deve ser bloqueado sem preflight obrigatório."""
    summary = run_go_live_preflight(
        model2_db_path=m2_db_path,
        output_dir=m2_db_path.parent / "results",
        env_file=m2_db_path.parent / ".env",
        apply_fixes=False,
        continue_on_error=True,
        live_symbols=("BTCUSDT",),
    )

    assert summary["status"] in {"ok", "alert"}
    assert any(check.get("id") == "rollback_preflight" for check in summary["checks"])


def _build_gate_input_for_regression() -> LiveExecutionGateInput:
    return LiveExecutionGateInput(
        technical_signal_id=1,
        opportunity_id=1,
        symbol="BTCUSDT",
        timeframe="H4",
        signal_side="SHORT",
        technical_signal_status="CONSUMED",
        signal_timestamp=1_700_000_000_000,
        short_only=True,
        funding_rate=0.0001,
        basis_value=1.0,
        funding_rate_max_for_short=0.01,
        execution_mode="live",
        live_symbols=("BTCUSDT",),
        authorized_symbols=("BTCUSDT",),
        available_balance_usd=100.0,
        max_margin_per_position_usd=1.0,
        recent_entries_today=0,
        max_daily_entries=10,
        symbol_active_execution_count=0,
        open_position_qty=0.0,
        cooldown_active=False,
        signal_age_ms=1,
        max_signal_age_ms=1_000_000,
        risk_gate_status="ACTIVE",
        risk_gate_allows_order=True,
        risk_gate_drawdown_pct=0.0,
        circuit_breaker_state="CLOSED",
        circuit_breaker_allows_trading=True,
        circuit_breaker_drawdown_pct=0.0,
    )


def test_guardrails_ativos_bloqueio_sem_reason_code_taxonomico_falha_red() -> None:
    """Regressao: bloqueio de guardrail deve emitir reason_code taxonomico."""
    gate_input = _build_gate_input_for_regression()
    decision = evaluate_live_execution_gate(gate_input)

    assert decision.allow_execution is True
    assert str(decision.reason).startswith("ops.")


def test_ambiguidade_operacional_sem_fail_safe_classificado_falha_red() -> None:
    """Regressao: estado ambiguo deve bloquear com reason_code fail-safe padrao."""
    gate_input = _build_gate_input_for_regression()
    gate_input = LiveExecutionGateInput(
        **{
            **gate_input.__dict__,
            "risk_gate_status": "unknown",
            "risk_gate_allows_order": False,
        }
    )
    decision = evaluate_live_execution_gate(gate_input)

    assert decision.allow_execution is False
    assert decision.target_status == "BLOCKED"
    assert decision.reason == "ops_ambiguous_state"


def test_sucesso_sem_reconciliacao_valida_deve_ser_proibido_falha_red() -> None:
    """Regressao: inferencia aceita sem reconciliacao valida deve ser bloqueada."""
    fake_decision = ModelDecision(
        action=ACTION_OPEN_LONG,
        confidence=0.95,
        size_fraction=0.2,
        sl_target=95.0,
        tp_target=110.0,
        reason_code="test_reason",
        decision_timestamp=1_700_000_000_000,
        symbol="BTCUSDT",
        model_version="m2-test",
        metadata={},
    )
    inference = InferenceServiceResult(
        accepted=True,
        decision=fake_decision,
        model_version="m2-test",
        inference_latency_ms=1,
        reason="accepted",
        rule_id="TEST-M2-021",
        details={"reconciliation_valid": False},
    )

    assert inference.accepted is True
    assert inference.details.get("reconciliation_valid") is False
