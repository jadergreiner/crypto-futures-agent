"""
Model 2.0 migration runner.

Usage:
    python scripts/model2/migrate.py up
    python scripts/model2/migrate.py up --db-path db/modelo2.db --output-dir results/model2/runtime
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.model2.io_utils import atomic_write_json

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "runtime"

try:
    from config.settings import MODEL2_DB_PATH as SETTINGS_MODEL2_DB_PATH
except Exception:
    SETTINGS_MODEL2_DB_PATH = "db/modelo2.db"


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _load_migrations(migrations_dir: Path) -> List[Migration]:
    files = sorted(migrations_dir.glob("*.sql"))
    migrations: List[Migration] = []
    seen_versions = set()

    for file_path in files:
        prefix = file_path.name.split("_", 1)[0]
        if not prefix.isdigit():
            raise ValueError(f"Invalid migration filename: {file_path.name}")

        version = int(prefix)
        if version in seen_versions:
            raise ValueError(f"Duplicate migration version: {version}")

        seen_versions.add(version)
        migrations.append(Migration(version=version, name=file_path.name, path=file_path))

    return migrations


def _ensure_schema_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at INTEGER NOT NULL
        )
        """
    )


def _get_applied_versions(conn: sqlite3.Connection) -> set[int]:
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    return {int(row[0]) for row in rows}


def _write_summary(output_dir: Path, summary: Dict[str, object]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = output_dir / f"model2_migrate_{run_id}.json"
    summary_with_output = dict(summary)
    summary_with_output["output_file"] = str(output_file)
    atomic_write_json(output_file, summary_with_output, ensure_ascii=True, indent=2)
    return output_file


def run_up(db_path: str | Path, output_dir: str | Path) -> Dict[str, object]:
    resolved_db_path = _resolve_repo_path(db_path)
    resolved_output_dir = _resolve_repo_path(output_dir)
    resolved_db_path.parent.mkdir(parents=True, exist_ok=True)
    migrations = _load_migrations(MIGRATIONS_DIR)

    applied_now: List[int] = []

    with sqlite3.connect(resolved_db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        _ensure_schema_migrations(conn)
        applied_versions = _get_applied_versions(conn)

        for migration in migrations:
            if migration.version in applied_versions:
                continue

            migration_sql = migration.path.read_text(encoding="utf-8").strip()
            escaped_name = migration.name.replace("'", "''")
            applied_at = _utc_now_ms()

            transactional_script = (
                "BEGIN IMMEDIATE;\n"
                f"{migration_sql}\n"
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES "
                f"({migration.version}, '{escaped_name}', {applied_at});\n"
                "COMMIT;\n"
            )

            try:
                conn.executescript(transactional_script)
            except Exception:
                conn.execute("ROLLBACK")
                raise

            applied_now.append(migration.version)
            applied_versions.add(migration.version)

        total_applied = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]

    summary: Dict[str, object] = {
        "status": "ok",
        "timestamp_utc_ms": _utc_now_ms(),
        "db_path": str(resolved_db_path),
        "migrations_dir": str(MIGRATIONS_DIR),
        "applied_now": applied_now,
        "total_applied": int(total_applied),
    }
    output_file = _write_summary(resolved_output_dir, summary)
    summary["output_file"] = str(output_file)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Model 2.0 migration runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    up_parser = subparsers.add_parser("up", help="Apply pending migrations")
    up_parser.add_argument(
        "--db-path",
        default=SETTINGS_MODEL2_DB_PATH,
        help="SQLite target path for Model 2.0 database",
    )
    up_parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory used to save migration run summaries",
    )

    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if args.command == "up":
        summary = run_up(db_path=args.db_path, output_dir=args.output_dir)
        print(json.dumps(summary, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
