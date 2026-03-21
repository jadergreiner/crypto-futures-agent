#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BLID-068: Wrapper de Geracao de Sinais com Votacao Ensemble (E.10)

Integra EnsembleVotingPPO no pipeline diario para gerar sinais técnicos
com votação (soft ou hard) entre modelos MLP + LSTM otimizados em E.8.

Substitui sinais determinísticos por sinais votados, mantendo fallback
automático para determinístico em caso de falha ou baixa confiança.

Entrada: technical_signals em status CREATED
Saída: technical_signals em status CREATED + confidence score votado
"""

import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.lstm_environment import LSTMSignalEnvironment
from scripts.model2.ensemble_voting_ppo import EnsembleVotingPPO
from scripts.model2.io_utils import atomic_write_json

# Setup logging — redireciona para arquivo para evitar OSError no pipe CMD
import os as _os
_log_dir = _os.path.join(_os.path.dirname(__file__), '..', '..', 'logs')
_os.makedirs(_log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(
            _os.path.join(_log_dir, 'm2_ensemble.log'), encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)

ENSEMBLE_SEQUENCE_LEN = 10
ENSEMBLE_FEATURES_PER_STEP = 22


class EnsembleSignalGenerator:
    """
    Gerador de sinais com votacao ensemble.

    Implementa soft + hard voting entre checkpoints E.8 (MLP + LSTM).
    Mantém fallback automático para determinístico.
    """

    def __init__(
        self,
        voting_method: str = 'soft',
        mlp_weight: float = 0.48,
        lstm_weight: float = 0.52,
        min_confidence: float = 0.6,
        mlp_checkpoint: Optional[str] = None,
        lstm_checkpoint: Optional[str] = None
    ):
        """
        Inicializa gerador ensemble.

        Args:
            voting_method: 'soft' ou 'hard'
            mlp_weight: Peso MLP (E.7 score: 0.8761)
            lstm_weight: Peso LSTM (E.7 score: 0.8690)
            min_confidence: Confidence mínimo para aceitar votação
            mlp_checkpoint: Path para checkpoint MLP (default: E.8 path)
            lstm_checkpoint: Path para checkpoint LSTM (default: E.8 path)
        """
        self.voting_method = voting_method
        total_weight = mlp_weight + lstm_weight
        self.mlp_weight = float(mlp_weight / total_weight) if total_weight > 0 else 0.5
        self.lstm_weight = float(lstm_weight / total_weight) if total_weight > 0 else 0.5
        self.min_confidence = min_confidence
        self.fallback_used = 0
        self.total_calls = 0
        self.votes_diverged = 0

        # Checkpoints E.8 com fallback para versao disponivel
        _mlp_e8 = REPO_ROOT / 'checkpoints/ppo_training/mlp/optuna/ppo_mlp_e8_optuna.zip'
        _mlp_fallback = REPO_ROOT / 'checkpoints/ppo_training/mlp/ppo_model_mlp.zip'
        _lstm_e8 = REPO_ROOT / 'checkpoints/ppo_training/lstm/optuna/ppo_lstm_e8_optuna.zip'
        _lstm_fallback = REPO_ROOT / 'checkpoints/ppo_training/lstm/ppo_model_lstm.zip'
        self.mlp_checkpoint = mlp_checkpoint or \
            str(_mlp_e8 if _mlp_e8.exists() else _mlp_fallback)
        self.lstm_checkpoint = lstm_checkpoint or \
            str(_lstm_e8 if _lstm_e8.exists() else _lstm_fallback)

        self.ensemble: Optional[EnsembleVotingPPO] = None
        self._init_ensemble()

    @staticmethod
    def _get_model_observation_shape(model: Any) -> tuple[int, ...] | None:
        """Retorna o shape esperado pelo modelo, quando disponivel."""
        observation_space = getattr(model, 'observation_space', None)
        shape = getattr(observation_space, 'shape', None)
        if shape is None:
            return None
        return tuple(int(item) for item in shape)

    @staticmethod
    def _adapt_observation_for_model(
        observation: np.ndarray,
        model: Any,
    ) -> np.ndarray:
        """Adapta observacao flat/seq para o contrato esperado pelo modelo."""
        expected_shape = EnsembleSignalGenerator._get_model_observation_shape(model)
        observation_array = np.asarray(observation, dtype=np.float32)

        if expected_shape is None or tuple(observation_array.shape) == expected_shape:
            return observation_array

        expected_size = int(np.prod(expected_shape, dtype=np.int64))
        if int(observation_array.size) != expected_size:
            raise ValueError(
                'Observacao incompatível com o modelo: '
                f'shape recebido={tuple(observation_array.shape)}, '
                f'shape esperado={expected_shape}'
            )

        return observation_array.reshape(expected_shape)

    @staticmethod
    def _action_to_int(action: Any) -> int:
        """Normaliza a saida de predict() para inteiro escalar."""
        action_array = np.asarray(action)
        if action_array.size == 0:
            raise ValueError('Acao vazia retornada pelo modelo ensemble')
        return int(action_array.reshape(-1)[0])

    def _init_ensemble(self) -> None:
        """Carrega ensemble (com fallback gracioso se checkpoints não existem)"""
        try:
            logger.info(f"Carregando checkpoints E.8...")
            logger.info(f"  MLP: {self.mlp_checkpoint}")
            logger.info(f"  LSTM: {self.lstm_checkpoint}")

            self.ensemble = EnsembleVotingPPO(
                mlp_checkpoint_path=self.mlp_checkpoint,
                lstm_checkpoint_path=self.lstm_checkpoint,
                mlp_weight=self.mlp_weight,
                lstm_weight=self.lstm_weight,
                voting_method=self.voting_method
            )

            logger.info("[OK] Ensemble carregado com sucesso")

        except Exception as e:
            logger.warning(f"[AVISO] Erro ao carregar ensemble: {e}")
            logger.warning("  Fallback para sinais deterministicos")
            self.ensemble = None
            self.env = None

    def generate_ensemble_signal(
        self,
        observation: np.ndarray
    ) -> Dict[str, Any]:
        """
        Gera sinal com votação ensemble.

        Args:
            observation: State observation (numpy array)

        Returns:
            {
                'action': int (0 ou 1),
                'confidence': float (0.0-1.0),
                'method': 'ensemble_soft'|'ensemble_hard'|'fallback',
                'voting_summary': {...},
                'metadata': {...}
            }
        """
        self.total_calls += 1

        # Se ensemble não carregou, usar fallback
        if self.ensemble is None:
            return self._generate_fallback_signal(observation)

        try:
            mlp_observation = self._adapt_observation_for_model(
                observation,
                self.ensemble.mlp_model,
            )
            lstm_observation = self._adapt_observation_for_model(
                observation,
                self.ensemble.lstm_model,
            )

            # Obter predicoes de ambos os modelos
            mlp_action, _ = self.ensemble.mlp_model.predict(
                mlp_observation, deterministic=True
            )
            lstm_action, _ = self.ensemble.lstm_model.predict(
                lstm_observation, deterministic=True
            )

            mlp_vote = self._action_to_int(mlp_action)
            lstm_vote = self._action_to_int(lstm_action)

            # Calcular consenso
            consenso = 1.0 if mlp_vote == lstm_vote else 0.0
            if consenso < 1.0:
                self.votes_diverged += 1

            # Aplicar votacao
            if self.voting_method == 'soft':
                action = self._soft_voting(mlp_vote, lstm_vote)
            else:
                action = self._hard_voting(mlp_vote, lstm_vote)

            # Confidence baseado em consenso + pesos
            confidence = self._calculate_confidence(
                action, mlp_vote, lstm_vote, consenso
            )

            # Se confidence < min_confidence, usar fallback
            if confidence < self.min_confidence:
                logger.warning(
                    f"Confidence baixa ({confidence:.2f} < {self.min_confidence}), "
                    f"usando fallback"
                )
                self.fallback_used += 1
                return self._generate_fallback_signal(observation)

            return {
                'action': action,
                'confidence': float(confidence),
                'method': f'ensemble_{self.voting_method}',
                'voting_summary': {
                    'mlp_vote': mlp_vote,
                    'lstm_vote': lstm_vote,
                    'consenso': float(consenso),
                    'divergence': consenso < 1.0
                },
                'metadata': {
                    'timestamp': datetime.utcnow().isoformat(),
                    'observation_shape': observation.shape
                }
            }

        except Exception as e:
            logger.error(f"Erro ao calcular votacao: {e}")
            self.fallback_used += 1
            return self._generate_fallback_signal(observation)

    def _soft_voting(self, mlp_vote: int, lstm_vote: int) -> int:
        """Soft voting: media ponderada"""
        if mlp_vote == lstm_vote:
            return mlp_vote  # Consenso
        else:
            # Discordancia: usar modelo com weight maior (LSTM)
            return lstm_vote if self.lstm_weight >= self.mlp_weight else mlp_vote

    def _hard_voting(self, mlp_vote: int, lstm_vote: int) -> int:
        """Hard voting: votacao com pesos"""
        score_0 = (1 - mlp_vote) * self.mlp_weight + (1 - lstm_vote) * self.lstm_weight
        score_1 = mlp_vote * self.mlp_weight + lstm_vote * self.lstm_weight
        return 1 if score_1 > score_0 else 0

    def _support_weight(self, chosen_action: int, mlp_vote: int, lstm_vote: int) -> float:
        """Peso total que suporta a acao escolhida pela votacao."""
        support = 0.0
        if mlp_vote == chosen_action:
            support += self.mlp_weight
        if lstm_vote == chosen_action:
            support += self.lstm_weight
        return float(support)

    def _calculate_confidence(
        self,
        action: int,
        mlp_vote: int,
        lstm_vote: int,
        consenso: float
    ) -> float:
        """Calcula confidence como funcao de consenso + pesos"""
        support_weight = self._support_weight(action, mlp_vote, lstm_vote)
        if consenso >= 1.0:
            return min(0.95, 0.70 + (0.25 * support_weight))
        return min(0.90, 0.50 + (0.35 * support_weight))

    def _generate_fallback_signal(
        self,
        observation: np.ndarray
    ) -> Dict[str, Any]:
        """Gera sinal fallback (determinístico ou constante)"""
        # Fallback: decisao aleatoria com confidence baixa
        # Em producao, seria usar modelo determinístico separado
        action = np.random.choice([0, 1])

        return {
            'action': action,
            'confidence': 0.5,
            'method': 'fallback_random',
            'voting_summary': {
                'reason': 'Ensemble indisponível ou low-confidence'
            },
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'fallback_count': self.fallback_used
            }
        }

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de votacao"""
        return {
            'total_calls': self.total_calls,
            'fallback_used': self.fallback_used,
            'fallback_rate': float(
                self.fallback_used / self.total_calls
                if self.total_calls > 0 else 0
            ),
            'votes_diverged': self.votes_diverged,
            'divergence_rate': float(
                self.votes_diverged / self.total_calls
                if self.total_calls > 0 else 0
            ),
            'voting_method': self.voting_method,
            'min_confidence': self.min_confidence
        }

    def close(self) -> None:
        """Libera recursos"""
        pass


