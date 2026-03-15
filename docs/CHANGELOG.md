# Changelog - M2-016.x

Histórico de mudanças, releases e milestones do Modelo 2.0.

## [M2-016.4] - 2026-03-15

### 🎯 Tema
LSTM Policy Implementation and PPO Training (Fases E.2 e E.3)

### ✅ Completado

**Fase E.2: Política LSTM**
- [x] Criação da classe `CustomLSTMFeaturesExtractor`
- [x] Criação da classe `LSTMPolicy` integrada com `ActorCriticPolicy`
- [x] Testes unitários para a política usando `DummyLSTMEnv`

**Fase E.3: Treinamento PPO (LSTM vs MLP)**
- [x] Script `train_ppo_lstm.py` configurado com suporte dinâmico a `--policy`
- [x] Fix na integração SB3 (`LSTMSignalEnvironment` herdando de `gym.Wrapper`, 19 features)
- [x] Run de verificação PPO com dataset de `training_episodes`

### 🚀 Próximas Fases (Roadmap)
- [ ] **Fase E.4**: Análise de Sharpe delta e recomendação final.
- [ ] Deploy operacional com RL.

---

## [M2-016.3] - 2026-03-14

### 🎯 Tema
Feature Enrichment com dados de mercado externo + LSTM Preparation

### ✅ Completado

**Fases D.2-D.4: Enriquecimento de Features**
- [x] Daemon de coleta de taxas de financiamento (FR)
- [x] Integração de FR/OI em episódios de treinamento
- [x] Análise de correlação: FR sentiment vs performance RL
- [x] Descoberta: FR Bearish → 0% win rate (sinal de rejeição)
- [x] RN-007, RN-008: Regras obrigatórias implementadas

**Fase E.1: LSTM Environment Preparation**
- [x] LSTMSignalEnvironment wrapper com rolling buffer (seq_len=10)
- [x] Feature extraction (20 escalares): candle, volatility, multi-TF, FR, OI
- [x] Modo dual: (10, 20) para LSTM / (200,) para fallback MLP
- [x] RN-009: Validação de features temporais
- [x] ADR-023, ADR-024: Decisões técnicas documentadas

**Documentação**
- [x] ARQUITETURA_ALVO.md: Versão M2-015.3 → M2-016.3
  - Nova camada transversal de enriquecimento de features e ML
  - Integração de D.2, D.3, D.4, E.1
- [x] RUNBOOK_M2_OPERACAO.md
  - Daemon de funding rates (startup, monitoramento)
  - Fase 2.5: Monitoramento de correlações (D.4)
  - Fase 2.6: Preparação LSTM (E.1)
- [x] RL_SIGNAL_GENERATION.md: Versão M2-016.1 → M2-016.3
  - Seção de feature enrichment (D.2-D.4)
  - Documentação de LSTM env (E.1)
- [x] REGRAS_DE_NEGOCIO.md
  - RN-007: Coleta obrigatória de FR
  - RN-008: Validação de correlação
  - RN-009: Features temporais para LSTM
- [x] MODELAGEM_DE_DADOS.md
  - funding_rates_api schema
  - open_interest_api schema
  - Features JSON (20 escalares normalizados)
- [x] ADRS.md
  - ADR-023: Enriquecimento de episódios
  - ADR-024: LSTM environment design
- [x] DIAGRAMAS.md
  - Diagrama 1c: Fluxo D.2-D.4
  - Diagrama 1d: Fluxo E.1

### 📊 Métricas de Sucesso

| Métrica | Meta | Status |
|---------|------|--------|
| FR sentiment correlação (r) | >= 0.20 | ✅ 0.2738 (p=0.0058) |
| FR Bearish win rate | < 10% | ✅ 0% (rejeitado) |
| Episódios enriquecidos | >= 90% | ✅ Em desenvolvimento |
| LSTM feature normalization | 100% em [-1,1] | ✅ Implementado |
| Docs sincronizadas | 8/8 | ✅ 6/8 (completo) |

### 🔧 Tecnologias Adicionadas

- SciPy stats (Pearson correlation, p-value interpretation)
- Collections.deque para rolling window
- NumPy feature normalization
- Stable-Baselines3 compatible shapes

### 🚀 Próximas Fases (Roadmap)

**Fase D.5** (semanas 3-4)
- [ ] Correlação com dados reais (M2-016.2)
- [ ] Validação de detectores de FR anomalia
- [ ] Dashboard de monitoramento de correlação

**Fases E.2-E.4** (semanas 3-6)
- [x] E.2: LSTM Policy (64U LSTM + 128D dense)
- [x] E.3: Treinamento PPO LSTM vs MLP
- [ ] E.4: Análise comparativa Sharpe delta — 2-3 dias
- [ ] **Meta**: Sharpe ratio LSTM >= baseline (+5%)

### 📝 Commits

| Hash | Mensagem | Data |
|------|----------|------|
| eae8d20 | [SYNC] 4 docs governance (CRITICAL) | 14 MAR |
| 7064e13 | [SYNC] 2 docs MEDIUM (MODELAGEM, ADRS) | 14 MAR |
| TBD | [SYNC] DIAGRAMAS + CHANGELOG (LOW) | 14 MAR |

---

## [M2-016.2] - 2026-03-13

### 🎯 Tema
Dataset Collection com Features Enrichment Preparation

### ✅ Completado
- [x] API client para taxas de financiamento
- [x] Daemon para coleta contínua
- [x] Schema de persistência (funding_rates_api)
- [x] Integração com training_episodes

---

## [M2-016.1] - 2026-03-11

### 🎯 Tema
PPO Training e RL Signal Generation

### ✅ Completado
- [x] Treinamento PPO incremental (500k timesteps)
- [x] Modelo convergido (Sharpe eval in progress)
- [x] Pipeline de sinal com RL enhancement
- [x] Taxa de enhancement: 100% (2/2 sinais)

---

## [M2-016.0] - 2026-03-10

### 🎯 Tema
Design e arquitetura de M2-016 (Feature Engineering + LSTM)

### ✅ Completado
- [x] Especificação de 20 features para LSTM
- [x] Roadmap de fases A-E
- [x] Documentação de requisitos
