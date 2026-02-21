#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resumo consolidado de ciclo de monitoramento (5 minutos).

Use: python resumo_ciclo.py

Mostra status RESUMIDO de todos os símbolos:
- Cotação atual
- Indicadores técnicos (SMC confluence, direção, regime)
- Se há sinal gerado
- Posição aberta (se houver) e seu PnL
- Status de treinamento (win rate)

A cada execução, consulta o banco de dados SQLite
e exibe a última foto de mercado.
"""

import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from monitoring.cycle_summary import print_cycle_summary
from config.symbols import ALL_SYMBOLS


def main():
    """Executa resumo consolidado do ciclo."""
    print_cycle_summary(ALL_SYMBOLS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print(f"\nErro ao exibir consolidado: {e}")
        sys.exit(1)
