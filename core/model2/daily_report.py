"""Relatorio diario consolidado de performance Model 2.0 — M2-028.6.

Coleta metricas do dia (UTC) diretamente do banco de dados, formata
bloco legivel ao operador e persiste arquivos JSON + TXT.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.model2.time_utils import now_brt_str

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapeamento de gate_reason para severidade
# ---------------------------------------------------------------------------
_GATE_REASON_SEVERIDADE: dict[str, str] = {
    "DAILY_DRAWDOWN_LIMIT": "CRITICAL",
    "CIRCUIT_BREAKER": "CRITICAL",
    "RECONCILIATION_DIVERGENCE": "CRITICAL",
    "SHORT_ONLY": "WARN",
    "ENTRY_LIMIT": "WARN",
    "MAX_MARGIN": "WARN",
    "ONBOARDING": "INFO",
}
_SEVERIDADE_PADRAO = "INFO"

_ADMITIDAS_STATUSES = {"ENTRY_FILLED", "PROTECTED", "EXITED"}
_BLOQUEADAS_STATUSES = {"BLOCKED", "CANCELLED"}


# ---------------------------------------------------------------------------
# Dataclass de resultado
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DailyReportData:
    """Dados consolidados do relatorio diario de performance."""

    data_ref_utc: str          # "YYYY-MM-DD"
    gerado_em_brt: str         # ts de geracao em BRT
    run_id: str

    # PnL realizado
    pnl_realizado_usd: float
    operacoes_exited: int

    # Episodios de treino
    episodios_total: int
    episodios_win: int
    episodios_loss: int
    win_rate: float | None     # None quando sem episodios

    # Drawdown
    drawdown_maximo_usd: float  # perdas acumuladas do dia (DB-only)

    # Operacoes
    execucoes_admitidas: int
    execucoes_bloqueadas: int

    # Alertas
    alertas_por_severidade: dict[str, int]

    # Erros nao-fatais de coleta
    stage_errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Servico principal
# ---------------------------------------------------------------------------
class DailyReportService:
    """Coleta, formata e persiste o relatorio diario de performance."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        reports_dir: str | Path | None = None,
    ) -> None:
        self._db_path = str(db_path)
        self._reports_dir = Path(reports_dir) if reports_dir else None

    # ------------------------------------------------------------------
    # Coleta de dados
    # ------------------------------------------------------------------
    def coletar_dados(self, data_ref_utc: str, *, run_id: str) -> DailyReportData:
        """Coleta metricas do dia `data_ref_utc` (formato 'YYYY-MM-DD').

        Nunca propaga excecao — campos ficam em zero/None e erros sao
        registrados em stage_errors.
        """
        dt = datetime.strptime(data_ref_utc, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        day_start_ms = int(dt.timestamp() * 1000)
        day_end_ms = day_start_ms + 86_400_000

        stage_errors: list[str] = []

        # Valores padrao
        pnl_realizado_usd: float = 0.0
        operacoes_exited: int = 0
        episodios_win: int = 0
        episodios_loss: int = 0
        drawdown_maximo_usd: float = 0.0
        execucoes_admitidas: int = 0
        execucoes_bloqueadas: int = 0
        alertas_por_severidade: dict[str, int] = {}

        with _conectar(self._db_path) as conn:
            # 1. PnL realizado
            try:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS operacoes_exited,
                           COALESCE(SUM(
                             (exit_price - filled_price) * filled_qty
                             * CASE signal_side WHEN 'SHORT' THEN -1.0 ELSE 1.0 END
                           ), 0.0) AS pnl_realizado_usd
                    FROM signal_executions
                    WHERE status = 'EXITED'
                      AND exited_at >= :s AND exited_at < :e
                    """,
                    {"s": day_start_ms, "e": day_end_ms},
                ).fetchone()
                if row:
                    operacoes_exited = int(row["operacoes_exited"] or 0)
                    pnl_realizado_usd = float(row["pnl_realizado_usd"] or 0.0)
            except Exception as exc:
                stage_errors.append(f"pnl_realizado: {exc}")

            # 2. Episodios de treino (win-rate)
            try:
                rows = conn.execute(
                    """
                    SELECT LOWER(label) AS lbl, COUNT(*) AS total
                    FROM training_episodes
                    WHERE LOWER(label) IN ('win', 'loss')
                      AND created_at >= :s AND created_at < :e
                    GROUP BY LOWER(label)
                    """,
                    {"s": day_start_ms, "e": day_end_ms},
                ).fetchall()
                for row in rows:
                    if row["lbl"] == "win":
                        episodios_win = int(row["total"])
                    elif row["lbl"] == "loss":
                        episodios_loss = int(row["total"])
            except Exception as exc:
                stage_errors.append(f"episodios: {exc}")

            # 3. Drawdown maximo (perdas acumuladas)
            try:
                row = conn.execute(
                    """
                    SELECT COALESCE(SUM(
                        CASE
                          WHEN (exit_price - filled_price)
                               * CASE signal_side WHEN 'SHORT' THEN -1.0 ELSE 1.0 END < 0
                          THEN ABS(
                                (exit_price - filled_price) * filled_qty
                                * CASE signal_side WHEN 'SHORT' THEN -1.0 ELSE 1.0 END
                              )
                          ELSE 0.0
                        END
                    ), 0.0) AS perdas_usd
                    FROM signal_executions
                    WHERE status = 'EXITED'
                      AND exited_at >= :s AND exited_at < :e
                    """,
                    {"s": day_start_ms, "e": day_end_ms},
                ).fetchone()
                if row:
                    drawdown_maximo_usd = float(row["perdas_usd"] or 0.0)
            except Exception as exc:
                stage_errors.append(f"drawdown: {exc}")

            # 4. Admitidas / bloqueadas
            try:
                rows = conn.execute(
                    """
                    SELECT status, COUNT(*) AS total
                    FROM signal_executions
                    WHERE created_at >= :s AND created_at < :e
                      AND status IN (
                        'ENTRY_FILLED', 'PROTECTED', 'EXITED',
                        'BLOCKED', 'CANCELLED'
                      )
                    GROUP BY status
                    """,
                    {"s": day_start_ms, "e": day_end_ms},
                ).fetchall()
                for row in rows:
                    status = row["status"]
                    total = int(row["total"])
                    if status in _ADMITIDAS_STATUSES:
                        execucoes_admitidas += total
                    elif status in _BLOQUEADAS_STATUSES:
                        execucoes_bloqueadas += total
            except Exception as exc:
                stage_errors.append(f"admitidas_bloqueadas: {exc}")

            # 5. Alertas por severidade
            try:
                rows = conn.execute(
                    """
                    SELECT gate_reason, COUNT(*) AS total
                    FROM signal_executions
                    WHERE gate_reason IS NOT NULL
                      AND created_at >= :s AND created_at < :e
                    GROUP BY gate_reason
                    """,
                    {"s": day_start_ms, "e": day_end_ms},
                ).fetchall()
                contagem: dict[str, int] = {}
                for row in rows:
                    reason = (row["gate_reason"] or "").upper()
                    sev = _GATE_REASON_SEVERIDADE.get(reason, _SEVERIDADE_PADRAO)
                    contagem[sev] = contagem.get(sev, 0) + int(row["total"])
                alertas_por_severidade = contagem
            except Exception as exc:
                stage_errors.append(f"alertas: {exc}")

        episodios_total = episodios_win + episodios_loss
        win_rate: float | None = (
            episodios_win / episodios_total if episodios_total > 0 else None
        )

        return DailyReportData(
            data_ref_utc=data_ref_utc,
            gerado_em_brt=now_brt_str(),
            run_id=run_id,
            pnl_realizado_usd=pnl_realizado_usd,
            operacoes_exited=operacoes_exited,
            episodios_total=episodios_total,
            episodios_win=episodios_win,
            episodios_loss=episodios_loss,
            win_rate=win_rate,
            drawdown_maximo_usd=drawdown_maximo_usd,
            execucoes_admitidas=execucoes_admitidas,
            execucoes_bloqueadas=execucoes_bloqueadas,
            alertas_por_severidade=alertas_por_severidade,
            stage_errors=stage_errors,
        )

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def persistir(self, data: DailyReportData) -> tuple[Path, Path]:
        """Persiste JSON e TXT em results/model2/reports/.

        Returns:
            Tupla (path_json, path_txt).
        """
        reports_dir = self._reports_dir or (
            Path(__file__).resolve().parents[2]
            / "results"
            / "model2"
            / "reports"
        )
        reports_dir.mkdir(parents=True, exist_ok=True)

        data_slug = data.data_ref_utc.replace("-", "")
        path_json = reports_dir / f"relatorio_diario_{data_slug}.json"
        path_txt = reports_dir / f"relatorio_diario_{data_slug}.txt"

        # JSON
        _atomic_write_json(path_json, _to_dict(data))

        # TXT
        texto = formatar_relatorio_diario(data)
        path_txt.write_text(texto, encoding="utf-8")

        return path_json, path_txt


# ---------------------------------------------------------------------------
# Formatacao
# ---------------------------------------------------------------------------
_SEP_DUPLO = "═" * 48
_SEP_SIMPLES = "─" * 48


def formatar_relatorio_diario(data: DailyReportData) -> str:
    """Formata o relatorio diario em bloco legivel ao operador."""
    pnl_sinal = "+" if data.pnl_realizado_usd >= 0 else ""
    pnl_str = f"{pnl_sinal}${data.pnl_realizado_usd:,.2f}"

    if data.win_rate is not None:
        wr_str = (
            f"{data.win_rate * 100:.1f}%"
            f"  ({data.episodios_win}W / {data.episodios_loss}L)"
        )
    else:
        wr_str = "N/A  (sem episodios)"

    dd_str = f"-${data.drawdown_maximo_usd:,.2f} acumulado"

    alertas_parts = "  ".join(
        f"{sev}={cnt}"
        for sev, cnt in sorted(data.alertas_por_severidade.items())
    ) or "nenhum"

    linhas = [
        _SEP_DUPLO,
        f"  RELATORIO DIARIO M2 | {data.data_ref_utc} | {data.gerado_em_brt}",
        _SEP_DUPLO,
        f"  PnL Realizado  : {pnl_str}  ({data.operacoes_exited} encerradas)",
        f"  Win-rate       : {wr_str}",
        f"  Drawdown Max.  : {dd_str}",
        _SEP_SIMPLES,
        f"  Operacoes      : {data.execucoes_admitidas} admitidas | "
        f"{data.execucoes_bloqueadas} bloqueadas",
        f"  Alertas        : {alertas_parts}",
        _SEP_SIMPLES,
        f"  Episodios RL   : {data.episodios_total} capturados "
        f"({data.episodios_win}W / {data.episodios_loss}L)",
        _SEP_DUPLO,
    ]
    if data.stage_errors:
        linhas.append(f"  Avisos coleta  : {len(data.stage_errors)} erro(s) nao-fatal(is)")
        for err in data.stage_errors:
            linhas.append(f"    - {err}")
        linhas.append(_SEP_DUPLO)
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------
def _conectar(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _to_dict(data: DailyReportData) -> dict[str, Any]:
    return dataclasses.asdict(data)


def _atomic_write_json(path: Path, payload: Any) -> None:
    import os
    import tempfile

    tmp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            tmp_file = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=True, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp_file), str(path))
    finally:
        if tmp_file is not None and tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass
