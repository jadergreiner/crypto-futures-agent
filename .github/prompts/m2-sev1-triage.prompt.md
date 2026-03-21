# Prompt: M2 SEV-1 Triage

Use este prompt para triagem ultrarrapida de incidente critico (SEV-1)
no Modelo 2.0.

## Contexto

Ha um incidente SEV-1 em execucao live do M2.

## Objetivo

1. Conter risco imediatamente (fail-safe).
2. Preservar evidencias minimas para auditoria.
3. Propor plano de mitigacao com passos curtos e verificaveis.

## Entrada esperada

- `symbol`
- `execution_id` (se existir)
- sintomas observados
- horario UTC aproximado do incidente

## Checklist de triagem (ordem obrigatoria)

1. Classificar impacto:
   - posicao desprotegida?
   - risco de perda relevante agora?
2. Conter:
   - bloquear novas entradas no fluxo afetado;
   - priorizar armamento/validacao de protecoes.
3. Evidencias minimas:
   - estado no banco (`signal_executions` e eventos);
   - estado na exchange (ordens, fills, posicao);
   - logs no intervalo do incidente.
4. Reconciliacao rapida:
   - comparar estado esperado x observado;
   - listar divergencias criticas.
5. Plano de acao:
   - mitigacao imediata;
   - correcao minima;
   - validacao pos-correcao.

## Formato de saida

Responder exatamente com estas secoes:

1. `Resumo Executivo`
2. `Risco Imediato`
3. `Evidencias Coletadas`
4. `Divergencias`
5. `Mitigacao Aplicada`
6. `Proximos Passos (30-60 min)`
7. `Criterio de Encerramento`

## Regras

- Em duvida, bloquear operacao.
- Nunca sugerir desabilitar `risk_gate` ou `circuit_breaker`.
- Evitar mudancas amplas; focar em correcao local e auditavel.
- Registrar timestamp UTC e identificadores em toda recomendacao.
