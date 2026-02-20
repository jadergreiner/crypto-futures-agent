# Implementação dos Layers 4 e 5 do Layer Manager

## Visão Geral

Este documento descreve a implementação completa dos métodos `h4_main_decision()` (Layer 4) e `d1_trend_macro()` (Layer 5) no `LayerManager`, que são o coração do sistema de decisão do agente de trading.

## Layer 5: D1 Trend & Macro Analysis

**Frequência:** 1x/dia às 23:59 UTC (antes do Layer 4 às 00:00)

### Responsabilidades

1. **Coleta de Dados D1**
   - Busca últimos 30 dias de dados D1 para todos os símbolos
   - Calcula todos os indicadores técnicos (EMAs, RSI, MACD, ADX, etc.)

2. **Coleta de Dados Macro**
   - Fear & Greed Index (alternative.me)
   - BTC Dominance (CoinGecko)
   - DXY, Fed Rate, CPI (placeholders)

3. **Coleta de Sentimento**
   - Long/Short Ratio
   - Open Interest
   - Funding Rate
   - Top Trader Ratio

4. **Análise Multi-Timeframe**
   - Determina D1 bias: BULLISH, BEARISH ou NEUTRO
   - Determina market regime: RISK_ON, RISK_OFF ou NEUTRO
   - Calcula correlação com BTC
   - Calcula beta em relação ao BTC

5. **Armazenamento**
   - Salva em `self.d1_context[symbol]`:

     ```python
     {
         'd1_bias': str,
         'market_regime': str,
         'correlation_btc': float,
         'beta_btc': float,
         'd1_data': pd.DataFrame,
         'macro': dict,
         'sentiment': dict
     }
     ```

   - Persiste no banco: `insert_indicators()`, `insert_sentiment()`, `insert_macro()`

### Lógica de D1 Bias

Avalia 4 condições (precisa de 3+ para BULLISH ou BEARISH):

- EMA alignment score >= 4 (bullish) ou <= -4 (bearish)
- ADX > 25 (tendência forte)
- DI+ > DI- (bullish) ou DI- > DI+ (bearish)
- RSI em zona apropriada (45-75 bullish, 25-55 bearish)

### Lógica de Market Regime

Sistema de pontuação baseado em:

- Fear & Greed >= 60 → +1 RISK_ON, <= 40 → +1 RISK_OFF
- DXY change < -0.5% → +1 RISK_ON, > 0.5% → +1 RISK_OFF
- BTC dominance < 45% → +1 RISK_ON, > 55% → +1 RISK_OFF
- D1 EMA score >= 3 → +1 RISK_ON, <= -3 → +1 RISK_OFF

Resultado: maior pontuação determina o regime.

## Layer 4: H4 Main Decision

**Frequência:** A cada 4 horas (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)

### Fluxo de Execução

Para cada símbolo em `ALL_SYMBOLS`:

1. **Coleta de Dados**
   - H4: últimos 30 dias
   - H1: últimos 7 dias (para SMC)

2. **Cálculo de Indicadores**
   - H4: todos os indicadores técnicos
   - H1: estruturas SMC (swings, BOS, CHoCH, OBs, FVGs, liquidity)

3. **Recupera Contexto D1**
   - D1 bias
   - Market regime
   - Correlação/Beta BTC
   - Dados macro e sentimento

4. **Constrói Features**
   - Vetor de 104 features normalizadas
   - Armazena em `self.feature_history` para treinamento RL futuro

5. **Calcula Score de Confluência** (ver seção detalhada abaixo)

6. **Decisão de Sinal**
   - Se score >= 8: prossegue com validação
   - Se score < 8: ignora

7. **Calcula Stops e Targets** (ver seção detalhada abaixo)

8. **Valida com Risk Manager**
   - Max 3 posições simultâneas
   - Stop distance <= 3%
   - High-beta só em RISK_ON
   - Verifica correlação com posições existentes

9. **Registra Sinal**
   - Calcula position size baseado em risco
   - Ajusta size pela confluência
   - Chama `register_signal()`

10. **Re-avalia Posições Existentes** (ver seção detalhada abaixo)

11. **Persiste Dados**
    - Indicadores H4 no banco
    - Features para treinamento

### Sistema de Confluência (8 Fatores, 14 Pontos)

| Fator | Condição LONG | Condição SHORT | Pontos |
|-------|---------------|----------------|--------|
| **1. D1 Bias** | BULLISH | BEARISH | 2 |
| **2. SMC Structure** | Bullish | Bearish | 2 |
| **3. EMA Alignment** | Score >= 4 | Score <= -4 | 2 |
| **4. RSI** | 40-70 | 30-60 | 1 |
| **5. ADX** | > 25 | > 25 | 1 |
| **6. BOS** | Bullish BOS | Bearish BOS | 2 |
| **7. Funding Rate** | < threshold | > -threshold | 2 |
| **8. Market Regime** | RISK_ON | RISK_OFF | 2 |

**Total:** 14 pontos máximo por direção

**Threshold:** Score >= 8 para abrir posição

**Lógica:**

