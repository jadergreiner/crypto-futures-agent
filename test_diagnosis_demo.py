#!/usr/bin/env python
"""
Script de demonstração do diagnóstico de dados.

Mostra como o método diagnose_data_readiness() funciona na prática.
"""

import logging
from agent.data_loader import DataLoader
from data.database import DatabaseManager
from config.settings import DB_PATH

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_diagnostico_sem_banco():
    """Demonstra diagnóstico quando não há banco de dados."""
    print("\n" + "="*70)
    print("DEMO 1: Diagnóstico SEM banco de dados")
    print("="*70)
    
    loader = DataLoader(db=None)
    diagnosis = loader.diagnose_data_readiness(
        symbol="BTCUSDT",
        min_length_train=1000,
        min_length_val=200
    )
    
    print(f"\nPronto: {diagnosis['ready']}")
    print(f"Resumo:\n{diagnosis['summary']}")


def demo_diagnostico_com_banco():
    """Demonstra diagnóstico com banco de dados real."""
    print("\n" + "="*70)
    print("DEMO 2: Diagnóstico COM banco de dados")
    print("="*70)
    
    try:
        db = DatabaseManager(DB_PATH)
        loader = DataLoader(db=db)
        
        diagnosis = loader.diagnose_data_readiness(
            symbol="BTCUSDT",
            min_length_train=1000,
            min_length_val=200,
            train_ratio=0.8
        )
        
        print(f"\nSímbolo: {diagnosis['symbol']}")
        print(f"Pronto para treinar: {diagnosis['ready']}")
        
        print("\n--- Status dos Timeframes ---")
        for tf, info in diagnosis['timeframes'].items():
            print(f"\n{tf.upper()}:")
            print(f"  Disponível: {info.get('available', 0)} candles")
            if 'needed_total' in info:
                print(f"  Necessário (total): {info['needed_total']} candles")
                print(f"  Necessário (treino): {info['needed_train']} candles")
                print(f"  Após split 80/20: {info['after_split']} candles")
            print(f"  Status: {info['status']}")
            if info.get('recommendation'):
                print(f"  Recomendação: {info['recommendation']}")
        
        if diagnosis.get('indicators'):
            print("\n--- Requisitos de Indicadores ---")
            for ind, info in diagnosis['indicators'].items():
                print(f"\n{ind}:")
                print(f"  Necessário: {info['required_candles']} candles")
                print(f"  Disponível: {info['available']} candles")
                print(f"  Status: {info['status']}")
                if '❌' in info.get('status', ''):
                    print(f"  Recomendação: {info['recommendation']}")
        
        if diagnosis.get('data_freshness'):
            print("\n--- Atualização dos Dados ---")
            freshness = diagnosis['data_freshness']
            print(f"  Último candle H4: {freshness['last_h4_timestamp']}")
            print(f"  Horas desde última atualização: {freshness['hours_since_last']}")
            if freshness['is_stale']:
                print("  ⚠️  DADOS DESATUALIZADOS (>24h)")
        
        print("\n" + "="*70)
        print("RESUMO FINAL")
        print("="*70)
        print(diagnosis['summary'])
        
    except Exception as e:
        print(f"\nErro ao conectar ao banco de dados: {e}")
        print("Execute 'python main.py --setup' para criar o banco e coletar dados.")


if __name__ == "__main__":
    print("\n")
    print("="*70)
    print("DEMONSTRAÇÃO DO DIAGNÓSTICO DE DISPONIBILIDADE DE DADOS")
    print("="*70)
    
    # Demo 1: Sem banco
    demo_diagnostico_sem_banco()
    
    # Demo 2: Com banco (se existir)
    demo_diagnostico_com_banco()
    
    print("\n" + "="*70)
    print("FIM DA DEMONSTRAÇÃO")
    print("="*70)
    print()
