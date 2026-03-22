---
name: symbol-onboarding
description: |
  Checklist para adicionar novo simbolo ao pipeline M2.
  Cobre configuracao, playbook, testes e inicializacao de dados.
  Propaga automaticamente para AUTHORIZED_SYMBOLS e M2_SYMBOLS.
metadata:
  tags:
    - simbolo
    - onboarding
    - pipeline
    - modelo2
    - config
  focus:
    - acao-direta
    - checklist-minimo
    - auditabilidade
user-invocable: true
---

# Skill: symbol-onboarding

## Objetivo

Guiar a adicao de um novo simbolo ao pipeline M2 com o menor esforco
possivel e garantia de que todos os pontos criticos foram cobertos.

Use esta skill para:

- adicionar um simbolo novo ao pipeline M2
- verificar se um simbolo existente esta configurado corretamente
- diagnosticar por que um simbolo nao esta sendo escaneado ou executado
- auditar a consistencia entre config, playbook, testes e dados

## Modo Economico

Regra principal: ler apenas os arquivos necessarios.

Ordem de leitura:

1. `config/symbols.py` — sempre o primeiro: estrutura da entrada e
   lista existente (ALL_SYMBOLS linha ~909).
2. `playbooks/__init__.py` — verificar importacoes e __all__.
3. `playbooks/btc_playbook.py` ou similar — template de playbook.
4. `tests/test_fluxusdt_integration.py` — template de teste.
5. Demais arquivos apenas se houver duvida especifica reportada.

Evitar:

- ler blocos inteiros de core/model2/ sem indicio de problema concreto
- rodar comandos live sem confirmar M2_EXECUTION_MODE=shadow primeiro
- fazer sync em docs que nao foram impactados

## Fluxo Operacional

1. Receber: simbolo (ex: `SOLUSDT`), classificacao desejada, beta e
   caracteristicas relevantes.
2. Validar se o simbolo ja existe em `config/symbols.py`.
3. Executar os passos obrigatorios na ordem do checklist abaixo.
4. Executar os passos opcionais conforme necessidade.
5. Rodar `pytest -q tests/` e corrigir falhas antes de commit.
6. Registrar em `docs/SYNCHRONIZATION.md` e fazer commit com `[FEAT]`.

## Checklist

### OBRIGATORIOS (bloqueantes)

#### Passo 1 — Registrar em `config/symbols.py`

Adicionar entrada no dicionario `SYMBOLS` com os campos obrigatorios:

```python
"SOLUSDT": {
    "papel": "Descricao funcional do ativo",
    "ciclo_proprio": "Descricao do ciclo de mercado tipico",
    "correlacao_btc": [0.55, 0.80],   # [min, max] historico
    "beta_estimado": 1.8,              # 1.0=BTC, >2.0=altcoin volatil
    "classificacao": "alta_cap",       # ver valores aceitos abaixo
    "caracteristicas": [               # lista livre de tags
        "proof_of_stake",
        "high_beta",
        "layer1_alt"
    ]
}
```

**Valores aceitos para `classificacao`:**

| Valor | Perfil |
|---|---|
| `alta_cap` | Alta liquidez, >$10B market cap |
| `mid_cap_defi` | DeFi com liquidez media |
| `mid_cap_cross_chain` | Infraestrutura cross-chain |
| `low_cap_speculative` | Alta volatilidade, baixa liquidez |
| `large_cap_infrastructure` | Infra de blockchain grande porte |
| `memecoin` | Especulativo puro |
| `niche_token` | Caso de uso nicho |

**Efeito automatico:** `ALL_SYMBOLS`, `AUTHORIZED_SYMBOLS` e
`M2_SYMBOLS` incluem o novo simbolo sem alteracao adicional.

---

#### Passo 2 — Criar playbook em `playbooks/`

Criar `playbooks/sol_playbook.py` (ou equivalente) seguindo o padrao:

```python
from playbooks.base_playbook import BasePlaybook


class SOLPlaybook(BasePlaybook):
    """Playbook para SOLUSDT."""

    def __init__(self) -> None:
        super().__init__("SOLUSDT")

    def get_confluence_adjustments(self, context: dict) -> dict:
        """Ajustes de confluencia especificos para SOL."""
        adjustments: dict = {}
        # Exemplo: reduzir entrada em periodos de alta volatilidade L1
        if context.get("volatilidade") == "alta":
            adjustments["min_confluence_score"] = 0.75
        return adjustments

    def get_risk_adjustments(self, context: dict) -> dict:
        """Ajustes de risco especificos para SOL."""
        # Beta alto: reduzir tamanho de posicao em tendencia lateral
        return {"position_size_multiplier": 0.85}
```

---

#### Passo 3 — Registrar playbook em `playbooks/__init__.py`

```python
# Adicionar import
from .sol_playbook import SOLPlaybook

# Adicionar em __all__
__all__ = [
    # ... existentes ...
    "SOLPlaybook",
]
```

---

#### Passo 4 — Criar teste de integracao

