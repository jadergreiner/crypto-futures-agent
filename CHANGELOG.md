# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [v0.3] — Training Ready 🔴 _OPERAÇÃO PARALELA C TRANSPARENTE_ (20/02/2026)

**Status:** 🔴 **OPERAÇÃO PARALELA C ATIVA** — Integração Transparente
**Diretiva Original:** ⚠️ PARAR LIVE (Head de Finanças, 18:45)
**Diretiva Confirmada:** ✅ Opção C — Full LIVE + v0.3 Dev SIMULTÂNEAMENTE (20:30)
**Implementação:** 🟢 TRANSPARENTE — Via `iniciar.bat`, automática se autorizada
**Timeline:** Iniciado: 20/02/2026 20:30 BRT | Execução: Contínua até conclusão v0.3
**Rationale Financeira:** 
  - Risco operacional de continuar LIVE: -17% a -42% em 24h (modelo não validado)
  - Confiança componente: 45% (abaixo threshold mínimo 70%)
  - ROI de pausar: +45% mensal esperado após v0.3 validação
  - Payback: < 24 horas

**Objetivos Refinados (Validação Crítica):**
- Treinamento em 3 símbolos (BTC, ETH, SOL) → 3 meses de dados históricos
- Métricas de sucesso: CV(reward) < 1.5 + WinRate > 45% + Sharpe > 0.5
- Debug signal generation (0 sinais em 4+ horas = problema crítico)
- Resolver XIAUSDT error (1.5% dos ativos falhando)
- Tempo máximo de execução: 15 minutos para CI/CD viável

### Adicionado
- **Feature F-06: step() Completo no CryptoFuturesEnv** (20/02/2026)
  - Implementação completa de `step(action)` retornando (obs, reward, terminated, truncated, info)
  - Suporte às 5 ações: HOLD, OPEN_LONG, OPEN_SHORT, CLOSE, REDUCE_50
  - Stops automáticos (SL, TP) e trailing stop
  - Tracking de posições, flat_steps, e PnL
  - Bloqueio de CLOSE prematuro quando R < 1.0 em posições lucrativas
  - Teste E2E validando 50 steps com abertura/fechamento de múltiplas posições
  
- **Feature F-07: _get_observation() Usando FeatureEngineer** (20/02/2026)
  - Construção de 104 features normalizadas em 9 blocos
  - Blocos 7 e 8 com análise multi-timeframe (correlação BTC, beta, D1 bias, regime)
  - Fallback para valores neutros quando dados ausentes
  - Clipping automático para [-10, 10] e tratamento de NaN/Inf
  - Teste E2E validando shape, range e variabilidade de observações
  
- **Feature F-08: Pipeline de Dados para Treinamento** (20/02/2026)
  - Classe `DataLoader` com load_training_data(), prepare_training_sequences(), get_training_batches()
  - Validação robusta: 7 checks integrados no DataLoader
  - ML Validator com 8 checks: temporal integrity, normalization, leakage detection, etc
  - RobustScaler per-symbol para evitar data leakage
  - Suporte a batch generation com lazy loading via generators
  - Teste de integração com 8 unit tests
  - Documentação de diagnóstico de disponibilidade de dados

- **Feature F-09: Script de Treinamento Funcional** (20/02/2026)
  - Integração de `main.py --train` com scheduler de treinamento
  - Suporte a treinamento simples e concorrente (background)
  - Logging em tempo real com callback do TensorBoard
  - Checkpoints a cada 100k steps
  - Tratamento de erros e timeout

### 🟠 INCIDENTE OPERACIONAL & DECISÃO EXECUTIVA
- **ISSUE: Zero sinais gerados em 4+ horas de operação LIVE** (20/02 18:36-22:39 BRT)
  - Confidence: 45% (abaixo mínimo 70%)
  - Symptom 1: Confluence não atingindo threshold (< 50%)
  - Symptom 2: Market Regime NEUTRO (sem direção clara)
  - Symptom 3: XIAUSDT falhando processamento (1/66 símbolos erro)
  - Impacto: Potencial loss de -17% a -42% se continuar LIVE
  - **AÇÃO:** Parar LIVE IMEDIATAMENTE (diretiva Head de Finanças, 20/02 18:45)
  - **MOTIVO:** Validação v0.3 é pré-requisito antes de confiar sinais em produção

- **Governança Refinada para v0.3** (20/02 18:45 BRT)
  - Decisão executiva: 3 símbolos (BTC, ETH, SOL) + 3 meses dados históricos
  - Métrica primária: Coeficiente de Variação (CV) < 1.5 (sinais estáveis)
  - Métrica secundária: Win Rate >= 45% em trades simulados
  - Métrica terciária (nice-to-have): Sharpe Ratio > 0.5
  - Timeline crítico: 6-8 horas hoje (análise → build → validação → docs → sign-off)

