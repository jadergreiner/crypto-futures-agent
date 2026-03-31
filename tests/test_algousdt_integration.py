"""
Testes de integracao para ALGOUSDT no ciclo M2.

Valida:
- Configuracao do simbolo em config/symbols.py
- Propagacao automatica para ALL_SYMBOLS e AUTHORIZED_SYMBOLS
- Fallback de escopo em config/settings.py
- Existencia e export do playbook dedicado ALGOPlaybook
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

from config.execution_config import AUTHORIZED_SYMBOLS
from config.settings import _normalize_symbol_scope
from config.symbols import ALL_SYMBOLS, SYMBOLS
from playbooks.base_playbook import BasePlaybook


def _get_algo_config() -> dict[str, Any]:
    """Retorna a configuracao de ALGOUSDT ou falha com mensagem clara."""
    if "ALGOUSDT" not in SYMBOLS:
        pytest.fail("ALGOUSDT nao encontrado em config/symbols.py")
    return SYMBOLS["ALGOUSDT"]


def _get_algo_playbook_class() -> Any:
    """Importa ALGOPlaybook do pacote principal ou falha com mensagem clara."""
    pacote = importlib.import_module("playbooks")
    classe = getattr(pacote, "ALGOPlaybook", None)
    if classe is None:
        pytest.fail("ALGOPlaybook nao exportado em playbooks/__init__.py")
    if not issubclass(classe, BasePlaybook):
        pytest.fail("ALGOPlaybook deve herdar de BasePlaybook")
    return classe


def test_algousdt_presente_em_symbols() -> None:
    """ALGOUSDT deve estar definido em SYMBOLS."""
    assert "ALGOUSDT" in SYMBOLS, "ALGOUSDT nao encontrado em config/symbols.py"


def test_algousdt_campos_obrigatorios() -> None:
    """ALGOUSDT deve expor todos os campos obrigatorios do cadastro."""
    config = _get_algo_config()
    for campo in (
        "papel",
        "ciclo_proprio",
        "correlacao_btc",
        "beta_estimado",
        "classificacao",
        "caracteristicas",
    ):
        assert campo in config, f"Campo obrigatorio ausente: {campo}"


def test_algousdt_beta_em_faixa_coerente() -> None:
    """ALGOUSDT deve manter beta moderado, sem perfil de memecoin."""
    beta = _get_algo_config()["beta_estimado"]
    assert 0.8 <= beta <= 2.5, f"Beta {beta} fora da faixa esperada para ALGOUSDT"


def test_algousdt_classificacao_nao_vazia() -> None:
    """ALGOUSDT deve ter classificacao textual explicita."""
    classificacao = _get_algo_config()["classificacao"]
    assert isinstance(classificacao, str) and classificacao.strip()


def test_algousdt_em_all_symbols() -> None:
    """ALGOUSDT deve aparecer em ALL_SYMBOLS."""
    assert "ALGOUSDT" in ALL_SYMBOLS


def test_authorized_symbols_derivado_de_all_symbols() -> None:
    """AUTHORIZED_SYMBOLS deve continuar derivado de ALL_SYMBOLS sem hardcode."""
    assert AUTHORIZED_SYMBOLS == set(ALL_SYMBOLS)


def test_algousdt_em_authorized_symbols() -> None:
    """ALGOUSDT deve estar na whitelist automatica de execucao."""
    assert "ALGOUSDT" in AUTHORIZED_SYMBOLS


def test_normalize_symbol_scope_expande_fallback_com_algousdt() -> None:
    """Fallback ALL_SYMBOLS deve carregar ALGOUSDT para o escopo M2."""
    scope = _normalize_symbol_scope("ALL_SYMBOLS:", fallback_symbols=ALL_SYMBOLS)
    assert "ALGOUSDT" in scope


def test_modulo_algo_playbook_existe() -> None:
    """Deve existir um modulo dedicado playbooks.algo_playbook."""
    modulo = importlib.import_module("playbooks.algo_playbook")
    assert hasattr(modulo, "ALGOPlaybook")


def test_algo_playbook_exportado_no_pacote() -> None:
    """ALGOPlaybook deve ser exportado pelo pacote playbooks."""
    classe = _get_algo_playbook_class()
    assert classe.__name__ == "ALGOPlaybook"


def test_algo_playbook_instancia_basica() -> None:
    """ALGOPlaybook deve ser instanciavel e carregar ALGOUSDT como symbol."""
    playbook_class = _get_algo_playbook_class()
    playbook = playbook_class()
    assert playbook.symbol == "ALGOUSDT"


def test_algo_playbook_get_info_campos_esperados() -> None:
    """get_info() deve expor os campos basicos do playbook."""
    playbook_class = _get_algo_playbook_class()
    playbook = playbook_class()
    info = playbook.get_info()
    for campo in (
        "symbol",
        "papel",
        "ciclo",
        "correlacao_btc",
        "beta",
        "classificacao",
    ):
        assert campo in info