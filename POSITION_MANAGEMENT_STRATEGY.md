# Estratégia de Gerenciamento de Posições Abertas

## 📋 Resumo Executivo

O sistema agora tem **3 fases** de operação:

### **FASE 1: Abertura da Posição** ✅ COMPLETO
- Executar ordem MARKET para entrada
- Criar **STOP_MARKET** (apregoado no Binance)
- Criar **TAKE_PROFIT_MARKET** (apregoado no Binance)
- Registrar todos os 3 IDs: `binance_order_id`, `binance_sl_order_id`, `binance_tp_order_id`

### **FASE 2: Administração de Realizes Parciais** 🔄 NOVO
- Monitorar posição enquanto aberta
- Executar fechamentos parciais (ex: 25%, 50%, 75%)
- Para cada parcial:
  - CANCELAR o antigo SL/TP (se ainda existem)
  - EXECUTAR ordem SELL parcial (reduzir quantidade)
  - RECRIAR novo SL/TP com quantidade reduzida
- Manter cada fechamento em histórico

### **FASE 3: Gestão de Risco Contínuo** 🛡️
- Monitoramento de liquidação (se < 1% de margem)
- Ajuste de SL se TP foi atingido parcialmente
- Stop automático após 2 horas
- Registro auditável de todas as ações

---

## 🎯 Fluxo Completo de Uma Operação

```
┌─────────────────────────────────────────────────────┐
│ [ABERTURA] Executar 1 MARKET order                  │
│  └─ Abrir 2,176 ANKR @ $0.00459810                  │
│     binance_order_id: 5412778331                    │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│ [SL/TP CONDICIONAL] Criar 2 ordens "apregoadas"     │
│  ├─ STOP_MARKET @ $0.00436810 (algo_id: 300..546)  │
│  └─ TAKE_PROFIT_MARKET @ $0.00505790 (algo_id: ..) │
└─────────────────────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
    [SE SL GATILHA]        [SE TP GATILHA]
    Posição fechada        Parcial realizado?
    Trade finalizado       │
                           ▼
                    ┌──────────────────┐
                    │ [PARCIAL 1: 50%] │
                    │ VENDER 1,088 ANKR│
                    │ + criar novo SL/TP
                    │ com 1,088 restante
                    └──────────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
              [PARCIAL 2]   [PARCIAL 3]
              (25% restante) (25% residual)
              ...
```

---

## 📊 Estrutura de Dados (BD)

### trade_log (já existe)
```sql
Campos críticos para gestão:
- trade_id              (PK, identificador único)
- timestamp_entrada     (quando abriu)
- timestamp_saida       (quando fechou - NULL se aberto)
- entry_price          (preço de entrada)
- exit_price           (preço de saída - NULL se aberto)
- status               (ABERTA, PARCIAL_1, PARCIAL_2, FECHADA)
- binance_order_id     (ordem de entrada)
- binance_sl_order_id  (algo_id do SL - pode ser cancelado)
- binance_tp_order_id  (algo_id do TP - pode ser cancelado)
```

### trade_partial_exits (NOVO - tabela de realizações)
```sql
CREATE TABLE trade_partial_exits (
    partial_id INTEGER PRIMARY KEY,
    trade_id INTEGER NOT NULL,          -- FK para trade_log
    partial_number INTEGER,              -- 1=primeiro, 2=segundo, ...
    quantity_closed REAL,                -- quanto foi fechado parcialmente
    quantity_remaining REAL,             -- quanto ficou na posição
    exit_price REAL,                    -- preço de saída na parcial
    exit_time INTEGER,                  -- timestamp de saída
    binance_order_id_close TEXT,        -- ID da ordem de fechamento
    binance_sl_order_id_new TEXT,       -- novo SL algo_id após parcial
    binance_tp_order_id_new TEXT,       -- novo TP algo_id após parcial
    reason TEXT                         -- por quê fechou: "TP_TRIGGER", "MANUAL", etc
);
```

---

## 🔧 Implementação: 3 Scripts Principais

### 1. `manage_open_position.py` (JÁ EXISTE: execute_1dollar_trade.py)
**O que faz**: Abre a posição com SL/TP reais
✅ COMPLETO desde a última implementação

### 2. `administrate_partial_exits.py` (NOVO)
**O que faz**: Gerencia realizações parciais
- Listar posições abertas
- Calcular pontos de parcial (25%, 50%, 75%)
- Executar fechamento parcial
- Recriar SL/TP automático com novo tamanho

**Fluxo mínimo**:
```python
# Exemplo de uso:
administrate = PartialExitManager(client, db)

# 1. Listar posições abertas
open_positions = administrate.list_open_positions()

# 2. Realizar 50% de lucro (se TP foi atingido)
administrate.close_partial(
    trade_id=7,
    percentage=0.50,  # Fechar 50%
    reason="TP_TRIGGER"
)
# Internamente faz:
#   a. Cancelar SL/TP antigas
#   b. Vender 50% da posição
#   c. Criar novo SL/TP com 50% restante
#   d. Registrar em trade_partial_exits

# 3. Registrar no histórico
```

