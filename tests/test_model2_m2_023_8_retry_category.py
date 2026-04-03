"""Suite RED para M2-023.8 — Política de retries orientada a categoria.

Cada teste mapeia 1 requisito do handoff SA->QA (RF-023.8.1 a RF-023.8.10).
Estado inicial esperado: FALHAR (comportamentos ausentes na implementacao stub).
"""

from __future__ import annotations

import importlib
from types import ModuleType
from unittest.mock import patch

import pytest


def _mod() -> ModuleType:
    return importlib.import_module("core.model2.resilience_controls")


@pytest.fixture(autouse=True)
def limpar_contadores() -> None:
    """Reseta contadores antes de cada teste para garantir isolamento."""
    mod = _mod()
    mod.reset_retry_counters()


# ---------------------------------------------------------------------------
# RF-023.8.1 — actual_attempts reflete tentativas reais (nao max_attempts)
# ---------------------------------------------------------------------------

def test_execute_transient_retries_traz_actual_attempts_real() -> None:
    """Categoria transient com 3 max_attempts e 2 falhas: actual_attempts == 3."""
    mod = _mod()
    chamadas: list[int] = []

    def fn() -> None:
        chamadas.append(1)
        if len(chamadas) < 3:
            raise ConnectionError("timeout simulado")

    resultado = mod.execute_with_category_retry(fn, category="transient",
                                                max_attempts=3)

    assert resultado["ok"] is True
    assert resultado["actual_attempts"] == 3, (
        f"Esperado actual_attempts=3, obteve {resultado.get('actual_attempts')}"
    )


# ---------------------------------------------------------------------------
# RF-023.8.2 — permanent interrompe apos 1 tentativa (actual_attempts == 1)
# ---------------------------------------------------------------------------

def test_execute_permanent_nao_reexecuta_actual_attempts_um() -> None:
    """Categoria permanent: falha imediata, actual_attempts deve ser 1."""
    mod = _mod()
    chamadas: list[int] = []

    def fn() -> None:
        chamadas.append(1)
        raise ValueError("erro permanente")

    resultado = mod.execute_with_category_retry(fn, category="permanent",
                                                max_attempts=5)

    assert resultado["ok"] is False
    assert len(chamadas) == 1, "Erro permanente nao deve gerar retry"
    assert resultado.get("actual_attempts") == 1, (
        f"Esperado actual_attempts=1, obteve {resultado.get('actual_attempts')}"
    )


# ---------------------------------------------------------------------------
# RF-023.8.3 — backoff entre retries transientes (sleep chamado)
# ---------------------------------------------------------------------------

def test_execute_transient_chama_sleep_entre_tentativas() -> None:
    """Retries transientes devem ter sleep de backoff entre tentativas."""
    mod = _mod()
    tentativas: list[int] = []

    def fn() -> None:
        tentativas.append(1)
        if len(tentativas) < 3:
            raise TimeoutError("timeout")

    with patch("time.sleep") as mock_sleep:
        mod.execute_with_category_retry(fn, category="transient", max_attempts=3)

    assert mock_sleep.call_count >= 1, (
        "Sleep deve ser chamado ao menos 1x entre retries transientes"
    )


# ---------------------------------------------------------------------------
# RF-023.8.4 — permanent nao chama sleep
# ---------------------------------------------------------------------------

def test_execute_permanent_nao_chama_sleep() -> None:
    """Categoria permanent nao deve ter sleep (sem retry)."""
    mod = _mod()

    def fn() -> None:
        raise ValueError("permanente")

    with patch("time.sleep") as mock_sleep:
        mod.execute_with_category_retry(fn, category="permanent", max_attempts=3)

    assert mock_sleep.call_count == 0, (
        "Permanent nao deve chamar sleep"
    )


# ---------------------------------------------------------------------------
# RF-023.8.5 — build_retry_category_report retorna contadores por categoria
# ---------------------------------------------------------------------------

