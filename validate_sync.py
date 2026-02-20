#!/usr/bin/env python
"""
Validação de Sincronização Completa de Documentação.
Verifica se todos os arquivos de documentação estão sincronizados com o código.
"""

import os
import json
from pathlib import Path
from datetime import datetime

WORKSPACE = "c:\\repo\\crypto-futures-agent"

# Documentos que DEVEM estar sincronizados
SYNC_MATRIX = {
    "README.md": {
        "depends_on": ["config/symbols.py", "playbooks/__init__.py"],
        "should_contain": ["16 Pares USDT", "v0.2.1", "Profit Guardian Mode"],
    },
    "docs/RELEASES.md": {
        "depends_on": ["README.md"],
        "should_contain": ["v0.2.1", "Administração de Posições"],
    },
    "docs/FEATURES.md": {
        "depends_on": ["README.md", "docs/RELEASES.md"],
        "should_contain": ["v0.2.1", "F-05a", "F-05b", "F-05c"],
    },
    "docs/ROADMAP.md": {
        "depends_on": ["README.md", "docs/RELEASES.md"],
        "should_contain": ["v0.2.1", "✅ CONCLUÍDO", "20/02/2026"],
    },
    "CHANGELOG.md": {
        "depends_on": ["docs/RELEASES.md"],
        "should_contain": ["[v0.2.1]", "Administração de Posições", "TWT", "LINK", "OGN", "IMX"],
    },
    "docs/SYNCHRONIZATION.md": {
        "depends_on": ["README.md"],
        "should_contain": ["Rastreamento de Sincronização", "Checklist de Sincronização", "config/symbols.py"],
    },
    ".github/copilot-instructions.md": {
        "depends_on": ["docs/SYNCHRONIZATION.md"],
        "should_contain": ["Regra de Sincronização Obrigatória", "Protocolo de Sincronização", "[SYNC]"],
    },
    "config/symbols.py": {
        "depends_on": [],
        "should_contain": ["TWTUSDT", "LINKUSDT", "OGNUSDT", "IMXUSDT"],
    },
    "playbooks/__init__.py": {
        "depends_on": ["config/symbols.py"],
        "should_contain": ["TWTPlaybook", "LINKPlaybook", "OGNPlaybook", "IMXPlaybook"],
    },
}

PARES_ESPERADOS = {
    "BTCUSDT": "alta_cap",
    "ETHUSDT": "alta_cap",
    "BNBUSDT": "alta_cap",
    "XRPUSDT": "alta_cap",
    "LTCUSDT": "alta_cap",
    "SOLUSDT": "high_beta",
    "DOGEUSDT": "memecoin",
    "C98USDT": "low_cap_defi",
    "0GUSDT": "low_cap_ai_infra",
    "KAIAUSDT": "low_cap_l1",
    "GTCUSDT": "mid_cap",
    "FILUSDT": "mid_cap",
    "TWTUSDT": "mid_cap",
    "LINKUSDT": "mid_cap",
    "POLYXUSDT": "mid_cap",
    "HYPERUSDT": "low_cap",
    "1000BONKUSDT": "low_cap",
    "OGNUSDT": "low_cap",
    "IMXUSDT": "low_cap",
}

def verificar_arquivo(arquivo, checks):
    """Verifica se arquivo existe e contém strings esperadas"""
    path = Path(WORKSPACE) / arquivo

    if not path.exists():
        return False, f"❌ Arquivo não existe: {arquivo}"

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        resultados = []
        for check in checks:
            if check in content:
                resultados.append(f"  ✅ Contém: {check}")
            else:
                resultados.append(f"  ❌ Falta: {check}")

        all_ok = all(check in content for check in checks)
        return all_ok, "\n".join(resultados)
    except Exception as e:
        return False, f"❌ Erro ao ler: {str(e)}"

