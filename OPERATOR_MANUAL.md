# Manual do Operador — Crypto Futures Agent

**Versão:** v0.3 Training Ready  
**Data:** 20/02/2026  
**Audiência:** Operadores do agente de trading

---

## 📋 Início Rápido

### Iniciar o Orquestrador

```bash
.\iniciar.bat
```

O script executará **verificações pré-operacionais** automaticamente:
- ✅ Ambiente virtual (venv)
- ✅ Configuração (.env)
- ✅ Banco de dados
- ✅ Logs e modelos

Se tudo estiver OK, você verá o **menu interativo** com 9 opções.

---

## 🎯 Opções de Execução

### 1️⃣ **Paper Trading** (Simulação)

**Use quando:** Testar a estratégia sem risco real

```
Opção: 1
```

**O que faz:**
- Simula trades em capital virtual
- Nenhuma ordem enviada para Binance
- Logs em: `logs/agent.log`

**Resumo de segurança:** ✅ SEGURO — Nenhum capital em risco

---

### 2️⃣ **Live Integrado** (Capital Real)

**Use quando:** Executar estratégia com capital real

```
Opção: 2
```

**Confirmações obrigatórias:**
1. Confirme que as ordens são REAIS
2. Confirme que revisou o `.env`
3. Digite "INICIO" como autorização final

**O que faz:**
- Busca oportunidades automaticamente
- Executa ordens REAIS na Binance
- Gerencia posições abertas
- Logs em: `logs/agent.log`

**Resumo de segurança:** ⚠️ CRÍTICO — Capital REAL em risco. Requer 3 confirmações.

---

### 3️⃣ **Monitorar Posições Abertas**

**Use quando:** Acompanhar trades abertos em tempo real

```
Opção: 3
```

**Dados de entrada:**
- Símbolo: `BTCUSDT` (ou deixe em branco para TODAS)
- Intervalo: `300` (segundos, padrão 5 min)

**O que faz:**
- Monitora posições abertas
- Exibe TP/SL status
- Atualiza a cada X segundos
- Logs em: `logs/agent.log`

**Resumo de segurança:** ✅ SEGURO — Apenas leitura, sem execução

---

### 4️⃣ **Executar Backtest**

**Use quando:** Validar performance histórica

```
Opção: 4
```

**Dados de entrada:**
- Data inicial: `2024-01-01`
- Data final: `2024-12-31`

**O que faz:**
- Testa estratégia em dados históricos
- Calcula métricas: Win Rate, Sharpe, Max DD
- Gera relatório em: `reports/backtest_report.html`
- Logs em: `logs/agent.log`

**Resumo de segurança:** ✅ SEGURO — Apenas backtesting, sem execução

---

### 5️⃣ **Treinar Modelo RL**

**Use quando:** Aprimorar o modelo com novos dados

```
Opção: 5
```

**Tempo estimado:** 4-7 horas (depende do hardware)

**O que faz:**
- Fase 1 — Exploração: 500k timesteps (~1-2h)
- Fase 2 — Refinamento: 1M timesteps (~2-4h)
- Fase 3 — Validação: 100 episódios (~30min)
- Modelo salvo em: `models/crypto_agent_ppo_final.zip`
- Logs em: `logs/agent.log`

**Resumo de segurança:** ✅ SEGURO — Treina offline, sem impacto operacional

---

### 6️⃣ **Executar Setup Inicial**

**Use quando:** Inicializar ambiente pela primeira vez

```
Opção: 6
```

**Tempo estimado:** 15-30 minutos

**O que faz:**
- Cria banco de dados vazio
- Coleta dados históricos:
  - 365 dias Daily (D1)
  - 180 dias Quarterly (H4)
  - 90 dias Hourly (H1)
- Calcula indicadores técnicos
- Banco de dados: `db/crypto_agent.db` (~500MB)

**Resumo de segurança:** ✅ SEGURO — Apenas coleta de dados, sem execução

---

### 7️⃣ **Diagnosticar Sistema**

**Use quando:** Verificar saúde do ambiente

```
Opção: 7
```

**O que faz:**
- Verifica dependências Python
- Testa conectividade Binance
- Valida configuração
- Logs em: `logs/agent.log`

