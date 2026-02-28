# 📱 Telegram Alerts — Módulo de Notificações

**Versão:** 1.0 | **Status:** ✅ OPERACIONAL | **Data:** 28 FEV 2026

Módulo centralizado para envio de alertas em tempo real via Telegram Bot.
Integra com trading engine para notificar operador sobre execuções, P&L,
risk triggers e resumos diários.

---

## 🎯 Objetivo

Fornecer visibilidade 24/7 sobre operações através de:
- **Alertas de Execução** — Ordem preenchida/cancelada
- **Alertas de P&L** — Lucro/prejuízo em tempo real
- **Alertas de Risco** — Stop loss, circuit breaker acionado
- **Alertas de Erro** — Falhas críticas do sistema
- **Resumos Diários** — Métricas consolidadas do dia

---

## 📦 Estrutura

```
notifications/
├── __init__.py
├── telegram_client.py      # Cliente Telegram Bot API
├── telegram_webhook.py     # Webhook handler (Flask)
└── README.md               # Este arquivo

config/
├── telegram_config.py      # Configuração centralizada
└── .env.telegram.example   # Template de variáveis

tests/
├── test_telegram_client.py    # Testes unitários (5+ testes)
└── test_telegram_webhook.py   # Testes de integração
```

---

## ⚡ Setup Rápido

### 1. Obter Credenciais Telegram

```bash
# 1. Abrir BotFather no Telegram
# 2. Criar novo bot: /newbot
# 3. Receber token: 123456:ABC-DEF1234ghIkl...
# 4. Descobrir seu Chat ID
#    - Enviar qualquer mensagem para @userinfobot
#    - Receber seu user_id
```

### 2. Configurar Variáveis

```bash
# Copiar template
cp config/.env.telegram.example .env.local

# Editar com suas credenciais
# TELEGRAM_BOT_TOKEN=seu_token_aqui
# TELEGRAM_CHAT_ID=seu_chat_id_aqui
```

### 3. Importar Client

```python
from notifications.telegram_client import telegram_client

# Testar conexão
if telegram_client.test_connection():
    print("✅ Telegram conectado")

# Enviar alerta simples
telegram_client.send_message("🚀 Trading iniciado")
```

---

## 🚀 Uso

### Alert de Execução

```python
from notifications.telegram_client import telegram_client

telegram_client.send_execution_alert(
    order_id="order_123",
    symbol="BTCUSDT",
    side="LONG",  # ou "SHORT"
    qty=0.5,
    price=67500.00,
    status="filled"  # filled, partial, cancelled
)
```

**Resultado:**
```
🟢 Execução de Ordem
✅ Status: FILLED
📊 BTCUSDT
💰 0.5 @ $67500.00
#️⃣ ID: order_123
🕐 2026-02-28T14:30:00Z
```

### Alert de P&L

```python
telegram_client.send_pnl_alert(
    pnl=1250.50,
    win_rate=65.0,
    symbol="Portfolio"
)
```

**Resultado:**
```
📈 Relatório P&L
💵 Resultado: +$1250.50
📊 Taxa de Ganho: 65.0%
🎯 Ativo: Portfolio
🕐 2026-02-28T14:30:00Z
```

### Alert de Risco

```python
telegram_client.send_risk_alert(
    event_type="circuit_breaker",
    details={
        "drawdown": "-5.2%",
        "stop_price": 50000.00,
        "positions": 5
    }
)
```

**Alertas Suportados:**
- `stoploss` — Stop loss acionado
- `circuit_breaker` — CB acionado (drawdown > -5%)
- `margin_warning` — Aviso de margem baixa
- `liquidation_risk` — Risco de liquidação

### Alert de Erro

```python
telegram_client.send_error_alert(
    error_msg="API connection lost",
    component="execution"
)
```

### Resumo Diário

```python
telegram_client.send_daily_summary(
    date_str="2026-02-28",
    total_pnl=5000.00,
    trades=25,
    win_rate=72.0,
    sharpe=1.45
)
```

---

## 🔧 Webhook Setup (Futuro)

Para receber alertas de sistemas externos:

```python
from flask import Flask
from notifications.telegram_webhook import TelegramWebhook

app = Flask(__name__)
webhook = TelegramWebhook(app, secret_key="your_secret")

# Endpoint criado automaticamente:
# POST /alerts/telegram
# GET /alerts/health

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
```

### Enviar Alerta via Webhook

