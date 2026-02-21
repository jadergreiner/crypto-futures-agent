# SIMPLIFICAÇÃO DE LOGS - CONSOLIDADO DE CICLO

**Data**: 2026-02-21 02:04  
**Status**: ✅ IMPLEMENTADO E TESTADO

---

## O QUE FOI IMPLEMENTADO

### 1. **Consolidado Visual de Ciclo (5 minutos)**

Novo módulo `monitoring/cycle_summary.py` que gera um resumo consolidado de TODOS os símbolos monitorados a cada ciclo de 5 minutos.

**Formato da tela:**
```
[CICLO] MONITORAMENTO - 2026-02-21 02:04:30
===============================================================================================================
SYMBOL       PRICE        CONF   DIR   REGIME SIGNAL POSITION                                           TRAINING
---------------------------------------------------------------------------------------------------------------
ETHUSDT      3500.123456  8/14   LONG  ALTA   SHORT  [-]UP 0.1@3400.0 | PnL:+16.67$              15%
BTCUSDT      45000.500000 10/14  LONG  ALTA   LONG   [+]UP 0.05@45000.0 | PnL:+100.00$            45%
SOLUSDT      120.456789   4/14   NONE  NEUTRO NA     NA                                           0%
... (66 símbolos)
===============================================================================================================
```

**Colunas:**
| Coluna | Descrição | Origem |
|--------|-----------|--------|
| SYMBOL | Símbolo do par | config/symbols.py |
| PRICE | Cotação atual da moeda | market_data (DB) |
| CONF | SMC Confluence (0-14) | indicator_cache (DB) |
| DIR | Direção (LONG/SHORT/NONE) | indicator_cache (DB) |
| REGIME | Regime de mercado (ALTA/BAIXA/NEUTRO) | indicator_cache (DB) |
| SIGNAL | Último sinal gerado | trade_signals (DB) |
| POSITION | Posição aberta com PnL | positions (DB) |
| TRAINING | % de win rate histórico | positions (DB) |

---

### 2. **Integração Automática no Monitor**

O consolidado agora aparece **automaticamente** a cada 5 minutos quando o sistema está em modo **OPERACAO PADRAO (LIVE INTEGRADO)**.

**Fluxo:**
```
[1] Sistema monitora 66 símbolos (5 min = 300s)
    ↓
[2] Coleta cotações + indicadores + sinais
    ↓
[3] Fim do ciclo → print_cycle_summary() é chamada
    ↓
[4] Tela mostra consolidado de TODOS os símbolos
    ↓
[5] Aguarda 5 min → Próximo ciclo
```

**Arquivo modificado:**
- `monitoring/position_monitor.py` (linha ~2920)
  - Adicionado chamada automática ao consolidado no final de cada `monitor_cycle()`

---

### 3. **Script Standalone**

Script `resumo_ciclo.py` para visualizar o consolidado sob demanda a qualquer momento:

```bash
python resumo_ciclo.py
```

Útil para:
- Checar status atual quando o sistema está rodando
- Ver foto de mercado on-demand
- Filtrar apenas alguns símbolos (edit do script)

---

### 4. **Menu Integrado**

Menu atualizado (`menu.py`) agora tem **13 opções** (era 12):

```
  --- Status e Monitoramento ---
  3. Status Rápido (posições abertas + PnL)
  4. Posições Detalhadas
  5. Status em Tempo Real (completo)
  6. Consolidado de Ciclo (de 5 minutos) ← NOVO
  
  --- Opcoes Avancadas ---
  7. Monitorar Posicoes Abertas (verbose)
  8. Executar Backtest
  ... etc
```

**Via menu:**
```bash
./iniciar.bat
# Selecionar Opção 6 → Mostra consolidado de ciclo
```

---

## LOGS SIMPLIFICADOS

### Antes (MUITO VERBOSO):
```
INFO | H4: ETHUSDT - Fetching 180 days of H4 data
INFO | H4: ETHUSDT - Fetched 753 candles for H4
INFO | H4: ETHUSDT - Processing SMC analysis
INFO | H4: ETHUSDT - SMC confluence: 8/14
INFO | H4: ETHUSDT - Market direction: LONG
INFO | H4: ETHUSDT - Regime: ALTA
INFO | H4: ETHUSDT - Checking for signals
... (x66 símbolos)
```

### Depois (SIMPLIFICADO):
```
[RESUMO] CICLO #1:
  • ETHUSDT LONG: HOLD (risco: 8.0/10, PnL: +5.23%)
  • BTCUSDT LONG: CLOSE (risco: 10.0/10, PnL: -2.15%)
  ... (resume curto)

[CICLO] MONITORAMENTO - 2026-02-21 02:04:30
ETHUSDT      3500.123456  8/14   LONG  ALTA   SHORT  [-]UP 0.1@3400.0 | PnL:+16.67$      15%
BTCUSDT      45000.500000 10/14  LONG  ALTA   LONG   [+]UP 0.05@45000.0 | PnL:+100.00$   45%
... (consolidado visual)
```

**Operações verbosas (INFO → DEBUG):**
- `data/collector.py`: Fetch candle operations
- `indicators/smc.py`: SMC analysis calculations
- `core/layer_manager.py`: Processing per-symbol