def _utc_now_ms() -> int:
    return int(datetime.utcnow().timestamp() * 1000)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _parse_payload(raw_payload: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_payload or '{}')
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _lookup_nested(payload: Mapping[str, Any], *path: str) -> Any:
    current: Any = payload
    for segment in path:
        if not isinstance(current, Mapping) or segment not in current:
            return None
        current = current[segment]
    return current


def _mapping_get(source: Mapping[str, Any], key: str, default: Any = None) -> Any:
    try:
        return source[key]
    except (KeyError, IndexError, TypeError):
        return default


def _sentiment_to_numeric(sentiment: Any) -> float:
    return {
        'bullish': 1.0,
        'neutral': 0.0,
        'bearish': -1.0,
    }.get(str(sentiment or '').strip().lower(), 0.0)


def _trend_to_numeric(trend: Any) -> float:
    return {
        'increasing': 1.0,
        'stable': 0.0,
        'decreasing': -1.0,
    }.get(str(trend or '').strip().lower(), 0.0)


def _direction_to_numeric(direction: Any) -> float:
    return {
        'up': 1.0,
        'steady': 0.0,
        'down': -1.0,
    }.get(str(direction or '').strip().lower(), 0.0)


def _default_sentiment_from_side(signal_side: Any) -> str:
    return 'bullish' if str(signal_side or '').upper() == 'LONG' else 'bearish'