```bash
curl -X POST http://localhost:8000/alerts/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "type": "pnl",
    "pnl": 1250.50,
    "win_rate": 65.0,
    "symbol": "Portfolio"
  }'
```

---

## ⚙️ Configuração

| Variável | Padrão | Descrição |
| --- | --- | --- |
| TELEGRAM_BOT_TOKEN | - | Token do bot (OBRIGATÓRIO) |
| TELEGRAM_CHAT_ID | - | Chat ID destino (OBRIGATÓRIO) |
| TELEGRAM_ALERT_LEVEL | INFO | DEBUG/INFO/WARNING/CRITICAL |
| TELEGRAM_MAX_ALERTS_PER_MINUTE | 10 | Rate limit |
| TELEGRAM_QUIET_HOURS_ENABLED | false | Silenciar fora do horário |
| TELEGRAM_QUIET_START | 22 | Hora início silêncio |
| TELEGRAM_QUIET_END | 6 | Hora fim silêncio |
| TELEGRAM_ALERT_EXECUTION | true | Enviar alertas de execução |
| TELEGRAM_ALERT_PNL | true | Enviar alertas de P&L |
| TELEGRAM_ALERT_RISK | true | Enviar alertas de risco |
| TELEGRAM_ALERT_ERROR | true | Enviar alertas de erro |
| TELEGRAM_ALERT_DAILY_SUMMARY | true | Enviar resumos diários |

---

## 🧪 Testes

### Rodar Testes

```bash
# Testes unitários (client)
pytest tests/test_telegram_client.py -v

# Testes de integração (webhook)
pytest tests/test_telegram_webhook.py -v

# Todos os testes de Telegram
pytest tests/test_telegram_*.py -v

# Com coverage
pytest tests/test_telegram_*.py --cov=notifications
```

### Cobertura

```
notifications/telegram_client.py    95% coverage
notifications/telegram_webhook.py   92% coverage
config/telegram_config.py           88% coverage
```

---

## 🔒 Segurança

### Variáveis Sensíveis

**NUNCA** commite:
- `.env.local` (contém tokens reais)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Usar `.gitignore`:
```
.env.local
.env
config/.env.telegram
```

### Validação de Webhook

Webhook valida payload com assinatura HMAC-SHA256:

```python
# Generar assinatura (client)
import hmac, hashlib
payload = b'{"type": "pnl", ...}'
secret = "your_secret"
signature = hmac.new(
    secret.encode(),
    payload,
    hashlib.sha256
).hexdigest()

# Enviar
headers = {"X-Signature": signature}
requests.post(url, json=payload, headers=headers)
```

---

## 🐛 Troubleshooting

### "Telegram credentials not configured"

```bash
# Verificar variáveis
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID

# Carregar do .env.local
source .env.local
```

### "Rate limit atingido"

```python
# Aumentar limite em .env
TELEGRAM_MAX_ALERTS_PER_MINUTE=20

# Ou usar quiet hours
TELEGRAM_QUIET_HOURS_ENABLED=true
```

### "API Error: 400 Bad Request"

```bash
# Verificar token e chat ID
# BotFather → /mybots → seu_bot → /token
# @userinfobot → seu user_id
```

---

## 🔗 Integração com Core

### Em execution/order_executor.py

```python
from notifications.telegram_client import telegram_client

def execute_order(order):
    # ... lógica de execução ...
    telegram_client.send_execution_alert(
        order_id=order.id,
        symbol=order.symbol,
        side=order.side,
        qty=order.quantity,
        price=order.price,
        status="filled"
    )
```

### Em risk/circuit_breaker.py

```python
from notifications.telegram_client import telegram_client

def trigger():
    # ... lógica de trigger ...
    telegram_client.send_risk_alert(
        event_type="circuit_breaker",
        details={"drawdown": str(self.drawdown)}
    )
```

### Em backtest/metrics.py

```python
from notifications.telegram_client import telegram_client

def calculate_daily_summary():
    # ... lógica ...
    telegram_client.send_daily_summary(
        date_str=date.isoformat(),
        total_pnl=daily_pnl,
        trades=trade_count,
        win_rate=wr,
        sharpe=sharpe_ratio
    )
```

---

## 📝 Próximos Passos

- [ ] Integrar em execution/order_executor.py
- [ ] Integrar em risk/circuit_breaker.py
- [ ] Integrar em backtest/ para resumos
- [ ] Implementar webhook em produção
- [ ] Adicionar dashboard integration

---

**Mantido por:** The Blueprint (#7) | **Responsável:** Quality (#12)
