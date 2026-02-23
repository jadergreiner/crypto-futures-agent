# 📝 Changelog — Crypto Futures Agent

Todas as mudanças notáveis deste projeto serão documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

---

## 🔗 Links Rápidos

- [ROADMAP](ROADMAP.md)
- [Status de Entregas](STATUS_ENTREGAS.md)

---

## [Não lançado]

### Adicionado

- **S2-4 Trailing Stop Loss (TSL)** — Implementação completa de proteção dinâmica de lucro
  - `risk/trailing_stop.py` — Core TSL Manager (38 funções)
  - `docs/SPEC_S2_4_TRAILING_STOP_LOSS.md` — Especificação técnica completa
  - `docs/ARCH_S2_4_TRAILING_STOP.md` — Arquitetura e design integrado
  - `tests/test_trailing_stop.py` — 24 testes unitários ✅ PASS
  - `tests/test_tsl_integration.py` — 10 testes integração ✅ PASS
  - Parâmetros: `trailing_activation_threshold = 1.5R`, `trailing_stop_distance_pct = 10%`
  - Status: Design + Code + Tests ✅ COMPLETO | Aguardando Binance Integration + QA
- `docs/STATUS_ENTREGAS.md` — fonte da verdade de status das entregas.
- `docs/PLANO_DE_SPRINTS_MVP_NOW.md` — mapa Now → Sprints com tabelas.
- `docs/CRITERIOS_DE_ACEITE_MVP.md` — matriz de critérios e Go/No-Go.
- `docs/RUNBOOK_OPERACIONAL.md` — pré-voo, comandos, incidentes, rollback.
- `docs/CHANGELOG.md` — este arquivo.
- Política `docs_sync_policy` em `prompts/board_16_members_data.json`.
- Seção "Execução / Visibilidade" em `docs/ROADMAP.md`.

---

## [0.3.0] — 2026-02-22

### Adicionado

- Backtest Engine (F-12) 100% funcional (9/9 testes passando).
- Decision #2 aprovada: Opção C Híbrido (Heurísticas + PPO paralelo).
- Signal-Driven RL com tabelas `trade_signals` e `signal_evolution`.
- SubAgentManager com PPO por símbolo (`models/sub_agents/`).
- RewardCalculator com 3 componentes: r\_pnl, r\_hold\_bonus, r\_invalid\_action.
- TrainingCallback corrigido (rastreamento por episódio).

### Alterado

- Environment bloqueia CLOSE quando PnL > 0 e R < 1.0.
- Hold bonus assimétrico: lucro = 0.05 + pnl \* 0.1; perda < -0.5% = -0.02.

### Corrigido

- pnl\_history não era resetado ao abrir posição.
- reward\_mean = 0.00 sempre no TrainingCallback.

---

## [0.2.0] — 2026-02-21

### Adicionado

- Go-Live Phase 2 (canary) autorizado e iniciado.
- Board de 16 membros: votação e quórum implementados.
- Pre-flight checklist automatizado.
- Circuit Breaker -3% ativo e validado.

### Alterado

- DB\_PATH padronizado como `db/crypto_agent.db`.

---

## [0.1.0] — 2026-02-18

### Adicionado

- Estrutura inicial do projeto.
- Integração Binance Futures REST e WebSocket.
- RiskGate básico com stop loss hardcoded.
- Módulo de execução de ordens.
- Telemetria básica de logs.

---

*Use o prompt `docs_sync_policy.sync_trigger_prompt` em
`prompts/board_16_members_data.json` para sincronizar docs via Copilot.*
