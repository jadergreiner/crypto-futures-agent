#!/usr/bin/env python
"""
Teste rápido para validar configuration dos novos pares.
"""

from config.symbols import SYMBOLS, ALL_SYMBOLS
from config.execution_config import AUTHORIZED_SYMBOLS
from playbooks import (
    DASHPlaybook, ZKPlaybook, WHYPlaybook, XAIPlaybook,
    GTCPlaybook, CELOPlaybook, HYPERPlaybook, MTLPlaybook,
    POLYXPlaybook, BONKPlaybook
)

# Pares que devem estar configurados
PARES = [
    'ZKUSDT', '1000WHYUSDT', 'XIAUSDT', 'GTCUSDT', 'CELOUSDT',
    'HYPERUSDT', 'MTLUSDT', 'POLYXUSDT', '1000BONKUSDT', 'DASHUSDT'
]

# Playbooks que devem estar funcionando
PLAYBOOK_CLASSES = [
    DASHPlaybook, ZKPlaybook, WHYPlaybook, XAIPlaybook,
    GTCPlaybook, CELOPlaybook, HYPERPlaybook, MTLPlaybook,
    POLYXPlaybook, BONKPlaybook
]

print("=" * 70)
print("VALIDAÇÃO DE ADMINISTRAÇÃO DE POSIÇÃO PARA PARES USDT")
print("=" * 70)

# 1. Validar símbolos em SYMBOLS
print("\n1. Validando símbolos em config/symbols.py...")
pares_em_symbols = [p for p in PARES if p in SYMBOLS]
print(f"   ✓ {len(pares_em_symbols)}/{len(PARES)} pares encontrados em SYMBOLS")
for p in pares_em_symbols:
    config = SYMBOLS[p]
    print(f"     - {p:<15} {config.get('classificacao', 'N/A'):<25} beta={config.get('beta_estimado', 1.0)}")

# 2. Validar ALL_SYMBOLS
print("\n2. Validando ALL_SYMBOLS...")
pares_em_all = [p for p in PARES if p in ALL_SYMBOLS]
print(f"   ✓ {len(pares_em_all)}/{len(PARES)} pares em ALL_SYMBOLS")

# 3. Validar AUTHORIZED_SYMBOLS
print("\n3. Validando AUTHORIZED_SYMBOLS...")
pares_autorizados = [p for p in PARES if p in AUTHORIZED_SYMBOLS]
print(f"   ✓ {len(pares_autorizados)}/{len(PARES)} pares em AUTHORIZED_SYMBOLS")

# 4. Validar playbooks
print("\n4. Validando playbooks...")
pbs_criados = []
try:
    for cls in PLAYBOOK_CLASSES:
        pb = cls()
        pbs_criados.append((pb.symbol, pb.classificacao, pb.beta))
    print(f"   ✓ {len(pbs_criados)} playbooks criados com sucesso")
    for symbol, classificacao, beta in pbs_criados:
        print(f"     - {symbol:<15} {classificacao:<25} beta={beta}")
except Exception as e:
    print(f"   ✗ Erro ao criar playbooks: {e}")

# 5. Resumo
print("\n" + "=" * 70)
total_ok = len(pares_em_symbols) + len(pares_em_all) + len(pares_autorizados) + len(pbs_criados)
total_esperado = len(PARES) * 4  # 4 validações por par
print(f"RESULTADO: {total_ok}/{total_esperado} validações OK")
if total_ok == total_esperado:
    print("✓✓✓ ADMINISTRAÇÃO DE POSIÇÃO CONFIGURADA COM SUCESSO ✓✓✓")
else:
    print(f"⚠ Algumas validações falharam. Verificar detalhes acima.")
print("=" * 70)