- Calcula `bullish_score` e `bearish_score` separadamente
- Se `bullish_score > bearish_score` e `bullish_score >= 8` → LONG
- Se `bearish_score > bullish_score` e `bearish_score >= 8` → SHORT
- Caso contrário → NONE (não abre posição)

### Cálculo de Stops e Targets

#### Stop Loss

**Prioridade 1: SMC Order Blocks**

- LONG: Abaixo do OB bullish mais próximo - 0.5 ATR
- SHORT: Acima do OB bearish mais próximo + 0.5 ATR

**Fallback: ATR**

- LONG: Entry - (1.5 × ATR)
- SHORT: Entry + (1.5 × ATR)

**Validação:**

- Stop distance <= 3% (rejeitado se maior)

#### Take Profit

**Prioridade 1: Liquidity Levels (SMC)**

- LONG: Próximo BSL (Buy Side Liquidity) acima do preço
- SHORT: Próximo SSL (Sell Side Liquidity) abaixo do preço

**Fallback: ATR**

- LONG: Entry + (3.0 × ATR)
- SHORT: Entry - (3.0 × ATR)

### Re-avaliação de Posições Abertas

Para cada posição aberta, calcula:

- PnL não realizado (%)
- Score de confluência atual
- D1 bias atual

**Decisões:**

1. **CLOSE** se:
   - D1 bias reverteu (LONG → BEARISH ou SHORT → BULLISH)
   - Confluência < 6/14

2. **REDUCE 50%** se:
   - Confluência < 8/14 (mas >= 6)

3. **HOLD** se:
   - Confluência >= 8/14
   - D1 bias favorável

### Validação de Risco

Rejeita sinal se:

1. **Max Posições:** `len(open_positions) >= 3`

2. **Stop Muito Largo:** `stop_distance > 3%`

3. **High-Beta Sem RISK_ON:**
   - Se beta >= 2.0 e regime != RISK_ON
   - Símbolos afetados: SOLUSDT (2.0), 0GUSDT (3.5), KAIAUSDT (2.8), AXLUSDT (2.5), NILUSDT (4.0), FOGOUSDT (3.8)

4. **Alta Correlação:**
   - Se posição existente na mesma direção
   - Ambas com correlação BTC > 0.8
   - Evita concentração de risco

## Position Sizing

1. **Calcula Risco Base:**

   ```python
   risk_capital = capital × max_risk_per_trade_pct  # 2%
   risk_per_unit = entry_price × (stop_distance_pct / 100)
   position_size = risk_capital / risk_per_unit
   ```

2. **Ajusta por Confluência:**
   - Score < 8: size = 0 (rejeitado)
   - Score 8-10: size × 0.6
   - Score >= 11: size × 1.0 (tamanho completo)

## Armazenamento de Features para RL

Cada execução do Layer 4 armazena:

- Vetor de 104 features em `self.feature_history[symbol]`
- Mantém últimas 1000 observações por símbolo
- Será usado futuramente para treinar modelo PPO

**Features incluem:**

- Preços e retornos (11)
- Distâncias EMAs (6)
- Indicadores técnicos (11)
- SMC estruturas (15)
- Volume Profile (8)
- Sentimento (12)
- Macro (8)
- Multi-timeframe (10)
- Correlações (6)
- Estado da posição (17)

## Error Handling

- **Por Símbolo:** Cada símbolo em try/except
- **Logging Detalhado:** Erros individuais não param o fluxo
- **Contadores:** Rastreia sucessos/falhas
- **Graceful Degradation:** Se sentimento falha, usa valores default

## Persistência no Banco

**Layer 5 persiste:**

- `insert_indicators()`: Indicadores D1
- `insert_sentiment()`: Dados de sentimento
- `insert_macro()`: Dados macro

**Layer 4 persiste:**

- `insert_indicators()`: Indicadores H4

**Formato de indicadores:**

```python
{
    'timestamp': int,
    'symbol': str,
    'timeframe': str,  # 'D1' ou 'H4'
    'ema_17': float,
    'ema_34': float,
    'ema_72': float,
    'ema_144': float,
    'ema_305': float,
    'ema_610': float,
    'rsi_14': float,
    'macd_line': float,
    'macd_signal': float,
    'macd_histogram': float,
    'bb_upper': float,
    'bb_middle': float,
    'bb_lower': float,
    'bb_bandwidth': float,
    'bb_percent_b': float,
    'vp_poc': float,
    'vp_vah': float,
    'vp_val': float,
    'obv': float,
    'atr_14': float,
    'adx_14': float,
    'di_plus': float,
    'di_minus': float,
}
```

## Constantes Definidas

```python
# SMC structure types
SMC_BULLISH = "bullish"
SMC_BEARISH = "bearish"

# Liquidity types
LIQUIDITY_BSL = "Buy Side Liquidity"
LIQUIDITY_SSL = "Sell Side Liquidity"

# Default capital (TODO: replace with portfolio manager)
DEFAULT_CAPITAL = 10000
```

## Testes

**17 testes abrangentes** em `tests/test_layer_integration.py`:

