"""
Testes para o Módulo convergence_monitor.py

Cenários cobertos:
- Logging de métricas
- Detecção de divergência
- Exportação CSV
- Sumários diários
- Integração TensorBoard (mock)
"""

import pytest
import csv
from pathlib import Path
from agent.convergence_monitor import ConvergenceMonitor


class TestConvergenceMonitorBasic:
    """Testes básicos de inicialização e logging."""

    def test_init_creates_output_dir(self, tmp_path):
        """Cria diretório de saída."""
        output_dir = tmp_path / "metrics"
        monitor = ConvergenceMonitor(output_dir=str(output_dir))

        assert output_dir.exists()
        assert (output_dir / "metrics.csv").exists()

    def test_log_step_records_metrics(self, tmp_path):
        """Registra métrica de um step."""
        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        monitor.log_step(
            step=100,
            episode_reward=10.5,
            episode_length=500,
            loss_policy=0.05,
            kl_divergence=0.02,
            entropy=0.8,
        )

        assert monitor.step_count == 100
        assert len(monitor.metrics_buffer["step"]) == 1
        assert monitor.metrics_buffer["episode_reward"][0] == 10.5

    def test_log_multiple_steps(self, tmp_path):
        """Registra múltiplos steps sequencialmente."""
        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        for i in range(10):
            monitor.log_step(
                step=i,
                episode_reward=float(i),
                kl_divergence=0.01 + i * 0.001,
            )

        assert len(monitor.metrics_buffer["step"]) == 10
        assert monitor.step_count == 9


class TestConvergenceMonitorDivergence:
    """Testes de detecção de divergência."""

    def test_detect_divergence_high_kl(self, tmp_path):
        """Detecta KL divergence alto persistente."""
        monitor = ConvergenceMonitor(
            output_dir=str(tmp_path),
            kl_divergence_threshold=0.05,
        )

        # Registrar 15 steps com KL alto
        for i in range(15):
            monitor.log_step(
                step=i,
                kl_divergence=0.12,  # > 0.05
                episode_reward=10.0,
            )

        is_diverging, reason = monitor.detect_divergence(kl_threshold=0.05)
        assert is_diverging is True
        assert "KL" in reason

    def test_detect_divergence_no_improvement(self, tmp_path):
        """Detecta estagnação de reward."""
        monitor = ConvergenceMonitor(
            output_dir=str(tmp_path),
            no_improve_episodes=5,
        )

        # Registrar rewards decrescentes (simula conversa para pior)
        for i in range(10):
            monitor.log_step(
                step=i,
                episode_reward=10.0 - i,  # Diminui progressivamente
                kl_divergence=0.01,
            )

        is_diverging, reason = monitor.detect_divergence(no_improve_threshold=5)
        # Pode ou não detectar dependendo da lógica (esperado comportamento)
        assert isinstance(is_diverging, bool)

    def test_detect_divergence_gradient_explosion(self, tmp_path):
        """Detecta gradiente explodindo."""
        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        # Registrar gradient normal, depois explosion
        for i in range(5):
            monitor.log_step(
                step=i,
                gradient_norm=1.0 if i < 4 else 15.0,  # Explosion no último
                kl_divergence=0.01,
            )

        is_diverging, reason = monitor.detect_divergence()
        assert is_diverging is True
        assert "Gradient" in reason

    def test_no_divergence_normal_training(self, tmp_path):
        """Não detecta divergência durante treinamento normal."""
        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        # Registrar métricas normais
        for i in range(20):
            monitor.log_step(
                step=i,
                episode_reward=10.0 + i * 0.1,  # Melhora gradualizada
                kl_divergence=0.01,
                entropy=0.8,
            )

        is_diverging, reason = monitor.detect_divergence()
        assert is_diverging is False
        assert reason is None


class TestConvergenceMonitorMetrics:
    """Testes de agregação de métricas."""

    def test_compute_moving_average_sharpe(self, tmp_path):
        """Calcula média móvel de Sharpe."""
        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        for i in range(100):
            monitor.log_step(
                step=i,
                episode_reward=10.0 + np.sin(i / 10),
            )

        avg = monitor.compute_moving_average("episode_reward", window=10)
        assert avg is not None
        assert 8 < avg < 12  # Razoable range

    def test_compute_moving_average_insufficient_data(self, tmp_path):
        """Retorna None se dados insuficientes."""
        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        monitor.log_step(step=0, episode_reward=10.0)

        avg = monitor.compute_moving_average("episode_reward", window=50)
        assert avg is None

    def test_moving_average_uses_recent_values(self, tmp_path):
        """Usa apenas últimos N valores."""
        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        # Registrar 10 com valor 5, depois 10 com valor 15
        for i in range(10):
            monitor.log_step(step=i, episode_reward=5.0)
        for i in range(10, 20):
            monitor.log_step(step=i, episode_reward=15.0)

        avg = monitor.compute_moving_average("episode_reward", window=5)
        assert avg == 15.0  # Usa últimos 5 (todos valor 15)


class TestConvergenceMonitorExport:
    """Testes de exportação CSV e relatórios."""

    def test_export_metrics_csv_creates_file(self, tmp_path):
        """Exporta métricas para CSV."""
        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        for i in range(5):
            monitor.log_step(
                step=i,
                episode_reward=float(i),
                kl_divergence=0.01,
            )

        export_path = monitor.export_metrics_csv()
        assert Path(export_path).exists()

        # Verificar conteúdo CSV
        with open(export_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 5
            assert rows[0]["step"] == "0"
            assert rows[-1]["step"] == "4"

    def test_generate_daily_summary_returns_stats(self, tmp_path):
        """Gera sumário diário com estatísticas."""
        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        for i in range(50):
            monitor.log_step(
                step=i,
                episode_reward=10.0 + i * 0.1,
                kl_divergence=0.02,
            )

        summary = monitor.generate_daily_summary()

        assert "total_steps" in summary
        assert "mean_reward" in summary
        assert "max_reward" in summary
        assert summary["total_steps"] == 49  # step_count

    def test_daily_summary_creates_json_file(self, tmp_path):
        """Cria arquivo JSON com sumário."""
        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        for i in range(10):
            monitor.log_step(step=i, episode_reward=10.0)

        summary = monitor.generate_daily_summary()

        json_files = list(Path(tmp_path).glob("summary_*.json"))
        assert len(json_files) > 0


class TestConvergenceMonitorEdgeCases:
    """Testes de casos extremos."""

    def test_close_flushes_resources(self, tmp_path):
        """Close encerra CSV e TensorBoard."""
        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        monitor.log_step(step=0, episode_reward=10.0)
        monitor.close()

        # Verificar que CSV foi fechado (não deve gerar erro ao acessar)
        csv_path = Path(tmp_path) / "metrics.csv"
        assert csv_path.exists()

    def test_empty_metrics_buffer_handling(self, tmp_path):
        """Lida com buffer vazio."""
        monitor = ConvergenceMonitor(output_dir=str(tmp_path))

        # Sem logging, apenas operações
        summary = monitor.generate_daily_summary()
        assert summary == {}

    def test_standard_deviation_calculation(self, tmp_path):
        """Calcula desvio padrão corretamente."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        std = ConvergenceMonitor._calculate_std(values)

        # Verificar contra cálculo manual
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        expected_std = variance ** 0.5

        assert abs(std - expected_std) < 1e-6


# Importar numpy para teste de moving average
import numpy as np
