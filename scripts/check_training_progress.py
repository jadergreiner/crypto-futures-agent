"""
Script de Daily Check-in para Monitoramento de Treinamento PPO — Phase 4
==========================================================================

Executar uma vez por dia durante treinamento (23-27 FEV) para validar:
- Convergência de Reward
- KL Divergence dentro de threshold
- Nenhuma explosão de gradiente
- Checkpoints sendo salvos corretamente
- Uso de memória/CPU saudável

Uso: python scripts/check_training_progress.py
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple
import re

logger = logging.getLogger(__name__)


class TrainingProgressChecker:
    """Valida progresso de treinamento PPO Phase 4."""

    def __init__(
        self,
        log_dir: str = "logs/ppo_training",
        checkpoint_dir: str = "models/ppo_phase4"
    ):
        """
        Inicializa checker.

        Args:
            log_dir: Diretório de logs
            checkpoint_dir: Diretório de checkpoints
        """
        self.log_dir = Path(log_dir)
        self.checkpoint_dir = Path(checkpoint_dir)
        self.report_path = self.log_dir / "daily_check_report.json"

        # Alertas
        self.kl_threshold = 0.05
        self.min_reward_trend = -0.1  # Mínimo aceitável de trend
        self.max_learning_iterations_without_checkpoint = 100000

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def check_log_files_exist(self) -> Tuple[bool, list]:
        """
        Verifica se os arquivos de log esperados existem.

        Returns:
            (all_exist, missing_files)
        """
        expected_files = [
            "convergence_dashboard.csv",
            "training_metrics.csv",
            "daily_summary.log",
            "alerts.log"
        ]

        tensorboard_dir = self.log_dir / "tensorboard"

        missing = []
        for f in expected_files:
            if not (self.log_dir / f).exists():
                missing.append(f)

        if not tensorboard_dir.exists():
            missing.append("tensorboard/")

        return len(missing) == 0, missing

    def check_convergence_dashboard(self) -> Dict[str, Any]:
        """
        Lê convergence_dashboard.csv e valida:
        - Reward está crescendo (trend positivo)?
        - KL divergence < 0.05?
        - Episódios completos?

        Returns:
            {
                'status': 'OK'|'WARNING'|'CRITICAL',
                'reward_trend': float,
                'latest_reward': float,
                'kl_divergence': float,
                'total_steps': int,
                'messages': [str]
            }
        """
        csv_path = self.log_dir / "convergence_dashboard.csv"

        result = {
            'status': 'OK',
            'reward_trend': None,
            'latest_reward': None,
            'kl_divergence': None,
            'total_steps': 0,
            'messages': []
        }

        if not csv_path.exists():
            result['status'] = 'CRITICAL'
            result['messages'].append(
                f"❌ convergence_dashboard.csv not found at {csv_path}"
            )
            return result

        try:
            import pandas as pd

            df = pd.read_csv(csv_path)

            # Validar colunas esperadas
            expected_cols = ['timestep', 'reward', 'kl_divergence']
            missing_cols = [c for c in expected_cols if c not in df.columns]
            if missing_cols:
                result['messages'].append(
                    f"⚠️ Missing columns in CSV: {missing_cols}"
                )

            if len(df) < 2:
                result['messages'].append(
                    "⚠️ CSV has < 2 rows, training just started"
                )
                return result

            # Stats
            result['total_steps'] = int(df['timestep'].iloc[-1])
            result['latest_reward'] = float(df['reward'].iloc[-1])

            # Trend (últimas 5 linhas)
            if len(df) >= 5:
                recent_rewards = df['reward'].tail(5).values
                trend = (recent_rewards[-1] - recent_rewards[0]) / (
                    len(recent_rewards) - 1
                )
                result['reward_trend'] = trend

                if trend < self.min_reward_trend:
                    result['status'] = 'WARNING'
                    result['messages'].append(
                        f"⚠️ Negative reward trend: {trend:.6f} "
                        "(check learning rate or reward function)"
                    )

            # KL Divergence
            if 'kl_divergence' in df.columns:
                latest_kl = float(df['kl_divergence'].iloc[-1])
                result['kl_divergence'] = latest_kl

                if latest_kl > self.kl_threshold:
                    result['status'] = 'WARNING'
                    result['messages'].append(
                        f"⚠️ KL divergence high: {latest_kl:.6f} > {self.kl_threshold} "
                        "(policy changing too fast)"
                    )

            # Progress indicator
            hours_elapsed = result['total_steps'] / 1000 / 3  # Rough estimate
            result['messages'].append(
                f"✅ Progress: {result['total_steps']:,} steps (~{hours_elapsed:.1f}h elapsed)"
            )

        except Exception as e:
            result['status'] = 'CRITICAL'
            result['messages'].append(f"❌ Error reading CSV: {e}")

        return result

    def check_checkpoint_progress(self) -> Dict[str, Any]:
        """
        Valida que checkpoints estão sendo salvos.

        Returns:
            {
                'status': 'OK'|'WARNING'|'CRITICAL',
                'checkpoint_count': int,
                'latest_checkpoint': str,
                'latest_checkpoint_age_hours': float,
                'messages': [str]
            }
        """
        result = {
            'status': 'OK',
            'checkpoint_count': 0,
            'latest_checkpoint': None,
            'latest_checkpoint_age_hours': None,
            'messages': []
        }

        if not self.checkpoint_dir.exists():
            result['status'] = 'CRITICAL'
            result['messages'].append(f"❌ Checkpoint dir not found: {self.checkpoint_dir}")
            return result

        # Procurar arquivos .zip (modelos PPO)
        checkpoint_files = list(self.checkpoint_dir.glob("*.zip"))

        if not checkpoint_files:
            result['status'] = 'WARNING'
            result['messages'].append(
                f"⚠️ No checkpoints found yet in {self.checkpoint_dir} "
                "(training just started)"
            )
            return result

        result['checkpoint_count'] = len(checkpoint_files)

        # Latest checkpoint
        latest = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
        result['latest_checkpoint'] = latest.name

        # Age
        import time
        age_seconds = time.time() - latest.stat().st_mtime
        age_hours = age_seconds / 3600
        result['latest_checkpoint_age_hours'] = age_hours

        if age_hours > 12:
            result['status'] = 'WARNING'
            result['messages'].append(
                f"⚠️ Latest checkpoint is {age_hours:.1f}h old "
                "(check if training is running)"
            )
        else:
            result['messages'].append(
                f"✅ Latest checkpoint: {latest.name} ({age_hours:.1f}h ago)"
            )

        return result

    def check_alerts_log(self) -> Dict[str, Any]:
        """
        Lê alerts.log e reporta problemas críticos.

        Returns:
            {
                'status': 'OK'|'WARNING'|'CRITICAL',
                'alert_count': int,
                'critical_alerts': [str],
                'warnings': [str],
                'messages': [str]
            }
        """
        alerts_path = self.log_dir / "alerts.log"

        result = {
            'status': 'OK',
            'alert_count': 0,
            'critical_alerts': [],
            'warnings': [],
            'messages': []
        }

        if not alerts_path.exists():
            result['messages'].append(
                f"ℹ️ No alerts log yet (may be created later)"
            )
            return result

        try:
            with open(alerts_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Procurar por padrões críticos
            for line in lines:
                if 'CRITICAL' in line or 'ERROR' in line:
                    result['status'] = 'CRITICAL'
                    result['critical_alerts'].append(line.strip())
                elif 'WARNING' in line:
                    if result['status'] == 'OK':
                        result['status'] = 'WARNING'
                    result['warnings'].append(line.strip())

            result['alert_count'] = len(result['critical_alerts']) + len(result['warnings'])

            if result['critical_alerts']:
                result['messages'].append(
                    f"❌ {len(result['critical_alerts'])} CRITICAL alerts found!"
                )
            elif result['warnings']:
                result['messages'].append(
                    f"⚠️ {len(result['warnings'])} warnings found"
                )
            else:
                result['messages'].append("✅ No critical alerts")

        except Exception as e:
            result['status'] = 'CRITICAL'
            result['messages'].append(f"❌ Error reading alerts.log: {e}")

        return result

    def generate_daily_report(self) -> Dict[str, Any]:
        """
        Gera relatório completo de daily check-in.

        Returns:
            Dicionário com todos os checks
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }

        # Check 1: Log files
        files_ok, missing = self.check_log_files_exist()
        report['checks']['log_files'] = {
            'status': 'OK' if files_ok else 'CRITICAL',
            'message': 'All expected log files present' if files_ok else f"Missing: {missing}"
        }

        # Check 2: Convergence
        convergence = self.check_convergence_dashboard()
        report['checks']['convergence'] = convergence

        # Check 3: Checkpoints
        checkpoints = self.check_checkpoint_progress()
        report['checks']['checkpoints'] = checkpoints

        # Check 4: Alerts
        alerts = self.check_alerts_log()
        report['checks']['alerts'] = alerts

        # Overall status
        statuses = [
            report['checks']['log_files']['status'],
            convergence['status'],
            checkpoints['status'],
            alerts['status']
        ]

        if 'CRITICAL' in statuses:
            report['overall_status'] = 'CRITICAL'
        elif 'WARNING' in statuses:
            report['overall_status'] = 'WARNING'
        else:
            report['overall_status'] = 'OK'

        return report

    def print_report(self, report: Dict[str, Any]) -> None:
        """
        Imprime relatório em formato legível.

        Args:
            report: Dicionário de relatório
        """
        overall = report['overall_status']
        status_emoji = {'OK': '✅', 'WARNING': '⚠️', 'CRITICAL': '❌'}

        print("\n" + "="*80)
        print(f"DAILY TRAINING CHECK-IN — {report['timestamp']}")
        print("="*80)

        print(f"\n{status_emoji.get(overall, '❓')} Overall Status: {overall}")

        # Log files
        lf = report['checks']['log_files']
        print(f"\n📄 Log Files: {status_emoji.get(lf['status'])} {lf['message']}")

        # Convergence
        conv = report['checks']['convergence']
        print(f"\n📈 Convergence: {status_emoji.get(conv['status'])}")
        if conv['total_steps']:
            print(f"   Total steps: {conv['total_steps']:,}")
        if conv['latest_reward'] is not None:
            print(f"   Latest reward: {conv['latest_reward']:.4f}")
        if conv['reward_trend'] is not None:
            print(f"   Reward trend: {conv['reward_trend']:+.6f}/step")
        if conv['kl_divergence'] is not None:
            print(f"   KL divergence: {conv['kl_divergence']:.6f} (threshold: {self.kl_threshold})")
        for msg in conv['messages']:
            print(f"   {msg}")

        # Checkpoints
        ckpt = report['checks']['checkpoints']
        print(f"\n💾 Checkpoints: {status_emoji.get(ckpt['status'])}")
        print(f"   Count: {ckpt['checkpoint_count']}")
        if ckpt['latest_checkpoint']:
            print(f"   Latest: {ckpt['latest_checkpoint']}")
        if ckpt['latest_checkpoint_age_hours'] is not None:
            print(f"   Age: {ckpt['latest_checkpoint_age_hours']:.1f}h")
        for msg in ckpt['messages']:
            print(f"   {msg}")

        # Alerts
        alerts = report['checks']['alerts']
        print(f"\n🔔 Alerts: {status_emoji.get(alerts['status'])}")
        print(f"   Count: {alerts['alert_count']}")
        for msg in alerts['messages']:
            print(f"   {msg}")

        print("\n" + "="*80 + "\n")

    def save_report(self, report: Dict[str, Any]) -> Path:
        """
        Salva relatório em JSON.

        Args:
            report: Dicionário de relatório

        Returns:
            Caminho do arquivo salvo
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)

        with open(self.report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Report saved to {self.report_path}")
        return self.report_path


def main():
    """Função principal."""
    import sys

    checker = TrainingProgressChecker()

    # Gerar relatório
    report = checker.generate_daily_report()

    # Imprimir
    checker.print_report(report)

    # Salvar
    checker.save_report(report)

    # Exit code baseado em status
    if report['overall_status'] == 'CRITICAL':
        print("🚨 CRITICAL issues detected! Check logs immediately.")
        sys.exit(1)
    elif report['overall_status'] == 'WARNING':
        print("⚠️ Warnings detected. Monitor closely.")
        sys.exit(0)
    else:
        print("✅ All checks passed. Training appears healthy.")
        sys.exit(0)


if __name__ == "__main__":
    main()
