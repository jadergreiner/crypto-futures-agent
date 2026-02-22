# 🛠️ Runbook Operacional — Crypto Futures Agent

**Versão:** 1.0.0
**Última atualização:** 2026-02-22

---

## 🔗 Links Rápidos

- [ROADMAP](ROADMAP.md)
- [Status de Entregas](STATUS_ENTREGAS.md)
- [Critérios de Aceite](CRITERIOS_DE_ACEITE_MVP.md)

---

## ✈️ Pré-Voo (Checklist de Inicialização)

Execute antes de cada sessão de trading:

| # | Verificação                                  | Comando / Ação                      | OK? |
|---|----------------------------------------------|-------------------------------------|-----|
| 1 | Variáveis de ambiente carregadas             | `cat .env` / verificar `.env`       | [ ] |
| 2 | Conexão com Binance Futures ativa            | `python check_data_availability.py` | [ ] |
| 3 | Banco de dados acessível                     | `python check_db_status.py`         | [ ] |
| 4 | Modo operacional (paper/live) correto        | Ver `config/settings.py` → `MODE`  | [ ] |
| 5 | Circuit Breaker configurado (-3%)            | Ver `config/settings.py`            | [ ] |
| 6 | Logs limpos ou rotacionados                  | Verificar pasta `logs/`             | [ ] |
| 7 | Capital disponível conferido                 | `python diag_saldo_futures.py`      | [ ] |

---

## ⚡ Comandos Rápidos

### Iniciar agente

```bash
# Windows
iniciar.bat

# Modo paper (recomendado para testes)
python main.py --mode paper

# Verificar status em tempo real
python status_realtime.py
```

### Consultar banco de dados

```bash
python check_db_status.py
python check_trades.py
```

### Verificar posições abertas

```bash
python posicoes.py
python audit_all_positions_real.py
```

### Parar agente com segurança

```bash
# Pressionar Ctrl+C no terminal do agente
# Verificar se posições foram fechadas:
python posicoes.py
```

---

## 🚨 Incidentes Comuns

### IC-01 — API Binance retorna erro 4xx/5xx

**Sintoma:** Logs mostram `BinanceAPIException` ou timeout.

**Ação:**
1. Verificar status da API: <https://www.binance.com/en/futures/BTCUSDT>
2. Conferir chaves de API: `cat .env | grep BINANCE`
3. Aguardar 60s e tentar novamente.
4. Se persistir: executar `python check_api_key.py`.

### IC-02 — Circuit Breaker ativado

**Sintoma:** Log contém `CIRCUIT BREAKER ACTIVATED` ou
`EMERGENCY STOP`.

**Ação:**
1. **NÃO** reiniciar o agente imediatamente.
2. Verificar PnL do dia: `python relatorio_24h_agente.py`.
3. Revisar posições: `python posicoes.py`.
4. Se drawdown > -3%: aguardar reset diário (00:00 UTC).
5. Registrar ocorrência no [Status de Entregas](STATUS_ENTREGAS.md).

### IC-03 — Banco de dados corrompido

**Sintoma:** Erro SQLite ou tabelas ausentes.

**Ação:**
1. Parar agente imediatamente.
2. Fazer backup:
   - Linux/Mac: `cp db/crypto_agent.db db/crypto_agent_backup_$(date +%Y%m%d).db`
   - Windows: `copy db\crypto_agent.db db\crypto_agent_backup_%date:~-4,4%%date:~-7,2%%date:~0,2%.db`
3. Rodar schema: `python check_schema.py`
4. Se irrecuperável: restaurar último backup em `db/`.

### IC-04 — Posição não fechada após stop

**Sintoma:** `posicoes.py` mostra posição aberta mas stop foi atingido.

**Ação:**
1. Verificar ordens abertas: `python check_open_orders.py`
2. Fechar manualmente via Binance Futures se necessário.
3. Registrar como incidente em [Status de Entregas](STATUS_ENTREGAS.md).

---

## 🔄 Rollback / Pausa Segura

### Pausa temporária (recomendada)

```bash
# 1. Pressionar Ctrl+C no terminal do agente
# 2. Verificar posições abertas:
python posicoes.py
# 3. Aguardar fechamento natural ou fechar manualmente
```

### Rollback completo (emergência)

```bash
# 1. Parar agente (Ctrl+C)
# 2. Fechar todas as posições no Binance Futures manualmente
# 3. Verificar que não há ordens pendentes:
python check_open_orders.py
# 4. Registrar rollback com motivo em CHANGELOG.md
```

> ⚠️ **Regra de ouro:** Em caso de dúvida, PARAR o agente e revisar
> [Critérios de Aceite](CRITERIOS_DE_ACEITE_MVP.md) antes de reiniciar.

---

## 📋 Manutenção Periódica

| Frequência | Ação                                    | Responsável |
|------------|-----------------------------------------|-------------|
| Diário     | Revisar logs e PnL do dia               | Operador    |
| Semanal    | Atualizar [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md) | Operador    |
| Por Sprint | Revisar [CRITERIOS_DE_ACEITE_MVP.md](CRITERIOS_DE_ACEITE_MVP.md) | TODO        |
| Por Sprint | Adicionar entrada em [CHANGELOG.md](CHANGELOG.md)   | TODO        |
