"""Sincroniza dados OHLCV mais recentes da Binance antes da pipeline Model2."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import DB_PATH, M2_SYMBOLS, MODEL2_DB_PATH
from data.binance_client import create_binance_client
from data.collector import BinanceCollector

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def sync_ohlcv_from_binance(
    *,
    source_db_path: str | Path,
    symbols: list[str],
    timeframes: list[str],
    output_dir: str | Path,
) -> dict[str, Any]:
    """
    Sincroniza dados OHLCV mais recentes da Binance.

    Atualiza cada timeframe com os candles mais recentes para os símbolos
    solicitados. Usa BinanceCollector para buscar dados e insere/atualiza
    no banco legado (crypto_agent.db).

    Args:
        source_db_path: Banco legado (coleta via Binance)
        symbols: Lista de símbolos
        timeframes: Lista de timeframes (D1, H4, H1)
        output_dir: Diretório para saída de summary

    Returns:
        dict com status, símbolos sincronizados, erros, etc.
    """
    from data.database import DatabaseManager

    resolved_source_db = _resolve_repo_path(source_db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    db = DatabaseManager(str(resolved_source_db))

    try:
        client = create_binance_client()
    except Exception as e:
        return {
            "status": "error",
            "error": f"Falha ao criar cliente Binance: {str(e)}",
            "timestamp_utc_ms": _utc_now_ms(),
            "source_db_path": str(resolved_source_db),
            "output_file": "",
        }

    collector = BinanceCollector(client)

    symbols_to_use = list(symbols) if symbols else list(M2_SYMBOLS)
    timeframes_to_sync = timeframes if timeframes else ["H4"]

    summary: dict[str, Any] = {
        "status": "ok",
        "timestamp_utc_ms": _utc_now_ms(),
        "source_db_path": str(resolved_source_db),
        "symbols": symbols_to_use,
        "timeframes": timeframes_to_sync,
        "synced_count": 0,
        "error_count": 0,
        "items": [],
    }

    # Mapear nomes Binance → nomes locais
    timeframe_map = {
        "D1": "1d",
        "H4": "4h",
        "H1": "1h",
    }

    for symbol in symbols_to_use:
        for timeframe in timeframes_to_sync:
            if timeframe not in timeframe_map:
                summary["error_count"] += 1
                summary["items"].append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "status": "error",
                    "reason": f"Timeframe inválido: {timeframe}",
                })
                continue

            binance_tf = timeframe_map[timeframe]
            try:
                # Buscar candles recentes (últimos 2 = ultimos ~8h para H4)
                data = collector.fetch_historical(
                    symbol,
                    binance_tf,
                    days=1,  # Busca 1 dia de data, mas será apenas os candles recentes
                )

                if data is None or data.empty:
                    summary["error_count"] += 1
                    summary["items"].append({
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "status": "no_data",
                    })
                    continue

                # Inserir/atualizar no banco
                db.insert_ohlcv(timeframe.lower(), data)

                summary["synced_count"] += 1
                summary["items"].append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "status": "synced",
                    "rows": len(data),
                    "latest_timestamp": int(data.iloc[-1]["timestamp"]) if len(data) > 0 else None,
                })

            except Exception as e:
                summary["error_count"] += 1
                summary["items"].append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "status": "error",
                    "reason": str(e),
                })

    # Persistir summary
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = resolved_output_dir / f"sync_ohlcv_from_binance_{run_id}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=True, default=str)

    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sincroniza OHLCV da Binance para o banco legado antes do pipeline M2"
    )
    parser.add_argument(
        "--source-db-path",
        default=DB_PATH,
        help="Banco legado para coleta Binance",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Símbolo para sincronizar. Repeat para múltiplos.",
    )
    parser.add_argument(
        "--timeframe",
        action="append",
        choices=["D1", "H4", "H1"],
        default=["H4"],
        help="Timeframe para sincronizar",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Diretório para saída de summary",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = sync_ohlcv_from_binance(
        source_db_path=args.source_db_path,
        symbols=list(args.symbol or []),
        timeframes=list(args.timeframe or ["H4"]),
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True, default=str))
    return 0 if summary["status"] in {"ok", "partial"} else 1


if __name__ == "__main__":
    sys.exit(main())
