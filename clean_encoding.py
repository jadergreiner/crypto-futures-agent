#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re

# Ler arquivo com UTF-8
with open('scripts/train_ppo_skeleton.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remover acentos e emojis
replacements = {
    'Configuração:': 'Configuracao PPO:',
    'determinístico': 'deterministico',
    'símbolo': 'simbolo',
    'Símbolo': 'Simbolo',
    'Diretório': 'Diretorio',
    'diretórios': 'diretorios',
    'não': 'nao',
    'Dados': 'Dados',
    'Preparando': 'Preparando',
    'Erro': 'Erro',
    '✅': '[OK]',
    '❌': '[ERROR]',
    'encontrados para': 'encontrados para',
}

for old, new in replacements.items():
    content = content.replace(old, new)

# Escrever de volta em UTF-8
with open('scripts/train_ppo_skeleton.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('[OK] Arquivo limpo - caracteres especiais removidos')
