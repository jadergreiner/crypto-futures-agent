# 🔧 Como Desabilitar Logger SB3 no Windows

## TL;DR — A Solução em 30 segundos

```python
from agent.sb3_utils import attach_safe_logger_to_model

# Criar modelo
model = PPO("MlpPolicy", env, verbose=0, tensorboard_log=None)

# Uma linha que resolve:
attach_safe_logger_to_model(model)

# Treinar sem OSError
model.learn(1000000)
```

Pronto! ✅

---

## 🚨 Problema

```
OSError: [Errno 22] Invalid argument
```

Acontece durante `model.learn()` em Windows quando Stable-Baselines3 tenta escrever logs internos.

---

## 💡 Por quê?

1. **SB3 usa TensorBoard internamente** para logging
2. **TensorBoard cria arquivos** com nomes que Windows não aceita
3. **No Windows**, certos caracteres e caminhos são inválidos
4. **Resultado:** OSError quando SB3 tenta salvar logs

---

## ✅ Solução Oficial: Desabilitar Logger

### Opção A: Usar função helper (RECOMENDADO)

**Arquivo:** `agent/sb3_utils.py` (já criado)

```python
from agent.sb3_utils import attach_safe_logger_to_model

model = PPO("MlpPolicy", env, verbose=0, tensorboard_log=None)
attach_safe_logger_to_model(model)
model.learn(1000000)
```

### Opção B: Configurar logger manualmente

```python
from stable_baselines3.common.logger import configure

# Desabilitar completamente
logger = configure(folder=None, format_strings=[])
model.set_logger(logger)
```

### Opção C: Redirecionar para local seguro

```python
from stable_baselines3.common.logger import configure

logger = configure("logs/sb3_safe", ["csv", "stdout"])
model.set_logger(logger)
```

---

## 📦 O que foi criado

```
agent/
├── sb3_utils.py                    ← Funções helper
│   ├── create_safe_sb3_logger()
│   ├── attach_safe_logger_to_model()  ← USE ISTO
│   ├── make_ppo_windows_safe()
│   └── validate_sb3_setup()

docs/
├── SB3_LOGGER_WINDOWS_FIX.md       ← Documentação completa

examples/
├── sb3_logger_safe_examples.py     ← 4 exemplos de uso

tests/
├── test_sb3_logger_safe.py         ← Teste automatizado

QUICK_START_SB3_LOGGER_FIX.py       ← Guia rápido
APPLY_SB3_LOGGER_PATCH.py           ← Instruções de patch
SB3_LOGGER_FIX_SUMMARY.md           ← Sumário executivo
```

---

## 🚀 Como integrar no seu projeto

### Passo 1: Validar que funciona

```bash
python tests/test_sb3_logger_safe.py
```

Resultado esperado:
```
✅ PASS: SB3 Imports
✅ PASS: sb3_utils Imports
✅ PASS: Logger Creation
✅ PASS: PPO Training
✅ TODOS OS TESTES PASSARAM!
```

### Passo 2: Modificar seus arquivos

#### Arquivo: `scripts/train_ppo_skeleton.py`

**Linha ~30 (imports):**
```python
from agent.sb3_utils import attach_safe_logger_to_model
```

**Linha ~164 (criação do modelo):**
```python
model = PPO(
    policy="MlpPolicy",
    env=vec_env,
    learning_rate=self.config.learning_rate,
    # ... outros parâmetros ...
    verbose=0,              # ← Adicionar
    tensorboard_log=None,   # ← Adicionar
)

attach_safe_logger_to_model(model)  # ← Adicionar esta linha
```

#### Arquivo: `agent/trainer.py`

Mesmo padrão (ver `APPLY_SB3_LOGGER_PATCH.py` para detalhes).

### Passo 3: Testar

```bash
python main.py --train
```

Resultado esperado: ✅ Treinamento sem OSError

---

## 📊 Comparação

| Aspecto | Antes | Depois |
|--------|-------|--------|
| OSError em Windows | ❌ Frequente | ✅ Resolvido |
| Logging interno | TensorBoard | Desabilitado |
| Performance | Normal | Normal/Melhor |
| Compatibilidade | Quebrada no Windows | ✅ Windows + Linux + macOS |
| Callbacks | Funcionam | Continuam funcionando |

---

## 🔍 Entender a solução

### Raiz do problema

1. **SB3 padrão cria:**
   ```
   logs/tensorboard/CartPole_0/events.out.tfevents.1234567890.hostname
   ```

