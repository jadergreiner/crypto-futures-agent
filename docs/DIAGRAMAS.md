# Diagramas - Modelo 2.0

## 1) Fluxo de dados

Runner operacional ponta a ponta: `scripts/model2/daily_pipeline.py`.
Runner operacional agendado: `scripts/model2/schedule_daily_pipeline.py`.
Runner de healthcheck: `scripts/model2/healthcheck_daily_schedule.py`.
Runner operacional da ponte: `scripts/model2/bridge.py`.
Runners do live: `scripts/model2/live_execute.py`,
`scripts/model2/live_reconcile.py`, `scripts/model2/live_dashboard.py` e
`scripts/model2/live_cycle.py`.

```mermaid
flowchart LR
    A[OHLCV + Indicadores + SMC] --> B[Scanner de Oportunidades]
    B --> C[(oportunidades)]
    C --> D[Rastreador de Tese]
    D --> E[(eventos_de_oportunidade)]
    E --> J[(snapshots_auditoria)]
    D --> F{Estado final?}
    F -->|VALIDADA| G[Ponte de Sinal]
    F -->|INVALIDADA| H[Fim da tese]
    F -->|EXPIRADA| H
    C --> K[(snapshots_painel)]
    G --> I[(technical_signals)]
    I --> L[Camada de Ordem M2]
    L --> M[Admissao: CONSUMED ou CANCELLED]
    M --> N[(signal_executions)]
    N --> O[Executor MARKET + Protecao]
    O --> P[Reconcile Live]
    P --> Q[(signal_execution_events)]
    P --> R[(signal_execution_snapshots)]
    M --> S[Adaptador M2-007.2 opcional]
    S --> T[(trade_signals legado)]
    I --> U[(signal_flow_snapshots)]
```

## 1b) Fluxo de Treinamento e RL (M2-015.3)

Execução semanal, fora do caminho crítico do pipeline diário:

```mermaid
flowchart LR
    A[(training_episodes)] -->|Episodios por ciclo| B[Agregar dataset semanal]
    B -->|547+ episodios| C[train_ppo_incremental.py]
    C -->|Sharpe > 0.5| D[(ppo_model.pkl)]
    D -->|Checkpoint| E[rl_signal_generation.py]
    E -->|RL confidence| F[(technical_signals)]
    F -->|Etapa 9| G[Pipeline diario]
    G -->|Novo ciclo| A
    C -->|Sharpe < 0.5| H[Fallback deterministica]
    H -->|Regressar confidence 0.70| F
```

**Notas:**
- Coleta de episodios é automática em cada ciclo do `daily_pipeline.py`
- Treinamento PPO roda off-pipeline (semanal)
- RL enhancement só ativa se modelo passar limiares de qualidade
- Auditoria completa de qual modelo foi usado (deterministica vs RL)

## 2) Diagrama de classes

```mermaid
classDiagram
    class Oportunidade {
      +id
      +simbolo
      +periodo
      +direcao
      +tipo_tese
      +status
      +zona_minima
      +zona_maxima
      +preco_gatilho
      +preco_invalidacao
      +expira_em
    }

    class EventoDaOportunidade {
      +id
      +id_oportunidade
      +tipo_evento
      +status_origem
      +status_destino
      +id_regra
      +momento_evento
    }

    class ScannerDeOportunidades {
      +identificar()
    }

    class RastreadorDeTese {
      +monitorar()
      +validar()
      +invalidar()
      +expirar()
    }

    class PonteDeSinal {
      +emitir_sinal()
    }

    class ExecucaoLive {
      +stage()
      +send_market_entry()
      +arm_protection()
      +reconcile()
    }

    class EventoDeExecucao {
      +id
      +id_execucao
      +status_origem
      +status_destino
      +id_regra
      +momento_evento
    }

    Oportunidade "1" --> "*" EventoDaOportunidade
    ScannerDeOportunidades --> Oportunidade
    RastreadorDeTese --> Oportunidade
    RastreadorDeTese --> EventoDaOportunidade
    PonteDeSinal --> Oportunidade
    PonteDeSinal --> ExecucaoLive
    ExecucaoLive "1" --> "*" EventoDeExecucao
```

## 3) Fluxo da tese

```mermaid
stateDiagram-v2
    [*] --> IDENTIFICADA
    IDENTIFICADA --> MONITORANDO
    MONITORANDO --> VALIDADA: confirmacao de gatilho
    MONITORANDO --> INVALIDADA: quebra da premissa
    MONITORANDO --> EXPIRADA: prazo encerrado
    VALIDADA --> [*]
    INVALIDADA --> [*]
    EXPIRADA --> [*]
```

## 4) Decisao do modelo (fase 1)

```mermaid
flowchart TD
    A[Preco entra na zona tecnica] --> B{Ha rejeicao valida?}
    B -->|Nao| C[Continuar monitorando]
    B -->|Sim| D{Rompeu gatilho da tese?}
    D -->|Nao| C
    D -->|Sim| E[VALIDADA]
    C --> F{Passou invalidacao?}
    F -->|Sim| G[INVALIDADA]
    F -->|Nao| H{Expirou tempo?}
    H -->|Sim| I[EXPIRADA]
    H -->|Nao| C
```

## 5) Ciclo de execucao live (fase 2)

```mermaid
stateDiagram-v2
    [*] --> READY
    [*] --> BLOCKED
    READY --> ENTRY_SENT
    READY --> FAILED
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

## 6) Loop operacional unificado (Windows)

Entry point local: `iniciar.bat` (opcao `2`).

```mermaid
flowchart TD
    A[iniciar.bat opcao 2] --> B[daily_pipeline]
    B --> C[live_cycle]
    C --> D[healthcheck_live_execution]
    D --> E{M2_RUN_ONCE=1?}
    E -->|Sim| F[Fim]
    E -->|Nao| G[timeout M2_LOOP_SECONDS]
    G --> B
```

## 7) Loop operacional unificado (Windows) - estado atual

Entry point local: `iniciar.bat` (opcao `2`).

```mermaid
flowchart TD
    A[iniciar.bat opcao 2] --> B[sync_market_context H4 M2_SYMBOLS]
    B --> C[sync_market_context M5 M2_SYMBOLS]
    C --> D[daily_pipeline H4 M2_SYMBOLS]
    D --> E[live_cycle H4 M2_SYMBOLS]
    E --> F[persist_training_episodes H4]
    F --> G[healthcheck_live_execution]
    G --> H{M2_RUN_ONCE=1?}
    H -->|Sim| I[Fim]
    H -->|Nao| J[timeout M2_LOOP_SECONDS]
    J --> B
```

Regra de deduplicacao:

1. `sync_market_context` nao persiste candle repetido com mesmo `symbol+timestamp`.