**Resumo de segurança:** ✅ SEGURO — Apenas diagnóstico, sem impacto

---

### 8️⃣ **Assumir Posição Aberta**

**Use quando:** Gerenciar trade já executado na Binance

```
Opção: 8
```

**Dados de entrada:**
- Símbolo: `BTCUSDT`
- Intervalo: `300` (segundos, padrão 5 min)

**O que faz:**
- Assume gerência de posição existente
- Monitora TP/SL
- Ajusta stops conforme necessário
- Logs em: `logs/agent.log`

**Resumo de segurança:** ⚠️ CUIDADO — Gerencia posição existente

---

### 9️⃣ **Sair**

**Use quando:** Encerrar o orquestrador

```
Opção: 9
```

---

## 📊 Estrutura de Arquivos Importantes

```
crypto-futures-agent/
├── .env                          ← Credenciais Binance (NUNCA fazer commit!)
├── logs/
│   └── agent.log                 ← Logs de execução
├── db/
│   └── crypto_agent.db           ← Banco de dados histórico
├── models/
│   └── crypto_agent_ppo_final.zip ← Modelo treinado
├── reports/
│   └── backtest_report.html      ← Relatório de backtest
└── README.md                     ← Documentação técnica
```

---

## 🔍 Leitura de Logs

**Localização:** `logs/agent.log`

**Ferramentas úteis:**

### PowerShell — Últimas linhas
```powershell
Get-Content logs/agent.log -Tail 20
```

### PowerShell — Buscar erros
```powershell
Select-String "ERRO|ERROR" logs/agent.log | Tail -10
```

### PowerShell — Monitorar em tempo real
```powershell
Get-Content logs/agent.log -Tail 10 -Wait
```

---

## ⚠️ Troubleshooting

### Problema: "Ambiente virtual não encontrado"

**Solução:**
```bash
setup.bat
```

---

### Problema: "Arquivo .env não encontrado"

**Solução:**
1. Copie `.env.example` para `.env`
2. Edite `.env` com suas chaves:
   ```
   BINANCE_API_KEY=sua_chave_aqui
   BINANCE_API_SECRET=seu_secret_aqui
   ```

---

### Problema: "Banco de dados não encontrado"

**Solução:**

Use a **Opção 6** do menu para executar setup inicial.

---

### Problema: Conexão com Binance falha

**Verificação:**
1. Opção 7 → Diagnosticar Sistema
2. Verifique logs: `logs/agent.log`
3. Confirme chaves em `.env`
4. Teste conexão manual:
   ```bash
   python main.py --test-connection
   ```

---

### Problema: Treino muito lento

**Diagnóstico:**
- Use **Opção 7** para verificar CPU/GPU
- Considere reduzir timesteps em `config/settings.py`

---

## 🛡️ Boas Práticas

### ✅ FAÇA

- ✅ Executar **Paper Trading** regularmente
- ✅ Revisar logs diariamente
- ✅ Fazer backtest antes de live trading
- ✅ Manter `.env` seguro (nunca fazer commit)
- ✅ Monitorar posições abertas
- ✅ Usar **Opção 7** para diagnosticar problemas

### ❌ NÃO FAÇA

- ❌ Compartilhar credenciais do `.env`
- ❌ Executar Live sem revisar backtest
- ❌ Ignorar confirmações de segurança
- ❌ Modificar código sem conhecimento técnico
- ❌ Deixar terminal aberta sem supervisão em Live

---

## 📞 Contato e Suporte

**Logs de erro:** Verifique `logs/agent.log` primeiro

**Documentação técnica:** Leia [README.md](README.md)

**Relatórios detalhados:** Disponíveis em `reports/`

---

## 📝 Histórico de Versões

| Versão | Data | Mudanças |
|--------|------|----------|
| v0.3 | 20/02/2026 | Training Ready (F-06, F-07, F-08, F-09) |
| v0.2 | 15/02/2026 | Paper Trading foundation |
| v0.1 | 01/02/2026 | Initial release |

---

**Última atualização:** 20/02/2026  
**Mantido por:** GitHub Copilot  
**Status:** ✅ Operacional