### 3. `monitor_and_manage_positions.py` (NOVO)
**O que faz**: Roda continuamente, monitora e gerencia automaticamente
- A cada 60 segundos:
  - Verifica se SL/TP trigaram (já fechou?)
  - Se não, checa se precisa realizar parcial automático
  - Atualiza PnL em tempo real
  - Aplica proteção de liquidação (se <1%)

---

## 📌 Integração com `iniciar.bat`

A opção 8 ("Assumir/Gerenciar Posição Aberta") deveria rodar:

```bat
:opcao8
echo GERENCIAR POSICOES ABERTAS
echo ==============================================================================
echo.
echo Menu:
echo  1. Listar posicoes abertas
echo  2. Realizar parcial manualmente (50%%, 75%%, etc)
echo  3. Ajustar SL para breakeven
echo  4. Fechar posicao inteira
echo  5. Voltar
echo.

set /p OP="Opcao: "
if "!OP!"=="1" python scripts/manage_positions.py --list
if "!OP!"=="2" python scripts/manage_positions.py --partial
if "!OP!"=="3" python scripts/manage_positions.py --breakeven
if "!OP!"=="4" python scripts/manage_positions.py --close-all
```

---

## 💡 Exemplo Prático: Operação Completa

### T0: Abertura (Trade ID 7)
```
✅ ABERTO: 2,174 ANKR @ $0.00459815
├─ Order ID (MARKET): 5412778331
├─ SL @ $0.00436824 (Algo ID: 3000000742992546)
└─ TP @ $0.00505797 (Algo ID: 3000000742992581)
```

### T1: +1 hora (Preço subiu para $0.00480)
```
⚠️ PREÇO: $0.00480 (+4.3%)
Decisão: Realizar 50% de lucro (move SL para breakeven)

Ações:
1. Cancelar SL antigo (Algo ID: 300...)
2. VENDER 1,087 ANKR @ market price
3. Registrar como PARCIAL_1:
   - quantity_closed: 1,087
   - quantity_remaining: 1,087
   - exit_price: $0.00480

4. RECRIAR SL/TP com 1,087 restante:
   - SL novo @ breakeven (~$0.00459)
   - TP novo @ $0.00505797 (ajustado)
```

### T2: +2 horas (Preço atingiu TP parcial)
```
✅ PARCIAL 2 TRIGADO: SL atingido @ $0.00459
- Binance executa ordem automática
- Posição vai de 1,087 para 0
- Trade ID 7 finalizado com 2 parciais

Resultado:
- Parcial 1: +2.2% ganho
- Parcial 2: +breakeven (proteção)
- PnL total: +2.2% da posição
```

---

## 🚀 Próximas Implementações

### Curto Prazo (Próximas 24h)
1. ✅ Criar `trade_partial_exits` table no BD
2. ✅ Criar `PartialExitManager` class
3. ✅ Criar script `manage_positions.py` interativo
4. ✅ Testar com Trade ID 7 (1 parcial 50%)

### Médio Prazo
1. Automação: `monitor_and_manage_positions.py` rodando
2. Integração com iniciar.bat opção 8
3. Dashboard mostrando estado em tempo real

### Longo Prazo
1. Apostar que SL/TP vão auto-triggar
2. Concentrar em NEW trades (não gasta tempo monitorando)
3. Escalar para múltiplas posições simultâneas

---

## ⚠️ Restrições Atuais

1. **Margem**: Apenas $6 restante
   - Máximo de 1 posição aberta por vez
   - Depois fecha a parcial/total antes de nova abertura

2. **Binance SL/TP Real**
   - Sem dependência de monitor local
   - Executa 24/7 mesmo offline
   - Auditável via Binance API

3. **Parciais Manuais**
   - Quando SL/TP trigam, Binance fecha automaticamente
   - Parciais adicionais precisam ser MANUAIS (via script)
   - Não há automação de parciais ainda (fase 2)

---

## 📖 Referência Rápida

| Situação | Ação | Script |
|----------|------|--------|
| Abrir nova | `execute_1dollar_trade.py` | ✅ |
| Listar abertas | `manage_positions.py --list` | 🔄 |
| Realizar parcial | `manage_positions.py --partial --id 7 --pct 50` | 🔄 |
| Ajustar SL | `manage_positions.py --breakeven --id 7` | 🔄 |
| Fechar tudo | `manage_positions.py --close-all --id 7` | 🔄 |
| Monitorar auto | `monitor_and_manage_positions.py` | 🔄 |

**Status**: ✅ Feito | 🔄 Em Progresso | ❌ Planejado

