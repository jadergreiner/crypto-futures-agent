"""Live execution contracts and deterministic gate logic for Model 2.0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class LiveExecutionErrorContract:
    """Contrato de erro para live_execution com auditabilidade.

    Garante que toda falha/bloqueio é rastreável com contexto completo:
    - decision_id: identificador da decisão que levou ao bloqueio
    - execution_id: identificador único da tentativa de execução
    - reason_code: código canônico da razão (auditável)
    - severity: nível de severidade da falha
    - recommended_action: ação recomendada para recuperação/troubleshooting
    - additional_context: metadados adicionais para análise
    """

    decision_id: int | None
    execution_id: int | None
    reason_code: str
    severity: str
    recommended_action: str
    additional_context: Mapping[str, Any] | None = None

    def is_complete(self) -> bool:
        """Valida se contrato tem todos os campos obrigatórios preenchidos."""
        return bool(
            self.decision_id is not None
            and self.execution_id is not None
            and self.reason_code
            and len(self.reason_code) > 0
            and self.severity
            and len(self.severity) > 0
            and self.recommended_action
            and len(self.recommended_action) > 0
        )

    def validate_reason_code_in_catalog(self) -> bool:
        """Valida se reason_code existe no catálogo."""
        return self.reason_code in REASON_CODE_CATALOG

    def validate_severity(self) -> bool:
        """Valida se severity é um de [INFO, MEDIUM, HIGH, CRITICAL]."""
        valid_severities = {"INFO", "MEDIUM", "HIGH", "CRITICAL"}
        return self.severity in valid_severities

    def validate_action(self) -> bool:
        """Valida se recommended_action não está vazia."""
        return bool(self.recommended_action and len(self.recommended_action) > 0)


class _ReasonCode(str):
    """String retrocompativel com alias textual para auditoria."""

    __slots__ = ("_alias_value",)
    _alias_value: str

    def __new__(cls, raw_value: str, alias_value: str | None = None) -> "_ReasonCode":
        obj = str.__new__(cls, raw_value)
        object.__setattr__(obj, "_alias_value", alias_value or raw_value)
        return obj

    def __str__(self) -> str:
        return str(self._alias_value)

M2_009_1_RULE_ID = "M2-009.1-RULE-SIGNAL-EXECUTION-LIFECYCLE"
M2_009_2_RULE_ID = "M2-009.2-RULE-LIVE-GATE"
M2_009_3_RULE_ID = "M2-009.3-RULE-MARKET-ENTRY"
M2_009_4_RULE_ID = "M2-009.4-RULE-PROTECTION-FAILSAFE"
M2_010_1_RULE_ID = "M2-010.1-RULE-LIVE-RECONCILE"

# Catalogo canônico de reason codes para hardening operacional M2-024.
# Mínimo 20 entries para cobertura adequada de casos operacionais.
REASON_CODE_CATALOG: dict[str, str] = {
    "ready_for_live_execution": "ops.ready_for_live_execution",
    "ops_ambiguous_state": "ops.ambiguous_state",
    "status_not_consumed": "ops.status_not_consumed",
    "risk_gate_blocked": "ops.risk_gate_blocked",
    "circuit_breaker_blocked": "ops.circuit_breaker_blocked",
    "signal_expired": "ops.signal_expired",
    "insufficient_balance": "ops.insufficient_balance",
    "timeout": "ops.timeout",
    "reconciliation_divergence": "ops.reconciliation_divergence",
    # Expansão M2-024.2: 11+ entries adicionais
    "entrada_validada": "ops.entrada_validada",
    "ordem_enviada": "ops.ordem_enviada",
    "ordem_confirmada": "ops.ordem_confirmada",
    "ordem_rejeitada": "ops.ordem_rejeitada",
    "protecao_armada": "ops.protecao_armada",
    "protecao_falhou": "ops.protecao_falhou",
    "posicao_aumentada": "ops.posicao_aumentada",
    "posicao_reduzida": "ops.posicao_reduzida",
    "posicao_fechada": "ops.posicao_fechada",
    "saida_forcada": "ops.saida_forcada",
    "reconciliacao_ok": "ops.reconciliacao_ok",
    "reconciliacao_pendente": "ops.reconciliacao_pendente",
    "decision_id_duplicado": "ops.decision_id_duplicado",
    # Codes do order_layer (unificados M2-024.2)
    "decision_recorded_no_real_order": "ops.decision_recorded_no_real_order",
    "status_not_created": "ops.status_not_created",
    "missing_decision_id": "ops.missing_decision_id",
    "missing_signal_timestamp": "ops.missing_signal_timestamp",
    "missing_payload_contract": "ops.missing_payload_contract",
    "symbol_not_authorized": "ops.symbol_not_authorized",
    "unsupported_signal_side": "ops.unsupported_signal_side",
    "short_only_enforced": "ops.short_only_enforced",
    "unsupported_entry_type": "ops.unsupported_entry_type",
    "invalid_price_geometry": "ops.invalid_price_geometry",
    # M2-026.1: Observabilidade de risk_gate
    "SIZE_EXCEEDS_LIMIT": "ops.size_exceeds_limit",
    "STOP_LOSS_TOO_LOOSE": "ops.stop_loss_too_loose",
    # M2-027.3: Posicoes orfas detectadas sem signal_execution correspondente
    "orphan_position": "ops.orphan_position",
    # M2-024.5: Timeout por etapa de execucao
    "TIMEOUT_ADMISSION": "ops.timeout_admission",
    "TIMEOUT_SEND": "ops.timeout_send",
    "TIMEOUT_RECONCILIATION": "ops.timeout_reconciliation",
    # M2-028.4: Drawdown diario como gate de admissao
    "daily_drawdown_limit": "ops.daily_drawdown_limit",
}

REASON_CODE_SEVERITY: dict[str, str] = {
    "ready_for_live_execution": "INFO",
    "ops_ambiguous_state": "HIGH",
    "status_not_consumed": "HIGH",
    "risk_gate_blocked": "HIGH",
    "circuit_breaker_blocked": "HIGH",
    "signal_expired": "MEDIUM",
    "insufficient_balance": "MEDIUM",
    "timeout": "HIGH",
    "reconciliation_divergence": "CRITICAL",
    # Expansão M2-024.2
    "entrada_validada": "INFO",
    "ordem_enviada": "INFO",
    "ordem_confirmada": "INFO",
    "ordem_rejeitada": "HIGH",
    "protecao_armada": "INFO",
    "protecao_falhou": "HIGH",
    "posicao_aumentada": "INFO",
    "posicao_reduzida": "INFO",
    "posicao_fechada": "INFO",
    "saida_forcada": "HIGH",
    "reconciliacao_ok": "INFO",
    "reconciliacao_pendente": "MEDIUM",
    "decision_id_duplicado": "HIGH",
    # Codes do order_layer (unificados M2-024.2)
    "decision_recorded_no_real_order": "INFO",
    "status_not_created": "HIGH",
    "missing_decision_id": "HIGH",
    "missing_signal_timestamp": "HIGH",
    "missing_payload_contract": "HIGH",
    "symbol_not_authorized": "MEDIUM",
    "unsupported_signal_side": "HIGH",
    "short_only_enforced": "INFO",
    "unsupported_entry_type": "HIGH",
    "invalid_price_geometry": "HIGH",
    # M2-026.1: Observabilidade de risk_gate
    "SIZE_EXCEEDS_LIMIT": "HIGH",
    "STOP_LOSS_TOO_LOOSE": "HIGH",
    # M2-024.5: Timeout por etapa de execucao
    "TIMEOUT_ADMISSION": "HIGH",
    "TIMEOUT_SEND": "HIGH",
    "TIMEOUT_RECONCILIATION": "HIGH",
    "daily_drawdown_limit": "HIGH",
}

REASON_CODE_ACTION: dict[str, str] = {
    "ready_for_live_execution": "seguir_fluxo",
    "ops_ambiguous_state": "bloquear_operacao",
    "status_not_consumed": "bloquear_operacao",
    "risk_gate_blocked": "bloquear_operacao",
    "circuit_breaker_blocked": "bloquear_operacao",
    "signal_expired": "descartar_sinal",
    "insufficient_balance": "ajustar_margem_ou_aguardar",
    "timeout": "aplicar_retry_controlado",
    "reconciliation_divergence": "interromper_e_reconciliar",
    # Expansão M2-024.2
    "entrada_validada": "continuar_fluxo",
    "ordem_enviada": "monitorar_preenchimento",
    "ordem_confirmada": "armar_protecoes",
    "ordem_rejeitada": "descartar_e_registrar",
    "protecao_armada": "monitorar_execucao",
    "protecao_falhou": "bloquear_operacao",
    "posicao_aumentada": "ajustar_protecao",
    "posicao_reduzida": "monitorar_saldo",
    "posicao_fechada": "registrar_resultado",
    "saida_forcada": "reconciliar_posicao",
    "reconciliacao_ok": "continuar_monitorando",
    "reconciliacao_pendente": "retentativas_reconciliacao",
    "decision_id_duplicado": "bloquear_operacao",
    # Codes do order_layer (unificados M2-024.2)
    "decision_recorded_no_real_order": "registrar_sem_ordem_real",
    "status_not_created": "bloquear_operacao",
    "missing_decision_id": "bloquear_operacao",
    "missing_signal_timestamp": "bloquear_operacao",
    "missing_payload_contract": "bloquear_operacao",
    "symbol_not_authorized": "descartar_sinal",
    "unsupported_signal_side": "bloquear_operacao",
    "short_only_enforced": "descartar_sinal",
    "unsupported_entry_type": "bloquear_operacao",
    "invalid_price_geometry": "bloquear_operacao",
    # M2-026.1: Observabilidade de risk_gate
    "SIZE_EXCEEDS_LIMIT": "bloquear_operacao",
    "STOP_LOSS_TOO_LOOSE": "bloquear_operacao",
    # M2-024.5: Timeout por etapa de execucao
    "TIMEOUT_ADMISSION": "bloquear_operacao",
    "TIMEOUT_SEND": "bloquear_operacao",
    "TIMEOUT_RECONCILIATION": "bloquear_operacao",
    "daily_drawdown_limit": "bloquear_operacao",
}

TECHNICAL_SIGNAL_STATUS_CONSUMED = "CONSUMED"
ENTRY_ORDER_TYPE_MARKET = "MARKET"

SIGNAL_EXECUTION_STATUS_READY = "READY"
SIGNAL_EXECUTION_STATUS_BLOCKED = "BLOCKED"
SIGNAL_EXECUTION_STATUS_ENTRY_SENT = "ENTRY_SENT"
SIGNAL_EXECUTION_STATUS_ENTRY_FILLED = "ENTRY_FILLED"
SIGNAL_EXECUTION_STATUS_PROTECTED = "PROTECTED"
SIGNAL_EXECUTION_STATUS_EXITED = "EXITED"
SIGNAL_EXECUTION_STATUS_FAILED = "FAILED"
SIGNAL_EXECUTION_STATUS_CANCELLED = "CANCELLED"

OFFICIAL_SIGNAL_EXECUTION_STATUSES = (
    SIGNAL_EXECUTION_STATUS_READY,
    SIGNAL_EXECUTION_STATUS_BLOCKED,
    SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
    SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
    SIGNAL_EXECUTION_STATUS_PROTECTED,
    SIGNAL_EXECUTION_STATUS_EXITED,
    SIGNAL_EXECUTION_STATUS_FAILED,
    SIGNAL_EXECUTION_STATUS_CANCELLED,
)
FINAL_SIGNAL_EXECUTION_STATUSES = frozenset(
    {
        SIGNAL_EXECUTION_STATUS_BLOCKED,
        SIGNAL_EXECUTION_STATUS_EXITED,
        SIGNAL_EXECUTION_STATUS_FAILED,
        SIGNAL_EXECUTION_STATUS_CANCELLED,
    }
)
ACTIVE_SIGNAL_EXECUTION_STATUSES = frozenset(
    {
        SIGNAL_EXECUTION_STATUS_READY,
        SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
        SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
        SIGNAL_EXECUTION_STATUS_PROTECTED,
    }
)
ALLOWED_SIGNAL_EXECUTION_TRANSITIONS: dict[str | None, frozenset[str]] = {
    None: frozenset(
        {
            SIGNAL_EXECUTION_STATUS_READY,
            SIGNAL_EXECUTION_STATUS_BLOCKED,
        }
    ),
    SIGNAL_EXECUTION_STATUS_READY: frozenset(
        {
            SIGNAL_EXECUTION_STATUS_ENTRY_SENT,
            SIGNAL_EXECUTION_STATUS_FAILED,
            SIGNAL_EXECUTION_STATUS_CANCELLED,
        }
    ),
    SIGNAL_EXECUTION_STATUS_ENTRY_SENT: frozenset(
        {
            SIGNAL_EXECUTION_STATUS_ENTRY_FILLED,
            SIGNAL_EXECUTION_STATUS_FAILED,
            SIGNAL_EXECUTION_STATUS_CANCELLED,
        }
    ),
    SIGNAL_EXECUTION_STATUS_ENTRY_FILLED: frozenset(
        {
            SIGNAL_EXECUTION_STATUS_PROTECTED,
            SIGNAL_EXECUTION_STATUS_EXITED,
            SIGNAL_EXECUTION_STATUS_FAILED,
        }
    ),
    SIGNAL_EXECUTION_STATUS_PROTECTED: frozenset(
        {
            SIGNAL_EXECUTION_STATUS_EXITED,
            SIGNAL_EXECUTION_STATUS_FAILED,
        }
    ),
    SIGNAL_EXECUTION_STATUS_BLOCKED: frozenset(),
    SIGNAL_EXECUTION_STATUS_EXITED: frozenset(),
    SIGNAL_EXECUTION_STATUS_FAILED: frozenset(),
    SIGNAL_EXECUTION_STATUS_CANCELLED: frozenset(),
}


def is_valid_signal_execution_transition(from_status: str | None, to_status: str) -> bool:
    """Return whether a signal execution transition is allowed."""

    allowed = ALLOWED_SIGNAL_EXECUTION_TRANSITIONS.get(from_status)
    if allowed is None:
        return False
    return to_status in allowed


@dataclass(frozen=True)
class LiveExecutionConfig:
    """Static runtime configuration for live/shadow execution."""

    execution_mode: str
    live_symbols: tuple[str, ...]
    authorized_symbols: tuple[str, ...]
    short_only: bool
    max_daily_entries: int
    max_margin_per_position_usd: float
    max_signal_age_ms: int
    symbol_cooldown_ms: int
    funding_rate_max_for_short: float
    leverage: int


@dataclass(frozen=True)
class LiveExecutionGateInput:
    """Inputs required to decide if a technical signal may enter live execution."""

    technical_signal_id: int
    opportunity_id: int
    symbol: str
    timeframe: str
    signal_side: str
    technical_signal_status: str
    signal_timestamp: int
    short_only: bool
    funding_rate: float | None
    basis_value: float | None
    funding_rate_max_for_short: float
    execution_mode: str
    live_symbols: tuple[str, ...]
    authorized_symbols: tuple[str, ...]
    available_balance_usd: float | None
    max_margin_per_position_usd: float
    recent_entries_today: int
    max_daily_entries: int
    symbol_active_execution_count: int
    open_position_qty: float
    cooldown_active: bool
    signal_age_ms: int
    max_signal_age_ms: int
    risk_gate_status: str
    risk_gate_allows_order: bool
    risk_gate_drawdown_pct: float | None
    circuit_breaker_state: str
    circuit_breaker_allows_trading: bool
    circuit_breaker_drawdown_pct: float | None
    decision_id: int | None = None
    execution_id: int | None = None


@dataclass(frozen=True)
class LiveExecutionGateDecision:
    """Decision emitted by the deterministic live gate."""

    allow_execution: bool
    target_status: str
    reason: str
    rule_id: str
    details: Mapping[str, Any]


def _blocked(reason: str, **details: Any) -> LiveExecutionGateDecision:
    alias = REASON_CODE_CATALOG.get(reason)
    detail_payload: dict[str, Any] = dict(details)
    detail_payload.setdefault("reason_code", reason)
    detail_payload.setdefault("severity", REASON_CODE_SEVERITY.get(reason, "HIGH"))
    detail_payload.setdefault(
        "recommended_action",
        REASON_CODE_ACTION.get(reason, "bloquear_operacao"),
    )
    detail_payload.setdefault("decision_id", details.get("decision_id"))
    detail_payload.setdefault("execution_id", details.get("execution_id"))
    return LiveExecutionGateDecision(
        allow_execution=False,
        target_status=SIGNAL_EXECUTION_STATUS_BLOCKED,
        reason=_ReasonCode(reason, alias),
        rule_id=M2_009_2_RULE_ID,
        details=detail_payload,
    )


def evaluate_live_execution_gate(gate_input: LiveExecutionGateInput) -> LiveExecutionGateDecision:
    """Evaluate whether a CONSUMED technical signal can enter live execution."""

    execution_mode = str(gate_input.execution_mode).strip().lower()
    if execution_mode not in {"shadow", "live"}:
        return _blocked(
            "unsupported_execution_mode",
            execution_mode=gate_input.execution_mode,
        )

    if gate_input.technical_signal_status != TECHNICAL_SIGNAL_STATUS_CONSUMED:
        return _blocked(
            "status_not_consumed",
            current_status=gate_input.technical_signal_status,
            decision_id=gate_input.decision_id,
            execution_id=gate_input.execution_id,
        )

    strict_contract = gate_input.decision_id is not None or gate_input.execution_id is not None
    if strict_contract and (gate_input.decision_id is None or int(gate_input.decision_id) <= 0):
        return _blocked(
            "ops_ambiguous_state",
            decision_id=gate_input.decision_id,
            execution_id=gate_input.execution_id,
        )

    if strict_contract and (gate_input.execution_id is None or int(gate_input.execution_id) <= 0):
        return _blocked(
            "ops_ambiguous_state",
            decision_id=gate_input.decision_id,
            execution_id=gate_input.execution_id,
        )

    risk_gate_status = str(gate_input.risk_gate_status).strip().lower()
    if risk_gate_status in {"", "unknown", "unavailable"}:
        if not bool(gate_input.risk_gate_allows_order):
            return _blocked(
                "ops_ambiguous_state",
                risk_gate_status=gate_input.risk_gate_status,
                risk_gate_drawdown_pct=gate_input.risk_gate_drawdown_pct,
            )
        return _blocked(
            "risk_gate_state_unavailable",
            risk_gate_status=gate_input.risk_gate_status,
            risk_gate_drawdown_pct=gate_input.risk_gate_drawdown_pct,
        )

    if not bool(gate_input.risk_gate_allows_order):
        return _blocked(
            "risk_gate_blocked",
            risk_gate_status=gate_input.risk_gate_status,
            risk_gate_drawdown_pct=gate_input.risk_gate_drawdown_pct,
            decision_id=gate_input.decision_id,
            execution_id=gate_input.execution_id,
        )

    circuit_breaker_state = str(gate_input.circuit_breaker_state).strip().lower()
    if circuit_breaker_state in {"", "unknown", "unavailable"}:
        return _blocked(
            "circuit_breaker_state_unavailable",
            circuit_breaker_state=gate_input.circuit_breaker_state,
            circuit_breaker_drawdown_pct=gate_input.circuit_breaker_drawdown_pct,
        )

    if not bool(gate_input.circuit_breaker_allows_trading):
        return _blocked(
            "circuit_breaker_blocked",
            circuit_breaker_state=gate_input.circuit_breaker_state,
            circuit_breaker_drawdown_pct=gate_input.circuit_breaker_drawdown_pct,
            decision_id=gate_input.decision_id,
            execution_id=gate_input.execution_id,
        )

    if gate_input.signal_side not in {"LONG", "SHORT"}:
        return _blocked(
            "unsupported_signal_side",
            signal_side=gate_input.signal_side,
        )

    if bool(gate_input.short_only) and gate_input.signal_side != "SHORT":
        return _blocked(
            "short_only_enforced",
            signal_side=gate_input.signal_side,
        )

    authorized_symbols = {symbol.upper() for symbol in gate_input.authorized_symbols}
    if authorized_symbols and gate_input.symbol.upper() not in authorized_symbols:
        return _blocked(
            "symbol_not_authorized",
            symbol=gate_input.symbol,
        )

    live_symbols = {symbol.upper() for symbol in gate_input.live_symbols}
    if live_symbols and gate_input.symbol.upper() not in live_symbols:
        return _blocked(
            "symbol_not_enabled",
            symbol=gate_input.symbol,
        )

    if gate_input.signal_age_ms > gate_input.max_signal_age_ms:
        return _blocked(
            "signal_expired",
            signal_age_ms=int(gate_input.signal_age_ms),
            max_signal_age_ms=int(gate_input.max_signal_age_ms),
        )

    if gate_input.symbol_active_execution_count > 0:
        return _blocked(
            "active_execution_exists",
            symbol=gate_input.symbol,
            active_count=int(gate_input.symbol_active_execution_count),
        )

    if gate_input.open_position_qty > 0:
        return _blocked(
            "open_position_exists",
            symbol=gate_input.symbol,
            open_position_qty=float(gate_input.open_position_qty),
        )

    if gate_input.cooldown_active:
        return _blocked(
            "symbol_in_cooldown",
            symbol=gate_input.symbol,
        )

    # NOTE: Daily entry limit removido em 2026-03-21 para permitir aprendizagem
    # do modelo em mercado real. Foco agora e evolucao e captura de episodios.

    if gate_input.max_margin_per_position_usd <= 0:
        return _blocked(
            "invalid_margin_limit",
            max_margin_per_position_usd=float(gate_input.max_margin_per_position_usd),
        )

    if gate_input.signal_side == "SHORT":
        if gate_input.funding_rate is not None and gate_input.funding_rate > gate_input.funding_rate_max_for_short:
            return _blocked(
                "funding_unfavorable",
                funding_rate=float(gate_input.funding_rate),
                threshold=float(gate_input.funding_rate_max_for_short),
            )
        if gate_input.basis_value is not None and gate_input.basis_value < 0:
            return _blocked(
                "negative_basis",
                basis_value=float(gate_input.basis_value),
            )

    if execution_mode == "live":
        if gate_input.available_balance_usd is None:
            return _blocked("balance_unavailable")
        if gate_input.available_balance_usd < gate_input.max_margin_per_position_usd:
            return _blocked(
                "insufficient_balance",
                available_balance_usd=float(gate_input.available_balance_usd),
                required_margin_usd=float(gate_input.max_margin_per_position_usd),
            )

    return LiveExecutionGateDecision(
        allow_execution=True,
        target_status=SIGNAL_EXECUTION_STATUS_READY,
        reason=_ReasonCode(
            "ready_for_live_execution",
            REASON_CODE_CATALOG.get("ready_for_live_execution"),
        ),
        rule_id=M2_009_2_RULE_ID,
        details={
            "reason_code": "ready_for_live_execution",
            "severity": REASON_CODE_SEVERITY.get("ready_for_live_execution", "INFO"),
            "recommended_action": REASON_CODE_ACTION.get("ready_for_live_execution", "seguir_fluxo"),
            "decision_id": gate_input.decision_id,
            "execution_id": gate_input.execution_id,
            "execution_mode": execution_mode,
            "max_margin_per_position_usd": float(gate_input.max_margin_per_position_usd),
            "recent_entries_today": int(gate_input.recent_entries_today),
            "signal_age_ms": int(gate_input.signal_age_ms),
        },
    )
