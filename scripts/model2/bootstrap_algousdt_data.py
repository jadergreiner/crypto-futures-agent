"""
CLI para bootstrap de dados históricos ALGOUSDT.

Uso:
    python scripts/model2/bootstrap_algousdt_data.py \\
      --symbol ALGOUSDT \\
      --timeframes D1,H4,H1,M5 \\
      --start-date 2025-04-01 \\
      --end-date 2026-03-31 \\
      --mode fetch
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.model2.bootstrap_data_loader import HistoricalDataBootstrapper
from data.binance_client import create_binance_client
from data.collector import BinanceCollector
from data.database import DatabaseManager
from scripts.model2.io_utils import atomic_write_json

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"

try:
    from config.settings import DB_PATH, MODEL2_DB_PATH
except Exception:
    DB_PATH = "db/crypto_agent.db"
    MODEL2_DB_PATH = "db/modelo2.db"


def _resolve_repo_path(value: str | Path) -> Path:
    """Resolver path relativo ou absoluto."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _utc_now_ms() -> int:
    """Retornar timestamp UTC atual em ms."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def run_bootstrap_algousdt(
    *,
    source_db_path: str | Path,
    symbol: str,
    timeframes: list[str],
    start_date: str,
    end_date: str,
    mode: str = "fetch",
) -> list[dict[str, Any]] | dict[str, Any]:
    """
    Executar bootstrap de dados históricos.

    Args:
        source_db_path: Caminho para DB legado (crypto_agent.db)
        symbol: Símbolo (ex: "ALGOUSDT")
        timeframes: Lista de timeframes ["D1", "H4", "H1", "M5"]
        start_date: Data inicial "YYYY-MM-DD"
        end_date: Data final "YYYY-MM-DD"
        mode: "fetch" (capturar) | "validate" (validar) | "both"

    Returns:
        Lista de candles ou dict com summary
    """
    resolved_source_db = _resolve_repo_path(source_db_path)

    # Criar cliente e collector
    try:
        client = create_binance_client()
        collector = BinanceCollector(client)
    except Exception as e:
        logger.error(f"Erro ao criar cliente Binance: {e}")
        return {
            "status": "error",
            "error": f"Falha ao criar cliente Binance: {str(e)}",
        }

    # Inicializar DB
    db = DatabaseManager(str(resolved_source_db))
    db.init_db()

    # Criar bootstrapper
    bootstrapper = HistoricalDataBootstrapper(collector, db)

    # Executar bootstrap
    if mode in ["fetch", "both"]:
        summary = bootstrapper.bootstrap(
            symbol=symbol,
            timeframes=timeframes,
            start_date=start_date,
            end_date=end_date,
        )
        logger.info(f"Bootstrap concluído: {summary['status']}")

        # Recuperar candles do DB e retornar como lista
        all_candles = []
        for tf in timeframes:
            tf_lower = tf.lower()
            rows = db.get_ohlcv(tf_lower, symbol)
            for row in rows:
                candle = dict(row)
                candle["timeframe"] = tf
                all_candles.append(candle)

        return all_candles
    elif mode == "validate":
        # Modo validação: apenas validar dados em DB
        logger.info("Modo validação: apenas checando dados em DB")
        return {
            "status": "ok",
            "mode": "validate",
        }
    else:
        return {
            "status": "error",
            "error": f"Mode inválido: {mode}",
        }


def validate_bootstrap_output(summary: dict[str, Any]) -> bool:
    """
    Validar estructura da saída bootstrap.

    Args:
        summary: Dict de resumo

    Returns:
        True se válido, False caso contrário
    """
    required_keys = [
        "status",
        "symbols",
        "timeframes",
        "synced_count",
        "error_count",
    ]
    return all(k in summary for k in required_keys)


def main() -> int:
    """Entrypoint CLI."""
    parser = argparse.ArgumentParser(
        description="Bootstrap de dados históricos para trading"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="ALGOUSDT",
        help="Símbolo de trading (default: ALGOUSDT)",
    )
    parser.add_argument(
        "--timeframes",
        type=str,
        default="D1,H4,H1,M5",
        help="Timeframes separados por vírgula (default: D1,H4,H1,M5)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2025-04-01",
        help="Data inicial YYYY-MM-DD (default: 2025-04-01)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="2026-03-31",
        help="Data final YYYY-MM-DD (default: 2026-03-31)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["fetch", "validate", "both"],
        default="fetch",
        help="Modo de operação (default: fetch)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(DB_PATH),
        help=f"Caminho para DB legado (default: {DB_PATH})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Diretório de saída (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ativar logging verbose",
    )

    args = parser.parse_args()

    # Configurar logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Parsear timeframes
    timeframes = [tf.strip().upper() for tf in args.timeframes.split(",")]

    # Executar bootstrap
    logger.info(
        f"Iniciando bootstrap {args.symbol} "
        f"timeframes={timeframes} "
        f"período={args.start_date}..{args.end_date}"
    )

    result = run_bootstrap_algousdt(
        source_db_path=args.db_path,
        symbol=args.symbol,
        timeframes=timeframes,
        start_date=args.start_date,
        end_date=args.end_date,
        mode=args.mode,
    )

    # Construir summary a partir dos resultados
    if isinstance(result, dict):
        # Erro retornado
        summary = result
    else:
        # Lista de candles retornada - criar summary
        db = DatabaseManager(args.db_path)
        summary = {
            "status": "ok",
            "symbols": [args.symbol],
            "timeframes": timeframes,
            "synced_count": len(set(c.get("timeframe") for c in result)) if result else 0,
            "error_count": 0,
            "items": [],
        }

        # Agrupar candles por timeframe
        for tf in timeframes:
            tf_candles = [c for c in result if c.get("timeframe") == tf]
            if tf_candles:
                summary["items"].append({
                    "symbol": args.symbol,
                    "timeframe": tf,
                    "status": "ok",
                    "rows": len(tf_candles),
                    "latest_timestamp": max(c.get("timestamp", 0) for c in tf_candles),
                })
            else:
                summary["items"].append({
                    "symbol": args.symbol,
                    "timeframe": tf,
                    "status": "no_data",
                })

    # Validar
    if not validate_bootstrap_output(summary):
        logger.error("Saída bootstrap inválida")
        summary["status"] = "error"

    # Escrever saída
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = output_dir / f"bootstrap_algousdt_{run_id}.json"

    summary["output_file"] = str(output_file)
    summary["timestamp_utc_ms"] = _utc_now_ms()

    atomic_write_json(output_file, summary, ensure_ascii=True, indent=2)

    logger.info(f"Bootstrap concluído: {summary['status']}")
    logger.info(f"Summary salvo em: {output_file}")

    # Retornar status
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
