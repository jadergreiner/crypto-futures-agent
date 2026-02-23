# 📋 Especificação S2-4 — Trailing Stop Loss (Dinâmico)

**Issue:** #61  
**Sprint:** Sprint 2-3  
**Status:** DESIGN ✅ EM EXECUÇÃO  
**Owner Técnico:** Arch (#6) + The Brain (#3)  
**Owner Documentação:** Doc Advocate (#17)  
**Último Update:** 2026-02-22 23:50 UTC

---

## 🎯 Objetivo

Implementar **Trailing Stop Loss (TSL) dinâmico** que ativa automaticamente após
atingir níveis de lucro predefinidos, protegendo ganhos sem sacrificar potencial
de upside.

**Visão:** Transformar lucros em risco reduzido, permitindo que operações
corridoras aproveitem movimentos de alta com proteção automática de capital.

---

## 📐 Conceituação

### O que é Trailing Stop Loss?

1. **Entry:** Abre posição em preço X
2. **Threshold:** Quando lucro ≥ 1.5R (15% do capital), TSL ativa
3. **Trailing:** Se preço subir, o stop sobe junto (mantém distância %)
4. **Proteção:** Se preço cair abaixo do trigger, fecha posição

### Exemplo Prático

```
Entry:       $100
Threshold:   $115 (lucro de 15% = 1.5R)
TSL Ativado: Quando ≥ $115
- Se sobe para $130: Stop move para $117 (mantém 10%)
- Se cai para $115: Posição fecha (preserva ganho)
- Se cai para $110: Posição fecha antes de -5%
```

### Diferença: Static SL vs. Dynamic TSL

| Aspecto | Static SL (-3%) | Trailing SL (dinâmico) |
|---------|-----------------|------------------------|
| **Proteção** | Até entry − 3% | Até lucro − X% |
| **Upside** | Ilimitado | Ilimitado |
| **Ativação** | Sempre ativa | Após threshold |
| **Ajuste** | Manual | Automático |
| **Melhor para** | Proteção rígida | Gestão de lucro |

---

## 🛠️ Requisitos Funcionais (RF)

### RF-TSL-001: Ativar Trailing Stop

**Descrição:** Sistema ativa TSL automaticamente quando atinge lucro threshold.

- **Entrada:** Posição aberta, lucro real-time
- **Condição:** `atual_lucro_pct >= threshold_ptcl` (padrão: 1.5R = 15%)
- **Saída:** Flag `trailing_active = True` no DB
- **Estado anterior:** `trailing_active = False`

**Teste:** Simular trade que sobe 15% → verificar flag ativa

---

### RF-TSL-002: Rastrear Maior Preço Atingido

**Descrição:** Mantém registro do **maior preço** desde ativação do TSL.

- **Entrada:** `current_price`, `trailing_active = True`
- **Lógica:** `trailing_high = MAX(trailing_high, current_price)`
- **Output:** Coluna `trailing_high` atualizada em tempo real
- **Persistência:** Salvar em DB a cada atualização

**Teste:** Trade sobe $100 → $130 → $120 → verificar `trailing_high = $130`

---

### RF-TSL-003: Calcular Nível de Stop Dinâmico

**Descrição:** Stop level segue automaticamente o high com distância %.

- **Fórmula:** `trailing_stop_price = trailing_high × (1 - trailing_stop_pct)`
- **Parâmetro:** `trailing_stop_pct = 0.10` (10% de distância)
- **Atualização:** A cada tick de preço ≥ 100ms

**Teste:** High = $130, distância 10% → Stop = $117

---

### RF-TSL-004: Fechar Posição ao Trigger

**Descrição:** Executa ordem de fechamento automático quando preço cai.

- **Condição:** `current_price <= trailing_stop_price`
- **Ação:** Market close order via Binance API
- **Registro:** Log motivo = `trailing_stop_activated`
- **Telemetria:** Registrar PnL final, horário, preço

**Teste:** Simular queda abaixo do TSL → fechar posição

---

### RF-TSL-005: Integração com Risk Gate 1.0

**Descrição:** TSL coexiste com Stop Loss estático (-3%) sem conflito.

- **Precedência:** TSL ativa apenas se `lucro >= threshold`
- **Fallback:** Se TSL desativa, SL (-3%) permanece ativo
- **Validação:** Ambas proteções nunca simultaneamente

**Teste:** Trade sobe 15% → TSL ativa, trade cai -3% → SL executa

---

### RF-TSL-006: Desativar TSL em Perda

**Descrição:** Se posição voltar a perda, TSL desativa automaticamente.

- **Condição:** `atual_lucro_pct < threshold_ptcl`
- **Ação:** `trailing_active = False`, voltar ao SL estático (-3%)
- **Cenário:** Trade ganha 20%, cai 10%, fica em lucro 10% → TSL mantém, se cai para -2% → SL ativa

---

## 🎲 Parâmetros Configuráveis

| Parâmetro | Padrão | Min | Max | Descrição |
|-----------|--------|-----|-----|-----------|
| `trailing_activation_threshold_r` | 1.5 | 0.5 | 5.0 | Risk units para ativar TSL (1.5R = 15% do capital) |
| `trailing_stop_distance_pct` | 0.10 | 0.05 | 0.20 | Distância % do TSL em relação ao high (10%) |
| `trailing_update_interval_ms` | 100 | 50 | 1000 | Intervalo de atualização (millisei) |
| `trailing_enabled` | True | - | - | Flag global para ativar/desativar TSL |

**Configuração:** `config/settings.py`

---

## 📊 Estrutura de Dados

### Novo Schema DB

```sql
ALTER TABLE trade_log ADD COLUMN trailing_activation_threshold DECIMAL(10, 2);
ALTER TABLE trade_log ADD COLUMN trailing_active BOOLEAN DEFAULT FALSE;
ALTER TABLE trade_log ADD COLUMN trailing_high DECIMAL(16, 8);
ALTER TABLE trade_log ADD COLUMN trailing_stop_price DECIMAL(16, 8);
ALTER TABLE trade_log ADD COLUMN trailing_activated_at TIMESTAMP;
ALTER TABLE trade_log ADD COLUMN trailing_stop_executed_at TIMESTAMP;
ALTER TABLE trade_log ADD COLUMN trailing_exit_reason VARCHAR(50);
```

### Estrutura Python (Trade Dataclass)

```python
@dataclass
class TrailingStopConfig:
    activation_threshold: float = 1.5  # R units
    stop_distance_pct: float = 0.10    # 10%
    update_interval_ms: int = 100
    enabled: bool = True

@dataclass
class TrailingStopState:
    active: bool = False
    high_price: float = 0.0
    stop_price: float = 0.0
    activated_at: Optional[datetime] = None
```

---

## 🔄 Fluxo de Operação

```
OPEN POSITION
    ↓
[Loop a cada 100ms]
    ↓
lucro_real_time = (preço_atual - entry) / entry
    ↓
    IF lucro_real_time >= threshold?
        YES → trailing_active = True
              trailing_high = MAX(trailing_high, preço_atual)
              trailing_stop = trailing_high × (1 - 0.10)
        NO  → IF preço_atual <= -3% entry?
              YES → CLOSE (SL estático)
              NO  → CONTINUE
    ↓
    IF trailing_active AND preço_atual <= trailing_stop?
        YES → CLOSE (TSL executado)
        NO  → CONTINUE
    ↓
[Fim do loop]
```

---

## ✅ Critérios de Aceite

### Gate 1: Design & Documentação

| # | Critério | Validação | Responsável |
|---|----------|-----------|-------------|
| 1 | Spec completa (este doc) | ✅ Arquivo exists | Doc Advocate (#17) |
| 2 | Arquitetura desenhada | ✅ Arch Design doc | Arch (#6) |
| 3 | Parâmetros definidos | ✅ settings.py | The Brain (#3) |
| 4 | DB schema pronto | ✅ migrations/ | Data (#11) |
| 5 | Test plan escrito | ✅ test_plan.md | Quality (#12) |

### Gate 2: Código & Integração

| # | Critério | Validação | Responsável |
|---|----------|-----------|-------------|
| 1 | TSL core implantado | `risk/trailing_stop.py` ready | Senior Engineer |
| 2 | Integrado em RiskGate | `risk/riskgate.py` updated | Arch (#6) |
| 3 | Binance API call OK | Testes integração | Data (#11) |
| 4 | Sem regressions S1 | `pytest tests/ -v` = 70 PASS + novos | Quality (#12) |
| 5 | Cobertura ≥ 85% | `pytest --cov=risk` | Audit (#8) |

### Gate 3: Validação & Testes

| # | Critério | Validação | Responsável |
|---|----------|-----------|-------------|
| 1 | 8 testes unitários | `pytest tests/test_trailing_stop.py -v` = 8 PASS | Quality (#12) |
| 2 | 4 testes integração | `pytest tests/test_tsl_integration.py -v` = 4 PASS | Quality (#12) |
| 3 | Backtest com TSL | Rodar backtest engine com TSL ativo | The Brain (#3) |
| 4 | PnL validado | Comparar TSL vs SL estático | Audit (#8) |
| 5 | Docs + examples | README + exemplos de uso | Doc Advocate (#17) |
| 6 | Code review | ✅ Arch + Senior aprovam | Arch (#6) |
| 7 | Marker "INVIOLÁVEL" | Nenhuma desabilitação da lógica | Guardian (#5) |

---

## 📁 Arquivos a Criar/Modificar

### Novos Arquivos
- `risk/trailing_stop.py` — Core logic
- `tests/test_trailing_stop.py` — Unit tests
- `tests/test_tsl_integration.py` — Integration tests
- `backtest/test_tsl_backtest.py` — Backtesting validation
- `docs/GUIDE_TRAILING_STOP.md` — User guide

### Modificações
- `risk/riskgate.py` — Integrar TSL check
- `config/settings.py` — Parâmetros TSL
- `execution/position_manager.py` — Update no loop de proteções
- `tests/test_protections.py` — Add TSL regression tests
- `db/migrations/` — Schema update script

---

## 📆 Timeline

| Fase | Data | Duração | Entregável |
|------|------|---------|-----------|
| **Design** | 22 FEV | 4h | Spec + Arch + Test Plan |
| **Implementação** | 23 FEV | 8h | Core code + Integração |
| **Testes** | 23-24 FEV | 8h | Unit + Integration + Backtest |
| **Validação** | 24 FEV | 4h | QA Gates + Sign-off |
| **Merge** | 24 FEV | 1h | PR + Sync Docs |

**Total:** ~25 horas de trabalho coordenado (24-48 horas calendar)

---

## 🚨 Riscos & Mitigação

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|--------|-----------|
| Conflito TSL + SL | MÉDIO | ALTO | Design explícito de FSM |
| Ordens não executam | BAIXA | CRÍTICO | Teste com API real em paper |
| Slippage não calculado | MÉDIO | MÉDIO | Validar spreads Binance |
| Race condition em DB | BAIXA | MÉDIO | Transaction locking |

---

## 🎯 Sucesso = Critério

✅ **GO** quando:
1. Spec aprovada
2. Código review ✅
3. 12 testes PASS + ≥ 85% coverage
4. 0 regressions Sprint 1 (70 testes)
5. Backtest com TSL ≥ estatisticamente melhor que SL estático
6. Nenhuma desabilitação da lógica (INVIOLÁVEL)

---

*Documento vivo — Atualizar conforme Squad progride.*
