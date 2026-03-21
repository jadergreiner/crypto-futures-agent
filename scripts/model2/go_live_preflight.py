"""Go-live preflight runner for Model 2.0 Phase 2."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import (
    M2_CANARY_DB_PATH,
    M2_CANARY_LEVERAGE,
    M2_LIVE_SYMBOLS,
    M2_FUNDING_RATE_MAX_FOR_SHORT,
    M2_MAX_DAILY_ENTRIES,
    M2_MAX_MARGIN_PER_POSITION_USD,
    M2_MAX_SIGNAL_AGE_MINUTES,
    M2_SHORT_ONLY,
    M2_SYMBOL_COOLDOWN_MINUTES,
    MODEL2_DB_PATH,
)
from scripts.model2.healthcheck_live_execution import run_live_healthcheck
from scripts.model2.live_dashboard import run_live_dashboard
from scripts.model2.live_execute import run_live_execute
from scripts.model2.live_reconcile import run_live_reconcile
from scripts.model2.migrate import run_up
from scripts.model2.io_utils import atomic_write_json

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
RUNBOOK_PATH = REPO_ROOT / "docs" / "RUNBOOK_M2_OPERACAO.md"
ENV_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


class _NoopExchange:
    def get_available_balance(self) -> float | None:
        return None

    def get_open_position(self, symbol: str) -> dict[str, Any] | None:
        return None

    def get_protection_state(self, *, symbol: str, signal_side: str) -> dict[str, Any]:
        return {
            "has_sl": True,
            "has_tp": True,
            "sl_order_id": None,
            "tp_order_id": None,
        }

    def place_protective_order(self, *, symbol: str, signal_side: str, trigger_price: float, order_type: str) -> dict[str, Any]:
        return {"algoId": None}

    @staticmethod
    def extract_order_identifier(order: dict[str, Any]) -> str | None:
        return None

    @staticmethod
    def is_existing_protection_error(error: Exception) -> bool:
        return False

    def close_position_market(self, *, symbol: str, signal_side: str, quantity: float) -> dict[str, Any]:
        return {"orderId": None, "executedQty": str(quantity)}


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _normalize_live_symbols(symbols: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(symbol.strip().upper() for symbol in symbols if symbol and symbol.strip())


def _load_env_values(env_file: Path) -> dict[str, str]:
    if not env_file.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        match = ENV_PATTERN.match(raw_line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        values[key] = value
    return values


def _update_env_file(env_file: Path, updates: dict[str, str]) -> dict[str, Any]:
    env_file.parent.mkdir(parents=True, exist_ok=True)
    original_text = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
    backup_file = env_file.with_suffix(env_file.suffix + ".bak")
    backup_file.write_text(original_text, encoding="utf-8")

    lines = original_text.splitlines()
    changed: list[str] = []
    seen: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        match = ENV_PATTERN.match(line)
        if not match:
            new_lines.append(line)
            continue
        key = match.group(1).strip()
        if key in updates:
            new_value = str(updates[key])
            new_line = f"{key}={new_value}"
            if line != new_line:
                changed.append(key)
            new_lines.append(new_line)
            seen.add(key)
            continue
        new_lines.append(line)

    for key, value in updates.items():
        if key in seen:
            continue
        changed.append(key)
        new_lines.append(f"{key}={value}")

    output_text = "\n".join(new_lines).strip("\n")
    if output_text:
        output_text += "\n"
    env_file.write_text(output_text, encoding="utf-8")
    return {
        "env_file": str(env_file),
        "backup_file": str(backup_file),
        "updated_keys": sorted(set(changed)),
    }


def _probe_db_write_access(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("CREATE TABLE IF NOT EXISTS __perm_test(id INTEGER)")
        conn.execute("DROP TABLE __perm_test")
        conn.execute("COMMIT")


def _has_minimum_live_schema(db_path: Path) -> bool:
    if not db_path.exists():
        return False
    required_tables = {
        "schema_migrations",
        "technical_signals",
        "signal_executions",
        "signal_execution_events",
        "signal_execution_snapshots",
    }
    with sqlite3.connect(db_path) as conn:
        found = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
    return required_tables.issubset(found)


def _to_positive_int(value: str, default: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        return int(default)
    return int(default) if parsed <= 0 else parsed


def _to_positive_float(value: str, default: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        return float(default)
    return float(default) if parsed <= 0 else parsed


def _run_acl_fix(command_runner: Callable[..., subprocess.CompletedProcess[str]]) -> subprocess.CompletedProcess[str]:
    return command_runner(
        ["cmd", "/c", "icacls db /grant %USERNAME%:(OI)(CI)M /T"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def _default_command_runner(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(*args, **kwargs)


def _check_guardrails_functional() -> dict[str, Any]:
    """Verifica que RiskGate e CircuitBreaker podem ser instanciados e estao funcionais.

    Retorna dict com 'ok' (bool) e 'details' (dict com evidencias por guard-rail).
    Falha explicita se qualquer guard-rail nao puder ser importado ou instanciado.
    """
    details: dict[str, Any] = {}
    try:
        from risk.risk_gate import RiskGate

        rg = RiskGate()
        can_order = rg.can_execute_order("market")
        metrics = rg.get_risk_metrics()
        details["risk_gate"] = {
            "instantiated": True,
            "can_execute_order": bool(can_order),
            "status": str(rg.status.value),
            "drawdown_pct": float(metrics.drawdown_pct),
        }
    except Exception as exc:
        details["risk_gate"] = {"instantiated": False, "error": str(exc)}

    try:
        from risk.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker()
        can_trade = cb.can_trade()
        status = cb.check_status()
        details["circuit_breaker"] = {
            "instantiated": True,
            "can_trade": bool(can_trade),
            "state": str(cb.state.value),
            "trading_allowed": bool(status.get("trading_allowed", can_trade)),
        }
    except Exception as exc:
        details["circuit_breaker"] = {"instantiated": False, "error": str(exc)}

    rg_ok = bool(details.get("risk_gate", {}).get("instantiated"))
    cb_ok = bool(details.get("circuit_breaker", {}).get("instantiated"))
    return {"ok": rg_ok and cb_ok, "details": details}


def run_go_live_preflight(
    *,
    model2_db_path: str | Path,
    output_dir: str | Path,
    env_file: str | Path,
    apply_fixes: bool,
    continue_on_error: bool,
    live_symbols: tuple[str, ...],
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = _default_command_runner,
    db_write_probe: Callable[[Path], None] = _probe_db_write_access,
    migrate_fn: Callable[..., dict[str, Any]] = run_up,
    live_execute_fn: Callable[..., dict[str, Any]] = run_live_execute,
    live_reconcile_fn: Callable[..., dict[str, Any]] = run_live_reconcile,
    live_dashboard_fn: Callable[..., dict[str, Any]] = run_live_dashboard,
    live_healthcheck_fn: Callable[..., dict[str, Any]] = run_live_healthcheck,
) -> dict[str, Any]:
    resolved_db = _resolve_repo_path(model2_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)
    resolved_env_file = _resolve_repo_path(env_file)
    selected_symbols = _normalize_live_symbols(live_symbols)
    applied_fixes: list[dict[str, Any]] = []
    next_actions: list[str] = []
    checks: list[dict[str, Any]] = []
    should_stop = False

    def add_check(
        *,
        check_id: str,
        description: str,
        status: str,
        actions: list[str] | None = None,
        evidence: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        nonlocal should_stop
        checks.append(
            {
                "id": check_id,
                "description": description,
                "status": status,
                "actions": actions or [],
                "evidence": evidence or {},
                "error": error,
            }
        )
        if status != "ok" and not continue_on_error:
            should_stop = True

    add_check(
        check_id="1",
        description="Confirmar MODEL2_DB_PATH operacional e path resolvido.",
        status="ok" if str(model2_db_path).strip() else "alert",
        evidence={
            "configured_model2_db_path": str(model2_db_path),
            "resolved_model2_db_path": str(resolved_db),
        },
        error=None if str(model2_db_path).strip() else "MODEL2_DB_PATH is empty.",
    )

    if not should_stop:
        write_actions = [
            "python -c \"import sqlite3; from config.settings import MODEL2_DB_PATH as p; c=sqlite3.connect(p); c.execute('BEGIN IMMEDIATE'); c.execute('CREATE TABLE IF NOT EXISTS __perm_test(id INTEGER)'); c.execute('DROP TABLE __perm_test'); c.execute('COMMIT'); c.close(); print('ok', p)\""
        ]
        try:
            db_write_probe(resolved_db)
            add_check(
                check_id="2",
                description="Validar permissao de escrita no banco operacional.",
                status="ok",
                actions=write_actions,
                evidence={"write_check": "ok", "model2_db_path": str(resolved_db)},
            )
        except Exception as exc:
            if apply_fixes:
                acl_cmd = 'cmd /c "icacls db /grant %USERNAME%:(OI)(CI)M /T"'
                fix_result = _run_acl_fix(command_runner)
                applied_fixes.append(
                    {
                        "type": "windows_acl_fix",
                        "command": acl_cmd,
                        "return_code": int(fix_result.returncode),
                        "stdout_tail": (fix_result.stdout or "")[-500:],
                        "stderr_tail": (fix_result.stderr or "")[-500:],
                    }
                )
                if fix_result.returncode == 0:
                    try:
                        db_write_probe(resolved_db)
                        add_check(
                            check_id="2",
                            description="Validar permissao de escrita no banco operacional.",
                            status="ok",
                            actions=write_actions + [acl_cmd],
                            evidence={"write_check": "ok_after_acl_fix", "model2_db_path": str(resolved_db)},
                        )
                    except Exception as second_exc:
                        add_check(
                            check_id="2",
                            description="Validar permissao de escrita no banco operacional.",
                            status="alert",
                            actions=write_actions + [acl_cmd],
                            evidence={"write_check": "failed_after_acl_fix", "model2_db_path": str(resolved_db)},
                            error=str(second_exc),
                        )
                else:
                    add_check(
                        check_id="2",
                        description="Validar permissao de escrita no banco operacional.",
                        status="alert",
                        actions=write_actions + [acl_cmd],
                        evidence={"write_check": "acl_fix_failed", "model2_db_path": str(resolved_db)},
                        error=str(exc),
                    )
            else:
                add_check(
                    check_id="2",
                    description="Validar permissao de escrita no banco operacional.",
                    status="alert",
                    actions=write_actions,
                    evidence={"write_check": "failed", "model2_db_path": str(resolved_db)},
                    error=str(exc),
                )

    if should_stop:
        for step in ("3", "4", "5", "6", "7", "8", "9", "10"):
            add_check(
                check_id=step,
                description="Checklist interrompido por fail-fast.",
                status="skipped",
            )
    else:
        if apply_fixes:
            migrate_action = f"python scripts/model2/migrate.py up --db-path {resolved_db}"
            try:
                migrate_summary = migrate_fn(db_path=resolved_db, output_dir=resolved_output_dir)
                applied_fixes.append(
                    {
                        "type": "migrate_up",
                        "command": migrate_action,
                        "status": migrate_summary.get("status"),
                        "output_file": migrate_summary.get("output_file"),
                    }
                )
                add_check(
                    check_id="3",
                    description="Executar migrate.py up no banco operacional.",
                    status="ok" if migrate_summary.get("status") == "ok" else "alert",
                    actions=[migrate_action],
                    evidence={"migration_summary": migrate_summary},
                    error=None if migrate_summary.get("status") == "ok" else "Migration returned non-ok status.",
                )
            except Exception as exc:
                add_check(
                    check_id="3",
                    description="Executar migrate.py up no banco operacional.",
                    status="alert",
                    actions=[migrate_action],
                    error=str(exc),
                )
        else:
            has_schema = _has_minimum_live_schema(resolved_db)
            add_check(
                check_id="3",
                description="Validar schema esperado para operacao live.",
                status="ok" if has_schema else "alert",
                actions=["validate required tables in sqlite_master"],
                evidence={"has_minimum_live_schema": has_schema, "model2_db_path": str(resolved_db)},
                error=None if has_schema else "Missing required tables. Run migrate.py up.",
            )

        env_values = _load_env_values(resolved_env_file)
        env_updates: dict[str, str] = {}
        chosen_symbols = selected_symbols or _normalize_live_symbols(tuple(env_values.get("M2_LIVE_SYMBOLS", "").split(",")))
        if env_values.get("M2_EXECUTION_MODE", "").strip().lower() != "shadow":
            env_updates["M2_EXECUTION_MODE"] = "shadow"

        if chosen_symbols:
            env_updates["M2_LIVE_SYMBOLS"] = ",".join(chosen_symbols)
        else:
            next_actions.append("Set explicit M2_LIVE_SYMBOLS subset before switching to live mode.")

        max_daily_entries = _to_positive_int(env_values.get("M2_MAX_DAILY_ENTRIES", ""), M2_MAX_DAILY_ENTRIES)
        max_margin = _to_positive_float(env_values.get("M2_MAX_MARGIN_PER_POSITION_USD", ""), M2_MAX_MARGIN_PER_POSITION_USD)
        max_age = _to_positive_int(env_values.get("M2_MAX_SIGNAL_AGE_MINUTES", ""), M2_MAX_SIGNAL_AGE_MINUTES)
        cooldown = _to_positive_int(env_values.get("M2_SYMBOL_COOLDOWN_MINUTES", ""), M2_SYMBOL_COOLDOWN_MINUTES)
        env_updates["M2_MAX_DAILY_ENTRIES"] = str(max_daily_entries)
        env_updates["M2_MAX_MARGIN_PER_POSITION_USD"] = str(max_margin)
        env_updates["M2_MAX_SIGNAL_AGE_MINUTES"] = str(max_age)
        env_updates["M2_SYMBOL_COOLDOWN_MINUTES"] = str(cooldown)
        env_updates["M2_SHORT_ONLY"] = "true" if M2_SHORT_ONLY else "false"
        env_updates["M2_CANARY_DB_PATH"] = str(M2_CANARY_DB_PATH)
        env_updates["M2_CANARY_LEVERAGE"] = str(M2_CANARY_LEVERAGE)
        env_updates["M2_FUNDING_RATE_MAX_FOR_SHORT"] = str(M2_FUNDING_RATE_MAX_FOR_SHORT)

        if apply_fixes:
            env_fix_info = _update_env_file(resolved_env_file, env_updates)
            applied_fixes.append(
                {
                    "type": "env_update",
                    "env_file": env_fix_info["env_file"],
                    "backup_file": env_fix_info["backup_file"],
                    "updated_keys": env_fix_info["updated_keys"],
                }
            )
            env_values = _load_env_values(resolved_env_file)
        else:
            for key, desired in env_updates.items():
                current = env_values.get(key)
                if current != desired:
                    next_actions.append(f"Set {key}={desired} in {resolved_env_file}.")

        execution_mode_ok = env_values.get("M2_EXECUTION_MODE", "").strip().lower() == "shadow"
        add_check(
            check_id="4",
            description="Validar M2_EXECUTION_MODE=shadow.",
            status="ok" if execution_mode_ok else "alert",
            evidence={"M2_EXECUTION_MODE": env_values.get("M2_EXECUTION_MODE", "")},
            error=None if execution_mode_ok else "M2_EXECUTION_MODE is not shadow.",
        )

        explicit_symbols = _normalize_live_symbols(tuple((env_values.get("M2_LIVE_SYMBOLS", "") or "").split(",")))
        symbols_ok = len(explicit_symbols) > 0
        add_check(
            check_id="5",
            description="Validar M2_LIVE_SYMBOLS com subset explicito.",
            status="ok" if symbols_ok else "alert",
            evidence={"M2_LIVE_SYMBOLS": list(explicit_symbols)},
            error=None if symbols_ok else "M2_LIVE_SYMBOLS is empty.",
        )

        risk_ok = all(
            (
                _to_positive_int(env_values.get("M2_MAX_DAILY_ENTRIES", ""), -1) > 0,
                _to_positive_float(env_values.get("M2_MAX_MARGIN_PER_POSITION_USD", ""), -1.0) > 0,
                _to_positive_int(env_values.get("M2_MAX_SIGNAL_AGE_MINUTES", ""), -1) > 0,
                _to_positive_int(env_values.get("M2_SYMBOL_COOLDOWN_MINUTES", ""), -1) > 0,
                _to_positive_int(env_values.get("M2_CANARY_LEVERAGE", ""), -1) > 0,
                _to_positive_float(env_values.get("M2_FUNDING_RATE_MAX_FOR_SHORT", ""), -1.0) > 0,
            )
        )
        # Verificar que guard-rails podem ser instanciados e estao funcionais (M2-020.5)
        guardrails_check = _check_guardrails_functional()
        guardrails_ok = bool(guardrails_check["ok"])
        check6_ok = risk_ok and guardrails_ok
        add_check(
            check_id="6",
            description="Validar limites de risco e guard-rails ativos (M2-020.5).",
            status="ok" if check6_ok else "alert",
            evidence={
                "M2_MAX_DAILY_ENTRIES": env_values.get("M2_MAX_DAILY_ENTRIES"),
                "M2_MAX_MARGIN_PER_POSITION_USD": env_values.get("M2_MAX_MARGIN_PER_POSITION_USD"),
                "M2_MAX_SIGNAL_AGE_MINUTES": env_values.get("M2_MAX_SIGNAL_AGE_MINUTES"),
                "M2_SYMBOL_COOLDOWN_MINUTES": env_values.get("M2_SYMBOL_COOLDOWN_MINUTES"),
                "M2_SHORT_ONLY": env_values.get("M2_SHORT_ONLY"),
                "M2_CANARY_LEVERAGE": env_values.get("M2_CANARY_LEVERAGE"),
                "M2_FUNDING_RATE_MAX_FOR_SHORT": env_values.get("M2_FUNDING_RATE_MAX_FOR_SHORT"),
                "guardrails": guardrails_check["details"],
            },
            error=(
                None if check6_ok
                else (
                    "Guard-rails nao funcionais (risk_gate/circuit_breaker)."
                    if not guardrails_ok
                    else "One or more risk limits are missing/invalid."
                )
            ),
        )

        if not continue_on_error and any(item["status"] != "ok" for item in checks if item["id"] in {"3", "4", "5", "6"}):
            should_stop = True

        if should_stop:
            for step in ("7", "8", "9", "10"):
                add_check(
                    check_id=step,
                    description="Checklist interrompido por fail-fast.",
                    status="skipped",
                )
        else:
            shared_params = {
                "model2_db_path": resolved_db,
                "symbol": explicit_symbols[0] if explicit_symbols else None,
                "timeframe": "H4",
                "limit": 200,
                "output_dir": resolved_output_dir,
                "execution_mode": "shadow",
                "live_symbols": explicit_symbols,
                "max_daily_entries": _to_positive_int(env_values.get("M2_MAX_DAILY_ENTRIES", ""), M2_MAX_DAILY_ENTRIES),
                "max_margin_per_position_usd": _to_positive_float(
                    env_values.get("M2_MAX_MARGIN_PER_POSITION_USD", ""),
                    M2_MAX_MARGIN_PER_POSITION_USD,
                ),
                "max_signal_age_minutes": _to_positive_int(
                    env_values.get("M2_MAX_SIGNAL_AGE_MINUTES", ""),
                    M2_MAX_SIGNAL_AGE_MINUTES,
                ),
                "symbol_cooldown_minutes": _to_positive_int(
                    env_values.get("M2_SYMBOL_COOLDOWN_MINUTES", ""),
                    M2_SYMBOL_COOLDOWN_MINUTES,
                ),
                "short_only": str(env_values.get("M2_SHORT_ONLY", str(M2_SHORT_ONLY))).strip().lower() in {"1", "true", "yes", "on"},
                "funding_rate_max_for_short": _to_positive_float(
                    env_values.get("M2_FUNDING_RATE_MAX_FOR_SHORT", ""),
                    M2_FUNDING_RATE_MAX_FOR_SHORT,
                ),
                "leverage": _to_positive_int(
                    env_values.get("M2_CANARY_LEVERAGE", ""),
                    M2_CANARY_LEVERAGE,
                ),
            }
            execute_action = "python scripts/model2/live_execute.py --timeframe H4 --execution-mode shadow"
            try:
                execute_summary = live_execute_fn(**shared_params)
                add_check(
                    check_id="7",
                    description="Validar live_execute em shadow.",
                    status="ok" if execute_summary.get("status") == "ok" else "alert",
                    actions=[execute_action],
                    evidence={"live_execute_summary": execute_summary},
                    error=None if execute_summary.get("status") == "ok" else "live_execute returned non-ok status.",
                )
            except Exception as exc:
                add_check(
                    check_id="7",
                    description="Validar live_execute em shadow.",
                    status="alert",
                    actions=[execute_action],
                    error=str(exc),
                )

            if not continue_on_error and checks[-1]["status"] != "ok":
                should_stop = True

            reconcile_action = "python scripts/model2/live_reconcile.py --timeframe H4 --execution-mode shadow"
            if should_stop:
                add_check(
                    check_id="8",
                    description="Checklist interrompido por fail-fast.",
                    status="skipped",
                )
            else:
                try:
                    reconcile_summary = live_reconcile_fn(exchange=_NoopExchange(), **shared_params)
                    reconcile_ok = reconcile_summary.get("status") == "ok"
                    add_check(
                        check_id="8",
                        description="Validar live_reconcile sem divergencias.",
                        status="ok" if reconcile_ok else "alert",
                        actions=[reconcile_action],
                        evidence={"live_reconcile_summary": reconcile_summary},
                        error=None if reconcile_ok else "live_reconcile returned non-ok status.",
                    )
                except Exception as exc:
                    add_check(
                        check_id="8",
                        description="Validar live_reconcile sem divergencias.",
                        status="alert",
                        actions=[reconcile_action],
                        error=str(exc),
                    )

            if not continue_on_error and checks[-1]["status"] != "ok":
                should_stop = True

            dashboard_action = "python scripts/model2/live_dashboard.py && python scripts/model2/healthcheck_live_execution.py"
            if should_stop:
                add_check(
                    check_id="9",
                    description="Checklist interrompido por fail-fast.",
                    status="skipped",
                )
            else:
                try:
                    dashboard_summary = live_dashboard_fn(
                        model2_db_path=resolved_db,
                        output_dir=resolved_output_dir,
                        retention_days=30,
                    )
                    healthcheck_summary = live_healthcheck_fn(
                        runtime_dir=resolved_output_dir,
                        output_dir=resolved_output_dir,
                        max_age_hours=2,
                        max_unprotected_filled=0,
                        max_stale_entry_sent=0,
                        max_position_mismatches=0,
                        alert_command=None,
                    )
                    status = "ok" if dashboard_summary.get("status") == "ok" and healthcheck_summary.get("status") == "ok" else "alert"
                    add_check(
                        check_id="9",
                        description="Validar live_dashboard e healthcheck_live_execution com status=ok.",
                        status=status,
                        actions=[dashboard_action],
                        evidence={
                            "live_dashboard_summary": dashboard_summary,
                            "live_healthcheck_summary": healthcheck_summary,
                        },
                        error=None if status == "ok" else "Dashboard or healthcheck returned non-ok status.",
                    )
                except Exception as exc:
                    add_check(
                        check_id="9",
                        description="Validar live_dashboard e healthcheck_live_execution com status=ok.",
                        status="alert",
                        actions=[dashboard_action],
                        error=str(exc),
                    )

            if not continue_on_error and checks[-1]["status"] != "ok":
                should_stop = True

            if should_stop:
                add_check(
                    check_id="10",
                    description="Checklist interrompido por fail-fast.",
                    status="skipped",
                )
            else:
                runbook_ok = RUNBOOK_PATH.exists()
                if runbook_ok:
                    try:
                        content = RUNBOOK_PATH.read_text(encoding="utf-8")
                        runbook_ok = bool(content.strip())
                    except Exception:
                        runbook_ok = False
                if runbook_ok:
                    next_actions.append("Review docs/RUNBOOK_M2_OPERACAO.md before switching M2_EXECUTION_MODE to live.")
                add_check(
                    check_id="10",
                    description="Validar runbook de incidente antes de ativar live.",
                    status="ok" if runbook_ok else "alert",
                    evidence={
                        "runbook_path": str(RUNBOOK_PATH),
                        "readable": runbook_ok,
                    },
                    error=None if runbook_ok else "Runbook file is missing or unreadable.",
                )

    overall_status = "ok" if all(check["status"] == "ok" for check in checks if check["status"] != "skipped") else "alert"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    timestamp_utc_ms = _utc_now_ms()
    summary: dict[str, Any] = {
        "status": overall_status,
        "run_id": run_id,
        "timestamp_utc_ms": timestamp_utc_ms,
        "model2_db_path": str(resolved_db),
        "env_file": str(resolved_env_file),
        "checks": checks,
        "applied_fixes": applied_fixes,
        "next_actions": next_actions,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    output_file = resolved_output_dir / f"model2_go_live_preflight_{run_id}.json"
    atomic_write_json(output_file, {**summary, "output_file": str(output_file)}, ensure_ascii=True, indent=2)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 go-live preflight (Phase 2).")
    parser.add_argument("--model2-db-path", default=MODEL2_DB_PATH, help="Target Model 2.0 SQLite path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory used for preflight summaries.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Path to .env file used by auto-fix checks.")
    parser.add_argument("--no-apply", action="store_true", help="Validation-only mode. No auto-fix actions are executed.")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue all checks even when a prior step fails.")
    parser.add_argument(
        "--live-symbol",
        action="append",
        default=[],
        help="Optional explicit subset for M2_LIVE_SYMBOLS. Repeat the flag for multiple symbols.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    cli_symbols = _normalize_live_symbols(tuple(args.live_symbol or M2_LIVE_SYMBOLS))
    summary = run_go_live_preflight(
        model2_db_path=args.model2_db_path,
        output_dir=args.output_dir,
        env_file=args.env_file,
        apply_fixes=not args.no_apply,
        continue_on_error=bool(args.continue_on_error),
        live_symbols=cli_symbols,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
