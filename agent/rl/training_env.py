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
        self.consecutive_losses = 0  # Counter for consecutive losing trades (v2.4 safeguard)
        self.max_consecutive_losses = 5  # Max allowed consecutive losses hard limit

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
        self.consecutive_losses = 0  # Reset counter on new episode

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
        Executa a ação de trading e calcula reward com shaping otimizado.

        Estratégia de Reward Shaping v2:
        - Bônus para trades lucrosos (+0.1 a +0.5 base reward)
        - Penalidade balanceada para trades negativos (-0.1, não -1.0)
        - Bônus de Sharpe por consistência (ganhos frequentes)
        - Incentivo para tomar trades (vs ficar em cash)
        - Sem penalidade severa que evita risco

        Args:
            action (int): Ação (0=HOLD, 1=LONG, 2=SHORT)
            trade (dict): Dados do trade atual

        Returns:
            float: Reward do passo com shaping otimizado
        """
        entry_price = trade['entry_price']
        exit_price = trade['exit_price']
        qty = trade.get('qty', 1.0)

        reward = 0.0

        # ============================================================
        # POSIÇÃO ABERTA: FECHA E CALCULA REWARD
        # ============================================================
        if self.position != 0:
            # Calcula PnL da posição fechada
            if self.position == 1:  # LONG
                pnl = (exit_price - self.entry_price) * self.entry_qty
            else:  # SHORT (-1)
                pnl = (self.entry_price - exit_price) * self.entry_qty

            # Atualiza equity
            self.equity += pnl

            # ============================================================
            # REWARD SHAPING v2 OTIMIZADO PARA WIN RATE
            # ============================================================
            # Base reward: PnL normalizado (pequeno, para escala consistente)
            base_reward = pnl / (self.initial_capital * 100)  # Divide por 100 para escala melhor

            # Determinação de win/loss
            is_win = pnl > 0

            if is_win:
                # WIN: Bônus de descoberta de padrão positivo
                # Para ganhos: bônus base + incentivo por magnitude
                win_bonus = 0.2  # Bônus fixo por descobrir padrão positivo
                magnitude_bonus = min(pnl / self.initial_capital * 0.5, 0.1)  # Até +0.1 extras
                reward = base_reward + win_bonus + magnitude_bonus
                # Reset consecutive losses on win
                self.consecutive_losses = 0
            else:
                # LOSS: Penalidade moderada (não severa)
                # Evita que o modelo fique paralisado de medo
                loss_penalty = -0.05  # Penalidade fixa pequena
                magnitude_loss = max(pnl / self.initial_capital * 0.1, -0.05)  # Até -0.05 extras
                reward = base_reward + loss_penalty + magnitude_loss
                
                # ============================================================
                # CONSECUTIVE LOSSES SAFEGUARD (v2.4)
                # ============================================================
                # Track consecutive losses; penalize heavily if limit reached
                self.consecutive_losses += 1
                
                if self.consecutive_losses >= self.max_consecutive_losses:
                    # Severe penalty when hitting max consecutive losses
                    penalty = -1.0  # Heavy penalty to discourage this pattern
                    reward += penalty

            # ============================================================
            # BÔNUS DE SHARPE (Consistência de Wins)
            # ============================================================
            # Se há histórico de trades, calcula taxa de ganhos recentes
            if len(self.trades_history) >= 5:
                recent_trades = self.trades_history[-5:]  # Últimos 5 trades
                recent_wins = sum(1 for t in recent_trades if t['pnl'] > 0)
                win_rate = recent_wins / len(recent_trades)

                # Bônus por win rate crescente
                if win_rate >= 0.6:  # 60% ou mais
                    reward += 0.05  # Bônus de consistência
                elif win_rate >= 0.8:  # 80% ou mais
                    reward += 0.10  # Bônus superior

            # Registra trade fechado
            self.trades_history.append({
                'entry_price': self.entry_price,
                'exit_price': exit_price,
                'qty': self.entry_qty,
                'position': 'LONG' if self.position == 1 else 'SHORT',
                'pnl': pnl,
                'reward': reward,
                'is_win': is_win,
            })

            self.position = 0
            self.entry_price = 0.0
            self.entry_qty = 0.0

        # ============================================================
        # ABRE NOVA POSIÇÃO (0=HOLD, 1=LONG, 2=SHORT)
        # ============================================================
        if action == 1:  # LONG
            self.position = 1
            self.entry_price = entry_price
            self.entry_qty = qty
            # Pequeno bônus por tomar decisão (vs ficar em HOLD)
            reward += 0.01
        elif action == 2:  # SHORT
            self.position = -1
            self.entry_price = entry_price
            self.entry_qty = qty
            # Pequeno bônus por tomar decisão (vs ficar em HOLD)
            reward += 0.01
        # action == 0: HOLD, não abre posição (sem bônus, encoraja decisão)

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