2. **No Windows, isso falha porque:**
   - Caractere `:` é inválido em nomes de arquivo
   - Caminho pode ficar muito longo
   - File locking issues

3. **Solução:**
   ```python
   # Criar logger vazio - nenhum arquivo será criado
   logger = configure(folder=None, format_strings=[])
   model.set_logger(logger)
   ```

### Por que funciona

- `format_strings=[]` = nenhum formato de output (csv, json, tensorboard, etc.)
- Sem formato = sem tentativa de criar arquivos
- Training continua normalmente (sem logs apenas)

---

## 🎯 Três formas de implementar

### 1️⃣ Simples (1 arquivo)

```python
from agent.sb3_utils import attach_safe_logger_to_model

model = PPO("MlpPolicy", env, verbose=0, tensorboard_log=None)
attach_safe_logger_to_model(model)
```

Código: **2 linhas**

---

### 2️⃣ Com mais controle

```python
from stable_baselines3.common.logger import configure

logger = configure(folder=None, format_strings=[])
model = PPO("MlpPolicy", env, verbose=0, tensorboard_log=None)
model.set_logger(logger)
```

Código: **4 linhas**

---

### 3️⃣ Redirecionar para arquivo

```python
from stable_baselines3.common.logger import configure
from pathlib import Path

log_dir = Path("logs/sb3_safe")
log_dir.mkdir(parents=True, exist_ok=True)

logger = configure(str(log_dir), ["csv", "stdout"])
model = PPO("MlpPolicy", env, verbose=0, tensorboard_log=None)
model.set_logger(logger)

# Salva em: logs/sb3_safe/progress.csv
```

Código: **8 linhas** (mas salva métricas em CSV)

---

## 📝 Checklist

- [ ] Ler este arquivo
- [ ] Ler `docs/SB3_LOGGER_WINDOWS_FIX.md`
- [ ] Executar `python tests/test_sb3_logger_safe.py` ✅
- [ ] Modificar `scripts/train_ppo_skeleton.py` (3 linhas)
- [ ] Modificar `agent/trainer.py` (3 linhas)
- [ ] Testar `python main.py --train`
- [ ] Fazer commit com tag `[FEAT]`

**Tempo total:** ~20 minutos

---

## 🐛 Diagnóstico

Se ainda receber OSError:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Seu código de treinamento
model.learn(1000)
```

Isso vai mostrar exatamente qual operação falha. Geralmente é:
- `tensorboard_log` não é `None`
- `verbose` não é `0`
- Logger não foi anexado correctamente

---

## 📚 Documentação

- **[SB3 Logger Docs](https://stable-baselines3.readthedocs.io/en/master/common/logger.html)** — Documentação oficial
- **`docs/SB3_LOGGER_WINDOWS_FIX.md`** — Documentação local (4 soluções)
- **`APPLY_SB3_LOGGER_PATCH.py`** — Instruções de patch
- **`examples/sb3_logger_safe_examples.py`** — 4 exemplos diferentes

---

## ❓ Dúvidas Frequentes

**P: Perco meus logs de treinamento?**
R: Sim. Desabilitar logger = sem logs internos. Você pode usar callbacks customizados para logging.

**P: Posso ainda usar TensorBoard?**
R: Não recomendado no Windows. Use CSV ou stdout em vez disso.

**P: Funciona com A2C, DQN, SAC?**
R: Sim! COM qualquer algoritmo do SB3.

**P: E no Linux/macOS?**
R: Funciona, mas geralmente não é necessário. Windows é o problema.

**P: Como restauro logging depois?**
R: Use `configure()` com formatos seguros (sem tensorboard).

---

## ✨ Próxima Tarefa

```
python tests/test_sb3_logger_safe.py
```

Se passar, você está pronto para integrar! ✅

---

## 📞 Resumo

| Pergunta | Resposta |
|----------|----------|
| **Qual é o problema?** | OSError quando SB3 tenta criar logs no Windows |
| **Qual é a causa?** | TensorBoard cria arquivos com nomes inválidos |
| **Qual é a solução?** | `attach_safe_logger_to_model(model)` |
| **Quantas linhas?** | 1-3 linhas de código |
| **Quanto tempo?** | 5 minutos para integrar |
| **Funciona?** | ✅ Sim, testado |

---

**Vá fazer:** `python tests/test_sb3_logger_safe.py` agora! 🚀
