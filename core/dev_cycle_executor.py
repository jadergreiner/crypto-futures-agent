from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping

DecisionStageFn = Callable[[dict[str, Any]], Mapping[str, Any]]

_DECISIONS_BLOQUEIO = {"DEVOLVIDO_PARA_REVISAO", "DEVOLVER_PARA_AJUSTE"}


@dataclass(frozen=True)
class StageExecution:
    index: int
    total: int
    name: str
    decision: str
    elapsed_ms: int
    handoff: dict[str, Any]
    motivo: str


@dataclass(frozen=True)
class BlockedStageRouting:
    decision: str
    action: str
    return_stage: str
    reason_code: str


class DevCycleExecutor:
    def __init__(self, *, checkpoint_path: Path | str, audit_log_path: Path | str | None) -> None:
        self._checkpoint_path = Path(checkpoint_path)
        self._audit_log_path = Path(audit_log_path) if audit_log_path is not None else None

    def run(
        self,
        *,
        item_id: str,
        stages: list[tuple[str, DecisionStageFn]],
        resume: bool = False,
        initial_context: Mapping[str, Any] | None = None,
        retry_budget_by_stage: Mapping[str, int] | None = None,
    ) -> dict[str, Any]:
        if resume:
            state = self._load_checkpoint()
            if state.get("item_id") != item_id:
                raise ValueError("checkpoint_item_id_invalido")
            next_stage_index = int(state.get("next_stage_index", 0))
            stage_outputs = dict(state.get("stage_outputs", {}))
            progress = list(state.get("progress", []))
        else:
            next_stage_index = 0
            stage_outputs = {}
            progress = []

        context: dict[str, Any] = {
            "item_id": item_id,
            "stage_outputs": stage_outputs,
            "initial_context": dict(initial_context or {}),
        }

        total = len(stages)
        for stage_idx in range(next_stage_index, total):
            stage_name, stage_fn = stages[stage_idx]
            known_output = stage_outputs.get(stage_name)
            if isinstance(known_output, Mapping):
                known_decision = str(known_output.get("decision", "")).strip().upper()
                if known_decision and known_decision not in _DECISIONS_BLOQUEIO:
                    skip_label = f"[STAGE {stage_idx + 1}/{total}] {stage_name} - JA_CONCLUIDO (SKIP)"
                    progress.append(skip_label)
                    self._append_audit_event(
                        item_id=item_id,
                        stage=stage_name,
                        event="stage_skipped_already_completed",
                        detail={"decision": known_decision},
                    )
                    continue

            start_label = f"[STAGE {stage_idx + 1}/{total}] {stage_name} - iniciando..."
            progress.append(start_label)
            self._append_audit_event(item_id=item_id, stage=stage_name, event="stage_started", detail={})

            started = perf_counter()
            stage_retry_budget = self._resolve_retry_budget(
                stage_name=stage_name,
                retry_budget_by_stage=retry_budget_by_stage,
            )
            attempt = 0
            try:
                while True:
                    try:
                        raw_result = dict(stage_fn(context))
                        break
                    except Exception as exc:
                        is_transient = isinstance(exc, (TimeoutError, ConnectionError))
                        if not is_transient or attempt >= stage_retry_budget:
                            raise
                        attempt += 1
                        retry_label = (
                            f"[STAGE {stage_idx + 1}/{total}] "
                            f"{stage_name} - RETRY_TRANSITORIO {attempt}/{stage_retry_budget}"
                        )
                        progress.append(retry_label)
                        self._append_audit_event(
                            item_id=item_id,
                            stage=stage_name,
                            event="stage_retry_transient_error",
                            detail={"attempt": attempt, "error": str(exc)},
                        )
            except Exception as exc:
                elapsed_ms = int((perf_counter() - started) * 1000)
                error_label = f"[STAGE {stage_idx + 1}/{total}] {stage_name} - DEVOLVIDO_PARA_REVISAO"
                progress.append(error_label)
                routing = self.resolve_blocked_routing(
                    stage_name=stage_name,
                    decision="DEVOLVIDO_PARA_REVISAO",
                    motivo=str(exc),
                )
                self._append_audit_event(
                    item_id=item_id,
                    stage=stage_name,
                    event="stage_blocked",
                    detail={
                        "reason": "exception",
                        "error": str(exc),
                        "elapsed_ms": elapsed_ms,
                        "return_stage": routing.return_stage,
                        "reason_code": routing.reason_code,
                    },
                )
                self._save_checkpoint(
                    item_id=item_id,
                    next_stage_index=stage_idx,
                    progress=progress,
                    stage_outputs=stage_outputs,
                    status="AGUARDANDO_CORRECAO",
                )
                return {
                    "status": "AGUARDANDO_CORRECAO",
                    "blocked_stage": stage_name,
                    "return_stage": routing.return_stage,
                    "return_action": routing.action,
                    "return_reason_code": routing.reason_code,
                    "motivo": str(exc),
                    "progress": progress,
                }

            elapsed_ms = int((perf_counter() - started) * 1000)
            stage_result = self._normalize_stage_result(
                stage_idx=stage_idx,
                total=total,
                stage_name=stage_name,
                raw_result=raw_result,
                elapsed_ms=elapsed_ms,
            )
            stage_outputs[stage_name] = {
                "decision": stage_result.decision,
                "handoff": stage_result.handoff,
                "motivo": stage_result.motivo,
                "elapsed_ms": stage_result.elapsed_ms,
            }
            context["stage_outputs"] = stage_outputs

            if stage_result.decision in _DECISIONS_BLOQUEIO:
                blocked_label = f"[STAGE {stage_idx + 1}/{total}] {stage_name} - {stage_result.decision}"
                progress.append(blocked_label)
                routing = self.resolve_blocked_routing(
                    stage_name=stage_name,
                    decision=stage_result.decision,
                    motivo=stage_result.motivo,
                )
                self._append_audit_event(
                    item_id=item_id,
                    stage=stage_name,
                    event="stage_blocked",
                    detail={
                        "decision": stage_result.decision,
                        "motivo": stage_result.motivo,
                        "elapsed_ms": stage_result.elapsed_ms,
                        "return_stage": routing.return_stage,
                        "reason_code": routing.reason_code,
                    },
                )
                self._save_checkpoint(
                    item_id=item_id,
                    next_stage_index=stage_idx,
                    progress=progress,
                    stage_outputs=stage_outputs,
                    status="AGUARDANDO_CORRECAO",
                )
                return {
                    "status": "AGUARDANDO_CORRECAO",
                    "blocked_stage": stage_name,
                    "return_stage": routing.return_stage,
                    "return_action": routing.action,
                    "return_reason_code": routing.reason_code,
                    "motivo": stage_result.motivo,
                    "progress": progress,
                }

            done_label = f"[STAGE {stage_idx + 1}/{total}] {stage_name} - CONCLUIDO"
            progress.append(done_label)
            self._append_audit_event(
                item_id=item_id,
                stage=stage_name,
                event="stage_completed",
                    detail={
                        "decision": stage_result.decision,
                        "elapsed_ms": stage_result.elapsed_ms,
                        "retry_attempts": attempt,
                    },
                )

        self._clear_checkpoint()
        return {
            "status": "CONCLUIDO",
            "blocked_stage": None,
            "motivo": "",
            "progress": progress,
            "stage_outputs": stage_outputs,
        }

    def _normalize_stage_result(
        self,
        *,
        stage_idx: int,
        total: int,
        stage_name: str,
        raw_result: Mapping[str, Any],
        elapsed_ms: int,
    ) -> StageExecution:
        decision = str(raw_result.get("decision", "OK")).strip().upper()
        handoff = raw_result.get("handoff", {})
        handoff_data = dict(handoff) if isinstance(handoff, Mapping) else {"value": handoff}
        motivo = str(raw_result.get("motivo", "")).strip()
        return StageExecution(
            index=stage_idx,
            total=total,
            name=stage_name,
            decision=decision,
            elapsed_ms=elapsed_ms,
            handoff=handoff_data,
            motivo=motivo,
        )

    def _load_checkpoint(self) -> dict[str, Any]:
        if not self._checkpoint_path.exists():
            raise ValueError("checkpoint_inexistente")
        loaded = json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("checkpoint_invalido")
        return dict(loaded)

    def _save_checkpoint(
        self,
        *,
        item_id: str,
        next_stage_index: int,
        progress: list[str],
        stage_outputs: Mapping[str, Any],
        status: str,
    ) -> None:
        payload = {
            "item_id": item_id,
            "next_stage_index": int(next_stage_index),
            "status": status,
            "updated_at": self._now_iso(),
            "progress": progress,
            "stage_outputs": dict(stage_outputs),
        }
        self._checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self._checkpoint_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def _clear_checkpoint(self) -> None:
        if self._checkpoint_path.exists():
            self._checkpoint_path.unlink()

    def _append_audit_event(
        self,
        *,
        item_id: str,
        stage: str,
        event: str,
        detail: Mapping[str, Any],
    ) -> None:
        if self._audit_log_path is None:
            return
        row = {
            "timestamp": self._now_iso(),
            "item_id": item_id,
            "stage": stage,
            "event": event,
            "detail": dict(detail),
        }
        self._audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._audit_log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=True) + "\n")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(tz=UTC).isoformat(timespec="seconds")

    @staticmethod
    def _resolve_retry_budget(*, stage_name: str, retry_budget_by_stage: Mapping[str, int] | None) -> int:
        if retry_budget_by_stage is None:
            return 0
        raw_budget = retry_budget_by_stage.get(stage_name, 0)
        if raw_budget <= 0:
            return 0
        return int(raw_budget)

    @staticmethod
    def resolve_blocked_routing(*, stage_name: str, decision: str, motivo: str) -> BlockedStageRouting:
        normalized_stage = stage_name.strip()
        normalized_decision = decision.strip().upper()
        normalized_motivo = motivo.strip().lower()

        if normalized_decision == "DEVOLVIDO_PARA_REVISAO":
            if normalized_stage == "Tech Lead":
                return BlockedStageRouting(
                    decision=normalized_decision,
                    action="RETORNAR_STAGE_ESPECIFICO",
                    return_stage="Software Engineer",
                    reason_code="tl_devolvido_para_se",
                )
            if normalized_stage == "Doc Advocate":
                return BlockedStageRouting(
                    decision=normalized_decision,
                    action="RETORNAR_STAGE_ESPECIFICO",
                    return_stage="Tech Lead",
                    reason_code="doc_devolvido_para_tl",
                )
            return BlockedStageRouting(
                decision=normalized_decision,
                action="REEXECUTAR_STAGE_ATUAL",
                return_stage=normalized_stage,
                reason_code="devolvido_reexecucao_mesmo_stage",
            )

        if normalized_decision == "DEVOLVER_PARA_AJUSTE":
            if normalized_stage == "Project Manager":
                if "doc" in normalized_motivo:
                    return BlockedStageRouting(
                        decision=normalized_decision,
                        action="RETORNAR_STAGE_ESPECIFICO",
                        return_stage="Doc Advocate",
                        reason_code="pm_ajuste_documentacao",
                    )
                if "teste" in normalized_motivo or "mypy" in normalized_motivo or "regress" in normalized_motivo:
                    return BlockedStageRouting(
                        decision=normalized_decision,
                        action="RETORNAR_STAGE_ESPECIFICO",
                        return_stage="Tech Lead",
                        reason_code="pm_ajuste_validacao_tecnica",
                    )
                return BlockedStageRouting(
                    decision=normalized_decision,
                    action="RETORNAR_STAGE_ESPECIFICO",
                    return_stage="Software Engineer",
                    reason_code="pm_ajuste_implementacao",
                )
            return BlockedStageRouting(
                decision=normalized_decision,
                action="REEXECUTAR_STAGE_ATUAL",
                return_stage=normalized_stage,
                reason_code="devolver_reexecucao_mesmo_stage",
            )

        return BlockedStageRouting(
            decision=normalized_decision,
            action="SEM_ROTEAMENTO",
            return_stage=normalized_stage,
            reason_code="decision_sem_bloqueio",
        )
