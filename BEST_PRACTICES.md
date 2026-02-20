# 📋 Boas Práticas do Projeto — Crypto Futures Agent

**Versão:** 1.0
**Data:** 20 de fevereiro de 2026
**Aplicável a:** Código, Documentação, Commits, Operação

---

## 🎯 Princípios Iniciais

1. **Segurança Operacional** — Nenhuma mudança quebra operação
   existente
2. **Rastreabilidade** — Cada mudança está documentada e
   sincronizada
3. **Previsibilidade** — Comportamento é determinístico e
   auditável
4. **Português Primeiro** — Idioma padrão em todo o projeto

---

## 📝 Boas Práticas de Código

### Estrutura e Organização

- Manter mudanças pequenas e focadas
- Não renomear APIs públicas desnecessariamente
- Preferir soluções locais antes de adicionar dependências
- Preservar compatibilidade entre modos `paper` e `live`
- Seguir padrões existentes de nomes e imports

### Segurança e Credenciais

- ❌ NUNCA commitar `.env`, chaves de API, credenciais
- ❌ NUNCA hardcode parâmetros de risco sensíveis
- ✅ Usar `config/` para parâmetros configuráveis
- ✅ Implementar fallbacks seguros quando dados faltam

### Comentários e Docstrings

- Evitar comentários óbvios
- Preferir nomes de variáveis significativos
- Usar docstrings NumPy style para funções públicas
- Type hints obrigatórios em assinaturas
- Exemplo ruim: `x = [1, 2, 3]  # lista`
- Exemplo bom: `candles: List[pd.DataFrame] = load_candles()`

### Funções e Responsabilidade

- Funções pequenas (< 30 linhas ideal)
- Uma responsabilidade clara por função
- Tratament robusto de erros externos (APIs, DB)
- Mensagens de erro descritivas em português

### Testes

- Rodar testes após toda mudança relevante:
  ```bash
  pytest -q tests/test_seu_modulo.py
  ```
- Não "consertar" testes não relacionados
- Mínimo de cobertura: 70% para módulos críticos
- Nomes de testes descrevem o que testam

---

## 💭 Boas Práticas de Documentação

### Linguagem

- ✅ **Português sempre** — Docs, comentários, logs, UI
- ✅ Termos técnicos em inglês apenas quando apropriado:
  - Nomes de bibliotecas: `scikit-learn`, `Gymnasium`
  - Nomes de APIs: `Binance SDK`, `WebSocket`
  - Padrões: `RESTful`, `PPO`, `OHLCV`
- ❌ Código em inglês misturado com português

### Capitalização e Formatação

- Títulos em Markdown: `# Título` (h1), `## Subtítulo` (h2)
- Nomes de seções descritivos e únicos
- Listas com `-` ou `*` consistentes
- Blocos de código com ` ```python ` (linguagem explícita)
- Links sempre quando apropriado: `[texto](/caminho)`

### Lint de Markdown

**Máximo 80 caracteres por linha** (inclusive títulos e listas)

- ✅ Correto:
  ```markdown
  Descrição curta que cabe em 80 caracteres
  Próxima linha com mais informação clara
  ```

- ❌ Errado:
  ```markdown
  Descrição muito longa que cabe MAIS de 80 caracteres e por
  isso quebrará a formatação em diferentes resoluções
  ```

- ❌ Errado com título:
  ```markdown
  # Este é um título muito longo que excede 80 caracteres (93)
  ```

### Estrutura de Documentação

```
docs/
├── FEATURES.md          → Roadmap de features
├── RELEASES.md          → Detalhes por versão
├── ROADMAP.md           → Timeline do projeto
├── SYNCHRONIZATION.md   → Rastreamento de sincronização
├── LESSONS_LEARNED.md   → Histórico de problemas resolvidos
├── USER_MANUAL.md       → Guia para usuários finais
├── USER_STORIES.md      → Histórias de usuário estruturadas
└── TRACKER.md           → Sprint tracker
```

Quando criar novo doc: adicionar referência em `SYNCHRONIZATION.md`

---

## 🔀 Boas Práticas de Commits

### Formato de Mensagem

**Template:**
```
[TAG] Escopo breve em português

