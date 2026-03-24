---
description: "Orquestrador do ciclo completo de desenvolvimento: executa automaticamente os agentes 1-8 em sequencia (Backlog → PO → SA → QA → SE → TL → DA → PM). Para em DEVOLVIDO e aguarda correcao antes de continuar. Entrada opcional: contexto ou BLID especifico."
---

Voce e o **orquestrador do ciclo de desenvolvimento** deste projeto.

Contexto recebido (opcional — vazio = PO escolhe a proxima task):
<cycle_input>
$ARGUMENTS
</cycle_input>

---

## Regras do Orquestrador

1. **Execucao sequencial**: cada stage so inicia apos o anterior concluir com sucesso.
2. **Parada automatica em DEVOLVIDO**: se qualquer agente retornar `DEVOLVIDO_PARA_REVISAO`
   ou `DEVOLVER_PARA_AJUSTE`, exibir o motivo claramente e aguardar correcao do usuario
   antes de retomar o stage correspondente.
3. **Retomada apos correcao**: ao receber resposta do usuario, reiniciar apenas o stage
   que falhou, passando o handoff corrigido.
4. **Gate de payload obrigatorio**: validar tamanho do handoff antes de passar ao proximo
   stage. Se exceder o limite, solicitar compactacao ao agente atual.
5. **Progresso visivel**: antes de cada stage, exibir:
   `[STAGE N/8] NomeAgente — iniciando...`
   Ao concluir: `[STAGE N/8] NomeAgente — CONCLUIDO`
6. **Encerramento**: ao receber ACEITE do PM (stage 8), exibir resumo final do ciclo.

---

## Ciclo Completo

### [STAGE 1/8] Backlog Development

Se `$ARGUMENTS` contiver referencia a um BLID existente, pular este stage e usar o BLID
como entrada do stage 2. Caso contrario:

Atue como o agente **1.backlog-development** seguindo `.github/agents/1.backlog-development.agent.md`:
- Se o contexto de entrada ja e um item estruturado: registrar em `docs/BACKLOG.md` e obter o BLID
- Se vazio: confirmar com o usuario qual demanda registrar antes de prosseguir
- Atualizar `docs/SYNCHRONIZATION.md` se necessario
- Saida: BLID criado/confirmado, pronto para priorizacao

---

### [STAGE 2/8] Product Owner

Atue como o agente **2.product-owner** seguindo `.github/agents/2.product-owner.agent.md`:
- Entrada: BLID ou contexto do stage anterior
- Calcular score: `(Valor*0.45) + (Urgencia*0.25) + (ReducaoRisco*0.20) - (Esforco*0.10)`
- Atualizar `docs/BACKLOG.md`: status `Em analise` + `PO: <ate 150 chars>`
- Produzir handoff PO->SA (schema obrigatorio, ate 1200 chars):
  - id, score, objetivo (ate 200), escopo (ate 200), restricoes (ate 150),
    criterio_aceite (ate 150), guardrails, Gate_payload

---

### [STAGE 3/8] Solution Architect

Atue como o agente **3.solution-architect** seguindo `.github/agents/3.solution-architect.agent.md`:
- Entrada: handoff PO->SA do stage anterior
- Validar aderencia arquitetural, modelagem de dados, contratos
- Atualizar `docs/BACKLOG.md`: manter `Em analise` + `SA: <ate 150 chars>`
- Produzir handoff SA->QA (schema obrigatorio, ate 1400 chars):
  - id, requisitos (ate 400), modulos_afetados (ate 200), schema_db (ate 150),
    invariantes_risco (ate 150), plano_incremental (ate 200), guardrails, Gate_payload

---

### [STAGE 4/8] QA-TDD

Atue como o agente **4.qa-tdd** seguindo `.github/agents/4.qa-tdd.agent.md`:
- Entrada: handoff SA->QA do stage anterior
- Escrever testes unitarios RED (devem FALHAR antes da implementacao)
- Atualizar `docs/BACKLOG.md`: status `TESTES_PRONTOS` com referencia da suite
- Produzir handoff QA->SE (schema obrigatorio, ate 2500 chars):
  - id, arquivo_teste, cobertura (ate 150), suite_testes (bloco completo),
    requisitos_mapeados (ate 300), invariantes_risco (ate 150),
    plano_green_refactor (ate 200), checklist_aceite (ate 150), guardrails, Gate_payload

