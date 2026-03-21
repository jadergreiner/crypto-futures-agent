from __future__ import annotations

import numpy as np

from scripts.model2.rl_signal_generation_wrapper import _build_features


def test_build_features_gera_vetor_com_5_features() -> None:
    row = {
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "take_profit": 115.0,
        "signal_side": "LONG",
    }

    features = _build_features(row)  # type: ignore[arg-type]

    assert isinstance(features, np.ndarray)
    assert tuple(features.shape) == (5,)
    assert float(features[3]) == 3.0
    assert float(features[4]) == 1.0


def test_build_features_mapeia_short_para_feature_negativa() -> None:
    row = {
        "entry_price": 100.0,
        "stop_loss": 105.0,
        "take_profit": 85.0,
        "signal_side": "SHORT",
    }

    features = _build_features(row)  # type: ignore[arg-type]

    assert tuple(features.shape) == (5,)
    assert float(features[4]) == -1.0