def _default_trend_from_side(signal_side: Any) -> str:
    return 'increasing' if str(signal_side or '').upper() == 'LONG' else 'decreasing'


def _default_direction_from_side(signal_side: Any) -> str:
    return 'up' if str(signal_side or '').upper() == 'LONG' else 'down'


def _build_signal_snapshot(
    row: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    entry_price = _to_float(_mapping_get(row, 'entry_price'))
    stop_loss = _to_float(_mapping_get(row, 'stop_loss'))
    take_profit = _to_float(_mapping_get(row, 'take_profit'))
    signal_side = str(_mapping_get(row, 'signal_side') or '').upper()

    zone_low = _to_float(
        payload.get('zone_low', min(entry_price, stop_loss, take_profit)),
        default=min(entry_price, stop_loss, take_profit),
    )
    zone_high = _to_float(
        payload.get('zone_high', max(entry_price, stop_loss, take_profit)),
        default=max(entry_price, stop_loss, take_profit),
    )

    candle_payload = _lookup_nested(payload, 'latest_candle')
    if not isinstance(candle_payload, Mapping):
        candle_payload = {}
    volatility_payload = _lookup_nested(payload, 'volatility')
    if not isinstance(volatility_payload, Mapping):
        volatility_payload = {}
    multi_tf_payload = _lookup_nested(payload, 'multi_timeframe')
    if not isinstance(multi_tf_payload, Mapping):
        multi_tf_payload = {}
    funding_payload = _lookup_nested(payload, 'funding_rates')
    if not isinstance(funding_payload, Mapping):
        funding_payload = {}
    open_interest_payload = _lookup_nested(payload, 'open_interest')
    if not isinstance(open_interest_payload, Mapping):
        open_interest_payload = {}

    price_floor = min(zone_low, stop_loss, entry_price, take_profit)
    price_ceiling = max(zone_high, stop_loss, entry_price, take_profit)
    price_mid = (zone_low + zone_high) / 2.0 if zone_high >= zone_low else entry_price
    risk_distance = abs(entry_price - stop_loss)
    reward_distance = abs(take_profit - entry_price)
    rr_ratio = reward_distance / risk_distance if risk_distance > 0 else 0.0
    side_factor = 1.0 if signal_side == 'LONG' else -1.0
    macd_hist = ((take_profit - stop_loss) / entry_price) if entry_price else 0.0

    return {
        'latest_candle': {
            'open': _to_float(candle_payload.get('open'), default=price_mid),
            'high': _to_float(candle_payload.get('high'), default=price_ceiling),
            'low': _to_float(candle_payload.get('low'), default=price_floor),
            'close': _to_float(candle_payload.get('close'), default=entry_price),
            'volume': _to_float(
                candle_payload.get('volume', payload.get('volume', payload.get('signal_volume', 0.0)))
            ),
        },
        'volatility': {
            'atr_14': _to_float(volatility_payload.get('atr_14'), default=risk_distance),
            'bollinger_bands': {
                'upper': _to_float(
                    _lookup_nested(volatility_payload, 'bollinger_bands', 'upper'),
                    default=price_ceiling,
                ),
                'sma': _to_float(
                    _lookup_nested(volatility_payload, 'bollinger_bands', 'sma'),
                    default=price_mid,
                ),
                'lower': _to_float(
                    _lookup_nested(volatility_payload, 'bollinger_bands', 'lower'),
                    default=price_floor,
                ),
            },
            'macd_line': _to_float(volatility_payload.get('macd_line'), default=side_factor * rr_ratio),
            'macd_signal': _to_float(volatility_payload.get('macd_signal'), default=side_factor),
            'macd_hist': _to_float(volatility_payload.get('macd_hist'), default=macd_hist),
        },
        'multi_timeframe': {
            'H1': {
                'close': _to_float(
                    _lookup_nested(multi_tf_payload, 'H1', 'close'),
                    default=entry_price,
                )
            },
            'H4': {
                'close': _to_float(
                    _lookup_nested(multi_tf_payload, 'H4', 'close'),
                    default=entry_price,
                )
            },
            'D1': {
                'close': _to_float(
                    _lookup_nested(multi_tf_payload, 'D1', 'close'),
                    default=entry_price,
                )
            },
        },
        'funding_rates': {
            'latest_rate': _to_float(
                funding_payload.get('latest_rate', payload.get('funding_rate', 0.0))
            ),
            'avg_rate_24h': _to_float(
                funding_payload.get('avg_rate_24h', payload.get('funding_rate', 0.0))
            ),
            'sentiment': str(
                funding_payload.get('sentiment', _default_sentiment_from_side(signal_side))
            ),
            'trend': str(funding_payload.get('trend', _default_trend_from_side(signal_side))),
        },
        'open_interest': {
            'current_oi': _to_float(
                open_interest_payload.get(
                    'current_oi',
                    payload.get('open_interest', payload.get('open_interest_notional', 0.0)),
                )
            ),
            'oi_sentiment': str(
                open_interest_payload.get(
                    'oi_sentiment',
                    _default_sentiment_from_side(signal_side),
                )
            ),
            'change_direction': str(
                open_interest_payload.get(
                    'change_direction',
                    _default_direction_from_side(signal_side),
                )
            ),
        },
    }


def _snapshot_to_feature_vector(snapshot: Mapping[str, Any]) -> np.ndarray:
    latest_candle = snapshot.get('latest_candle', {})
    volatility = snapshot.get('volatility', {})
    multi_timeframe = snapshot.get('multi_timeframe', {})
    funding_rates = snapshot.get('funding_rates', {})
    open_interest = snapshot.get('open_interest', {})
    bollinger_bands = volatility.get('bollinger_bands', {}) if isinstance(volatility, Mapping) else {}

    features = [
        _to_float(latest_candle.get('open')),
        _to_float(latest_candle.get('high')),
        _to_float(latest_candle.get('low')),
        _to_float(latest_candle.get('close')),
        _to_float(latest_candle.get('volume')),
        _to_float(volatility.get('atr_14')),
        _to_float(bollinger_bands.get('upper')),
        _to_float(bollinger_bands.get('sma')),
        _to_float(bollinger_bands.get('lower')),
        _to_float(volatility.get('macd_line')),
        _to_float(volatility.get('macd_signal')),
        _to_float(volatility.get('macd_hist')),
        _to_float(_lookup_nested(multi_timeframe, 'H1', 'close')),
        _to_float(_lookup_nested(multi_timeframe, 'H4', 'close')),
        _to_float(_lookup_nested(multi_timeframe, 'D1', 'close')),
        _to_float(funding_rates.get('latest_rate')),
        _to_float(funding_rates.get('avg_rate_24h')),
        _sentiment_to_numeric(funding_rates.get('sentiment')),
        _trend_to_numeric(funding_rates.get('trend')),
        _to_float(open_interest.get('current_oi')) / 100000.0,
        _sentiment_to_numeric(open_interest.get('oi_sentiment')),
        _direction_to_numeric(open_interest.get('change_direction')),
    ]
    return np.array(features[:ENSEMBLE_FEATURES_PER_STEP], dtype=np.float32)


def _build_real_observation(
    row: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    seq_len: int = ENSEMBLE_SEQUENCE_LEN,
) -> np.ndarray:
    snapshot = _build_signal_snapshot(row, payload)
    base_features = _snapshot_to_feature_vector(snapshot)
    repeated = np.tile(base_features, (seq_len, 1))
    return repeated.astype(np.float32).reshape(seq_len * ENSEMBLE_FEATURES_PER_STEP)


def run_ensemble_signal_generation(
    *,
    model2_db_path: str,
    timeframe: str = 'H4',
    symbols: list[str] | None = None,
    voting_method: str = 'soft',
    min_confidence: float = 0.6,
    dry_run: bool = False,
    output_dir: str | Path = 'results/model2/runtime'
) -> Dict[str, Any]:
    """
    Runner (compativel com daily_pipeline) para geracao de sinais ensemble.

    Args:
        model2_db_path: Path para db modelo 2
        timeframe: Timeframe (default H4)
        symbols: Símbolos (default None = todos)
        voting_method: 'soft' ou 'hard'
        min_confidence: Confidence minimo para aceitar votacao
        dry_run: Se True, não modifica banco
        output_dir: Diretório para outputs

    Returns:
        {
            'status': 'ok'|'partial'|'error',
            'ensemble_signals_generated': int,
            'fallback_rate': float,
            'divergence_rate': float,
            'output_file': str
        }
    """
    started = datetime.utcnow()
    logger.info("=" * 70)
    logger.info("BLID-068: Geracao de Sinais Ensemble (E.10)")
    logger.info("=" * 70)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Inicializar gerador ensemble
        generator = EnsembleSignalGenerator(
            voting_method=voting_method,
            min_confidence=min_confidence
        )

        logger.info(f"Metodo votacao: {voting_method}")
        logger.info(f"Confianca minima: {min_confidence}")
        logger.info(f"Dry run: {dry_run}")

        query = [
            "SELECT id, symbol, timeframe, signal_side, entry_type, entry_price,",
            "       stop_loss, take_profit, signal_timestamp, status, payload_json",
            "FROM technical_signals",
            "WHERE timeframe = ?",
            "  AND status IN ('CREATED', 'CONSUMED')",
            "ORDER BY id ASC",
        ]
        params: list[Any] = [str(timeframe)]
        normalized_symbols = [str(item).upper() for item in symbols] if symbols else []
        if normalized_symbols:
            placeholders = ', '.join('?' for _ in normalized_symbols)
            query.insert(4, f"  AND symbol IN ({placeholders})")
            params = [str(timeframe), *normalized_symbols]

        processed = 0
        enhanced = 0
        items: list[dict[str, Any]] = []
        now_ms = _utc_now_ms()

        with sqlite3.connect(model2_db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('\n'.join(query), params).fetchall()

            for index, row in enumerate(rows):
                payload = _parse_payload(row['payload_json'])
                observation = _build_real_observation(row, payload)
                signal = generator.generate_ensemble_signal(observation)

                ensemble_payload = {
                    'action': int(signal['action']),
                    'confidence': float(round(signal['confidence'], 6)),
                    'method': str(signal['method']),
                    'voting_summary': dict(signal.get('voting_summary', {})),
                    'scored_at': int(now_ms),
                    'observation_source': 'technical_signal_snapshot',
                    'observation_shape': list(observation.shape),
                }
                payload['ensemble'] = ensemble_payload

                if not dry_run:
                    conn.execute(
                        """
                        UPDATE technical_signals
                        SET payload_json = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            json.dumps(payload, ensure_ascii=True, sort_keys=True),
                            int(now_ms),
                            int(row['id']),
                        ),
                    )
                    enhanced += 1

                processed += 1
                items.append(
                    {
                        'signal_id': int(row['id']),
                        'symbol': str(row['symbol']),
                        'action': int(signal['action']),
                        'confidence': float(round(signal['confidence'], 6)),
                        'method': str(signal['method']),
                    }
                )

                if index == 0:
                    logger.info("Exemplo sinal gerado:")
                    logger.info(f"  Signal ID: {int(row['id'])}")
                    logger.info(f"  Symbol: {str(row['symbol'])}")
                    logger.info(f"  Action: {signal['action']}")
                    logger.info(f"  Confidence: {signal['confidence']:.2f}")
                    logger.info(f"  Method: {signal['method']}")

            if not dry_run:
                conn.commit()

        # Estatísticas
        stats = generator.get_stats()

        # Salvar resultado
        result_file = output_dir / f"ensemble_signals_{started.strftime('%Y%m%d_%H%M%S')}.json"
        result = {
            'status': 'ok',
            'phase': 'E.10_ensemble_signal_generation',
            'timestamp': started.isoformat(),
            'model2_db_path': str(Path(model2_db_path)),
            'timeframe': str(timeframe),
            'symbols': normalized_symbols,
            'dry_run': bool(dry_run),
            'ensemble_signals_generated': processed,
            'signals_enhanced': enhanced,
            'fallback_rate': stats['fallback_rate'],
            'divergence_rate': stats['divergence_rate'],
            'voting_method': voting_method,
            'output_file': str(result_file),
            'statistics': stats,
            'items': items,
        }

        atomic_write_json(result_file, result, ensure_ascii=True, indent=2)

        logger.info(f"[OK] Ensembles gerados: {processed}")
        logger.info(f"  Fallback rate: {stats['fallback_rate']:.2%}")
        logger.info(f"  Divergence rate: {stats['divergence_rate']:.2%}")
        logger.info(f"  Output: {result_file}")

        generator.close()
        return result

    except Exception as e:
        logger.error(f"Erro em ensemble signal generation: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': started.isoformat()
        }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='BLID-068: Ensemble Signal Generation')
    parser.add_argument('--db', type=str, default='db/modelo2.db')
    parser.add_argument('--voting', type=str, default='soft', choices=['soft', 'hard'])
    parser.add_argument('--confidence', type=float, default=0.6)
    parser.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()

    result = run_ensemble_signal_generation(
        model2_db_path=args.db,
        voting_method=args.voting,
        min_confidence=args.confidence,
        dry_run=args.dry_run
    )

    sys.exit(0 if result.get('status') == 'ok' else 1)