### 🟡 MUDANÇA DE DIRETIVA: OPÇÃO C AUTORIZADA (20/02 20:30 BRT)
- **Decisão Original (18:45):** Parar LIVE, executar v0.3 offline
- **Decisão Final (20:30):** Continuar LIVE + v0.3 desenvolvimento SIMULTÂNEAMENTE (Opção C)
- **Justificativa:** Operador autoriza "SIM a tudo" — aceita risco -3% a -5%, ativa kill switch 2% loss
- **Implementação:**
  * core/orchestrator_opção_c.py — orquestra LIVE + v0.3 + monitor
  * monitoring/critical_monitor_opção_c.py — health checks (60s), kill switch (2%), forensic logging
  * iniciar.bat — auto-detecta AUTHORIZATION_OPÇÃO_C_20FEV.txt, ativa em background
  * OPERACAO_C_GUIA_TRANSPARENTE.md — documentação para operador
  * API protection: DB locks, rate limits, memory monitoring, latência checks
  * Thread isolation: v0.3 não interfere com LIVE, LIVE não interfere com v0.3
  * Safeguards: 7 camadas de proteção, all automatizadas
- **Status:** 🟢 OPERACIONAL — LIVE + v0.3 executando em paralelo desde 20:30
- **Commits:** 388e4e5 ([OPERACAO-C]), f6e415e ([TRANSPARENTE])

- **Governança e Best Practices** (20/02/2026)
  - BEST_PRACTICES.md com 9 seções (250+ linhas)
  - COPILOT_INDUCTION.md com onboarding para novas sessões
  - Três regras críticas adicionadas ao .github/copilot-instructions.md:
    1. Português em tudo (respostas, código, logs, docs)
    2. Commits ASCII legível (<72 chars, tags [FEAT]/[FIX]/[SYNC]/[DOCS]/[TEST])
    3. Markdown lint 80-chars/linha em TODAS docs criadas/editadas

### Corrigido
- **BUG: Treino concorrente não estava ativando via iniciar.bat** (20/02/2026)
  - Problema 1: Variáveis `TRAINING_FLAG` e `TRAINING_INTERVAL_FLAG` não inicializadas antes do bloco if  
  - Problema 2: Inicialização COM aspas vs SET SEM aspas causava inconsistência em delayed expansion
  - Problema 3: Parêntese `hora(s)` em echo fechava bloco if prematuramente
  - Solução: (1) Inicializar antes do if, (2) Sintaxe consistente, (3) Escape ^( e ^)
  - Commits: 1e5b97a, 7ad8ab5, 6cf93cd, 0d3511c (success)
  - Status: LIVE — Treino concorrente ativado e operacional em produção
  - Sincronização obrigatória de documentação rastreada em docs/SYNCHRONIZATION.md

- **BUG no truncation check de episódios (F-06)**
  - Comparava `current_step >= episode_length` em vez de `(current_step - start_step) >= episode_length`
  - Causava terminação prematura após 1-2 steps
  - Fix validado com E2E test de 50 steps

- **Dependencies adicionadas a requirements.txt**
  - scikit-learn>=1.3.0, scipy>=1.11.0 para DataLoader (F-08)

### Adicionado (Documentação)
- **docs/DOCUMENTACAO_SINCRONIZACAO_RELATORIO.md** (20/02/2026)
  - Mapa consolidado de todos os documentos
  - Matriz de interdependências
  - Checklist automático de sincronização (obrigatório)
  - Protocolo de sincronização OBRIGATÓRIA
  - Histórico de sincronizações recentes
  - Validações críticas pré-commit
  - Lições aprendidas e mecanismos de escalação

## [v0.2.1] — Administração de Posições (20/02/2026)

### Adicionado
- **9 Novos Pares USDT em Profit Guardian Mode**
  - TWT (Trust Wallet Token, β=2.0, mid_cap_utility)
  - LINK (Chainlink, β=2.3, mid_cap_oracle_infra)
  - OGN (Origin Protocol, β=3.2, low_cap_commerce) — CONSERVADOR
  - IMX (Immutable X, β=3.0, low_cap_l2_nft)
  - GTC, HYPER, 1000BONK, FIL, POLYX já existentes
  - **Total: 16 pares USDT suportados**

- **4 Novos Playbooks Especializados**
  - twt_playbook.py — Wallet ecosystem token
  - link_playbook.py — Oracle infrastructure
  - ogn_playbook.py — Commerce protocol (CONSERVADOR)
  - imx_playbook.py — Layer 2 NFT/Gaming
  - Cada playbook: ajustes de confluência, risk multipliers, regras de trade

