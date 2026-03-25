"""Testes RED para M2-025.2 - Normalizacao de timezone de evento no pipeline.

Fase: RED — devem FALHAR antes da implementacao.
Cobre: format_cycle_summary usa BRT canonico; live_service em conformidade;
       time_utils como unico ponto de exibicao; persistencia UTC preservada.
"""
from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# R1 — format_cycle_summary deve exibir BRT canonico (nunca LMT ou offset)
# ---------------------------------------------------------------------------

class TestCycleReportTimezoneExibicao:
    """R1: format_cycle_summary deve terminar timestamp em 'BRT'."""

    def _make_reports(self) -> list:  # type: ignore[type-arg]
        from core.model2.cycle_report import SymbolReport
        return [
            SymbolReport(
                symbol="BTCUSDT",
                timeframe="5m",
                timestamp="2026-03-25 10:00:00 BRT",
                decision="HOLD",
                confidence=0.6,
                candle_state="fresh",
                freshness_reason="within_window",
            )
        ]

    def test_format_cycle_summary_header_termina_em_brt(self) -> None:
        """Header do ciclo deve conter ' BRT' como sufixo de timestamp."""
        from core.model2.cycle_report import format_cycle_summary

        resultado = format_cycle_summary(
            reports=self._make_reports(),
            cycle_number=1,
            next_cycle_time="2026-03-25 10:00 BRT",
        )
        # Deve conter BRT no header
        assert " BRT" in resultado, (
            f"Header nao contem ' BRT': {resultado[:200]}"
        )

    def test_format_cycle_summary_header_nao_contem_lmt(self) -> None:
        """Header nao deve conter 'LMT' (fuso ambiguo legado)."""
        from core.model2.cycle_report import format_cycle_summary

        resultado = format_cycle_summary(
            reports=self._make_reports(),
            cycle_number=2,
            next_cycle_time="2026-03-25 10:00 BRT",
        )
        assert "LMT" not in resultado, (
            f"Header contem 'LMT' (fuso ambiguo): {resultado[:200]}"
        )

    def test_format_cycle_summary_header_nao_contem_offset_numerico(self) -> None:
        """Header nao deve conter offset numerico como -0300 ou -03:00."""
        from core.model2.cycle_report import format_cycle_summary

        resultado = format_cycle_summary(
            reports=self._make_reports(),
            cycle_number=3,
            next_cycle_time="2026-03-25 10:00 BRT",
        )
        assert not re.search(r"[+-]\d{2}:?\d{2}", resultado[:200]), (
            f"Header contem offset numerico de timezone: {resultado[:200]}"
        )

    def test_format_cycle_summary_formato_brt_padrao(self) -> None:
        """Timestamp no header deve seguir formato 'YYYY-MM-DD HH:MM:SS BRT'."""
        from core.model2.cycle_report import format_cycle_summary

        resultado = format_cycle_summary(
            reports=self._make_reports(),
            cycle_number=4,
            next_cycle_time="2026-03-25 10:00 BRT",
        )
        # Padrao canonico do time_utils: YYYY-MM-DD HH:MM:SS BRT
        padrao = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} BRT"
        assert re.search(padrao, resultado), (
            f"Formato canonico BRT nao encontrado no header: {resultado[:200]}"
        )


# ---------------------------------------------------------------------------
# R2 — time_utils e o utilitario canonico de exibicao
# ---------------------------------------------------------------------------

class TestTimeUtilsCanonicos:
    """R2: time_utils fornece funcoes canonicas para exibicao BRT."""

    def test_now_brt_str_termina_em_brt(self) -> None:
        """now_brt_str() deve retornar string terminando em ' BRT'."""
        from core.model2.time_utils import now_brt_str

        resultado = now_brt_str()
        assert resultado.endswith(" BRT"), f"now_brt_str={resultado!r}"

    def test_ts_ms_to_brt_str_termina_em_brt(self) -> None:
        """ts_ms_to_brt_str() deve retornar string terminando em ' BRT'."""
        from core.model2.time_utils import ts_ms_to_brt_str

        ts_ms = 1_700_000_000_000  # timestamp arbitrario
        resultado = ts_ms_to_brt_str(ts_ms)
        assert resultado.endswith(" BRT"), f"ts_ms_to_brt_str={resultado!r}"

    def test_ts_ms_to_brt_str_formato_completo(self) -> None:
        """ts_ms_to_brt_str() deve seguir 'YYYY-MM-DD HH:MM:SS BRT'."""
        from core.model2.time_utils import ts_ms_to_brt_str

        resultado = ts_ms_to_brt_str(1_700_000_000_000)
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} BRT", resultado), (
            f"Formato invalido: {resultado!r}"
        )

    def test_posix_to_brt_str_termina_em_brt(self) -> None:
        """posix_to_brt_str() deve retornar string terminando em ' BRT'."""
        from core.model2.time_utils import posix_to_brt_str

        resultado = posix_to_brt_str(1_700_000_000)
        assert resultado.endswith(" BRT"), f"posix_to_brt_str={resultado!r}"


