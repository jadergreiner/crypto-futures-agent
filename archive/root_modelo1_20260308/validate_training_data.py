"""
Validador de dados para treinamento — Especialista ML.
Executa 8 validações críticas para garantir qualidade e segurança do dataset.

Validações:
1. Check Temporal Integrity: gaps, duplicatas, ordem cronológica
2. Check Distribution: shape, dtype, outliers, skewness
3. Check Data Leakage: separação treino/validação, scaler fit
4. Check Normalization: RobustScaler por símbolo, mean/std
5. Check Feature Patterns: correlação, entropy, zero-variance
6. Check Target Imbalance: distribuição ações (se aplicável)
7. Check Missing Values: NaN, inf, edge cases
8. Check Performance Benchmark: tempo load, batch generation, pico memória
"""

import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.preprocessing import RobustScaler
from scipy import stats

from data.data_loader import DataLoader
from config.symbols import SYMBOLS
from monitoring.logger import AgentLogger

logger = logging.getLogger(__name__)


class MLValidator:
    """Validador especialista em ML para dataset de treinamento."""

    def __init__(self, db_path: str):
        """
        Inicializa validador.

        Args:
            db_path: Caminho para DATABASE_PATH
        """
        self.db_path = db_path
        self.loader = DataLoader(db_path)
        self.results = {
            'checks': {},
            'overall_status': 'OK',
            'warnings': [],
            'errors': [],
            'metrics': {}
        }

    def run_all_checks(
        self,
        symbols: List[str],
        start_date: str = "2024-08-01",
        end_date: str = "2026-02-20"
    ) -> Dict[str, Any]:
        """
        Executa todas as 8 validações.

        Returns:
            Resultado consolidado com status overall e detalhes de cada check
        """
        logger.info("[MLValidator] Iniciando suite de 8 validações...")

        try:
            # 1. Temporal Integrity
            self._check_temporal_integrity(symbols, start_date, end_date)

            # 2. Distribution Check
            self._check_distribution(symbols, start_date, end_date)

            # 3. Data Leakage
            self._check_data_leakage(symbols)

            # 4. Normalization
            self._check_normalization(symbols, start_date, end_date)

            # 5. Feature Patterns
            self._check_feature_patterns(symbols, start_date, end_date)

            # 6. Target Imbalance
            self._check_target_imbalance(symbols)

            # 7. Missing Values
            self._check_missing_values(symbols, start_date, end_date)

            # 8. Performance Benchmark
            self._check_performance_benchmark(symbols, start_date, end_date)

        except Exception as e:
            logger.error(f"[MLValidator] Erro durante validação: {e}")
            self.results['overall_status'] = 'CRITICAL'
            self.results['errors'].append(str(e))

        # Consolidar status
        has_errors = len(self.results['errors']) > 0
        has_warnings = len(self.results['warnings']) > 0

        if has_errors:
            self.results['overall_status'] = 'CRITICAL'
        elif has_warnings:
            self.results['overall_status'] = 'WARNING'
        else:
            self.results['overall_status'] = 'OK'

        logger.info(f"[MLValidator] Status final: {self.results['overall_status']}")
        return self.results

    def _check_temporal_integrity(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> None:
        """
        CHECK 1: Integridade temporal — gaps, duplicatas, ordem.
        """
        check_name = "Temporal Integrity"
        logger.info(f"[Validador] {check_name}...")

        check_results = {}

        for symbol in symbols:
            try:
                df = self.loader.load_training_data(symbol, start_date, end_date)

                # Duplicatas
                duplicates = df.index.duplicated().sum()

                # Gaps > 15 minutos
                gaps = (df.index.to_series().diff().dt.total_seconds() / 60) > 15
                gap_count = gaps.sum()

                # Monotônico? (ordem cronológica)
                is_monotonic = df.index.is_monotonic_increasing

                # Duração
                duration_days = (df.index[-1] - df.index[0]).days

                status = 'OK'
                if duplicates > 0 or gap_count > 10 or not is_monotonic:
                    status = 'FAIL'
                    self.results['errors'].append(
                        f"{symbol}: {duplicates} dups, {gap_count} gaps, monotonic={is_monotonic}"
                    )

                check_results[symbol] = {
                    'status': status,
                    'duplicates': duplicates,
                    'gaps_gt_15min': gap_count,
                    'is_monotonic': is_monotonic,
                    'duration_days': duration_days
                }

            except Exception as e:
                self.results['errors'].append(f"{symbol} - {check_name}: {e}")
                check_results[symbol] = {'status': 'ERROR', 'error': str(e)}

        self.results['checks'][check_name] = check_results

    def _check_distribution(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> None:
        """
        CHECK 2: Distribuição — shape, dtype, outliers, skewness.
        """
        check_name = "Distribution"
        logger.info(f"[Validador] {check_name}...")

        check_results = {}

        for symbol in symbols:
            try:
                df = self.loader.load_training_data(symbol, start_date, end_date)

                # Shapes
                shape = df.shape

                # OHLCV validade
                invalid_ohlc = (df['high'] < df['low']).sum()

                # Outliers (> 5σ)
                closes = df['close'].values
                mean, std = closes.mean(), closes.std()
                outliers = ((closes > mean + 5*std) | (closes < mean - 5*std)).sum()

                # Skewness (>2 é assimétrico)
                skewness = stats.skew(df['close'])

                # Kurtosis (>3 é heavy-tail)
                kurtosis = stats.kurtosis(df['close'])

                status = 'OK'
                if invalid_ohlc > 0 or outliers > len(df) * 0.01:  # >1%
                    status = 'FAIL'
                    self.results['errors'].append(
                        f"{symbol}: invalid_ohlc={invalid_ohlc}, outliers={outliers} ({outliers/len(df)*100:.2f}%)"
                    )

                if abs(skewness) > 2:
                    status = 'WARNING'
                    self.results['warnings'].append(f"{symbol}: skewness alto ({skewness:.2f})")

                check_results[symbol] = {
                    'status': status,
                    'shape': shape,
                    'invalid_ohlcv': invalid_ohlc,
                    'outliers_5sigma': outliers,
                    'outliers_pct': f"{outliers/len(df)*100:.2f}%",
                    'skewness': f"{skewness:.2f}",
                    'kurtosis': f"{kurtosis:.2f}"
                }

            except Exception as e:
                self.results['errors'].append(f"{symbol} - {check_name}: {e}")
                check_results[symbol] = {'status': 'ERROR', 'error': str(e)}

        self.results['checks'][check_name] = check_results

    def _check_data_leakage(self, symbols: List[str]) -> None:
        """
        CHECK 3: Data leakage — validar separação treino/val.
        Regra: Trainset fitted ANTES de salvar scalers; testset usa scalers salvos.
        """
        check_name = "Data Leakage Prevention"
        logger.info(f"[Validador] {check_name}...")

        check_results = {}

        for symbol in symbols:
            try:
                # Simular: carrega treino, fit scaler, depois valida
                df = self.loader.load_training_data(symbol, "2024-08-01", "2025-08-01")  # 12M treino

                # Split temporal (não random!)
                split_idx = int(len(df) * 0.8)
                train_df = df.iloc[:split_idx]
                val_df = df.iloc[split_idx:]

                # Fit APENAS em treino
                scaler = RobustScaler()
                train_scaled = scaler.fit_transform(train_df[['close', 'volume']])

                # Transform val (sem re-fit)
                val_scaled = scaler.transform(val_df[['close', 'volume']])

                # Validar: escalarscaler mean/std vêm de treino
                train_mean = train_df[['close', 'volume']].mean().values
                scaler_center = scaler.center_

                # Tolerância: 0.01%
                matches = np.allclose(train_mean, scaler_center, rtol=1e-4)

                status = 'OK' if matches else 'FAIL'
                if not matches:
                    self.results['errors'].append(
                        f"{symbol}: RobustScaler não fit corretamente em treino"
                    )

                check_results[symbol] = {
                    'status': status,
                    'temporal_split': f"{len(train_df)}/{len(val_df)}",
                    'scaler_fitted_in_train': matches,
                    'train_val_feature_std_ratio': f"{train_df['close'].std() / val_df['close'].std():.2f}"
                }

            except Exception as e:
                self.results['errors'].append(f"{symbol} - {check_name}: {e}")
                check_results[symbol] = {'status': 'ERROR', 'error': str(e)}

        self.results['checks'][check_name] = check_results

    def _check_normalization(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> None:
        """
        CHECK 4: Normalização com RobustScaler.
        Validar: mean ≈ 0, scale ≈ 1 após normalização.
        """
        check_name = "Normalization (RobustScaler)"
        logger.info(f"[Validador] {check_name}...")

        check_results = {}

        for symbol in symbols:
            try:
                df = self.loader.load_training_data(symbol, start_date, end_date)

                # Aplicar RobustScaler
                scaler = RobustScaler()
                cols = ['close', 'volume']
                scaled = scaler.fit_transform(df[cols])
                scaled_df = pd.DataFrame(scaled, columns=cols, index=df.index)

                # Check: mean ≈ 0 (dentro de 0.01)
                mean_ok = np.allclose(scaled_df.mean(), 0, atol=0.01)

                # Check: Q3-Q1 ≈ 1 (IQR = 1 é a definição de RobustScaler)
                q1 = scaled_df.quantile(0.25)
                q3 = scaled_df.quantile(0.75)
                iqr = (q3 - q1).values
                iqr_ok = np.allclose(iqr, 1.0, rtol=0.1)

                status = 'OK' if mean_ok and iqr_ok else 'FAIL'
                if not (mean_ok and iqr_ok):
                    self.results['warnings'].append(
                        f"{symbol}: normalização fora dos limites (mean_ok={mean_ok}, iqr_ok={iqr_ok})"
                    )

                check_results[symbol] = {
                    'status': status,
                    'mean_close': f"{scaled_df['close'].mean():.6f}",
                    'std_close': f"{scaled_df['close'].std():.6f}",
                    'iqr_close': f"{(q3['close'] - q1['close']):.6f}",
                    'range_close': f"[{scaled_df['close'].min():.2f}, {scaled_df['close'].max():.2f}]"
                }

            except Exception as e:
                self.results['errors'].append(f"{symbol} - {check_name}: {e}")
                check_results[symbol] = {'status': 'ERROR', 'error': str(e)}

        self.results['checks'][check_name] = check_results

    def _check_feature_patterns(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> None:
        """
        CHECK 5: Padrões de features — correlação, entropia, zero-variance.
        """
        check_name = "Feature Patterns"
        logger.info(f"[Validador] {check_name}...")

        check_results = {}

        for symbol in symbols:
            try:
                df = self.loader.load_training_data(symbol, start_date, end_date)

                # Correlação preço-volume
                corr = df[['close', 'volume']].corr().iloc[0, 1]

                # Zero-variance features
                zero_var_close = df['close'].std() == 0
                zero_var_volume = df['volume'].std() == 0

                # Entropia (quanto "randomness" tem no close returns?)
                returns = np.diff(np.log(df['close'].values))
                # Discretizar em 10 bins
                hist, _ = np.histogram(returns, bins=10)
                hist = hist[hist > 0]  # Remove bins vazios
                probabilities = hist / hist.sum()
                entropy = -np.sum(probabilities * np.log2(probabilities))

                status = 'OK'
                if zero_var_close or zero_var_volume:
                    status = 'FAIL'
                    self.results['errors'].append(f"{symbol}: zero variance detectado")

                check_results[symbol] = {
                    'status': status,
                    'price_volume_correlation': f"{corr:.4f}",
                    'zero_variance': f"close={zero_var_close}, vol={zero_var_volume}",
                    'entropy_returns': f"{entropy:.2f} bits",
                    'expected_entropy': "log2(10)=3.32 bits (10 bins humanos)"
                }

            except Exception as e:
                self.results['errors'].append(f"{symbol} - {check_name}: {e}")
                check_results[symbol] = {'status': 'ERROR', 'error': str(e)}

        self.results['checks'][check_name] = check_results

    def _check_target_imbalance(self, symbols: List[str]) -> None:
        """
        CHECK 6: Target imbalance — ações esperadas (se houver dados de labels).
        Para v0.3, este é placeholder. Será ativado quando temos trades reais.
        """
        check_name = "Target Imbalance"
        logger.info(f"[Validador] {check_name}...")

        check_results = {}

        for symbol in symbols:
            # Placeholder: distribuição esperada é uniforme
            check_results[symbol] = {
                'status': 'PLACEHOLDER',
                'note': 'v0.3 não usa labels pré-coletados, ações geradas durante treinamento',
                'expected_distribution': 'Uniformemente distribuído entre 5 ações'
            }

        self.results['checks'][check_name] = check_results

    def _check_missing_values(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> None:
        """
        CHECK 7: Missing values — NaN, inf, edge cases.
        """
        check_name = "Missing Values"
        logger.info(f"[Validador] {check_name}...")

        check_results = {}

        for symbol in symbols:
            try:
                df = self.loader.load_training_data(symbol, start_date, end_date)

                # NaN
                nan_total = df.isna().sum().sum()

                # Inf
                inf_total = 0
                for col in df.select_dtypes(include=[np.number]):
                    inf_total += np.isinf(df[col]).sum()

                # Zero prices (pode acontecer em edge case)
                zero_close = (df['close'] == 0).sum()
                zero_volume = (df['volume'] == 0).sum()

                status = 'OK'
                if nan_total > 0 or inf_total > 0 or zero_close > 0:
                    status = 'FAIL'
                    self.results['errors'].append(
                        f"{symbol}: nan={nan_total}, inf={inf_total}, zero_close={zero_close}"
                    )

                check_results[symbol] = {
                    'status': status,
                    'nan_count': nan_total,
                    'inf_count': inf_total,
                    'zero_close_count': zero_close,
                    'zero_volume_count': zero_volume
                }

            except Exception as e:
                self.results['errors'].append(f"{symbol} - {check_name}: {e}")
                check_results[symbol] = {'status': 'ERROR', 'error': str(e)}

        self.results['checks'][check_name] = check_results

    def _check_performance_benchmark(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> None:
        """
        CHECK 8: Benchmark — tempo load, batch gen, pico memória.
        Alvos: load <2s, batch <5s, mem <8GB
        """
        check_name = "Performance Benchmark"
        logger.info(f"[Validador] {check_name}...")

        check_results = {}
        metrics = {
            'load_total_time': 0,
            'batch_total_time': 0,
            'peak_memory_mb': 0
        }

        import tracemalloc

        for symbol in symbols:
            try:
                # LOAD BENCHMARK
                tracemalloc.start()
                t0 = time.time()

                df = self.loader.load_training_data(symbol, start_date, end_date)

                load_time = time.time() - t0
                _, peak_mem = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                load_ok = load_time < 2.0

                # BATCH BENCHMARK (primeira chamada)
                tracemalloc.start()
                t0 = time.time()

                batch_count = 0
                for X_batch, y_batch in self.loader.get_training_batches(
                    [symbol], batch_size=32
                ):
                    batch_count += 1
                    if batch_count >= 3:  # 3 batches
                        break

                batch_time = time.time() - t0
                _, batch_peak_mem = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                batch_ok = batch_time < 5.0
                mem_ok = batch_peak_mem / (1024**2) < 8192  # < 8GB

                status = 'OK'
                if not (load_ok and batch_ok and mem_ok):
                    status = 'WARNING'
                    if not load_ok:
                        self.results['warnings'].append(f"{symbol} load time: {load_time:.2f}s > 2s")
                    if not batch_ok:
                        self.results['warnings'].append(f"{symbol} batch time: {batch_time:.2f}s > 5s")
                    if not mem_ok:
                        self.results['warnings'].append(f"{symbol} peak memory: {batch_peak_mem/(1024**3):.2f}GB > 8GB")

                check_results[symbol] = {
                    'status': status,
                    'load_time_sec': f"{load_time:.3f}",
                    'load_target': "< 2s",
                    'load_ok': load_ok,
                    'batch_time_sec': f"{batch_time:.3f}",
                    'batch_target': "< 5s",
                    'batch_ok': batch_ok,
                    'peak_memory_mb': f"{batch_peak_mem/(1024**2):.1f}",
                    'memory_target': "< 8192 MB",
                    'memory_ok': mem_ok
                }

                metrics['load_total_time'] += load_time
                metrics['batch_total_time'] += batch_time
                metrics['peak_memory_mb'] = max(metrics['peak_memory_mb'], batch_peak_mem/(1024**2))

            except Exception as e:
                logger.error(f"[Validador] Benchmark error para {symbol}: {e}")
                check_results[symbol] = {'status': 'ERROR', 'error': str(e)}

        self.results['checks'][check_name] = check_results
        self.results['metrics'] = metrics


def print_validation_report(results: Dict[str, Any]) -> None:
    """Imprime relatório de validação formatado."""
    print("\n" + "="*80)
    print(f"[VALIDAÇÃO ML] Status Overall: {results['overall_status']}")
    print("="*80)

    # Checks detalhados
    for check_name, check_details in results['checks'].items():
        print(f"\n📋 {check_name}:")
        for symbol, detail in check_details.items():
            status = detail.get('status', 'UNKNOWN')
            status_icon = '✅' if status == 'OK' else '⚠️' if status == 'WARNING' else '❌' if status == 'FAIL' else '❓'
            print(f"  {status_icon} {symbol}: {status}")
            for key, value in detail.items():
                if key != 'status':
                    print(f"      {key}: {value}")

    # Warnings e Errors
    if results['warnings']:
        print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
        for w in results['warnings']:
            print(f"  - {w}")

    if results['errors']:
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for e in results['errors']:
            print(f"  - {e}")

    # Métricas
    if results['metrics']:
        print(f"\n📊 Métricas Consolidadas:")
        print(f"  Total load time: {results['metrics'].get('load_total_time', 0):.3f}s")
        print(f"  Total batch time: {results['metrics'].get('batch_total_time', 0):.3f}s")
        print(f"  Peak memory: {results['metrics'].get('peak_memory_mb', 0):.1f} MB")

    print("\n" + "="*80)


if __name__ == "__main__":
    from config.settings import DATABASE_PATH

    validator = MLValidator(DATABASE_PATH)

    # Rodar todas as 8 validações
    symbols_to_validate = ["BTCUSDT", "ETHUSDT"]  # Subset para teste rápido

    results = validator.run_all_checks(
        symbols_to_validate,
        start_date="2025-11-01",
        end_date="2026-02-20"
    )

    # Imprimir relatório
    print_validation_report(results)
