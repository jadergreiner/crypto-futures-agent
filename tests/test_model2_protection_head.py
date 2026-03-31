from __future__ import annotations

import numpy as np

from core.model2.protection_head import train_protection_head


def test_train_protection_head_predicts_valid_ranges() -> None:
    features = np.array(
        [
            [100.0, 102.0, 98.0, 1.0, 100.5, 0.01, -0.0002, 90000.0],
            [200.0, 206.0, 194.0, 1.0, 199.8, 0.02, -0.0001, 110000.0],
            [150.0, 153.0, 147.0, 1.0, 150.2, 0.015, -0.0003, 100000.0],
            [120.0, 124.0, 116.0, 1.0, 120.4, 0.013, -0.0004, 98000.0],
        ],
        dtype=float,
    )
    targets = np.array(
        [
            [0.95, 1.10],
            [1.05, 0.90],
            [0.90, 1.25],
            [1.10, 0.85],
        ],
        dtype=float,
    )

    model = train_protection_head(features=features, targets=targets, epochs=150)
    sl_mult, tp_mult = model.predict(features[0])

    assert 0.75 <= sl_mult <= 1.25
    assert 0.70 <= tp_mult <= 2.00


def test_train_protection_head_rejects_empty_samples() -> None:
    features = np.zeros((0, 8), dtype=float)
    targets = np.zeros((0, 2), dtype=float)

    try:
        train_protection_head(features=features, targets=targets)
        assert False, "esperado ValueError para sem_amostras"
    except ValueError as exc:
        assert "sem_amostras" in str(exc)
