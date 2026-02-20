# Integração de Dados Reais — Sistema de Reunião

## 📋 Visão Geral

O sistema de reunião (Head Financeiro × Operador Autônomo) agora integra **dados reais** de operações, logs e análises dinâmicas. Anteriormente, usava exemplos hardcoded; agora carrega histórico atual do banco de dados e logs operacionais.

## 🔄 Fluxo de Dados

```
iniciar.bat (opera o agente)
    ↓
db/crypto_futures.db (trade_log, execution_log)
    ↓
scripts/disparador_reuniao.py
    ↓
ExecutorReuniao._obter_trades_periodo()       [lê trade_log]
ExecutorReuniao._analisar_logs_operacionais() [parseia logs/]
ExecutorReuniao._calcular_metricas_trades()   [calcula PnL, Sharpe, etc]
    ↓
_gerar_feedbacks_dinamicos() [identifica força/fraqueza/oportunidade]
_gerar_acoes_dinamicas()     [cria plano baseado em problemas reais]
    ↓
Relatório markdown com dados atualizados
```

## 📊 Dados Carregados

### De `db/crypto_futures.db`

#### Tabela: `trade_log`
- **symbol**: Par operado (BTCUSDT, ETHUSDT, etc)
- **direcao**: LONG ou SHORT
- **entry_price**: Preço de entrada
- **exit_price**: Preço de saída (NULL se aberto)
- **pnl_usdt**: Lucro/prejuízo em dólar
- **pnl_pct**: Retorno percentual
- **timestamp_entrada**: Quando abriu
- **timestamp_saida**: Quando fechou

**Consulta realizada:**
```python
trades = self.db_trades.get_trades(start_time=data_inicio)
```
Padrão: últimas 7 dias (configurável)

#### Tabela: `execution_log`
- **symbol**: Par executado
- **action**: CLOSE, REDUCE_50, etc
- **executed**: 1 se sucesso, 0 se falhou
- **timestamp**: Quando executou
- **reason**: Por que foi feita

**Consulta realizada:**
```python
execucoes = self.db_trades.get_execution_log(start_time=data_inicio, executed_only=True)
```

### De `logs/`

#### Arquivos analisados
- `logs/live_trading_YYYYMMDD.log`
- `logs/paper_trading_YYYYMMDD.log`
- `logs/app_YYYYMMDD.log`
- `logs/errors_YYYYMMDD.log`

**Padrões procurados:**
- ERROR/error → Erros críticos
- WARNING/warning → Avisos de sistema
- FAILED/failed → Falhas de execução

**Função:**
```python
logs_analise = self._analisar_logs_operacionais(dias=1)
```
Retorna: top 3 erros, avisos, falhas + padrões identificados

## 📈 Métricas Calculadas

### Globais

Baseadas em trades fechados do período:

- **PnL (USDT)**: Soma de `pnl_usdt` de todos trades
- **PnL (%)**: `(PnL Total / 10000) * 100` (assumindo account $10k)
- **Sharpe Ratio**: `(média PnL / desvio_padrão) * sqrt(252 / num_trades)`
- **Max Drawdown**: Drawdown máximo observado no período
- **Taxa Acertos**: % de trades com `pnl_usdt > 0`
- **Num Operações**: Total de trades fechados

### Por Par

Top 5 pares por PnL:
- **Par**: BTCUSDT, ETHUSDT, etc
- **PnL**: Lucro total do par
- **Operações**: Número de trades
- **Taxa Acerto**: % ganho naquele par

## 🧠 Geração de Feedbacks (3+3+3)

### Quando há dados reais

**FORÇA** (3 itens): O que funcionou bem
1. Trade com maior lucro é mencionado como força
2. Zero erros em logs → "Sistema rodou estável"
3. Disciplina em número de pares operados

**FRAQUEZA** (3 itens): O que não funcionou
1. Trade com maior prejuízo é nota como problema de SL/TP
2. Presença de erros em logs → gera feedback específico
3. Taxa de acerto baixa sugere MIN_ENTRY_SCORE fraco

**OPORTUNIDADE** (3 itens): Melhorias dinâmicas
1. H4 como filtro de tendência (múltiplos timeframes)
2. Zona cinzenta de score 4.8-5.2 (capture with risk mgmt)
3. Retrainagem rolling window (7 dias)

### Fallback (sem dados)

Se não houver trades, usa exemplos pré-definidos como antes. Permite testes sem produção.

## 🚀 Geração de Ações (6 itens)

### Quando há dados reais

Ações variam conforme problemas identificados:

**CRÍTICA 1**: Taxa acerto < 50%
→ "Aumentar MIN_ENTRY_SCORE"

**CRÍTICA 2**: Muitos trades com prejuízo
→ "Bloquear escalação após reject"

**ALTA 1-3**: Slots insuficientes, posições inativas, múltiplos timeframes
→ Baseadas em dados de pares e frequência

**MÉDIA**: Retrainagem rolling window

### Fallback

Se sem dados, usa 6 ações pré-definidas como antes.

## 🔧 Como Usar

### Teste com dados reais

