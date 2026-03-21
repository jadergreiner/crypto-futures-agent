from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace

import gymnasium as gym
import numpy as np

from scripts.model2 import ensemble_signal_generation_wrapper as wrapper
from scripts.model2.ensemble_signal_generation_wrapper import (
    EnsembleSignalGenerator,
    _build_real_observation,
    run_ensemble_signal_generation,
)


class _FakeModel:
    def __init__(self, shape: tuple[int, ...], action: int) -> None:
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=shape,
            dtype=np.float32,
        )
        self.action = action
        self.received_shapes: list[tuple[int, ...]] = []

    def predict(self, observation: np.ndarray, deterministic: bool = True):
        self.received_shapes.append(tuple(observation.shape))
        return np.array([self.action]), None


def test_generate_ensemble_signal_adapta_shape_para_lstm() -> None:
    generator = EnsembleSignalGenerator.__new__(EnsembleSignalGenerator)
    generator.voting_method = 'soft'
    generator.mlp_weight = 0.48
    generator.lstm_weight = 0.52
    generator.min_confidence = 0.6
    generator.fallback_used = 0
    generator.total_calls = 0
    generator.votes_diverged = 0

    mlp_model = _FakeModel((220,), 1)
    lstm_model = _FakeModel((10, 22), 1)
    generator.ensemble = SimpleNamespace(
        mlp_model=mlp_model,
        lstm_model=lstm_model,
    )

    observation = np.arange(220, dtype=np.float32)

    result = generator.generate_ensemble_signal(observation)

    assert result['method'] == 'ensemble_soft'
    assert mlp_model.received_shapes == [(220,)]
    assert lstm_model.received_shapes == [(10, 22)]


def test_generate_ensemble_signal_fallback_em_shape_incompativel() -> None:
    generator = EnsembleSignalGenerator.__new__(EnsembleSignalGenerator)
    generator.voting_method = 'soft'
    generator.mlp_weight = 0.48
    generator.lstm_weight = 0.52
    generator.min_confidence = 0.6
    generator.fallback_used = 0
    generator.total_calls = 0
    generator.votes_diverged = 0

    mlp_model = _FakeModel((220,), 1)
    lstm_model = _FakeModel((10, 22), 1)
    generator.ensemble = SimpleNamespace(
        mlp_model=mlp_model,
        lstm_model=lstm_model,
    )

    observation = np.arange(100, dtype=np.float32)

    result = generator.generate_ensemble_signal(observation)

    assert result['method'] == 'fallback_random'
    assert generator.fallback_used == 1


def test_generate_ensemble_signal_nao_faz_fallback_so_por_divergencia() -> None:
    generator = EnsembleSignalGenerator.__new__(EnsembleSignalGenerator)
    generator.voting_method = 'soft'
    generator.mlp_weight = 0.48
    generator.lstm_weight = 0.52
    generator.min_confidence = 0.6
    generator.fallback_used = 0
    generator.total_calls = 0
    generator.votes_diverged = 0

    mlp_model = _FakeModel((220,), 0)
    lstm_model = _FakeModel((10, 22), 1)
    generator.ensemble = SimpleNamespace(
        mlp_model=mlp_model,
        lstm_model=lstm_model,
    )

    observation = np.arange(220, dtype=np.float32)

    result = generator.generate_ensemble_signal(observation)

    assert result['method'] == 'ensemble_soft'
    assert result['action'] == 1
    assert result['confidence'] >= 0.6
    assert generator.fallback_used == 0


def test_generate_ensemble_signal_respeita_threshold_alto() -> None:
    generator = EnsembleSignalGenerator.__new__(EnsembleSignalGenerator)
    generator.voting_method = 'soft'
    generator.mlp_weight = 0.48
    generator.lstm_weight = 0.52
    generator.min_confidence = 0.8
    generator.fallback_used = 0
    generator.total_calls = 0
    generator.votes_diverged = 0

    mlp_model = _FakeModel((220,), 0)
    lstm_model = _FakeModel((10, 22), 1)
    generator.ensemble = SimpleNamespace(
        mlp_model=mlp_model,
        lstm_model=lstm_model,
    )

    observation = np.arange(220, dtype=np.float32)

    result = generator.generate_ensemble_signal(observation)

    assert result['method'] == 'fallback_random'
    assert generator.fallback_used == 1


