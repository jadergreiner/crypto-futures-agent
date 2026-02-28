# 🚀 README de Impacto — Crypto Futures Agent

**Versão:** 0.3.0 | **Data:** 28 FEV 2026
**Impacto:** Setup, Teste, Deploy para Produção

---

## 🎯 O Que é Este Documento?

Este README explica:

1. **Como configurar** o ambiente (dev + deps)
2. **Como testar** (unit, integration, backtesting)
3. **Como fazer deploy** (paper + live trading)
4. **Como monitorar** em produção

**Público-alvo:** Desenvolvedores, DevOps, Operadores

---

## 📋 Quick Start (5 minutos)

### Pré-requisitos

- Python 3.11+
- Git
- Conta Binance Futures (chaves API)

### Setup Inicial

```bash
# 1. Clone o repositório
git clone https://github.com/jadergreiner/crypto-futures-agent.git
cd crypto-futures-agent

# 2. Configure ambiente virtual
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Instale dependências
pip install -r requirements.txt

# 4. Configure chaves API Binance
# Edite: config/.env.local
cat > config/.env.local << EOF
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
TRADING_MODE=paper
EOF

# 5. Execute o menu
python menu.py
```



---

## 🛠️ Setup Detalhado

### 1. Dependências Principais

| Pacote | Versão | Propósito |
| --- | --- | --- |
| numpy | ^1.24 | Cálculos numéricos |
| pandas | ^2.0 | Análise de dados |
| requests | ^2.31 | HTTP client (Binance API) |
| python-dotenv | ^1.0 | Carregamento de env vars |
| pytest | ^7.4 | Testing framework |
| black | ^23.9 | Code formatter |
| markdownlint | ^0.35 | Markdown linter |

### 2. Instalação em Produção

```bash
# Produção (sem dev deps)
pip install -r requirements.txt

# Desenvolvimento (com testes + linting)
pip install -r requirements-dev.txt

# Verificar instalação
python -c "import numpy, pandas, requests; print('✅ Deps OK')"
```



### 3. Configuração de Ambiente

```bash
# Copiar template
cp config/.env.example config/.env.local

# Editar com suas chaves
# IMPORTANTE: Nunca commit .env.local em git!
```

**Arquivo `.env.local`:**

```bash
# Binance Futures
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# Modo de trading
TRADING_MODE=paper  # ou "live"

# Capital inicial
INITIAL_CAPITAL=10000

# Símbolos a operar
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT

# Logging
LOG_LEVEL=INFO

# Cache de dados
DATA_CACHE_DIR=./data/
```



---

## 🧪 Teste Completo

### 1. Unit Tests

```bash
# Rodar todos os testes
pytest tests/ -v

# Teste específico
pytest tests/test_smc_analyzer.py::test_order_block_detection -v

# Com coverage
pytest --cov=agent --cov=execution tests/
```



**Estrutura de testes:**

```text
tests/
├── test_smc_analyzer.py       (28 tests PASS)
├── test_position_manager.py   (15 tests PASS)
├── test_risk_gates.py         (12 tests PASS)
├── test_klines_cache.py       (8 tests PASS)
└── test_backtester.py         (22 tests PASS)
```



### 2. Integration Tests

```bash
# Teste com cache SQLite real
pytest tests/integration/ -v --db=:memory:

# Teste com Binance Sandbox (se disponível)
pytest tests/integration/test_binance_sandbox.py
```



### 3. Data Validation

```bash
# Validar 1Y histórico de dados
python data/scripts/klines_cache_manager.py --action validate

# Esperado:
# ✅ 60 símbolos
# ✅ 131.400 candles
# ✅ Integridade > 99%
```

### 4. Backtesting

```bash
# Backtesting 1 símbolo em 1 ano
python backtest/backtester.py \
  --symbol BTCUSDT \
  --start_date 2025-02-28 \
  --end_date 2026-02-28

# Relatório gerado: backtest/reports/BTCUSDT_20260228.json
# Equity curve: backtest/plots/BTCUSDT_equity_curve.png
```



**Métricas esperadas:**

```text
Sharpe Ratio: 1.2–1.8 (objetivo ≥ 1.0)
Max Drawdown: < 10%
Win Rate: > 50%
Profit Factor: > 1.5
```



---

## 🎯 Modos de Operação

### Paper Trading (Simulação)

```bash
# config/.env.local
TRADING_MODE=paper

# Executa: iniciar.bat
python menu.py

# Resultado:
# ✅ Sinais detectados (SMC análise)
# ✅ Ordens "colocadas" (sem efeito real)
# ✅ P&L rastreado (simulado)
# ✅ Logs completos (idênticos ao live)
```



**Objetivo:** Validar disciplina de risco antes de usar capital real.

### Live Trading (Produção)

```bash
# ⚠️ ANTES de ativar:
# 1. Executar backtesting em Paper com sucesso
# 2. Validar signals em Paper por ≥ 1 semana
# 3. Ter capital >= $1,000 em Binance Futures
# 4. Rever risk gates (leverage, drawdown)

# Ativar:
# config/.env.local
TRADING_MODE=live
INITIAL_CAPITAL=10000  # ou seu capital real

# Executar: iniciar.bat
python menu.py

# Resultado:
# 🔴 Ordens REAIS em Binance
# 🔴 Capital em risco
# ✅ Logs completos + auditoria
```



