from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from core.model2.daily_report import (
    DailyReportData,
    DailyReportService,
    formatar_relatorio_diario,
)


def _criar_db_base(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE signal_executions (
            id INTEGER PRIMARY KEY,
            status TEXT,
            signal_side TEXT,
            filled_price REAL,
            exit_price REAL,
            filled_qty REAL,
            gate_reason TEXT,
            created_at INTEGER,
            exited_at INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE training_episodes (
            id INTEGER PRIMARY KEY,
            label TEXT,
            created_at INTEGER
        )
        """
    )
    conn.commit()
    conn.close()


def _ms_utc(data_iso: str) -> int:
    # Sempre usa o inicio do dia em UTC para manter determinismo nos testes.
    ano, mes, dia = (int(p) for p in data_iso.split("-"))
    import datetime as _dt

    dt = _dt.datetime(ano, mes, dia, tzinfo=_dt.timezone.utc)
    return int(dt.timestamp() * 1000)


def test_coletar_pnl_realizado_com_exited_calcula_total(tmp_path: Path) -> None:
    db_path = tmp_path / "modelo2.db"
    _criar_db_base(db_path)
    ref = "2026-03-30"
    t0 = _ms_utc(ref)

    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO signal_executions (
            status, signal_side, filled_price, exit_price, filled_qty,
            gate_reason, created_at, exited_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("EXITED", "LONG", 100.0, 110.0, 2.0, None, t0 + 1, t0 + 2),
            ("EXITED", "SHORT", 100.0, 95.0, 1.0, None, t0 + 3, t0 + 4),
            ("EXITED", "LONG", 100.0, 90.0, 1.0, None, t0 + 5, t0 + 6),
        ],
    )
    conn.commit()
    conn.close()

    svc = DailyReportService(db_path)
    data = svc.coletar_dados(ref, run_id="RID-1")

    assert data.operacoes_exited == 3
    assert data.pnl_realizado_usd == 15.0


def test_coletar_win_rate_com_win_loss_calcula_taxa(tmp_path: Path) -> None:
    db_path = tmp_path / "modelo2.db"
    _criar_db_base(db_path)
    ref = "2026-03-30"
    t0 = _ms_utc(ref)

    conn = sqlite3.connect(db_path)
    conn.executemany(
        "INSERT INTO training_episodes (label, created_at) VALUES (?, ?)",
        [
            ("win", t0 + 1),
            ("WIN", t0 + 2),
            ("loss", t0 + 3),
        ],
    )
    conn.commit()
    conn.close()

    svc = DailyReportService(db_path)
    data = svc.coletar_dados(ref, run_id="RID-2")

    assert data.episodios_win == 2
    assert data.episodios_loss == 1
    assert data.episodios_total == 3
    assert data.win_rate == 2 / 3


def test_coletar_sem_episodios_retorna_win_rate_none(tmp_path: Path) -> None:
    db_path = tmp_path / "modelo2.db"
    _criar_db_base(db_path)

    svc = DailyReportService(db_path)
    data = svc.coletar_dados("2026-03-30", run_id="RID-3")

    assert data.episodios_total == 0
    assert data.win_rate is None


def test_coletar_drawdown_soma_apenas_perdas(tmp_path: Path) -> None:
    db_path = tmp_path / "modelo2.db"
    _criar_db_base(db_path)
    ref = "2026-03-30"
    t0 = _ms_utc(ref)

    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO signal_executions (
            status, signal_side, filled_price, exit_price, filled_qty,
            gate_reason, created_at, exited_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("EXITED", "LONG", 100.0, 90.0, 1.0, None, t0 + 1, t0 + 2),
            ("EXITED", "SHORT", 100.0, 110.0, 2.0, None, t0 + 3, t0 + 4),
            ("EXITED", "LONG", 100.0, 105.0, 1.0, None, t0 + 5, t0 + 6),
        ],
    )
    conn.commit()
    conn.close()

    svc = DailyReportService(db_path)
    data = svc.coletar_dados(ref, run_id="RID-4")

    assert data.drawdown_maximo_usd == 30.0


def test_coletar_execucoes_separa_admitidas_bloqueadas(tmp_path: Path) -> None:
    db_path = tmp_path / "modelo2.db"
    _criar_db_base(db_path)
    ref = "2026-03-30"
    t0 = _ms_utc(ref)

    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO signal_executions (
            status, signal_side, filled_price, exit_price, filled_qty,
            gate_reason, created_at, exited_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("ENTRY_FILLED", "LONG", 0, 0, 0, None, t0 + 1, None),
            ("PROTECTED", "LONG", 0, 0, 0, None, t0 + 2, None),
            ("EXITED", "LONG", 100.0, 105.0, 1.0, None, t0 + 3, t0 + 4),
            ("BLOCKED", "LONG", 0, 0, 0, "ENTRY_LIMIT", t0 + 5, None),
            ("CANCELLED", "LONG", 0, 0, 0, "ONBOARDING", t0 + 6, None),
        ],
    )
    conn.commit()
    conn.close()

    svc = DailyReportService(db_path)
    data = svc.coletar_dados(ref, run_id="RID-5")

    assert data.execucoes_admitidas == 3
    assert data.execucoes_bloqueadas == 2


def test_coletar_alertas_agrega_por_severidade(tmp_path: Path) -> None:
    db_path = tmp_path / "modelo2.db"
    _criar_db_base(db_path)
    ref = "2026-03-30"
    t0 = _ms_utc(ref)

    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO signal_executions (
            status, signal_side, filled_price, exit_price, filled_qty,
            gate_reason, created_at, exited_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("BLOCKED", "LONG", 0, 0, 0, "CIRCUIT_BREAKER", t0 + 1, None),
            ("BLOCKED", "LONG", 0, 0, 0, "RECONCILIATION_DIVERGENCE", t0 + 2, None),
            ("BLOCKED", "LONG", 0, 0, 0, "ENTRY_LIMIT", t0 + 3, None),
            ("BLOCKED", "LONG", 0, 0, 0, "UNKNOWN_REASON", t0 + 4, None),
        ],
    )
    conn.commit()
    conn.close()

    svc = DailyReportService(db_path)
    data = svc.coletar_dados(ref, run_id="RID-6")

    assert data.alertas_por_severidade == {"CRITICAL": 2, "WARN": 1, "INFO": 1}


def test_persistir_gera_json_e_txt_com_nome_da_data(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    data = DailyReportData(
        data_ref_utc="2026-03-30",
        gerado_em_brt="2026-03-30 10:00:00 BRT",
        run_id="RID-7",
        pnl_realizado_usd=10.5,
        operacoes_exited=2,
        episodios_total=3,
        episodios_win=2,
        episodios_loss=1,
        win_rate=2 / 3,
        drawdown_maximo_usd=5.5,
        execucoes_admitidas=4,
        execucoes_bloqueadas=1,
        alertas_por_severidade={"WARN": 2},
        stage_errors=[],
    )

    svc = DailyReportService(tmp_path / "modelo2.db", reports_dir=reports_dir)
    path_json, path_txt = svc.persistir(data)

    assert path_json.name == "relatorio_diario_20260330.json"
    assert path_txt.name == "relatorio_diario_20260330.txt"
    assert path_json.exists()
    assert path_txt.exists()
    payload = json.loads(path_json.read_text(encoding="utf-8"))
    assert payload["run_id"] == "RID-7"
    assert "RELATORIO DIARIO M2" in path_txt.read_text(encoding="utf-8")


def test_formatar_relatorio_exibe_winrate_e_avisos() -> None:
    data = DailyReportData(
        data_ref_utc="2026-03-30",
        gerado_em_brt="2026-03-30 10:00:00 BRT",
        run_id="RID-8",
        pnl_realizado_usd=-12.0,
        operacoes_exited=2,
        episodios_total=2,
        episodios_win=1,
        episodios_loss=1,
        win_rate=0.5,
        drawdown_maximo_usd=12.0,
        execucoes_admitidas=1,
        execucoes_bloqueadas=2,
        alertas_por_severidade={"CRITICAL": 1},
        stage_errors=["pnl_realizado: tabela ausente"],
    )

    texto = formatar_relatorio_diario(data)

    assert "Win-rate       : 50.0%  (1W / 1L)" in texto
    assert "Avisos coleta  : 1 erro(s) nao-fatal(is)" in texto
    assert "pnl_realizado: tabela ausente" in texto