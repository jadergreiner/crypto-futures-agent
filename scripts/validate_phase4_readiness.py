"""
Validação Final de Readiness para Phase 4 — 21 FEV 2026
========================================================

Gera relatório JSON com status completo de readiness para launch.
"""

import json
from pathlib import Path
from datetime import datetime


def check_files_exist():
    """Valida que todos os arquivos críticos existem."""
    critical_files = {
        'config/ppo_config.py': 'PPO Config',
        'scripts/revalidate_model.py': 'Revalidation Script',
        'scripts/check_training_progress.py': 'Training Progress Checker',
        'scripts/ppo_training_dashboard.py': 'Training Dashboard',
        'GUIA_PPO_TRAINING_PHASE4.md': 'Training Guide',
        'ML_OPERATIONS_CHECKLIST.md': 'Operations Checklist',
        'agent/reward.py': 'Reward Function',
        'agent/environment.py': 'RL Environment',
        'tests/test_ppo_config_integration.py': 'PPO Config Tests',
        'tests/test_reward_revalidation.py': 'Reward Function Tests',
        'tests/test_backtest_integration_final.py': 'Backtest Integration Tests',
    }

    files_status = {}
    all_present = True

    for filepath, description in critical_files.items():
        exists = Path(filepath).exists()
        files_status[filepath] = {
            'description': description,
            'exists': exists,
            'status': '✅' if exists else '❌'
        }
        if not exists:
            all_present = False

    return all_present, files_status


def check_directories_exist():
    """Valida que diretórios necessários existem."""
    required_dirs = {
        'logs/ppo_training': 'Training Logs',
        'checkpoints': 'Checkpoints Root',
        'models': 'Models Root',
        'reports/revalidation': 'Revalidation Reports',
        'tests': 'Test Suite',
    }

    dirs_status = {}
    all_ready = True

    for dirpath, description in required_dirs.items():
        exists = Path(dirpath).exists()
        dirs_status[dirpath] = {
            'description': description,
            'exists': exists,
            'status': '✅' if exists else '❌ (will be created during training)'
        }
        if dirpath in ['logs/ppo_training', 'tests'] and not exists:
            all_ready = False

    return all_ready, dirs_status


def check_imports():
    """Valida que imports críticos funcionam."""
    imports_to_check = {
        'config.ppo_config.PPOConfig': 'PPO Config Load',
        'agent.reward.RewardCalculator': 'Reward Calculator',
        'agent.environment.CryptoFuturesEnv': 'Environment',
        'agent.trainer.Trainer': 'Trainer (optional)',
        'scripts.check_training_progress.TrainingProgressChecker': 'Progress Checker',
    }

    imports_status = {}

    for import_path, description in imports_to_check.items():
        try:
            module_path, class_name = import_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            imports_status[import_path] = {
                'description': description,
                'status': '✅',
                'error': None
            }
        except Exception as e:
            imports_status[import_path] = {
                'description': description,
                'status': '❌' if 'Trainer' not in import_path else '⚠️ (optional)',
                'error': str(e)[:100]
            }

    return imports_status


def validate_ppo_config():
    """Valida PPO Config específicamente."""
    try:
        from config.ppo_config import PPOConfig, get_ppo_config

        config = PPOConfig()

        expected_values = {
            'learning_rate': 3e-4,
            'batch_size': 64,
            'n_steps': 2048,
            'n_epochs': 10,
            'gamma': 0.99,
            'gae_lambda': 0.95,
            'ent_coef': 0.001,
            'clip_range': 0.2,
            'vf_coef': 0.5,
            'max_grad_norm': 0.5,
            'total_timesteps': 500_000,
        }

        validation_results = {}
        all_correct = True

        for param_name, expected_value in expected_values.items():
            actual_value = getattr(config, param_name)
            is_correct = actual_value == expected_value
            validation_results[param_name] = {
                'expected': expected_value,
                'actual': actual_value,
                'correct': is_correct,
                'status': '✅' if is_correct else '❌'
            }
            if not is_correct:
                all_correct = False

        # Checklist adicional
        additional_checks = {
            'norm_obs': config.norm_obs == True,
            'norm_reward': config.norm_reward == True,
            'tensorboard_enabled': config.tensorboard_enabled == True,
            'enable_convergence_monitoring': config.enable_convergence_monitoring == True,
            'reward_components_present': config.reward_components is not None,
        }

        for check_name, is_passed in additional_checks.items():
            validation_results[check_name] = {
                'status': '✅' if is_passed else '❌',
                'passed': is_passed
            }
            if not is_passed:
                all_correct = False

        return all_correct, validation_results

    except Exception as e:
        return False, {'error': str(e)}


def validate_reward_function():
    """Valida Reward Function."""
    try:
        from agent.reward import RewardCalculator, REWARD_CLIP

        calculator = RewardCalculator()

        expected_components = ['r_pnl', 'r_hold_bonus', 'r_invalid_action', 'r_out_of_market']
        all_present = all(c in calculator.weights for c in expected_components)

        return all_present, {
            'components': list(calculator.weights.keys()),
            'reward_clip': REWARD_CLIP,
            'weights_valid': all(w > 0 for w in calculator.weights.values()),
            'status': '✅' if all_present else '❌'
        }

    except Exception as e:
        return False, {'error': str(e)}


