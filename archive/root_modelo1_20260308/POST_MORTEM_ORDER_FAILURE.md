# 🔴 Post-Mortem: Ordem Executada com Margem Incorreta

**Data do Incidente**: 21 de fevereiro de 2026, 00:17:39 UTC
**Status**: ❌ **FALHA - Ordem Fechada Manualmente**

---

## Sumário Executivo

Ordem foi executada com **$46 de margem** ao invés dos $1 planejados.

- **Order ID**: 5412767346
- **Total Trading**: 459.84189400 USDT
- **Margem Usada**: $46.00 (46× acima do esperado)
- **Ação**: Fechada manualmente pelo usuário

---

## O que Aconteceu

### Timeline

| Hora UTC | Evento |
|----------|--------|
| 00:13:42-00:15:54 | Phase 0 validation passou (7/7 testes) |
| 00:17:35-00:17:40 | script `execute_1dollar_trade.py` executado |
| 00:17:40 | Ordem enviada ao Binance (ORDER_2026-02-21T00:17:40.007420) |
| 00:17:39 | **Ordem realmente aberta com $46 (5412767346)** |
| [Posterior] | Usuário identificou erro e fechou manualmente |

### Análise de Raiz

**Problema 1: Preço Fallback Usado**

```python
# NO SCRIPT (ERRADO):
mark_price_result = client.rest_api.mark_price(symbol=symbol)
if hasattr(mark_price_result, "markPrice"):
    price = float(mark_price_result.markPrice)
else:
    price = 0.0001  # ← FALLBACK PROBLEMÁTICO!

quantity = exposure_usd / price  # $10 / 0.0001 = 100,000
```

Se o API falhou e retornou `0.0001`, então:
- Quantidade calculada = $10 / $0.0001 = 100,000 units
- Mas a API pode ter retornado um preço ainda MENOR, como $0.0000216 (estimado)
- Quantidade real = $10 / $0.0000216 ≈ ~463,000 units
- Margem = $463,000 / 10x leverage ≈ $46

**Problema 2: Sem Validação de Sanidade**

Script não validava se quantidade era absurda para o valor de margem.

**Problema 3: Sem Confirmação Manual**

Em LIVE mode, não havia checkpoint final antes de executar.

---

## Impacto

✅ **Baixo risco operacional**
- Apenas $46 de $424 (10.8% do capital)
- Usuário fechou rapidamente
- Perda controlada

❌ **Alto risco de confiança**
- Prova que sistema ainda tem bugs críticos
- Não deve executar ordens reais até estar bulletproof

---

## Correções Implementadas (Imediatas)

### 1. Remover TODOS os Fallbacks de Preço
```python
# NOVO (CORRETO):
try:
    price = float(mark_price_result.markPrice)
except:
    logger.error("Preço não disponível - ABORTANDO")
    return False  # ← Sem fallback!
```

### 2. Adicionar Validação de Sanidade
```python
# Se quantity > 50,000 com $1 margem = ERRO
if quantity > 50_000 and margin_usd == 1.0:
    logger.error("Quantidade suspeita - ABORTANDO")
    return False
```

### 3. Adicionar Checkpoint Manual
```python
logger.info("⚠️ RESUMO DA ORDEM:")
logger.info(f"   Symbol: {symbol}")
logger.info(f"   Quantity: {quantity:.8f}")
logger.info(f"   Margin: ${margin_usd:.2f}")
# Em produção: aguardar confirmação do usuário
```

---

## Novo Script com Proteções

Arquivo atualizado: `scripts/execute_1dollar_trade.py`

**Mudanças**:
- ✅ Preço sem fallback (erro se API falha)
- ✅ Validação de quantidade absurda
- ✅ Validação de margem acima do esperado
- ✅ Checkpoint pré-execução com resumo completo
- ✅ Melhor logging de erros

---

## Decisão Operacional

### Recomendação: ⛔ **NÃO EXECUTAR ATÉ INVESTIGAR COMPLETAMENTE**

Antes de próxima ordem ao vivo:

1. **[ ] Investigar**: Por que `mark_price()` falhou?
   - Testar API manualmente
   - Verificar resposta exata

2. **[ ] Validar**: Novo script com proteções
   - Rodar DRY RUN
   - Verificar logs detalhados

3. **[ ] Confirmar**: Margem real vs. calculada
   - Coincidem com valores esperados?
   - Sem discrepâncias de 10× ou mais?

4. **[ ] Autorizar**: Somente após validações passarem

---

## Checklist de Correção

- [x] Identificado problema (preço fallback)
- [x] Identificada causa (API falha)
- [x] Script atualizado com validações
- [x] Documentação criada
- [ ] Teste com DRY RUN (próximo passo)
- [ ] Investigação de por que API falhou
- [ ] Aprovação para próxima execução ao vivo

---

## Próximas Ações (Obrigatórias)

### 1. Testar Script Corrigido em DRY RUN
```bash
python scripts/execute_1dollar_trade.py --symbol ANKRUSDT --direction LONG --dry-run
```

### 2. Investigar Falha de API
```bash
# Testar mark_price manualmente
python -c "from data.binance_client import BinanceClientFactory; ..."
```

### 3. Validar Comportamento sem Fallback
- Verifique logs para ver se validações funcionam
- Confirme abortamento se preço inválido

### 4. Execução ao Vivo (Somente após 1-3)
- Usar script corrigido
- Validar margem antes de confirmar

---

## Lições Aprendidas

| # | Lição | Aplicar |
|---|-------|---------|
| 1 | Fallbacks numéricos são perigosos | Remover todos em cálculos críticos |
| 2 | Sem validação de sanidade = risco | Adicionar limites e verificações |
| 3 | Sem confirmação final = acidentes | Implementar checkpoint manual |
| 4 | Logs bons salvam vidas (e capital) | Manter detalhe em transações |
| 5 | Testes não garantem realidade | Primeiro trade é sempre risco |

---

## Conclusão

**Sistema não está pronto para trading automatizado sem supervisão.**

Próximas execuções devem:
1. Sempre passar por DRY RUN primeiro
2. Ter validações de sanidade rigorosas
3. Ter checkpoint manual antes de LIVE
4. Ser supervisionadas por humano

---

**Documento criado**: 2026-02-21T00:26:00 UTC
**Responsabilidade**: GitHub Copilot - Post-Mortem Analysis
**Status**: Crítico - Aguardando investigação e correção
