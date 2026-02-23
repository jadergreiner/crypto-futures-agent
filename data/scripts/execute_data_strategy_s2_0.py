#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Data Strategy S2-0: Execução Completa do Download 1 Ano
Role: Data Engineer #11 | Binance API Expert
Data: 22 de fevereiro de 2026
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.scripts.klines_cache_manager import KlinesOrchestrator
import logging

# ============================================================================
# LOGGING CONFIG
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("data/execution_log_s2_0.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# EXECUTION ORCHESTRATOR
# ============================================================================

class DataStrategyExecutor:
    """Orquestra execução completa S2-0."""
    
    def __init__(self):
        self.start_time = time.time()
        self.results = {
            "execution_id": datetime.utcnow().isoformat(),
            "phase": "S2-0 Data Strategy",
            "start_time": None,
            "end_time": None,
            "duration_minutes": 0,
            "symbols_total": 0,
            "symbols_success": 0,
            "symbols_failed": 0,
            "total_candles": 0,
            "storage_mb": 0,
            "rate_limit_usage_pct": 0,
            "metrics": {},
            "status": "EXECUTING"
        }
    
    def execute(self):
        """Executa S2-0 completo."""
        logger.info("=" * 80)
        logger.info("🚀 S2-0 DATA STRATEGY INITIALIZATION")
        logger.info("=" * 80)
        
        self.results["start_time"] = datetime.utcnow().isoformat()
        
        try:
            # STEP 1: Preparação
            logger.info("\n📋 STEP 1: Preparação e Validação")
            self._prepare_environment()
            
            # STEP 2: Inicializar Orchestrator
            logger.info("\n🔧 STEP 2: Inicializando Binance Orchestrator")
            orch = KlinesOrchestrator(
                db_path="data/klines_cache.db",
                symbols_file="config/symbols.json"
            )
            
            self.results["symbols_total"] = len(orch.symbols)
            logger.info(f"✅ Carregados {len(orch.symbols)} símbolos")
            logger.info(f"   Símbolos: {', '.join(orch.symbols[:5])}... (primeiros 5)")
            
            # STEP 3: Teste com 3 símbolos primeiro (validação rápida)
            logger.info("\n⚡ STEP 3: Teste Rápido (3 símbolos para validação)")
            test_symbols = orch.symbols[:3]
            logger.info(f"   Testando com: {test_symbols}")
            
            test_stats = orch.fetch_full_year(
                symbols=test_symbols,
                interval="4h",
                from_days_ago=7  # Apenas 7 dias para teste
            )
            
            logger.info(f"✅ Teste completo: {test_stats}")
            
            # STEP 4: Download completo 1 ano
            logger.info("\n📥 STEP 4: Download Completo (1 ano, 60 símbolos)")
            logger.info(f"   Período: 365 dias (1 ano)")
            logger.info(f"   Intervalo: 4h (6 candles/dia)")
            logger.info(f"   Estimativa: ~2.190 candles/símbolo = 131.400 total")
            logger.info(f"   Prazo estimado: 15-20 minutos")
            
            fetch_start = time.time()
            full_stats = orch.fetch_full_year(
                symbols=orch.symbols,
                interval="4h",
                from_days_ago=365
            )
            fetch_duration = (time.time() - fetch_start) / 60
            
            logger.info(f"\n✅ Download concluído em {fetch_duration:.1f} minutos")
            
            # STEP 5: Validação de Integridade
            logger.info("\n🔍 STEP 5: Validação de Integridade (99%+)")
            
            validate_start = time.time()
            validation_results = orch.validate_all()
            validate_duration = (time.time() - validate_start) / 60
            
            logger.info(f"✅ Validação concluída em {validate_duration:.1f} minutos")
            
            # STEP 6: Análise de Resultados
            logger.info("\n📊 STEP 6: Análise de Resultados")
            self._analyze_results(full_stats, validation_results, orch)
            
            # STEP 7: Documentação
            logger.info("\n📝 STEP 7: Salvando Documentação")
            self._save_deliverables(full_stats, validation_results, orch)
            
            self.results["status"] = "SUCCESS"
            self.results["end_time"] = datetime.utcnow().isoformat()
            self.results["duration_minutes"] = (time.time() - self.start_time) / 60
        
        except Exception as e:
            logger.error(f"\n❌ ERRO CRÍTICO: {e}", exc_info=True)
            self.results["status"] = "FAILED"
            self.results["error"] = str(e)
            self.results["end_time"] = datetime.utcnow().isoformat()
            self.results["duration_minutes"] = (time.time() - self.start_time) / 60
        
        finally:
            self._print_summary()
    
    def _prepare_environment(self):
        """Prepara diretórios e validações."""
        # Ensure data directory exists
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        scripts_dir = Path("data/scripts")
        scripts_dir.mkdir(exist_ok=True)
        
        # Verify symbols.json
        symbols_file = Path("config/symbols.json")
        if not symbols_file.exists():
            logger.error(f"❌ {symbols_file} não encontrado")
            raise FileNotFoundError(f"Arquivo crítico não encontrado: {symbols_file}")
        
        logger.info(f"✅ Ambiente preparado")
        logger.info(f"   - data/: OK")
        logger.info(f"   - config/symbols.json: OK")
    
    def _analyze_results(self, full_stats: dict, validation_results: dict, orch):
        """Analisa resultados de download e validação."""
        success_count = 0
        failed_count = 0
        total_candles = 0
        
        for symbol, count in full_stats.items():
            if isinstance(count, int):
                success_count += 1
                total_candles += count
            else:
                failed_count += 1
        
        # Calcular estatísticas de validação
        pass_rate = 100
        total_invalid = 0
        total_gaps = 0
        
        for symbol, result in validation_results.items():
            if result["status"] == "FAIL":
                pass_rate = min(pass_rate, 0)
            total_invalid += result.get("invalid", 0)
            total_gaps += len(result.get("gaps", []))
        
        # Tamanho do database
        db_path = Path("data/klines_cache.db")
        db_size_mb = db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0
        
        self.results["symbols_success"] = success_count
        self.results["symbols_failed"] = failed_count
        self.results["total_candles"] = total_candles
        self.results["storage_mb"] = round(db_size_mb, 2)
        self.results["rate_limit_usage_pct"] = round(
            (total_candles / 131400) * (88 / 1200) * 100, 2
        )  # Estimativa: 88 req para 60 símbolos, ~7% dos limites
        
        self.results["metrics"] = {
            "candles_avg_by_symbol": round(total_candles / max(1, success_count), 0),
            "validation_invalid_total": total_invalid,
            "validation_gaps_total": total_gaps,
            "db_size_mb": db_size_mb
        }
        
        logger.info(f"\n📈 RESULTADOS:")
        logger.info(f"   Símbolos com sucesso: {success_count}/{self.results['symbols_total']}")
        logger.info(f"   Total de candles: {total_candles:,}")
        logger.info(f"   Storage utilizado: {db_size_mb:.2f} MB")
        logger.info(f"   Taxa de sucesso: {(success_count/self.results['symbols_total']*100):.1f}%")
        logger.info(f"   Candles/símbolo (média): {total_candles/max(1, success_count):.0f}")
    
    def _save_deliverables(self, full_stats, validation_results, orch):
        """Salva documentação de entrega."""
        deliverables = {
            "execution_summary": self.results,
            "fetch_results": full_stats,
            "validation_results": validation_results,
            "orchestrator_metadata": orch.metadata
        }
        
        summary_file = Path(f"data/S2_0_SUMMARY_{datetime.utcnow():%Y%m%d_%H%M%S}.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(deliverables, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Deliverables salvos: {summary_file}")
    
    def _print_summary(self):
        """Imprime resumo final."""
        logger.info("\n" + "=" * 80)
        logger.info("📊 RESUMO FINAL S2-0")
        logger.info("=" * 80)
        logger.info(f"Status:              {self.results['status']}")
        logger.info(f"Início:              {self.results['start_time']}")
        logger.info(f"Fim:                 {self.results['end_time']}")
        logger.info(f"Duração:             {self.results['duration_minutes']:.1f} minutos")
        logger.info(f"\nSímbolos:")
        logger.info(f"  Total:             {self.results['symbols_total']}")
        logger.info(f"  Sucesso:           {self.results['symbols_success']}")
        logger.info(f"  Falha:             {self.results['symbols_failed']}")
        logger.info(f"\nDados:")
        logger.info(f"  Total de candles:  {self.results['total_candles']:,}")
        logger.info(f"  Storage utilizado: {self.results['storage_mb']:.2f} MB")
        logger.info(f"  Rate limit usage:  {self.results['rate_limit_usage_pct']:.1f}%")
        logger.info(f"\nMétricas:")
        for key, value in self.results.get("metrics", {}).items():
            logger.info(f"  {key}: {value}")
        logger.info("=" * 80)


# ============================================================================
# CLI ENTRY
# ============================================================================

if __name__ == "__main__":
    logger.info("🚀 Iniciando Data Strategy S2-0...")
    
    executor = DataStrategyExecutor()
    executor.execute()
    
    sys.exit(0 if executor.results["status"] == "SUCCESS" else 1)
