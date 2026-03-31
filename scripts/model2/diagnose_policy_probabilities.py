#!/usr/bin/env python3
"""Diagnostico direto das probabilidades do policy PPO por acao.

Uso:
  python scripts/model2/diagnose_policy_probabilities.py --symbol BTCUSDT
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stable_baselines3 import PPO
import torch

from core.model2.model_inference_service import TechnicalSignalInferenceProvider


def _resolve_checkpoint(symbol: str) -> Path:
    symbol_ckpt = REPO_ROOT / "models" / "sub_agents" / f"{symbol}_entry_ppo.zip"
    if symbol_ckpt.exists():
        return symbol_ckpt
    default_ckpt = REPO_ROOT / "checkpoints" / "ppo_training" / "ppo_model.zip"
    return default_ckpt


def _adapt_features_for_model(model: Any, features: np.ndarray) -> np.ndarray:
    features_array = np.asarray(features, dtype=np.float32)
    obs_space = getattr(model, "observation_space", None)
    shape = getattr(obs_space, "shape", None)

    if not isinstance(shape, tuple):
        return features_array.reshape(1, -1) if features_array.ndim == 1 else features_array

    if features_array.ndim == 1 and len(shape) == 1:
        expected_size = int(shape[0])
        current_size = int(features_array.size)
        if current_size < expected_size:
            features_array = np.pad(
                features_array,
                (0, expected_size - current_size),
                mode="constant",
            )
        elif current_size > expected_size:
            features_array = features_array[:expected_size]
        return features_array.reshape(1, -1)

    if features_array.ndim == len(shape):
        return features_array

    return features_array.reshape(1, -1)


def _fetch_latest_decision_input(db_path: Path, symbol: str) -> dict[str, Any]:
    with sqlite3.connect(str(db_path), timeout=5) as conn:
        row = conn.execute(
            """
            SELECT id, action, confidence, reason_code, model_version, input_json, decision_timestamp
            FROM model_decisions
            WHERE symbol = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()

    if row is None:
        raise RuntimeError(f"Nenhuma decisao encontrada para {symbol}")

    (
        decision_id,
        action,
        confidence,
        reason_code,
        model_version,
        input_json,
        decision_timestamp,
    ) = row

    payload = json.loads(input_json or "{}")
    return {
        "decision_id": int(decision_id),
        "action": str(action or "HOLD"),
        "confidence": float(confidence or 0.0),
        "reason_code": str(reason_code or ""),
        "model_version": str(model_version or ""),
        "input": payload,
        "decision_timestamp": decision_timestamp,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostico de probabilidade por acao")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--db-path", default=str(REPO_ROOT / "db" / "modelo2.db"))
    args = parser.parse_args()

    symbol = str(args.symbol).upper()
    db_path = Path(args.db_path)

    decision = _fetch_latest_decision_input(db_path, symbol)
    model_input = decision["input"]

    market_state = model_input.get("market_state")
    risk_state = model_input.get("risk_state")
    position_state = model_input.get("position_state")

    if not isinstance(market_state, dict) or not isinstance(risk_state, dict) or not isinstance(position_state, dict):
        raise RuntimeError("input_json da decisao sem market_state/risk_state/position_state validos")

    # Reusa o mesmo builder de features do provider de inferencia.
    feature_source = type("FeatureSource", (), {
        "market_state": market_state,
        "risk_state": risk_state,
        "position_state": position_state,
        "decision_timestamp": decision.get("decision_timestamp"),
    })
    features = TechnicalSignalInferenceProvider._build_features(feature_source)  # type: ignore[arg-type]

    checkpoint = _resolve_checkpoint(symbol)
    if not checkpoint.exists():
        raise RuntimeError(f"Checkpoint nao encontrado: {checkpoint}")

    model = PPO.load(str(checkpoint))
    adapted = _adapt_features_for_model(model, features)

    with torch.no_grad():
        policy = model.policy
        obs_tensor = torch.as_tensor(adapted, device=policy.device)
        distribution = policy.get_distribution(obs_tensor)
        probs_tensor = getattr(distribution.distribution, "probs", None)
        if probs_tensor is None:
            raise RuntimeError("Policy nao expos probs na distribuicao")
        probs = probs_tensor.detach().cpu().numpy()[0]

    action_names = ["HOLD", "LONG", "SHORT"]
    p_hold, p_long, p_short = [float(v) for v in probs[:3]]
    top2 = sorted([p_hold, p_long, p_short], reverse=True)[:2]
    margin = float(top2[0] - top2[1]) if len(top2) == 2 else 0.0
    entropy = float(-(probs[:3] * np.log(np.clip(probs[:3], 1e-12, 1.0))).sum())

    print("=" * 72)
    print(f"DIAGNOSTICO PPO - {symbol}")
    print("=" * 72)
    print(f"decision_id={decision['decision_id']} | action_reportada={decision['action']} | confidence_reportada={decision['confidence']:.2%}")
    print(f"reason_code={decision['reason_code']} | model_version={decision['model_version']}")
    print(f"checkpoint={checkpoint}")
    print("-")
    print("Probabilidades diretas do policy (sem clamp):")
    print(f"  HOLD : {p_hold:.4f} ({p_hold:.2%})")
    print(f"  LONG : {p_long:.4f} ({p_long:.2%})")
    print(f"  SHORT: {p_short:.4f} ({p_short:.2%})")
    print("-")
    print(f"Top margin (1o - 2o): {margin:.4f} ({margin:.2%})")
    print(f"Entropia (3 acoes): {entropy:.4f}")

    # Explicar por que a confianca exibida pode diferir da probabilidade bruta.
    # No provider atual, a confianca final usa a probabilidade bruta clampada [0,1].
    expected_side = "LONG" if decision["action"] == "OPEN_LONG" else "SHORT" if decision["action"] == "OPEN_SHORT" else "HOLD"
    selected_prob = {
        "HOLD": p_hold,
        "LONG": p_long,
        "SHORT": p_short,
    }.get(expected_side, p_hold)
    confidence_after_rule = max(0.0, min(1.0, selected_prob))
    print("-")
    print(f"Probabilidade da acao esperada ({expected_side}): {selected_prob:.4f} ({selected_prob:.2%})")
    print(f"Confianca apos regra atual (max(0.0, min(1.0, p))): {confidence_after_rule:.4f} ({confidence_after_rule:.2%})")

    if abs(confidence_after_rule - float(decision["confidence"])) <= 0.02:
        print("[OK] Confianca reportada consistente com probabilidade bruta do policy.")
    else:
        print("[WARN] Diferenca relevante entre confianca reportada e calculada. Aguarde proximo ciclo para refletir regra nova.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
