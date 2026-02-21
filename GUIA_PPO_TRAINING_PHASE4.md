"""
GUIA PRÁTICO — Como Executar Treinamento Phase 4 (23-27 FEV)
===============================================================

Checklist pré-treinamento, rotina diária e revalidação.
"""

# ============================================================================
# PARTE 1: PRÉ-TREINAMENTO (23 FEV 10:00-14:00 UTC)
# ============================================================================

PRE_TRAINING_CHECKLIST = """
=== 23 FEV, 10:00 UTC: PRÉ-TREINAMENTO CHECKLIST ===

[ ] 1. SWE finalizou integração
    - agent/trainer.py foi atualizado com PPOConfig (config/ppo_config.py)
    - ConvergenceDashboard está importado e funcional
    - Teste rápido: python -c "from config.ppo_config import PPOConfig; print(PPOConfig())"

[ ] 2. Dados de treinamento estão prontos
    - data/ tem H4, H1, D1, sentiment, macro, SMC
    - Cache de OHLCV está atualizado (~700 candles mínimo)
    - Test: python -c "from data.data_loader import DataLoader; print('OK')"

[ ] 3. Environment testado
    - agent/environment.py retorna obs, done, info['trades'], info['capital']
    - Test: pytest tests/test_environment.py -v

[ ] 4. Diretórios criados
    - mkdir -p logs/ppo_training
    - mkdir -p models/ppo_phase4
    - mkdir -p reports/revalidation

[ ] 5. Dependências verificadas
    - pip list | grep stable-baselines3
    - pip list | grep gymnasium
    - pip list | grep numpy

[ ] 6. TensorBoard (opcional)
    - pip install tensorboard (se quer visualizar)
    - ou usar CSV do dashboard

[ ] ✅ PRONTO PARA INICIAR TREINAMENTO
"""

# ============================================================================
# PARTE 2: INICIAR TREINAMENTO (23 FEV 14:00 UTC)
# ============================================================================

START_TRAINING_COMMANDS = """
=== 23 FEV, 14:00 UTC: INICIAR TREINAMENTO ===

# Opção A: Script simples (recomendado)
python scripts/start_ppo_training.py

# Opção B: Manualmente no Python
python
>>> from config.ppo_config import PPOConfig
>>> from agent.trainer import Trainer
>>> from scripts.ppo_training_dashboard import ConvergenceDashboard
>>> from data.data_loader import DataLoader

>>> config = PPOConfig.phase4_conservative()
>>> trainer = Trainer(save_dir="models/ppo_phase4")
>>> dashboard = ConvergenceDashboard(log_dir="logs/ppo_training")
>>> data = DataLoader.load_backtest_data("BTCUSDT")

>>> # Treinar com dashboard
>>> trainer.train_with_dashboard(
...     train_data=data,
...     config=config,
...     dashboard=dashboard,
...     total_timesteps=500_000
... )

# Monitorar em tempo real
tail -f logs/ppo_training/convergence_dashboard.csv
tail -f logs/ppo_training/daily_summary.log
"""

# ============================================================================
# PARTE 3: MONITORAMENTO DIÁRIO (23-27 FEV, 10:00 UTC cada dia)
# ============================================================================

DAILY_CHECKIN_TEMPLATE = """
=== DAILY CHECK-IN TEMPLATE (10:00 UTC) ===

Data: __/__/2026

1. MÉTRICAS ATUAIS (do CSV ou dashboard log)
   - Episodes trained hoje: ___
   - Reward moving average (50 ep): ___
   - Best episode reward: ___
   - Current Sharpe estimate: ___
   - KL divergence (últimas updates): ___

2. SAÚDE DO TREINAMENTO
   - Convergência? (reward aumentando?)  [ ] Sim [ ] Lento [ ] Plateau
   - Nenhum crashe ou erro?              [ ] Sim [ ] Não → PARAR E DEBUG
   - Entropy normal (0.0001-1.5)?        [ ] Sim [ ] Anormalmente baixa [ ] Anormalmente alta
   - Gradient norm < 1.0?                [ ] Sim [ ] Explosão detected

3. ALERTAS GERADOS?
   - KL divergence > 0.05?  [ ] Não [ ] Sim → reduzir learning rate?
   - No improve x 100 ep?   [ ] Não [ ] Sim → preparar parada
   - Sharpe > 0.7?          [ ] Não [ ] Sim → SAVE CHECKPOINT IMMEDIATELY

4. AÇÕES NECESSÁRIAS
   - [ ] Nenhuma (continuar)
   - [ ] Salvar checkpoint
   - [ ] Ajustar hyperparâmetro (LR, entropy)
   - [ ] Parar e investigar

5. ESTIMATIVA DE TEMPO RESTANTE
   - Horas de treinamento completadas: ___
   - Steps completados: _____ / 500k
   - Estimativa de conclusão: __:__ UTC em __/__/2026
"""

# ============================================================================
# PARTE 4: ROTINA DIÁRIA DETALHADA (por dia)
# ============================================================================

