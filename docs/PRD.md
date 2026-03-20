# PRD — crypto-futures-agent

**Versão:** 1.0.0
**Data:** 2026-03-20
**Autor:** Arquiteto de Soluções Sênior / Product Owner
**Status:** APROVADO PARA REVISÃO

---

## Sumário

- [1. Visão Geral](#1-visão-geral)
- [2. Análise de Viabilidade Técnica e Riscos](#2-análise-de-viabilidade-técnica-e-riscos)
- [3. Objetivos e KPIs](#3-objetivos-e-kpis)
- [4. Personas e User Stories](#4-personas-e-user-stories)
- [5. Requisitos Funcionais](#5-requisitos-funcionais)
- [6. Requisitos Não-Funcionais](#6-requisitos-não-funcionais)
- [7. Stack Tecnológica](#7-stack-tecnológica)
- [8. Plano de Release — Fases e MVP](#8-plano-de-release--fases-e-mvp)
- [9. Glossário](#9-glossário)

---

## 1. Visão Geral

### 1.1 Problema

Operadores de criptomoedas no mercado de futuros enfrentam três desafios
centrais:

1. **Volume e velocidade:** O mercado opera 24/7 com dezenas de pares
   simultâneos — impossível para análise manual em escala.
2. **Disciplina emocional:** Decisões humanas sofrem viés cognitivo (FOMO,
   over-trading, hesitação em stop loss), degradando o resultado esperado.
3. **Fragmentação de ferramentas:** Análise técnica, gestão de risco,
   execução de ordens e monitoramento ficam em sistemas separados, criando
   latência e inconsistências operacionais.

### 1.2 Solução

O **crypto-futures-agent** é um agente autônomo de negociação de futuros de
criptomoedas na Binance, combinando duas camadas de decisão:

- **Camada Determinística (Modelo 2.0):** Pipeline de 5 etapas baseado em
  Smart Money Concepts (SMC) — detecção de padrões, rastreamento de tese,
  conversão em sinal, admissão de ordem e execução nativa.
- **Camada de Aprendizado por Reforço (PPO/LSTM):** Modelo PPO que gradua
  sinais determinísticos com confiança aprendida, melhorando sizing e
  filtragem de entradas ao longo do tempo.

### 1.3 Proposta de Valor

| Dimensão | Benefício Entregue |
| --------- | ------------------ |
| Velocidade | Scan de 40+ pares simultâneos em cada candle novo |
| Disciplina | Regras de negócio invioláveis codificadas no sistema |
| Rastreabilidade | Audit trail completo de cada decisão (DB canônico) |
| Segurança | Circuit breaker automático, stop loss obrigatório |
| Evolução | Modelo RL que aprende com o histórico de sinais |

---

## 2. Análise de Viabilidade Técnica e Riscos

### 2.1 Pontos Fortes Identificados

- **Pipeline bem definido:** A separação em 5 camadas com
  responsabilidades claras facilita manutenção e evolução independente de
  cada etapa.
- **Estado auditável:** O uso de máquinas de estado explícitas
  (`IDENTIFICADA → MONITORANDO → VALIDADA → EXPIRADA/INVALIDADA`) garante
  idempotência e rastreabilidade completa.
- **Controles de risco invioláveis:** `risk_gate.py` e `circuit_breaker.py`
  estão no caminho crítico de toda execução live; remoção deliberada
  exigiria modificação estrutural, reduzindo risco de bypass acidental.
- **Cobertura de testes adequada:** 112 arquivos de teste cobrindo unidade,
  integração e pipeline completo.

### 2.2 Riscos e Falhas Lógicas Identificadas

> ⚠️ **Seção crítica** — pontos onde a arquitetura atual tem lacunas que
> devem ser endereçadas antes da operação live em escala.

| # | Risco | Severidade | Observação |
| --- | ----- | ---------- | ---------- |
| R-01 | **SQLite em produção** — escritas concorrentes de múltiplos processos (scanner, executor, reconciliador) em `modelo2.db` podem gerar `database is locked` sob carga | Alta | SQLite é single-writer; processos assíncronos precisam de WAL mode habilitado e retry com back-off |
| R-02 | **RL em mercados financeiros não-estacionários** — modelos PPO treinados em janelas históricas tendem a overfitting; o mercado muda de regime (bull/bear/sideways) quebrando políticas otimizadas | Alta | Necessário mecanismo de detecção de drift e retreino automático com validação walk-forward |
| R-03 | **Setup Windows-only** — scripts `setup.bat` e `iniciar.bat` limitam o ambiente de produção a Windows, inviabilizando deploy em servidores Linux/cloud | Média | Criar equivalentes `Makefile` ou `setup.sh`; dockerizar para eliminar dependência de SO |
| R-04 | **Ausência de streaming de dados em tempo real** — o sistema consome candles OHLCV fechados (batch), introduzindo latência de até um candle inteiro antes de reagir a um sinal | Média | Para scalping/operações de curto prazo isso é inaceitável; para swing trade (H4/D1) é aceitável |
| R-05 | **Credenciais em `.env` local** — chaves Binance armazenadas em arquivo plano sem rotação ou secret manager; risco de exfiltração caso o repositório seja exposto | Alta | Integrar com vault (ex.: HashiCorp Vault, AWS Secrets Manager) ou variáveis de ambiente CI/CD |
| R-06 | **Sem mecanismo de rollback de ordens** — se a proteção (STOP/TP) falhar no envio após a entrada MARKET ser executada, a posição fica desprotegida | Alta | Implementar idempotência com retry e verificação de estado pós-envio de proteção |
| R-07 | **Modelo RL único para 40+ símbolos** — política global tende a generalizar mal para ativos com beta e liquidez muito distintos (DOGE vs BTC) | Média | Iniciativa M2-019 (RL por símbolo) já está no backlog; deve ser priorizada |
| R-08 | **Ausência de testes de carga e stress** — comportamento do pipeline sob alta volatilidade (ex.: liquidação em cascata, falha da API Binance) não está coberto | Média | Adicionar chaos tests e mock de falhas da API |

### 2.3 Viabilidade Geral

O projeto é tecnicamente viável para **operação paper trading e swing trade
live em escala de 1 usuário**. Para escala multi-usuário ou HFT, as
mitigações dos riscos R-01, R-04 e R-07 são bloqueantes.

---

## 3. Objetivos e KPIs

### 3.1 Objetivos Estratégicos

| OBJ | Descrição |
| ---- | --------- |
| OBJ-01 | Executar operações rentáveis de forma autônoma no mercado de futuros da Binance |
| OBJ-02 | Manter drawdown máximo controlado com circuit breaker automático |
| OBJ-03 | Evoluir continuamente a política de decisão via aprendizado por reforço |
| OBJ-04 | Fornecer rastreabilidade completa de cada decisão para auditoria |

### 3.2 KPIs por Camada

#### Performance de Trading

| KPI | Meta MVP | Meta v1.0 | Método de Medição |
| --- | -------- | --------- | ----------------- |
| Win Rate (taxa de acerto) | ≥ 45% | ≥ 55% | `signal_executions` resolvidas como lucro / total |
| Profit Factor | ≥ 1.3 | ≥ 1.8 | Soma de ganhos / soma de perdas |
| Sharpe Ratio anualizado | ≥ 0.8 | ≥ 1.5 | `backtest_metrics.py` |
| Max Drawdown | ≤ −15% | ≤ −10% | `circuit_breaker.py` threshold |
| Latência entrada (MARKET) | ≤ 500 ms | ≤ 200 ms | Timestamp order_sent − signal_created |

#### Pipeline de Sinais

| KPI | Meta MVP | Meta v1.0 | Método de Medição |
| --- | -------- | --------- | ----------------- |
| Oportunidades identificadas / dia | ≥ 5 | ≥ 20 | `opportunities` table count |
| Taxa de validação de teses | ≥ 30% | ≥ 40% | VALIDADA / (VALIDADA + INVALIDADA) |
| Taxa de conversão sinal → ordem | ≥ 80% | ≥ 90% | CONSUMED / (CONSUMED + CANCELLED) |
| Integridade do audit trail | 100% | 100% | Ausência de `opportunity_events` faltantes |

#### Aprendizado por Reforço

| KPI | Meta | Método de Medição |
| --- | ---- | ----------------- |
| Convergência do treinamento PPO | ≤ 500k steps | `convergence_monitor.py` |
| Melhora de Win Rate com RL vs sem RL | ≥ +5 pp | A/B em paper trading |
| Detecção de drift de regime | ≤ 48h | Alerta automático no log |

---

## 4. Personas e User Stories

### 4.1 Personas

#### P-01: Trader Quantitativo Independente

- **Perfil:** Desenvolvedor/trader com conhecimento de Python e mercado
  financeiro; opera com capital próprio de R$10k–R$200k.
- **Objetivo:** Automatizar estratégias SMC já validadas manualmente,
  aumentando escala sem aumentar tempo dedicado.
- **Frustração:** Ferramentas de automação existentes são genéricas demais
  (sem SMC), caras (assinatura SaaS) ou inseguras.

#### P-02: Analista Técnico em Transição para Automação

- **Perfil:** Experiência em análise técnica (Smart Money, ICT), iniciante
  em programação; quer reduzir viés emocional.
- **Objetivo:** Codificar suas regras de entrada/saída e deixar o sistema
  operar 24/7 com discipline enforcement.
- **Frustração:** Não executa suas próprias ideias por medo de perder o
  controle ou por dificuldade técnica.

#### P-03: Pesquisador de Sistemas de Trading Algorítmico

- **Perfil:** Mestrando/doutorando ou profissional de quant finance
  explorando RL aplicado a mercados de alta volatilidade.
- **Objetivo:** Usar o projeto como plataforma de pesquisa para testar
  hipóteses de policy gradient em dados de cripto.
- **Frustração:** Faltam ambientes de backtesting com dados reais de
  futuros e integração nativa com exchanges.

### 4.2 User Stories

| ID | Persona | Eu quero... | Para... | Critério de Aceite |
| -- | ------- | ----------- | ------- | ------------------ |
| US-01 | P-01 | Configurar os símbolos e timeframes que o scanner deve monitorar | Focar em pares de alta liquidez | Editar `config/symbols.py` e reiniciar; scanner opera apenas nos símbolos configurados |
| US-02 | P-01 | Ver em tempo real quais oportunidades estão sendo rastreadas | Auditar a lógica sem intervenção manual | `python status_realtime.py` exibe estado atual de todas as `opportunities` abertas |
| US-03 | P-02 | Definir stop loss e take profit como percentual do preço de entrada | Garantir relação risco/retorno mínima | `risk_params.py` aceita `stop_pct` e `tp_pct`; sistema rejeita ordens fora da faixa configurada |
| US-04 | P-02 | Receber notificação quando uma ordem for executada | Acompanhar operações sem monitorar tela | Telegram alert disparado em `signal_execution` com status PROTECTED |
| US-05 | P-01 | Rodar backtest de uma estratégia antes de ativá-la em live | Validar parâmetros sem risco real | `python main.py --mode paper` executa com dados históricos e retorna métricas de Sharpe e max drawdown |
| US-06 | P-03 | Treinar um modelo PPO isolado por símbolo | Comparar performance por ativo | `python scripts/model2/train_entry_agents.py --symbol BTCUSDT` treina e salva checkpoint |
| US-07 | P-01 | Pausar o agente imediatamente em caso de perda acima de X% no dia | Evitar blow-up de capital | Circuit breaker ativa `HALT` automaticamente; `python status.py` confirma estado HALTED |
| US-08 | P-03 | Exportar histórico completo de sinais e execuções para análise | Pesquisar features e patterns | `SELECT * FROM signal_executions` em `modelo2.db` com todos os campos documentados |

---

## 5. Requisitos Funcionais

> Formato: RF-[Módulo]-[Número] | Prioridade: P0 (bloqueante MVP), P1
> (essencial v1.0), P2 (melhoria futura)

### 5.1 Scanner de Oportunidades (Camada 1)

| ID | Descrição | Prioridade |
| -- | --------- | ---------- |
| RF-SC-001 | O sistema deve detectar padrões SMC (Order Blocks, Fair Value Gaps, falha de venda/compra) em dados OHLCV de múltiplos timeframes (D1, H4, H1) | P0 |
| RF-SC-002 | Cada oportunidade detectada deve ser persistida em `opportunities` com status inicial `IDENTIFICADA` e timestamp de criação | P0 |
| RF-SC-003 | O scanner deve operar sobre todos os símbolos configurados em `config/symbols.py` a cada ciclo de candle novo | P0 |
| RF-SC-004 | O sistema deve registrar zona de entrada, alvo (TP) e nível de invalidação (SL) no momento da identificação | P0 |
| RF-SC-005 | Oportunidades duplicadas para o mesmo símbolo/timeframe devem ser idempotentes (sem inserção duplicada) | P1 |

### 5.2 Rastreador e Validador de Tese (Camada 2)

| ID | Descrição | Prioridade |
| -- | --------- | ---------- |
| RF-VL-001 | O rastreador deve atualizar o estado de oportunidades a cada novo candle para `MONITORANDO`, `VALIDADA`, `INVALIDADA` ou `EXPIRADA` | P0 |
| RF-VL-002 | Uma tese deve ser marcada `VALIDADA` somente quando todos os critérios de confirmação SMC definidos em `REGRAS_DE_NEGOCIO.md` forem satisfeitos | P0 |
| RF-VL-003 | Teses com TTL expirado (sem validação dentro do prazo) devem ser marcadas `EXPIRADA` automaticamente | P0 |
| RF-VL-004 | Toda transição de estado deve gerar um registro em `opportunity_events` com timestamp e motivo | P0 |
| RF-VL-005 | O sistema não deve reabrir teses `INVALIDADA` ou `EXPIRADA` para o mesmo gatilho | P1 |

### 5.3 Ponte de Sinal (Camada 3)

| ID | Descrição | Prioridade |
| -- | --------- | ---------- |
| RF-SB-001 | Teses `VALIDADA` devem ser convertidas em registros padronizados em `technical_signals` com status `CREATED` | P0 |
| RF-SB-002 | O sinal deve conter direção (LONG/SHORT), preço de entrada, SL, TP, símbolo, timeframe e referência à oportunidade de origem | P0 |
| RF-SB-003 | A conversão deve ser idempotente: uma tese não deve gerar mais de um sinal ativo simultaneamente | P0 |

### 5.4 Camada de Ordem (Camada 4)

| ID | Descrição | Prioridade |
| -- | --------- | ---------- |
| RF-OL-001 | O sistema deve consumir sinais `CREATED` e verificar limite diário de entradas (`M2_MAX_DAILY_ENTRIES`) antes de aprovar | P0 |
| RF-OL-002 | Sinais que excedam o limite diário devem ser marcados `CANCELLED` com motivo registrado | P0 |
| RF-OL-003 | O sistema deve verificar razão risco/retorno mínima (configurável) antes de aprovar a entrada | P0 |
| RF-OL-004 | Sinais aprovados devem transitar para `CONSUMED` e ser entregues à Camada 5 | P0 |

### 5.5 Execução Live (Camada 5)

| ID | Descrição | Prioridade |
| -- | --------- | ---------- |
| RF-EX-001 | O sistema deve enviar ordem MARKET na entrada; imediatamente após o fill, armar STOP_MARKET e TAKE_PROFIT_MARKET | P0 |
| RF-EX-002 | Se o envio de ordens de proteção falhar, o sistema deve tentar novamente (retry com back-off exponencial, mínimo 3 tentativas) | P0 |
| RF-EX-003 | O reconciliador deve verificar continuamente o estado das ordens abertas na Binance e sincronizar com `signal_executions` | P0 |
| RF-EX-004 | O sistema deve detectar saídas externas (liquidação manual, liquidação forçada) e atualizar o estado para `EXITED` | P0 |
| RF-EX-005 | Toda execução deve ser precedida de validação pelo `risk_gate.py`; ordens reprovadas devem ser registradas com motivo | P0 |

### 5.6 Gestão de Risco

| ID | Descrição | Prioridade |
| -- | --------- | ---------- |
| RF-RK-001 | O circuit breaker deve monitorar drawdown diário e ativar `HALT` automático quando o limite configurado for atingido | P0 |
| RF-RK-002 | Stop loss deve ser obrigatório em toda ordem; ordens sem SL devem ser rejeitadas antes do envio | P0 |
| RF-RK-003 | O sizing de posição deve ser calculado em função do capital disponível, stop percentual e alavancagem configurada | P0 |
| RF-RK-004 | O sistema deve impedir alavancagem acima do limite configurado em `risk_params.py` | P0 |

### 5.7 Aprendizado por Reforço (RL)

| ID | Descrição | Prioridade |
| -- | --------- | ---------- |
| RF-RL-001 | O agente PPO deve receber vetores de features de sinais técnicos e retornar um escore de confiança (0–1) | P1 |
| RF-RL-002 | O ambiente de treino deve suportar sequências LSTM de comprimento configurável (padrão seq_len=10, n_features=20) | P1 |
| RF-RL-003 | O sistema deve suportar retreino com parâmetros otimizados via Optuna sem interromper o pipeline de produção | P1 |
| RF-RL-004 | O modelo RL deve poder operar em modo degradado (fallback determinístico) caso o checkpoint não esteja disponível | P0 |
| RF-RL-005 | Deve haver suporte a modelos RL individuais por símbolo para capturar idiossincrasias de cada ativo | P2 |

### 5.8 Backtest e Validação

| ID | Descrição | Prioridade |
| -- | --------- | ---------- |
| RF-BT-001 | O backtester deve suportar walk-forward validation com janelas de treino e teste configuráveis | P1 |
| RF-BT-002 | As métricas de saída devem incluir: Sharpe Ratio, Sortino Ratio, max drawdown, win rate, profit factor e número de trades | P1 |
| RF-BT-003 | O backtester deve ser idêntico ao pipeline live para garantir ausência de look-ahead bias | P1 |

### 5.9 Observabilidade e Auditoria

| ID | Descrição | Prioridade |
| -- | --------- | ---------- |
| RF-OB-001 | O sistema deve gerar snapshots periódicos do estado do pipeline em `observability.py` | P1 |
| RF-OB-002 | Notificações Telegram devem ser enviadas nos eventos: entrada executada, proteção armada, saída detectada, circuit breaker ativado | P1 |
| RF-OB-003 | Logs estruturados devem ser gerados para todos os eventos críticos com nível, timestamp, símbolo e contexto | P0 |

---

## 6. Requisitos Não-Funcionais

### 6.1 Desempenho

| ID | Requisito | Métrica | Prioridade |
| -- | --------- | ------- | ---------- |
| RNF-DE-001 | Latência fim-a-fim sinal → ordem MARKET enviada | ≤ 500 ms (paper), ≤ 200 ms (live) | P0 |
| RNF-DE-002 | Throughput do scanner sobre 40 símbolos por candle | ≤ 5 s por ciclo completo | P0 |
| RNF-DE-003 | Tempo de retreino PPO completo (500k steps) | ≤ 2 h em hardware local (GPU opcional) | P1 |
| RNF-DE-004 | Tempo de inicialização do pipeline completo | ≤ 30 s | P1 |

### 6.2 Segurança

| ID | Requisito | Métrica | Prioridade |
| -- | --------- | ------- | ---------- |
| RNF-SE-001 | Credenciais Binance nunca devem ser hardcoded ou commitadas no repositório | 0 ocorrências em `git log` | P0 |
| RNF-SE-002 | Chaves de API devem ser lidas exclusivamente via variáveis de ambiente ou secret manager | Validado por `go_live_preflight.py` | P0 |
| RNF-SE-003 | Comunicação com a API Binance deve usar TLS 1.2+ | Verificado pelo SDK oficial | P0 |
| RNF-SE-004 | O banco `modelo2.db` deve ter permissões restritas ao processo do agente (chmod 600 em Linux) | Verificado no deploy | P1 |
| RNF-SE-005 | Toda ordem live deve ser precedida de checklist automatizado (`go_live_preflight.py`) sem erros | 0 erros no preflight | P0 |

### 6.3 Disponibilidade

| ID | Requisito | Métrica | Prioridade |
| -- | --------- | ------- | ---------- |
| RNF-DI-001 | O pipeline deve se recuperar automaticamente de falhas transientes da API Binance (rate limit, timeout) com retry e back-off exponencial | ≥ 3 retentativas antes de abort | P0 |
| RNF-DI-002 | Em caso de restart do processo, o sistema deve retomar o estado persistido sem criar ordens duplicadas (idempotência de re-entrada) | Validado por teste de integração | P0 |
| RNF-DI-003 | O circuit breaker deve permanecer ativo mesmo após restart do processo | Estado persistido em DB | P0 |

### 6.4 Escalabilidade

| ID | Requisito | Métrica | Prioridade |
| -- | --------- | ------- | ---------- |
| RNF-ES-001 | Adicionar novo símbolo ao pipeline deve exigir apenas inserção em `config/symbols.py` sem alteração de código | Validado por convenção arquitetural | P0 |
| RNF-ES-002 | O banco `modelo2.db` deve suportar 12 meses de histórico de operações sem degradação de consulta | ≤ 100 ms para queries de auditoria com índices | P1 |
| RNF-ES-003 | A arquitetura deve permitir migração futura para PostgreSQL substituindo apenas a camada de repositório (`repository.py`) | Sem SQL vendor-specific fora de `repository.py` | P2 |

### 6.5 Manutenibilidade

| ID | Requisito | Métrica | Prioridade |
| -- | --------- | ------- | ---------- |
| RNF-MA-001 | Cobertura de testes ≥ 80% nos módulos críticos (risk, execution, core/model2) | Medido por `pytest --cov` | P1 |
| RNF-MA-002 | Toda mudança de schema no DB deve ser aplicada via migration versionada (`scripts/model2/migrations/*.sql`) | 0 alterações diretas de schema fora de migrations | P0 |
| RNF-MA-003 | Código deve passar em linter (`markdownlint`, `mypy --strict`) sem erros nos módulos críticos | CI verde obrigatório antes de merge | P1 |
| RNF-MA-004 | Documentação de regras de negócio (`REGRAS_DE_NEGOCIO.md`) deve ser atualizada junto com toda mudança de lógica de validação | Revisão humana obrigatória no PR | P0 |

---

## 7. Stack Tecnológica

### 7.1 Decisões Atuais e Justificativas

| Componente | Tecnologia Atual | Justificativa | Alternativa Considerada |
| ---------- | ---------------- | ------------- | ----------------------- |
| **Linguagem** | Python 3.8+ | Ecossistema de ML/quant finance maduro; Stable-Baselines3, PyTorch, Pandas, TA-Lib nativos | Go (performance), Rust (latência) — descartados pela ausência de ecossistema RL comparável |
| **Exchange API** | Binance SDK Derivatives (USDS Futures) | SDK oficial com suporte a STOP_MARKET e TAKE_PROFIT_MARKET nativos; rate limiting gerenciado | CCXT (mais genérico, menos controle sobre tipos de ordem específicos) |
| **Banco de Dados** | SQLite3 (dual DB) | Zero-setup, transacional, auditável; adequado para 1 usuário/processo | PostgreSQL (multi-user, WAL robusto) — planejado para v2.0 |
| **RL Framework** | Stable-Baselines3 + PPO | Implementação PPO estável, bem testada, integração nativa com Gymnasium | RLlib (mais complexo, overhead de cluster), custom PPO (risco de bugs) |
| **Deep Learning** | PyTorch ≥ 2.0 | Backend do SB3; suporte nativo CUDA para treino acelerado | TensorFlow — descartado por ruptura de API histórica |
| **Hyperparameter Search** | Optuna | Busca bayesiana eficiente, persistência de trials, suporte a pruning | Ray Tune — funcionalidade equivalente com overhead maior |
| **Scheduling** | APScheduler + schedule | Simplicidade; adequado para processo único local | Celery (overkill para 1 processo), Airflow (infraestrutura excessiva) |
| **CI/CD** | GitHub Actions | Integração nativa com repositório; workflows de lint e validação de docs já configurados | Jenkins, GitLab CI — sem vantagem para projeto open/individual |
| **Deploy** | Script local (Windows) + systemd (Linux planejado) | Fase atual é single-user local; systemd para persistência em servidor | Docker — **recomendado** para eliminar dependência de SO |

### 7.2 Recomendações de Evolução

```
Fase atual (MVP)          →  Fase v1.0              →  Fase v2.0
─────────────────────────────────────────────────────────────────
SQLite (WAL mode)         →  PostgreSQL              →  TimescaleDB
Script local              →  Docker Compose          →  Kubernetes
Credenciais em .env       →  Variáveis CI/CD         →  HashiCorp Vault
Modelo RL global          →  RL por símbolo          →  Ensemble adaptativo
Batch OHLCV               →  WebSocket streaming     →  CEP (event processing)
```

---

## 8. Plano de Release — Fases e MVP

### 8.1 Princípio de Priorização

Entregar primeiro o **controle de risco** e a **rastreabilidade**; depois
**rentabilidade**; por último **escalabilidade**. Um sistema que perde
capital de forma incontrolável é pior que um sistema parado.

### 8.2 Fases

#### Fase 0 — Fundação (CONCLUÍDA)

> Sprint de estabilização arquitetural: pipeline determinístico 5 camadas
> operacional em paper trading.

| Entregável | Status |
| ---------- | ------ |
| Pipeline 5 camadas (Scanner → Execução) | ✅ Completo |
| Circuit breaker e risk gate invioláveis | ✅ Completo |
| Banco canônico `modelo2.db` com migrations | ✅ Completo |
| Suite de testes (112 arquivos) | ✅ Completo |
| Documentação de regras de negócio | ✅ Completo |

#### Fase 1 — MVP Operacional (EM CURSO — Sprint Atual)

> **Meta:** Operação live real com controle de risco validado e RL básico.

| ID | Entregável | Critério de Aceite | Prazo |
| -- | ---------- | ------------------ | ----- |
| M1-01 | Execução live com STOP + TP nativos Binance | 10 operações paper sem erro de proteção | Sprint atual |
| M1-02 | Reconciliação de ordens e detecção de saída externa | 0 posições órfãs após 24h de paper | Sprint atual |
| M1-03 | PPO global treinado e integrado ao order_layer | Melhora ≥ +3 pp Win Rate vs baseline | Sprint +1 |
| M1-04 | Checklist preflight live automático | `go_live_preflight.py` sem falhas | Sprint +1 |
| M1-05 | Dockerfile para deploy Linux | Container sobe e opera paper em Ubuntu 22.04 | Sprint +2 |
| M1-06 | Mitigação R-01 (SQLite WAL + retry) | 0 erros `database is locked` em 48h de operação contínua | Sprint +2 |

#### Fase 2 — Consolidação e Resiliência (v0.9)

> **Meta:** Sistema estável para operação live prolongada; RL por símbolo.

| ID | Entregável | Critério de Aceite |
| -- | ---------- | ------------------ |
| M2-01 | RL individual por símbolo (M2-019) | Modelo por símbolo ≥ performance modelo global |
| M2-02 | Detecção automática de drift de regime | Alerta em ≤ 48h após mudança de regime |
| M2-03 | WebSocket streaming de dados (substituir batch) | Latência sinal → ordem ≤ 200 ms |
| M2-04 | Chaos tests (mock de falha API Binance) | Pipeline se recupera em ≤ 60s após falha simulada |
| M2-05 | Integração com secret manager | 0 credenciais em arquivos locais |

#### Fase 3 — Escala (v1.0)

> **Meta:** Multi-usuário, observabilidade avançada, PostgreSQL.

| ID | Entregável | Critério de Aceite |
| -- | ---------- | ------------------ |
| M3-01 | Migração para PostgreSQL | 0 regressões em suite de testes existente |
| M3-02 | Dashboard web de observabilidade | Métricas live acessíveis via browser |
| M3-03 | API REST para consulta de status e controle | Especificação OpenAPI 3.0 publicada |
| M3-04 | Multi-tenant (múltiplos usuários isolados) | Isolamento de DB e configuração por tenant |

### 8.3 Critérios de Go/No-Go para Live Real

Antes de qualquer operação live com capital real, os seguintes critérios
devem ser satisfeitos:

- [ ] `go_live_preflight.py` executa sem nenhum erro
- [ ] Mínimo de 30 dias de paper trading com Win Rate ≥ 45%
- [ ] Circuit breaker testado e validado em paper (não apenas unitariamente)
- [ ] Toda posição aberta tem STOP_MARKET confirmado na Binance
- [ ] Logs e audit trail acessíveis e legíveis
- [ ] Capital inicial não superior ao limite configurado em `risk_params.py`

---

## 9. Glossário

| Termo | Definição |
| ----- | --------- |
| **SMC** | Smart Money Concepts — metodologia de análise técnica baseada em rastreamento de liquidez e fluxo institucional |
| **Order Block** | Zona de preço onde houve acumulação/distribuição institucional relevante |
| **FVG** | Fair Value Gap — desequilíbrio de preço entre candles consecutivos |
| **Tese** | Hipótese de trade com entrada, alvo e invalidação definidos |
| **Idempotência** | Propriedade de operações que produzem o mesmo resultado independente do número de execuções |
| **Walk-forward** | Técnica de validação temporal que evita look-ahead bias em backtesting |
| **Circuit Breaker** | Mecanismo automático de parada do sistema ao atingir limite de perda configurado |
| **Drift de Regime** | Mudança estatística no comportamento do mercado que invalida uma política RL treinada |
| **WAL** | Write-Ahead Logging — modo de operação do SQLite que permite leituras concorrentes durante escritas |
| **PPO** | Proximal Policy Optimization — algoritmo de aprendizado por reforço baseado em gradiente de política |
| **LSTM** | Long Short-Term Memory — arquitetura de rede neural recorrente para dados sequenciais |

---

*Este documento é a fonte de verdade para requisitos do crypto-futures-agent.*
*Atualizações devem ser registradas em `docs/SYNCHRONIZATION.md` com tag*
*`[SYNC]`.*