Descrição detalhada (opcional):
- Por que foi feita a mudança
- Como foi implementada
- Qualquer nota relevante
```

### Tags Obrigatórias

| Tag | Uso | Exemplo |
|-----|-----|---------|
| `[FEAT]` | Nova feature | `[FEAT] Pipeline de dados F-08` |
| `[FIX]` | Correção de bug | `[FIX] Validação de gaps em dados` |
| `[SYNC]` | Sincronização de docs | `[SYNC] FEATURES.md atualizado` |
| `[DOCS]` | Apenas documentação | `[DOCS] README.md lint aplicado` |
| `[TEST]` | Testes novos/alterados | `[TEST] 8 testes para data_loader` |
| `[CHORE]` | Manutenção, limpeza | `[CHORE] Removidos prints debug` |
| `[PERF]` | Otimização | `[PERF] Índices SQL adicionados` |

### ⚠️ REGRA CRÍTICA: Não Quebrar Texto

**NÃO fazer:**
```
ee8dfb1 docs: Sumário de atualiza├º├úo de arquitetura
(BaseAutoTrader pattern + Quick
```

**FAZER:**
```
ee8dfb1 [SYNC] Sumário de atualização de arquitetura
```

**Explicação:**
- Usar apenas caracteres ASCII (0-127)
- Não quebrar linhas longas em múltiplas linhas
- Se mensagem > 72 caracteres, use `git log --oneline` ou
  abrevie no commit

**Verificar antes de commitar:**
```bash
git log --oneline -1  # Verificar última mensagem
```

---

## 📊 Boas Práticas de Versionamento

### Versionamento (SemVer)

Formato: `v{MAJOR}.{MINOR}.{PATCH}`

Exemplo: `v0.3.0`

- **MAJOR**: Quebra compatibilidade (novo modo operação)
- **MINOR**: Feature nova, compatível (F-08, F-09)
- **PATCH**: Bug fix, compatível (correção de validação)

### Arquivo CHANGELOG.md

Manter atualizado com padrão Keep a Changelog:

```markdown
## [0.3.0] - 2026-02-28
### Added
- Pipeline de dados para treinamento (F-08)

### Fixed
- Validação de gaps em OHLCV

### Changed
- RobustScaler por símbolo (sem data leakage)
```

---

## 🔄 Boas Práticas de Sincronização

### Matriz de Dependências

Quando alterar arquivo X, verificar se Y precisa atualizar:

| Alterado | Verificar | Tag |
|----------|-----------|-----|
| `symbols.py` | `playbooks/`, README, SYNC | `[SYNC]` |
| `playbooks/*.py` | `symbols.py`, `__init__.py`, tests | `[SYNC]` |
| `README.md` | ROADMAP, RELEASES, CHANGELOG | `[SYNC]` |
| `agent/reward.py` | FEATURES, docs/REWARD_FIXES | `[SYNC]` |
| Qualquer `docs/` | `SYNCHRONIZATION.md` | `[SYNC]` |

### Checklist de Commit

Antes de fazer push:

- [ ] Código está funcional
- [ ] Testes passam: `pytest -q`
- [ ] Documentação foi atualizada
- [ ] `SYNCHRONIZATION.md` foi atualizado
- [ ] Lint Markdown aplicado (máx 80 chars)
- [ ] Mensagem de commit correta: `[TAG] Escopo`
- [ ] Caracteres ASCII apenas (sem ├, ├º, etc)

---

## ⚙️ Boas Práticas de Operação

### Execução Automática

Para operador executar `iniciar.bat` sem impactos:

- ✅ Mudanças isoladas (F-08 não afeta `main.py`)
- ✅ Dependências da feature segregadas
- ✅ Zero mudanças em startup paths
- ✅ Logging padrão mantido
- ✅ Comportamento transparente

### Validações Críticas

Antes de merge em main:

1. Testes de integração passam
2. Documentação sincronizada
3. Lint Markdown OK
4. Commits com tags corretas
5. Transparência operacional confirmada

---

## 🚀 Boas Práticas de Performance

### Otimizações

- Preferir índices SQL antes de carregar tudo em memória
- Numpy vectorization em vez de loops Python
- Generators para lazy-loading grandes datasets
- Cache apropriado com expiração

### Benchmarks

Alvos de performance esperados:

- Load 18M dados H1: `< 2 segundos`
- Batch 100K timesteps: `< 5 segundos`
- Peak memory: `< 8 GB`
- Startup app: `< 5 segundos`

---

## 🔐 Boas Práticas de Segurança

### Risco Operacional

- Nunca remover validações de risco existentes
- Fallback conservador quando dados faltam
- Usar `config/` para parâmetros de risco
- Circuit breakers para losses > limiar

### Validação de Dados

- Verificar volume > 0 (dados inválidos)
- Detectar gaps > 15 minutos (coleta quebrada)
- Validar OHLC integridade (high >= low)
- Limpar NaN/inf antes de features

### Auditoria

- Registrar decisões importantes em logs
- Timestamps em UTC sempre
- Rastreabilidade de cada ordem
- Falha segura (prefira bloquear que arriscar)

---

## 📚 Referências de Boas Práticas

### Estilo de Código Python

- [PEP 8](https://www.python.org/dev/peps/pep-0008/) —
  Style guide
- [PEP 257](https://www.python.org/dev/peps/pep-0257/) —
  Docstring conventions

### Versionamento

- [SemVer](https://semver.org/) — Semantic Versioning
- [Keep a Changelog](https://keepachangelog.com/) — CHANGELOG
  format

### Git Commits

- [Conventional Commits](https://www.conventionalcommits.org/)
  — Padrão para commits

### Markdown

- [Markdown Lint](https://github.com/markdownlint/markdownlint)
  — Validação
- [CommonMark](https://spec.commonmark.org/) — Especificação

---

## ❓ FAQ de Boas Práticas

**P: Posso usar variáveis de uma letra?**
R: Apenas em contextos óbvios (`for i in range(n)` é OK, `x =
valor_importante` não é)

**P: Como aplicar lint em Markdown?**
R: `npm install -g markdownlint-cli && markdownlint *.md`

**P: O que fazer se quebrei uma regra?**
R: Avisar no PR, corrigir no próximo commit, atualizar
`SYNCHRONIZATION.md`

**P: Quando usar `[SYNC]` vs `[FEAT]`?**
R: `[SYNC]` se APENAS docs foram alteradas, `[FEAT]` se código +
docs

---

**Mantido por:** GitHub Copilot + Time de Engenharia
**Última atualização:** 20 de fevereiro de 2026
**Próxima revisão:** Quando surgirem novas boas práticas