1. Inicialização do LayerManager
2. D1 popula contexto corretamente
3. D1 trata falhas de símbolos
4. D1 persiste no banco
5. H4 processa todos os símbolos
6. Lógica de confluência correta
7. Threshold de registro de sinais
8. Registro acima do threshold
9. Re-avaliação de posições
10. Fechamento em reversão de bias
11. Redução em confluência baixa
12. Stops com SMC Order Blocks
13. Fallback para ATR
14. Validação max posições
15. High-beta requer RISK_ON
16. H4 trata coletores ausentes
17. D1 trata coletores ausentes

**Cobertura:** 100% dos fluxos principais

**Status:** 17/17 passando (100%)

## Integração com Outros Módulos

### Collectors

- `BinanceCollector.fetch_historical()`: Dados OHLCV
- `SentimentCollector.fetch_all_sentiment()`: L/S ratio, funding, OI
- `MacroCollector.fetch_all_macro()`: Fear & Greed, dominance

### Indicators

- `TechnicalIndicators.calculate_all()`: EMAs, RSI, MACD, ADX, ATR
- `SmartMoneyConcepts.calculate_all_smc()`: Swings, BOS, OBs, FVGs
- `MultiTimeframeAnalysis.aggregate()`: D1 bias, market regime
- `FeatureEngineer.build_observation()`: Vetor de 104 features

### Risk

- `RiskManager.calculate_position_size()`: Sizing baseado em risco
- `RiskManager.calculate_stop_loss()`: Stops ATR
- `RiskManager.calculate_take_profit()`: Targets ATR
- `RiskManager.adjust_size_by_confluence()`: Ajuste por score

### Config

- `ALL_SYMBOLS`: Lista de símbolos a processar
- `RISK_PARAMS`: Parâmetros de risco (thresholds, limits)
- `SYMBOLS`: Metadata dos símbolos (beta, características)

## Próximos Passos

### Imediatos

1. ✅ Implementação completa
2. ✅ Testes abrangentes
3. ✅ Code review
4. ✅ Security scan

### Curto Prazo

1. Integrar com portfolio manager real
2. Implementar Layer 3 (H1 timing)
3. Adicionar trailing stops
4. Backtesting da estratégia

### Médio Prazo

1. Treinar modelo RL com features coletadas
2. A/B test: confluência vs RL
3. Walk-forward optimization
4. Adicionar mais símbolos

### Longo Prazo

1. Multi-agent RL (um por símbolo)
2. Adaptive learning online
3. Meta-learning para novos símbolos
4. Ensemble de estratégias

## Manutenção

### Como Ajustar Confluência

**Adicionar novo fator:**

1. Adicionar cálculo em `_calculate_confluence_score()`
2. Atualizar doc string com nova pontuação
3. Adicionar testes
4. Ajustar threshold se necessário

**Modificar pesos:**

- Editar pontos atribuídos (1, 2, etc.)
- Re-calibrar threshold (pode não ser mais 8)
- Backtesting para validar

### Como Modificar Stops

**Usar outro método SMC:**

1. Modificar `_calculate_stops_and_targets()`
2. Trocar Order Blocks por FVGs, por exemplo
3. Atualizar testes

**Ajustar multiplicadores ATR:**

1. Modificar `RISK_PARAMS['stop_loss_atr_multiplier']`
2. Modificar `RISK_PARAMS['take_profit_atr_multiplier']`

### Como Adicionar Novo Símbolo

1. Adicionar em `config/symbols.py` → `SYMBOLS`
2. Criar playbook em `playbooks/`
3. Adicionar em `playbooks/__init__.py`
4. Adicionar em `config/execution_config.py` → `AUTHORIZED_SYMBOLS`
5. Layer 4 e 5 processarão automaticamente

## Troubleshooting

### Nenhum Sinal Sendo Gerado

**Check:**

1. Score de confluência >= 8?
2. Risk validation passando?
3. High-beta em regime correto?
4. Max posições não atingido?

**Debug:**

```python
# Adicionar logs temporários em _calculate_confluence_score
logger.info(f"Bullish score: {bullish_score}, Bearish: {bearish_score}")
```

### Muitos Sinais Rejeitados

**Possíveis causas:**

1. Stop muito largo (> 3%)
2. Alta correlação entre posições
3. High-beta fora de RISK_ON
4. Max posições atingido

**Solução:**

- Revisar multiplicadores ATR
- Revisar threshold de correlação
- Ajustar `max_simultaneous_positions`

### Erro em Símbolo Específico

**Isolamento:**

- Erro é capturado por símbolo
- Outros símbolos continuam processando
- Check logs para detalhes

**Fix:**

1. Verificar se símbolo existe na exchange
2. Verificar metadados em `config/symbols.py`
3. Verificar playbook correspondente

## Referências

- **Problem Statement:** Seção "Requirements" do PR
- **Testes:** `tests/test_layer_integration.py`
- **Config:** `config/risk_params.py`, `config/symbols.py`
- **Indicators:** `indicators/technical.py`, `indicators/smc.py`
- **Risk:** `agent/risk_manager.py`
