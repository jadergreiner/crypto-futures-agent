"""
Treinador do agente RL com múltiplas fases.
"""

import logging
from typing import Dict, Any, Optional
import os
from datetime import datetime
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from .environment import CryptoFuturesEnv

logger = logging.getLogger(__name__)

# Verificar se tensorboard está disponível
try:
    import tensorboard.summary
    TENSORBOARD_AVAILABLE = True
except ImportError:
    TENSORBOARD_AVAILABLE = False
    logger.warning("TensorBoard não instalado. Treinamento continuará sem logging do TensorBoard.")


class TrainingCallback(BaseCallback):
    """Callback para logging durante o treinamento."""
    
    def __init__(self, verbose=0, log_interval=1000):
        super().__init__(verbose)
        self.log_interval = log_interval
        self.episode_rewards = []
        self.episode_lengths = []
        self._last_ep_info_len = 0  # Rastrear quantos episódios já processamos
    
    def _on_step(self) -> bool:
        """Chamado a cada step."""
        # Capturar TODOS os novos episódios do buffer (não apenas o último)
        current_len = len(self.model.ep_info_buffer)
        if current_len > self._last_ep_info_len:
            for i in range(self._last_ep_info_len, current_len):
                ep_info = self.model.ep_info_buffer[i]
                self.episode_rewards.append(ep_info.get('r', 0))
                self.episode_lengths.append(ep_info.get('l', 0))
            self._last_ep_info_len = current_len
        
        # Logar a cada intervalo
        if self.n_calls % self.log_interval == 0:
            if self.episode_rewards:
                recent_rewards = self.episode_rewards[-100:]
                logger.info(f"Training step {self.n_calls}: "
                           f"reward_mean={np.mean(recent_rewards):.4f}, "
                           f"episodes={len(self.episode_rewards)}, "
                           f"ep_len_mean={np.mean(self.episode_lengths[-100:]):.0f}")
            else:
                logger.info(f"Training step {self.n_calls}: "
                           f"reward_mean=N/A (nenhum episódio completo ainda)")
        
        return True
    
    def _on_rollout_end(self) -> None:
        """Chamado ao final de cada rollout. Nada a fazer — captura já acontece em _on_step."""
        pass