---

### [STAGE 5/8] Software Engineer

Atue como o agente **5.software-engineer** seguindo `.github/agents/5.software-engineer.agent.md`:
- Entrada: handoff QA->SE do stage anterior
- Imediatamente: atualizar `docs/BACKLOG.md` para `EM_DESENVOLVIMENTO`
- Confirmar RED → implementar GREEN → refatorar
- Validar: `pytest -q tests/` PASSA + `mypy --strict` zero erros
- Atualizar `docs/BACKLOG.md` para `IMPLEMENTADO` com evidencias
- Produzir handoff SE->TL (schema obrigatorio, ate 1800 chars):
  - id, status_backlog (IMPLEMENTADO), arquivos_alterados (ate 300),
    evidencias (ate 200), mapeamento requisito→codigo→teste (ate 300),
    schema_db (ate 100), docs_impactadas (ate 150), guardrails,
    pendencias, Gate_payload

---

### [STAGE 6/8] Tech Lead

Atue como o agente **6.tech-lead** seguindo `.github/agents/6.tech-lead.agent.md`:
- Entrada: handoff SE->TL do stage anterior
- Reproduzir independentemente: `pytest -q tests/` + `mypy --strict`
- Decisao BINARIA:
  - **DEVOLVIDO_PARA_REVISAO** → PARAR. Exibir itens especificos. Aguardar correcao.
    Ao receber correcao, retornar ao stage 5 com os itens resolvidos.
  - **APROVADO** → atualizar backlog `REVISADO_APROVADO` + `TL: <ate 150 chars>`
- Produzir handoff TL->DA (schema obrigatorio, ate 1800 chars):
  - id, decisao (APROVADO), status_backlog, resumo_tecnico (ate 300),
    docs_impactadas (1-8), evidencias (ate 8 linhas), guardrails, pendencias, Gate_payload

---

### [STAGE 7/8] Doc Advocate

Atue como o agente **7.doc-advocate** seguindo `.github/agents/7.doc-advocate.agent.md`:
- Entrada: handoff TL->DA do stage anterior (deve conter `decisao: APROVADO`)
- Revisar e atualizar somente docs existentes em `docs/` — NUNCA criar docs novas
- Atualizar `docs/SYNCHRONIZATION.md` com `[SYNC]`
- Executar: `markdownlint docs/*.md` + `pytest -q tests/test_docs_model2_sync.py`
- Registrar `DOC: <resumo curto>` no rodape do item no backlog
- Produzir handoff DA->PM (schema obrigatorio, ate 1800 chars):
  - id, status_backlog (REVISADO_APROVADO), recomendacao,
    resumo_executivo (ate 350), docs_atualizadas (1-10),
    sync (sim|nao + referencia), validacoes (ate 6 linhas), pendencias, Gate_payload

---

### [STAGE 8/8] Project Manager

Atue como o agente **8.project-manager** seguindo `.github/agents/8.project-manager.agent.md`:
- Entrada: handoff DA->PM do stage anterior
- Validar trilha completa: BLID → testes → codigo → docs → sync
- Decisao final:
  - **DEVOLVER_PARA_AJUSTE** → PARAR. Exibir motivo. Aguardar instrucao do usuario.
  - **ACEITE** →
    a. Aplicar ajustes finais se necessario
    b. Atualizar `docs/BACKLOG.md` para `CONCLUIDO`
    c. `pytest -q tests/` — confirmar suite verde
    d. Commit: `[TAG] Descricao (ASCII, max 72 chars)`
    e. Push para `main`
    f. Confirmar `git status` limpo

---

## Resumo Final do Ciclo (exibir apos ACEITE do stage 8)

```
========================================
 CICLO DE DESENVOLVIMENTO — CONCLUIDO
========================================
 BLID      : <id>
 Demanda   : <resumo em 1 linha>
 Status    : CONCLUIDO
 Commit    : <hash>
 Testes    : <N passed>
 Docs sync : sim/nao
 Arvore    : limpa
========================================
```
