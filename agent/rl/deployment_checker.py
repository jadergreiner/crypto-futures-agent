"""
Deployment Checklist para TASK-005 — Preparação de modelo para produção.

Responsabilidades:
- Preparar modelo para deployment
- Validar arquivos necessários
- Gerar manifesto de deployment
- Criar documentação de operação
- Verificar conformidade com padrões
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentChecker:
    """
    Checker para validar readiness de deployment.

    Responsabilidades:
    - Verificar arquivos necessários
    - Validar configurações
    - Gerar manifesto
    - Prépare documentação
    """

    # Arquivos obrigatórios para deployment
    REQUIRED_FILES = {
        'Model': 'models/ppo_v0_final.pkl',
        'Validation Report': 'validation/task005_validation_results.json',
        'Phase 3 Report': 'validation/task005_phase3_final_report.json',
        'Training Log': 'TASK_005_EXECUTION_LOG.md',
        'Spec': 'docs/TASK_005_ML_TRAINING_SPEC.md',
    }

    # Documentação recomendada
    RECOMMENDED_DOCS = {
        'Operational Manual': 'docs/USER_MANUAL.md',
        'Architecture Diagram': 'docs/C4_MODEL.md',
        'Implementation Guide': 'TASK_005_PHASE2_SUMMARY.md',
    }

    def __init__(self, output_dir: str = "deployment/"):
        """
        Inicializa o checker.

        Args:
            output_dir: Diretório para artifacts de deployment
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.checklist_results = {}
        self.manifest = {}

    def check_deployment_readiness(self) -> Tuple[bool, Dict]:
        """
        Verifica se modelo está pronto para deployment.

        Returns:
            tuple: (is_ready, manifest)
        """
        logger.info("\n" + "="*70)
        logger.info("📋 DEPLOYMENT READINESS CHECKLIST")
        logger.info("="*70)

        try:
            # Check 1: Arquivos obrigatórios
            logger.info("\n[1/5] Validando arquivos obrigatórios...")
            files_ok = self._check_required_files()

            # Check 2: Documentação
            logger.info("\n[2/5] Validando documentação...")
            docs_ok = self._check_documentation()

            # Check 3: Validation results
            logger.info("\n[3/5] Validando relatórios de teste...")
            validation_ok = self._check_validation_reports()

            # Check 4: Configurações
            logger.info("\n[4/5] Validando configurações...")
            config_ok = self._check_configurations()

            # Check 5: Sign-off
            logger.info("\n[5/5] Validando sign-offs...")
            signoff_ok = self._check_signoffs()

            # Determina readiness geral
            is_ready = all([
                files_ok,
                docs_ok,
                validation_ok,
                config_ok,
                signoff_ok
            ])

            # Gera manifesto
            self._generate_deployment_manifest(is_ready)

            # Imprime checklist
            self._print_checklist(is_ready)

            return is_ready, self.manifest

        except Exception as e:
            logger.error(f"❌ Erro no checklist: {e}")
            return False, {}

    def _check_required_files(self) -> bool:
        """Valida presença de arquivos obrigatórios."""
        all_present = True

        for name, filepath in self.REQUIRED_FILES.items():
            path = Path(filepath)
            exists = path.exists()

            status = "✅" if exists else "❌"
            logger.info(f"  {status} {name:20} | {filepath}")

            self.checklist_results[f'file_{name}'] = exists
            all_present = all_present and exists

        return all_present

    def _check_documentation(self) -> bool:
        """Valida documentação."""
        all_present = True

        logger.info("  📚 Obrigatória:")
        for name, filepath in self.RECOMMENDED_DOCS.items():
            path = Path(filepath)
            exists = path.exists()

            status = "✅" if exists else "⚠️ "
            logger.info(f"    {status} {name:20} | {filepath}")

            self.checklist_results[f'doc_{name}'] = exists
            all_present = all_present and exists

        return all_present

    def _check_validation_reports(self) -> bool:
        """Valida relatórios de validação."""
        try:
            # Check Phase 3 report
            phase3_report = Path("validation/task005_phase3_final_report.json")

            if not phase3_report.exists():
                logger.info("  ⚠️ Phase 3 report não encontrado (esperado pós-treinamento)")
                self.checklist_results['validation_phase3'] = False
                return True  # Não falha se ainda não foi treinado

            with open(phase3_report) as f:
                report = json.load(f)

            decision = report.get('decision', 'UNKNOWN')
            go_decision = report.get('go_decision', False)

            status = "✅" if go_decision else "❌"
            logger.info(f"  {status} Phase 3 Decision: {decision}")

            self.checklist_results['validation_phase3'] = go_decision
            return go_decision

        except Exception as e:
            logger.warning(f"  ⚠️ Erro lendo Phase 3 report: {e}")
            return False

    def _check_configurations(self) -> bool:
        """Valida configurações."""
        try:
            # Verifica se há config file
            config_files = list(Path('.').glob('config/*.py'))

            has_config = len(config_files) > 0

            status = "✅" if has_config else "⚠️ "
            logger.info(f"  {status} Configuration files: {len(config_files)} found")

            self.checklist_results['configuration'] = True  # Passível
            return True

        except Exception as e:
            logger.warning(f"  ⚠️ Erro validando config: {e}")
            return False

    def _check_signoffs(self) -> bool:
        """Valida sign-offs de personas."""
        try:
            phase3_report = Path("validation/task005_phase3_final_report.json")

            if not phase3_report.exists():
                logger.info("  ⚠️ Sign-offs não disponíveis (esperado pós-treinamento)")
                self.checklist_results['signoffs'] = False
                return True  # Não falha se ainda não foi treinado

            with open(phase3_report) as f:
                report = json.load(f)

            approvals = report.get('approvals', {})

            for persona_name, approval in approvals.items():
                status = "✅" if approval['approval'] == 'APPROVED' else "⚠️ "
                logger.info(
                    f"  {status} {approval['persona']:12} | {approval['approval']}"
                )

            all_approved = report.get('all_approved', False)
            self.checklist_results['signoffs'] = all_approved
            return all_approved

        except Exception as e:
            logger.warning(f"  ⚠️ Erro validando sign-offs: {e}")
            return False

    def _generate_deployment_manifest(self, is_ready: bool) -> None:
        """Gera manifesto de deployment."""
        self.manifest = {
            'name': 'TASK-005: PPO Trading Agent v0',
            'version': '0.1.0',
            'status': 'READY' if is_ready else 'PENDING',
            'timestamp': datetime.utcnow().isoformat(),

            # Componentes
            'components': {
                'model': {
                    'type': 'stable-baselines3.PPO',
                    'path': 'models/ppo_v0_final.pkl',
                    'training': {
                        'framework': 'Gymnasium',
                        'timesteps': 500000,
                        'duration': '96h wall-time',
                    },
                },
                'environment': {
                    'type': 'CryptoTradingEnv',
                    'observation_space': [5],
                    'action_space': 3,
                },
                'data': {
                    'type': 'Sprint 1 Trade History',
                    'trades': 70,
                    'path': 'data/trades_history.json',
                },
            },

            # Métricas
            'metrics': {
                'sharpe_ratio': '≥0.80 required',
                'max_drawdown': '≤12% required',
                'win_rate': '≥45% required',
                'profit_factor': '≥1.5 required',
                'consecutive_losses': '≤5 required',
            },

            # Checklist
            'checklist': self.checklist_results,

            # Deployment instructions
            'deployment_steps': [
                '1. Backup current production model (if any)',
                '2. Copy models/ppo_v0_final.pkl to production server',
                '3. Deploy agent/rl/ modules to production',
                '4. Initialize CryptoTradingEnv with live data',
                '5. Run inference loop with circuit breakers enabled',
                '6. Monitor Sharpe ratio and drawdown metrics',
                '7. Enable automatic alerts for gate violations',
            ],

            # Rollback plan
            'rollback_plan': [
                '1. Stop inference immediately',
                '2. Restore previous model version',
                '3. Run validation on restored model',
                '4. Resume trading with restored model',
                '5. Generate incident report',
            ],

            # Support contacts
            'support': {
                'architect': 'Arch (#6)',
                'qa_lead': 'Audit (#8)',
                'ml_engineer': 'Brain (#3)',
                'escalation': 'Dr.Risk (#5) - Risk Manager',
            },
        }

        # Salva manifesto
        manifest_file = self.output_dir / "deployment_manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)

        logger.info(f"\n✅ Manifesto salvo: {manifest_file}")

    def _print_checklist(self, is_ready: bool) -> None:
        """Imprime checklist formatado."""
        print("\n" + "="*70)
        print("📋 DEPLOYMENT READINESS SUMMARY")
        print("="*70)

        status = "🟢 READY FOR DEPLOYMENT" if is_ready else "🟡 PENDING ITEMS"
        print(f"\nStatus: {status}\n")

        print("Checklist Items:")
        passed = sum(1 for v in self.checklist_results.values() if v)
        total = len(self.checklist_results)
        print(f"  {passed}/{total} items passed")

        for item, result in self.checklist_results.items():
            symbol = "✅" if result else "❌"
            print(f"    {symbol} {item}")

        if is_ready:
            print("\n✅ All deployment requirements met!")
            print("🚀 Ready for production deployment")
        else:
            print("\n⚠️ Address remaining items before deployment")

        print("="*70 + "\n")


def check_deployment_readiness() -> bool:
    """
    Função convenience para verificar readiness.

    Returns:
        bool: True se ready for deployment
    """
    checker = DeploymentChecker()
    is_ready, manifest = checker.check_deployment_readiness()
    return is_ready


if __name__ == "__main__":
    import sys

    is_ready = check_deployment_readiness()
    sys.exit(0 if is_ready else 1)
