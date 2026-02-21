# Training PPO Phase 4 - Instruções

Bem-vindo ao diretório de gerenciamento de checkpoints PPO Phase 4!

## Estrutura

```
checkpoints/ppo_training/
├── model_*.pkl        # Checkpoints do modelo PPO
├── vecnorm_*.pkl      # Normalizadores de vetores
└── *.json             # Metadados de treinamento
```

## Como usar

### 1. Iniciar treinamento (dry-run)

```bash
python scripts/start_ppo_training.py --dry-run
```

Valida toda a infraestrutura sem treinar. Use para verificar que tudo está OK antes de começar treinamento real.

### 2. Iniciar treinamento real

```bash
# Com símbolo padrão (OGNUSDT)
python scripts/start_ppo_training.py

# Com símbolo específico
python scripts/start_ppo_training.py --symbol 1000PEPEUSDT

# Com número de timesteps customizado
python scripts/start_ppo_training.py --timesteps 750000
```

### 3. Monitorar progresso

```bash
# Checklist de treinamento
python scripts/check_training_progress.py

# Dashboard em tempo real
python scripts/ppo_training_dashboard.py
```

### 4. Verificar logs

Todos os logs são salvos em `logs/ppo_training/training_YYYYMMDD_HHMMSS.log`

```bash
# Último log
tail -50 logs/ppo_training/training_*.log | tail -50

# Grep por erros
grep ERROR logs/ppo_training/training_*.log
```

## Configuração

A configuração é carregada automaticamente de `config/ppo_config.py`:

- **Learning Rate**: 3e-4 (conservador)
- **Batch Size**: 64
- **N-Steps**: 2048  
- **Total Timesteps**: 500,000 (default, customizável)
- **Phase**: Phase 4 (conservador, pós-Phase 3)

## Safety Checks

Antes de iniciar, o trainer valida:

1. ✅ Configuração PPO (11 hiperparâmetros)
2. ✅ Símbolo válido
3. ✅ Dados disponíveis (parquet)
4. ✅ BacktestEnvironment funcional
5. ✅ ParquetCache funcional
6. ✅ PPOStrategy imports OK
7. ✅ Diretórios de saída OK
8. ✅ Estrutura do agent OK
9. ✅ Extensões OK

Se qualquer validação falhar, o treinamento é bloqueado.

## Troubleshooting

### "No module named 'config'"

```bash
cd c:\repo\crypto-futures-agent
python scripts/start_ppo_training.py --dry-run
```

### "Parquet file not found"

Garantir que dados foram baixados:

```bash
# Verificar dados disponíveis
python -c "
from pathlib import Path
for p in Path('backtest/cache').glob('*_4h.parquet'):
    size = p.stat().st_size / (1024*1024)
    print(f'{p.name}: {size:.2f}MB')
"
```

### Verificar integrity

```bash
python scripts/preflight_validation.py
```

## Deadlines

- **Preparação**: 22 FEV 14:00 UTC ✅
- **Validação Final**: 23 FEV 10:00 UTC
- **Início Treinamento**: 23 FEV 14:00 UTC

## Contato

Se houver problemas, verifique:

1. `logs/ppo_training/training_*.log`
2. `scripts/preflight_validation.py`
3. `docs/SYNCHRONIZATION.md` (histórico de mudanças)

---

**Data**: 21 FEV 2026  
**Version**: 1.0  
**Status**: READY FOR PHASE 4 TRAINING
