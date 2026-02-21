#!/usr/bin/env python
"""
TASK 1: Extração de Dados Históricos para Treinamento PPO

Prepara 700 candles H4 para OGNUSDT e 1000PEPEUSDT.
- Verifica se ParquetCache já tem dados
- Se não: carrega via API Binance pública (HTTP)
- Valida continuidade (sem gaps)
- Cria dataset final (80% treino, 20% validação)
"""
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import requests
import time

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ExtractionResult:
    """Resultado da extração de dados."""
    symbol: str
    timeframe: str
    candles_count: int
    start_timestamp: int
    end_timestamp: int
    has_gaps: bool
    all_positive_volume: bool
    is_valid: bool
    parquet_path: Optional[str] = None
    error: Optional[str] = None


class DataExtractor:
    """Extrator de dados históricos para treinamento."""
    
    CACHE_DIR = Path('backtest/cache')
    MIN_CANDLES = 700
    REQUIRED_TIMEFRAME = '4h'
    
    def __init__(self):
        """Inicializa extrator."""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.extraction_results: Dict[str, ExtractionResult] = {}
        
    def _get_parquet_path(self, symbol: str, timeframe: str) -> Path:
        """Retorna path para arquivo Parquet."""
        return self.CACHE_DIR / f"{symbol}_{timeframe}.parquet"
    
    def _load_from_cache(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Carrega dados do cache Parquet se existirem."""
        parquet_path = self._get_parquet_path(symbol, timeframe)
        
        if parquet_path.exists():
            try:
                df = pd.read_parquet(str(parquet_path))
                logger.info(f"✅ Cache hit: {symbol} {timeframe} ({len(df)} candles)")
                return df
            except Exception as e:
                logger.warning(f"⚠️  Erro ao ler cache: {symbol} {timeframe}: {e}")
                return None
        
        return None
    
    def _fetch_from_ccxt(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Busca dados via API REST Binance pública."""
        try:
            logger.info(f"📥 Buscando {symbol} {timeframe} via API Binance...")
            
            # Configurar URL da API
            base_url = "https://fapi.binance.com"
            endpoint = "/fapi/v1/klines"
            
            # Mapear timeframe para valor Binance
            tf_map = {'1h': '1h', '4h': '4h', '1d': '1d'}
            binance_tf = tf_map.get(timeframe, '4h')
            
            # Parâmetros iniciais
            params = {
                'symbol': symbol,
                'interval': binance_tf,
                'limit': 1000  # Máximo que a API retorna por requisição
            }
            
            all_klines = []
            max_iterations = 20  # Máximo de requisições para não exagerar
            
            for iteration in range(max_iterations):
                try:
                    response = requests.get(
                        f"{base_url}{endpoint}",
                        params=params,
                        timeout=10
                    )
                    response.raise_for_status()
                    
                    klines = response.json()
                    if not klines:
                        logger.info(f"  Sem mais dados após {len(all_klines)} candles")
                        break
                    
                    all_klines.extend(klines)
                    
                    # Para próxima requisição, usar timestamp do último candle como startTime
                    last_time = klines[-1][0]
                    params['startTime'] = last_time + 1
                    
                    logger.info(f"  Iteração {iteration+1}: {len(klines)} candles (total: {len(all_klines)})")
                    
                    # Rate limiting
                    time.sleep(0.1)
                    
                    if len(all_klines) >= 2000:  # Mais que suficiente
                        break
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"  Erro na requisição: {e}")
                    break
                except json.JSONDecodeError:
                    logger.error("  Erro ao decodificar JSON")
                    break
            
            if not all_klines:
                logger.error(f"❌ Nenhum dado Binance para {symbol}")
                return None
            
            # Converter para DataFrame
            # Formato: [timestamp, open, high, low, close, volume, close_time, quote_volume, trades, ...]
            df = pd.DataFrame(
                [[k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[7])] 
                 for k in all_klines],
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            logger.info(f"✅ Binance: {symbol} {timeframe} ({len(df)} candles)")
            return df
            
        except Exception as e:
            logger.error(f"❌ Erro Binance: {symbol} {timeframe}: {e}")
            return None
    
    def _validate_ohlcv(self, df: pd.DataFrame, symbol: str, 
                        timeframe: str) -> Tuple[bool, bool, str]:
        """
        Valida integridade de dados.
        
        Retorna: (is_valid, has_gaps, error_msg)
        """
        errors = []
        has_gaps = False
        
        # Checks básicos
        if df is None or df.empty:
            return False, True, "DataFrame vazio"
        
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            return False, False, f"Colunas faltando: {missing}"
        
        # Sanity checks OHLC
        if (df['high'] < df['low']).any():
            errors.append("High < Low em alguns candles")
        
        if (df['close'] < df['low']).any() or (df['close'] > df['high']).any():
            errors.append("Close fora do intervalo [Low, High]")
        
        if (df['open'] < df['low']).any() or (df['open'] > df['high']).any():
            errors.append("Open fora do intervalo [Low, High]")
        
        # Volume > 0
        if (df['volume'] <= 0).any():
            errors.append(f"Volume <= 0 em {(df['volume'] <= 0).sum()} candles")
        
        # Timestamp ordering
        if not df['timestamp'].is_monotonic_increasing:
            errors.append("Timestamps não estão em ordem crescente")
        
        # Gap checking (para 4h, gap máximo = 4h = 14400000 ms)
        EXPECTED_GAP_MS = 4 * 60 * 60 * 1000
        if len(df) > 1:
            gaps = df['timestamp'].diff()[1:] - EXPECTED_GAP_MS
            large_gaps = gaps[gaps > EXPECTED_GAP_MS * 0.5]  # Tolerância de 50%
            if len(large_gaps) > 0:
                has_gaps = True
                errors.append(f"{len(large_gaps)} gaps detectados > tolerância")
        
        is_valid = len(errors) == 0 and len(df) >= self.MIN_CANDLES
        error_msg = " | ".join(errors) if errors else ""
        
        return is_valid, has_gaps, error_msg
    
    def extract_symbol(self, symbol: str, timeframe: str = '4h') -> ExtractionResult:
        """
        Extrai dados para um símbolo.
        
        Estratégia:
        1. Tentar carregar do cache Parquet
        2. Se falhar, tentar API Binance pública (HTTP)
        """
        logger.info(f"\n📊 Extraindo {symbol} {timeframe}...")
        
        try:
            # 1. Tentar cache
            df = self._load_from_cache(symbol, timeframe)
            
            # 2. Se não há cache, buscar da API Binance
            if df is None:
                logger.info(f"💾 Cache não encontrado, buscando dados da API Binance...")
                df = self._fetch_from_ccxt(symbol, timeframe)
            
            # Se ainda não temos dados
            if df is None:
                return ExtractionResult(
                    symbol=symbol,
                    timeframe=timeframe,
                    candles_count=0,
                    start_timestamp=0,
                    end_timestamp=0,
                    has_gaps=True,
                    all_positive_volume=False,
                    is_valid=False,
                    error="API Binance indisponível ou símbolo não existe"
                )
            
            # 3. Validar
            is_valid, has_gaps, error_msg = self._validate_ohlcv(df, symbol, timeframe)
            
            # Log validação
            if error_msg:
                logger.warning(f"⚠️  Validação: {error_msg}")
            
            all_positive_volume = (df['volume'] > 0).all()
            
            # 4. Salvar em cache se válido
            parquet_path = None
            if is_valid:
                parquet_path = str(self._get_parquet_path(symbol, timeframe))
                try:
                    df.to_parquet(parquet_path, index=False)
                    logger.info(f"💾 Cache salvo: {parquet_path}")
                except Exception as e:
                    logger.error(f"❌ Erro ao salvar cache: {e}")
                    parquet_path = None
            
            result = ExtractionResult(
                symbol=symbol,
                timeframe=timeframe,
                candles_count=len(df),
                start_timestamp=int(df['timestamp'].min()),
                end_timestamp=int(df['timestamp'].max()),
                has_gaps=has_gaps,
                all_positive_volume=all_positive_volume,
                is_valid=is_valid,
                parquet_path=parquet_path,
                error=error_msg if not is_valid else None
            )
            
            # Log resultado
            status = "✅" if is_valid else "❌"
            logger.info(f"{status} {symbol}: {len(df)} candles")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro crítico: {symbol}: {e}")
            return ExtractionResult(
                symbol=symbol,
                timeframe=timeframe,
                candles_count=0,
                start_timestamp=0,
                end_timestamp=0,
                has_gaps=True,
                all_positive_volume=False,
                is_valid=False,
                error=str(e)
            )
    
    def prepare_training_dataset(self, symbols: list, 
                                  train_split: float = 0.8) -> Dict:
        """
        Prepara dataset final para treinamento.
        
        - Combina dados de múltiplos símbolos
        - Split: 80% treino, 20% validação
        - Salva em formato compatível com BacktestEnvironment
        """
        logger.info(f"\n🔧 Preparando dataset de treinamento...")
        
        all_data = {}
        
        # Carregar cada símbolo
        for symbol in symbols:
            parquet_path = self._get_parquet_path(symbol, '4h')
            if parquet_path.exists():
                df = pd.read_parquet(str(parquet_path))
                all_data[symbol] = df
                logger.info(f"  ✅ {symbol}: {len(df)} candles")
            else:
                logger.error(f"  ❌ {symbol}: arquivo não encontrado")
        
        if not all_data:
            logger.error("❌ Nenhum dado disponível para dataset")
            return {"error": "Nenhum dado disponível"}
        
        # Criar dataset combinado
        dataset = {
            "metadata": {
                "symbols": list(all_data.keys()),
                "timeframe": "4h",
                "total_candles": sum(len(df) for df in all_data.values()),
                "created_at": datetime.utcnow().isoformat()
            },
            "data": {},
            "splits": {
                "train": {},
                "validation": {}
            }
        }
        
        # Split por símbolo
        for symbol, df in all_data.items():
            split_idx = int(len(df) * train_split)
            
            train_df = df.iloc[:split_idx]
            val_df = df.iloc[split_idx:]
            
            dataset["data"][symbol] = {
                "total": len(df),
                "train_start": int(df.iloc[0]['timestamp']),
                "train_end": int(train_df.iloc[-1]['timestamp']),
                "val_start": int(val_df.iloc[0]['timestamp']),
                "val_end": int(val_df.iloc[-1]['timestamp'])
            }
            
            dataset["splits"]["train"][symbol] = len(train_df)
            dataset["splits"]["validation"][symbol] = len(val_df)
            
            logger.info(f"  {symbol}: {len(train_df)} treino + {len(val_df)} validação")
        
        # Salvar dataset metadata
        dataset_dir = Path('data/training_datasets')
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        dataset_info_path = dataset_dir / 'dataset_info.json'
        with open(dataset_info_path, 'w') as f:
            json.dump(dataset, f, indent=2)
        
        logger.info(f"📄 Dataset info salvo: {dataset_info_path}")
        
        return dataset


