# Solução: Desabilitar Logger do Stable-Baselines3 no Windows

## Problema

Durante `model.learn()` em Windows, Stable-Baselines3 (SB3) tenta escrever em arquivos de log interno com nomes inválidos, causando:

```
OSError: [Errno 22] Invalid argument
```

Causas possíveis:
- Caracteres inválidos em nomes de arquivo (`:`, `<`, `>`, etc.)
- Caminhos muito longos (>260 caracteres em alguns cases)
- Problemas de permission/file locking no Windows
- Formato de path incompatível com Windows

---

## Solução 1: Desabilitar Logger Completamente (RECOMENDADO)

Passar um logger vazio ao modelo PPO:

```python
from stable_baselines3 import PPO
from stable_baselines3.common.logger import configure

# Configure logger com lista vazia (desabilita todos os formatos)
logger = configure(folder=None, format_strings=[])

# Criar modelo PPO
model = PPO(
    "MlpPolicy",
    env=vec_env,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    verbose=0,  # Importante: desabilitar verbose também
)

# Definir logger vazio
model.set_logger(logger)

# Agora o learn() não tentará escrever logs interno
model.learn(total_timesteps=1000000)
```

### Por que funciona:
- `format_strings=[]` significa que nenhum formato de saída é configurado
- O logger não tenta criar arquivos ou diretórios
- Training continua normalmente, apenas sem logging interno

---

## Solução 2: Redirecionar para Arquivo Seguro

Se você quer manter algum logging, redirecione para um arquivo em local seguro:

```python
from stable_baselines3 import PPO
from stable_baselines3.common.logger import configure
import os
from pathlib import Path

# Crie diretório de logs com path simples (sem caracteres especiais)
log_dir = Path("logs/sb3_safe").absolute()
log_dir.mkdir(parents=True, exist_ok=True)

# Configure logger com formatos seguros
# Evitar 'tensorboard' no Windows (causa problemas)
logger = configure(
    folder=str(log_dir),
    format_strings=["csv", "stdout"]  # Apenas CSV e stdout
)

# Criar e configurar modelo
model = PPO("MlpPolicy", env=vec_env, verbose=0)
model.set_logger(logger)

# Training sem OSError
model.learn(total_timesteps=1000000)
```

### Formatos disponíveis:
- `"csv"` — Salva métricas em CSV (seguro no Windows)
- `"stdout"` — Imprime em console
- `"log"` — Salva em arquivo de texto simples
- `"json"` — Salva em JSON
- `"tensorboard"` — ⚠️ EVITAR NO WINDOWS (causa OSError frequente)

---

## Solução 3: Desabilitar tensorboard_log

Alguns problemas ocorrem especificamente com TensorBoard. Desabilite-o explicitamente:

```python
model = PPO(
    "MlpPolicy",
    env=vec_env,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    verbose=0,
    tensorboard_log=None,  # Importante: não usar TensorBoard no Windows
)

# Opcionalmente desabilitar logger também
from stable_baselines3.common.logger import configure
logger = configure(folder=None, format_strings=[])
model.set_logger(logger)

model.learn(total_timesteps=1000000)
```

---

## Solução 4: Usar Context Manager (Mais Limpo)

Para garantir limpeza segura:

```python
from stable_baselines3 import PPO
from stable_baselines3.common.logger import configure
from contextlib import contextmanager

@contextmanager
def sb3_training_safe():
    """Context manager para treino seguro do SB3 no Windows."""
    logger = configure(folder=None, format_strings=[])
    yield logger

# Usar:
with sb3_training_safe() as logger:
    model = PPO("MlpPolicy", env=vec_env, verbose=0)
    model.set_logger(logger)
    model.learn(total_timesteps=1000000)
```

---

## Como Integrar no Projeto

### Opção A: Função Helper (RECOMENDADO)

Criar arquivo `agent/sb3_utils.py`:

