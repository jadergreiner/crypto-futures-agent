#!/usr/bin/env python3
"""
[SYNC] Integração: Scripts de Reunião de Board com 16 Membros
Atualiza disparador_reuniao.py para usar novo orchestrator

Mudanças:
1. Importa BoardMeetingOrchestrator
2. Detecta tipo de decisão (ML, Posições, Escalabilidade)
3. Executa ciclo estruturado de opiniões
4. Registra em banco de dados
5. Exporta relatório markdown [SYNC]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.board_meeting_orchestrator import BoardMeetingOrchestrator
from scripts.condutor_board_meeting import ConductorBoardMeeting


def patch_disparador_reuniao():
    """
    Patch para disparador_reuniao.py
    Adiciona suporte a ciclo estruturado de opiniões
    """

    arquivo = Path(__file__).parent / "disparador_reuniao.py"

    conteudo = arquivo.read_text()

    # Verificar se já foi patchado
    if "BoardMeetingOrchestrator" in conteudo:
        print("✅ disparador_reuniao.py já foi patchado")
        return

    # Adicionar imports
    import_adicional = """
from scripts.board_meeting_orchestrator import BoardMeetingOrchestrator
from scripts.condutor_board_meeting import ConductorBoardMeeting
"""

    # Adicionar método ao ExecutorReuniao
    metodo_bonus = '''

    def executar_com_ciclo_opiniones(self, tipo_decisao: str = "ML_TRAINING_STRATEGY"):
        """
        Executa reunião com ciclo estruturado de opiniões (16 membros)

        Args:
            tipo_decisao: Tipo de decisão (ML_TRAINING_STRATEGY, POSIOES_UNDERWATER, ESCALABILIDADE)
        """
        condutor = ConductorBoardMeeting()
        condutor.executar_reuniao_completa(tipo_decisao)
'''

    print(f"✅ Patch disponível para disparador_reuniao.py")
    print(f"   Adicionar imports e método executar_com_ciclo_opiniones()")


if __name__ == "__main__":
    patch_disparador_reuniao()

    # Demonstração
    print("\n" + "=" * 80)
    print("DEMO: Executando reunião com ciclo de opiniões")
    print("=" * 80 + "\n")

    condutor = ConductorBoardMeeting()
    condutor.executar_reuniao_completa("ML_TRAINING_STRATEGY")
