#!/usr/bin/env python3
"""
ANÁLISE TÉCNICA REALTIME — ADAUSDT
Data: 22 FEV 2026
Integração: Binance API + Indicadores Técnicos + SMC + Sentimento
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pandas as pd
    import numpy as np
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    import ta  # Technical Analysis library
except ImportError as e:
    print(f"⚠️  Dependência faltando: {e}")
    print("Execute: pip install python-binance pandas-ta")
    sys.exit(1)

from config.settings import BINANCE_API_KEY, BINANCE_API_SECRET

class AnaliseADATecnica:
    """Análise técnica realtime de ADAUSDT"""

    def __init__(self):
        self.symbol = "ADAUSDT"
        self.client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
        self.data = {}

    def fetch_ohlcv(self, interval="4h", limit=500):
        """Buscar dados OHLCV da API Binance"""
        try:
            print(f"📊 Buscando {limit} candles de {self.symbol} em {interval}...")

            klines = self.client.get_klines(
                symbol=self.symbol,
                interval=interval,
                limit=limit
            )

            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df[['open', 'high', 'low', 'close', 'volume']] = \
                df[['open', 'high', 'low', 'close', 'volume']].astype(float)

            return df.tail(min(200, limit))  # Últimos 200 candles para análise

        except BinanceAPIException as e:
            print(f"❌ Erro API Binance: {e}")
            return None

    def calcular_indicadores(self, df):
        """Calcular indicadores técnicos"""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values

        indicadores = {}

        # RSI (Relative Strength Index)
        try:
            rsi = ta.momentum.rsi(df['close'], length=14)
            indicadores['RSI_14'] = rsi.iloc[-1]
            indicadores['RSI_overbought'] = rsi.iloc[-1] > 70
            indicadores['RSI_oversold'] = rsi.iloc[-1] < 30
        except:
            indicadores['RSI_14'] = None

        # MACD
        try:
            macd = ta.trend.macd(df['close'])
            indicadores['MACD_line'] = macd.iloc[-1, 0]
            indicadores['MACD_signal'] = macd.iloc[-1, 1]
            indicadores['MACD_histogram'] = macd.iloc[-1, 2]
            indicadores['MACD_bullish'] = indicadores['MACD_line'] > indicadores['MACD_signal']
        except:
            indicadores['MACD_line'] = None

        # Bandas de Bollinger
        try:
            bb = ta.volatility.bollinger_bands(df['close'], length=20, std=2)
            bb_high = bb.iloc[-1, 0]
            bb_mid = bb.iloc[-1, 1]
            bb_low = bb.iloc[-1, 2]
            close_last = df['close'].iloc[-1]

            indicadores['BB_upper'] = bb_high
            indicadores['BB_middle'] = bb_mid
            indicadores['BB_lower'] = bb_low
            indicadores['BB_percent_b'] = (close_last - bb_low) / (bb_high - bb_low) * 100
            indicadores['BB_squeeze'] = (bb_high - bb_low) / bb_mid < 0.1
        except:
            indicadores['BB_upper'] = None

        # ATR (Average True Range)
        try:
            atr = ta.volatility.average_true_range(high=df['high'], low=df['low'], close=df['close'], length=14)
            indicadores['ATR_14'] = atr.iloc[-1]
            indicadores['ATR_pct'] = (atr.iloc[-1] / df['close'].iloc[-1]) * 100
        except:
            indicadores['ATR_14'] = None

        # ADX (Average Directional Index)
        try:
            adx = ta.trend.adx(high=df['high'], low=df['low'], close=df['close'], length=14)
            indicadores['ADX_14'] = adx.iloc[-1]
            indicadores['ADX_trending'] = adx.iloc[-1] > 25
        except:
            indicadores['ADX_14'] = None

        # EMA (Exponential Moving Averages)
        try:
            ema_17 = ta.trend.ema(df['close'], length=17).iloc[-1]
            ema_34 = ta.trend.ema(df['close'], length=34).iloc[-1]
            ema_72 = ta.trend.ema(df['close'], length=72).iloc[-1]

            indicadores['EMA_17'] = ema_17
            indicadores['EMA_34'] = ema_34
            indicadores['EMA_72'] = ema_72
            indicadores['Close'] = df['close'].iloc[-1]

            # Preço acima de EMAs = tendência UP
            indicadores['Above_EMA_17'] = df['close'].iloc[-1] > ema_17
            indicadores['Above_EMA_34'] = df['close'].iloc[-1] > ema_34
            indicadores['Above_EMA_72'] = df['close'].iloc[-1] > ema_72
        except:
            indicadores['EMA_17'] = None

        # Volume Analysis
        try:
            volume_ma = df['volume'].rolling(20).mean().iloc[-1]
            volume_current = df['volume'].iloc[-1]
            indicadores['Volume_current'] = volume_current
            indicadores['Volume_MA20'] = volume_ma
            indicadores['Volume_surge'] = volume_current > volume_ma * 1.5
        except:
            indicadores['Volume_current'] = None

        return indicadores

    def analisar_estrutura_smc(self, df):
        """Análise Simple Smart Money Concepts (ordem blocks, liquidities)"""
        smc = {}

        # Identificar swing highs/lows (extremos locais)
        try:
            highs = df['high'].values
            lows = df['low'].values

            # Swing high (3 candles: anterior < atual > posterior)
            swing_highs = []
            for i in range(1, len(highs) - 1):
                if highs[i-1] < highs[i] > highs[i+1]:
                    swing_highs.append((i, highs[i]))

            # Swing low
            swing_lows = []
            for i in range(1, len(lows) - 1):
                if lows[i-1] > lows[i] < lows[i+1]:
                    swing_lows.append((i, lows[i]))

            smc['swing_highs'] = swing_highs[-3:] if swing_highs else []
            smc['swing_lows'] = swing_lows[-3:] if swing_lows else []

            # Estrutura de mercado (UPtrend, DNtrend, Range)
            if swing_highs and swing_lows:
                last_high = swing_highs[-1][1]
                last_low = swing_lows[-1][1]
                current_price = df['close'].iloc[-1]

                if current_price > last_high:
                    smc['market_structure'] = '📈 UPTREND (Higher Highs & Highs)'
                elif current_price < last_low:
                    smc['market_structure'] = '📉 DOWNTREND (Lower Lows & Lows)'
                else:
                    smc['market_structure'] = '↔️  RANGE (Consolidation)'
        except Exception as e:
            smc['market_structure'] = f'⚠️  Erro: {str(e)}'

        return smc

    def fetch_sentimento(self):
        """Buscar dados de sentimento (funding rate, open interest)"""
        sentimento = {}

        try:
            # Funding Rate
            funding = self.client.futures_funding_rate(symbol=self.symbol)
            if funding:
                funding_rate = float(funding[-1]['fundingRate'])
                sentimento['funding_rate'] = funding_rate * 100  # em %

                if funding_rate > 0.0005:
                    sentimento['funding_bias'] = '📈 BULLISH (Longos pagando)'
                elif funding_rate < -0.0005:
                    sentimento['funding_bias'] = '📉 BEARISH (Shorts pagando)'
                else:
                    sentimento['funding_bias'] = '↔️  NEUTRO'
        except Exception as e:
            sentimento['funding_rate'] = f"⚠️  Erro: {e}"

        try:
            # Open Interest
            ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
            if ticker:
                sentimento['open_interest'] = ticker.get('openInterest', 'N/A')
        except:
            sentimento['open_interest'] = "N/A"

        return sentimento

    def gerar_sinal(self, indicators, smc, sentimento):
        """Gerar sinal de operação baseado em análise técnica"""
        sinal = {'direction': None, 'força': 0, 'confiança': 0, 'motivos': []}

        # Critérios LONG
        criterios_long = 0
        if indicators.get('RSI_14') and 30 < indicators['RSI_14'] < 70:
            criterios_long += 1
            sinal['motivos'].append("✅ RSI em zona neutra")

        if indicators.get('MACD_bullish', False):
            criterios_long += 1
            sinal['motivos'].append("✅ MACD bullish")

        if indicators.get('Above_EMA_17', False):
            criterios_long += 1
            sinal['motivos'].append("✅ Preço acima EMA-17")

        if indicators.get('Above_EMA_34', False):
            criterios_long += 1
            sinal['motivos'].append("✅ Preço acima EMA-34")

        if indicators.get('ADX_trending', False):
            criterios_long += 1
            sinal['motivos'].append("✅ Tendência estabelecida (ADX > 25)")

        if indicators.get('Volume_surge', False):
            criterios_long += 0.5
            sinal['motivos'].append("✅ Volume surge detectado")

        if "UPTREND" in smc.get('market_structure', ''):
            criterios_long += 1.5
            sinal['motivos'].append("✅ Estrutura SMC em UPTREND")

        # Rankeamento
        if criterios_long >= 4:
            sinal['direction'] = 'LONG 🟢'
            sinal['força'] = 'FORTE'
            sinal['confiança'] = 85
        elif criterios_long >= 2.5:
            sinal['direction'] = 'LONG 🟢'
            sinal['força'] = 'MÉDIA'
            sinal['confiança'] = 65
        elif criterios_long >= 1:
            sinal['direction'] = 'LONG 🟢'
            sinal['força'] = 'FRACA'
            sinal['confiança'] = 45
        else:
            sinal['direction'] = 'NEUTRO ⚪ / SHORT 🔴'
            sinal['força'] = 'FRACA'
            sinal['confiança'] = 50

        return sinal

    def executar(self):
        """Executar análise completa"""
        print("\n" + "="*70)
        print("🤖 ANÁLISE TÉCNICA REALTIME — ADAUSDT")
        print(f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S UTC')}")
        print("="*70 + "\n")

        # Buscar dados
        df = self.fetch_ohlcv(interval="4h", limit=200)
        if df is None or df.empty:
            print("❌ Não foi possível buscar dados")
            return

        # Calcular indicadores
        print("\n📈 INDICADORES TÉCNICOS")
        print("-" * 70)
        indicators = self.calcular_indicadores(df)

        print(f"  Preço Atual: ${indicators.get('Close', 'N/A'):.4f}")
        print(f"  RSI(14):     {indicators.get('RSI_14', 'N/A'):.2f} {'(Overbought 🔴)' if indicators.get('RSI_overbought') else '(Oversold 🟢)' if indicators.get('RSI_oversold') else ''}")
        print(f"  MACD Line:   {indicators.get('MACD_line', 'N/A'):.6f} {'🟢 BULLISH' if indicators.get('MACD_bullish') else '🔴 BEARISH'}")
        print(f"  ADX(14):     {indicators.get('ADX_14', 'N/A'):.2f} {'📈 TRENDING' if indicators.get('ADX_trending') else '↔️  RANGE'}")
        print(f"  ATR(14):     {indicators.get('ATR_14', 'N/A'):.4f} ({indicators.get('ATR_pct', 'N/A'):.2f}%)")

        print(f"\n  EMAs:")
        print(f"    EMA-17: ${indicators.get('EMA_17', 'N/A'):.4f} {('🟢 Acima' if indicators.get('Above_EMA_17') else '🔴 Abaixo')}")
        print(f"    EMA-34: ${indicators.get('EMA_34', 'N/A'):.4f} {('🟢 Acima' if indicators.get('Above_EMA_34') else '🔴 Abaixo')}")
        print(f"    EMA-72: ${indicators.get('EMA_72', 'N/A'):.4f} {('🟢 Acima' if indicators.get('Above_EMA_72') else '🔴 Abaixo')}")

        print(f"\n  Bollinger Bands: {indicators.get('BB_percent_b', 'N/A'):.1f}% {'(Squeeze 📉)' if indicators.get('BB_squeeze') else ''}")
        print(f"  Volume: {indicators.get('Volume_current', 'N/A'):.0f} vs MA20: {indicators.get('Volume_MA20', 'N/A'):.0f} {'⬆️  SURGE' if indicators.get('Volume_surge') else ''}")

        # Análise SMC
        print("\n🔷 SMART MONEY CONCEPTS (SMC)")
        print("-" * 70)
        smc = self.analisar_estrutura_smc(df)
        print(f"  Estrutura: {smc.get('market_structure', 'N/A')}")
        if smc.get('swing_highs'):
            print(f"  Swing Highs: {[f'${h[1]:.4f}' for h in smc['swing_highs']]}")
        if smc.get('swing_lows'):
            print(f"  Swing Lows:  {[f'${l[1]:.4f}' for l in smc['swing_lows']]}")

        # Sentimento
        print("\n💭 SENTIMENTO DE MERCADO")
        print("-" * 70)
        sentimento = self.fetch_sentimento()
        print(f"  Funding Rate: {sentimento.get('funding_rate', 'N/A')}")
        print(f"  Bias: {sentimento.get('funding_bias', 'N/A')}")
        print(f"  Open Interest: {sentimento.get('open_interest', 'N/A')}")

        # Gerar Sinal
        print("\n🎯 SINAL DE OPERAÇÃO")
        print("-" * 70)
        sinal = self.gerar_sinal(indicators, smc, sentimento)
        print(f"  Direção: {sinal['direction']}")
        print(f"  Força:   {sinal['força']}")
        print(f"  Confiança: {sinal['confiança']}%")
        print(f"\n  Motivos:")
        for motivo in sinal['motivos']:
            print(f"    {motivo}")

        if not sinal['motivos']:
            print("    ⚠️  Nenhum critério atendido - AGUARDAR CONFIRMAÇÃO")

        print("\n" + "="*70)
        print("✅ Análise concluída")
        print("="*70 + "\n")

        return {
            'timestamp': datetime.now().isoformat(),
            'symbol': self.symbol,
            'price': indicators.get('Close'),
            'indicators': indicators,
            'smc': smc,
            'sentimento': sentimento,
            'sinal': sinal
        }

if __name__ == "__main__":
    analisador = AnaliseADATecnica()
    resultado = analisador.executar()
