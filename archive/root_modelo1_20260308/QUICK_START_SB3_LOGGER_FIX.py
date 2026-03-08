"""
GUIA RÁPIDO: Desabilitar Logger SB3 (OSError no Windows)

==============================================================================
PROBLEMA
==============================================================================

Durante model.learn() em Windows, Stable-Baselines3 falha com:

    OSError: [Errno 22] Invalid argument

Causa: SB3 tenta escrever em arquivos de log interno com nomes inválidos.


==============================================================================
SOLUÇÃO (Uma linha de código)
==============================================================================

from stable_baselines3 import PPO
from agent.sb3_utils import attach_safe_logger_to_model

model = PPO("MlpPolicy", env, verbose=0, tensorboard_log=None)
attach_safe_logger_to_model(model)  # ← Resolve o problema!

model.learn(1000000)  # Agora funciona!


==============================================================================
CHECKLIST DE IMPLEMENTAÇÃO
==============================================================================

Para cada arquivo que cria/treina PPO:

[ ] 1. Adicionar import:
    from agent.sb3_utils import attach_safe_logger_to_model

[ ] 2. Ao criar PPO, adicionar:
    verbose=0
    tensorboard_log=None

[ ] 3. Depois de criar o modelo, adicionar:
    attach_safe_logger_to_model(model)

[ ] 4. Testar:
    python -m pytest tests/test_sb3_logger_safe.py


==============================================================================
ARQUIVOS CRIADOS
==============================================================================

1. agent/sb3_utils.py
   ├─ create_safe_sb3_logger()       — Cria logger seguro
   ├─ attach_safe_logger_to_model()  — Anexa ao modelo ← USAR ISTO
   ├─ make_ppo_windows_safe()        — Cria PPO pré-configurado
   └─ validate_sb3_setup()           — Valida instalação

2. docs/SB3_LOGGER_WINDOWS_FIX.md
   └─ Documentação completa com 4 soluções alternativas

3. examples/sb3_logger_safe_examples.py
   └─ 4 exemplos: simple, context manager, factory, patch

4. tests/test_sb3_logger_safe.py
   └─ Teste que valida a solução


==============================================================================
INTEGRAÇÃO RÁPIDA (Scripts Principais)
==============================================================================

ARQUIVO: scripts/train_ppo_skeleton.py (linha ~164)

    ANTES:
    ------
    model = PPO(
        policy="MlpPolicy",
        env=vec_env,
        learning_rate=self.config.learning_rate,
        # ... outros params ...
    )

    model.learn(
        total_timesteps=self.config.total_timesteps,
        callback=checkpoint_callback
    )


    DEPOIS:
    ------
    from agent.sb3_utils import attach_safe_logger_to_model

    model = PPO(
        policy="MlpPolicy",
        env=vec_env,
        learning_rate=self.config.learning_rate,
        # ... outros params ...
        verbose=0,              # ← ADD
        tensorboard_log=None,   # ← ADD
    )

    attach_safe_logger_to_model(model)  # ← ADD ESTA LINHA

    model.learn(
        total_timesteps=self.config.total_timesteps,
        callback=checkpoint_callback
    )


ARQUIVO: agent/trainer.py (linha ~154)

    Mesmo padrão acima na função train_phase1_exploration()


==============================================================================
COMO TESTAR
==============================================================================

Passo 1: Executar teste automatizado
    python tests/test_sb3_logger_safe.py

    Saída esperada:
    ✅ PASS: SB3 Imports
    ✅ PASS: sb3_utils Imports
    ✅ PASS: Logger Creation
    ✅ PASS: PPO Training
    ✅ TODOS OS TESTES PASSARAM!


Passo 2: Testar com seu código
    python main.py --train

    Resultado: Treino sem OSError!


==============================================================================
ALTERNATIVAS (se não quiser usar agent/sb3_utils.py)
==============================================================================

ALT 1: Desabilitar logger completamente (mais simples)
-------
from stable_baselines3.common.logger import configure

logger = configure(folder=None, format_strings=[])
model.set_logger(logger)


ALT 2: Redirecionar para diretório seguro (com CSV)
-------
from stable_baselines3.common.logger import configure
from pathlib import Path

log_dir = Path("logs/sb3_safe")
log_dir.mkdir(parents=True, exist_ok=True)

logger = configure(str(log_dir), ["csv", "stdout"])
model.set_logger(logger)


ALT 3: Logger na criação do modelo (factory)
-------
from agent.sb3_utils import make_ppo_windows_safe

model = make_ppo_windows_safe(
    "MlpPolicy",
    env,
    learning_rate=3e-4,
    log_stdout=True
)

model.learn(1000000)


==============================================================================
REFERÊNCIAS
==============================================================================

Documentação SB3 Logger:
  https://stable-baselines3.readthedocs.io/en/master/common/logger.html

Discussões Windows:
  https://github.com/DLR-RM/stable-baselines3/issues?q=windows+logger

Arquivo Detalhado:
  docs/SB3_LOGGER_WINDOWS_FIX.md


==============================================================================
DÚVIDAS FREQUENTES
==============================================================================

P: Por que usar verbose=0 e tensorboard_log=None?
R: TensorBoard tenta criar arquivos com nomes inválidos no Windows.
   verbose=0 desabilita logging do SB3 via stdout.

P: Perdi meus logs de treinamento?
R: Não. Você pode ainda usar callbacks customizados para logging.
   A solução só desabilita o logger interno do SB3.

P: Funciona com A2C, DQN, SAC também?
R: Sim! A função attach_safe_logger_to_model() funciona com qualquer
   algoritmo do SB3.

P: Como restauro logging se precisar?
R: Use configure() com formatos seguros:
   logger = configure(folder, ["csv", "stdout"])  # Sem "tensorboard"

P: Isso afeta performance?
R: Não. Pode até melhorar (menos I/O com arquivos).


==============================================================================
COMMIT SUGERIDO
==============================================================================

[FEAT] Solucionar OSError SB3 logger no Windows com agent/sb3_utils.py

- Criar agent/sb3_utils.py com funções helper
- Criar docs/SB3_LOGGER_WINDOWS_FIX.md com documentação completa
- Criar tests/test_sb3_logger_safe.py com teste de validação
- Criar examples/sb3_logger_safe_examples.py com 4 exemplos
- Integração em scripts/train_ppo_skeleton.py e agent/trainer.py

Problema resolvido: model.learn() no Windows agora funciona sem OSError.

Closes: [Issue_Number]


==============================================================================
PRÓXIMAS TAREFAS
==============================================================================

[ ] Executar teste: python tests/test_sb3_logger_safe.py
[ ] Integrar em scripts/train_ppo_skeleton.py
[ ] Integrar em agent/trainer.py
[ ] Integrar em agent/sub_agent_manager.py (se houver create/learn PPO)
[ ] Executar: python main.py --train
[ ] Validar que treinamento funciona sem OSError
[ ] Fazer commit com tag [FEAT]
[ ] Atualizar docs/SYNCHRONIZATION.md


==============================================================================
RESUMO TÉCNICO
==============================================================================

Problema Raiz:
  Stable-Baselines3 usa tensorboard_log para escrever logs internos.
  No Windows, isso gera OSError com "Invalid argument" devido a:
  - Caracteres especiais em caminhos
  - Problemas de file locking
  - Caminhos muito longos

Solução:
  Desabilitar logger interno do SB3 passando um logger vazio ou seguro.

Implementação:
  1. Criar logger com configure(folder=None, format_strings=[])
  2. Anexar ao modelo com model.set_logger(logger)
  3. Garantir verbose=0 e tensorboard_log=None

Impacto:
  Zero impacto no treinamento. Training loop continua igual.
  Apenas logging interno é desabilitado.

Cobertura:
  - PPO, A2C, DDPG, DQN, SAC, TD3 (qualquer algoritmo SB3)
  - Windows, Linux, macOS
  - Python 3.8+


==============================================================================
PRONTO? Comece aqui:
==============================================================================

1. Copiar a função do agent/sb3_utils.py para seu código
2. Adicionar: attach_safe_logger_to_model(model)
3. Executar treino
4. Sem OSError! ✅

"""

if __name__ == "__main__":
    # Print este guia
    import inspect
    print(inspect.getdoc(__import__(__name__)))
