"""
Phase 3: Validação & Salvamento do Modelo — Orquestração Final de TASK-005.

Responsabilidades:
- Executar backtest final com modelo treinado
- Validar contra 5 critérios de sucesso
- Gerar relatório de sign-off com 4-persona approval
- Preparar modelo para deployment em produção
- Registrar decisão GO/NO-GO final

Módulos:
    json: Salvamento de resultados
    pathlib: Manipulação de caminhos
    datetime: Rastreamento de tempo
    logging: Logging estruturado
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List

from agent.rl.training_env import CryptoTradingEnv
from agent.rl.data_loader import TradeHistoryLoader
from agent.rl.final_validation import Task005FinalValidator


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class Phase3Executor:
    """
    Executor de Phase 3: Validação final e sign-off de TASK-005.
    
    Timeline:
    - Pós-treinamento (~4 horas após fim de Phase 2)
    - Validação backtest completa
    - 4-persona approval simulation
    - GO/NO-GO determination
    - Model serialization for production
    """
    
    # 4-persona approval signatures
    PERSONAS = {
        'Arch': '#6',          # Arquitetura
        'Audit': '#8',         # QA & Auditoria
        'Quality': '#12',      # Testes & Qualidade
        'Brain': '#3',         # ML/IA
    }
    
    def __init__(
        self,
        model_path: str = "models/ppo_v0_final.pkl",
        trades_filepath: str = "data/trades_history.json",
        output_dir: str = "validation/",
    ):
        """
        Inicializa Phase 3 executor.
        
        Args:
            model_path: Caminho do modelo treinado
            trades_filepath: Caminho do histórico de trades
            output_dir: Diretório para resultados Phase 3
        """
        self.model_path = model_path
        self.trades_filepath = trades_filepath
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.validator = None
        self.validation_results = {}
        self.phase3_report = {}
        self.approvals = {}
    
    def execute(self) -> Tuple[bool, Dict]:
        """
        Executa Phase 3 completo.
        
        Returns:
            tuple: (is_valid, report_dict)
        """
        logger.info("\n" + "="*70)
        logger.info("🚀 TASK-005 PHASE 3: VALIDAÇÃO FINAL & SIGN-OFF")
        logger.info("="*70)
        
        try:
            # Step 1: Validação backtest
            logger.info("\n[1/4] Executando backtest final...")
            if not self._run_validation():
                return False, {}
            
            # Step 2: Compilación de métricas
            logger.info("\n[2/4] Compilando métricas finais...")
            if not self._compile_metrics():
                return False, {}
            
            # Step 3: 4-persona approval
            logger.info("\n[3/4] Simulando aprovações 4-persona...")
            if not self._simulate_approvals():
                return False, {}
            
            # Step 4: Relatório final & decision
            logger.info("\n[4/4] Gerando relatório final...")
            final_decision = self._generate_final_report()
            
            # Salva Phase 3 report
            self._save_phase3_report(final_decision)
            
            logger.info("\n" + "="*70)
            logger.info("✅ PHASE 3 COMPLETE")
            logger.info("="*70)
            
            return final_decision['go_decision'], self.phase3_report
        
        except Exception as e:
            logger.error(f"\n❌ Erro em Phase 3: {e}")
            import traceback
            traceback.print_exc()
            return False, {}
    
    def _run_validation(self) -> bool:
        """Executa validator final."""
        try:
            self.validator = Task005FinalValidator(
                model_path=self.model_path,
                trades_filepath=self.trades_filepath,
                output_dir=str(self.output_dir),
            )
            
            is_valid, results = self.validator.validate()
            self.validation_results = results
            
            logger.info(f"✅ Validação completa: {'PASS' if is_valid else 'FAIL'}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Erro na validação: {e}")
            return False
    
    def _compile_metrics(self) -> bool:
        """Compila e standardiza métricas finais."""
        try:
            metrics = self.validation_results.get('metrics', {})
            criteria = self.validation_results.get('criteria_check', {})
            
            compiled = {
                'timestamp': datetime.utcnow().isoformat(),
                'model_path': str(self.model_path),
                'backtest_trades': self.validation_results.get('backtest_trades_count', 0),
                
                # Métricas calculadas
                'metrics': {
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                    'win_rate': metrics.get('win_rate', 0),
                    'max_drawdown': metrics.get('max_drawdown', 0),
                    'profit_factor': metrics.get('profit_factor', 0),
                    'consecutive_losses': metrics.get('consecutive_losses', 0),
                    'total_return': metrics.get('total_return', 0),
                },
                
                # Validação de critérios
                'criteria_validation': criteria,
                
                # Resumo de pass/fail
                'all_criteria_passed': all(
                    c['passed'] for c in criteria.values()
                ),
            }
            
            self.phase3_report['metrics_compiled'] = compiled
            return True
        
        except Exception as e:
            logger.error(f"❌ Erro compilando métricas: {e}")
            return False
    
    def _simulate_approvals(self) -> bool:
        """
        Simula aprovações 4-persona.
        
        Em produção real, seria manual. Aqui são automáticas baseadas
        em critérios técnicos.
        """
        try:
            criteria = self.phase3_report.get(
                'metrics_compiled', {}
            ).get('criteria_validation', {})
            
            # Arch approval: Qualidade de código + arquitetura
            arch_check = all(
                criteria.get(k, {}).get('passed', False)
                for k in ['sharpe_ratio', 'profit_factor']
            )
            
            # Audit approval: Conformidade + auditoria
            audit_check = all(
                criteria.get(k, {}).get('passed', False)
                for k in ['max_drawdown', 'consecutive_losses']
            )
            
            # Quality approval: Testes + validação
            quality_check = criteria.get('win_rate', {}).get('passed', False)
            
            # Brain approval: ML metrics + Sharpe target
            brain_check = (
                criteria.get('sharpe_ratio', {}).get('passed', False) and
                self.phase3_report.get('metrics_compiled', {}).get(
                    'metrics', {}
                ).get('sharpe_ratio', 0) >= 0.8
            )
            
            self.approvals = {
                'Arch': {
                    'persona': 'Arch (#6)',
                    'approval': 'APPROVED' if arch_check else 'CONDITIONAL',
                    'reason': 'Architecture & efficiency metrics OK'
                    if arch_check else 'Review metrics',
                    'timestamp': datetime.utcnow().isoformat(),
                },
                'Audit': {
                    'persona': 'Audit (#8)',
                    'approval': 'APPROVED' if audit_check else 'CONDITIONAL',
                    'reason': 'Risk gate validation passed'
                    if audit_check else 'Review risk gates',
                    'timestamp': datetime.utcnow().isoformat(),
                },
                'Quality': {
                    'persona': 'Quality (#12)',
                    'approval': 'APPROVED' if quality_check else 'CONDITIONAL',
                    'reason': 'Win rate & quality metrics OK'
                    if quality_check else 'Review quality gates',
                    'timestamp': datetime.utcnow().isoformat(),
                },
                'Brain': {
                    'persona': 'Brain (#3)',
                    'approval': 'APPROVED' if brain_check else 'CONDITIONAL',
                    'reason': 'Learning convergence achieved'
                    if brain_check else 'Review learning metrics',
                    'timestamp': datetime.utcnow().isoformat(),
                },
            }
            
            # Log approvals
            for persona_name, approval_data in self.approvals.items():
                status = approval_data['approval']
                logger.info(
                    f"  {approval_data['persona']}: {status} — {approval_data['reason']}"
                )
            
            self.phase3_report['approvals'] = self.approvals
            return True
        
        except Exception as e:
            logger.error(f"❌ Erro nas aprovações: {e}")
            return False
    
    def _generate_final_report(self) -> Dict:
        """
        Gera relatório final com decisão GO/NO-GO.
        
        Returns:
            dict: Report com decisão final
        """
        try:
            metrics = self.phase3_report.get('metrics_compiled', {})
            criteria = metrics.get('criteria_validation', {})
            approvals = self.phase3_report.get('approvals', {})
            
            # Decisão GO/NO-GO
            all_passed = all(c['passed'] for c in criteria.values())
            all_approved = all(
                a['approval'] == 'APPROVED' for a in approvals.values()
            )
            
            final_decision = all_passed and all_approved
            
            report = {
                'phase': 'Phase 3: Validation & Sign-off',
                'timestamp': datetime.utcnow().isoformat(),
                'model_path': str(self.model_path),
                'decision': 'GO' if final_decision else 'NO-GO',
                
                # Métricas finais
                'final_metrics': metrics.get('metrics', {}),
                
                # Validação de critérios (5/5)
                'success_criteria': {
                    'sharpe_ratio': {
                        'target': '≥ 0.80',
                        'actual': metrics.get('metrics', {}).get('sharpe_ratio', 0),
                        'passed': criteria.get('sharpe_ratio', {}).get('passed', False),
                    },
                    'max_drawdown': {
                        'target': '≤ 12%',
                        'actual': f"{metrics.get('metrics', {}).get('max_drawdown', 0)*100:.1f}%",
                        'passed': criteria.get('max_drawdown', {}).get('passed', False),
                    },
                    'win_rate': {
                        'target': '≥ 45%',
                        'actual': f"{metrics.get('metrics', {}).get('win_rate', 0)*100:.1f}%",
                        'passed': criteria.get('win_rate', {}).get('passed', False),
                    },
                    'profit_factor': {
                        'target': '≥ 1.5',
                        'actual': metrics.get('metrics', {}).get('profit_factor', 0),
                        'passed': criteria.get('profit_factor', {}).get('passed', False),
                    },
                    'consecutive_losses': {
                        'target': '≤ 5',
                        'actual': metrics.get('metrics', {}).get('consecutive_losses', 0),
                        'passed': criteria.get('consecutive_losses', {}).get('passed', False),
                    },
                },
                
                # 4-persona approvals
                'approvals': approvals,
                'all_approved': all_approved,
                
                # Summarized decision
                'summary': {
                    'criteria_passed': sum(1 for c in criteria.values() if c['passed']),
                    'criteria_total': len(criteria),
                    'personas_approved': sum(
                        1 for a in approvals.values() if a['approval'] == 'APPROVED'
                    ),
                    'personas_total': len(approvals),
                },
                
                # Final GO/NO-GO
                'go_decision': final_decision,
                
                # Recomendações
                'recommendations': [
                    '✅ Model ready for production deployment'
                    if final_decision
                    else '⚠️ Address failing criteria before production',
                    '✅ All risk gates passed'
                    if metrics.get('metrics', {}).get('max_drawdown', 0) <= 0.12
                    else '⚠️ Review drawdown management',
                    '✅ Sharpe convergence achieved'
                    if metrics.get('metrics', {}).get('sharpe_ratio', 0) >= 0.80
                    else '⚠️ Continue learning or adjust parameters',
                ],
            }
            
            return report
        
        except Exception as e:
            logger.error(f"❌ Erro gerando relatório: {e}")
            return {'go_decision': False}
    
    def _save_phase3_report(self, final_report: Dict) -> None:
        """Salva relatório Phase 3 em JSON."""
        report_file = self.output_dir / "task005_phase3_final_report.json"
        
        with open(report_file, 'w') as f:
            json.dump(final_report, f, indent=2)
        
        logger.info(f"✅ Relatório salvo: {report_file}")
        
        # Imprime relatório formatado
        self._print_final_report(final_report)
    
    def _print_final_report(self, report: Dict) -> None:
        """Imprime relatório final formatado."""
        if not report or 'decision' not in report:
            return
        
        decision = report['decision']
        metrics = report['success_criteria']
        approvals = report['approvals']
        
        print("\n" + "="*70)
        print("📋 TASK-005 FINAL VALIDATION REPORT - PHASE 3")
        print("="*70)
        
        print(f"\n🎯 FINAL DECISION: {decision}")
        print("-" * 70)
        
        print("\n✅ SUCCESS CRITERIA (5/5):")
        for name, criterion in metrics.items():
            status = "✅ PASS" if criterion['passed'] else "❌ FAIL"
            print(
                f"  {status} {name:20} | "
                f"Target: {criterion['target']:8} | "
                f"Actual: {criterion['actual']}"
            )
        
        print("\n👥 4-PERSONA APPROVALS:")
        for persona_name, approval in approvals.items():
            status = "✅" if approval['approval'] == 'APPROVED' else "⚠️ "
            print(
                f"  {status} {approval['persona']:12} | "
                f"{approval['approval']:12} | {approval['reason']}"
            )
        
        print("\n📊 SUMMARY:")
        summary = report['summary']
        print(
            f"  Criteria Passed:   {summary['criteria_passed']}/{summary['criteria_total']}"
        )
        print(
            f"  Personas Approved: {summary['personas_approved']}/{summary['personas_total']}"
        )
        
        print("\n💡 RECOMMENDATIONS:")
        for rec in report['recommendations']:
            print(f"  {rec}")
        
        print("\n" + "="*70)
        if decision == 'GO':
            print("✅ GO-LIVE APPROVED — Ready for production deployment!")
        else:
            print("❌ NO-GO — Address issues before production")
        print("="*70 + "\n")


def run_phase3_final_validation() -> bool:
    """
    Função principal para executar Phase 3.
    
    Returns:
        bool: True se GO-LIVE approved
    """
    logger.info("🚀 Iniciando TASK-005 PHASE 3: Validação Final & Sign-off")
    
    executor = Phase3Executor()
    is_valid, report = executor.execute()
    
    return is_valid


if __name__ == "__main__":
    import sys
    
    success = run_phase3_final_validation()
    sys.exit(0 if success else 1)
