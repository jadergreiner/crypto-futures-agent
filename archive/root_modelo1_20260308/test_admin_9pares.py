#!/usr/bin/env python
"""
Teste de validação para administração de posição dos 9 pares USDT.
Valida que todos os símbolos, playbooks e configurações estão em lugar.
"""

from config.symbols import SYMBOLS, ALL_SYMBOLS
from config.execution_config import AUTHORIZED_SYMBOLS
from playbooks import (
    GTCPlaybook, HYPERPlaybook, BONKPlaybook, FILPlaybook,
    TWTPlaybook, POLYXPlaybook, LINKPlaybook, OGNPlaybook, IMXPlaybook
)

# Pares que devem estar configurados (conforme solicitado)
PARES_SOLICITADOS = [
    'GTCUSDT', 'HYPERUSDT', '1000BONKUSDT', 'FILUSDT',
    'TWTUSDT', 'POLYXUSDT', 'LINKUSDT', 'OGNUSDT', 'IMXUSDT'
]

# Playbooks que devem estar funcionando
PLAYBOOK_CLASSES = [
    GTCPlaybook, HYPERPlaybook, BONKPlaybook, FILPlaybook,
    TWTPlaybook, POLYXPlaybook, LINKPlaybook, OGNPlaybook, IMXPlaybook
]

print("=" * 80)
print("VALIDAÇÃO DE ADMINISTRAÇÃO DE POSIÇÃO PARA 9 PARES USDT")
print("=" * 80)

# 1. Validar símbolos em SYMBOLS
print("\n1. Validando símbolos em config/symbols.py...")
pares_em_symbols = [p for p in PARES_SOLICITADOS if p in SYMBOLS]
print(f"   ✓ {len(pares_em_symbols)}/{len(PARES_SOLICITADOS)} pares encontrados em SYMBOLS")
for p in pares_em_symbols:
    config = SYMBOLS[p]
    classificacao = config.get('classificacao', 'N/A')
    beta = config.get('beta_estimado', 1.0)
    print(f"     - {p:<15} {classificacao:<30} beta={beta:.1f}")

missing_symbols = [p for p in PARES_SOLICITADOS if p not in SYMBOLS]
if missing_symbols:
    print(f"   ✗ FALTANDO: {missing_symbols}")
else:
    print("   ✓ Todos os símbolos estão em SYMBOLS")

# 2. Validar ALL_SYMBOLS
print("\n2. Validando ALL_SYMBOLS...")
pares_em_all = [p for p in PARES_SOLICITADOS if p in ALL_SYMBOLS]
print(f"   ✓ {len(pares_em_all)}/{len(PARES_SOLICITADOS)} pares em ALL_SYMBOLS")

# 3. Validar AUTHORIZED_SYMBOLS
print("\n3. Validando AUTHORIZED_SYMBOLS...")
pares_autorizados = [p for p in PARES_SOLICITADOS if p in AUTHORIZED_SYMBOLS]
print(f"   ✓ {len(pares_autorizados)}/{len(PARES_SOLICITADOS)} pares em AUTHORIZED_SYMBOLS")

# 4. Validar playbooks
print("\n4. Validando playbooks...")
pbs_criados = []
try:
    for cls in PLAYBOOK_CLASSES:
        pb = cls()
        symbol = pb.symbol
        classificacao = pb.classificacao
        beta = pb.beta
        pbs_criados.append((symbol, classificacao, beta))
    print(f"   ✓ {len(pbs_criados)}/{len(PLAYBOOK_CLASSES)} playbooks criados com sucesso")
    for symbol, classificacao, beta in pbs_criados:
        print(f"     - {symbol:<15} {classificacao:<30} beta={beta:.1f}")
except Exception as e:
    print(f"   ✗ Erro ao criar playbooks: {e}")
    import traceback
    traceback.print_exc()

# 5. Resumo final
print("\n" + "=" * 80)
total_validacoes = (
    len(pares_em_symbols) +
    len(pares_em_all) +
    len(pares_autorizados) +
    len(pbs_criados)
)
total_esperado = len(PARES_SOLICITADOS) * 4  # 4 validações por par

print(f"RESULTADO: {total_validacoes}/{total_esperado} validações OK")

if total_validacoes == total_esperado:
    print("\n✓✓✓ ADMINISTRAÇÃO DE POSIÇÃO PARA 9 PARES CONFIGURADA COM SUCESSO ✓✓✓")
    print("\nPares configurados:")
    for i, par in enumerate(PARES_SOLICITADOS, 1):
        print(f"  {i}. {par}")
else:
    print(f"\n⚠ Algumas validações falharam ({total_validacoes}/{total_esperado})")

print("=" * 80)
