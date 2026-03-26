# Diagramas - Modelo 2.0 (Estado Atual)

## 1) Fluxo ponta a ponta (model-driven)

Fluxo operacional de referencia para execucao diaria e live.

```mermaid
flowchart LR
  A[Coleta de estado de mercado] --> B[Policy Model]
  B --> C{Acao}
  C -->|OPEN_LONG| D[Safety Envelope]
  C -->|OPEN_SHORT| D
  C -->|REDUCE| D
  C -->|CLOSE| D
  C -->|HOLD| E[Persistir decisao e episodio]
  D -->|Aprovado| F[Execucao]
  D -->|Bloqueado| G[Evento de bloqueio]
  F --> H[Reconciliacao]
  H --> I[Persistir execucao e eventos]
  I --> E
  G --> E
```

## 2) Fluxo de decisao do modelo

A decisao nasce exclusivamente no modelo e segue para seguranca.

```mermaid
flowchart TD
  A[Estado consolidado] --> B[Inferencia da policy]
  B --> C{Acao prevista}
  C -->|OPEN_LONG| D[Validar risco e limites]
  C -->|OPEN_SHORT| D
  C -->|REDUCE| D
  C -->|CLOSE| D
  C -->|HOLD| E[Registrar HOLD]
  D -->|Passou| F[Gerar ordem]
  D -->|Falhou| G[Registrar bloqueio fail-safe]
  F --> H[Registrar decisao efetiva]
  E --> H
  G --> H
```

## 3) Safety envelope e fail-safe

Guard-rails obrigatorios em todo caminho live.

```mermaid
flowchart TD
  A[Decisao do modelo] --> B[risk_gate]
  B --> C[circuit_breaker]
  C --> D[Preflight live]
  D --> E{Seguro para executar?}
  E -->|Sim| F[Execucao permitida]
  E -->|Nao| G[Bloquear operacao]
  G --> H[Emitir evento auditavel]
```

## 4) Ciclo de execucao e reconciliacao

Estados operacionais de execucao no live.

```mermaid
stateDiagram-v2
  [*] --> READY
  READY --> ENTRY_SENT
  READY --> BLOCKED
  READY --> CANCELLED
  ENTRY_SENT --> ENTRY_FILLED
  ENTRY_SENT --> FAILED
  ENTRY_SENT --> CANCELLED
  ENTRY_FILLED --> PROTECTED
  ENTRY_FILLED --> EXITED
  ENTRY_FILLED --> FAILED
  PROTECTED --> EXITED
  PROTECTED --> FAILED
  BLOCKED --> [*]
  CANCELLED --> [*]
  FAILED --> [*]
  EXITED --> [*]
```

## 5) Entidades e relacoes de dados

Representacao logica das entidades do estado atual.

```mermaid
erDiagram
  MODEL_DECISIONS ||--o{ SIGNAL_EXECUTIONS : gera
  SIGNAL_EXECUTIONS ||--o{ SIGNAL_EXECUTION_EVENTS : possui
  MODEL_DECISIONS ||--o{ LEARNING_EPISODES : alimenta
  TRAINING_RUNS ||--o{ MODEL_DECISIONS : referencia_versao

  MODEL_DECISIONS {
    int id
    string symbol
    string action
    float confidence
    string model_version
    string reason_code
  }

  SIGNAL_EXECUTIONS {
    int id
    int decision_id
    string execution_mode
    string status
    string exchange_order_id
  }

  SIGNAL_EXECUTION_EVENTS {
    int id
    int signal_execution_id
    string event_type
    string to_status
    string rule_id
  }

  LEARNING_EPISODES {
    int id
    int decision_id
    string action_t
    float reward_t
    int done
  }

  TRAINING_RUNS {
    int id
    string model_version_candidate
    string go_no_go
  }
```

## 6) Aprendizado continuo e promocao

Fluxo de retreino governado fora do runtime live.

```mermaid
flowchart LR
  A[(learning_episodes)] --> B[Montar dataset de treino]
  B --> C[Retreinar modelo]
  C --> D[Validar metricas]
  D --> E{Go/No-Go}
  E -->|GO| F[Promover versao]
  E -->|NO_GO| G[Manter versao atual]
  F --> H[(training_runs)]
  G --> H
```

## 7) Loop operacional unificado (Windows)

Entry point local: `iniciar.bat` (opcao `2`).

```mermaid
flowchart TD
  A[iniciar.bat opcao 2] --> B[sync_market_context H4 M2_SYMBOLS]
  B --> C[sync_market_context M5 M2_SYMBOLS]
  C --> D[daily_pipeline H4 M2_SYMBOLS]
  D --> E[live_cycle H4 M2_SYMBOLS]
  E --> F[persist_learning_episodes H4]
  F --> G[healthcheck_live_execution]
  G --> H{M2_RUN_ONCE=1?}
  H -->|Sim| I[Fim]
  H -->|Nao| J[timeout M2_LOOP_SECONDS]
  J --> B
```

Regra de deduplicacao:

1. `sync_market_context` nao persiste candle repetido com mesmo
   `symbol+timestamp`.

## 8) Maquina de estados do Circuit Breaker (BLID-092)

Estados e transicoes do `risk/circuit_breaker.py`.

```mermaid
stateDiagram-v2
  [*] --> CLOSED
  CLOSED --> OPEN : trip(reason) — drawdown excedeu limiar
  OPEN --> HALF_OPEN : attempt_recovery() ou reset_manual(operator)
  HALF_OPEN --> CLOSED : attempt_recovery() — drawdown recuperado
  HALF_OPEN --> OPEN : attempt_recovery() — drawdown ainda critico
  CLOSED --> [*]
  OPEN --> [*]
  HALF_OPEN --> [*]
```

Aliases em `risk/states.py`: `NORMAL = CLOSED`, `TRANCADO = OPEN`.

Toda transicao gera `CircuitBreakerTransition` (frozen dataclass) com
`from_state`, `to_state`, `reason`, `timestamp_utc`.

## 9) Referencias canonicas

1. `docs/ARQUITETURA_ALVO.md`
2. `docs/REGRAS_DE_NEGOCIO.md`
3. `docs/MODELAGEM_DE_DADOS.md`

## 10) Controles de resiliencia contratuais (PKG-PO10-0326)

```mermaid
flowchart TD
  A[Entrada de ciclo] --> B[Drift gate pre-admissao]
  B -->|ok| C[Validacao cruzada sinal-contexto-posicao]
  B -->|bloqueio| H[Evento auditavel]
  C -->|ok| D[Retry por categoria]
  C -->|contradicao| H
  D --> E[Indicadores de reconciliacao]
  E --> F{Schema completo?}
  F -->|sim| G[Prosseguir ciclo]
  F -->|nao| H
  H --> I[Fail-safe sem bypass de guardrails]
```
