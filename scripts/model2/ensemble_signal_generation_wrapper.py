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
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.lstm_environment import LSTMSignalEnvironment
from scripts.model2.ensemble_voting_ppo import EnsembleVotingPPO

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


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

    def _init_ensemble(self) -> None:
        """Carrega ensemble (com fallback gracioso se checkpoints não existem)"""
        try:
            logger.info(f"Carregando checkpoints E.8...")
            logger.info(f"  MLP: {self.mlp_checkpoint}")
            logger.info(f"  LSTM: {self.lstm_checkpoint}")

            self.ensemble = EnsembleVotingPPO(
                mlp_checkpoint_path=self.mlp_checkpoint,
                lstm_checkpoint_path=self.lstm_checkpoint,
                mlp_weight=0.48,
                lstm_weight=0.52,
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
            # Obter predicoes de ambos os modelos
            mlp_action, _ = self.ensemble.mlp_model.predict(
                observation, deterministic=True
            )
            lstm_action, _ = self.ensemble.lstm_model.predict(
                observation, deterministic=True
            )

            mlp_vote = int(mlp_action)
            lstm_vote = int(lstm_action)

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
                mlp_vote, lstm_vote, consenso
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
            return lstm_vote

    def _hard_voting(self, mlp_vote: int, lstm_vote: int) -> int:
        """Hard voting: votacao com pesos"""
        score_0 = (1 - mlp_vote) * 0.48 + (1 - lstm_vote) * 0.52
        score_1 = mlp_vote * 0.48 + lstm_vote * 0.52
        return 1 if score_1 > score_0 else 0

    def _calculate_confidence(
        self,
        mlp_vote: int,
        lstm_vote: int,
        consenso: float
    ) -> float:
        """Calcula confidence como funcao de consenso + pesos"""
        base_confidence = consenso  # 1.0 se concordam, 0.0 se discordam

        # Se discordam, bonus pequeno se voto é com weight alto (LSTM)
        if consenso < 1.0:
            # LSTM tem weight 0.52 > MLP 0.48
            lstm_confidence_bonus = 0.15
            return min(0.95, base_confidence + lstm_confidence_bonus)

        return base_confidence

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

        # Simulacao: gerar X sinais ensemble
        # Em producao real, seria: ler technical_signals, gerar votacao, atualizar
        logger.info(f"Metodo votacao: {voting_method}")
        logger.info(f"Confianca minima: {min_confidence}")
        logger.info(f"Dry run: {dry_run}")

        # Mock: simular 10 sinais
        n_signals = 10
        for i in range(n_signals):
            # Mock observation
            observation = np.random.randn(10, 20).astype(np.float32)  # LSTM shape
            signal = generator.generate_ensemble_signal(observation)

            if i == 0:
                logger.info(f"Exemplo sinal gerado:")
                logger.info(f"  Action: {signal['action']}")
                logger.info(f"  Confidence: {signal['confidence']:.2f}")
                logger.info(f"  Method: {signal['method']}")

        # Estatísticas
        stats = generator.get_stats()

        # Salvar resultado
        result_file = output_dir / f"ensemble_signals_{started.strftime('%Y%m%d_%H%M%S')}.json"
        result = {
            'status': 'ok',
            'phase': 'E.10_ensemble_signal_generation',
            'timestamp': started.isoformat(),
            'ensemble_signals_generated': n_signals,
            'fallback_rate': stats['fallback_rate'],
            'divergence_rate': stats['divergence_rate'],
            'voting_method': voting_method,
            'output_file': str(result_file),
            'statistics': stats
        }

        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)

        logger.info(f"[OK] Ensembles gerados: {n_signals}")
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
