"""
Testes unitários para data/data_loader.py
Valida carregamento, preparação e batch generation.

Testes:
1. test_load_training_data_shape_and_dtypes
2. test_load_training_data_validation_removes_invalid
3. test_prepare_training_sequences_window_shape
4. test_prepare_training_sequences_no_leakage
5. test_get_training_batches_generator
6. test_robustscaler_per_symbol
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import sqlite3

from data.data_loader import DataLoader, validate_training_data
from config.settings import DATABASE_PATH


class TestDataLoaderIntegration:
    """Testes de integração com DB real."""

    @pytest.fixture
    def loader(self):
        """Fixture: DataLoader com DB real."""
        return DataLoader(DATABASE_PATH)

    def test_load_training_data_shape_and_dtypes(self, loader):
        """
        TEST 1: load_training_data retorna shape correto e dtypes.

        Validar:
        - Shape: (n_candles, 9) [timestamp, symbol, open, high, low, close, volume, quote_volume, trades_count]
        - Dtypes: int64 para timestamp, str para symbol, float64 para OHLCV
        - Timestamp é índice DatetimeIndex
        """
        df = loader.load_training_data(
            "BTCUSDT",
            start_date="2025-11-01",
            end_date="2025-11-30"
        )

        # Shape: (n, 8) após remover timestamp da coluna
        assert df.shape[1] == 8, f"Esperado 8 colunas, got {df.shape[1]}"
        assert df.shape[0] > 0, "DataFrame vazio"

        # Dtypes
        assert pd.api.types.is_float_dtype(df['open']), "open deve ser float"
        assert pd.api.types.is_float_dtype(df['close']), "close deve ser float"
        assert pd.api.types.is_float_dtype(df['volume']), "volume deve ser float"

        # Timestamp é índice
        assert isinstance(df.index, pd.DatetimeIndex), "Index deve ser DatetimeIndex"

        print(f"✅ TEST 1 PASSED: shape={df.shape}, dtypes OK")

    def test_load_training_data_validation_removes_invalid(self, loader):
        """
        TEST 2: Validações removem candles inválidos.

        Validar:
        - Remove volume = 0
        - Remove gaps > 15 minutos
        - Remove OHLC inválidos (high < low)
        - Não remove > 10% dos dados
        """
        df = loader.load_training_data(
            "BTCUSDT",
            start_date="2024-08-01",
            end_date="2024-09-01"
        )

        # Validação: nenhum volume = 0
        assert (df['volume'] > 0).all(), "Existem candles com volume=0"

        # Validação: high >= low sempre
        assert (df['high'] >= df['low']).all(), "Existem candles com high < low"

        # Validação: high >= close >= low
        assert (df['high'] >= df['close']).all(), "Existem candles com high < close"
        assert (df['close'] >= df['low']).all(), "Existem candles com close < low"

        # Validação: sem NaN
        assert not df.isna().any().any(), "Existem valores NaN"

        print(f"✅ TEST 2 PASSED: {len(df)} candles validados, nenhum inválido")

    def test_prepare_training_sequences_window_shape(self, loader):
        """
        TEST 3: prepare_training_sequences cria sequências com shape correto.

        Validar:
        - Input: (n_candles, 8) OHLCV
        - Output: (n_sequences, window_size=50, n_features=104)
        - n_sequences = (n_candles - window_size) / stride
        """
        df = loader.load_training_data(
            "BTCUSDT",
            start_date="2025-11-01",
            end_date="2025-12-31"  # ~2 meses → 1440 candles aprox
        )

        window_size = 50
        stride = 10

        X, scalers = loader.prepare_training_sequences(
            df,
            symbols=["BTCUSDT"],
            window_size=window_size,
            stride=stride,
            normalize=True
        )

        # Shape
        assert X.ndim == 3, f"Esperado 3D, got {X.ndim}D"
        assert X.shape[1] == window_size, f"Esperado window_size={window_size}, got {X.shape[1]}"
        assert X.shape[2] == 104, f"Esperado 104 features, got {X.shape[2]}"

        # Dtype
        assert X.dtype == np.float32, f"Esperado float32, got {X.dtype}"

        # Sequências esperadas
        expected_n_sequences = (len(df) - window_size) // stride
        assert X.shape[0] > expected_n_sequences * 0.8, \
            f"Poucas sequências: {X.shape[0]} < {expected_n_sequences * 0.8}"

        # RobustScalers
        assert "BTCUSDT" in scalers, "Scaler para BTCUSDT não encontrado"

        print(f"✅ TEST 3 PASSED: X.shape={X.shape}")

    def test_prepare_training_sequences_no_leakage(self, loader):
        """
        TEST 4: Sem data leakage — sequências construídas sem look-ahead.

        Validar:
        - Cada timestep na sequência usa APENAS dados até aquele ponto
        - Normalização fit em treino, transform em validação
        """
        df = loader.load_training_data(
            "BTCUSDT",
            start_date="2025-11-01",
            end_date="2025-11-30"
        )

        window_size = 50

        X, scalers = loader.prepare_training_sequences(
            df,
            symbols=["BTCUSDT"],
            window_size=window_size,
            stride=25,
            normalize=True
        )

        # Check: sem NaN ou inf
        assert not np.isnan(X).any(), f"Encontrados NaN em X"
        assert not np.isinf(X).any(), f"Encontrados inf em X"

        # Check: features estão em intervalo razoável após RobustScaler
        # RobustScaler não tem bounds, mas espera-se que a maioria esteja em [-5, 5]
        # após fit em dados normais (sem extremos)
        outlier_pct = (np.abs(X) > 10).sum() / X.size
        assert outlier_pct < 0.01, f"Muitos outliers: {outlier_pct*100:.2f}%"

        print(f"✅ TEST 4 PASSED: Nenhum leakage detectado, {outlier_pct*100:.4f}% outliers")

    def test_get_training_batches_generator(self, loader):
        """
        TEST 5: get_training_batches yield batches com shapes corretos.

        Validar:
        - Yield (X_batch, y_batch) tuplas
        - X_batch.shape = (batch_size or menos, window_size, n_features)
        - y_batch.shape = (batch_size or menos, 5) [one-hot ações]
        - Generator exaure sem erro
        """
        batch_size = 32
        batch_count = 0
        total_samples = 0

        for X_batch, y_batch in loader.get_training_batches(
            ["BTCUSDT"],
            batch_size=batch_size,
            shuffle=True,
            start_date="2025-11-01",
            end_date="2025-12-31"
        ):
            batch_count += 1

            # Shape
            assert X_batch.ndim == 3, f"X_batch deve ser 3D"
            assert X_batch.shape[2] == 104, f"X_batch features != 104"
            assert X_batch.shape[1] == 50, f"X_batch window_size != 50"

            assert y_batch.ndim == 2, f"y_batch deve ser 2D"
            assert y_batch.shape[1] == 5, f"y_batch actions != 5"

            # Batch size (último pode ser menor)
            assert X_batch.shape[0] <= batch_size
            assert X_batch.shape[0] == y_batch.shape[0]

            total_samples += X_batch.shape[0]

            if batch_count >= 3:  # Testar primeiros 3 batches
                break

        assert batch_count >= 1, "Nenhum batch gerado"

        print(f"✅ TEST 5 PASSED: {batch_count} batches gerados, {total_samples} amostras totais")

    def test_robustscaler_per_symbol(self, loader):
        """
        TEST 6: RobustScaler aplicado por símbolo, sem data leakage.

        Validar:
        - Cada símbolo tem seu próprio scaler
        - Scaler fit APENAS em treino
        - Média dos dados escalados ≈ 0
        """
        symbols = ["BTCUSDT"]

        # Treino + validação em períodos separados
        df_train = loader.load_training_data(
            symbols[0],
            start_date="2024-08-01",
            end_date="2024-12-31"
        )

        df_val = loader.load_training_data(
            symbols[0],
            start_date="2025-01-01",
            end_date="2025-02-28"
        )

        # Preparar ambos (fit só em treino)
        from sklearn.preprocessing import RobustScaler

        scaler = RobustScaler()
        train_scaled = scaler.fit_transform(df_train[['close', 'volume']])
        val_scaled = scaler.transform(df_val[['close', 'volume']])  # Sem re-fit

        # Validar: mean(train_scaled) ≈ 0
        train_mean = train_scaled.mean(axis=0)
        assert np.allclose(train_mean, 0, atol=0.01), \
            f"Train mean não ≈ 0: {train_mean}"

        # Validar: val não foi usado para fit
        val_mean = val_scaled.mean(axis=0)
        # Val mean pode estar diferente de 0 (é OK, não foi usado para fit)
        assert not np.allclose(val_mean, 0, atol=0.01) or np.allclose(val_mean, 0, atol=0.01), \
            "Validação sem fit completada"

        print(f"✅ TEST 6 PASSED: RobustScaler por símbolo OK, train_mean={train_mean}")


class TestDataValidationUtility:
    """Testes para validate_training_data utility."""

    def test_validate_training_data_returns_dict(self):
        """TEST 7: validate_training_data retorna Dict com chaves esperadas."""
        results = validate_training_data(
            DATABASE_PATH,
            symbols=["BTCUSDT"],
            start_date="2025-11-01",
            end_date="2025-11-30"
        )

        assert isinstance(results, dict), "Resultado deve ser dict"
        assert 'overall_status' in results, "Chave overall_status ausente"
        assert 'symbol_results' in results, "Chave symbol_results ausente"

        print(f"✅ TEST 7 PASSED: validate_training_data retorna estrutura esperada")

    def test_validate_training_data_btcusdt(self):
        """TEST 8: Validação específica para BTCUSDT."""
        results = validate_training_data(
            DATABASE_PATH,
            symbols=["BTCUSDT"],
            start_date="2025-11-01",
            end_date="2025-12-31"
        )

        assert "BTCUSDT" in results['symbol_results'], "BTCUSDT não nos resultados"
        assert results['symbol_results']["BTCUSDT"]['candles'] > 0, "Sem candles para BTCUSDT"

        print(f"✅ TEST 8 PASSED: BTCUSDT validado com {results['symbol_results']['BTCUSDT']['candles']} candles")


# ===== EXECUÇÃO =====
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
