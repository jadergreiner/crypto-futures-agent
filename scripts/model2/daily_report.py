"""Runner standalone do relatorio diario de performance Model 2.0 — M2-028.6.

Pode ser executado diretamente ou chamado como stage 17 do daily_pipeline.py.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.model2.daily_report import DailyReportService, formatar_relatorio_diario

logger = logging.getLogger(__name__)


def run_daily_report(
    *,
    model2_db_path: str | Path,
    data_ref_utc: str | None = None,
    run_id: str | None = None,
    reports_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Coleta, formata e persiste o relatorio diario de performance.

    Compativel com o padrao de retorno dos outros stages do daily_pipeline.py.

    Args:
        model2_db_path: Caminho para o banco modelo2.db.
        data_ref_utc: Data de referencia no formato 'YYYY-MM-DD'.
            Padrao: hoje UTC.
        run_id: Identificador do ciclo. Gerado automaticamente se omitido.
        reports_dir: Diretorio de saida para os arquivos de relatorio.

    Returns:
        Dicionario de sumario compativel com stage_summaries do pipeline.
    """
    t0 = perf_counter()

    if data_ref_utc is None:
        data_ref_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    servico = DailyReportService(
        db_path=model2_db_path,
        reports_dir=reports_dir,
    )

    dados = servico.coletar_dados(data_ref_utc, run_id=run_id)
    path_json, path_txt = servico.persistir(dados)

    texto = formatar_relatorio_diario(dados)
    logger.info("Relatorio diario gerado:\n%s", texto)

    elapsed_ms = int((perf_counter() - t0) * 1000)

    return {
        "status": "ok" if not dados.stage_errors else "partial",
        "stage_elapsed_ms": elapsed_ms,
        "data_ref_utc": data_ref_utc,
        "run_id": run_id,
        "json_path": str(path_json),
        "txt_path": str(path_txt),
        "pnl_realizado_usd": dados.pnl_realizado_usd,
        "operacoes_exited": dados.operacoes_exited,
        "win_rate": dados.win_rate,
        "episodios_total": dados.episodios_total,
        "drawdown_maximo_usd": dados.drawdown_maximo_usd,
        "execucoes_admitidas": dados.execucoes_admitidas,
        "execucoes_bloqueadas": dados.execucoes_bloqueadas,
        "stage_errors": dados.stage_errors,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Relatorio diario consolidado Model 2.0"
    )
    parser.add_argument(
        "--model2-db-path",
        default="db/modelo2.db",
        help="Caminho para modelo2.db (padrao: db/modelo2.db).",
    )
    parser.add_argument(
        "--data-ref-utc",
        default=None,
        help="Data de referencia UTC no formato YYYY-MM-DD (padrao: hoje).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Identificador do ciclo (padrao: gerado automaticamente).",
    )
    parser.add_argument(
        "--reports-dir",
        default=None,
        help="Diretorio de saida (padrao: results/model2/reports/).",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = _parse_args()

    try:
        resultado = run_daily_report(
            model2_db_path=args.model2_db_path,
            data_ref_utc=args.data_ref_utc,
            run_id=args.run_id,
            reports_dir=args.reports_dir,
        )
    except Exception as exc:
        logger.error("Falha ao gerar relatorio diario: %s", exc)
        return 1

    if resultado.get("stage_errors"):
        logger.warning(
            "Relatorio gerado com %d aviso(s) de coleta.",
            len(resultado["stage_errors"]),
        )

    print(f"JSON : {resultado['json_path']}")
    print(f"TXT  : {resultado['txt_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
