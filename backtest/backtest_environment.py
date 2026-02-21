"""
BacktestEnvironment — Subclass determinística de CryptoFuturesEnv.

Herda 99% da lógica de CryptoFuturesEnv.step(), apenas garantindo determinismo
e operação com dados históricos (vs. oracle estocástico).

Não adiciona novas funcionalidades — é um wrapper que força reproducibilidade.
"""

import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

from agent.environment import CryptoFuturesEnv

logger = logging.getLogger(__name__)


class BacktestEnvironment(CryptoFuturesEnv):
    """
    Environment determinístico para backtesting com dados históricos.

    Reutiliza 99% do código de CryptoFuturesEnv.step() — apenas força:
    - Seed para reproducibilidade
    - Ignorar randomização de start_step (sempre começar em warmup+1)
    - Dados históricos (não muda durante episódio)

    Observation Space: Box(104,) — Features normalizadas
    Action Space: Discrete(5) — 0:HOLD, 1:OPEN_LONG, 2:OPEN_SHORT, 3:CLOSE, 4:REDUCE_50
    """

    def __init__(self,
                 data: Dict[str, pd.DataFrame],
                 initial_capital: float = 10000,
                 risk_params: Optional[Dict[str, Any]] = None,
                 episode_length: Optional[int] = None,
                 deterministic: bool = True):
        """
        Inicializa BacktestEnvironment.

        Args:
            data: Dicionário com {h1, h4, d1, symbol, sentiment, macro, smc}
            initial_capital: Capital inicial em USDT
            risk_params: Parâmetros de risco opcionais
            episode_length: Comprimento máximo do episódio (Default: len(h4) - 1)
            deterministic: Se True, ignora randomização de start_step
        """
        # Inferir episode_length se não fornecido
        if episode_length is None:
            h4_data = data.get('h4', pd.DataFrame())
            episode_length = len(h4_data) - 1 if len(h4_data) > 1 else 100

        # Chamar super().__init__() — isso popula TODAS as estruturas necessárias
        super().__init__(
            data=data,
            initial_capital=initial_capital,
            risk_params=risk_params,
            episode_length=episode_length
        )

        self.deterministic = deterministic

        logger.info(f"BacktestEnvironment initialized: symbol={data.get('symbol', 'UNKNOWN')}, "
                   f"deterministic={deterministic}, episode_length={episode_length}")

    def reset(self,
              seed: Optional[int] = None,
              options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict]:
        """
        Reset em modo determinístico.

        Em backtesting, sempre começar após warmup (step 30) e ignorar randomização.

        Args:
            seed: Seed (ignorado em modo determinístico)
            options: Opções customizadas

        Returns:
            (observation, info)
        """
        if self.deterministic:
            # Modo determinístico: sempre começar em warmup + 0
            warmup_steps = 30
            self.start_step = warmup_steps
        else:
            # Modo aleatório: usar seed
            if seed is not None:
                np.random.seed(seed)

            warmup_steps = 30
            max_start = max(0, len(self.data.get('h4', [])) - self.episode_length - warmup_steps)

            if max_start > warmup_steps:
                self.start_step = np.random.randint(warmup_steps, max_start)
            else:
                self.start_step = warmup_steps

        # Chamar reset da classe pai (CryptoFuturesEnv) — isto cuida de tudo
        # (state reset, observation creation, info dict)
        return super().reset(seed=seed, options=options)

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Executa step do episódio.

        **CRÍTICO**: Reutiliza COMPLETAMENTE CryptoFuturesEnv.step()
        Sem adicionar nenhuma lógica nova — backtesting não muda a mecânica do environment.

        Args:
            action: Ação (0-4)

        Returns:
            (observation, reward, terminated, truncated, info)
        """
        # Chamar super().step() — isto é 99% do trabalho
        return super().step(action)

    def get_backtest_summary(self) -> Dict[str, Any]:
        """
        Retorna sumário de performance do episódio.

        Used by backtester para coletar métricas.

        Returns:
            Dict com stats do episódio (trades, PnL, etc)
        """
        closed_trades = [t for t in self.trades_history if t.get('exit_price')]
        total_trades = len(self.trades_history)

        if total_trades == 0:
            return {
                'symbol': self.symbol,
                'total_trades': 0,
                'final_capital': self.capital,
                'return_pct': 0.0,
            }

        winning = sum(1 for t in closed_trades if t.get('pnl_abs', 0) > 0)
        total_pnl = sum(t.get('pnl_abs', 0) for t in closed_trades)
        return_pct = ((self.capital - self.initial_capital) / self.initial_capital * 100
                     if self.initial_capital > 0 else 0)

        return {
            'symbol': self.symbol,
            'total_trades': total_trades,
            'closed_trades': len(closed_trades),
            'winning_trades': winning,
            'losing_trades': len(closed_trades) - winning,
            'win_rate_pct': (winning / len(closed_trades) * 100) if closed_trades else 0,
            'total_pnl': total_pnl,
            'final_capital': self.capital,
            'return_pct': return_pct,
            'peak_capital': self.peak_capital,
            'max_drawdown_pct': ((self.peak_capital - self.capital) / self.peak_capital * 100
                                if self.peak_capital > 0 else 0),
        }


if __name__ == '__main__':
    # Test rápido para verificar que BacktestEnvironment funciona
    import logging
    logging.basicConfig(level=logging.INFO)

    print("✅ BacktestEnvironment importado com sucesso!")
    print(f"   Classe: {BacktestEnvironment}")
    print(f"   Herda de: {BacktestEnvironment.__bases__}")