def test_build_retry_category_report_retorna_contadores() -> None:
    """build_retry_category_report deve retornar dict com contagens por categoria."""
    mod = _mod()

    # Garantir estado limpo
    if hasattr(mod, "reset_retry_counters"):
        mod.reset_retry_counters()

    # Executar uma operacao transient (2 falhas + 1 sucesso)
    tentativas: list[int] = []

    def fn_transient() -> None:
        tentativas.append(1)
        if len(tentativas) < 3:
            raise ConnectionError("transient")

    with patch("time.sleep"):
        mod.execute_with_category_retry(fn_transient, category="transient",
                                        max_attempts=5)

    # Executar uma operacao permanent (falha imediata)
    def fn_permanent() -> None:
        raise ValueError("permanente")

    mod.execute_with_category_retry(fn_permanent, category="permanent",
                                    max_attempts=3)

    report = mod.build_retry_category_report()

    assert isinstance(report, dict), "Report deve ser dict"
    assert "transient" in report or "timeout" in report or "permanent" in report, (
        f"Report deve conter categorias usadas, obteve: {report}"
    )


# ---------------------------------------------------------------------------
# RF-023.8.6 — reset_retry_counters limpa estado acumulado
# ---------------------------------------------------------------------------

def test_reset_retry_counters_limpa_estado() -> None:
    """reset_retry_counters deve zerar contadores acumulados."""
    mod = _mod()

    # Verificar que a funcao existe
    assert hasattr(mod, "reset_retry_counters"), (
        "Funcao reset_retry_counters ausente em resilience_controls"
    )

    # Acumular algum estado
    tentativas: list[int] = []

    def fn() -> None:
        tentativas.append(1)
        if len(tentativas) < 2:
            raise ConnectionError("transient")

    with patch("time.sleep"):
        mod.execute_with_category_retry(fn, category="transient", max_attempts=3)

    # Resetar
    mod.reset_retry_counters()

    report = mod.build_retry_category_report()
    total = sum(v for v in report.values() if isinstance(v, (int, float)))

    assert total == 0, f"Apos reset contadores devem ser 0, obteve: {report}"


# ---------------------------------------------------------------------------
# RF-023.8.7 — resultado contem reason_code mapeado
# ---------------------------------------------------------------------------

def test_execute_resultado_contem_reason_code() -> None:
    """Resultado deve conter campo reason_code auditavel."""
    mod = _mod()

    def fn_ok() -> None:
        pass

    resultado = mod.execute_with_category_retry(fn_ok, category="transient",
                                                max_attempts=2)

    assert "reason_code" in resultado, (
        "Resultado deve conter reason_code para auditabilidade"
    )


# ---------------------------------------------------------------------------
# RF-023.8.8 — retrocompatibilidade: campos ok, category, should_retry preservados
# ---------------------------------------------------------------------------

def test_execute_retrocompat_campos_existentes_preservados() -> None:
    """Campos existentes (ok, category, should_retry) devem ser preservados."""
    mod = _mod()

    def fn() -> None:
        pass

    resultado = mod.execute_with_category_retry(fn, category="transient",
                                                max_attempts=2)

    assert "ok" in resultado
    assert "category" in resultado
    assert "should_retry" in resultado
    assert resultado["ok"] is True
    assert resultado["category"] == "transient"


# ---------------------------------------------------------------------------
# RF-023.8.9 — timeout trata como transient (retries com backoff)
# ---------------------------------------------------------------------------

def test_execute_timeout_categoria_retenta_igual_transient() -> None:
    """Categoria timeout deve ser tratada como transient (retentavel)."""
    mod = _mod()
    chamadas: list[int] = []

    def fn() -> None:
        chamadas.append(1)
        if len(chamadas) < 2:
            raise TimeoutError("timeout")

    with patch("time.sleep"):
        resultado = mod.execute_with_category_retry(fn, category="timeout",
                                                    max_attempts=3)

    assert resultado["ok"] is True
    assert len(chamadas) >= 2, "Timeout deve retry ate sucesso"


# ---------------------------------------------------------------------------
# RF-023.8.10 — fail-safe: excecao em fn nao propaga para o caller
# ---------------------------------------------------------------------------

def test_execute_excecao_nao_propaga_para_caller() -> None:
    """Falha em fn nunca deve propagar excecao para o caller (fail-safe)."""
    mod = _mod()

    def fn() -> None:
        raise RuntimeError("erro nao esperado")

    try:
        resultado = mod.execute_with_category_retry(fn, category="permanent",
                                                    max_attempts=1)
        assert resultado["ok"] is False
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"execute_with_category_retry nao deve propagar excecao: {exc}"
        ) from exc
