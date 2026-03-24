"""Utilitarios de conversao e exibicao de timestamps para o ciclo M2.

Padrao adotado: toda exibicao ao operador usa horario de Brasilia (BRT).
Internamente, timestamps continuam em Unix milliseconds (inteiro).
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_BRT = ZoneInfo("America/Sao_Paulo")
_FMT_DISPLAY = "%Y-%m-%d %H:%M:%S BRT"
_FMT_DISPLAY_SHORT = "%Y-%m-%d %H:%M BRT"


def now_brt() -> datetime:
    """Retorna o instante atual em BRT."""
    return datetime.now(timezone.utc).astimezone(_BRT)


def now_brt_str() -> str:
    """Retorna o instante atual formatado em BRT para exibicao ao operador."""
    return now_brt().strftime(_FMT_DISPLAY)


def ts_ms_to_brt_str(ts_ms: int | float, *, short: bool = False) -> str:
    """Converte Unix milliseconds para string BRT de exibicao.

    Args:
        ts_ms: Timestamp em milissegundos desde epoch UTC.
        short: Se True, omite segundos (formato HH:MM).

    Returns:
        String no formato 'YYYY-MM-DD HH:MM:SS BRT' ou 'YYYY-MM-DD HH:MM BRT'.
    """
    dt = datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc).astimezone(_BRT)
    fmt = _FMT_DISPLAY_SHORT if short else _FMT_DISPLAY
    return dt.strftime(fmt)


def posix_to_brt_str(posix_seconds: int | float) -> str:
    """Converte segundos POSIX (stat().st_mtime) para string BRT de exibicao."""
    dt = datetime.fromtimestamp(float(posix_seconds), tz=timezone.utc).astimezone(_BRT)
    return dt.strftime(_FMT_DISPLAY)
