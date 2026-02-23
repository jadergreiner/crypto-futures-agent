#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Validação Prévia S2-0 + Teste de Conectividade Binance
"""

import json
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s'
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Verifica dependências críticas."""
    logger.info("\n✅ Validando dependências...")
    
    deps = ["requests", "sqlite3", "json", "logging"]
    missing = []
    
    for dep in deps:
        try:
            __import__(dep)
            logger.info(f"   ✓ {dep}")
        except ImportError:
            logger.error(f"   ✗ {dep} (FALTANDO)")
            missing.append(dep)
    
    if missing:
        logger.error(f"\n❌ Instale: pip install {' '.join(missing)}")
        return False
    return True

def check_config():
    """Verifica arquivos de configuração."""
    logger.info("\n✅ Validando arquivos de configuração...")
    
    files_to_check = [
        "config/symbols.json",
        "data/scripts/klines_cache_manager.py",
    ]
    
    all_ok = True
    for file_path in files_to_check:
        p = Path(file_path)
        if p.exists():
            logger.info(f"   ✓ {file_path}")
        else:
            logger.error(f"   ✗ {file_path} (NÃO ENCONTRADO)")
            all_ok = False
    
    return all_ok

def check_symbols():
    """Valida lista de símbolos."""
    logger.info("\n✅ Validando símbolos...")
    
    try:
        with open("config/symbols.json", "r") as f:
            data = json.load(f)
            symbols = data.get("symbols", [])
            
            logger.info(f"   Total de símbolos: {len(symbols)}")
            logger.info(f"   Primeiros 5: {symbols[:5]}")
            logger.info(f"   Últimos 5: {symbols[-5:]}")
            
            # Validar formato
            for sym in symbols:
                if not isinstance(sym, str) or len(sym) < 6:
                    logger.error(f"   ✗ Símbolo inválido: {sym}")
                    return False
            
            logger.info(f"   ✓ Todos os símbolos válidos")
            return True
    
    except Exception as e:
        logger.error(f"   ✗ Erro ao carregar símbolos: {e}")
        return False

def check_binance_api():
    """Testa conectividade com Binance API."""
    logger.info("\n✅ Testando conectividade Binance API...")
    
    try:
        import requests
        
        # Endpoint público (sem auth)
        url = "https://fapi.binance.com/fapi/v1/time"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            server_time = response.json()["serverTime"]
            logger.info(f"   ✓ Ping OK")
            logger.info(f"   Server time: {datetime.fromtimestamp(server_time/1000)}")
            
            # Test klines endpoint com 1 requisição
            logger.info("\n   Testando endpoint /klines...")
            now = int(datetime.utcnow().timestamp() * 1000)
            week_ago = now - (7 * 24 * 60 * 60 * 1000)
            
            params = {
                "symbol": "BTCUSDT",
                "interval": "4h",
                "startTime": week_ago,
                "endTime": now,
                "limit": 10
            }
            
            response = requests.get(
                "https://fapi.binance.com/fapi/v1/klines",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"   ✓ /klines OK (retornou {len(data)} candles)")
                
                if data:
                    first_candle = data[0]
                    logger.info(f"   Sample candle: [{first_candle[0]}, {first_candle[4]}]")
                
                return True
            else:
                logger.error(f"   ✗ /klines erro: {response.status_code}")
                return False
        
        else:
            logger.error(f"   ✗ Ping falhou: {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"   ✗ Erro: {e}")
        return False

def create_db_schema():
    """Cria schema SQLite."""
    logger.info("\n✅ Setup de Database SQLite...")
    
    try:
        import sqlite3
        
        db_path = Path("data/klines_cache.db")
        
        if db_path.exists():
            logger.info(f"   ✓ Database existente: {db_path}")
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM klines")
            count = cursor.fetchone()[0]
            logger.info(f"   ✓ {count} candles já armazenados")
            conn.close()
        else:
            logger.info(f"   Nova database: {db_path}")
            # Schema será criado pelo orchestrator
        
        return True
    
    except Exception as e:
        logger.error(f"   ✗ Erro: {e}")
        return False

def estimate_execution():
    """Estima tempo de execução."""
    logger.info("\n📊 ESTIMATIVA DE EXECUÇÃO S2-0")
    logger.info("   ─────────────────────────────")
    logger.info("   Período: 365 dias (1 ano)")
    logger.info("   Intervalo: 4h")
    logger.info("   Símbolos: 60")
    logger.info("   Candles/símbolo: 2.190 (365d × 6 candles/dia)")
    logger.info("   Total candles: 131.400")
    logger.info("   Requisições: ~88 (60 sym × 1.5 calls/sym)")
    logger.info("   Rate limit Binance: 1200/min")
    logger.info("   Uso estimado: ~7% do rate limit")
    logger.info("   Tempo estimado: 15-20 minutos")
    logger.info("   Storage esperado: ~0.6 MB (SQLite)")

def main():
    """Executa validações."""
    logger.info("=" * 80)
    logger.info("🚀 S2-0 DATA STRATEGY - PRÉ-VALIDAÇÃO")
    logger.info("=" * 80)
    
    checks = [
        ("Dependências", check_dependencies),
        ("Configuração", check_config),
        ("Símbolos", check_symbols),
        ("Binance API", check_binance_api),
        ("Database", create_db_schema),
    ]
    
    results = {}
    for name, check_fn in checks:
        try:
            results[name] = check_fn()
        except Exception as e:
            logger.error(f"\n❌ Erro em {name}: {e}")
            results[name] = False
    
    estimate_execution()
    
    logger.info("\n" + "=" * 80)
    logger.info("📋 RESULTADO DA VALIDAÇÃO")
    logger.info("=" * 80)
    
    for name, status in results.items():
        status_str = "✅ OK" if status else "❌ FALHOU"
        logger.info(f"   {name:.<40} {status_str}")
    
    all_ok = all(results.values())
    
    if all_ok:
        logger.info("\n✅ PRÉ-VALIDAÇÃO COMPLETA - Sistema pronto para S2-0")
        logger.info("\nPróximo passo: python data/scripts/execute_data_strategy_s2_0.py")
        return 0
    else:
        logger.info("\n❌ Corriga os erros acima antes de executar S2-0")
        return 1

if __name__ == "__main__":
    sys.exit(main())