def validate_revalidation_gates():
    """Valida que 6 gates estão presentes no revalidate_model.py."""
    try:
        # Ler arquivo e procurar por gates
        revalidate_path = Path('scripts/revalidate_model.py')
        if not revalidate_path.exists():
            return False, {'error': 'revalidate_model.py not found'}

        with open(revalidate_path, 'r') as f:
            content = f.read()

        gates = ['SHARPE_MIN', 'MAX_DD_MAX', 'WIN_RATE_MIN', 'PROFIT_FACTOR_MIN',
                'CONSECUTIVE_LOSSES_MAX', 'CALMAR_MIN']

        gates_found = {}
        all_found = True

        for gate in gates:
            found = gate in content
            gates_found[gate] = {'found': found, 'status': '✅' if found else '❌'}
            if not found:
                all_found = False

        return all_found, gates_found

    except Exception as e:
        return False, {'error': str(e)}


def main():
    """Executa validação completa."""
    print("\n" + "="*80)
    print("PHASE 4 READINESS VALIDATION — 21 FEV 2026")
    print("="*80 + "\n")

    report = {
        'timestamp': datetime.now().isoformat(),
        'validation_checklist': {}
    }

    # 1. Files Check
    print("1️⃣ Checking Critical Files...")
    files_ok, files_status = check_files_exist()
    report['validation_checklist']['files_present'] = {
        'passed': files_ok,
        'status': '✅' if files_ok else '❌',
        'files': files_status
    }
    print(f"   Status: {'✅ ALL PRESENT' if files_ok else '❌ SOME MISSING'}\n")

    # 2. Directories Check
    print("2️⃣ Checking Critical Directories...")
    dirs_ok, dirs_status = check_directories_exist()
    report['validation_checklist']['directories_ready'] = {
        'passed': dirs_ok,
        'status': '✅' if dirs_ok else '❌',
        'directories': dirs_status
    }
    print(f"   Status: {'✅ ALL READY' if dirs_ok else '⚠️ SOME MISSING (will auto-create)'}\n")

    # 3. Imports Check
    print("3️⃣ Checking Critical Imports...")
    imports_status = check_imports()
    report['validation_checklist']['imports_working'] = imports_status
    imports_ok = all(v.get('status') == '✅' for v in imports_status.values())
    print(f"   Status: {'✅ ALL WORKING' if imports_ok else '⚠️ SOME ISSUES'}\n")

    # 4. PPO Config Validation
    print("4️⃣ Validating PPO Config...")
    ppo_ok, ppo_validation = validate_ppo_config()
    report['validation_checklist']['ppo_config_valid'] = {
        'passed': ppo_ok,
        'status': '✅' if ppo_ok else '❌',
        'details': ppo_validation
    }
    print(f"   Status: {'✅ ALL HYPERPARAMETERS CORRECT' if ppo_ok else '❌ SOME ISSUES'}\n")

    # 5. Reward Function Validation
    print("5️⃣ Validating Reward Function...")
    reward_ok, reward_validation = validate_reward_function()
    report['validation_checklist']['reward_function_valid'] = {
        'passed': reward_ok,
        'status': '✅' if reward_ok else '❌',
        'details': reward_validation
    }
    print(f"   Status: {'✅ 4 COMPONENTS PRESENT' if reward_ok else '❌ ISSUES'}\n")

    # 6. Revalidation Gates
    print("6️⃣ Validating Revalidation Gates...")
    gates_ok, gates_validation = validate_revalidation_gates()
    report['validation_checklist']['revalidation_gates'] = {
        'passed': gates_ok,
        'status': '✅' if gates_ok else '❌',
        'gates': gates_validation
    }
    print(f"   Status: {'✅ ALL 6 GATES PRESENT' if gates_ok else '❌ GATES MISSING'}\n")

    # Overall Status
    all_critical_ok = files_ok and ppo_ok and reward_ok and gates_ok

    print("="*80)
    if all_critical_ok:
        print("🎉 OVERALL STATUS: ✅ READY FOR PHASE 4 LAUNCH (23 FEV)")
    else:
        print("⚠️ OVERALL STATUS: ❌ BLOCKERS DETECTED")
    print("="*80 + "\n")

    # Save report
    report_path = Path('reports/phase4_readiness_validation.json')
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Report saved to: {report_path}\n")

    # Print summary
    print(f"Overall Readiness: {'✅✅✅✅✅✅' if all_critical_ok else '⚠️⚠️⚠️'}")
    print(f"Files Ready: {'✅' if files_ok else '❌'}")
    print(f"PPO Config Valid: {'✅' if ppo_ok else '❌'}")
    print(f"Reward Function Valid: {'✅' if reward_ok else '❌'}")
    print(f"Revalidation Gates: {'✅' if gates_ok else '❌'}")
    print()

    return all_critical_ok


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
