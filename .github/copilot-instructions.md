# Instruções para o GitHub Copilot

Estas instruções orientam mudanças neste repositório `crypto-futures-agent`.

## Objetivo
- Priorizar segurança operacional, previsibilidade e rastreabilidade.
- Evitar mudanças amplas sem necessidade.
- Fazer correções na causa raiz, não apenas paliativos.

## Idioma
- Manter o idioma do projeto sempre em português.
- Escrever documentação, comentários, mensagens de log e
  textos de interface em português.
- Permitir termos técnicos em inglês apenas quando forem
  nomes próprios, APIs, bibliotecas ou padrões amplamente
  usados.

## Stack e organização
- Linguagem principal: Python.
- Módulos importantes:
  - `agent/`: lógica de RL, ambiente e reward.
  - `execution/`: execução de ordens.
  - `data/`: clientes e coleta de dados (Binance, macro, sentimento).
  - `risk/` e `monitoring/`: controles de risco e monitoramento.
  - `backtest/`: backtesting e walk-forward.
  - `playbooks/`: regras por símbolo.
  - `tests/`: testes automatizados.

## Regras de implementação
- Manter mudanças pequenas, focadas e compatíveis com o estilo existente.
- Não renomear APIs públicas, arquivos ou funções sem necessidade explícita.
- Não adicionar dependências novas se houver solução local simples.
- Não inserir credenciais, chaves de API ou segredos em código, logs ou docs.
- Evitar hardcode de parâmetros sensíveis de risco; preferir `config/`.
- Preservar compatibilidade entre modos `paper` e `live`.

## Regras de domínio (trading/risk)
- Nunca remover validações de risco existentes para "fazer
  funcionar".
- Qualquer alteração em sizing, alavancagem, stop,
  liquidação, margem ou reward deve:
  - manter comportamento seguro por padrão;
  - ter fallback conservador em caso de erro/ausência de
    dados;
  - registrar decisão relevante de forma auditável.
- Em caso de dúvida, preferir bloquear operação a assumir
  risco extra.

## Logs e observabilidade
- Reutilizar o padrão de logging existente em
  `monitoring/`.
- Logs devem ser úteis para diagnóstico e curtos o
  suficiente para operação contínua.
- Não gerar ruído excessivo em loops de alta frequência.

## Testes e validação
- Sempre que alterar lógica, rodar ao menos os testes
  mais próximos do escopo alterado.
- Quando aplicável, usar:
  - `pytest -q`
  - ou teste específico, por exemplo: `pytest -q tests/test_new_symbols.py`
- Não corrigir testes não relacionados sem solicitação explícita.

## Estilo de código
- Seguir padrões já usados no repositório (nomes, imports, estrutura).
- Evitar comentários óbvios e variáveis de uma letra.
- Preferir funções pequenas e com responsabilidade clara.
- Tratar erros de integração externa com mensagens úteis e fallback seguro.

## Documentação e Sincronização

### Regra de Sincronização Obrigatória

**CRÍTICO:** Toda mudança em código deve sincronizar
documentação automaticamente.

Quando alterado:
- `config/symbols.py` → atualizar `README.md`,
  `playbooks/__init__.py`, `docs/SYNCHRONIZATION.md`
- `playbooks/*.py` → verificar `symbols.py`,
  `playbooks/__init__.py`, testes
- `README.md` versão → atualizar `docs/ROADMAP.md`,
  `docs/RELEASES.md`, `CHANGELOG.md`
- Qualquer ficheiro em `docs/` → rastrear em
  `docs/SYNCHRONIZATION.md`

### Protocolo de Sincronização

1. **Identificar mudança** — Qual arquivo foi alterado?
2. **Propagar mudança** — Quais documentos dependem deste?
3. **Validar impacto** — Há testes que confirmam a mudança?
4. **Documentar sincronização** — Atualizar `docs/SYNCHRONIZATION.md`
5. **Commit com [SYNC] tag** — `[SYNC] Documento X sincronizado`

### Matriz de Dependências

```
symbols.py ← Fonte de Verdade
  ├── playbooks/*.py (um playbook por símbolo)
  ├── playbooks/__init__.py (registro de imports)
  ├── config/execution_config.py (auto-sync via ALL_SYMBOLS)
  ├── README.md (listagem de moedas)
  └── docs/SYNCHRONIZATION.md (rastreamento)

playbooks/*.py
  ├── symbols.py (check: símbolo existe?)
  ├── playbooks/__init__.py (check: registrado?)
  ├── tests/test_*playbook.py (check: testa?)
  └── README.md (atualizar listagem)

README.md
  ├── docs/ROADMAP.md (versão consistente)
  ├── docs/RELEASES.md (features listadas)
  ├── docs/FEATURES.md (status de features)
  └── CHANGELOG.md (entrada de release)

docs/*
  └── docs/SYNCHRONIZATION.md (sempre ratrear)
```

### Checklist de Atualização

Antes de confirmar qualquer mudança:

- [ ] Código alterado está funcional?
- [ ] Testes passam (`pytest -q`)?
- [ ] Documentação dependente foi atualizada?
- [ ] `docs/SYNCHRONIZATION.md` foi atualizado?
- [ ] `README.md` reflete mudança se impacta usuário?
- [ ] Commit message contém `[SYNC]` se documentação foi alterada?

