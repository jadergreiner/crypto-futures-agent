#!/usr/bin/env python3
"""
Script para corrigir encoding de commits históricos
Converte UTF-8 multi-byte para ASCII puro conforme COMMIT_MESSAGE_POLICY.md
"""

import subprocess
import json
import sys
from pathlib import Path

def run_cmd(cmd, shell=True):
    """Executa comando e retorna output"""
    result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def get_commits_with_encoding_issues():
    """Retorna lista de commits com problemas de encoding"""
    cmd = 'git log --format="%h|%s" -20'
    output, _, _ = run_cmd(cmd)

    commits = []
    for line in output.split('\n'):
        if line:
            parts = line.split('|')
            if len(parts) == 2:
                hash_short = parts[0]
                message = parts[1]

                # Verificar se tem caracteres não-ASCII
                has_non_ascii = any(ord(c) > 127 for c in message)

                if has_non_ascii:
                    commits.append({
                        'hash': hash_short,
                        'message': message,
                        'fixed': False
                    })

    return commits

def convert_to_ascii(text):
    """Converte texto com acentos para ASCII puro"""
    conversions = {
        'ã': 'a', 'Ã': 'A',
        'á': 'a', 'Á': 'A',
        'à': 'a', 'À': 'A',
        'â': 'a', 'Â': 'A',
        'ä': 'a', 'Ä': 'A',
        'é': 'e', 'É': 'E',
        'è': 'e', 'È': 'E',
        'ê': 'e', 'Ê': 'E',
        'ë': 'e', 'Ë': 'E',
        'í': 'i', 'Í': 'I',
        'ì': 'i', 'Ì': 'I',
        'î': 'i', 'Î': 'I',
        'ï': 'i', 'Ï': 'I',
        'ó': 'o', 'Ó': 'O',
        'ò': 'o', 'Ò': 'O',
        'ô': 'o', 'Ô': 'O',
        'ö': 'o', 'Ö': 'O',
        'õ': 'o', 'Õ': 'O',
        'ú': 'u', 'Ú': 'U',
        'ù': 'u', 'Ù': 'U',
        'û': 'u', 'Û': 'U',
        'ü': 'u', 'Ü': 'U',
        'ç': 'c', 'Ç': 'C',
        'ñ': 'n', 'Ñ': 'N',
    }

    # Remove caracteres de corrupsão UTF-8
    # ├º├ú → a, ÔÇö → -, Ô£à → etc
    result = text

    # Remove caracteres corrompidos conhecidos
    corrupted = ['├', '½', '│', 'Ô', 'ç', 'Â', 'Ø', 'é', 'ê', 'ü']
    for char in corrupted:
        if ord(char) > 127:
            result = result.replace(char, '')

    # Faz conversão de acentos
    for accent, replacement in conversions.items():
        result = result.replace(accent, replacement)

    # Remove caracteres inválidos que sobraram
    result = ''.join(c for c in result if ord(c) < 128 or c in ' ')

    # Limpa espaços múltiplos
    result = ' '.join(result.split())

    return result

def print_commits_to_fix(commits):
    """Exibe commits que serão corrigidos"""
    print("\n" + "="*80)
    print("COMMITS COM PROBLEMA DE ENCODING IDENTIFICADOS")
    print("="*80)

    for i, commit in enumerate(commits, 1):
        print(f"\n{i}. {commit['hash']}")
        print(f"   Original: {commit['message']}")

        # Ao invés de corrigir automaticamente, vou usar um dicionário manual
        fixed = fix_commit_message(commit['message'], commit['hash'])
        print(f"   Corrigido: {fixed}")
        commit['fixed_message'] = fixed

def fix_commit_message(original, commit_hash):
    """Retorna mensagem corrigida para cada commit específico"""

    # Mapeamento manual de cada commit problemático
    fixes = {
        '81aa257': '[PHASE2] Script recuperacao dados conta real',
        '6e04cd4': '[GOLIVE] Canary Deployment Phase 1 iniciado',
        '9b5166c': '[BOARD] Votacao Final GO-LIVE aprovada unanime',
        'b715f9a': '[DOCS] Integration Summary Board 16 membros',
        '0dcee01': '[INFRA] Board Orchestrator 16 membros setup',
        '1f2b75d': '[BOARD] Reuniao 16 membros Go-Live Auth',
        '09d2ecf': '[CLOSE] Reuniao Board 21 FEV encerrada',
        '813e5fd': '[VALIDATE] TASK-003 Alpha SMC Validation OK',
        'fd1a7f8': '[PLAN] TASK-004 Preparacao go-live canary',
        'a229fab': '[TEST] TASK-002 QA Testing 40/40 testes ok',
        '7849056': '[FEAT] TASK-001 Heuristicas implementadas',
    }

    # Se temos mapeamento específico, use
    if commit_hash in fixes:
        return fixes[commit_hash]

    # Caso contrário, tente conversão automática
    return convert_to_ascii(original)

def main():
    print("FERRAMENTA DE CORRECAO DE ENCODING - COMMITS")
    print("="*80)

    # Obter commits problemáticos
    commits = get_commits_with_encoding_issues()

    if not commits:
        print("\n✓ Nenhum commit com problema de encoding encontrado!")
        return

    print(f"\nEncontrados {len(commits)} commits com problemas de encoding.")

    # Exibir commits
    print_commits_to_fix(commits)

    print("\n" + "="*80)
    print("PARA EXECUTAR A CORRECAO, USE:")
    print('  git rebase -i HEAD~{} (abra o editor e marque "edit" nos linhas)'.format(len(commits) + 1))
    print("  Ou execute o comando interativo abaixo:")
    print("="*80)

    # Mostrar passos
    print("\nEtapas para correção manual:")
    for i, commit in enumerate(commits, 1):
        print(f"\n{i}. git rebase -i {commit['hash']}^")
        print(f"   Altere a mensagem para: {commit.get('fixed_message', '(auto)')}")
        print(f"   git commit --amend -m \"{commit.get('fixed_message', commit['message'])}\"")
        print(f"   git rebase --continue")

if __name__ == '__main__':
    main()
