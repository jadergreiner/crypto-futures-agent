#!/usr/bin/env python3
"""Verificar resultado do bootstrap training."""

import json
from pathlib import Path

# 1. Verificar learning_state
state_file = Path('results/model2/learning_state.json')
with open(state_file) as f:
    state = json.load(f)
    
print('='*60)
print('BOOTSTRAP TRAINING - RESULTADO')
print('='*60)
print(f'Treinado em: {state.get("bootstrap_training_at", "N/A")}')
print(f'Episodios usados: {state.get("bootstrap_episodes_count", 0)}')
print(f'Timesteps: {state.get("bootstrap_timesteps", 0):,}')
print(f'Episodes acumulados reset para: {state.get("episodes_accumulated", 0)}/100')

# 2. Verificar checkpoint existe
checkpoint_path = Path('checkpoints/ppo_training/ppo_model.zip')
if checkpoint_path.exists():
    size_mb = checkpoint_path.stat().st_size / 1024 / 1024
    print(f'\n[OK] Checkpoint encontrado: {checkpoint_path}')
    print(f'  Tamanho: {size_mb:.2f} MB')
else:
    print(f'\n[ERROR] Checkpoint nao encontrado: {checkpoint_path}')

# 3. Proximas acoes
print(f'\n' + '='*60)
print('PROXIMAS ACOES')
print('='*60)
print('1. Modelo RL retreinado com 1000 episodios (15k timesteps)')
print('2. Proximo sinal OPEN_LONG esperado em ~2 minutos')
print('3. Modelo deve ter confianca > 65% (vs 55% anterior)')
print('4. Se confianca > 65%: Execution vai FILL (sucesso!)')
print('5. Se ainda divergencia: repetir bootstrap com mais episodios')