### Exemplos de Sincronização Correta

**Exemplo 1: Adicionar novo símbolo**
```
1. Editar config/symbols.py → adicionar XYZUSDT
2. Criar playbooks/xyz_playbook.py
3. Editar playbooks/__init__.py → adicionar importação
4. Editar README.md → adicionar moeda na listagem
5. Criar tests/test_xyz_playbook.py
6. Editar docs/SYNCHRONIZATION.md → rastrear mudança
7. Commit: "[SYNC] Adicionados símbolo XYZ e playbook correspondente"
```

**Exemplo 2: Alterar reward function**
```
1. Editar agent/reward.py
2. Editar tests/test_reward.py
3. Editar docs/REWARD_FIXES_*.md (se arquivo específico existe)
4. Editar README.md → seção "Reward Function"
5. Editar CHANGELOG.md → adicionar entry
6. Editar docs/SYNCHRONIZATION.md → rastrear mudança
7. Commit: "[SYNC] Corrigido reward function, documentação atualizada"
```

## O que evitar
- Não criar funcionalidades "nice to have" fora do pedido.
- Não alterar arquitetura inteira para resolver problema local.
- Não executar ações destrutivas (ex.: apagar dados, cancelar
  ordens em massa) sem solicitação explícita.
- **NÃO deixar documentação desatualizada** — sincronização é
  obrigatória.

## Três Regras Críticas — Adicionadas 20/02/2026

### Regra 1: Diálogo e Documentação SEMPRE em Português

**OBRIGATÓRIO:**
- Todos os diálogos (respostas do Copilot) em português
- Comentários de código em português
- Mensagens de log em português
- Documentação em português
- Exceção: Termos técnicos propriedade (APIs, bibliotecas)

**Verificação:** `grep -r "english\|english" *.md src/ --include="*.py"`
deve retornar vazio (exceto comentários técnicos)

### Regra 2: Não Quebrar Texto de Commits

**OBRIGATÓRIO:** Mensagens legíveis, ASCII apenas

**Padrão:** `[TAG] Escopo breve em português`

**Exemplo ERRADO:**
```
ee8dfb1 docs: Sumário de atualiza├º├úo
(caracteres corrompidos, linha quebrada)
```

**Exemplo CORRETO:**
```
ee8dfb1 [SYNC] Sumário de atualização de arquitetura
```

**Regras:**
- Usar apenas ASCII (0-127)
- Máximo 72 caracteres primeira linha
- Tags: `[FEAT]`, `[FIX]`, `[SYNC]`, `[DOCS]`, `[TEST]`
- Verificar: `git log --oneline -1` (sem `.` ruído)

### Regra 3: Aplicar Lint em TODOS os Docs

**OBRIGATÓRIO:** Markdown lint em docs criadas/editadas

**Limitar:** Máximo 80 caracteres por linha

**Tool:**
```bash
npm install -g markdownlint-cli
markdownlint *.md docs/*.md
markdownlint --fix *.md docs/*.md  # Corrigir
```

**Exemplo ERRADO:**
```markdown
## Análise de Dados de Treinamento com RobustScaler Normalizado
```

**Exemplo CORRETO:**
```markdown
## Análise de Dados com Normalização

Usando RobustScaler para evitar data leakage
```

**Checklist antes de commit:**
- [ ] Nenhuma linha > 80 caracteres
- [ ] Títulos descritivos
- [ ] Português correto
- [ ] Listas consistentes (`-` ou `*`)
- [ ] Blocos de código com linguagem: ` ```python `

**Referência:** Ver `BEST_PRACTICES.md` para detalhes completos

## Sincronização Obrigatória de Documentação

**CRÍTICO:** Toda mudança em código deve sincronizar documentação automaticamente.

### Protocolo de Sincronização (Automático)

Sempre que alterar um dos documentos principais:
- `config/symbols.py` → atualizar `README.md`, `playbooks/__init__.py`, `docs/SYNCHRONIZATION.md`
- `docs/FEATURES.md` → atualizar `docs/ROADMAP.md`, `CHANGELOG.md`, `docs/SYNCHRONIZATION.md`
- Qualquer arquivo em `docs/` → registrar em `docs/SYNCHRONIZATION.md`

### Checklist de Sincronização Obrigatória

Antes de cada commit com mudanças:

- [ ] **Código alterado está funcional?**
- [ ] **Testes passam?** (`pytest -q`)
- [ ] **Documentação dependente foi atualizada?**
  - [ ] `docs/SYNCHRONIZATION.md` registra mudança?
  - [ ] `docs/FEATURES.md` reflete status?
  - [ ] `docs/ROADMAP.md` reflete prioridades?
  - [ ] `README.md` reflete mudança?
- [ ] **Commit message contém tag?** (`[SYNC]`, `[FEAT]`, `[FIX]`, `[TEST]`)

### Validação Automática

Cada commit com `[SYNC]` tag deve manter checklist em `docs/SYNCHRONIZATION.md`

---

**Referência:** Ver `docs/SYNCHRONIZATION.md` para histórico completo
