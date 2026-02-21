#!/usr/bin/env python3
"""
PRE-FLIGHT VALIDATION — Verificação Completa de Integração PPO
================================================================

Data: 21 FEV 2026
Objetivo: Validar que toda infraestrutura está pronta para treinamento PPO Phase 4
Status: Check-list de 9 validações críticas

"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict

# Adicionar raiz do projeto ao sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class PreFlightValidator:
    """Validator para PRÉ-FLIGHT CHECK."""
    
    def __init__(self):
        self.results = []
        self.errors = []
        self.warnings = []
        self.start_time = datetime.now()
        
    def check(self, name: str, condition: bool, message: str):
        """Registra resultado de uma validação."""
        status = "✅" if condition else "❌"
        self.results.append((name, condition))
        logger.info(f"{status} {name}: {message}")
        if not condition:
            self.errors.append(f"{name}: {message}")
    
    def run_all_validations(self) -> bool:
        """Executa todas as 9 validações críticas."""
        
        logger.info("="*70)
        logger.info("INICIANDO PRÉ-FLIGHT VALIDATION")
        logger.info("="*70)
        
        # 1. Validar config/ppo_config.py
        logger.info("\n[1/9] Validando config/ppo_config.py...")
        try:
            from config.ppo_config import get_ppo_config, PPOConfig
            config = get_ppo_config('phase4')
            assert config.learning_rate == 3e-4, "learning_rate incorreto"
            assert config.batch_size == 64, "batch_size incorreto"
            assert config.n_steps == 2048, "n_steps incorreto"
            assert config.total_timesteps >= 200000, "total_timesteps < 200k"
            self.check(
                "config.ppo_config",
                True,
                f"✓ Configuração válida (LR={config.learning_rate}, batch={config.batch_size}, steps={config.total_timesteps:,})"
            )
        except Exception as e:
            self.check("config.ppo_config", False, f"Erro ao importar: {e}")
            return False
        
        # 2. Validar agent/trainer.py
        logger.info("\n[2/9] Validando agent/trainer.py...")
        try:
            from agent.trainer import PPOStrategy
            self.check("agent.trainer", True, "✓ PPOStrategy importado com sucesso")
        except Exception as e:
            self.check("agent.trainer", False, f"Erro ao importar: {e}")
            self.warnings.append(f"agent.trainer pode estar com issues: {e}")
        
        # 3. Validar scripts/train_ppo_skeleton.py
        logger.info("\n[3/9] Validando scripts/train_ppo_skeleton.py...")
        try:
            # Verificar que arquivo pode ser lido sem erros de encoding
            with open("scripts/train_ppo_skeleton.py", "r", encoding="utf-8") as f:
                content = f.read()
            assert len(content) > 500, "Arquivo muito pequeno"
            assert "BacktestEnvironment" in content, "BacktestEnvironment não importado"
            assert "ParquetCache" in content, "ParquetCache não importado"
            self.check("scripts.train_ppo_skeleton", True, "✓ Arquivo válido e com imports corretos")
        except Exception as e:
            self.check("scripts.train_ppo_skeleton", False, f"Erro aovalidar: {e}")
            return False
        
        # 4. Validar BacktestEnvironment
        logger.info("\n[4/9] Validando BacktestEnvironment...")
        try:
            from backtest.backtest_environment import BacktestEnvironment
            self.check("BacktestEnvironment", True, "✓ Importado com sucesso")
        except Exception as e:
            self.check("BacktestEnvironment", False, f"Erro ao importar: {e}")
            return False
        
        # 5. Validar ParquetCache
        logger.info("\n[5/9] Validando ParquetCache...")
        try:
            from backtest.data_cache import ParquetCache
            self.check("ParquetCache", True, "✓ Importado com sucesso")
        except Exception as e:
            self.check("ParquetCache", False, f"Erro ao importar: {e}")
            return False
        
        # 6. Validar dados OGNUSDT
        logger.info("\n[6/9] Validando dados OGNUSDT_4h.parquet...")
        try:
            path = Path("backtest/cache/OGNUSDT_4h.parquet")
            assert path.exists(), "Arquivo não encontrado"
            size_mb = path.stat().st_size / (1024*1024)
            assert size_mb > 1, f"Arquivo muito pequeno ({size_mb:.2f}MB)"
            self.check("OGNUSDT_data", True, f"✓ Presente ({size_mb:.2f}MB)")
        except Exception as e:
            self.check("OGNUSDT_data", False, f"Erro: {e}")
            return False
        
        # 7. Validar dados 1000PEPEUSDT
        logger.info("\n[7/9] Validando dados 1000PEPEUSDT_4h.parquet...")
        try:
            path = Path("backtest/cache/1000PEPEUSDT_4h.parquet")
            assert path.exists(), "Arquivo não encontrado"
            size_mb = path.stat().st_size / (1024*1024)
            assert size_mb > 1, f"Arquivo muito pequeno ({size_mb:.2f}MB)"
            self.check("1000PEPEUSDT_data", True, f"✓ Presente ({size_mb:.2f}MB)")
        except Exception as e:
            self.check("1000PEPEUSDT_data", False, f"Erro: {e}")
            return False
        
        # 8. Validar diretórios de saída
        logger.info("\n[8/9] Validando diretórios de saída...")
        try:
            dirs_ok = True
            for dir_path in [
                "checkpoints/ppo_training",
                "logs/ppo_training",
                "models/trained"
            ]:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                assert Path(dir_path).exists(), f"Não conseguiu criar {dir_path}"
            self.check("output_directories", True, "✓ Todos os diretórios existem/criados")
        except Exception as e:
            self.check("output_directories", False, f"Erro ao validar: {e}")
        
        # 9. Validar estrutura de imports do agent
        logger.info("\n[9/9] Validando estrutura completa do agent...")
        try:
            from agent.environment import TradingEnvironment
            from agent.reward import RewardCalculator
            from agent.risk_manager import RiskManager
            self.check(
                "agent_structure",
                True,
                "✓ TradingEnvironment, RewardCalculator, RiskManager importados"
            )
        except Exception as e:
            self.check("agent_structure", False, f"Erro: {e}")
            self.warnings.append(f"Estrutura do agent pode ter issues: {e}")
        
        return len(self.errors) == 0
    
    def print_summary(self):
        """Imprime sumário final."""
        logger.info("\n" + "="*70)
        logger.info("SUMÁRIO DO PRÉ-FLIGHT CHECK")
        logger.info("="*70)
        
        passed = sum(1 for _, result in self.results if result)
        total = len(self.results)
        
        logger.info(f"\nValidações: {passed}/{total} PASSADAS")
        
        if self.errors:
            logger.error("\n❌ ERROS ENCONTRADOS:")
            for error in self.errors:
                logger.error(f"   - {error}")
        
        if self.warnings:
            logger.warning("\n⚠️  AVISOS:")
            for warning in self.warnings:
                logger.warning(f"   - {warning}")
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        logger.info(f"\nTempo total: {elapsed:.2f}s")
        
        if len(self.errors) == 0:
            logger.info("\n✅ PRÉ-FLIGHT CHECK COMPLETO - TUDO OK!")
            logger.info("Sistema pronto para treinamento PPO Phase 4")
            return True
        else:
            logger.error("\n❌ PRÉ-FLIGHT CHECK FALHOU")
            logger.error("Corrija os erros acima antes de prosseguir")
            return False

def main():
    """Função principal."""
    validator = PreFlightValidator()
    success = validator.run_all_validations()
    validator.print_summary()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
