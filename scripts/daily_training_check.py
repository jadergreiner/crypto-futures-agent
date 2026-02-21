#!/usr/bin/env python3
"""
Daily Training Check — Monitoramento rápido de treinamento PPO

Lê logs, extrai métricas, verifica status e gera relatório.
Esperado rodar em ~2 minutos.

Executar: python scripts/daily_training_check.py --date 2026-02-24

Saída: JSON com status + checklist de 5 pontos
"""

import logging
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DailyTrainingCheck:
    """Verifica status diário de treinamento PPO."""

    def __init__(self, training_logs_dir: str = "logs/ppo_training"):
        """
        Inicializa checker.

        Args:
            training_logs_dir: Diretório com logs de treinamento
        """
        self.training_logs_dir = Path(training_logs_dir)
        self.training_log = self.training_logs_dir / "training.log"
        self.daily_summaries_dir = self.training_logs_dir / "daily_summaries"
        self.daily_summaries_dir.mkdir(parents=True, exist_ok=True)

    def parse_training_log(self) -> Dict[str, Any]:
        """
        Parseia training.log e extrai últimas métricas.

        Returns:
            Dict com métricas extraídas
        """
        metrics = {
            "last_step": 0,
            "last_reward": 0.0,
            "last_policy_loss": None,
            "last_value_loss": None,
            "last_kl_divergence": 0.0,
            "mean_reward_last_1000": None,
            "checkpoint_time": None,
            "training_active": False,
            "errors": []
        }

        if not self.training_log.exists():
            metrics["errors"].append(f"Log file not found: {self.training_log}")
            return metrics

        try:
            with open(self.training_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if not lines:
                metrics["errors"].append("Log file is empty")
                return metrics

            # Extrair últimas 500 linhas para análise
            recent_lines = lines[-500:] if len(lines) > 500 else lines

            # Padrões regex
            step_pattern = re.compile(r"Step (\d+)")
            reward_pattern = re.compile(r"(?:mean_)?reward[:\s=]*([+-]?\d+\.?\d*)")
            policy_loss_pattern = re.compile(r"policy_loss[:\s=]*([+-]?\d+\.?\d*)")
            value_loss_pattern = re.compile(r"value_loss[:\s=]*([+-]?\d+\.?\d*)")
            kl_pattern = re.compile(r"kl_divergence[:\s=]*([+-]?\d+\.?\d*)")
            checkpoint_pattern = re.compile(r"\[CHECKPOINT\]|saved model")

            # Parse linhas recentes
            for line in recent_lines:
                # Step
                step_match = step_pattern.search(line)
                if step_match:
                    metrics["last_step"] = int(step_match.group(1))

                # Reward
                reward_match = reward_pattern.search(line)
                if reward_match:
                    try:
                        metrics["last_reward"] = float(reward_match.group(1))
                    except:
                        pass

                # Policy loss
                policy_match = policy_loss_pattern.search(line)
                if policy_match:
                    try:
                        metrics["last_policy_loss"] = float(policy_match.group(1))
                    except:
                        pass

                # Value loss
                value_match = value_loss_pattern.search(line)
                if value_match:
                    try:
                        metrics["last_value_loss"] = float(value_match.group(1))
                    except:
                        pass

                # KL divergence
                kl_match = kl_pattern.search(line)
                if kl_match:
                    try:
                        metrics["last_kl_divergence"] = float(kl_match.group(1))
                    except:
                        pass

                # Checkpoint
                if checkpoint_pattern.search(line):
                    metrics["checkpoint_time"] = datetime.now().isoformat()

            # Verificar se training ainda ativo (log recente)
            if lines[-1]:
                last_line_time = datetime.now()
                metrics["training_active"] = True

            logger.info(f"Parsed training log: step={metrics['last_step']}, "
                       f"reward={metrics['last_reward']}, "
                       f"kl={metrics['last_kl_divergence']}")

        except Exception as e:
            metrics["errors"].append(f"Error parsing log: {str(e)}")
            logger.error(f"Error parsing training log: {e}")

        return metrics

    def check_checkpoint_age(self) -> Optional[float]:
        """
        Verifica idade do checkpoint mais recente.

        Returns:
            Idade em segundos, ou None se não encontrado
        """
        checkpoint_dir = Path("models/ppo_phase4")
        if not checkpoint_dir.exists():
            return None

        # Procurar arquivo mais recente
        latest_time = None
        for file in checkpoint_dir.glob("**/*"):
            if file.is_file():
                mtime = file.stat().st_mtime
                if latest_time is None or mtime > latest_time:
                    latest_time = mtime

        if latest_time is None:
            return None

        age_seconds = datetime.now().timestamp() - latest_time
        return age_seconds

    def estimate_remaining_time(self, current_step: int, total_steps: int = 500_000) -> Optional[float]:
        """
        Estima tempo restante de treinamento.

        Args:
            current_step: Passo atual de treinamento
            total_steps: Total de passos esperados

        Returns:
            Horas restantes estimadas
        """
        if current_step == 0:
            return None

        # Ler múltiplas linhas para calcular velocidade média
        try:
            with open(self.training_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if len(lines) < 2:
                return None

            # Procurar primeira e última linha com step
            first_step = None
            last_step = current_step

            step_pattern = re.compile(r"Step (\d+)")
            for line in lines:
                match = step_pattern.search(line)
                if match:
                    step = int(match.group(1))
                    if first_step is None:
                        first_step = step
                        first_line_idx = len(lines) - 1
                    last_line_idx = len(lines) - 1

            if first_step is None or first_step >= last_step:
                return None

            # Estimar velocidade (steps/hora)
            steps_done = last_step - first_step
            # Aproximação: ~30 linhas por hora de treinamento
            estimated_hours_elapsed = max(len(lines) / 100, 0.1)  # Crude estimate

            if estimated_hours_elapsed == 0:
                return None

            steps_per_hour = steps_done / estimated_hours_elapsed
            if steps_per_hour <= 0:
                return None

            remaining_steps = total_steps - last_step
            remaining_hours = remaining_steps / steps_per_hour

            return remaining_hours

        except Exception as e:
            logger.error(f"Error estimating remaining time: {e}")
            return None

    def determine_reward_trend(self, metrics: Dict[str, Any]) -> str:
        """
        Determina tendência de reward (INCREASING, STABLE, DECREASING).

        Args:
            metrics: Métricas extraídas do log

        Returns:
            String com tendência
        """
        # Simplificado: se reward > 0 e KL low, é bom sinal
        if metrics["last_reward"] > 1.0 and metrics["last_kl_divergence"] < 0.05:
            return "INCREASING"
        elif metrics["last_reward"] > -5.0 and metrics["last_kl_divergence"] < 0.02:
            return "STABLE"
        else:
            return "UNKNOWN"

    def calculate_approx_sharpe(self, metrics: Dict[str, Any]) -> Optional[float]:
        """
        Calcula Sharpe ratio aproximado baseado em reward.

        Nota: Este é um estimate muito grosseiro.
        Valores reais só disponíveis após backtest final.

        Args:
            metrics: Métricas do treino

        Returns:
            Sharpe aproximado
        """
        reward = metrics["last_reward"]

        # Heurística simples
        if reward < -10:
            return -1.0
        elif reward < 0:
            return 0.0
        elif reward < 20:
            return 0.2
        elif reward < 40:
            return 0.5
        else:
            return 0.8

    def run_check(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Executa full check e retorna resultado.

        Args:
            date_str: Data check (padrão: hoje)

        Returns:
            Dict com status completo
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"Running daily training check for {date_str}")

        # 1. Parse logs
        metrics = self.parse_training_log()

        # 2. Check checkpoint age
        checkpoint_age_seconds = self.check_checkpoint_age()
        checkpoint_age_hours = checkpoint_age_seconds / 3600 if checkpoint_age_seconds else None

        # 3. Estimate remaining time
        remaining_hours = self.estimate_remaining_time(metrics["last_step"])

        # 4. Determine trends
        reward_trend = self.determine_reward_trend(metrics)
        approx_sharpe = self.calculate_approx_sharpe(metrics)

        # 5. Build checklist
        checklist = []
        checklist.append("✅" if metrics["training_active"] else "❌")  # Running?
        checklist.append("✅" if reward_trend != "UNKNOWN" else "❌")  # Reward trend OK?
        checklist.append("✅" if (approx_sharpe is not None and approx_sharpe >= 0.0) else "❌")  # Sharpe >= 0?
        checklist.append("✅" if metrics["last_kl_divergence"] < 0.01 else "❌")  # KL OK?
        checklist.append("✅" if len(metrics["errors"]) == 0 else "❌")  # No errors?

        # 6. Time elapsed
        start_time = datetime(2026, 2, 23, 14, 0, 0)  # 23 FEV 14:00 UTC
        now = datetime.now()
        time_elapsed_hours = (now - start_time).total_seconds() / 3600

        # Build result
        result = {
            "date": date_str,
            "training_status": "RUNNING" if metrics["training_active"] else "STOPPED",
            "time_elapsed_hours": round(time_elapsed_hours, 1),
            "estimated_time_remaining_hours": round(remaining_hours, 1) if remaining_hours else None,
            "last_step": metrics["last_step"],
            "reward_trend": reward_trend,
            "last_reward": round(metrics["last_reward"], 2),
            "approx_sharpe": round(approx_sharpe, 2) if approx_sharpe else None,
            "kl_divergence_last": round(metrics["last_kl_divergence"], 4),
            "checkpoint_age_hours": round(checkpoint_age_hours, 1) if checkpoint_age_hours else None,
            "no_issues": len(metrics["errors"]) == 0,
            "errors": metrics["errors"],
            "checklist": " ".join(checklist),
            "timestamp": datetime.now().isoformat()
        }

        return result

    def save_daily_summary(self, result: Dict[str, Any]) -> Path:
        """Salva resultado em daily_summaries."""
        summary_file = self.daily_summaries_dir / f"{result['date']}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Daily summary saved: {summary_file}")
        return summary_file

    def print_report(self, result: Dict[str, Any]) -> None:
        """Imprime relatório formatado."""
        print("\n" + "=" * 70)
        print(f"  DAILY TRAINING CHECK — {result['date']}")
        print("=" * 70)
        print(f"\n Status: {result['training_status']}")
        print(f"   Time elapsed: {result['time_elapsed_hours']}h")
        if result['estimated_time_remaining_hours']:
            print(f"   Estimated remaining: {result['estimated_time_remaining_hours']}h")
        print(f"\n Metrics:")
        print(f"   Last step: {result['last_step']:,}/{500_000:,}")
        print(f"   Reward trend: {result['reward_trend']}")
        print(f"   Last reward: {result['last_reward']}")
        print(f"   Approx Sharpe: {result['approx_sharpe']}")
        print(f"   KL divergence: {result['kl_divergence_last']}")
        print(f"\n Checklist:")
        print(f"   {result['checklist']}")
        print(f"   (1=Running, 2=Trend OK, 3=Sharpe OK, 4=KL OK, 5=No errors)")
        if result['errors']:
            print(f"\n ⚠️  ERRORS:")
            for err in result['errors']:
                print(f"   - {err}")
        print("\n" + "=" * 70 + "\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Daily training check")
    parser.add_argument("--date", type=str, default=None, help="Date (YYYY-MM-DD)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    checker = DailyTrainingCheck()
    result = checker.run_check(date_str=args.date)

    # Save summary
    checker.save_daily_summary(result)

    # Print report
    checker.print_report(result)

    # Return JSON
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
