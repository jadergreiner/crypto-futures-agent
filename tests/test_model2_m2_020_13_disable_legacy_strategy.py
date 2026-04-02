from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, cast

from agent.rollback_handler import RollbackHandler
from core.model2.model_decision import ModelDecisionInput
from core.model2.model_inference_service import (
    ModelInferenceService,
    TechnicalSignalInferenceProvider,
)
from scripts.model2.operator_cycle_status import _build_symbol_report


class _FakeLoader:
    """Loader deterministico para exercitar a auditoria de origem."""

    def __init__(
        self,
        *,
        confidence: float = 0.82,
        action: str = "LONG",
        is_fallback: bool = False,
        fallback_reason: str = "",
    ) -> None:
        self._confidence = float(confidence)
        self._action = str(action)
        self.is_fallback = bool(is_fallback)
        self.fallback_reason = str(fallback_reason)

    def predict_confidence(self, *, features: Any, signal_side: str) -> tuple[float, str]:
        _ = features
        _ = signal_side
        return self._confidence, self._action


class _NoopProtectionHeads:
    """Evita dependencia de modelo de protecao real nos testes unitarios."""

    def predict(self, *, symbol: str, features: Any) -> None:
        _ = symbol
        _ = features
        return None


class _AuditableProvider:
    """Provider fake que devolve payload valido com campos de auditoria."""

    def infer(self, model_input: ModelDecisionInput) -> Mapping[str, Any]:
        _ = model_input
        return {
            "action": "OPEN_LONG",
            "confidence": 0.88,
            "size_fraction": 0.25,
            "sl": 95.0,
            "tp": 112.0,
            "reason": "provider_fake_auditavel",
            "origin": "RL_MODEL",
            "contaminated": False,
            "decision_id": "dec-audit-001",
            "baseline_comparative": {
                "action": "OPEN_SHORT",
                "confidence": 0.41,
                "reasoning": "legacy_should_stay_only_in_audit",
            },
            "metadata": {
                "action_source": "rl_action",
                "rl_fallback": False,
                "rl_fallback_reason": "",
            },
        }


def _base_input(*, signal_side: str = "SHORT") -> ModelDecisionInput:
    return ModelDecisionInput(
        symbol="BTCUSDT",
        timeframe="M5",
        decision_timestamp=1_700_001_000_000,
        model_version="m2-inference-v1",
        market_state={
            "signal_side": signal_side,
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 112.0,
            "close_price": 101.0,
            "market_context": {"h1_close": 101.2, "h4_close": 100.5},
        },
        position_state={},
        risk_state={"signal_age_ms": 60_000, "max_signal_age_ms": 300_000},
    )


def _build_provider(*, is_fallback: bool = False) -> TechnicalSignalInferenceProvider:
    provider = TechnicalSignalInferenceProvider(model_first=True)
    provider._resolve_loader_for_symbol = cast(  # type: ignore[method-assign]
        Any,
        lambda _symbol: _FakeLoader(
            action="LONG",
            confidence=0.87,
            is_fallback=is_fallback,
            fallback_reason="model_loader_unavailable" if is_fallback else "",
        ),
    )
    provider._protection_heads = _NoopProtectionHeads()  # type: ignore[assignment]
    return provider


def _create_status_db(
    tmp_path: Path,
    *,
    input_json: dict[str, Any] | None = None,
    output_json: dict[str, Any] | None = None,
) -> str:
    db_path = tmp_path / "status_m2_020_13.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE model_decisions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "symbol TEXT NOT NULL,"
            "action TEXT NOT NULL,"
            "confidence REAL,"
            "model_version TEXT,"
            "reason_code TEXT,"
            "decision_timestamp INTEGER,"
            "input_json TEXT NOT NULL DEFAULT '{}',"
            "output_json TEXT NOT NULL DEFAULT '{}'"
            ")"
        )
        conn.execute(
            "INSERT INTO model_decisions ("
            "symbol, action, confidence, model_version, reason_code, "
            "decision_timestamp, input_json, output_json"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "BTCUSDT",
                "OPEN_LONG",
                0.81,
                "m2-inference-v1",
                "provider_fake_auditavel",
                1_700_001_000_000,
                json.dumps(input_json or {}),
                json.dumps(output_json or {}),
            ),
        )
        conn.commit()
    return str(db_path)


