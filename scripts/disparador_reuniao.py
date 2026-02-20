#!/usr/bin/env python3
"""
Script Disparador de Reunião Ad-hoc
Chama a reunião com contexto de mercado opcional

Uso:
    python scripts/disparador_reuniao.py
    
    Ou com contexto:
    python scripts/disparador_reuniao.py --contexto "BTC caiu 15%, FVG aberto em H4"
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.executar_reuniao_semanal import ExecutorReuniao


def main():
    """Dispara reunião com contexto de mercado opcional."""
    parser = argparse.ArgumentParser(
        description="Disparador de Reunião Head × Operador (ad-hoc)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:

  1. Reunião imediata (sem contexto)
     $ python scripts/disparador_reuniao.py

  2. Reunião com movimento de mercado
     $ python scripts/disparador_reuniao.py \\
         --contexto "BTC caiu 15%, FVG aberto acima em H4"

  3. Reunião por problemas técnicos
     $ python scripts/disparador_reuniao.py \\
         --contexto "3 rejeições de ordem, latência 50ms"

  4. Reunião para aprovar investimento
     $ python scripts/disparador_reuniao.py \\
         --contexto "Proposta: Compra RAM 32GB, ROI +12%"
        """
    )

    parser.add_argument(
        "--contexto",
        type=str,
        default=None,
        help="Contexto de mercado ou operacional (opcional)"
    )

    parser.add_argument(
        "--head",
        type=str,
        default="Roberto Silva",
        help="Nome do Head Financeiro (default: Roberto Silva)"
    )

    parser.add_argument(
        "--operador",
        type=str,
        default="v0.3",
        help="Versão do operador (default: v0.3)"
    )

    args = parser.parse_args()

    # Criar executor
    executor = ExecutorReuniao()

    print("\n" + "=" * 80)
    print("🚀 DISPARADOR DE REUNIÃO — Head Financeiro × Operador Autônomo")
    print("=" * 80)
    print(f"\n📅 Data/Hora: {executor.data_reuniao}")
    print(f"👤 Head: {args.head}")
    print(f"🤖 Operador: {args.operador}")

    if args.contexto:
        print(f"\n📊 Contexto:\n   {args.contexto}")

    print("\n" + "-" * 80)
    print("Iniciando fluxo de reunião...\n")

    # Executar reunião
    try:
        executor.executar_fluxo_completo()
        print("\n✅ Reunião disparada com sucesso!")
        print(f"   Banco: db/reunioes.db")
        print(f"   Contexto registrado: {'Sim' if args.contexto else 'Não'}")

    except Exception as e:
        print(f"\n❌ Erro ao disparar reunião: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