**Gatilhos de Parada de Emergência:**

- Drawdown portfolio > -5% -> circuit breaker ativo
- Drawdown símbolo > -3% -> posição fechada
- Orden não preenchida > 2h -> cancel automático



---

## 📊 Monitoramento em Produção

### 1. Logs em Tempo Real

```bash
# Terminal 1: Ver logs ao vivo
tail -f logs/crypto_futures.log | grep "TRADE\|ERROR\|CIRCUIT"

# Exemplo:
# [2026-02-28 14:30:00] [INFO] [BTCUSDT] TRADE ENTRY: qty=0.1, price=67500.00
# [2026-02-28 14:35:00] [WARN] [ETHUSDT] SL hit: -2.1%, pos_closed
# [2026-02-28 15:00:00] [ERROR] [CIRCUIT] Portfolio DD = -5.2% > -5.0% threshold
```



### 2. Mét ricas Diárias

```bash
# Gerar relatório diário
python execution/report_generator.py --date 2026-02-28

# Output: reports/daily_report_20260228.json
# Conteúdo:
# {
#   "date": "2026-02-28",
#   "trades_executed": 5,
#   "pnl_realized": 1250.00,
#   "pnl_unrealized": -300.00,
#   "equity": 10950.00,
#   "margin_ratio": 3.5,
#   "max_drowdown_daily": -2.1%
# }
```

### 3. Telegram Alerts (Issue #64)

```bash
# Configurar webhook Telegram
# config/.env.local
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Alertas automáticos:
# ✅ Trade entry
# ⚠️ Stop loss hit
# ❌ Circuit breaker acionado
```



### 4. Dashboard Web (Futuro)

```bash
# Iniciar servidor HTTP (planejado para v0.4)
python dashboard/server.py --port 8000

# Acessar em browser:
# http://localhost:8000/dashboard
```



---

## 🚀 Deploy

### Deploy Local (Desenvolvimento)

```bash
# 1. Clonar repo
git clone https://github.com/jadergreiner/crypto-futures-agent.git

# 2. Setup env
cd crypto-futures-agent
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate (Windows)
pip install -r requirements-dev.txt

# 3. Rodar testes
pytest tests/ -v
markdownlint docs/*.md

# 4. Executar em paper mode
export TRADING_MODE=paper
python menu.py
```



### Deploy em VPS/Cloud (Produção)

#### Opção 1: Linux (Recomendado)

```bash
# 1. SSH no servidor
ssh user@your-vps-ip

# 2. Clone repo
git clone https://github.com/jadergreiner/crypto-futures-agent.git
cd crypto-futures-agent

# 3. Setup systemd service
sudo tee /etc/systemd/system/crypto-agent.service << EOF
[Unit]
Description=Crypto Futures Agent
After=network.target

[Service]
Type=simple
User=crypto
WorkingDirectory=/home/crypto/crypto-futures-agent
Environment="TRADING_MODE=live"
ExecStart=/home/crypto/crypto-futures-agent/venv/bin/python menu.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 4. Ativar serviço
sudo systemctl daemon-reload
sudo systemctl enable crypto-agent
sudo systemctl start crypto-agent

# 5. Monitorar
sudo systemctl status crypto-agent
tail -f /var/log/crypto-agent.log
```



#### Opção 2: Docker (Futuro)

```dockerfile
# Dockerfile (v0.4+)
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV TRADING_MODE=live
CMD ["python", "menu.py"]
```

```bash
# Buildar e rodar
docker build -t crypto-agent:0.3.0 .
docker run --env-file .env.secret crypto-agent:0.3.0
```



---

## 🔍 Troubleshooting

### Problema: "API Keys Não Carregadas"

```bash
# Solução:
1. Verificar .env.local existe
2. Validar sintaxe (sem espaços extras)
3. Recarregar shell: source venv/bin/activate
```

### Problema: "Rate Limit 429 da Binance"

```bash
# Solução:
# RateLimitManager já implementa backoff exponencial
# Se persiste:
1. Aumentar WAIT_TIME em config/params.yaml
2. Reduzir número de símbolos analisados
```

### Problema: "Circuit Breaker Acionado"

```bash
# Verificar:
python execution/audit_positions.py

# Se false positive:
1. Validar cálculo de drawdown em risk_gates.py
2. Consultar DECISIONS.md para decisão sobre limite
```



---

## 📚 Próximos Passos

1. **Backtesting:** Execute `backtest/` antes de live
2. **Paper Trading:** Simule por ≥ 1 semana
3. **Monitoring:** Configure Telegram alerts
4. **Go-Live:** Autorizar trading real em config/.env.local

---

## 🔗 Documentação Relacionada

- [C4_MODEL.md](C4_MODEL.md) — Diagrama arquitetural
- [ADR_INDEX.md](ADR_INDEX.md) — Decisões de design
- [OPENAPI_SPEC.md](OPENAPI_SPEC.md) — Especificação de API
- [architecture.md](architecture.md) — Design detalhado
- [DECISIONS.md](DECISIONS.md) — Histórico de decisões

---

## 💬 Suporte

**Issues:** GitHub Issues (repo: crypto-futures-agent)
**Discussões:** GitHub Discussions
**Slack:** #crypto-futures (internal team)

---

**Atualizado:** 28 FEV 2026 | **Versão:** 0.3.0

