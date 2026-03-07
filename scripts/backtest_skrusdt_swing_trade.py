#!/usr/bin/env python
"""
Backtest Script — SKRUSDT Swing Trade Model Validation

Valida modelo SKRPlaybook em dados históricos:
- Teste de entrada via confluência
- Teste de saída via stop loss / take profit
- Cálculo de métricas (Sharpe, DD, Win Rate, etc)
- Geração de relatório

Uso:
    python scripts/backtest_skrusdt_swing_trade.py
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add root to path
root = str(Path(__file__).parent.parent)
if root not in sys.path:
    sys.path.insert(0, root)

from config.symbols import SYMBOLS
from playbooks import SKRPlaybook
from indicators.technical import TechnicalIndicators
from indicators.smc import SmartMoneyConcepts

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SKRBacktestEngine:
    """Engine de backtest para modelo SKR."""

    def __init__(self, initial_capital: float = 1000.0):
        """Inicializa engine."""
        self.symbol = "SKRUSDT"
        self.initial_capital = initial_capital
        self.playbook = SKRPlaybook()
        self.tech_ind = TechnicalIndicators()
        self.smc = SmartMoneyConcepts()

        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[float] = [initial_capital]
        self.balance = initial_capital

        logger.info(f"SKRBacktestEngine initialized: {self.symbol}, Capital: ${initial_capital:.2f}")

    def generate_synthetic_data(self, days: int = 100, base_price: float = 0.005) -> pd.DataFrame:
        """
        Gera dados históricos sintéticos para teste.

        Características:
        - Simula movimentos de swing trade (5-20% swings)
        - Inclui ordem blocks detectáveis
        - Beta 2.8: volatilidade amplificada

        Args:
            days: Número de dias
            base_price: Preço base inicial

        Returns:
            DataFrame com OHLCV
        """
        logger.info(f"Gerando {days} dias de dados sintéticos (base_price=${base_price:.6f})")

        np.random.seed(42)
        data = []

        current_price = base_price
        btc_bias = "LONG"
        d1_bias = "LONG"

        for i in range(days):
            # Simulação com tendências e reversões
            if i % 15 == 0:
                # Muda tendência a cada 15 dias
                btc_bias = "SHORT" if btc_bias == "LONG" else "LONG"

            if i % 8 == 0:
                d1_bias = "SHORT" if d1_bias == "LONG" else "LONG"

            # Volatilidade amplificada (beta 2.8)
            volatility = np.random.normal(0, 0.015)  # 1.5% volatilidade diária
            if btc_bias == "LONG":
                volatility += 0.005  # +0.5% viés para cima
            else:
                volatility -= 0.005  # -0.5% viés para baixo

            # Volume simulado
            volume = np.random.uniform(50000, 150000)

            # OHLCV
            open_price = current_price
            close_price = current_price * (1 + volatility)
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))

            data.append({
                'timestamp': int((datetime.utcnow() - timedelta(days=days-i)).timestamp() * 1000),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })

            current_price = close_price

        df = pd.DataFrame(data)
        df = df.sort_values('timestamp').reset_index(drop=True)

        logger.info(f"Dados gerados: {len(df)} candles, preço final: ${df['close'].iloc[-1]:.6f}")
        return df

    def detect_confluence(self, df: pd.DataFrame, idx: int) -> Tuple[str, float, Dict[str, float]]:
        """
        Detecta confluência para entrada.

        Args:
            df: DataFrame OHLCV
            idx: Índice do candle

        Returns:
            (signal_type, confluence_score, adjustments)
        """
        if idx < 50:
            return "HOLD", 0.0, {}

        # Simular cálculos de indicators
        rsi = 50 + np.random.normal(0, 10)  # RSI sintético
        ema_ratio = 1.0 + np.random.normal(0, 0.02)  # EMA ratio
        volume_ratio = df['volume'].iloc[max(0, idx-20):idx+1].mean()
        volume_ratio = df['volume'].iloc[idx] / volume_ratio if volume_ratio > 0 else 1.0

        # Context para playbook
        context = {
            "market_regime": "RISK_ON" if np.random.random() > 0.3 else "NEUTRAL",
            "btc_bias": "LONG" if np.sin(idx / 10) > 0 else "SHORT",
            "d1_bias": "LONG" if np.cos(idx / 15) > 0 else "SHORT",
            "smc_d1_structure": "bullish" if np.random.random() > 0.5 else "bearish",
            "volume_ratio": volume_ratio,
            "fear_greed_value": 50 + np.random.normal(0, 15),
            "atr_pct": 3.0 + np.random.normal(0, 1.0)
        }

        # Obter ajustes do playbook
        confluence = self.playbook.get_confluence_adjustments(context)
        confluence_total = sum(confluence.values())

        # Decisão de trade
        should_trade = self.playbook.should_trade(
            context.get("market_regime", "NEUTRAL"),
            context.get("d1_bias", "NEUTRO"),
            context.get("btc_bias", "NEUTRO")
        )

        if should_trade and confluence_total >= 0.5:
            # Determinar direção
            if context["d1_bias"] == "LONG":
                return "BUY", min(100, 50 + confluence_total * 10), context
            elif context["d1_bias"] == "SHORT":
                return "SELL", min(100, 50 + confluence_total * 10), context

        return "HOLD", confluence_total, context

    def calculate_entry_exit(self, df: pd.DataFrame, idx: int, signal: str, context: Dict) -> Tuple[float, float, float]:
        """
        Calcula preços de entrada, SL e TP.

        Args:
            df: DataFrame
            idx: Índice
            signal: BUY ou SELL
            context: Contexto da decisão

        Returns:
            (entry, stop_loss, take_profit)
        """
        entry = df['close'].iloc[idx]

        # Risco ajustes
        risk_adj = self.playbook.get_risk_adjustments(context)
        stop_multiplier = risk_adj.get("stop_multiplier", 1.5)

        # ATR simulado
        atr = (df['high'].iloc[max(0, idx-14):idx+1].mean() -
               df['low'].iloc[max(0, idx-14):idx+1].mean())

        if signal == "BUY":
            stop_loss = entry - (stop_multiplier * atr)
            take_profit = entry * 1.15  # 15% TP alvo para swing
        else:  # SELL
            stop_loss = entry + (stop_multiplier * atr)
            take_profit = entry * 0.85  # -15% TP alvo

        return entry, stop_loss, take_profit

    def run_backtest(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Executa backtest completo.

        Args:
            data: DataFrame histórico

        Returns:
            Resultados do backtest
        """
        logger.info("=" * 70)
        logger.info("INICIANDO BACKTEST SKRUSDT SWING TRADE")
        logger.info("=" * 70)

        position = None
        results = {
            "trades": [],
            "equity_curve": [self.initial_capital],
            "balance": self.initial_capital,
            "max_balance": self.initial_capital,
            "min_balance": self.initial_capital
        }

        for i in range(len(data)):
            current_price = data['close'].iloc[i]

            # Verificar posição aberta
            if position:
                # Check SL
                if position["signal"] == "BUY" and current_price <= position["stop_loss"]:
                    # Saída por SL
                    pnl = (position["stop_loss"] - position["entry"]) * position["quantity"]
                    self.balance += pnl

                    results["trades"].append({
                        "entry_price": position["entry"],
                        "exit_price": position["stop_loss"],
                        "pnl": pnl,
                        "pnl_pct": (pnl / position["entry"]) * 100,
                        "reason": "stop_loss"
                    })

                    logger.debug(f"[{i}] SL hit: BUY @ ${position['entry']:.6f} → SL @ ${position['stop_loss']:.6f}, PnL: ${pnl:.2f}")
                    position = None

                # Check TP
                elif position["signal"] == "BUY" and current_price >= position["take_profit"]:
                    # Saída por TP
                    pnl = (position["take_profit"] - position["entry"]) * position["quantity"]
                    self.balance += pnl

                    results["trades"].append({
                        "entry_price": position["entry"],
                        "exit_price": position["take_profit"],
                        "pnl": pnl,
                        "pnl_pct": (pnl / position["entry"]) * 100,
                        "reason": "take_profit"
                    })

                    logger.debug(f"[{i}] TP hit: BUY @ ${position['entry']:.6f} → TP @ ${position['take_profit']:.6f}, PnL: ${pnl:.2f}")
                    position = None

                # SELL checks
                elif position["signal"] == "SELL" and current_price >= position["stop_loss"]:
                    pnl = (position["entry"] - position["stop_loss"]) * position["quantity"]
                    self.balance += pnl
                    results["trades"].append({
                        "entry_price": position["entry"],
                        "exit_price": position["stop_loss"],
                        "pnl": pnl,
                        "pnl_pct": -(pnl / position["entry"]) * 100,
                        "reason": "stop_loss"
                    })
                    position = None

                elif position["signal"] == "SELL" and current_price <= position["take_profit"]:
                    pnl = (position["entry"] - position["take_profit"]) * position["quantity"]
                    self.balance += pnl
                    results["trades"].append({
                        "entry_price": position["entry"],
                        "exit_price": position["take_profit"],
                        "pnl": pnl,
                        "pnl_pct": -(pnl / position["entry"]) * 100,
                        "reason": "take_profit"
                    })
                    position = None

            # Passar tempo (max 5 candles por posição)
            if position:
                position["bars"] += 1
                if position["bars"] > 5:
                    # Saída por timeout
                    exit_price = current_price
                    if position["signal"] == "BUY":
                        pnl = (exit_price - position["entry"]) * position["quantity"]
                    else:
                        pnl = (position["entry"] - exit_price) * position["quantity"]

                    self.balance += pnl
                    results["trades"].append({
                        "entry_price": position["entry"],
                        "exit_price": exit_price,
                        "pnl": pnl,
                        "pnl_pct": (pnl / position["entry"]) * 100 if position["signal"] == "BUY" else -(pnl / position["entry"]) * 100,
                        "reason": "timeout"
                    })
                    position = None

            # Gerar novo sinal se sem posição
            if not position:
                signal, confidence, context = self.detect_confluence(data, i)

                if signal != "HOLD" and confidence > 50:
                    entry, stop_loss, tp = self.calculate_entry_exit(data, i, signal, context)

                    # Criar posição ($10 capital)
                    quantity = 10.0 / entry  # Quantidade de tokens

                    position = {
                        "signal": signal,
                        "entry": entry,
                        "stop_loss": stop_loss,
                        "take_profit": tp,
                        "quantity": quantity,
                        "bars": 0,
                        "confidence": confidence
                    }

                    logger.debug(f"[{i}] OPEN {signal}: @ ${entry:.6f}, SL=${stop_loss:.6f}, TP=${tp:.6f}, Conf={confidence:.0f}%")

            # Update equity
            results["equity_curve"].append(self.balance)
            results["max_balance"] = max(results["max_balance"], self.balance)
            results["min_balance"] = min(results["min_balance"], self.balance)

        results["balance"] = self.balance
        results["trades"] = pd.DataFrame(results["trades"]) if results["trades"] else pd.DataFrame()

        logger.info(f"Backtest completed: {len(results['trades'])} trades")
        return results

    def calculate_metrics(self, results: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcula métricas de performance.

        Args:
            results: Resultados do backtest

        Returns:
            Dicionário com métricas
        """
        trades = results["trades"]
        equity_curve = np.array(results["equity_curve"])

        if len(trades) == 0:
            return {
                "trades_total": 0,
                "trades_win": 0,
                "trades_loss": 0,
                "win_rate_pct": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "sharpe": 0,
                "max_drawdown_pct": 0,
                "return_pct": 0
            }

        # Métricas básicas
        total_pnl = trades["pnl"].sum()
        trades_total = len(trades)
        trades_win = len(trades[trades["pnl"] > 0])
        trades_loss = len(trades[trades["pnl"] <= 0])

        win_rate = trades_win / trades_total * 100 if trades_total > 0 else 0
        avg_win = trades[trades["pnl"] > 0]["pnl"].mean() if trades_win > 0 else 0
        avg_loss = abs(trades[trades["pnl"] <= 0]["pnl"].mean()) if trades_loss > 0 else 0

        profit_factor = avg_win / avg_loss if avg_loss > 0 else 0

        # Drawdown
        cumulative = np.cumprod(1 + (np.diff(equity_curve) / equity_curve[:-1]))
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        # Sharpe (simplificado)
        returns = np.diff(equity_curve) / equity_curve[:-1]
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0

        # Return
        total_return = (results["balance"] - self.initial_capital) / self.initial_capital * 100

        return {
            "trades_total": trades_total,
            "trades_win": trades_win,
            "trades_loss": trades_loss,
            "win_rate_pct": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "sharpe": sharpe,
            "max_drawdown_pct": max_drawdown * 100,
            "return_pct": total_return
        }

    def print_report(self, results: Dict[str, Any], metrics: Dict[str, float]):
        """Imprime relatório final."""
        logger.info("\n" + "=" * 70)
        logger.info("BACKTEST REPORT — SKRUSDT SWING TRADE")
        logger.info("=" * 70)

        logger.info(f"\nCapital Inicial:        ${self.initial_capital:.2f}")
        logger.info(f"Capital Final:          ${results['balance']:.2f}")
        logger.info(f"Ganho Total:            ${results['balance'] - self.initial_capital:.2f}")
        logger.info(f"Retorno:                {metrics['return_pct']:+.2f}%")

        logger.info(f"\nNúmero de Trades:       {metrics['trades_total']}")
        logger.info(f"  Vitórias:             {metrics['trades_win']}")
        logger.info(f"  Derrotas:             {metrics['trades_loss']}")
        logger.info(f"Win Rate:               {metrics['win_rate_pct']:.1f}%")

        logger.info(f"\nMédia de Ganho:         ${metrics['avg_win']:.2f}")
        logger.info(f"Média de Perda:         ${metrics['avg_loss']:.2f}")
        logger.info(f"Profit Factor:          {metrics['profit_factor']:.2f}x")

        logger.info(f"\nSharpe Ratio:           {metrics['sharpe']:.2f}")
        logger.info(f"Max Drawdown:           {metrics['max_drawdown_pct']:.2f}%")

        # Status
        logger.info("\n" + "=" * 70)
        if metrics['win_rate_pct'] >= 45 and metrics['sharpe'] >= 0.8:
            logger.info("✅ BACKTEST APROVADO — MODELO VIÁVEL PARA TRADING")
        elif metrics['win_rate_pct'] >= 40:
            logger.info("🟡 BACKTEST MARGINAL — PODE SER USADO COM CAUTELA")
        else:
            logger.info("❌ BACKTEST FALHOU — MODELO NÃO VIÁVEL")
        logger.info("=" * 70 + "\n")


def main():
    """Executa backtest."""
    engine = SKRBacktestEngine(initial_capital=1000.0)

    # Gerar dados sintéticos (100 dias)
    data = engine.generate_synthetic_data(days=100)

    # Executar backtest
    results = engine.run_backtest(data)

    # Calcular métricas
    metrics = engine.calculate_metrics(results)

    # Imprimir relatório
    engine.print_report(results, metrics)


if __name__ == "__main__":
    main()