def test_provider_marca_rl_model_apenas_quando_acao_veio_do_modelo() -> None:
    """RL_MODEL so e valido quando action_source=rl_action e sem fallback."""
    provider = _build_provider(is_fallback=False)

    resultado = provider.infer(
        signal={
            "symbol": "BTCUSDT",
            "signal_side": "SHORT",
            "action_source": "rl_model",
            "rl_fallback": False,
            "decision_id": "dec-001",
        }
    )

    assert resultado["origin"] == "RL_MODEL"
    assert resultado["contaminated"] is False
    assert resultado["decision_id"] == "dec-001"


def test_provider_marca_fallback_quando_signal_side_vira_fonte_oficial() -> None:
    """Se a fonte oficial for signal_side, o payload deve ficar contaminado."""
    provider = _build_provider(is_fallback=False)

    resultado = provider.infer(
        signal={
            "symbol": "BTCUSDT",
            "signal_side": "SHORT",
            "action_source": "signal_side",
            "rl_fallback": False,
        }
    )

    assert resultado["origin"] == "FALLBACK"
    assert resultado["contaminated"] is True


def test_provider_marca_fallback_quando_loader_esta_em_rl_fallback() -> None:
    """Mesmo com action_source=rl_action, rl_fallback=True invalida RL_MODEL."""
    provider = _build_provider(is_fallback=True)

    resultado = provider.infer(
        signal={
            "symbol": "BTCUSDT",
            "signal_side": "SHORT",
            "action_source": "rl_model",
        }
    )

    assert resultado["origin"] == "FALLBACK"
    assert resultado["contaminated"] is True
    assert resultado["metadata"]["rl_fallback_reason"] == "model_loader_unavailable"


def test_provider_mantem_baseline_comparative_apenas_como_auditoria() -> None:
    """A comparacao com o legado deve permanecer auditavel sem virar decisao."""
    provider = _build_provider(is_fallback=False)

    resultado = provider.infer(
        signal={
            "symbol": "BTCUSDT",
            "signal_side": "SHORT",
            "action_source": "rl_model",
        }
    )

    assert resultado["action"] == "OPEN_LONG"
    assert resultado["baseline_comparative"]["action"] == "OPEN_SHORT"
    assert "signal_side_fallback=SHORT" in resultado["baseline_comparative"]["reasoning"]


def test_model_inference_service_preserva_campos_auditaveis_no_metadata() -> None:
    """Campos de auditoria precisam sobreviver ao contrato validado."""
    service = ModelInferenceService(provider=_AuditableProvider(), model_version="m2-audit")

    resultado = service.infer(_base_input(signal_side="SHORT"))

    assert resultado.accepted is True
    assert resultado.decision is not None
    assert resultado.decision.metadata["origin"] == "RL_MODEL"
    assert resultado.decision.metadata["contaminated"] is False
    assert resultado.decision.metadata["decision_id"] == "dec-audit-001"
    assert resultado.decision.metadata["baseline_comparative"]["action"] == "OPEN_SHORT"


def test_model_inference_service_expoe_auditoria_nos_details_sem_schema_novo() -> None:
    """O resultado de inferencia deve carregar auditoria para persistencia."""
    service = ModelInferenceService(provider=_AuditableProvider(), model_version="m2-audit")

    resultado = service.infer(_base_input(signal_side="SHORT"))

    assert resultado.accepted is True
    assert resultado.details["origin"] == "RL_MODEL"
    assert resultado.details["contaminated"] is False
    assert resultado.details["decision_id"] == "dec-audit-001"
    assert resultado.details["baseline_comparative"]["action"] == "OPEN_SHORT"


def test_status_operacional_rebaixa_source_quando_action_source_e_signal_side(
    tmp_path: Path,
) -> None:
    """Status do iniciar.bat nao pode mascarar decisao legada como RL_MODEL."""
    db_path = _create_status_db(
        tmp_path,
        input_json={
            "market_state": {"signal_timestamp": 1_700_000_940_000},
            "risk_state": {"signal_age_ms": 60_000, "max_signal_age_ms": 300_000},
        },
        output_json={
            "origin": "RL_MODEL",
            "metadata": {"action_source": "signal_side", "rl_fallback": False},
        },
    )

    report = _build_symbol_report(
        symbol="BTCUSDT",
        scan_d1=None,
        scan_h4=None,
        scan_h1=None,
        scan_m5=None,
        live_execute_summary=None,
        exchange=None,
        last_train_time="N/A",
        pending_episodes=0,
        training_timeframe="M5",
        db_path=db_path,
    )

    assert "source=RL_MODEL" not in report
    assert "source=FALLBACK_MODELO_RL" in report


