# PRD - crypto-futures-agent

**Produto:** Agente especialista em posicoes short de futuros de
criptomoedas na Binance  
**Versao do Documento:** 1.0  
**Versao do Produto:** 0.1.0  
**Data:** 2026-03-21  
**Autor:** Arquiteto de Solucoes Senior  
**Status:** FONTE DA VERDADE

> Este documento substitui `docs/prd_short.md` e
> `docs/PRD_SHORT_AGENT.html` e passa a ser a unica referencia de produto
> do projeto.

---

## Sumario

- [1. Visao do Produto](#1-visao-do-produto)
- [2. Problema que Resolve](#2-problema-que-resolve)
- [3. Objetivos e KPIs](#3-objetivos-e-kpis)
- [4. Publico-Alvo e Casos de Uso](#4-publico-alvo-e-casos-de-uso)
- [5. Escopo e Arquitetura Atual](#5-escopo-e-arquitetura-atual)
- [6. Requisitos Funcionais](#6-requisitos-funcionais)
- [7. Requisitos Nao Funcionais](#7-requisitos-nao-funcionais)
- [8. Arquitetura Tecnica e Stack](#8-arquitetura-tecnica-e-stack)
- [9. Riscos e Mitigacoes](#9-riscos-e-mitigacoes)
- [10. Release Atual, Backlog Prioritario e Go No-Go](#10-release-atual-backlog-prioritario-e-go-no-go)
- [11. Glossario](#11-glossario)
- [12. Operacao com Copilot](#12-operacao-com-copilot)

---

## 1. Visao do Produto

O **crypto-futures-agent** e um agente autonomo especializado em
**posicoes short** para contratos perpetuos de criptomoedas na Binance
Futures. O produto identifica, avalia, admite e executa oportunidades de
venda em ativos de alta liquidez, combinando:

- pipeline operacional M2 com rastreabilidade ponta a ponta;
- contexto de mercado enriquecido com funding, basis e dados multi-timeframe;
- controles de risco fail-closed;
- camadas de ML e RL usadas para ranking, calibracao e promocao gradual.

### 1.1 Escopo operacional atual

| Dimensao | Posicao atual do projeto |
| --- | --- |
| Mercado | Binance USD-M Futures |
| Direcao operacional | Short-only em `live` |
| Modos suportados | `backtest`, `shadow`, `live` |
| Banco principal | `db/modelo2.db` |
| Agente dedicado | ciclo short com runtime proprio e artefatos operacionais |
| Usuario alvo | operacao single-user, conta propria |
| Promocao de mudancas | `shadow` antes de qualquer promocao para `live` |

### 1.2 Diferenciais do produto

| Diferencial | Beneficio entregue |
| --- | --- |
| Especializacao em short | captura movimentos de queda com regras especificas de futures |
| Gate de funding e basis | evita shorts caros ou estruturalmente desfavoraveis |
| Pipeline auditavel | cada oportunidade, sinal, execucao e bloqueio deixa trilha persistida |
| Risco no caminho critico | stop, limites, circuit breaker e preflight nao sao opcionais |
| Evolucao assistida por modelos | ML e RL entram por validacao gradual, sem romper o baseline operacional |

---

## 2. Problema que Resolve

| Dor do operador | Solucao do produto |
| --- | --- |
| Ficar exposto apenas a altas e perder movimentos fortes de queda | o agente opera vendido de forma sistematica, com foco em setups short |
| Ser liquidado ou sofrer perdas desproporcionais em futures | o pipeline aplica limites de exposicao, stop obrigatorio, hard caps e circuit breaker |
| Entrar vendido em contexto caro ou desfavoravel | funding e basis sao avaliados antes da execucao |
| Ter bom backtest e mau desempenho ao vivo | a promocao exige validacao em `shadow`, healthcheck e gate de risco de modelo |
| Nao conseguir explicar por que uma operacao entrou ou foi bloqueada | toda decisao gera motivo, status e timestamps em banco e artefatos operacionais |

---

## 3. Objetivos e KPIs

### 3.1 Objetivos estrategicos

| ID | Objetivo |
| --- | --- |
| OBJ-01 | Operar quedas do mercado de criptofuturos com preservacao de capital como restricao primaria |
| OBJ-02 | Manter uma esteira short-only segura, auditavel e repetivel em `shadow` e `live` |
| OBJ-03 | Incorporar ML/RL como camada de inteligencia validada, e nao como atalho operacional |
| OBJ-04 | Reduzir falsos positivos e custos de short com gates especificos de futures |
| OBJ-05 | Centralizar o contrato do produto em um unico PRD |

### 3.2 KPIs de trading e risco

| KPI | Meta atual |
| --- | --- |
| Win rate | >= 45% |
| Profit factor | >= 1.3 |
| Sharpe ratio | >= 0.8 |
| Max drawdown | <= 10% em janelas de 30 dias |
| Posicoes live protegidas | 100% |
| Posicoes preenchidas sem protecao | 0 |
| Tempo medio entre stop-loss | > 5 h |

### 3.3 KPIs operacionais e de modelo

| KPI | Meta atual |
| --- | --- |
| Preflight antes de live | 100% |
| Integridade do audit trail | 100% |
| Concordancia shadow vs promocao | >= 60% |
| Taxa de modelos rejeitados por overfitting | < 10% |
| Latencia de ordem em live | <= 300 ms |
| Alertas criticos | < 60 s |

---

## 4. Publico-Alvo e Casos de Uso

### 4.1 Publico-alvo

- **Trader individual:** operador com conta Futures na Binance que quer
  automatizar shorts com disciplina.
- **Perfil tecnico:** programador Python com conhecimento de mercado de criptomoedas.
- **Perfil de pesquisa:** usuario que quer testar features, modelos e
  politica RL sobre pipeline real e auditavel.

### 4.2 User stories

| ID | Usuario | Eu quero... | Para... |
| --- | --- | --- | --- |
| US-01 | Trader | configurar simbolos e timeframes autorizados | restringir o agente ao universo operacional desejado |
| US-02 | Trader | executar o ciclo dedicado do agente short em `shadow` ou `live` | rodar a operacao de forma repetivel |
| US-03 | Trader | bloquear shorts com funding ou basis desfavoravel | evitar entradas caras ou com estrutura ruim |
| US-04 | Trader | garantir protecao obrigatoria apos entrada | nao deixar posicoes descobertas |
| US-05 | Trader | receber trilha de auditoria para cada decisao | entender por que entrou, bloqueou ou saiu |
| US-06 | Pesquisador | comparar baseline operacional com ML/RL em `shadow` | validar ganho real antes da promocao |
| US-07 | Pesquisador | treinar modelos por simbolo e reprocessar episodios | capturar comportamento especifico de cada ativo |

---

## 5. Escopo e Arquitetura Atual

### 5.1 Mercados, simbolos e timeframes

- Mercado alvo: contratos perpetuos USD-M da Binance.
- Universo base: configurado centralmente em `config/symbols.py`.
- Universo live: allow-list via `M2_LIVE_SYMBOLS`.
- Timeframes operacionais: `D1`, `H4` e `H1`.
- Timeframe auxiliar de contexto: `M5` para sincronizacao
  tatico-operacional do ciclo short.

### 5.2 Modos de operacao

| Modo | Papel |
| --- | --- |
| `backtest` | validar a estrategia fora do ambiente operacional |
| `shadow` | executar o pipeline completo sem enviar ordens reais |
| `live` | executar ordens reais com gates, preflight e protecao obrigatoria |

### 5.3 Estrategias e camadas ativas

| Camada | Papel no produto | Status |
| --- | --- | --- |
| M2 deterministico | identifica, valida e materializa sinais tecnicos | Ativa |
| Short rules-based | baseline de execucao live | Ativa |
| LSTM + XGBoost | ranking e previsao de queda/volatilidade | Piloto |
| PPO/A2C | calibracao, confianca e priorizacao | Piloto |
| Modelos por simbolo | especializacao por ativo | Backlog prioritario |
| DRL comportamental / regime-aware | extensao de pesquisa | Futuro |

### 5.4 Fora de escopo na release atual

- Operacao spot.
- Estrategia long em `live`.
- Multiusuario e multi-tenant.
- Exchange adicional alem da Binance Futures.
- Escalada agressiva de alavancagem.

---

## 6. Requisitos Funcionais

> Prioridades: `P0` = bloqueante para a release atual, `P1` = essencial
> na proxima release operacional, `P2` = evolucao futura.

### 6.1 Orquestracao do ciclo short

| ID | Descricao | Prioridade |
| --- | --- | --- |
| RF-ORQ-001 | O agente short deve orquestrar sincronizacao de mercado, pipeline diario, execucao, persistencia de episodios e healthcheck em um ciclo unico | P0 |
| RF-ORQ-002 | O ciclo deve suportar execucao em `shadow` e `live` com saida operacional resumida e artefato persistido | P0 |
| RF-ORQ-003 | O ciclo deve operar apenas sobre simbolos autorizados para o contexto atual | P0 |
| RF-ORQ-004 | O runtime deve registrar status `ok`, `partial` ou `error` por ciclo executado | P1 |

### 6.2 Contexto de mercado e enriquecimento

| ID | Descricao | Prioridade |
| --- | --- | --- |
| RF-CTX-001 | O sistema deve sincronizar OHLCV multi-timeframe para o universo operacional | P0 |
| RF-CTX-002 | O sistema deve enriquecer contexto com funding rate, basis e demais features operacionais disponiveis | P0 |
| RF-CTX-003 | O sistema deve bloquear execucao quando o contexto critico estiver ausente, stale ou inconsistente | P0 |
| RF-CTX-004 | O conjunto de features deve aceitar extensao para open interest, sentimento e variaveis exogenas | P1 |

### 6.3 Pipeline M2 de oportunidade e sinal

| ID | Descricao | Prioridade |
| --- | --- | --- |
| RF-M2-001 | O scanner deve detectar oportunidades short em OHLCV multi-timeframe e persistir em `opportunities` | P0 |
| RF-M2-002 | O rastreador deve mover a tese por estados auditaveis ate `VALIDADA`, `INVALIDADA` ou `EXPIRADA` | P0 |
| RF-M2-003 | Toda transicao deve gerar evento com motivo e timestamp em `opportunity_events` | P0 |
| RF-M2-004 | Teses validadas devem gerar `technical_signals` padronizados e idempotentes | P0 |
| RF-M2-005 | Sinais devem carregar lado, preco de entrada, stop, alvo, simbolo, timeframe e referencia da tese | P0 |

### 6.4 Camada preditiva

| ID | Descricao | Prioridade |
| --- | --- | --- |
| RF-PR-001 | O produto deve suportar um modelo hibrido LSTM + XGBoost para prever probabilidade de queda e qualidade do contexto short | P1 |
| RF-PR-002 | As entradas do modelo devem aceitar OHLCV, indicadores tecnicos, funding, open interest e features enriquecidas | P1 |
| RF-PR-003 | A camada preditiva deve operar primeiro em `shadow` antes de qualquer promocao operacional | P0 |
| RF-PR-004 | O produto deve manter fallback para baseline rules-based quando o modelo nao estiver disponivel ou aprovado | P0 |

### 6.5 Camada RL

| ID | Descricao | Prioridade |
| --- | --- | --- |
| RF-RL-001 | O produto deve suportar agente PPO/A2C para ranking, confianca ou acao sugerida sobre sinais short | P1 |
| RF-RL-002 | O reward deve considerar P&L liquido, custo de funding e permanencia em contexto desfavoravel | P1 |
| RF-RL-003 | O ambiente de treino deve suportar validacao walk-forward e comparacao contra o baseline operacional | P1 |
| RF-RL-004 | Deve haver suporte a modelos por simbolo como extensao prioritaria | P2 |
| RF-RL-005 | O sistema deve operar em modo degradado quando checkpoint ou features RL nao estiverem disponiveis | P0 |

### 6.6 Risco e gates short-only

| ID | Descricao | Prioridade |
| --- | --- | --- |
| RF-RK-001 | O rollout live deve operar em modo short-only por padrao | P0 |
| RF-RK-002 | Sinais `LONG` devem ser bloqueados quando o modo short-only estiver ativo | P0 |
| RF-RK-003 | Shorts devem ser bloqueados quando o funding rate exceder o limite configurado | P0 |
| RF-RK-004 | Shorts devem ser bloqueados quando a basis estiver negativa ou desfavoravel | P0 |
| RF-RK-005 | Toda entrada deve possuir stop loss obrigatorio | P0 |
| RF-RK-006 | O sizing deve respeitar saldo disponivel, distancia ate o stop, margem maxima por posicao e risco maximo por trade | P0 |
| RF-RK-007 | O sistema deve impor limite diario de entradas e cooldown por simbolo | P0 |
| RF-RK-008 | O circuit breaker deve acionar `HALT` automatico ao atingir o limite de perda configurado | P0 |
| RF-RK-009 | O sistema deve suportar gate de risco de modelo, incluindo rejeicao por overfitting e kill switch por divergencia em `shadow` | P1 |

### 6.7 Execucao e reconciliacao

| ID | Descricao | Prioridade |
| --- | --- | --- |
| RF-EX-001 | O fluxo `shadow` deve percorrer o pipeline de execucao sem enviar ordem real | P0 |
| RF-EX-002 | O fluxo `live` deve enviar ordem de entrada e, apos fill, armar protecoes obrigatorias | P0 |
| RF-EX-003 | Falha no envio das protecoes deve disparar retry com backoff e classificacao de risco bloqueante | P0 |
| RF-EX-004 | O reconciliador deve sincronizar ordens e posicoes com a Binance continuamente | P0 |
| RF-EX-005 | Saidas externas ou divergencias devem atualizar `signal_executions` e gerar eventos de auditoria | P0 |
| RF-EX-006 | Nenhuma execucao live pode ocorrer sem preflight operacional aprovado | P0 |

### 6.8 Observabilidade, auditoria e operacao

| ID | Descricao | Prioridade |
| --- | --- | --- |
| RF-OB-001 | O produto deve gerar logs estruturados por operacao com simbolo, timeframe, motivo, status e timestamps | P0 |
| RF-OB-002 | O banco deve manter trilha completa de oportunidades, sinais, execucoes e eventos | P0 |
| RF-OB-003 | O produto deve emitir artefatos JSON para preflight, healthcheck e ciclos executados | P1 |
| RF-OB-004 | O healthcheck deve detectar posicoes sem protecao, entradas stale e mismatch entre exchange e banco | P0 |
| RF-OB-005 | Eventos criticos devem poder disparar notificacao operacional | P1 |

---

## 7. Requisitos Nao Funcionais

### 7.1 Desempenho

| ID | Requisito | Meta | Prioridade |
| --- | --- | --- | --- |
| RNF-DE-001 | Latencia sinal admitido -> ordem enviada em `live` | <= 300 ms | P0 |
| RNF-DE-002 | Ciclo de analise e decisao por ativo | <= 20 s | P1 |
| RNF-DE-003 | Throughput do scanner no universo operacional | <= 5 s por ciclo padrao | P0 |
| RNF-DE-004 | Alertas criticos operacionais | < 60 s | P1 |

### 7.2 Seguranca e compliance

| ID | Requisito | Meta | Prioridade |
| --- | --- | --- | --- |
| RNF-SE-001 | Credenciais nunca devem ficar hardcoded nem commitadas | 0 ocorrencias | P0 |
| RNF-SE-002 | Chaves devem ser lidas via variaveis de ambiente ou secret manager | 100% | P0 |
| RNF-SE-003 | Toda promocao para `live` deve passar por `go_live_preflight.py` sem erro bloqueante | 100% | P0 |
| RNF-SE-004 | O produto deve falhar fechado em caso de restricao operacional ou regulatoria aplicavel | Fail-closed | P1 |
| RNF-SE-005 | Comunicacao com a Binance deve usar canais autenticados e stack suportada | 100% | P0 |

### 7.3 Confiabilidade e resiliencia

| ID | Requisito | Meta | Prioridade |
| --- | --- | --- | --- |
| RNF-DI-001 | Falhas transientes de API devem usar retry com backoff | >= 3 tentativas | P0 |
| RNF-DI-002 | Reinicio do processo nao pode gerar ordens duplicadas | Idempotencia validada | P0 |
| RNF-DI-003 | Estado de `HALT` deve sobreviver a restart | Persistido | P0 |
| RNF-DI-004 | O runtime deve produzir healthchecks e artefatos recentes para auditoria operacional | Dentro da janela configurada | P1 |

### 7.4 Manutenibilidade e evolucao

| ID | Requisito | Meta | Prioridade |
| --- | --- | --- | --- |
| RNF-MA-001 | Modulos criticos devem possuir cobertura automatizada adequada | >= 80% nos modulos criticos | P1 |
| RNF-MA-002 | Mudancas de schema devem ocorrer via migrations versionadas | 100% | P0 |
| RNF-MA-003 | O PRD deve permanecer como documento mestre e unico do produto | 1 fonte de verdade | P0 |
| RNF-MA-004 | A arquitetura deve permitir migracao futura de SQLite para PostgreSQL | Suportada | P1 |

---

## 8. Arquitetura Tecnica e Stack

### 8.1 Arquitetura atual

```text
+----------------------------------------------------+
| Orquestracao do Ciclo Short                        |
| live_cycle_short_agent / live_cycle                |
+----------------------------------------------------+
| Contexto de Mercado e Features                     |
| OHLCV + funding + basis + multi-timeframe          |
+----------------------------------------------------+
| Pipeline M2                                        |
| opportunities -> validation -> technical_signals   |
+----------------------------------------------------+
| Camada Preditiva                                   |
| LSTM + XGBoost (piloto / shadow)                   |
+----------------------------------------------------+
| Camada RL                                          |
| PPO/A2C para ranking e confianca                   |
+----------------------------------------------------+
| Risco e Gates de Admissao                          |
| short-only, funding, basis, margem, cooldown       |
+----------------------------------------------------+
| Execucao e Reconciliacao Binance                   |
| shadow/live, protecao, sync                        |
+----------------------------------------------------+
| Persistencia e Observabilidade                     |
| modelo2.db, eventos, healthcheck, artefatos JSON   |
+----------------------------------------------------+
```

### 8.2 Decisoes arquiteturais atuais

| Tema | Decisao |
| --- | --- |
| Direcao operacional | short-only em `live` |
| Promocao | `shadow` obrigatorio antes de `live` |
| Banco canonico | `db/modelo2.db` |
| Persistencia operacional | tabelas dedicadas para oportunidades, sinais, execucoes e eventos |
| Gating de futures | funding, basis, margem, cooldown, idade do sinal e preflight no caminho critico |
| Agente dedicado | ciclo short com runtime e artefatos operacionais proprios |

### 8.3 Stack

| Componente | Baseline atual |
| --- | --- |
| Linguagem | Python 3.10+ |
| Exchange integration | Binance Futures REST/WebSocket |
| Persistencia | SQLite |
| RL | PyTorch + Stable-Baselines3 |
| Hiperparametros | Optuna |
| Modelos supervisionados | LSTM + XGBoost |
| Operacao | scripts CLI, `setup.bat`, `setup.sh`, `Makefile`, `Dockerfile` |
| Observabilidade | logs estruturados, runbook, healthchecks e artefatos JSON |

---

## 9. Riscos e Mitigacoes

| ID | Risco | Severidade | Mitigacao |
| --- | --- | --- | --- |
| R-01 | Funding e basis desfavoraveis degradarem o short | Alta | gates especificos antes da execucao |
| R-02 | Posicao entrar sem protecao confirmada | Alta | retry, reconciliacao e healthcheck |
| R-03 | Overfitting ou leak de validacao nos modelos | Alta | walk-forward, gate de risco de modelo e shadow obrigatorio |
| R-04 | Drift de mercado degradar ML/RL | Alta | fallback rules-based, monitoramento e retreino controlado |
| R-05 | API Binance falhar em momento critico | Alta | retry com backoff, reconciliacao e artefatos operacionais |
| R-06 | Lock ou gargalo de concorrencia no SQLite | Media | idempotencia, WAL e trilha de migracao futura |
| R-07 | Divergencia entre documento e produto | Media | manter apenas este PRD como contrato ativo |

---

## 10. Release Atual, Backlog Prioritario e Go No-Go

### 10.1 Release atual

A release atual do produto e um **agente short-only para Binance Futures**, com:

- pipeline M2 auditavel;
- gates de funding e basis no caminho de admissao;
- execucao segregada em `shadow` e `live`;
- protecao obrigatoria;
- preflight e healthcheck operacionais;
- trilha pronta para ML e RL com promocao gradual.

### 10.2 Backlog prioritario

| Prioridade | Item |
| --- | --- |
| P1 | consolidar camada LSTM + XGBoost em `shadow` com metricas de promocao |
| P1 | validar PPO/A2C sobre baseline short com comparacao estatistica |
| P1 | ativar gate de risco de modelo com criterio formal de overfitting |
| P1 | ampliar enriquecimento com open interest e features de regime |
| P2 | modelos dedicados por simbolo |
| P2 | migracao para PostgreSQL quando o volume operacional justificar |

### 10.3 Go/No-Go para capital real

Antes de qualquer ampliacao de uso em `live`, os itens abaixo devem estar satisfeitos:

- `go_live_preflight.py` sem erro bloqueante.
- Janela minima de validacao em `shadow` concluida com sucesso.
- `Posicoes protegidas = 100%`.
- `Posicoes preenchidas sem protecao = 0`.
- Logs, healthchecks e artefatos operacionais disponiveis.
- Simbolos live explicitamente allow-listed.
- KPIs minimos de risco e operacao dentro das metas definidas neste documento.

---

## 11. Glossario

| Termo | Definicao |
| --- | --- |
| Short-only | politica operacional que permite apenas sinais `SHORT` em `live` |
| Funding rate | taxa periodica dos contratos perpetuos que afeta o custo da posicao |
| Basis | diferenca entre preco futuro e spot usada como gate de contexto |
| `shadow` | execucao operacional sem envio de ordens reais |
| `live` | execucao operacional com envio real de ordens |
| Tese | hipotese operacional com entrada, alvo, stop e criterio de validacao |
| M2 | pipeline operacional que materializa oportunidade, validacao, sinal e execucao |
| Audit trail | trilha completa de eventos, estados e motivos persistidos |
| Walk-forward | validacao temporal sem contaminacao entre treino e teste |
| Drift | mudanca de regime que degrada a qualidade do modelo |

---

*Documento mestre do produto. Toda alteracao de escopo, requisito ou
criterio operacional deve ser feita aqui primeiro.*

---

## 12. Operacao com Copilot

Esta secao lista prompts e customizacoes recomendadas para acelerar a
operacao do projeto com assistentes locais.

### 12.1 Prompts recomendados para teste

1. Mapeie a proxima tarefa seguindo BACKLOG, TRACKER e ROADMAP e
  proponha um plano de execucao.
2. Implemente a task X com mudanca minima, rode pytest -q tests/ e
  atualize docs/SYNCHRONIZATION.md se necessario.
3. Revise esta alteracao com foco em risco operacional e regressao de
  comportamento.
4. Atualize docs/BACKLOG.md e sincronize docs/TRACKER.md e
  docs/SYNCHRONIZATION.md.

### 12.2 Customizacoes recomendadas

1. /create-instruction model2-live applyTo core/model2/**
  Uso pratico: reforcar protecoes, reconciliacao e fail-closed no fluxo
  live.
2. /create-instruction docs-sync applyTo docs/**
  Uso pratico: reforcar limite de 80 colunas e trilha em
  docs/SYNCHRONIZATION.md.
3. /create-skill m2-incident-response
  Uso pratico: padronizar coleta de evidencias e mitigacao durante
  incidentes.
4. /create-prompt preflight-live-check
  Uso pratico: checklist rapido antes de promover de shadow para live.
