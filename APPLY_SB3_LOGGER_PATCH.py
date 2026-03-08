"""
PATCH: Como aplicar a solução SB3 Logger nos arquivos existentes

Use este documento para integrar a solução nos arquivos do projeto.
"""

# ===========================================================================
# ARQUIVO 1: scripts/train_ppo_skeleton.py
# ===========================================================================

PATCH_TRAIN_PPO_SKELETON = """
ARQUIVO: scripts/train_ppo_skeleton.py
LINHA: ~30 (section de imports)

ADICIONE:
---------

from agent.sb3_utils import attach_safe_logger_to_model


---

ARQUIVO: scripts/train_ppo_skeleton.py
LINHA: ~160-190 (função train())

MODIFIQUE:

    ANTES:
    ------
    model = PPO(
        policy="MlpPolicy",
        env=vec_env,
        learning_rate=self.config.learning_rate,
        n_steps=self.config.n_steps,
        batch_size=self.config.batch_size,
        n_epochs=self.config.n_epochs,
        gamma=self.config.gamma,
        gae_lambda=self.config.gae_lambda,
        clip_range=self.config.clip_range,
        ent_coef=self.config.ent_coef,
        vf_coef=self.config.vf_coef,
        max_grad_norm=self.config.max_grad_norm,
        device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'),
        verbose=self.config.verbose
    )


    DEPOIS:
    ------
    model = PPO(
        policy="MlpPolicy",
        env=vec_env,
        learning_rate=self.config.learning_rate,
        n_steps=self.config.n_steps,
        batch_size=self.config.batch_size,
        n_epochs=self.config.n_epochs,
        gamma=self.config.gamma,
        gae_lambda=self.config.gae_lambda,
        clip_range=self.config.clip_range,
        ent_coef=self.config.ent_coef,
        vf_coef=self.config.vf_coef,
        max_grad_norm=self.config.max_grad_norm,
        device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'),
        verbose=0,  # ← ALTERAR: Desabilitar verbose
        tensorboard_log=None,  # ← ADICIONAR: Desabilitar TensorBoard
    )

    # ← ADICIONAR: Logger seguro para Windows
    attach_safe_logger_to_model(model, use_stdout=False)


    ANTES:
    ------
    # 4. Treinar
    logger.info(f"Iniciando treinamento para {symbol}...")

    model.learn(
        total_timesteps=self.config.total_timesteps,
        callback=checkpoint_callback
    )


    DEPOIS:
    ------
    # 4. Treinar
    logger.info(f"Iniciando treinamento para {symbol}...")
    logger.info("Logger seguro anexado (sem OSError no Windows)")

    model.learn(
        total_timesteps=self.config.total_timesteps,
        callback=checkpoint_callback,
        progress_bar=False  # ← OPCIONAL: progress bar customizado se desejado
    )

"""


# ===========================================================================
# ARQUIVO 2: agent/trainer.py
# ===========================================================================

PATCH_AGENT_TRAINER = """
ARQUIVO: agent/trainer.py
LINHA: ~1-20 (section de imports)

ADICIONE:
---------

from agent.sb3_utils import attach_safe_logger_to_model


---

ARQUIVO: agent/trainer.py
LINHA: ~144-172 (função train_phase1_exploration())

MODIFIQUE:

    ANTES:
    ------
    # Criar modelo PPO com hiperparâmetros de config
    self.model = PPO(
        "MlpPolicy",
        vec_env,
        learning_rate=self.config.learning_rate,
        n_steps=self.config.n_steps,
        batch_size=self.config.batch_size,
        n_epochs=self.config.n_epochs,
        gamma=self.config.gamma,
        gae_lambda=self.config.gae_lambda,
        clip_range=self.config.clip_range,
        ent_coef=self.config.ent_coef,
        vf_coef=self.config.vf_coef,
        max_grad_norm=self.config.max_grad_norm,
        normalize_advantage=True,
        verbose=self.config.verbose,
        tensorboard_log=tb_log
    )


    DEPOIS:
    ------
    # Criar modelo PPO com hiperparâmetros de config
    self.model = PPO(
        "MlpPolicy",
        vec_env,
        learning_rate=self.config.learning_rate,
        n_steps=self.config.n_steps,
        batch_size=self.config.batch_size,
        n_epochs=self.config.n_epochs,
        gamma=self.config.gamma,
        gae_lambda=self.config.gae_lambda,
        clip_range=self.config.clip_range,
        ent_coef=self.config.ent_coef,
        vf_coef=self.config.vf_coef,
        max_grad_norm=self.config.max_grad_norm,
        normalize_advantage=True,
        verbose=0,  # ← ALTERAR: Desabilitar verbose
        tensorboard_log=None,  # ← ALTERAR: Sempre None no Windows
    )

    # ← ADICIONAR: Logger seguro para Windows
    attach_safe_logger_to_model(self.model, use_stdout=False)


    ANTES:
    ------
    # Callback
    callback = TrainingCallback(log_interval=1000)

    # Treinar
    logger.info(f"Starting Phase 1 training: {total_timesteps} timesteps")
    logger.info(f"Config - lr={self.config.learning_rate}, nt={self.config.n_epochs}, "
               f"ent_coef={self.config.ent_coef}")
    self.model.learn(
        total_timesteps=total_timesteps,
        callback=callback,
        progress_bar=False
    )


    DEPOIS:
    ------
    # Callback
    callback = TrainingCallback(log_interval=1000)

    # Treinar
    logger.info(f"Starting Phase 1 training: {total_timesteps} timesteps")
    logger.info(f"Config - lr={self.config.learning_rate}, nt={self.config.n_epochs}, "
               f"ent_coef={self.config.ent_coef}")
    logger.info("Logger seguro anexado (sem OSError no Windows)")  # ← ADICIONAR

    self.model.learn(
        total_timesteps=total_timesteps,
        callback=callback,
        progress_bar=False
    )

"""