def main():
    """TASK 1: Extração de Dados Históricos."""
    
    logger.info("="*70)
    logger.info("TASK 1: EXTRAÇÃO DE DADOS HISTÓRICOS PARA TREINAMENTO PPO")
    logger.info("="*70)
    
    extractor = DataExtractor()
    
    # Símbolos necessários
    symbols = ['OGNUSDT', '1000PEPEUSDT']
    
    # 1. Extrair dados
    logger.info("\n[FASE 1] Extraindo dados...")
    results = {}
    for symbol in symbols:
        result = extractor.extract_symbol(symbol, '4h')
        results[symbol] = result
    
    # 2. Preparar dataset
    logger.info("\n[FASE 2] Preparando dataset de treinamento...")
    valid_symbols = [s for s, r in results.items() if r.is_valid]
    
    if len(valid_symbols) >= 1:  # Aceita pelo menos 1 símbolo
        dataset_info = extractor.prepare_training_dataset(valid_symbols)
    else:
        dataset_info = {"error": "Nenhum dado válido extraído"}
    
    # 3. Resumo final
    logger.info("\n" + "="*70)
    logger.info("RESUMO - TASK 1")
    logger.info("="*70)
    
    for symbol in symbols:
        result = results[symbol]
        status = "✅ OK" if result.is_valid else f"❌ ERRO: {result.error}"
        print(f"  {symbol}: {result.candles_count} candles - {status}")
    
    # Retornar status
    ready = (
        results['OGNUSDT'].is_valid and 
        results['1000PEPEUSDT'].is_valid
    )
    
    if ready:
        logger.info("\n✅ TASK 1 CONCLUÍDA COM SUCESSO")
        print(f"\n  Dados prontos para treinamento:")
        print(f"  - {results['OGNUSDT'].candles_count} candles OGNUSDT")
        print(f"  - {results['1000PEPEUSDT'].candles_count} candles 1000PEPEUSDT")
    else:
        logger.warning("\n⚠️  TASK 1 PARCIALMENTE CONCLUÍDA")
        print(f"\n  Dados extraídos:")
        for symbol in symbols:
            result = results[symbol]
            if result.is_valid:
                print(f"  ✅ {symbol}: {result.candles_count} candles")
            else:
                print(f"  ❌ {symbol}: {result.error}")
    
    return results, dataset_info


if __name__ == '__main__':
    results, dataset_info = main()
