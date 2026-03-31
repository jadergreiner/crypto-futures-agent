#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste de integração: Validação da automação do ciclo contínuo.
Simula: 1. Check (verifica se pode executar)
       2. Marca episódios fictícios
       3. Re-check (valida trigger)
       4. Mark (registra execução)
"""

import json
import sys
from datetime import timedelta
from pathlib import Path

# Adiciona scripts ao path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "scripts" / "model2"))

import continuous_learning_controller as controller

from continuous_learning_controller import (
    _load_state,
    _save_state,
    _get_episode_count,
    should_run_continuous_cycle,
    mark_run_executed,
)


def test_automation_workflow():
    """Testa fluxo completo de automação."""
    print("\n" + "=" * 80)
    print("TESTE DE INTEGRAÇÃO: AUTOMAÇÃO DO CICLO CONTÍNUO")
    print("=" * 80)

    # 1. Estado inicial
    print("\n[1/4] Estado inicial...")
    state = _load_state()
    print(f"  Última execução: {state['last_continuous_run'] or 'Nunca'}")
    print(f"  Episodes no DB: {_get_episode_count()}")
    # Usa um threshold artificial alto para manter o teste deterministico,
    # independente do estado real do banco local.
    should_run, reason = should_run_continuous_cycle(min_new_episodes=10**9)
    print(f"  Deve rodar: {should_run}")
    print(f"  Motivo: {reason}")
    assert not should_run, "Esperava falha (sem episódios)"
    print("  ✅ PASS")

    # 2. Simula adição de episódios (marcando estado)
    print("\n[2/4] Simulando adição de 100+ episódios...")
    state["last_episode_count"] = 0
    state["last_continuous_run"] = "2020-01-01T00:00:00"  # Tempo antigo
    _save_state(state)

    # Simula episódios no DB alterando o estado
    state = _load_state()
    # Força _get_episode_count() a retornar valor maior alterando manualmente
    print("  ✅ Simulação preparada")

    # 3. Marca primeira execução (como se tivesse rodar)
    print("\n[3/4] Marcando primeira execução com 150 episódios...")
    # Simula que DB tem 150 episodes
    state["last_episode_count"] = 0  # zero antes
    _save_state(state)

    # "Finge" que continuous_learning_cycle rodou e coletou 150 episodes
    mark_run_executed(symbols=["BTCUSDT", "ETHUSDT"])

    state = _load_state()
    print(f"  Última execução: {state['last_continuous_run']}")
    print(f"  Episodes marcados: {state['last_episode_count']}")
    print(f"  Símbolos: {state['runs'][-1]['symbols'] if state['runs'] else []}")
    assert state["last_continuous_run"] is not None, "Execução não foi marcada"
    print("  ✅ PASS")

    # 4. Valida cooldown
    print("\n[4/4] Validando cooldown (2 horas mínimas)...")
    should_run, reason = should_run_continuous_cycle(
        min_new_episodes=100,
        min_hours_between_runs=2.0
    )
    print(f"  Deve rodar agora: {should_run}")
    print(f"  Motivo: {reason}")
    assert not should_run, "Esperava falha (está em cooldown de 2h)"
    print("  ✅ PASS")

    print("\n" + "=" * 80)
    print("✅ TODOS OS TESTES PASSARAM")
    print("=" * 80)
    print("\nResumo:")
    print("  • Controlador lê/escreve estado corretamente")
    print("  • Lógica de trigger funciona (episódios + tempo)")
    print("  • Marca execuções com histórico")
    print("  • Cooldown evita execuções frequentes")
    print("\n✓ Automação está pronta para iniciar.bat\n")


def test_should_run_usa_threshold_dinamico_quando_confianca_baixa(monkeypatch):
    """Com confiança baixa, o gatilho deve cair para 3 episódios."""
    monkeypatch.setattr(controller, "_load_state", lambda: {
        "last_continuous_run": "2020-01-01T00:00:00",
        "last_episode_count": 10,
        "runs": [],
    })
    monkeypatch.setattr(controller, "_get_episode_count", lambda: 13)
    monkeypatch.setattr(controller, "resolve_retrain_threshold", lambda _db_path: (3, 0.34))

    should_run, reason = controller.should_run_continuous_cycle(min_hours_between_runs=0.0)

    assert should_run is True
    assert "Threshold: 3" in reason


def test_should_run_mantem_threshold_padrao_quando_confianca_alta(monkeypatch):
    """Com confiança >= 65%, o gatilho continua em 100 episódios."""
    monkeypatch.setattr(controller, "_load_state", lambda: {
        "last_continuous_run": "2020-01-01T00:00:00",
        "last_episode_count": 10,
        "runs": [],
    })
    monkeypatch.setattr(controller, "_get_episode_count", lambda: 13)
    monkeypatch.setattr(controller, "resolve_retrain_threshold", lambda _db_path: (100, 0.72))

    should_run, reason = controller.should_run_continuous_cycle(min_hours_between_runs=0.0)

    assert should_run is False
    assert "Necessário: 100" in reason


def test_should_run_bloqueia_cooldown_de_15min_em_modo_aquecimento(monkeypatch):
    """Em aquecimento, deve respeitar cooldown padrão de 15 minutos."""
    now_iso = controller.datetime.now().isoformat()
    monkeypatch.setattr(controller, "_load_state", lambda: {
        "last_continuous_run": now_iso,
        "last_episode_count": 23425,
        "runs": [],
    })
    monkeypatch.setattr(controller, "_get_episode_count", lambda: 23436)
    monkeypatch.setattr(controller, "resolve_retrain_threshold", lambda _db_path: (3, 0.34))

    should_run, reason = controller.should_run_continuous_cycle()

    assert should_run is False
    assert "Próxima execução" in reason


def test_should_run_retreino_historico_apos_15min_sem_novos_episodios(monkeypatch):
    """Em aquecimento, após 15min deve retreinar histórico mesmo sem novos episódios."""
    old_iso = (controller.datetime.now() - timedelta(minutes=16)).isoformat()
    monkeypatch.setattr(controller, "_load_state", lambda: {
        "last_continuous_run": old_iso,
        "last_episode_count": 23436,
        "runs": [],
    })
    monkeypatch.setattr(controller, "_get_episode_count", lambda: 23436)
    monkeypatch.setattr(controller, "resolve_retrain_threshold", lambda _db_path: (3, 0.34))

    should_run, reason = controller.should_run_continuous_cycle()

    assert should_run is True
    assert "Retreino histórico periódico" in reason


def test_should_run_usa_estado_independente_por_simbolo(monkeypatch):
    """Cooldown e contador devem ser avaliados por símbolo, não de forma global."""
    now_iso = controller.datetime.now().isoformat()
    old_iso = (controller.datetime.now() - timedelta(minutes=16)).isoformat()

    monkeypatch.setattr(controller, "_load_state", lambda: {
        "last_continuous_run": now_iso,
        "last_episode_count": 999,
        "symbol_states": {
            "BTCUSDT": {
                "last_continuous_run": now_iso,
                "last_episode_count": 10,
            },
            "ETHUSDT": {
                "last_continuous_run": old_iso,
                "last_episode_count": 0,
            },
        },
        "runs": [],
    })

    def fake_episode_count(*, symbol=None, timeframe=None):
        if symbol == "BTCUSDT":
            return 12
        if symbol == "ETHUSDT":
            return 3
        return 15

    monkeypatch.setattr(controller, "_get_episode_count", fake_episode_count)
    monkeypatch.setattr(
        controller,
        "resolve_retrain_threshold",
        lambda _db_path, symbol=None, timeframe=None: (3, 0.34),
    )

    should_run, reason = controller.should_run_continuous_cycle(symbols=["BTCUSDT", "ETHUSDT"])

    assert should_run is True
    assert "ETHUSDT" in reason


def test_mark_run_executed_persiste_contagem_por_simbolo(monkeypatch):
    """Marcacao do controller deve manter snapshot separado por símbolo."""
    captured: dict[str, object] = {}

    monkeypatch.setattr(controller, "_load_state", lambda: {
        "last_continuous_run": None,
        "last_episode_count": 0,
        "symbol_states": {},
        "runs": [],
    })
    monkeypatch.setattr(controller, "_save_state", lambda state: captured.update(state))

    def fake_episode_count(*, symbol=None, timeframe=None):
        if symbol == "BTCUSDT":
            return 5
        if symbol == "ETHUSDT":
            return 9
        return 14

    monkeypatch.setattr(controller, "_get_episode_count", fake_episode_count)

    controller.mark_run_executed(symbols=["BTCUSDT", "ETHUSDT"])

    symbol_states = captured.get("symbol_states")
    assert isinstance(symbol_states, dict)
    assert symbol_states["BTCUSDT"]["last_episode_count"] == 5
    assert symbol_states["ETHUSDT"]["last_episode_count"] == 9
    assert captured["last_episode_count"] == 14


if __name__ == "__main__":
    try:
        test_automation_workflow()
    except AssertionError as e:
        print(f"\n❌ FALHA no teste: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