# ---------------------------------------------------------------------------
# R3 — Persistencia UTC nao alterada
# ---------------------------------------------------------------------------

class TestPersistenciaUTCPreservada:
    """R3: Persistencia de timestamps permanece em UTC (int ms)."""

    def test_emit_stage_slo_violation_event_persiste_utc_int(self) -> None:
        """emit_stage_slo_violation_event deve persistir timestamp como int UTC ms."""
        from core.model2.live_service import emit_stage_slo_violation_event

        payload = emit_stage_slo_violation_event(
            stage="admissao",
            latency_ms=100,
            slo_ms=50,
        )
        ts = payload["timestamp"]
        assert isinstance(ts, int), f"timestamp deve ser int, got {type(ts)}"
        # Deve ser epoch ms (ordem de grandeza ~1.7 trilhao em 2024)
        assert ts > 1_600_000_000_000, f"timestamp parece invalido: {ts}"

    def test_cycle_report_nao_altera_signal_timestamp_ms(self) -> None:
        """SymbolReport instancia sem alterar timestamps UTC do repositorio."""
        from core.model2.cycle_report import SymbolReport

        r = SymbolReport(
            symbol="BTCUSDT",
            timeframe="5m",
            timestamp="2026-03-25 10:00:00 BRT",
            decision="HOLD",
            confidence=0.5,
            candle_state="fresh",
            freshness_reason="ok",
        )
        # SymbolReport nao tem campo signal_timestamp — persistencia e responsabilidade
        # do repositorio; apenas validamos que SymbolReport e instanciavel sem erro
        assert r.symbol == "BTCUSDT"

    def test_time_utils_nao_altera_timestamp_ms_persistido(self) -> None:
        """ts_ms_to_brt_str converte apenas para exibicao; int original inalterado."""
        from core.model2.time_utils import ts_ms_to_brt_str

        ts_original = 1_700_000_000_123
        _ = ts_ms_to_brt_str(ts_original)
        # O int original nao e mutavel — apenas verificamos que a funcao nao levanta
        assert ts_original == 1_700_000_000_123


# ---------------------------------------------------------------------------
# R1 (integracao) — cycle_report usa time_utils canonico internamente
# ---------------------------------------------------------------------------

class TestCycleReportUsaTimeUtils:
    """R1 integracao: cycle_report.py deve importar time_utils para exibicao."""

    def test_cycle_report_importa_time_utils(self) -> None:
        """cycle_report.py deve importar now_brt_str de core.model2.time_utils."""
        import ast
        import pathlib

        src = pathlib.Path("core/model2/cycle_report.py")
        tree = ast.parse(src.read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "time_utils" in node.module:
                    imports += [alias.name for alias in node.names]
        assert "now_brt_str" in imports, (
            f"cycle_report.py nao importa now_brt_str de time_utils. "
            f"Imports encontrados: {imports}"
        )

    def test_format_cycle_summary_nao_usa_strftime_com_pct_z(self) -> None:
        """format_cycle_summary nao deve usar strftime('%Z') — usa BRT canonico."""
        import ast
        import pathlib

        src = pathlib.Path("core/model2/cycle_report.py")
        tree = ast.parse(src.read_text(encoding="utf-8"))

        # Busca chamadas strftime com argumento contendo %Z
        violations: list[int] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "strftime":
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and "%Z" in str(arg.value):
                            violations.append(node.col_offset)
        assert not violations, (
            f"strftime('%Z') ainda presente em cycle_report.py "
            f"(col_offset={violations})"
        )