DAILY_ROUTINES = {
    "23_FEV": {
        "10:00": "✅ CHECKLIST PRÉ-TREINAMENTO (ver PARTE 1)",
        "14:00": "✅ INICIAR TREINAMENTO (ver PARTE 2)",
        "14:30": "Verificar primeiros logs em logs/ppo_training/",
        "18:00": "Primeiro check-in rápido (episódios começaram?)",
    },
    "24_FEV": {
        "10:00": "📊 DAILY CHECKIN #1 (ver PARTE 3)",
        "target": "Reward deve estar >-50 (mínimo learning)",
        "action": "Se muito ruim (<-100): verificar environment, reward function",
    },
    "25_FEV": {
        "10:00": "📊 DAILY CHECKIN #2",
        "target": "Sharpe estimate > 0.2 (começando a convergir)",
        "note": "Se ainda negativo: normal, modelo explore ainda",
        "action_ok": "Continuar normalmente",
        "action_bad": "Verificar reward clipping, nn architecture",
    },
    "26_FEV": {
        "10:00": "📊 DAILY CHECKIN #3",
        "target": "Modelo começando a consolidar (reward estável ou +)",
        "target_sharpe": "0.3-0.7 (bom sinal de convergência)",
        "action": "Se plateau: considerar parar treinamento cedo",
    },
    "27_FEV": {
        "10:00": "📊 DAILY CHECKIN #4 (último antes revalidação)",
        "target": "Sharpe ≥0.7 esperado (ready for validation)",
        "16:00": "🔬 EXECUTAR REVALIDAÇÃO (ver PARTE 5)",
        "17:00": "📋 GO/NO-GO DECISION",
    },
}

# ============================================================================
# PARTE 5: REVALIDAÇÃO (27 FEV 16:00 UTC)
# ============================================================================

REVALIDATION_STEPS = """
=== 27 FEV, 16:00 UTC: REVALIDAÇÃO COM 6 GATES ===

Step 1: Carregar melhor modelo treinado
    python
    >>> from scripts.revalidate_model.py import RevalidationValidator
    >>> validator = RevalidationValidator()
    >>> model, vec_norm = validator.load_model("best_model")
    
Step 2: Preparar dados de backtest (sem leakage)
    >>> from data.data_loader import DataLoader
    >>> backtest_data = DataLoader.load_validation_set()
    
Step 3: Executar backtest
    >>> trades, equity_curve, stats = validator.run_backtest(
    ...     model=model,
    ...     vec_normalize=vec_norm,
    ...     backtest_data=backtest_data,
    ...     num_episodes=10
    ... )
    
Step 4: Calcular 6 métricas
    >>> metrics = validator.calculate_metrics_from_trades(trades, equity_curve)
    >>> print(metrics)
    
Step 5: Validar contra 6 gates
    >>> result = validator.validate_gates(metrics)
    >>> print(f"Gates passed: {result['gates_passed']}/6")
    >>> print(f"Decision: {result['go_no_go']}")
    
Step 6: Gerar relatório
    >>> report = validator.generate_report(result)
    >>> validator.save_results(result, report)
    
Step 7: Impacto
    >>> print(result['go_no_go'])
    "GO"        → Proceder com 28 FEV deployment
    "PARTIAL"   → CTO review necessário
    "NO-GO"     → Analisar, considerar Option A modificado

Expectativa: 5-6 / 6 gates (vs 2/6 random)
"""

# ============================================================================
# PARTE 6: TROUBLESHOOTING
# ============================================================================

TROUBLESHOOTING = """
=== TROUBLESHOOTING DURANTE TREINAMENTO ===

❌ Problema: "Reward não está aumentando, fica em ~-50"
   → Causa provável: Environment retornando rewards ruins constantemente
   → Ação: Verificar reward.py, conferir se formula está correta
   → Debug: python -c "from agent.environment import CryptoFuturesEnv; env = CryptoFuturesEnv(...); obs, info = env.reset(); print(info)"

❌ Problema: "Model crashes com CUDA error"
   → Ação: Usar CPU em vez de GPU (ou ajustar batch_size)
   → Config: config.ppo_config.PPOConfig() → batch_size = 32 (reduzido)

❌ Problema: "Sharpe muito baixo depois de 5 dias (< 0.3)"
   → Causa: Modelo não convergedido com reward function atual
   → Ação: Considerar Option A (override com heurísticas) + continue training
   → Ou Option B: Aumentar learning_rate ligeiramente (5e-4), continuar

❌ Problema: "KL divergence constantemente > 0.05"
   → Ação: Política está mudando muito por update
   → Fix: Reduzir learning_rate (1e-4), aumentar clip_range (0.3)

❌ Problema: "No improvement por 100+ episódios no meio do treinamento"
   → Normal: Exploração vs exploitation
   → Ação: Aumentar ent_coef temporariamente (0.005)

✅ Sucesso: "Sharpe > 0.7 no lógos"
   → Salvar checkpoint automático (ConvergenceDashboard faz isso)
   → Status = "EXCELLENT" — pronto para revalidação

❓ Dúvida: "Quantos episódios = quantos dias?"
   → ~5k episodes / dia (com GPU parallelism)
   → ~500k total timesteps / 5k = ~100 dias episódios
   → Mas cada episode = 500 steps, então ~2000k / dia steps
   → 500k / 2000k ≈ 0.25 dias = 6 horas CPU
   → Realista: 5-7 dias wall-clock com GPU
"""

if __name__ == "__main__":
    print(PRE_TRAINING_CHECKLIST)
    print("\n")
    print(START_TRAINING_COMMANDS)
    print("\n")
    print(DAILY_CHECKIN_TEMPLATE)
