"""Backtesting Engine — S2-3 Sprint 2-3.

Module exports:
- BacktestEngine: Motor principal de backtesting
- TradeState: Gerenciamento de estado de posição
- BacktestMetrics: Cálculo de PnL, Drawdown, Sharpe
- DataProvider: Interface abstrata de dados históricos
- SMCStrategy: Estratégia Smart Money Concepts
"""

__version__ = "0.1.0"
__author__ = "Crypto Futures Agent Squad"
__status__ = "Design Kickoff (Sprint 2-3)"

# Legacy exports (mantém compatibilidade)
try:
    from .backtester import Backtester
    from .walk_forward import WalkForward
except ImportError:
    pass  # Módulos serão criados em Sprint 2-3

# S2-3 Core exports (implementados Sprint 2-3)
# from .core.backtest_engine import BacktestEngine
# from .core.trade_state import TradeState
# from .core.metrics import BacktestMetrics

# S2-3 Data provider
# from .data.data_provider import DataProvider
# from .data.cache_reader import CacheReader

# S2-3 Strategies
# from .strategies.smc_strategy import SMCStrategy
# from .strategies.signal_factory import SignalFactory

# S2-3 Validation
# from .validation.gates import GateValidator
# from .validation.walk_forward import WalkForwardValidator

__all__ = ['Backtester', 'WalkForward']  # Legacy