class Trainer:
    """
    Gerencia o treinamento do agente RL em múltiplas fases.
    
    Fase 1: Exploração (500k steps)
    Fase 2: Refinamento (1M steps)
    Fase 3: Validação (out-of-sample)
    """
    
    def __init__(self, save_dir: str = "models"):
        """
        Inicializa trainer.
        
        Args:
            save_dir: Diretório para salvar modelos
        """
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        self.model = None
        self.env = None
        self.vec_env = None  # Armazenar vec_env com VecNormalize
        logger.info(f"Trainer initialized, save_dir={save_dir}")
    
    def create_env(self, data: Dict[str, Any], **kwargs) -> CryptoFuturesEnv:
        """
        Cria environment.
        
        Args:
            data: Dados para o environment
            **kwargs: Argumentos adicionais para o environment
            
        Returns:
            Environment
        """
        env = CryptoFuturesEnv(data, **kwargs)
        return env
    
    def train_phase1_exploration(self, train_data: Dict[str, Any], 
                                 total_timesteps: int = 500000,
                                 **env_kwargs) -> PPO:
        """
        Fase 1: Exploração inicial com alta entropia.
        
        Args:
            train_data: Dados de treinamento
            total_timesteps: Número total de timesteps
            **env_kwargs: Argumentos para o environment
            
        Returns:
            Modelo treinado
        """
        logger.info("="*60)
        logger.info("PHASE 1: Exploration Training")
        logger.info("="*60)
        
        # Criar environment
        self.env = self.create_env(train_data, **env_kwargs)
        vec_env = DummyVecEnv([lambda: self.env])
        
        # Aplicar VecNormalize para estabilizar treinamento
        vec_env = VecNormalize(
            vec_env,
            norm_obs=True,
            norm_reward=True,
            clip_obs=10.0,
            clip_reward=10.0,
            gamma=0.99
        )
        self.vec_env = vec_env
        
        # Determinar tensorboard_log baseado na disponibilidade
        tb_log = f"{self.save_dir}/tensorboard/phase1" if TENSORBOARD_AVAILABLE else None
        
        # Criar modelo PPO com hiperparâmetros ajustados para exploração
        self.model = PPO(
            "MlpPolicy",
            vec_env,
            learning_rate=3e-4,
            n_steps=4096,          # Aumentado de 2048 para cobrir episódios completos
            batch_size=128,        # Aumentado de 64 para estabilidade
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.03,         # Aumentado de 0.01 para mais exploração e evitar convergência prematura para HOLD
            vf_coef=0.5,
            max_grad_norm=0.5,
            normalize_advantage=True,  # Adicionar normalização de advantage
            verbose=1,
            tensorboard_log=tb_log
        )
        
        # Callback
        callback = TrainingCallback(log_interval=1000)
        
        # Treinar
        logger.info(f"Starting Phase 1 training: {total_timesteps} timesteps")
        self.model.learn(
            total_timesteps=total_timesteps,
            callback=callback,
            progress_bar=False
        )
        
        # Salvar
        model_path = os.path.join(self.save_dir, "phase1_exploration.zip")
        self.model.save(model_path)
        
        # Salvar estatísticas de normalização do VecNormalize
        vec_normalize_path = os.path.join(self.save_dir, "phase1_vec_normalize.pkl")
        self.vec_env.save(vec_normalize_path)
        
        logger.info(f"Phase 1 model saved to {model_path}")
        logger.info(f"VecNormalize stats saved to {vec_normalize_path}")
        
        return self.model
    
    def train_phase2_refinement(self, train_data: Dict[str, Any],
                                total_timesteps: int = 1000000,
                                load_phase1: bool = True,
                                **env_kwargs) -> PPO:
        """
        Fase 2: Refinamento com menor entropia.
        
        Args:
            train_data: Dados de treinamento
            total_timesteps: Número total de timesteps
            load_phase1: Se deve carregar modelo da fase 1
            **env_kwargs: Argumentos para o environment
            
        Returns:
            Modelo treinado
        """
        logger.info("="*60)
        logger.info("PHASE 2: Refinement Training")
        logger.info("="*60)
        
        # Criar environment
        self.env = self.create_env(train_data, **env_kwargs)
        vec_env = DummyVecEnv([lambda: self.env])
        
        # Aplicar VecNormalize
        vec_env = VecNormalize(
            vec_env,
            norm_obs=True,
            norm_reward=True,
            clip_obs=10.0,
            clip_reward=10.0,
            gamma=0.99
        )
        
        if load_phase1 and self.model is None:
            # Carregar modelo da fase 1
            phase1_path = os.path.join(self.save_dir, "phase1_exploration.zip")
            vec_normalize_path = os.path.join(self.save_dir, "phase1_vec_normalize.pkl")
            
            if os.path.exists(phase1_path):
                logger.info(f"Loading Phase 1 model from {phase1_path}")
                
                # Carregar estatísticas de normalização da fase 1
                if os.path.exists(vec_normalize_path):
                    logger.info(f"Loading VecNormalize stats from {vec_normalize_path}")
                    vec_env = VecNormalize.load(vec_normalize_path, vec_env)
                else:
                    logger.warning("VecNormalize stats not found, using new normalization")
                
                self.model = PPO.load(phase1_path, env=vec_env)
            else:
                logger.warning("Phase 1 model not found, creating new model")
                self.model = PPO(
                    "MlpPolicy", 
                    vec_env, 
                    learning_rate=3e-4,
                    n_steps=4096,
                    batch_size=128,
                    normalize_advantage=True,
                    verbose=1
                )
        elif self.model is None:
            self.model = PPO(
                "MlpPolicy", 
                vec_env, 
                learning_rate=3e-4,
                n_steps=4096,
                batch_size=128,
                normalize_advantage=True,
                verbose=1
            )
        else:
            # Atualizar environment
            self.model.set_env(vec_env)
        
        self.vec_env = vec_env
        
        # Reduzir entropia para refinamento
        self.model.ent_coef = 0.005
        
        # Callback
        callback = TrainingCallback(log_interval=1000)
        
        # Treinar
        logger.info(f"Starting Phase 2 training: {total_timesteps} timesteps")
        self.model.learn(
            total_timesteps=total_timesteps,
            callback=callback,
            progress_bar=False,
            reset_num_timesteps=False  # Continuar contagem
        )
        
        # Salvar
        model_path = os.path.join(self.save_dir, "phase2_refinement.zip")
        self.model.save(model_path)
        
        # Salvar estatísticas de normalização do VecNormalize
        vec_normalize_path = os.path.join(self.save_dir, "phase2_vec_normalize.pkl")
        self.vec_env.save(vec_normalize_path)
        
        logger.info(f"Phase 2 model saved to {model_path}")
        logger.info(f"VecNormalize stats saved to {vec_normalize_path}")
        
        return self.model
    
    def train_phase3_validation(self, test_data: Dict[str, Any],
                                n_episodes: int = 100,
                                **env_kwargs) -> Dict[str, Any]:
        """
        Fase 3: Validação em dados out-of-sample.
        
        Args:
            test_data: Dados de teste
            n_episodes: Número de episódios de validação
            **env_kwargs: Argumentos para o environment
            
        Returns:
            Métricas de validação
        """
        logger.info("="*60)
        logger.info("PHASE 3: Validation on Out-of-Sample Data")
        logger.info("="*60)
        
        if self.model is None:
            raise ValueError("Model not trained. Run phase 1 and 2 first.")
        
        # Criar environment de teste
        test_env = self.create_env(test_data, **env_kwargs)
        
        # Avaliar
        metrics = self.evaluate(test_env, n_episodes=n_episodes, deterministic=True)
        
        logger.info("Validation Results:")
        logger.info(f"  Win Rate: {metrics['win_rate']*100:.2f}%")
        logger.info(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        logger.info(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        logger.info(f"  Max Drawdown: {metrics['max_drawdown']*100:.2f}%")
        logger.info(f"  Avg R-Multiple: {metrics['avg_r_multiple']:.2f}")
        
        # Salvar relatório
        report_path = os.path.join(self.save_dir, "validation_report.txt")
        with open(report_path, 'w') as f:
            f.write("VALIDATION REPORT\n")
            f.write("="*60 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Episodes: {n_episodes}\n\n")
            f.write("METRICS:\n")
            for key, value in metrics.items():
                f.write(f"  {key}: {value}\n")
        
        logger.info(f"Validation report saved to {report_path}")
        
        return metrics
    
    def evaluate(self, env: CryptoFuturesEnv, n_episodes: int = 100,
                 deterministic: bool = True) -> Dict[str, float]:
        """
        Avalia o modelo em um environment.
        
        Args:
            env: Environment para avaliação
            n_episodes: Número de episódios
            deterministic: Se deve usar política determinística
            
        Returns:
            Dicionário com métricas
        """
        if self.model is None:
            raise ValueError("Model not trained")
        
        all_trades = []
        episode_returns = []
        episode_capitals = []
        
        for episode in range(n_episodes):
            obs, info = env.reset()
            episode_reward = 0
            done = False
            
            while not done:
                action, _states = self.model.predict(obs, deterministic=deterministic)
                obs, reward, terminated, truncated, info = env.step(action)
                episode_reward += reward
                done = terminated or truncated
            
            # Coletar trades do episódio
            all_trades.extend(env.episode_trades)
            episode_returns.append(episode_reward)
            episode_capitals.append(env.capital)
            
            if (episode + 1) % 10 == 0:
                logger.info(f"Evaluation episode {episode+1}/{n_episodes} completed")
        
        # Calcular métricas
        metrics = self._calculate_metrics(all_trades, episode_capitals, env.initial_capital)
        
        return metrics
    
    def _calculate_metrics(self, trades: list, final_capitals: list, 
                          initial_capital: float) -> Dict[str, float]:
        """
        Calcula métricas de performance.
        
        Args:
            trades: Lista de trades
            final_capitals: Capitais finais de cada episódio
            initial_capital: Capital inicial
            
        Returns:
            Dicionário com métricas
        """
        if not trades:
            return {
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'avg_r_multiple': 0.0,
                'total_trades': 0,
                'avg_return': 0.0
            }
        
        # Win Rate
        winners = [t for t in trades if t['pnl'] > 0]
        win_rate = len(winners) / len(trades) if trades else 0
        
        # Profit Factor
        gross_profit = sum(t['pnl'] for t in winners)
        losers = [t for t in trades if t['pnl'] <= 0]
        gross_loss = abs(sum(t['pnl'] for t in losers)) if losers else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe Ratio
        returns = [t['pnl_pct'] for t in trades]
        if len(returns) > 1:
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Max Drawdown
        peak = initial_capital
        max_dd = 0
        for capital in final_capitals:
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak
            if dd > max_dd:
                max_dd = dd
        
        # Avg R-Multiple
        r_multiples = [t['r_multiple'] for t in trades]
        avg_r = np.mean(r_multiples) if r_multiples else 0
        
        # Avg Return
        capital_returns = [(c - initial_capital) / initial_capital * 100 for c in final_capitals]
        avg_return = np.mean(capital_returns) if capital_returns else 0
        
        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_dd,
            'avg_r_multiple': avg_r,
            'total_trades': len(trades),
            'avg_return': avg_return,
            'total_episodes': len(final_capitals)
        }
    
    def save_model(self, path: Optional[str] = None) -> None:
        """
        Salva o modelo atual.
        
        Args:
            path: Caminho customizado (opcional)
        """
        if self.model is None:
            raise ValueError("No model to save")
        
        if path is None:
            path = os.path.join(self.save_dir, "crypto_agent_ppo.zip")
        
        self.model.save(path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str, env: Optional[CryptoFuturesEnv] = None) -> PPO:
        """
        Carrega um modelo salvo.
        
        Args:
            path: Caminho do modelo
            env: Environment (opcional)
            
        Returns:
            Modelo carregado
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model not found: {path}")
        
        self.model = PPO.load(path, env=env)
        logger.info(f"Model loaded from {path}")
        
        return self.model
    
    def train_from_real_signals(self, symbol: str, db) -> Dict[str, Any]:
        """
        Treina sub-agente do símbolo usando sinais reais acumulados.
        Busca sinais com outcome do banco e cria episódios de replay.
        
        Args:
            symbol: Símbolo do ativo (ex: BTCUSDT)
            db: DatabaseManager instance
            
        Returns:
            Dicionário com resultado do treino
        """
        from .sub_agent_manager import SubAgentManager
        from config.settings import (
            SUB_AGENTS_BASE_DIR, 
            SIGNAL_MIN_TRADES_FOR_RETRAINING,
            SIGNAL_RETRAINING_TIMESTEPS
        )
        
        logger.info(f"Iniciando treino com sinais reais para {symbol}")
        
        # Buscar sinais com outcome do banco
        signals = db.get_signals_for_training(symbol=symbol, limit=1000)
        
        if not signals:
            logger.warning(f"Nenhum sinal com outcome encontrado para {symbol}")
            return {
                'success': False,
                'reason': 'no_signals',
                'symbol': symbol
            }
        
        if len(signals) < SIGNAL_MIN_TRADES_FOR_RETRAINING:
            logger.warning(f"Sinais insuficientes para treino de {symbol}: "
                          f"{len(signals)} < {SIGNAL_MIN_TRADES_FOR_RETRAINING}")
            return {
                'success': False,
                'reason': 'insufficient_signals',
                'symbol': symbol,
                'signals_available': len(signals),
                'signals_required': SIGNAL_MIN_TRADES_FOR_RETRAINING
            }
        
        # Buscar evoluções para cada sinal
        evolutions_dict = {}
        for signal in signals:
            signal_id = signal['id']
            evolutions = db.get_signal_evolution(signal_id)
            evolutions_dict[signal_id] = evolutions
        
        logger.info(f"Carregados {len(signals)} sinais e suas evoluções para {symbol}")
        
        # Inicializar gerenciador de sub-agentes
        manager = SubAgentManager(base_dir=SUB_AGENTS_BASE_DIR)
        
        # Treinar sub-agente
        result = manager.train_agent(
            symbol=symbol,
            signals=signals,
            evolutions=evolutions_dict,
            total_timesteps=SIGNAL_RETRAINING_TIMESTEPS
        )
        
        # Salvar sub-agente
        if result.get('success'):
            manager.save_all()
            logger.info(f"Sub-agente {symbol} treinado e salvo com sucesso")
        
        return {
            **result,
            'symbol': symbol,
            'signals_used': len(signals)
        }