Criar `tests/test_solusdt_integration.py` copiando o padrao de
`tests/test_fluxusdt_integration.py` e adaptando:

```python
SYMBOL = "SOLUSDT"
EXPECTED_BETA_RANGE = (1.5, 2.5)
EXPECTED_CLASSIFICACAO = "alta_cap"
EXPECTED_CARACTERISTICAS_SUBSET = ["proof_of_stake", "high_beta"]

def test_symbol_in_symbols(): ...
def test_mandatory_fields(): ...
def test_symbol_in_all_symbols(): ...
def test_symbol_in_authorized_symbols(): ...
def test_beta_in_range(): ...
def test_classificacao(): ...
def test_caracteristicas(): ...
def test_playbook_instantiation(): ...
def test_playbook_loads_metadata(): ...
```

Rodar: `pytest -q tests/test_solusdt_integration.py`

---

### OPCIONAIS

#### Passo 5 — Coletar dados historicos OHLCV

```bash
python scripts/model2/sync_ohlcv_from_binance.py \
    --symbols "SOLUSDT" \
    --timeframes H4 H1 D1
```

Verificar minimo de 500 candles H4 para viabilizar treinamento.

#### Passo 6 — Testar pipeline local (modo shadow)

```bash
# Garantir modo shadow antes de qualquer execucao
export M2_EXECUTION_MODE=shadow   # Linux/Mac
$env:M2_EXECUTION_MODE="shadow"   # Windows PowerShell

python scripts/model2/scan.py --symbol SOLUSDT --timeframe H4
python scripts/model2/track.py --symbol SOLUSDT --timeframe H4
python scripts/model2/validate.py --symbol SOLUSDT --timeframe H4
```

#### Passo 7 — Incluir em M2_LIVE_SYMBOLS (quando pronto para shadow/live)

No arquivo `.env`:

```dotenv
M2_LIVE_SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT
```

**Atencao:** So adicionar apos validar steps 1-4 e coletar dados
historicos suficientes.

#### Passo 8 — Treinar modelo com novo simbolo

```bash
python main.py --train --symbols "SOLUSDT"
```

---

## Diagnostico de Problemas

### Simbolo nao escaneado

```bash
# Verificar se esta em M2_SYMBOLS
python -c "from config.settings import M2_SYMBOLS; print('SOLUSDT' in M2_SYMBOLS)"

# Verificar se M2_LIVE_SYMBOLS esta sobrescrevendo
python -c "import os; print(os.getenv('M2_LIVE_SYMBOLS', '<vazio>'))"
```

### Simbolo bloqueado na ordem

```bash
# Verificar se esta em AUTHORIZED_SYMBOLS
python -c "from config.execution_config import AUTHORIZED_SYMBOLS; print('SOLUSDT' in AUTHORIZED_SYMBOLS)"
```

Causa mais comum: simbolo nao esta em `config/symbols.py`.

### Candles insuficientes

```sql
-- Verificar cobertura em db/crypto_agent.db
SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
FROM ohlcv_h4
WHERE symbol = 'SOLUSDT';
```

Minimo necessario para treinamento: **500 candles H4**.

---

## Sincronizacao de Documentacao

Apos completar o onboarding, registrar em `docs/SYNCHRONIZATION.md`:

| Componente | Arquivo | Mudanca |
|---|---|---|
| Novo simbolo | config/symbols.py | SOLUSDT adicionado |
| Novo playbook | playbooks/sol_playbook.py | Criado |
| Registro playbook | playbooks/__init__.py | Importacao e __all__ |
| Teste | tests/test_solusdt_integration.py | Criado |

Commit: `[FEAT] Adicionar SOLUSDT ao pipeline M2`

Sincronizar `README.md` se houver lista publica de simbolos suportados.
Sincronizar `docs/SYNCHRONIZATION.md` sempre (regra do projeto).

---

## Guardrails

- Nunca executar scan/track/validate com `M2_EXECUTION_MODE=live` antes
  de validar todos os passos obrigatorios e os dados historicos.
- Nao adicionar simbolo sem entrada em `config/symbols.py` — o sistema
  nao impedira a insercao, mas o playbook e os testes falharao.
- Nao criar playbook sem `super().__init__("SIMBOLO")` — o BasePlaybook
  exige o simbolo para carregar metadados de risco.
- Parametros de risco globais (`config/risk_params.py`) nao devem ser
  alterados para acomodar um simbolo especifico. Usar o playbook.

## Formato de Resposta

Para cada passo executado:

```
PASSO: <numero e nome>
STATUS: <OK | PENDENTE | FALHOU>
EVIDENCIA: <arquivo alterado, teste passando, contagem de candles, etc.>
PROXIMO: <proximo passo ou acao necessaria>
```

Para diagnostico de problema existente:

```
SIMBOLO: <XYZUSDT>
PROBLEMA: <descricao objetiva>
CAUSA: <arquivo e linha ou configuracao ausente>
CORRECAO: <passo exato a executar>
```