# ===========================================================================
# ARQUIVO 3: agent/sub_agent_manager.py (se houver treinamento)
# ===========================================================================

PATCH_SUB_AGENT_MANAGER = """
ARQUIVO: agent/sub_agent_manager.py
LINHA: ~30 (section de imports)

Se houver model.learn() neste arquivo:

ADICIONE:
---------

from agent.sb3_utils import attach_safe_logger_to_model


DEPOIS:
------

Onde há:
    model = PPO(...)
    model.learn(...)

ADICIONE:
    attach_safe_logger_to_model(model)

Antes de:
    model.learn(...)

"""


# ===========================================================================
# RESUMO DAS MUDANÇAS
# ===========================================================================

SUMMARY = """
RESUMO DAS MUDANÇAS NECESSÁRIAS
================================

1. Importar helper (em 3 arquivos):
   from agent.sb3_utils import attach_safe_logger_to_model

2. Modificar criação de PPO (adicionar 2 parâmetros):
   verbose=0,
   tensorboard_log=None,

3. Adicionar 1 linha após criar PPO:
   attach_safe_logger_to_model(model)

TOTAL: 3 linhas em 3 arquivos principais


ARQUIVOS A MODIFICAR:
- scripts/train_ppo_skeleton.py      (linha ~164)
- agent/trainer.py                    (linha ~154)
- agent/sub_agent_manager.py          (se houver model.learn())


TEMPO ESTIMADO: 5 minutos


VALIDAÇÃO:
- python tests/test_sb3_logger_safe.py
- python main.py --train

"""


# ===========================================================================
# COMO APLICAR PATCH AUTOMATICAMENTE
# ===========================================================================

AUTOMATED_PATCH = """
OPÇÃO 1: Aplicar patch manual (recomendado para revisão)
=========================================================

Para cada arquivo:
1. Abrir em VS Code
2. Seguir as instruções de PATCH acima
3. Testar com: pytest tests/test_sb3_logger_safe.py


OPÇÃO 2: Script Python automático
=================================

python apply_sb3_logger_patch.py

(script fornecido separadamente)


OPÇÃO 3: Git patch
==================

git apply sb3_logger_windows.patch

(arquivo patch fornecido separadamente)

"""


# ===========================================================================
# CHECKLIST
# ===========================================================================

CHECKLIST = """
CHECKLIST DE IMPLEMENTAÇÃO
===========================

[ ] 1. Ler agent/sb3_utils.py para entender a solução
[ ] 2. Verificar se agent/sb3_utils.py está no projeto
[ ] 3. Modificar scripts/train_ppo_skeleton.py
      [ ] Adicionar import
      [ ] Adicionar verbose=0
      [ ] Adicionar tensorboard_log=None
      [ ] Adicionar attach_safe_logger_to_model()

[ ] 4. Modificar agent/trainer.py
      [ ] Adicionar import
      [ ] Adicionar verbose=0
      [ ] Adicionar tensorboard_log=None
      [ ] Adicionar attach_safe_logger_to_model()

[ ] 5. (Opcional) Modificar agent/sub_agent_manager.py
      [ ] Se houver model.learn()

[ ] 6. Executar testes
      [ ] python tests/test_sb3_logger_safe.py
      [ ] Resultado esperado: ✅ PASS todos os testes

[ ] 7. Testar treinamento real
      [ ] python main.py --train
      [ ] Resultado esperado: Sem OSError

[ ] 8. Fazer commit
      [ ] git add agent/sb3_utils.py
      [ ] git add scripts/train_ppo_skeleton.py
      [ ] git add agent/trainer.py
      [ ] git commit -m "[FEAT] Desabilitar SB3 logger para evitar OSError no Windows"


TEMPO TOTAL: ~20 minutos (leitura + implementação + teste)

"""


# ===========================================================================
# REFERÊNCIA RÁPIDA
# ===========================================================================

QUICK_REFERENCE = """
CÓDIGO PARA COPIAR/COLAR
=========================

IMPORT:
-------
from agent.sb3_utils import attach_safe_logger_to_model


CRIAR MODELO:
-------
model = PPO(
    "MlpPolicy",
    env,
    # ... parâmetros ...
    verbose=0,
    tensorboard_log=None,
)

attach_safe_logger_to_model(model)  # ← ESTA LINHA RESOLVE


TREINAR:
-------
model.learn(total_timesteps=1000000)


PRONTO! SEM OSError!

"""


if __name__ == "__main__":
    import inspect

    print("""
    =========================================================================
    PATCH: Como aplicar a solução SB3 Logger
    =========================================================================
    """)

    print("\n" + "=" * 75)
    print("ARQUIVO 1: scripts/train_ppo_skeleton.py")
    print("=" * 75)
    print(PATCH_TRAIN_PPO_SKELETON)

    print("\n" + "=" * 75)
    print("ARQUIVO 2: agent/trainer.py")
    print("=" * 75)
    print(PATCH_AGENT_TRAINER)

    print("\n" + "=" * 75)
    print("ARQUIVO 3: agent/sub_agent_manager.py")
    print("=" * 75)
    print(PATCH_SUB_AGENT_MANAGER)

    print("\n" + "=" * 75)
    print(SUMMARY)
    print(CHECKLIST)
    print(QUICK_REFERENCE)