```python
"""Utilidades para SB3 no Windows."""

from stable_baselines3.common.logger import configure
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def create_safe_sb3_logger(
    folder: Optional[str] = None,
    use_csv: bool = False,
    use_stdout: bool = True
):
    """
    Cria logger seguro do SB3 para Windows.

    Args:
        folder: Diretório para salvar logs (None = nenhum arquivo)
        use_csv: Se deve salvar em CSV (recomendado apenas com folder seguro)
        use_stdout: Se deve imprimir em stdout

    Returns:
        Logger configurado do SB3
    """
    formats = []

    if use_stdout:
        formats.append("stdout")

    if use_csv and folder:
        formats.append("csv")

    # Se não tem formats, usa lista vazia (desabilita logging)
    if not formats:
        logger.info("SB3 Logger desabilitar (nenhum formato configurado)")

    return configure(folder=folder, format_strings=formats)

def attach_safe_logger_to_model(model, folder=None, use_csv=False):
    """
    Anexa logger seguro a um modelo PPO/A2C/etc.

    Args:
        model: Modelo do SB3
        folder: Diretório (opcional)
        use_csv: Se deve salvar em CSV
    """
    logger_obj = create_safe_sb3_logger(
        folder=folder,
        use_csv=use_csv,
        use_stdout=True
    )
    model.set_logger(logger_obj)
    logger.info("Logger seguro anexado ao modelo")
    return model
```

### Opção B: Atualizar `scripts/train_ppo_skeleton.py`

```python
# Substituir a criação do modelo em train_ppo_skeleton.py

from agent.sb3_utils import attach_safe_logger_to_model

# ...

def train(self, symbol: str = 'OGNUSDT') -> dict:
    # ... código anterior ...

    # 2. Criar modelo PPO
    logger.info("Criando modelo PPO com config Phase 4...")
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
        verbose=0,
        tensorboard_log=None,  # Desabilitar TensorBoard
    )

    # ✅ FIXO: Anexar logger seguro
    attach_safe_logger_to_model(model, folder=None)

    # 3. Callbacks
    checkpoint_callback = CheckpointCallback(...)

    # 4. Treinar (agora sem OSError)
    logger.info(f"Iniciando treinamento para {symbol}...")
    model.learn(
        total_timesteps=self.config.total_timesteps,
        callback=checkpoint_callback
    )
```

### Opção C: Atualizar `agent/trainer.py`

```python
# Em agent/trainer.py, função train_phase1_exploration

def train_phase1_exploration(self, train_data: Dict[str, Any],
                            total_timesteps: int = 500000,
                            **env_kwargs) -> PPO:
    # ... setup anterior ...

    # Criar modelo PPO
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
        verbose=0,  # Desabilitar verbose
        tensorboard_log=None  # ✅ Desabilitar TensorBoard
    )

    # ✅ Anexar logger seguro
    from agent.sb3_utils import attach_safe_logger_to_model
    attach_safe_logger_to_model(self.model, folder=None)

    # Callback e training
    callback = TrainingCallback(log_interval=1000)
    self.model.learn(
        total_timesteps=total_timesteps,
        callback=callback,
        progress_bar=False
    )
```

---

## Checklist de Implementação

- [ ] Desabilitar `tensorboard_log=None` em todas as criações de PPO
- [ ] Desabilitar `verbose=0` em PPO
- [ ] Usar `configure(folder=None, format_strings=[])` ou função helper
- [ ] Chamar `model.set_logger()` antes de `model.learn()`
- [ ] Testar com `python main.py --train`
- [ ] Verificar se treinamento executa sem OSError

---

## Diagnóstico

Se ainda receber OSError, execute:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Seu código de treinamento aqui
# Isso vai mostrar exatamente qual operação falha
```

---

## Referências

- SB3 Logger Documentation: https://stable-baselines3.readthedocs.io/en/master/common/logger.html
- SB3 PPO Documentation: https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html
- Windows Path Limitations: https://docs.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation

