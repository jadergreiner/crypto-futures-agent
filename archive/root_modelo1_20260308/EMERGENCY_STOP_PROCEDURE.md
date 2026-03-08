# 🚨 PROCEDIMENTO DE PARADA DE EMERGÊNCIA

**Documento:** Procedimento de Parada Segura
**Audiência:** Operador/Executivo
**Crítico:** ⚠️ SIM — Leia ANTES de iniciar Phase 2
**Data:** 22 FEV 2026 | **Status:** ✅ OPERACIONAL

---

## 1️⃣ PARADA IMEDIATA (Ctrl+C)

### Cenário: Algo deu muito errado AGORA

```
Janela Python principal (onde está rodando main.py):

Pressione:  Ctrl + C

Resultado esperado:
  - Sistema vai PARAR gracefully
  - Ordens abertas -> estado SALVO no database
  - Posições mantidas ABERTAS (no Binance)
  - Logs escrito em: logs/agent.log
```

**Tempo de parada:** ~2-5 segundos
**Capital em risco:** ⚠️ Posições PERMANECEM ABERTAS
**Próximo passo:** Contate Risk Manager

---

## 2️⃣ ENCERRAMENTO COM DUMP DE ESTADO (Script)

### Cenário: Preciso parar E salvar diagnostics

```powershell
# Terminal 1: Parar main.py
Ctrl + C

# Terminal 2: Executar diagnostics
cd C:\repo\crypto-futures-agent
python posicoes.py

# Resultado:
#   - Lista TODAS as 20 posições abertas
#   - Mostra P&L de cada uma
#   - Salva em: reports/position_snapshot_*.json
```

**Tempo:** ~5-10 segundos
**O que é salvo:** Estado completo de posições para auditoria
**Próximo passo:** Enviar diagnóstico para Risk Manager

---

## 3️⃣ PARADA SEGURA COM GERENCIAMENTO DE POSIÇÕES

### Cenário: Preciso parar, mas quer fechar posições

⚠️ **AVISO:** Esta operação requer DECISÃO DE RISCO

```powershell
# Este procedimento NÃO é automatizado.
# Requer contato com Risk Manager primeiro!

Opções:
  A) Fechar TUDO (vender todas as posições)
  B) Fechar 50% (reduzir risco)
  C) Deixar como está (apenas parar agente)
```

**Decisão recomendada:** Contate Angel ou Dr. Risk ANTES de fechar

---

## 4️⃣ RECUPERAÇÃO APÓS PARADA

### Se parou com Ctrl+C

```powershell
# Reiniciar Phase 2
.\iniciar_phase2_risco_alto.bat

# OU (se quiser esperar antes de reiniciar)
python main.py --status
  # Mostra: estado das posições
  # Mostra: P&L atual
  # Mostra: Circuit breaker status
```

---

## 🚨 SITUAÇÕES CRÍTICAS & RESPOSTAS

### Situação 1: Drawdown caindo abaixo de -50%

```
Ação IMEDIATA:
  1. Pressione Ctrl+C (parar agente)
  2. Execute: python posicoes.py (salvar estado)
  3. Contate Angel AGORA (escalação crítica)

Status do sistema: MANTÉM posições abertas (protetor)
Circuit breaker: JÁ bloqueou novas ordens
```

### Situação 2: API Binance offline

```
Erro no log:
  "ConnectionError: Failed to connect to Binance"

Ação:
  1. Ctrl+C (parar agente)
  2. Aguarde 30 segundos (Binance pode estar recuperando)
  3. Execute: python main.py --test-connection
  4. Se ainda falhar: Contate Data Engineer
```

### Situação 3: Erro de Database

```
Erro no log:
  "sqlite3.Error: database is locked"

Ação:
  1. Ctrl+C (parar agente)
  2. Aguarde 10 segundos
  3. Reiniciar: .\iniciar_phase2_risco_alto.bat
```

### Situação 4: Liquidação de Posição

```
Evento no log:
  "LIQUIDATION: BROCCOLI position closed by Binance"

Ação:
  1. Monitor dashboard (já mostra nova realidade)
  2. Não feche outras posições por pânico
  3. Circuit breaker vai bloquear pior cenário
  4. Contate Risk Manager em 5 minutos
```

---

## 📋 CHECKLIST DE PARADA SEGURA

Antes de pressionar Ctrl+C:

- [ ] Você TEM diagnóstico do estado atual?
  (Se não: execute `python posicoes.py` PRIMEIRO)
- [ ] Dashboard mostra status? (Sim/Não)
- [ ] Você SABE por que está parando?
  (Escalação crítica? Erro? Manutenção?)
- [ ] Você AVISOU Risk Manager?
  (Se houver tempo, sim)

---

## 🔗 DOCUMENTAÇÃO RELACIONADA

- [CIRCUIT_BREAKER_RESPONSE.md](CIRCUIT_BREAKER_RESPONSE.md)
  — O que fazer quando CB dispara
- [DASHBOARD_OPERATOR_ALERTS.md](DASHBOARD_OPERATOR_ALERTS.md)
  — Como interpretar alertas
- [OPERADOR_GUIA_SIMPLES.md](OPERADOR_GUIA_SIMPLES.md)
  — Guia rápido de início

---

## 📞 CONTATOS CRÍTICOS

- **Angel** (Executiva): decisões críticas
- **Dr. Risk** (Risco): análise de cenários
- **Guardian** (Circuit Breaker): proteções
- **Executor** (Implementação): troubleshooting técnico

---

**Lembre:** Parar é melhor que continuar em crise.
**Sempre:** Salve o estado ANTES de reconectar.

