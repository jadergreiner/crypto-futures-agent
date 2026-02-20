"""
Validador de Métricas para Backtest — F-12 Risk Clearance

Implementa checklist automático de 6 métricas críticas para GO/NO-GO.
"""

from dataclasses import dataclass
from typing import List, Optional
import json


@dataclass
class BacktestMetrics:
    """Métricas de backteste com critérios de risco."""
    
    # 6 Métricas Críticas (GO/NO-GO)
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    profit_factor: float
    consecutive_losses: int
    recovery_factor: float
    
    # Métricas Informativas  
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_trade_duration_hours: float = 0.0
    largest_win_pct: float = 0.0
    largest_loss_pct: float = 0.0
    total_return_pct: float = 0.0
    
    # Critérios de Passagem
    SHARPE_MIN = 1.0
    MAX_DD_MAX = 15.0
    WIN_RATE_MIN = 45.0
    PROFIT_FACTOR_MIN = 1.5
    CONSECUTIVE_LOSSES_MAX = 5
    RECOVERY_FACTOR_MIN = 2.0
    
    @property
    def risk_clearance_status(self) -> str:
        """
        Determina GO/NO-GO baseado em 6 métricas críticas.
        
        Returns:
            "✅ GO" se TODAS as métricas passam
            "❌ NO-GO" se qualquer métrica falha
        """
        checks = [
            ("Sharpe Ratio", self.sharpe_ratio >= self.SHARPE_MIN),
            ("Max Drawdown", self.max_drawdown_pct <= self.MAX_DD_MAX),
            ("Win Rate", self.win_rate_pct >= self.WIN_RATE_MIN),
            ("Profit Factor", self.profit_factor >= self.PROFIT_FACTOR_MIN),
            ("Consecutive Losses", self.consecutive_losses <= self.CONSECUTIVE_LOSSES_MAX),
            ("Recovery Factor", self.recovery_factor >= self.RECOVERY_FACTOR_MIN),
        ]
        
        all_pass = all(check[1] for check in checks)
        return "✅ GO" if all_pass else "❌ NO-GO"
    
    def get_checklist(self) -> List[tuple]:
        """Retorna checklist de validação com status."""
        return [
            ("Sharpe Ratio", self.sharpe_ratio, "≥", self.SHARPE_MIN,
             self.sharpe_ratio >= self.SHARPE_MIN),
            ("Max Drawdown", self.max_drawdown_pct, "≤", self.MAX_DD_MAX,
             self.max_drawdown_pct <= self.MAX_DD_MAX),
            ("Win Rate", self.win_rate_pct, "≥", self.WIN_RATE_MIN,
             self.win_rate_pct >= self.WIN_RATE_MIN),
            ("Profit Factor", self.profit_factor, "≥", self.PROFIT_FACTOR_MIN,
             self.profit_factor >= self.PROFIT_FACTOR_MIN),
            ("Consecutive Losses", self.consecutive_losses, "≤", 
             self.CONSECUTIVE_LOSSES_MAX,
             self.consecutive_losses <= self.CONSECUTIVE_LOSSES_MAX),
            ("Recovery Factor", self.recovery_factor, "≥", 
             self.RECOVERY_FACTOR_MIN,
             self.recovery_factor >= self.RECOVERY_FACTOR_MIN),
        ]
    
    def print_report(self, symbol: str = "BTCUSDT", 
                    start_date: str = "2023-01-01",
                    end_date: str = "2023-12-31"):
        """Imprime relatório formatado."""
        
        status = self.risk_clearance_status
        
        print("\n" + "="*60)
        print(f"Backtester Report — {symbol}")
        print(f"Period: {start_date} → {end_date}")
        print("="*60)
        print(f"\nRISK CLEARANCE STATUS: {status}\n")
        
        # Checklist
        print("Critérios de Risk Clearance:")
        print("-"*60)
        for metric, value, op, threshold, passed in self.get_checklist():
            status_icon = "✓" if passed else "✗"
            print(f" [{status_icon}] {metric:20} {value:8.2f} {op} {threshold}")
        
        # Métricas Extras
        print("\nMétricas Informativas:")
        print("-"*60)
        print(f"  Total Trades:       {self.total_trades}")
        print(f"  Winning Trades:     {self.winning_trades} "
              f"({self.win_rate_pct:.1f}%)")
        print(f"  Losing Trades:      {self.losing_trades}")
        print(f"  Avg Trade Duration: {self.avg_trade_duration_hours:.1f}h")
        print(f"  Largest Win:        +{self.largest_win_pct:.2f}%")
        print(f"  Largest Loss:       -{self.largest_loss_pct:.2f}%")
        print(f"  Total Return:       {self.total_return_pct:+.1f}%")
        
        # Recomendação Final
        print("\n" + "="*60)
        if self.risk_clearance_status == "✅ GO":
            print("✅ APROVADO PARA: Paper Trading (v0.5)")
            print("   Próximo passo: Implementar ciclo de papel trading")
        else:
            print("❌ NÃO APROVADO")
            print("   Ações necessárias:")
            for metric, value, op, threshold, passed in self.get_checklist():
                if not passed:
                    diff = value - threshold if op == "≥" else threshold - value
                    print(f"     - {metric}: melhorar {diff:.2f} unidades")
        
        print("="*60 + "\n")
    
    def to_json(self) -> str:
        """Serializa para JSON."""
        return json.dumps({
            "metrics": {
                "sharpe_ratio": self.sharpe_ratio,
                "max_drawdown_pct": self.max_drawdown_pct,
                "win_rate_pct": self.win_rate_pct,
                "profit_factor": self.profit_factor,
                "consecutive_losses": self.consecutive_losses,
                "recovery_factor": self.recovery_factor,
            },
            "status": self.risk_clearance_status,
            "trades": {
                "total": self.total_trades,
                "winning": self.winning_trades,
                "losing": self.losing_trades,
                "avg_duration_hours": self.avg_trade_duration_hours,
            },
            "performance": {
                "largest_win_pct": self.largest_win_pct,
                "largest_loss_pct": self.largest_loss_pct,
                "total_return_pct": self.total_return_pct,
            }
        }, indent=2)


# Exemplo de uso
if __name__ == "__main__":
    # Cenário de teste: modelo com performance marginal
    metrics = BacktestMetrics(
        sharpe_ratio=1.15,
        max_drawdown_pct=12.5,
        win_rate_pct=52.3,
        profit_factor=1.78,
        consecutive_losses=3,
        recovery_factor=2.25,
        sortino_ratio=2.10,
        calmar_ratio=8.14,
        total_trades=87,
        winning_trades=45,
        losing_trades=42,
        avg_trade_duration_hours=4.2,
        largest_win_pct=5.2,
        largest_loss_pct=3.8,
        total_return_pct=34.5,
    )
    
    # Imprimir relatório
    metrics.print_report("BTCUSDT", "2023-01-01", "2023-12-31")
    
    # Exportar JSON
    print("JSON Output:")
    print(metrics.to_json())
