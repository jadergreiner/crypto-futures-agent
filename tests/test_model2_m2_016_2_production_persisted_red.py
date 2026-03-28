"""Suite RED M2-016.2: validacao imediata com artefatos persistidos de producao.

Objetivo:
- R1: consumir artefatos persistidos sem aguardar nova janela.
- R2: falhar em modo conservador quando faltar arquivo/campo obrigatorio.
- R3: consolidar comparativo RL vs baseline de forma auditavel.
- R4: validar consistencia temporal da janela ja concluida.
- R5: emitir GO/NO-GO imediato preservando idempotencia por decision_id.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.model2 import m2_016_2_validation_window as validation_window
from scripts.model2 import phase_d5_real_data_correlation as phase_d5
from scripts.model2 import train_ppo_lstm as train_lstm


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _prepare_persisted_artifacts(base_dir: Path) -> dict[str, Path]:
    runtime_dir = base_dir / "results" / "model2" / "runtime"
    analysis_dir = base_dir / "results" / "model2" / "analysis"

    start_ms = 1_800_000_000_000
    end_ms = start_ms + (73 * 3600 * 1000)

    window_file = runtime_dir / "model2_m2_016_2_window_20260328T120000Z.json"
    checkpoint_file = runtime_dir / "model2_m2_016_2_checkpoint_20260328T180000Z.json"
    report_file = analysis_dir / "model2_m2_016_2_report_20260328T120000Z.json"
    baseline_file = base_dir / "results" / "model2" / "signal_enhancement_report_20260314.json"

    _write_json(
        window_file,
        {
            "task_id": "M2-016.2",
            "window_id": "20260328T120000Z",
            "started_at_utc_ms": start_ms,
            "planned_end_utc_ms": end_ms,
            "execution_mode": "live",
            "status": "in_progress",
        },
    )
    _write_json(
        checkpoint_file,
        {
            "task_id": "M2-016.2",
            "window_id": "20260328T120000Z",
            "timestamp_utc_ms": end_ms,
            "kpis": {
                "enhancement_rate_percent": 68.0,
                "win_rate_percent": 57.0,
                "incident_count": 0,
                "divergence_proxy": {"divergence_rate_percent": 11.0},
            },
            "incident_severity_summary": {"P1": 0, "HIGH": 0, "WARN": 0, "UNKNOWN": 0},
        },
    )
    _write_json(
        report_file,
        {
            "task_id": "M2-016.2",
            "window_id": "20260328T120000Z",
            "kpis": {
                "enhancement_rate_percent": 68.0,
                "win_rate_percent": 57.0,
                "incident_count": 0,
                "avg_pipeline_latency_ms": 4200.0,
                "p95_pipeline_latency_ms": 5900.0,
                "divergence_proxy": {"divergence_rate_percent": 11.0},
            },
        },
    )
    _write_json(
        baseline_file,
        {
            "enhancement_rate_percent": 41.0,
            "win_rate_percent": 46.0,
            "incident_count": 1,
            "avg_pipeline_latency_ms": 5300.0,
            "p95_pipeline_latency_ms": 7900.0,
        },
    )

    return {
        "runtime_dir": runtime_dir,
        "analysis_dir": analysis_dir,
        "window_file": window_file,
        "checkpoint_file": checkpoint_file,
        "report_file": report_file,
        "baseline_file": baseline_file,
    }


def test_collect_persisted_validation_artifacts_requires_runtime_and_analysis_files(
    tmp_path: Path,
) -> None:
    """R1: deve localizar artefatos persistidos sem depender de nova coleta."""
    artifacts = _prepare_persisted_artifacts(tmp_path)

    result = validation_window.collect_persisted_validation_artifacts(
        runtime_dir=artifacts["runtime_dir"],
        analysis_dir=artifacts["analysis_dir"],
    )

    assert result["window_file"] == str(artifacts["window_file"])
    assert result["checkpoint_file"] == str(artifacts["checkpoint_file"])
    assert result["report_file"] == str(artifacts["report_file"])


def test_validate_persisted_artifact_completeness_requires_required_files_and_fields(
    tmp_path: Path,
) -> None:
    """R2: completude minima precisa falhar quando faltar arquivo ou campo obrigatorio."""
    artifacts = _prepare_persisted_artifacts(tmp_path)

    result = validation_window.validate_persisted_artifact_completeness(
        window_file=artifacts["window_file"],
        checkpoint_file=artifacts["checkpoint_file"],
        report_file=artifacts["report_file"],
    )

    assert result["status"] == "PASS"
    assert result["missing_files"] == []
    assert result["missing_fields"] == []


def test_validate_persisted_artifact_completeness_missing_report_returns_fail_safe(
    tmp_path: Path,
) -> None:
    """R2: ausencia de relatorio persistido deve bloquear diagnostico imediato."""
    artifacts = _prepare_persisted_artifacts(tmp_path)
    artifacts["report_file"].unlink()

    result = validation_window.validate_persisted_artifact_completeness(
        window_file=artifacts["window_file"],
        checkpoint_file=artifacts["checkpoint_file"],
        report_file=artifacts["report_file"],
    )

    assert result["status"] == "FAIL"
    assert str(artifacts["report_file"]) in result["missing_files"]


def test_validate_persisted_artifact_completeness_missing_required_kpi_returns_fail_safe(
    tmp_path: Path,
) -> None:
    """R2: ausencia de KPI obrigatorio deve invalidar artefato mesmo com kpis presente."""
    artifacts = _prepare_persisted_artifacts(tmp_path)
    _write_json(
        artifacts["report_file"],
        {
            "task_id": "M2-016.2",
            "window_id": "20260328T120000Z",
            "kpis": {
                "enhancement_rate_percent": 68.0,
                "win_rate_percent": 57.0,
                "incident_count": 0,
                "divergence_proxy": {"divergence_rate_percent": 11.0},
            },
        },
    )

    result = validation_window.validate_persisted_artifact_completeness(
        window_file=artifacts["window_file"],
        checkpoint_file=artifacts["checkpoint_file"],
        report_file=artifacts["report_file"],
    )

    assert result["status"] == "FAIL"
    assert any("avg_pipeline_latency_ms" in item for item in result["missing_fields"])


def test_validate_persisted_window_consistency_requires_elapsed_window_greater_than_72h(
    tmp_path: Path,
) -> None:
    """R4: janela persistida precisa provar consistencia temporal acima de 72h."""
    artifacts = _prepare_persisted_artifacts(tmp_path)

    result = validation_window.validate_persisted_window_consistency(
        window_file=artifacts["window_file"],
        checkpoint_file=artifacts["checkpoint_file"],
    )

    assert result["status"] == "PASS"
    assert result["elapsed_hours"] >= 72.0


def test_validate_persisted_window_consistency_detects_checkpoint_before_start(
    tmp_path: Path,
) -> None:
    """R4: checkpoint antes do inicio da janela deve retornar FAIL conservador."""
    artifacts = _prepare_persisted_artifacts(tmp_path)
    _write_json(
        artifacts["checkpoint_file"],
        {
            "task_id": "M2-016.2",
            "window_id": "20260328T120000Z",
            "timestamp_utc_ms": 1_799_999_999_000,
            "kpis": {"incident_count": 0},
        },
    )

    result = validation_window.validate_persisted_window_consistency(
        window_file=artifacts["window_file"],
        checkpoint_file=artifacts["checkpoint_file"],
    )

    assert result["status"] == "FAIL"
    assert result["reason"] == "CHECKPOINT_BEFORE_WINDOW"


def test_build_persisted_baseline_comparison_requires_auditable_delta_table(
    tmp_path: Path,
) -> None:
    """R3: comparativo com baseline precisa gerar tabela de deltas auditavel."""
    artifacts = _prepare_persisted_artifacts(tmp_path)

    result = validation_window.build_persisted_baseline_comparison(
        report_file=artifacts["report_file"],
        baseline_report_path=artifacts["baseline_file"],
    )

    table = {row["metric_key"]: row for row in result["comparison_table"]}
    assert table["enhancement_rate_percent"]["delta_rl_minus_baseline"] == 27.0
    assert table["incident_count"]["delta_rl_minus_baseline"] == -1.0


def test_build_persisted_incident_log_requires_auditable_entries_for_production_diagnostics(
    tmp_path: Path,
) -> None:
    """R3: diagnostico imediato precisa consolidar incidentes persistidos em artefato rastreavel."""
    artifacts = _prepare_persisted_artifacts(tmp_path)

    result = validation_window.build_persisted_incident_log(
        checkpoint_file=artifacts["checkpoint_file"],
        report_file=artifacts["report_file"],
    )

    assert result["status"] == "ok"
    assert "incident_severity_summary" in result


def test_phase_d5_requires_persisted_metrics_bundle_contract_for_production_inputs() -> None:
    """R3: correlacao D5 deve aceitar bundle vindo de artefatos persistidos."""
    result = phase_d5.build_persisted_phase_e_metrics_bundle(
        validation_report={
            "kpis": {
                "enhancement_rate_percent": 68.0,
                "win_rate_percent": 57.0,
                "incident_count": 0,
            }
        }
    )

    assert result["enhancement_rate_percent"] == 68.0
    assert result["win_rate_percent"] == 57.0


def test_train_lstm_requires_production_validation_gate_contract_for_immediate_close() -> None:
    """R4: treino/fechamento precisa aceitar gate de validacao imediata em producao."""
    result = train_lstm.validate_m2_016_2_production_gate(
        validation_status="GO",
        evidence_source="persisted_artifacts",
    )

    assert result["status"] == "PASS"
    assert result["evidence_source"] == "persisted_artifacts"


def test_run_finalize_from_persisted_artifacts_emits_immediate_go_no_go_without_wait(
    tmp_path: Path,
) -> None:
    """R4: fechamento imediato nao deve depender de nova janela quando artefatos ja existem."""
    artifacts = _prepare_persisted_artifacts(tmp_path)

    result = validation_window.run_finalize_from_persisted_artifacts(
        runtime_dir=artifacts["runtime_dir"],
        analysis_dir=artifacts["analysis_dir"],
        baseline_report_path=artifacts["baseline_file"],
    )

    assert result["status"] == "ok"
    assert result["wait_for_new_window"] is False
    assert result["go_no_go"]["decision"] == "GO"


def test_run_finalize_from_persisted_artifacts_returns_no_go_when_required_artifact_missing(
    tmp_path: Path,
) -> None:
    """R2: falta de artefato obrigatorio deve retornar NO_GO fail-safe."""
    artifacts = _prepare_persisted_artifacts(tmp_path)
    artifacts["checkpoint_file"].unlink()

    result = validation_window.run_finalize_from_persisted_artifacts(
        runtime_dir=artifacts["runtime_dir"],
        analysis_dir=artifacts["analysis_dir"],
        baseline_report_path=artifacts["baseline_file"],
    )

    assert result["status"] == "fail_safe"
    assert result["go_no_go"]["decision"] == "NO_GO"
    assert result["reason"] == "MISSING_REQUIRED_ARTIFACT"


def test_run_finalize_from_persisted_artifacts_returns_no_go_when_required_kpi_missing(
    tmp_path: Path,
) -> None:
    """R2: KPI obrigatorio ausente deve bloquear fechamento imediato."""
    artifacts = _prepare_persisted_artifacts(tmp_path)
    _write_json(
        artifacts["report_file"],
        {
            "task_id": "M2-016.2",
            "window_id": "20260328T120000Z",
            "kpis": {
                "enhancement_rate_percent": 68.0,
                "win_rate_percent": 57.0,
                "incident_count": 0,
            },
        },
    )

    result = validation_window.run_finalize_from_persisted_artifacts(
        runtime_dir=artifacts["runtime_dir"],
        analysis_dir=artifacts["analysis_dir"],
        baseline_report_path=artifacts["baseline_file"],
    )

    assert result["status"] == "fail_safe"
    assert result["go_no_go"]["decision"] == "NO_GO"
    assert result["reason"] == "MISSING_REQUIRED_ARTIFACT"


def test_run_finalize_from_persisted_artifacts_persists_decision_id_idempotency_summary(
    tmp_path: Path,
) -> None:
    """R5: fechamento imediato deve expor sumario de idempotencia por decision_id."""
    artifacts = _prepare_persisted_artifacts(tmp_path)

    result = validation_window.run_finalize_from_persisted_artifacts(
        runtime_dir=artifacts["runtime_dir"],
        analysis_dir=artifacts["analysis_dir"],
        baseline_report_path=artifacts["baseline_file"],
        decision_ids=["dec-001", "dec-002", "dec-001"],
    )

    assert result["decision_id_idempotency"]["status"] == "FAIL"
    assert result["decision_id_idempotency"]["duplicates"] == 1


def test_run_finalize_from_persisted_artifacts_returns_no_go_when_report_window_id_mismatch(
    tmp_path: Path,
) -> None:
    """R4: report de outra janela nao pode ser misturado ao fechamento imediato."""
    artifacts = _prepare_persisted_artifacts(tmp_path)
    _write_json(
        artifacts["report_file"],
        {
            "task_id": "M2-016.2",
            "window_id": "20260328T999999Z",
            "kpis": {
                "enhancement_rate_percent": 68.0,
                "win_rate_percent": 57.0,
                "incident_count": 0,
                "avg_pipeline_latency_ms": 4200.0,
                "p95_pipeline_latency_ms": 5900.0,
                "divergence_proxy": {"divergence_rate_percent": 11.0},
            },
        },
    )

    result = validation_window.run_finalize_from_persisted_artifacts(
        runtime_dir=artifacts["runtime_dir"],
        analysis_dir=artifacts["analysis_dir"],
        baseline_report_path=artifacts["baseline_file"],
    )

    assert result["status"] == "fail_safe"
    assert result["go_no_go"]["decision"] == "NO_GO"
    assert result["reason"] == "WINDOW_ID_MISMATCH"


def test_run_finalize_from_persisted_artifacts_writes_analysis_report_with_traceability(
    tmp_path: Path,
) -> None:
    """R3: fechamento imediato deve gerar relatorio final com rastreabilidade de origem."""
    artifacts = _prepare_persisted_artifacts(tmp_path)

    result = validation_window.run_finalize_from_persisted_artifacts(
        runtime_dir=artifacts["runtime_dir"],
        analysis_dir=artifacts["analysis_dir"],
        baseline_report_path=artifacts["baseline_file"],
    )

    analysis_file = Path(result["analysis_file"])
    payload = json.loads(analysis_file.read_text(encoding="utf-8"))

    assert analysis_file.exists()
    assert payload["evidence_source"] == "persisted_artifacts"
    assert payload["source_window_file"] == str(artifacts["window_file"])
