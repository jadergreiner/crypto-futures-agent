"""
CANARY MONITORING - TASK-004 REAL-TIME MONITORING
===================================================
Sistema de monitoramento em tempo real durante canary deployment.
Coleta métricas, valida gates e dispara alertas.

Owner: Dev + Planner
Execução: 22 FEV 10:00-14:00 UTC (contínuo)
Status: LIVE during canary phases
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass, asdict


@dataclass
class TradeMetric:
    """Métrica individual de trade."""
    timestamp: str
    pair: str
    side: str  # BUY / SELL
    entry_price: float
    quantity: float
    latency_ms: int
    fill_rate_pct: float
    slippage_bps: float
    signal_confidence: float
    confluence_score: float
    status: str  # FILLED / PENDING / FAILED
    error_msg: Optional[str] = None


@dataclass
class RiskMetric:
    """Métrica de risco."""
    timestamp: str
    cumulative_drawdown_pct: float
    current_drawdown_pct: float
    max_intraday_drawdown_pct: float
    risk_gate_status: str  # CLEARED / RISKY / BLOCKED
    circuit_breaker_armed: bool
    circuit_breaker_triggered: bool
    open_positions: int


class CanaryMonitor:
    """Monitor em tempo real para canary deployment."""
    
    # Thresholds
    LATENCY_WARNING_MS = 750
    LATENCY_CRITICAL_MS = 1500
    FILL_RATE_WARNING = 95.0
    FILL_RATE_CRITICAL = 90.0
    SLIPPAGE_WARNING_BPS = 20
    SLIPPAGE_CRITICAL_BPS = 50
    DRAWDOWN_WARNING_PCT = -1.5
    DRAWDOWN_CRITICAL_PCT = -2.5
    CONFLUENCE_WARNING = 2.5
    CONFLUENCE_CRITICAL = 2.0
    ERROR_RATE_WARNING = 1.0
    ERROR_RATE_CRITICAL = 3.0
    
    def __init__(self, phase: int = 1):
        """
        Inicializa monitor.
        
        Args:
            phase: 1 (10%), 2 (50%), ou 3 (100%)
        """
        self.phase = phase
        self.start_time = datetime.utcnow()
        self.metrics_window = deque(maxlen=1000)
        self.risk_metrics = deque(maxlen=100)
        self.alerts = []
        self.running = False
        
        # Histórico para cálculo de médias
        self.latencies = deque(maxlen=100)
        self.fill_rates = deque(maxlen=100)
        self.slippages = deque(maxlen=100)
        self.confluences = deque(maxlen=100)
        self.errors = deque(maxlen=100)
    
    def record_trade(self, metric: TradeMetric) -> None:
        """Registra métrica de trade."""
        self.metrics_window.append(metric)
        
        # Atualiza históricos
        self.latencies.append(metric.latency_ms)
        self.fill_rates.append(metric.fill_rate_pct)
        self.slippages.append(metric.slippage_bps)
        self.confluences.append(metric.confluence_score)
        
        if metric.status == "FAILED":
            self.errors.append(1)
        else:
            self.errors.append(0)
        
        # Valida thresholds
        self._validate_trade_metric(metric)
    
    def record_risk_metric(self, metric: RiskMetric) -> None:
        """Registra métrica de risco."""
        self.risk_metrics.append(metric)
        self._validate_risk_metric(metric)
    
    def _validate_trade_metric(self, metric: TradeMetric) -> None:
        """Valida trade contra thresholds."""
        alerts_local = []
        
        # Latência
        if metric.latency_ms > self.LATENCY_CRITICAL_MS:
            alerts_local.append({
                "severity": "CRITICAL",
                "type": "LATENCY",
                "value": metric.latency_ms,
                "threshold": self.LATENCY_CRITICAL_MS,
                "message": f"Latência crítica: {metric.latency_ms}ms"
            })
        elif metric.latency_ms > self.LATENCY_WARNING_MS:
            alerts_local.append({
                "severity": "WARNING",
                "type": "LATENCY",
                "value": metric.latency_ms,
                "threshold": self.LATENCY_WARNING_MS,
                "message": f"Latência elevada: {metric.latency_ms}ms"
            })
        
        # Fill rate
        if metric.fill_rate_pct < self.FILL_RATE_CRITICAL:
            alerts_local.append({
                "severity": "CRITICAL",
                "type": "FILL_RATE",
                "value": metric.fill_rate_pct,
                "threshold": self.FILL_RATE_CRITICAL,
                "message": f"Fill rate crítica: {metric.fill_rate_pct:.1f}%"
            })
        elif metric.fill_rate_pct < self.FILL_RATE_WARNING:
            alerts_local.append({
                "severity": "WARNING",
                "type": "FILL_RATE",
                "value": metric.fill_rate_pct,
                "threshold": self.FILL_RATE_WARNING,
                "message": f"Fill rate baixa: {metric.fill_rate_pct:.1f}%"
            })
        
        # Slippage
        if metric.slippage_bps > self.SLIPPAGE_CRITICAL_BPS:
            alerts_local.append({
                "severity": "CRITICAL",
                "type": "SLIPPAGE",
                "value": metric.slippage_bps,
                "threshold": self.SLIPPAGE_CRITICAL_BPS,
                "message": f"Slippage crítica: {metric.slippage_bps}bps"
            })
        elif metric.slippage_bps > self.SLIPPAGE_WARNING_BPS:
            alerts_local.append({
                "severity": "WARNING",
                "type": "SLIPPAGE",
                "value": metric.slippage_bps,
                "threshold": self.SLIPPAGE_WARNING_BPS,
                "message": f"Slippage alta: {metric.slippage_bps}bps"
            })
        
        # Confluence score
        if metric.confluence_score < self.CONFLUENCE_CRITICAL:
            alerts_local.append({
                "severity": "CRITICAL",
                "type": "CONFLUENCE",
                "value": metric.confluence_score,
                "threshold": self.CONFLUENCE_CRITICAL,
                "message": f"Confluence crítica: {metric.confluence_score:.1f}/4"
            })
        elif metric.confluence_score < self.CONFLUENCE_WARNING:
            alerts_local.append({
                "severity": "WARNING",
                "type": "CONFLUENCE",
                "value": metric.confluence_score,
                "threshold": self.CONFLUENCE_WARNING,
                "message": f"Confluence baixa: {metric.confluence_score:.1f}/4"
            })
        
        # Adiciona ao histórico
        for alert in alerts_local:
            alert["timestamp"] = metric.timestamp
            alert["pair"] = metric.pair
            self.alerts.append(alert)
    
    def _validate_risk_metric(self, metric: RiskMetric) -> None:
        """Valida riscos contra thresholds."""
        alerts_local = []
        
        # Drawdown
        if metric.cumulative_drawdown_pct < self.DRAWDOWN_CRITICAL_PCT:
            alerts_local.append({
                "severity": "CRITICAL",
                "type": "DRAWDOWN",
                "value": metric.cumulative_drawdown_pct,
                "threshold": self.DRAWDOWN_CRITICAL_PCT,
                "message": f"Drawdown crítica: {metric.cumulative_drawdown_pct:.2f}%"
            })
        elif metric.cumulative_drawdown_pct < self.DRAWDOWN_WARNING_PCT:
            alerts_local.append({
                "severity": "WARNING",
                "type": "DRAWDOWN",
                "value": metric.cumulative_drawdown_pct,
                "threshold": self.DRAWDOWN_WARNING_PCT,
                "message": f"Drawdown elevada: {metric.cumulative_drawdown_pct:.2f}%"
            })
        
        # Circuit breaker
        if metric.circuit_breaker_triggered:
            alerts_local.append({
                "severity": "CRITICAL",
                "type": "CIRCUIT_BREAKER",
                "value": metric.cumulative_drawdown_pct,
                "message": "⚠️  CIRCUIT BREAKER TRIGGERED — Iniciando rollback!"
            })
        
        # Adiciona ao histórico
        for alert in alerts_local:
            alert["timestamp"] = metric.timestamp
            self.alerts.append(alert)
    
    def get_phase_duration_elapsed(self) -> float:
        """Retorna tempo decorrido desta fase (segundos)."""
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    def get_average_metrics(self) -> Dict:
        """Retorna médias dos últimos trades."""
        if not self.latencies:
            return {}
        
        return {
            "avg_latency_ms": sum(self.latencies) / len(self.latencies),
            "max_latency_ms": max(self.latencies),
            "min_latency_ms": min(self.latencies),
            "avg_fill_rate": sum(self.fill_rates) / len(self.fill_rates) if self.fill_rates else 0,
            "avg_slippage_bps": sum(self.slippages) / len(self.slippages) if self.slippages else 0,
            "avg_confluence": sum(self.confluences) / len(self.confluences) if self.confluences else 0,
            "error_rate": (sum(self.errors) / len(self.errors) * 100) if self.errors else 0,
        }
    
    def get_latest_risk_status(self) -> Optional[RiskMetric]:
        """Retorna último status de risco."""
        if not self.risk_metrics:
            return None
        return self.risk_metrics[-1]
    
    def get_critical_alerts(self) -> List[Dict]:
        """Retorna alertas críticos."""
        return [a for a in self.alerts if a.get("severity") == "CRITICAL"]
    
    def get_warnings(self) -> List[Dict]:
        """Retorna avisos."""
        return [a for a in self.alerts if a.get("severity") == "WARNING"]
    
    def print_status(self) -> None:
        """Imprime status atual no console."""
        print("\n" + "="*70)
        print(f"📊 CANARY PHASE {self.phase} — MONITORING STATUS")
        print(f"⏱️  Tempo decorrido: {self.get_phase_duration_elapsed():.0f}s")
        print("="*70)
        
        # Métricas gerais
        avg_metrics = self.get_average_metrics()
        if avg_metrics:
            print("\n📈 Average Metrics:")
            print(f"  Latência: {avg_metrics.get('avg_latency_ms', 0):.0f}ms " +
                  f"(max: {avg_metrics.get('max_latency_ms', 0):.0f}ms)")
            print(f"  Fill Rate: {avg_metrics.get('avg_fill_rate', 0):.1f}%")
            print(f"  Slippage: {avg_metrics.get('avg_slippage_bps', 0):.1f}bps")
            print(f"  Confluence: {avg_metrics.get('avg_confluence', 0):.2f}/4")
            print(f"  Error Rate: {avg_metrics.get('error_rate', 0):.1f}%")
        
        # Status de risco
        risk = self.get_latest_risk_status()
        if risk:
            print(f"\n⚠️  Risk Status:")
            print(f"  Cumulative Drawdown: {risk.cumulative_drawdown_pct:.2f}%")
            print(f"  Current Drawdown: {risk.current_drawdown_pct:.2f}%")
            print(f"  Max Intraday: {risk.max_intraday_drawdown_pct:.2f}%")
            print(f"  Gate Status: {risk.risk_gate_status}")
            print(f"  Open Positions: {risk.open_positions}")
        
        # Alertas
        critical = self.get_critical_alerts()
        warnings = self.get_warnings()
        
        if critical:
            print(f"\n🚨 CRITICAL ALERTS ({len(critical)}):")
            for alert in critical[-5:]:  # Últimos 5
                print(f"  ❌ {alert.get('message', 'Unknown alert')}")
        
        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for alert in warnings[-5:]:  # Últimos 5
                print(f"  ⚠ {alert.get('message', 'Unknown warning')}")
        
        # Decisão de gate
        print(f"\n🎯 Phase {self.phase} Decision:")
        if len(critical) > 0:
            print(f"  ❌ FAIL — {len(critical)} críticas detectadas")
        elif len(warnings) > (2 if self.phase < 3 else 0):
            print(f"  ⚠️  CAUTION — {len(warnings)} warnings, monitorar")
        else:
            print(f"  ✅ PASS — Métrica saudável")
        
        print("="*70 + "\n")
    
    def export_metrics_json(self, filename: Optional[str] = None) -> str:
        """Exporta métrica para JSON."""
        if filename is None:
            filename = f"canary_phase{self.phase}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            "phase": self.phase,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": self.get_phase_duration_elapsed(),
            "trades_count": len(self.metrics_window),
            "average_metrics": self.get_average_metrics(),
            "latest_risk": asdict(self.get_latest_risk_status()) if self.get_latest_risk_status() else None,
            "critical_alerts": len(self.get_critical_alerts()),
            "warnings": len(self.get_warnings()),
            "recent_alerts": self.alerts[-10:]  # Últimas 10
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return filename


def simulate_trades_demo() -> None:
    """Demo função que simula trades para teste."""
    print("\n🧪 DEMO MODE — Simulando trades para teste de monitoring\n")
    
    monitor = CanaryMonitor(phase=1)
    
    # Simula 5 trades
    for i in range(5):
        trade = TradeMetric(
            timestamp=datetime.utcnow().isoformat(),
            pair="BTCUSDT",
            side="BUY",
            entry_price=42500.0 + i*100,
            quantity=0.05,
            latency_ms=250 + i*20,
            fill_rate_pct=98.5 - i*0.5,
            slippage_bps=12.5 + i*1.5,
            signal_confidence=78.0 + i*2,
            confluence_score=3.5 + (i % 2) * 0.25,
            status="FILLED"
        )
        monitor.record_trade(trade)
    
    # Simula riscos
    risk = RiskMetric(
        timestamp=datetime.utcnow().isoformat(),
        cumulative_drawdown_pct=-0.8,
        current_drawdown_pct=-0.5,
        max_intraday_drawdown_pct=-0.8,
        risk_gate_status="CLEARED",
        circuit_breaker_armed=True,
        circuit_breaker_triggered=False,
        open_positions=3
    )
    monitor.record_risk_metric(risk)
    
    # Imprime status
    monitor.print_status()
    
    # Exporta
    filename = monitor.export_metrics_json()
    print(f"✅ Métricas exportadas para: {filename}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        simulate_trades_demo()
    else:
        print("Uso: python canary_monitoring.py [demo]")
        print("  demo — Executa simulação para teste")