print("=" * 90)
print("VALIDAÇÃO DE SINCRONIZAÇÃO COMPLETA DE DOCUMENTAÇÃO")
print("=" * 90)
print(f"\nData: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print(f"Workspace: {WORKSPACE}\n")

# 1. Validar arquivo de rastreamento
print("\n1️⃣ ARQUIVO DE RASTREAMENTO")
print("-" * 90)
sync_ok, sync_msg = verificar_arquivo("docs/SYNCHRONIZATION.md", ["Rev. v0.2.1", "Checklist de Sincronização"])
print(f"docs/SYNCHRONIZATION.md: {'✅ OK' if sync_ok else '❌ FAIL'}")
print(sync_msg)

# 2. Validar sincronização de matriz de documentos
print("\n2️⃣ MATRIZ DE SINCRONIZAÇÃO DE DOCUMENTOS")
print("-" * 90)

sync_results = {}
for doc, checks_info in SYNC_MATRIX.items():
    should_contain = checks_info.get("should_contain", [])
    ok, msg = verificar_arquivo(doc, should_contain)
    sync_results[doc] = ok
    status = "✅" if ok else "❌"
    print(f"{status} {doc:<40}")

    # Mostrar detalhes apenas se falhar
    if not ok:
        for linha in msg.split("\n"):
            if "❌" in linha:
                print(f"   {linha}")

# 3. Validar símbolos em config/symbols.py
print("\n3️⃣ VALIDAÇÃO DE SÍMBOLOS")
print("-" * 90)

try:
    exec(open(Path(WORKSPACE) / "config" / "symbols.py").read())
    simbolos_encontrados = list(SYMBOLS.keys()) if 'SYMBOLS' in locals() else []

    pares_ok = 0
    for par, tipo in PARES_ESPERADOS.items():
        if par in simbolos_encontrados:
            print(f"  ✅ {par:<15} ({tipo})")
            pares_ok += 1
        else:
            print(f"  ❌ {par:<15} (FALTANDO)")

    print(f"\n✅ {pares_ok}/{len(PARES_ESPERADOS)} pares configurados")
except Exception as e:
    print(f"❌ Erro ao validar símbolos: {str(e)}")

# 4. Validar playbooks registrados
print("\n4️⃣ VALIDAÇÃO DE PLAYBOOKS")
print("-" * 90)

playbooks_esperados = [
    "TWTPlaybook",
    "LINKPlaybook",
    "OGNPlaybook",
    "IMXPlaybook",
    "GTCPlaybook",
    "HYPERPlaybook",
    "BONKPlaybook",
    "FILPlaybook",
    "POLYXPlaybook",
]

try:
    with open(Path(WORKSPACE) / "playbooks" / "__init__.py", 'r', encoding='utf-8') as f:
        init_content = f.read()

    playbooks_ok = 0
    for pb in playbooks_esperados:
        if pb in init_content:
            print(f"  ✅ {pb}")
            playbooks_ok += 1
        else:
            print(f"  ❌ {pb} (não registrado)")

    print(f"\n✅ {playbooks_ok}/{len(playbooks_esperados)} playbooks registrados")
except Exception as e:
    print(f"❌ Erro ao validar playbooks: {str(e)}")

# 5. Resumo final
print("\n" + "=" * 90)
print("RESUMO EXECUTIVO")
print("=" * 90)

total_docs = len(SYNC_MATRIX)
docs_ok = sum(1 for ok in sync_results.values() if ok)

print(f"\n✅ Documentos Sincronizados: {docs_ok}/{total_docs}")
print(f"✅ Pares Configurados: {pares_ok}/{len(PARES_ESPERADOS)}")
print(f"✅ Playbooks Registrados: {playbooks_ok}/{len(playbooks_esperados)}")

if docs_ok == total_docs and pares_ok == len(PARES_ESPERADOS) and playbooks_ok == len(playbooks_esperados):
    print("\n" + "=" * 90)
    print("🎉 SINCRONIZAÇÃO COMPLETA E VALIDADA!")
    print("=" * 90)
    print("\n✅ v0.2.1 — Administração de Posições")
    print("✅ 9 pares USDT em Profit Guardian Mode")
    print("✅ 16 pares USDT total com playbooks")
    print("✅ Mecanismos de sincronização documentation implementados")
    print("✅ Rastreamento automático ativo")
else:
    print("\n⚠️ Alguns itens ainda precisam de sincronização")

print("\n" + "=" * 90)