def test_build_real_observation_deriva_snapshot_do_technical_signal() -> None:
    row = {
        'id': 11,
        'symbol': 'BTCUSDT',
        'signal_side': 'LONG',
        'entry_price': 105.0,
        'stop_loss': 100.0,
        'take_profit': 115.0,
    }
    payload = {
        'zone_low': 101.0,
        'zone_high': 109.0,
        'funding_rate': 0.0003,
        'open_interest': 250000.0,
    }

    observation = _build_real_observation(row, payload)

    assert observation.shape == (220,)
    assert np.allclose(observation[:22], observation[22:44])
    assert observation[0] == 105.0
    assert observation[1] == 115.0
    assert observation[2] == 100.0
    assert observation[3] == 105.0
    assert observation[15] == 0.0003
    assert observation[19] == 2.5


class _FakeEnsembleGenerator:
    def __init__(self, *args, **kwargs) -> None:
        self.observations: list[tuple[int, ...]] = []

    def generate_ensemble_signal(self, observation: np.ndarray):
        self.observations.append(tuple(observation.shape))
        return {
            'action': 1,
            'confidence': 0.73,
            'method': 'ensemble_soft',
            'voting_summary': {
                'mlp_vote': 1,
                'lstm_vote': 1,
                'consenso': 1.0,
                'divergence': False,
            },
        }

    def get_stats(self):
        return {
            'total_calls': len(self.observations),
            'fallback_used': 0,
            'fallback_rate': 0.0,
            'votes_diverged': 0,
            'divergence_rate': 0.0,
            'voting_method': 'soft',
            'min_confidence': 0.6,
        }

    def close(self) -> None:
        pass


def test_run_ensemble_signal_generation_persiste_resultado_no_payload(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / 'modelo2.db'
    output_dir = tmp_path / 'runtime'

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE technical_signals (
                id INTEGER PRIMARY KEY,
                opportunity_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                signal_side TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                signal_timestamp INTEGER NOT NULL,
                status TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO technical_signals (
                id, opportunity_id, symbol, timeframe, signal_side, entry_type,
                entry_price, stop_loss, take_profit, signal_timestamp, status,
                rule_id, payload_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                101,
                'BTCUSDT',
                'H4',
                'LONG',
                'MARKET',
                105.0,
                100.0,
                115.0,
                1_700_000_000_000,
                'CONSUMED',
                'M2-006.1',
                json.dumps({'zone_low': 101.0, 'zone_high': 109.0}, ensure_ascii=True),
                1_700_000_000_000,
                1_700_000_000_000,
            ),
        )
        conn.commit()

    fake_generator = _FakeEnsembleGenerator()
    monkeypatch.setattr(
        wrapper,
        'EnsembleSignalGenerator',
        lambda *args, **kwargs: fake_generator,
    )

    result = run_ensemble_signal_generation(
        model2_db_path=str(db_path),
        timeframe='H4',
        symbols=['BTCUSDT'],
        dry_run=False,
        output_dir=output_dir,
    )

    assert result['status'] == 'ok'
    assert result['ensemble_signals_generated'] == 1
    assert result['signals_enhanced'] == 1
    assert fake_generator.observations == [(220,)]

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            'SELECT payload_json FROM technical_signals WHERE id = 1'
        ).fetchone()

    payload = json.loads(row[0])
    assert payload['ensemble']['action'] == 1
    assert payload['ensemble']['confidence'] == 0.73
    assert payload['ensemble']['method'] == 'ensemble_soft'
    assert payload['ensemble']['observation_source'] == 'technical_signal_snapshot'