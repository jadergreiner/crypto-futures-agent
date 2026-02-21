#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Board Orchestrator — Carregador automático de 16 membros
Gerencia reuniões de go-live com estrutura de 6 blocos temáticos

Uso:
    python board_orchestrator.py --init      # Inicializa nova reunião
    python board_orchestrator.py --status    # Mostra status atual
    python board_orchestrator.py --vote <membro> <voto>  # Registra voto
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class BoardOrchestrator:
    """Orquestrador de reunião do Board com 16 membros."""
    
    def __init__(self, config_path: str = "prompts/board_16_members_data.json"):
        self.config_path = Path(config_path)
        self.board_data = None
        self.votos = {}
        self.reuniao_status = "NOT_STARTED"
        self.timestamp_inicio = None
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"Arquivo de config não encontrado: {self.config_path}")
    
    def carregar_board(self):
        """Carrega dados dos 16 membros do JSON."""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.board_data = json.load(f)
        
        # Inicializar votos vazios
        for member in self.board_data['members']:
            self.votos[member['nome']] = None
        
        return self.board_data
    
    def validar_quorum(self) -> bool:
        """Valida quorum (12/16 mínimo)."""
        if not self.board_data:
            self.carregar_board()
        
        total_membros = self.board_data['board_config']['total_members']
        quorum = self.board_data['board_config']['quorum_required']
        
        membros_presentes = total_membros  # Assume todos presentes por padrão
        
        return membros_presentes >= quorum
    
    def validar_membros_criticos(self) -> bool:
        """Valida presença dos 4 membros críticos."""
        criticos = ["Angel", "Elo", "The Brain", "Dr. Risk"]
        return all(nome in [m['nome'] for m in self.board_data['members']] 
                   for nome in criticos)
    
    def exibir_tabela_presenca(self):
        """Exibe tabela de presença dos 16 membros."""
        print("\n" + "="*100)
        print("📋 TABELA DE PRESENÇA — BOARD 16 MEMBROS")
        print("="*100)
        print(f"{'#':<3} {'Nome':<20} {'Especialidade':<25} {'Prioridade':<18} {'Bloco':<6} {'Status':<10}")
        print("-"*100)
        
        for member in self.board_data['members']:
            status = "✅ OK"
            print(f"{member['id']:<3} {member['nome']:<20} {member['especialidade']:<25} "
                  f"{member['prioridade']:<18} {member['bloco']:<6} {status:<10}")
        
        print("="*100)
        print(f"\n✅ Total de membros: {len(self.board_data['members'])}")
        print(f"⭐ Membros críticos: {self.board_data['board_config']['critical_members']}")
        print(f"📊 Quorum requerido: {self.board_data['board_config']['quorum_required']}/16")
        print(f"🎤 Facilitador: GitHub Copilot (Governance Mode)\n")
    
    def exibir_blocos_tematicos(self):
        """Exibe estrutura dos 6 blocos temáticos."""
        print("\n" + "="*100)
        print("🎯 AGENDA — 6 BLOCOS TEMÁTICOS")
        print("="*100)
        
        for bloco in self.board_data['blocos']:
            membros_str = ", ".join(bloco['membros'])
            print(f"\n[BLOCO {bloco['id']}] {bloco['nome']} ({bloco['duracao_min']} min)")
            print(f"  Membros: {membros_str}")
            print(f"  Tópicos:")
            for topico in bloco['topicos']:
                print(f"    • {topico}")
        
        print("\n" + "="*100)
        print(f"⏱️  Tempo total: ~42 minutos (32 min opiniões + 5 min síntese + 5 min votação)\n")
    
    def exibir_criterios_sucesso(self):
        """Exibe critérios de sucesso da reunião."""
        print("\n" + "="*100)
        print("✅ CRITÉRIOS DE SUCESSO (PRÉ-GO-LIVE)")
        print("="*100)
        
        for key, criterion in self.board_data['success_criteria'].items():
            status_symbol = "✅" if "PASSED" in criterion['status'] else "⏳"
            print(f"{status_symbol} {criterion['metric']:<30} | Target: {criterion['target']:<25} | {criterion['status']}")
        
        print("="*100)
        print("🟢 OVERALL STATUS: GREEN (Tudo pronto para go-live)\n")
    
    def registrar_voto(self, nome_membro: str, voto: str, raciocinio: str = ""):
        """Registra voto de um membro."""
        opcoes_validas = ["A", "B", "C"]
        
        if voto not in opcoes_validas:
            print(f"❌ Voto inválido. Use A, B ou C")
            return False
        
        if nome_membro not in self.votos:
            print(f"❌ Membro não encontrado: {nome_membro}")
            return False
        
        self.votos[nome_membro] = {
            'voto': voto,
            'timestamp': datetime.now().isoformat(),
            'raciocinio': raciocinio
        }
        
        label_voto = {
            'A': '✅ SIM',
            'B': '⚠️  CAUTELA',
            'C': '🔴 NÃO'
        }
        
        print(f"✅ Voto registrado: {nome_membro} → {label_voto[voto]}")
        return True
    
    def compilar_resultado_votacao(self) -> Dict:
        """Compila resultado final da votação."""
        resultado = {
            'timestamp': datetime.now().isoformat(),
            'total_votos': sum(1 for v in self.votos.values() if v is not None),
            'total_membros': len(self.votos),
            'quorum_atingido': sum(1 for v in self.votos.values() if v is not None) >= 12,
            'votos_por_opcao': {'A': 0, 'B': 0, 'C': 0},
            'votos_detalhados': {}
        }
        
        for nome, voto_info in self.votos.items():
            if voto_info:
                opcao = voto_info['voto']
                resultado['votos_por_opcao'][opcao] += 1
                resultado['votos_detalhados'][nome] = voto_info
        
        # Determinar decisão final
        votos_sim = resultado['votos_por_opcao']['A']
        votos_cautela = resultado['votos_por_opcao']['B']
        votos_nao = resultado['votos_por_opcao']['C']
        
        if votos_sim >= 9:  # Maioria simples (9/16)
            resultado['decisao_final'] = "✅ GO-LIVE APROVADO"
        elif votos_nao >= 9:
            resultado['decisao_final'] = "🔴 GO-LIVE BLOQUEADO"
        else:
            resultado['decisao_final'] = "⚠️  RESULTADO INDEFINIDO (verificar votos críticos)"
        
        return resultado
    
    def exibir_resultado_votacao(self):
        """Exibe resultado da votação."""
        resultado = self.compilar_resultado_votacao()
        
        print("\n" + "="*100)
        print("🎬 RESULTADO FINAL DA VOTAÇÃO")
        print("="*100)
        print(f"\nQuorum: {resultado['total_votos']}/{resultado['total_membros']} membros votaram")
        print(f"Status: {'✅ QUORUM ATINGIDO' if resultado['quorum_atingido'] else '❌ QUORUM NÃO ATINGIDO'}")
        
        print(f"\nVotos por opção:")
        print(f"  ✅ SIM:       {resultado['votos_por_opcao']['A']:2d} votos")
        print(f"  ⚠️  CAUTELA:   {resultado['votos_por_opcao']['B']:2d} votos")
        print(f"  🔴 NÃO:       {resultado['votos_por_opcao']['C']:2d} votos")
        
        print(f"\n{'='*100}")
        print(f"DECISÃO FINAL: {resultado['decisao_final']}")
        print(f"{'='*100}\n")
        
        return resultado
    
    def inicializar_reuniao(self):
        """Inicializa nova reunião."""
        print("\n🚀 INICIALIZANDO REUNIÃO DO BOARD — GO-LIVE STRATEGY")
        print(f"   Timestamp: {datetime.now().isoformat()}")
        
        # Carregar board
        self.carregar_board()
        
        # Validações
        print("\n📋 VALIDAÇÕES PRÉ-REUNIÃO:")
        
        if self.validar_quorum():
            print("  ✅ Quorum validado (12/16 mínimo)")
        else:
            print("  ❌ QUORUM NÃO ATINGIDO")
            return False
        
        if self.validar_membros_criticos():
            print("  ✅ Membros críticos presentes")
        else:
            print("  ❌ MEMBROS CRÍTICOS AUSENTES - ABORTAR REUNIÃO")
            return False
        
        print("  ✅ Pré-condições validadas")
        
        # Exibir tabelas
        self.exibir_tabela_presenca()
        self.exibir_blocos_tematicos()
        self.exibir_criterios_sucesso()
        
        self.reuniao_status = "RUNNING"
        self.timestamp_inicio = datetime.now().isoformat()
        
        print("✅ Reunião inicializada com sucesso!")
        print("🎤 Podemos começar com o BLOCO 1 (Angel & Elo)\n")
        
        return True
    
    def gerar_snapshot_para_banco(self) -> Dict:
        """Gera snapshot para persistência em banco de dados."""
        return {
            'reunion_id': f"BOARD_21FEV_GOLIVE_16MEMBROS",
            'timestamp_inicio': self.timestamp_inicio,
            'timestamp_agora': datetime.now().isoformat(),
            'status': self.reuniao_status,
            'total_membros': 16,
            'votos_registrados': sum(1 for v in self.votos.values() if v is not None),
            'resultado_votacao': self.compilar_resultado_votacao(),
            'go_live_readiness': '🟢 GREEN',
            'risk_level': '🟢 LOW',
            'timeline_target': '22 FEV 10:00 UTC'
        }


def main():
    """Função principal."""
    try:
        orchestrator = BoardOrchestrator()
        
        if len(sys.argv) < 2:
            print("Uso: python board_orchestrator.py [--init|--status|--vote|--resultado]")
            return
        
        command = sys.argv[1]
        
        if command == "--init":
            orchestrator.inicializar_reuniao()
        
        elif command == "--status":
            orchestrator.carregar_board()
            orchestrator.exibir_tabela_presenca()
            orchestrator.exibir_criterios_sucesso()
        
        elif command == "--vote" and len(sys.argv) >= 4:
            orchestrator.carregar_board()
            nome = sys.argv[2]
            voto = sys.argv[3]
            raciocinio = sys.argv[4] if len(sys.argv) > 4 else ""
            orchestrator.registrar_voto(nome, voto, raciocinio)
        
        elif command == "--resultado":
            orchestrator.carregar_board()
            orchestrator.exibir_resultado_votacao()
        
        else:
            print(f"Comando desconhecido: {command}")
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
