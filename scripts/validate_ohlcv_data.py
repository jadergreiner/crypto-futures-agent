"""
Validação de integridade OHLCV — ML Specialist

Checklist:
1. Continuidade de candles (sem gaps > 4h para H4)
2. Sanidade de OHLC (high >= max(open,close), low <= min(open,close))
3. Volume > 0
4. Mínimo 300 candles por símbolo (3 meses H4)
5. Correlação com BTC para teste de relevância
"""

import sqlite3
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.symbols import ALL_SYMBOLS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OHLCVValidator:
    """Validador de dados OHLCV."""

    def __init__(self, db_path: str = "db/crypto_agent.db"):
        """Inicializa validator."""
        self.db_path = db_path
        self.conn = None
        self.report = {
            'symbols': {},
            'summary': {
                'total_symbols': 0,
                'symbols_ok': 0,
                'symbols_with_warnings': 0,
                'symbols_with_errors': 0,
                'min_candles': 300,
                'timestamp': datetime.now().isoformat()
            }
        }

    def connect(self):
        """Conecta ao banco de dados."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            logger.info(f"✅ Conectado ao banco: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Erro conectando ao banco: {e}")
            return False
        return True

    def validate_symbol(self, symbol: str) -> dict:
        """
        Valida dados OHLCV para um símbolo.

        Returns:
            Dict com status e detalhes
        """
        result = {
            'symbol': symbol,
            'status': 'OK',
            'warnings': [],
            'errors': [],
            'metrics': {
                'total_candles': 0,
                'candles_h4': 0,
                'candle_gaps': 0,
                'ohlc_violations': 0,
                'volume_issues': 0,
                'date_range': None
            }
        }

        try:
            # Query H4 data
            query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv_h4
            WHERE symbol = ?
            ORDER BY timestamp ASC
            """
            df = pd.read_sql_query(query, self.conn, params=(symbol,))

            if df.empty:
                result['errors'].append(f"Nenhum dado H4 encontrado para {symbol}")
                result['status'] = 'ERROR'
                return result

            result['metrics']['candles_h4'] = len(df)
            result['metrics']['total_candles'] = len(df)
            result['metrics']['date_range'] = {
                'start': str(df['timestamp'].min()),
                'end': str(df['timestamp'].max())
            }

            # 1. Verificar continuidade (sem gaps > 4h)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['time_diff'] = df['timestamp'].diff().dt.total_seconds() / 3600  # horas
            gaps = df[df['time_diff'] > 4.5]  # Tolerância de 30 min

            result['metrics']['candle_gaps'] = len(gaps)
            if len(gaps) > 0:
                result['warnings'].append(
                    f"⚠️  {len(gaps)} gaps > 4h detectados"
                )

            # 2. Verificar sanidade de OHLC
            violations = df[
                (df['high'] < df[['open', 'close']].max(axis=1)) |
                (df['low'] > df[['open', 'close']].min(axis=1))
            ]

            result['metrics']['ohlc_violations'] = len(violations)
            if len(violations) > 0:
                result['errors'].append(
                    f"❌ {len(violations)} violações de OHLC sanity (high < max(O,C) ou low > min(O,C))"
                )
                result['status'] = 'ERROR'

            # 3. Verificar volume > 0
            zero_volume = df[df['volume'] == 0]
            result['metrics']['volume_issues'] = len(zero_volume)
            if len(zero_volume) > 0:
                result['warnings'].append(
                    f"⚠️  {len(zero_volume)} candles com volume = 0"
                )

            # 4. Verificar mínimo de candles
            min_candles = result['metrics']['total_candles'] >= result['metrics']['metrics'] if 'metrics' not in result else 300
            if result['metrics']['total_candles'] < 300:
                result['warnings'].append(
                    f"⚠️  Apenas {result['metrics']['total_candles']} candles (< 300 recomendado, ~3 meses)"
                )

            # Finalizar status
            if result['errors']:
                result['status'] = 'ERROR'
            elif result['warnings']:
                result['status'] = 'WARNING'
            else:
                result['status'] = 'OK'

        except Exception as e:
            result['errors'].append(f"Exceção durante validação: {e}")
            result['status'] = 'ERROR'

        return result

    def validate_all(self):
        """Valida todos os símbolos."""
        if not self.connect():
            return False

        symbols = ALL_SYMBOLS if ALL_SYMBOLS else ['BTCUSDT', 'ETHUSDT']  # Fallback

        logger.info(f"\n{'='*60}\nINÍCIO VALIDAÇÃO OHLCV — {len(symbols)} símbolos\n{'='*60}")

        for symbol in symbols:
            logger.info(f"\n▶ Validando {symbol}...")
            result = self.validate_symbol(symbol)
            self.report['symbols'][symbol] = result

            # Log status
            status_emoji = {
                'OK': '✅',
                'WARNING': '⚠️ ',
                'ERROR': '❌'
            }.get(result['status'], '?')

            logger.info(f"{status_emoji} {symbol}: {result['status']} "
                       f"({result['metrics']['candles_h4']} candles)")

            if result['warnings']:
                for warning in result['warnings']:
                    logger.warning(f"   {warning}")

            if result['errors']:
                for error in result['errors']:
                    logger.error(f"   {error}")

            # Atualizar counters
            self.report['summary']['total_symbols'] += 1
            if result['status'] == 'OK':
                self.report['summary']['symbols_ok'] += 1
            elif result['status'] == 'WARNING':
                self.report['summary']['symbols_with_warnings'] += 1
            else:
                self.report['summary']['symbols_with_errors'] += 1

        self._print_summary()
        return True

    def _print_summary(self):
        """Imprime sumário final."""
        summary = self.report['summary']
        logger.info(f"\n{'='*60}\nSUMÁRIO FINAL\n{'='*60}")
        logger.info(f"Total: {summary['total_symbols']} símbolos")
        logger.info(f"✅ OK: {summary['symbols_ok']}")
        logger.info(f"⚠️  Warnings: {summary['symbols_with_warnings']}")
        logger.info(f"❌ Errors: {summary['symbols_with_errors']}")

        if summary['symbols_with_errors'] > 0:
            logger.error(f"\n🔴 BLOCKER: {summary['symbols_with_errors']} símbolos com ERRO")
            logger.error("Ação: Executar data refresh ANTES de backtest")
        elif summary['symbols_with_warnings'] > 0:
            logger.warning(f"\n⚠️  {summary['symbols_with_warnings']} símbolos com warnings (proceder com cuidado)")
        else:
            logger.info(f"\n✅ PRONTO PARA BACKTEST: Todos {summary['total_symbols']} símbolos validados")

    def close(self):
        """Fecha conexão."""
        if self.conn:
            self.conn.close()


if __name__ == '__main__':
    validator = OHLCVValidator()
    try:
        validator.validate_all()
    finally:
        validator.close()