- **Mecanismos de Sincronização de Documentação**
  - Novo arquivo: docs/SYNCHRONIZATION.md (rastreamento obrigatório)
  - Protocolo de sincronização em .github/copilot-instructions.md
  - Checklist automático de atualização
  - Matriz de dependências de documentação

### Alterado
- README.md: Atualizado com 16 pares categorizados por beta e maturidade
- .github/copilot-instructions.md: Adicionadas regras de sincronização obrigatória

### Validado
- test_admin_9pares.py: 36/36 validações OK
- Todos os símbolos em SYMBOLS
- Todos os playbooks criados e registrados
- AUTHORIZED_SYMBOLS auto-sincronizado via ALL_SYMBOLS
  - Analisa quantidade de candles disponíveis por timeframe (H1, H4, D1)
  - Calcula requisitos considerando split treino/validação e min_length
  - Verifica requisitos de indicadores (ex: EMA_610 precisa de 610+ candles D1)
  - Verifica atualização dos dados (detecta dados desatualizados >24h)
  - Retorna diagnóstico detalhado com recomendações acionáveis
- Integração do diagnóstico no `train_model()` - agora para com mensagem clara se dados insuficientes (sem fallback silencioso)
- Script de demonstração `test_diagnosis_demo.py` para visualizar o diagnóstico
- Testes abrangentes em `tests/test_data_diagnostics.py` (6 testes, 100% cobertura)

### Modificado
- `HISTORICAL_PERIODS` em `config/settings.py`:
  - H4: 180 → 250 dias (para suportar min_length=1000 com split 80/20)
  - D1: 365 → 730 dias (para suportar EMA_610 com margem)
  - H1: 90 → 120 dias (ajuste para consistência)
- `_validate_data()` em `agent/data_loader.py` agora exibe mensagens mais informativas com cálculo de dias necessários e recomendações
- `collect_historical_data()` em `main.py` agora usa valores de `HISTORICAL_PERIODS` do settings.py
- `RL_TRAINING_GUIDE.md` atualizado com seção sobre diagnóstico de dados e requisitos mínimos

### Corrigido
- 🐛 **FIX:** Problema do fallback silencioso para dados sintéticos quando usuário esperava treinar com dados reais
- 🐛 **FIX:** Mensagens de erro genéricas substituídas por diagnósticos detalhados e acionáveis
- 🐛 **FIX:** Falta de visibilidade sobre requisitos de dados antes de iniciar treinamento demorado

## [0.2.0] — 2026-02-15 (Pipeline Fix)

### Corrigido
- 🐛 **FIX:** Integrado `multi_tf_result` no `build_observation` — Blocos 7 e 8 agora usam valores reais de correlação BTC, beta, D1 bias e market regime
- 🐛 **FIX:** Corrigida lógica de R-multiple no `RewardCalculator` — if/elif invertidos para que bonus de 3R+ funcione corretamente
- 🐛 **FIX:** Corrigido mapeamento de FVG distance features no bloco SMC — índices 13-14 agora calculam distâncias de FVG ao invés de liquidity sweeps
- 🐛 **FIX:** Sincronizado `get_feature_names()` com `build_observation()` — agora retorna exatamente 104 nomes com padding

### Adicionado
- ✨ **FEAT:** Testes unitários para `FeatureEngineer` (10 testes)
- ✨ **FEAT:** Testes unitários para `MultiTimeframeAnalysis` (9 testes)
- ✨ **FEAT:** Testes unitários para `RewardCalculator` (10 testes)

## [0.1.0] — 2026-02-15 (Foundation)

### Adicionado
- Arquitetura completa em camadas (data → indicators → features → agent → execution)
- Coleta de dados Binance (OHLCV H1/H4/D1)
- 22+ indicadores técnicos (EMAs, RSI, MACD, BB, VP, OBV, ATR, ADX)
- Smart Money Concepts completo (Swings, BOS, CHoCH, OBs, FVGs, Liquidity, Premium/Discount)
- Análise multi-timeframe (D1 Bias, Market Regime, Correlação/Beta BTC)
- Feature Engineering (104 features normalizadas)
- Gymnasium Environment estruturado (PPO, 5 ações)
- Risk Manager com regras invioláveis
- Reward Calculator multi-componente
- Database SQLite
- Coleta de sentimento (Funding Rate, OI, Long/Short Ratio)
- Coleta de dados macro (Fear&Greed, DXY, BTC Dominance)
- Dry-run pipeline com dados sintéticos
- Position Monitor
- Scheduler básico
- Logging estruturado
