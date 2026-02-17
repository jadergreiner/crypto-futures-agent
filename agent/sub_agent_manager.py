"""
Gerenciador de sub-agentes especializados por símbolo.
Cada símbolo tem seu próprio modelo PPO treinado com dados específicos.
"""

import logging
import os
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from .signal_environment import SignalReplayEnv
from .signal_reward import SignalRewardCalculator

logger = logging.getLogger(__name__)

# Configurações padrão para sub-agentes
DEFAULT_SUB_AGENT_CONFIG = {
    'learning_rate': 3e-4,
    'n_steps': 2048,
    'batch_size': 64,
    'n_epochs': 10,
    'gamma': 0.99,
    'gae_lambda': 0.95,
    'clip_range': 0.2,
    'ent_coef': 0.01,
    'verbose': 0
}

# Mínimo de trades para começar treino de um sub-agente
MIN_TRADES_FOR_TRAINING = 20


class SubAgentManager:
    """
    Gerencia sub-agentes especializados por símbolo.
    
    Cada símbolo tem seu próprio modelo PPO treinado com dados específicos
    daquele ativo. Isso permite especialização e melhor performance, já que
    nem tudo que funciona para um símbolo funciona para outro.
    """
    
    def __init__(self, base_dir: str = "models/sub_agents"):
        """
        Inicializa gerenciador de sub-agentes.
        
        Args:
            base_dir: Diretório base para salvar/carregar sub-agentes
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.agents: Dict[str, PPO] = {}  # Dict[symbol, PPO]
        self.agent_stats: Dict[str, Dict[str, Any]] = {}  # Stats por símbolo
        self.reward_calculator = SignalRewardCalculator()
        
        logger.info(f"SubAgentManager inicializado, base_dir={base_dir}")
        
        # Carregar agentes existentes
        self.load_all()
    
    def get_or_create_agent(self, symbol: str) -> PPO:
        """
        Retorna o sub-agente do símbolo. Cria se não existir.
        
        Args:
            symbol: Símbolo do ativo (ex: BTCUSDT)
            
        Returns:
            Instância do modelo PPO para o símbolo
        """
        if symbol in self.agents:
            return self.agents[symbol]
        
        logger.info(f"Criando novo sub-agente para {symbol}")
        
        # Criar environment dummy para inicializar o agente
        # (será substituído por environment real durante treino)
        dummy_env = self._create_dummy_env()
        
        # Criar modelo PPO com configurações padrão
        agent = PPO(
            policy='MlpPolicy',
            env=dummy_env,
            learning_rate=DEFAULT_SUB_AGENT_CONFIG['learning_rate'],
            n_steps=DEFAULT_SUB_AGENT_CONFIG['n_steps'],
            batch_size=DEFAULT_SUB_AGENT_CONFIG['batch_size'],
            n_epochs=DEFAULT_SUB_AGENT_CONFIG['n_epochs'],
            gamma=DEFAULT_SUB_AGENT_CONFIG['gamma'],
            gae_lambda=DEFAULT_SUB_AGENT_CONFIG['gae_lambda'],
            clip_range=DEFAULT_SUB_AGENT_CONFIG['clip_range'],
            ent_coef=DEFAULT_SUB_AGENT_CONFIG['ent_coef'],
            verbose=DEFAULT_SUB_AGENT_CONFIG['verbose']
        )
        
        self.agents[symbol] = agent
        
        # Inicializar stats
        self.agent_stats[symbol] = {
            'trades_trained': 0,
            'total_steps': 0,
            'last_training': None,
            'win_rate': 0.0,
            'avg_r_multiple': 0.0
        }
        
        return agent
    
    def train_agent(self, symbol: str, signals: List[Dict[str, Any]], 
                   evolutions: Dict[int, List[Dict[str, Any]]],
                   total_timesteps: int = 10000) -> Dict[str, Any]:
        """
        Treina o sub-agente do símbolo com dados reais acumulados.
        
        Args:
            symbol: Símbolo do ativo
            signals: Lista de sinais com outcomes preenchidos
            evolutions: Dicionário {signal_id: [snapshots]} com evoluções
            total_timesteps: Número de timesteps para treino
            
        Returns:
            Dicionário com estatísticas do treino
        """
        if len(signals) < MIN_TRADES_FOR_TRAINING:
            logger.warning(f"Não há trades suficientes para treinar {symbol}: "
                          f"{len(signals)} < {MIN_TRADES_FOR_TRAINING}")
            return {
                'success': False,
                'reason': 'insufficient_trades',
                'trades_available': len(signals)
            }
        
        logger.info(f"Iniciando treino de sub-agente {symbol} com {len(signals)} sinais")
        
        # Obter ou criar agente
        agent = self.get_or_create_agent(symbol)
        
        # Criar environment de replay com os sinais
        env = SignalReplayEnv(signals=signals, evolutions_dict=evolutions)
        vec_env = DummyVecEnv([lambda: env])
        
        # Atualizar environment do agente
        agent.set_env(vec_env)
        
        # Treinar
        try:
            agent.learn(total_timesteps=total_timesteps, reset_num_timesteps=False)
            
            # Atualizar stats
            self.agent_stats[symbol]['trades_trained'] = len(signals)
            self.agent_stats[symbol]['total_steps'] += total_timesteps
            self.agent_stats[symbol]['last_training'] = self._get_timestamp()
            
            # Calcular estatísticas dos sinais
            wins = sum(1 for s in signals if s.get('outcome_label') == 'win')
            self.agent_stats[symbol]['win_rate'] = wins / len(signals) if signals else 0.0
            
            avg_r = sum(s.get('r_multiple', 0.0) for s in signals) / len(signals) if signals else 0.0
            self.agent_stats[symbol]['avg_r_multiple'] = avg_r
            
            logger.info(f"Treino concluído para {symbol}: "
                       f"win_rate={self.agent_stats[symbol]['win_rate']:.2%}, "
                       f"avg_r={avg_r:.2f}")
            
            return {
                'success': True,
                'trades_trained': len(signals),
                'total_timesteps': total_timesteps,
                'win_rate': self.agent_stats[symbol]['win_rate'],
                'avg_r_multiple': avg_r
            }
            
        except Exception as e:
            logger.error(f"Erro ao treinar sub-agente {symbol}: {e}")
            return {
                'success': False,
                'reason': 'training_error',
                'error': str(e)
            }
    
    def evaluate_signal_quality(self, symbol: str, signal_context: Dict[str, Any]) -> float:
        """
        Usa o sub-agente para avaliar qualidade de um novo sinal.
        
        Args:
            symbol: Símbolo do ativo
            signal_context: Contexto do sinal (indicadores, SMC, sentimento, etc)
            
        Returns:
            Score de qualidade (0.0 a 1.0)
        """
        if symbol not in self.agents:
            logger.warning(f"Sub-agente para {symbol} não existe. Retornando score neutro.")
            return 0.5
        
        agent = self.agents[symbol]
        
        try:
            # Construir observação a partir do contexto
            obs = self._build_observation_from_context(signal_context)
            
            # Obter ação e valor estimado do agente
            action, _states = agent.predict(obs, deterministic=True)
            
            # Usar value function como proxy de qualidade
            # (valores altos = agente espera bom resultado)
            value = agent.policy.predict_values(obs)
            
            # Normalizar para [0, 1]
            quality_score = self._normalize_value_to_score(value)
            
            logger.debug(f"Qualidade de sinal {symbol}: {quality_score:.2f}")
            
            return quality_score
            
        except Exception as e:
            logger.error(f"Erro ao avaliar sinal {symbol}: {e}")
            return 0.5
    
    def get_agent_stats(self, symbol: str) -> Dict[str, Any]:
        """
        Retorna estatísticas do sub-agente (trades, win_rate, etc).
        
        Args:
            symbol: Símbolo do ativo
            
        Returns:
            Dicionário com estatísticas
        """
        if symbol not in self.agent_stats:
            return {
                'exists': False,
                'trades_trained': 0,
                'total_steps': 0,
                'last_training': None,
                'win_rate': 0.0,
                'avg_r_multiple': 0.0
            }
        
        return {
            'exists': True,
            **self.agent_stats[symbol]
        }
    
    def save_all(self) -> None:
        """Salva todos os sub-agentes e suas estatísticas."""
        for symbol, agent in self.agents.items():
            try:
                # Salvar modelo
                model_path = self.base_dir / f"{symbol}_ppo.zip"
                agent.save(str(model_path))
                
                # Salvar stats
                stats_path = self.base_dir / f"{symbol}_stats.json"
                with open(stats_path, 'w') as f:
                    json.dump(self.agent_stats.get(symbol, {}), f, indent=2)
                
                logger.debug(f"Sub-agente {symbol} salvo em {model_path}")
                
            except Exception as e:
                logger.error(f"Erro ao salvar sub-agente {symbol}: {e}")
        
        logger.info(f"Todos os sub-agentes salvos em {self.base_dir}")
    
    def load_all(self) -> None:
        """Carrega todos os sub-agentes salvos."""
        if not self.base_dir.exists():
            logger.info("Diretório de sub-agentes não existe ainda")
            return
        
        model_files = list(self.base_dir.glob("*_ppo.zip"))
        
        for model_path in model_files:
            try:
                symbol = model_path.stem.replace('_ppo', '')
                
                # Carregar modelo
                agent = PPO.load(str(model_path))
                self.agents[symbol] = agent
                
                # Carregar stats
                stats_path = self.base_dir / f"{symbol}_stats.json"
                if stats_path.exists():
                    with open(stats_path, 'r') as f:
                        self.agent_stats[symbol] = json.load(f)
                else:
                    self.agent_stats[symbol] = {
                        'trades_trained': 0,
                        'total_steps': 0,
                        'last_training': None,
                        'win_rate': 0.0,
                        'avg_r_multiple': 0.0
                    }
                
                logger.info(f"Sub-agente {symbol} carregado de {model_path}")
                
            except Exception as e:
                logger.error(f"Erro ao carregar sub-agente de {model_path}: {e}")
        
        if self.agents:
            logger.info(f"{len(self.agents)} sub-agentes carregados")
        else:
            logger.info("Nenhum sub-agente encontrado")
    
    def _create_dummy_env(self) -> SignalReplayEnv:
        """
        Cria environment dummy para inicialização de agente.
        
        Returns:
            SignalReplayEnv vazio
        """
        # Environment com um sinal dummy
        dummy_signal = {
            'id': 0,
            'timestamp': 0,
            'symbol': 'DUMMY',
            'direction': 'LONG',
            'entry_price': 100.0,
            'stop_loss': 98.0,
            'take_profit_1': 102.0,
            'pnl_pct': 0.0,
            'r_multiple': 0.0,
            'outcome_label': 'breakeven'
        }
        
        return SignalReplayEnv(signals=[dummy_signal], evolutions_dict={0: []})
    
    def _build_observation_from_context(self, context: Dict[str, Any]) -> Any:
        """
        Constrói observação a partir do contexto do sinal.
        
        Args:
            context: Dicionário com indicadores, SMC, sentimento, etc
            
        Returns:
            Observação no formato esperado pelo modelo
        """
        # Construir array de observação com 20 features
        # (mesmo formato do SignalReplayEnv)
        obs = [
            context.get('unrealized_pnl_pct', 0.0),
            context.get('distance_to_stop_pct', 0.0),
            context.get('distance_to_tp1_pct', 0.0),
            context.get('rsi_14', 50.0) / 50.0 - 1.0,  # Normalizar
            context.get('macd_histogram', 0.0),
            context.get('bb_percent_b', 0.5) * 2 - 1,
            context.get('atr_14', 0.0),
            context.get('adx_14', 25.0) / 50.0 - 1.0,
            0.0,  # mfe_pct (não disponível para novo sinal)
            0.0,  # mae_pct
            1.0,  # position_size
            0.0,  # steps_elapsed
            0.0,  # market_structure
            context.get('funding_rate', 0.0) * 10,
            context.get('long_short_ratio', 1.0) - 1.0,
            0.0, 0.0, 0.0, 0.0, 0.0  # Momentum features (não disponíveis)
        ]
        
        import numpy as np
        return np.array(obs, dtype=np.float32)
    
    def _normalize_value_to_score(self, value: float) -> float:
        """
        Normaliza value function para score [0, 1].
        
        Args:
            value: Valor da value function
            
        Returns:
            Score normalizado
        """
        # Assumindo que values estão tipicamente em [-5, 5]
        # Mapear para [0, 1]
        import numpy as np
        normalized = (np.clip(value, -5, 5) + 5) / 10
        return float(normalized)
    
    def _get_timestamp(self) -> int:
        """Retorna timestamp atual em milissegundos."""
        from datetime import datetime
        return int(datetime.now().timestamp() * 1000)