**Resultado:** Tela visualiza CONSOLIDADO, não detalhes por símbolo

---

## COMO USAR

### Opção 1: Automático (Durante OPERACAO PADRAO)
```bash
./iniciar.bat
# Selecionar: 2 - OPERACAO PADRAO
# Sistema inicia e mostra consolidado a cada 5 min
```

### Opção 2: Under Demand (Anytime)
```bash
python resumo_ciclo.py
# Mostra consolidado instantaneamente
```

### Opção 3: Via Menu
```bash
./iniciar.bat
# Selecionar: 6 - Consolidado de Ciclo
```

---

## DADOS DA TELA

Quando o sistema tiver dados de operação em andamento, mostrará valores reais:

```
ETHUSDT      3501.567890  10/14  LONG  ALTA   SHORT  [-]DN 0.05@3500.0 | PnL:-10.50$    25%
                        ^         ↓     ↓      ↓     ↓
                    Última    SMC   Dire- Regime Sinal Posição  Win
                    cotação   conf  ção           aberta       Rate
                    (Binance) (DB)  (DB)  (DB)   (DB)  (DB)     (%)
```

**Preenchimento:**
- PRICE: Atualizado a cada coleta (polling contínuo)
- CONF/DIR/REGIME: Atualizado a cada ciclo de análise (5 min)
- SIGNAL: Atualizado quando novo sinal gerado (variável)
- POSITION: Atualizado quando posição abre/fecha (variável)
- TRAINING: Atualizado ao fim de cada operação fechada (variável)

---

## EXEMPLO COM DADOS REAIS

(Será mostrado assim quando sistema tiver posições em operação)

```
[CICLO] MONITORAMENTO - 2026-02-21 03:15:22
===============================================================================================================
SYMBOL       PRICE        CONF   DIR   REGIME SIGNAL POSITION                                           TRAINING
---------------------------------------------------------------------------------------------------------------
0GUSDT       0.213456     2/14   NONE  BAIXO  NA     NA                                               0%
BNBUSDT      615.123456   7/14   LONG  ALTA   LONG   [+]UP 0.008@615.0 | PnL:+24.50$              42%
BTCUSDT      45234.567890 11/14  LONG  ALTA   LONG   [+]UP 0.001@45000.0 | PnL:+234.57$           58%
ETHUSDT      3567.890123  8/14   LONG  ALTA   SHORT  [-]DN 0.03@3500.0 | PnL:-5.60$               35%
... mais 62 símbolos ...
===============================================================================================================
```

---

## CHECKLIST DE VALIDAÇÃO

- [x] Módulo `monitoring/cycle_summary.py` criado
- [x] Trata erros quando DB vazio (NA para valores)
- [x] Encoding UTF-8 / ASCII-only para Windows compatibility
- [x] Integrado em `position_monitor.py` (auto-executa a cada ciclo)
- [x] Menu `menu.py` atualizado (opção 6)
- [x] Script `resumo_ciclo.py` standalone criado e testado
- [x] Formatação clara e legível
- [x] Sem emojis problemáticos (Windows-friendly)
- [x] Documenta todas as 5 informações solicitadas:
  - [x] 1. Atualização de cotações (PRICE)
  - [x] 2. Cálculo de indicadores (CONF, DIR, REGIME)
  - [x] 3. Sinais gerados (SIGNAL)
  - [x] 4. Dados consolidados por símbolo (POSITION, TRAINING)
  - [x] 5. Padrão uniforme (uma linha por símbolo)

---

## PRÓXIMOS PASSOS

Quando o sistema rodando em **OPERACAO PADRAO**:
1. A cada 5 minutos, tela exibe consolidado de TODOS os 66 símbolos
2. Operador vê em tempo real:
   - Quais posições foram abertas / fechadas
   - Sinais gerados (SIGNAL column)
   - PnL de cada posição
   - Taxa de treino (win rate)
3. Pode pressionar Ctrl+C se precisar interromper
4. Ou abrir outro terminal exe `python resumo_ciclo.py` anytime

---

## NOTAS TÉCNICAS

**Resiliência:**
- Se banco de dados vazio → mostra "NA"
- Se posição sem dados → mostra "NA"
- Se erro em qualquer coluna → try/except captura e mostra "NA"

**Performance:**
- Consolidado é leitura pura (SELECT) → rápido
- Executado APÓS análise completa → não bloqueia decisões
- Sem lock, sem contentions

**Encoding:**
- Windows PowerShell: UTF-8 via chcp 65001
- Linux/Mac: UTF-8 nativo
- Fallback: ASCII-only quando problemas (nomes de colunas, símbolos)

---

## RESUMO

✅ **Tela de logs simplificada**: Consolidado visual ao invés de linhas verbosas por símbolo
✅ **A cada 5 minutos**: Automático durante OPERACAO PADRAO  
✅ **Todas as informações solicitadas**: Cotação, indicadores, sinais, posições, treinamento  
✅ **Padrão uniforme**: Uma linha cleanly formatada por símbolo  
✅ **Acesso fácil**: Menu opção 6 + script `resumo_ciclo.py` standalone

**Sistema pronto para operação com visibilidade clara!**