def test_status_operacional_rebaixa_source_quando_rl_fallback_esta_ativo(
    tmp_path: Path,
) -> None:
    """Fallback do loader precisa aparecer como fallback no status oficial."""
    db_path = _create_status_db(
        tmp_path,
        input_json={
            "market_state": {"signal_timestamp": 1_700_000_940_000},
            "risk_state": {"signal_age_ms": 60_000, "max_signal_age_ms": 300_000},
        },
        output_json={
            "origin": "RL_MODEL",
            "metadata": {"action_source": "rl_action", "rl_fallback": True},
        },
    )

    report = _build_symbol_report(
        symbol="BTCUSDT",
        scan_d1=None,
        scan_h4=None,
        scan_h1=None,
        scan_m5=None,
        live_execute_summary=None,
        exchange=None,
        last_train_time="N/A",
        pending_episodes=0,
        training_timeframe="M5",
        db_path=db_path,
    )

    assert "source=RL_MODEL" not in report
    assert "source=FALLBACK_MODELO_RL" in report


def test_status_operacional_nao_expoe_signal_side_nem_fallback_action_no_resumo(
    tmp_path: Path,
) -> None:
    """Campos legados podem existir na auditoria, nunca na decisao oficial exibida."""
    db_path = _create_status_db(
        tmp_path,
        input_json={
            "market_state": {"signal_timestamp": 1_700_000_940_000},
            "risk_state": {"signal_age_ms": 60_000, "max_signal_age_ms": 300_000},
        },
        output_json={
            "origin": "RL_MODEL",
            "metadata": {
                "action_source": "rl_action",
                "signal_side": "SHORT",
                "fallback_action": "OPEN_SHORT",
                "rl_fallback": False,
            },
        },
    )

    report = _build_symbol_report(
        symbol="BTCUSDT",
        scan_d1=None,
        scan_h4=None,
        scan_h1=None,
        scan_m5=None,
        live_execute_summary=None,
        exchange=None,
        last_train_time="N/A",
        pending_episodes=0,
        training_timeframe="M5",
        db_path=db_path,
    )

    assert "signal_side=" not in report
    assert "fallback_action=" not in report
    assert "decision_id=" in report


def test_trigger_rollback_gera_trilha_auditavel_com_contexto_explicito(
    tmp_path: Path,
) -> None:
    """Rollback fail-safe explicito deve registrar motivo, step e modulo."""
    handler = RollbackHandler(rollback_log_dir=str(tmp_path))

    ok = handler.trigger_rollback(
        reason="kl_divergence_critica",
        model_step=42,
        metrics_snapshot={"risk_gate": "ATIVO", "circuit_breaker": "ATIVO"},
    )

    arquivos = list(tmp_path.glob("rollback_*.json"))
    assert ok is True
    assert handler.is_on_fallback is True
    assert len(arquivos) == 1
    payload = json.loads(arquivos[0].read_text(encoding="utf-8"))
    assert payload["reason"] == "kl_divergence_critica"
    assert payload["step"] == 42
    assert payload["fallback_module"] == "execution.heuristic_signals"


def test_fallback_to_heuristics_sem_contexto_explicito_nao_ativa_fluxo_nominal(
    tmp_path: Path,
) -> None:
    """O caminho nominal nao pode acionar heuristica sem rollback auditavel."""
    handler = RollbackHandler(rollback_log_dir=str(tmp_path))

    resultado = handler.fallback_to_heuristics()

    assert resultado is False
    assert handler.is_on_fallback is False
    assert list(tmp_path.glob("rollback_*.json")) == []


def test_decision_id_permanece_estavel_em_fail_safe_auditavel() -> None:
    """A idempotencia por decision_id precisa sobreviver ao fail-safe."""
    provider = _build_provider(is_fallback=False)

    resultado = provider.infer(
        signal={
            "symbol": "BTCUSDT",
            "signal_side": "SHORT",
            "action_source": "rl_model",
            "rl_fallback": False,
            "decision_id": "dec-stable-777",
            "model_available": False,
        }
    )

    assert resultado["decision_id"] == "dec-stable-777"
    assert resultado["fail_safe"] is True
    assert resultado["audit_trail"]["decision_id"] == "dec-stable-777"
