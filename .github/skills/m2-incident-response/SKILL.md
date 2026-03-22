---
name: m2-incident-response
description: |
  Responde incidentes do Modelo 2.0 com mitigacao fail-safe.
  Prioriza evidencia minima e reconciliacao auditavel.
metadata:
  tags:
    - incidente
    - live
    - reconciliacao
  focus:
    - economia-de-tokens
    - fail-safe
    - causa-raiz-minima
---

# Skill: M2 Incident Response

## Objetivo

Responder incidentes de execucao no Modelo 2.0 com prioridade para
seguranca operacional, preservacao de capital e trilha de auditoria.

## Quando usar

Use este skill quando houver sinais como:

- posicao aberta sem protecao;
- divergencia entre banco e exchange;
- ordem duplicada, rejeitada ou com estado inconsistente;
- fill sem atualizacao de `signal_executions`;
- comportamento inesperado em `live_service` ou `live_exchange`.

## Modo Economico

Regra principal: conter risco primeiro e investigar depois, lendo apenas
o necessario para reconciliar o estado.

Ordem de leitura:

1. Ler a evidencia mais direta do incidente: logs, execution_id,
  order_id, posicao, erro ou diff citado.
2. Ler banco, exchange e eventos apenas no intervalo e simbolo afetados.
3. Ler `core/model2/**`, `scripts/model2/**` ou `risk/**` apenas no
  caminho de execucao relacionado ao sintoma.
4. Ler `docs/RUNBOOK_M2_OPERACAO.md` e `docs/SYNCHRONIZATION.md`
  apenas se houver mudanca de processo, doc ou necessidade de auditoria.

Evitar:

- abrir varredura ampla do sistema antes de conter risco
- reler modulos inteiros sem correlacao com o sintoma
- gerar narrativa longa quando bastam evidencias e decisao
- propor mudanca arquitetural ampla para defeito localizado

## Principios

- Seguranca antes de performance.
- Em duvida, falhar fechado e bloquear continuidade.
- Nunca desabilitar `risk/risk_gate.py` ou `risk/circuit_breaker.py`.
- Registrar o que foi observado, decidido e executado.

## Fluxo Operacional

1. Classificar severidade e escopo minimo: simbolo, execution_id,
  componente e janela UTC.
2. Conter risco imediato antes de aprofundar diagnostico.
3. Coletar evidencias minimas para reconciliar banco, exchange e logs.
4. Manter fluxo bloqueado se houver divergencia critica.
5. Corrigir a causa raiz com mudanca minima e localizada.
6. Validar o fluxo seguro e registrar apenas o que for necessario.

## Severidade

- `SEV-1`: risco imediato de perda relevante ou posicao desprotegida.
- `SEV-2`: risco moderado com impacto operacional parcial.
- `SEV-3`: anomalia sem risco imediato, mas com necessidade de correcao.

## Evidencia Minima

- severidade
- componente afetado
- simbolo e `execution_id`, quando houver
- order_id(s) de entrada e protecao, quando houver
- status de posicao, SL/TP e sequencia de eventos
- janela UTC do incidente

## Guardrails

- Se houver ambiguidade de estado, manter bloqueio ate reconciliacao.
- Nunca liberar fluxo com posicao potencialmente desprotegida.
- Nunca desabilitar validacoes de risco para "destravar" incidente.
- Priorizar retries, idempotencia e conciliacao antes de qualquer bypass.

## Formato de Resposta

Para economizar tokens, responder em bloco curto:

- Severidade
- Escopo
- Evidencias
- Mitigacao imediata
- Divergencia reconciliada ou pendente
- Causa raiz provavel
- Correcao aplicada ou proposta
- Validacao
- Follow-up, se existir

Nao gerar relatorio longo se o caso couber em 10-14 linhas.

## Template Curto

```markdown
- Severidade: SEV-X
- Componente: core/model2/<arquivo>
- Symbol: <SYMBOL>
- Execution ID: <ID>
- Janela UTC: <inicio> -> <fim>
- Exchange: <ordens/posicao>
- Banco: <execucao/eventos>
- Logs: <arquivos>
- <acao 1>
- <acao 2>
- <descricao objetiva>
- <mudanca minima>
- <teste/check>
- <acao futura>
```

## Prompts de Exemplo

```text
Use o skill m2-incident-response para investigar uma posicao sem SL/TP apos
ENTRY_FILLED e proponha mitigacao fail-safe.
```

```text
Aplique o playbook m2-incident-response para reconciliar divergencia entre
signal_executions e ordens da exchange para execution_id 42.
```
