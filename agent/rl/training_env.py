"""
CryptoTradingEnv — Gymnasium environment para treinamento PPO.

Observação: estado do mercado + posição aberta
Ação: HOLD (0), LONG (1), SHORT (2)
Recompensa: PnL realizado + bônus Sharpe

Módulos:
    gymnasium: Framework para ambientes RL
    numpy: Computação numérica
    json: Carregamento de dados de trades
    pathlib: Manipulação de caminhos de arquivo
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import json
from pathlib import Path


class CryptoTradingEnv(gym.Env):
    """
    Ambiente Gymnasium para treinamento de agente PPO em trading crypto.
    
    Atributos:
        trade_data (list): Lista de dicts OHLCV com histórico de trades
        initial_capital (float): Capital inicial em USD
        current_step (int): Índice do passo atual
        equity (float): Capital/patrimônio líquido atual
        position (int): Posição aberta (0=fechada, 1=LONG, -1=SHORT)
        entry_price (float): Preço de entrada da posição atual
        trades_history (list): Histórico de trades executados
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(self, trade_data=None, initial_capital=10000.0):
        """
        Inicializa o ambiente de trading.
        
        Args:
            trade_data (list): Lista de dicts com {entry_price, exit_price, qty, direction}
            initial_capital (float): Capital inicial (padrão: $10,000)
        """
        super().__init__()
        
        # Carrega dados se não fornecidos
        if trade_data is None:
            trade_data = self._load_trades_from_file()
        
        self.trade_data = trade_data
        self.initial_capital = initial_capital
        self.current_step = 0
        self.equity = initial_capital
        self.position = 0  # 0=closed, 1=LONG, -1=SHORT
        self.entry_price = 0.0
        self.entry_qty = 0.0
        self.trades_history = []
        self.step_rewards = []
        
        # Espaço de observação: [close, volume, rsi, position, pnl]
        # Shape: (5,) de floats
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(5,),
            dtype=np.float32
        )
        
        # Espaço de ação: 3 ações discretas
        # 0 = HOLD, 1 = LONG, 2 = SHORT
        self.action_space = spaces.Discrete(3)
    
    def _load_trades_from_file(self, filepath="data/trades_history.json"):
        """
        Carrega histórico de trades de um arquivo JSON.
        
        Args:
            filepath (str): Caminho do arquivo de trades
            
        Returns:
            list: Lista de trades carregados
        """
        fpath = Path(filepath)
        if not fpath.exists():
            # Se não houver arquivo, retorna dados simulados
            return self._generate_dummy_trades()
        
        with open(fpath, 'r') as f:
            trades = json.load(f)
        
        return trades
    
    def _generate_dummy_trades(self, n=70):
        """
        Gera trades simulados para teste rápido.
        
        Args:
            n (int): Número de trades a gerar
            
        Returns:
            list: Lista de trades dummy
        """
        trades = []
        np.random.seed(42)
        
        for i in range(n):
            entry_price = 40000 + np.random.normal(0, 1000)
            exit_price = entry_price * (1 + np.random.uniform(-0.02, 0.03))
            
            trade = {
                'id': i + 1,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'qty': 1.0,
                'direction': 'LONG' if np.random.random() > 0.4 else 'SHORT',
                'reward': (exit_price - entry_price) / entry_price,
            }
            trades.append(trade)
        
        return trades
    
    def reset(self, seed=None, options=None):
        """
        Reseta o ambiente para o início do episódio.
        
        Args:
            seed (int): Seed para reproduzibilidade
            options (dict): Opções adicionais (não utilizado)
            
        Returns:
            tuple: (observation, info)
        """
        super().reset(seed=seed)
        
        self.current_step = 0
        self.equity = self.initial_capital
        self.position = 0
        self.entry_price = 0.0
        self.entry_qty = 0.0
        self.trades_history = []
        self.step_rewards = []
        
        obs = self._get_observation()
        info = {}
        
        return obs, info
    
    def step(self, action):
        """
        Executa um passo no ambiente (executa uma ação de trading).
        
        Args:
            action (int): Ação (0=HOLD, 1=LONG, 2=SHORT)
            
        Returns:
            tuple: (observation, reward, terminated, truncated, info)
        """
        assert self.action_space.contains(action), f"Ação inválida: {action}"
        
        # Pega o trade atual
        if self.current_step >= len(self.trade_data):
            # Fim dos dados
            obs = np.zeros(5, dtype=np.float32)
            return obs, 0.0, True, False, {}
        
        trade = self.trade_data[self.current_step]
        
        # Executa lógica de trading baseada na ação
        reward = self._execute_action(action, trade)
        self.step_rewards.append(reward)
        
        # Próximo passo
        self.current_step += 1
        
        # Observação para próximo passo
        obs = self._get_observation()
        
        # Verificar condições de término
        terminated = self.current_step >= len(self.trade_data)
        truncated = self.equity <= 0  # Arruinado
        
        info = {
            'equity': self.equity,
            'position': self.position,
            'trades_executed': len(self.trades_history),
        }
        
        return obs, float(reward), terminated, truncated, info
    
    def _execute_action(self, action, trade):
        """
        Executa a ação de trading e calcula reward.
        
        Args:
            action (int): Ação (0=HOLD, 1=LONG, 2=SHORT)
            trade (dict): Dados do trade atual
            
        Returns:
            float: Reward do passo
        """
        entry_price = trade['entry_price']
        exit_price = trade['exit_price']
        qty = trade.get('qty', 1.0)
        
        reward = 0.0
        
        # Se há posição aberta, fecha antes de abrir nova
        if self.position != 0:
            # Calcula PnL da posição fechada
            if self.position == 1:  # LONG
                pnl = (exit_price - self.entry_price) * self.entry_qty
            else:  # SHORT (-1)
                pnl = (self.entry_price - exit_price) * self.entry_qty
            
            # Atualiza equity
            self.equity += pnl
            
            # Reward: PnL normalizado pelo capital
            reward = pnl / self.initial_capital
            
            # Registra trade fechado
            self.trades_history.append({
                'entry_price': self.entry_price,
                'exit_price': exit_price,
                'qty': self.entry_qty,
                'position': 'LONG' if self.position == 1 else 'SHORT',
                'pnl': pnl,
                'reward': reward,
            })
            
            self.position = 0
            self.entry_price = 0.0
            self.entry_qty = 0.0
        
        # Abre nova posição conforme a ação
        if action == 1:  # LONG
            self.position = 1
            self.entry_price = entry_price
            self.entry_qty = qty
        elif action == 2:  # SHORT
            self.position = -1
            self.entry_price = entry_price
            self.entry_qty = qty
        # action == 0: HOLD, não abre posição
        
        return reward
    
    def _get_observation(self):
        """
        Retorna a observação atual do estado do mercado.
        
        Returns:
            np.ndarray: Array [close, volume, rsi, position, pnl]
        """
        if self.current_step < len(self.trade_data):
            trade = self.trade_data[self.current_step]
            
            # Close: preço de entrada do trade
            close = float(trade['entry_price'])
            
            # Volume: quantidade (simulada)
            volume = float(trade.get('qty', 1.0))
            
            # RSI: calculado como placeholder (valor entre 0-100)
            # Em uma implementação real, seria calculado a partir do histórico OHLC
            if self.current_step > 0:
                prev_reward = self.trade_data[self.current_step - 1].get('reward', 0)
                rsi = 50.0 + (prev_reward * 100)  # Heurística simples
            else:
                rsi = 50.0
            
            # Posição: -1, 0, 1
            position = float(self.position)
            
            # PnL não realizado
            pnl = 0.0
            if self.position != 0:
                if self.position == 1:  # LONG
                    pnl = (close - self.entry_price) * self.entry_qty
                else:  # SHORT
                    pnl = (self.entry_price - close) * self.entry_qty
            
            obs = np.array(
                [close, volume, rsi, position, pnl],
                dtype=np.float32
            )
        else:
            obs = np.zeros(5, dtype=np.float32)
        
        return obs
    
    def render(self):
        """Renderiza o estado atual do ambiente (console output)."""
        if self.current_step < len(self.trade_data):
            trade = self.trade_data[self.current_step]
            print(
                f"\nStep {self.current_step}: "
                f"Price={trade['entry_price']:.2f}, "
                f"Equity=${self.equity:.2f}, "
                f"Position={self.position}, "
                f"Trades={len(self.trades_history)}"
            )
    
    def close(self):
        """Fecha o ambiente (limpeza)."""
        pass