1. **Operar o agente normalmente** (iniciar.bat opção 1-3)
   - Sistema gera trades, executa ordens
   - Popula `db/crypto_futures.db` com histórico
   - Cria logs em `logs/`

2. **Disparar reunião**
   ```bash
   python scripts/disparador_reuniao.py --contexto "Contexto do mercado"
   ```
   - Carrega dados do DB (últimas 7 dias)
   - Analisa logs (últimas 24h)
   - Gera feedbacks e ações dinamicamente
   - Exporta `docs/reuniao_YYYY_WW_semWW.md`

### Teste sem dados reais (debug)

Se não há trades em DB (primeira viagem), sistema:
1. Não falha ❌
2. Usa feedbacks de exemplo em vez de dinâmicos
3. Usa ações padrão em vez de baseadas em problemas
4. Continua gerando 30 diálogos + 9 feedbacks + 6 ações

## 📝 Configurações

### Período de análise

**Padrão:**
```python
trades = self._obter_trades_periodo(dias=7)      # Últimos 7 dias
logs_analise = self._analisar_logs_operacionais(dias=1)  # Últimas 24h
```

**Modificar:**
```python
trades = self._obter_trades_periodo(dias=30)     # 30 dias
```

### Número de pares analisados

```python
top_pares = self._obter_pares_mais_operados(trades, top_n=2)
```
Top 2 pares aparecem no relatório. Modificar `top_n=5` para top 5.

### Limite de erros em logs

```python
erros = erros[:3]  # Top 3 erros
```
Modificar para `:5` para top 5 erros.

## 🐛 Debug

### Logs produzidos

Arquivo: `logs/reuniao_execucao.log`

Exemplo:
```
2026-02-20 20:24:29,206 [INFO] Carregados 0 trades do período
2026-02-20 20:24:29,206 [INFO] Análise de logs: 0 erros, 0 avisos, 0 falhas
2026-02-20 20:24:29,207 [INFO] Métricas carregadas (dados reais): PnL=0.00 USDT, Ops=0, Sharpe=0.00
```

### Verificar dados carregados

```python
# Debug: verificar trades carregados
trades = self._obter_trades_periodo(dias=7)
print(f"Trades carregados: {len(trades)}")
for t in trades[:3]:
    print(f"  {t['symbol']}: {t['pnl_usdt']:.2f} USDT")

# Debug: verificar métricas
metricas = self.carregar_metricas()
print(f"PnL geral: {metricas['globais']['pnl_usdt']:.2f} USDT")
print(f"Taxa acertos: {metricas['globais']['taxa_acertos']:.1%}")
```

## 🎯 Próximas Melhorias

1. **Análise de Binance API** (em progresso)
   - Obter fills reais de `/fapi/v1/trades`
   - Comparar price action vs modelo

2. **Contexto Macro Automático**
   - Integrar DXY, S&P 500, VIX
   - Colocar no relatório automaticamente

3. **Comparação Semana A Semana**
   - Carregar reunião anterior
   - Comparar PnL, Sharpe, taxa acerto
   - Mostrar tendência (↑/↓/→)

4. **Recomendações LLM**
   - Usar feedbacks/ações como prompt
   - Gerar diálogos mais naturalistas
   - Adaptar tom baseado em performance

## 📚 Referência Rápida

### Funções Principais

| Função | O que faz | Saída |
|--------|----------|-------|
| `_obter_trades_periodo()` | Lê trade_log do DB | List[Dict] |
| `_calcular_metricas_trades()` | Calcula PnL, Sharpe, etc | Dict com métricas |
| `_obter_pares_mais_operados()` | Identifica top pares | List[Dict] |
| `_analisar_logs_operacionais()` | Parseia logs/ | Dict com erros/avisos |
| `_gerar_feedbacks_dinamicos()` | Cria 9 feedbacks | List[Dict] (3+3+3) |
| `_gerar_acoes_dinamicas()` | Cria 6 ações | List[Dict] com plano |

### Estrutura Retornada

```python
metricas = {
    "periodo": {"data_inicio": "...", "data_fim": "..."},
    "globais": {
        "pnl_usdt": 12450.75,
        "pnl_percentual": 2.15,
        "sharpe_ratio": 1.82,
        "max_drawdown": 3.2,
        "taxa_acertos": 0.62,
        "num_operacoes": 45,
        "pares_operados": 12
    },
    "por_par": [
        {"par": "BTCUSDT", "pnl": 5200.00, "operacoes": 8, "taxa_acerto": 0.75}
    ],
    "logs": {
        "erros": [...],
        "avisos": [...],
        "falhas_execucao": [...],
        "padroes": [...]
    }
}
```

## ✅ Status

- [x] Leitura de `trade_log` do DB
- [x] Cálculo de métricas reais
- [x] Parsing de logs operacionais
- [x] Geração dinâmica de feedbacks
- [x] Geração dinâmica de ações
- [x] Fallback para exemplos
- [x] Integração com disparador
- [ ] Análise Binance API
- [ ] Contexto Macro automático
- [ ] Comparação semana anterior

---

**Data de criação:** 2026-02-20
**Versão:** 1.0 (Initial Data Integration)
**Autor:** GitHub Copilot
