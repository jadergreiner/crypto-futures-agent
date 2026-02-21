# 🚀 Indução para Novas Sessões — GitHub Copilot

**Data:** 20 de fevereiro de 2026
**Versão:** 1.0
**Lido automaticamente?** Sim — Ver `.github/copilot-instructions.md`

---

## 📌 TL;DR — 3 Regras Críticas

Quando inicia sessão com o Copilot neste projeto:

### 1️⃣ **PORTUGUÊS em Tudo**
- ✅ Respostas do Copilot: português
- ✅ Código comentários: português
- ✅ Documentação: português
- ❌ Inglês apenas para APIs/bibliotecas

### 2️⃣ **Commits Limpos (ASCII, < 72 chars)**
```bash
✅ [SYNC] Sumário de atualização (correto)
❌ ee8dfb1 docs: Sumário de atualiza├º├úo (quebrado)
```bash

### 3️⃣ **Lint em Documentação (máx 80 chars/linha)**
```bash
markdownlint *.md docs/*.md  # Verificar antes de commit
markdownlint --fix *.md      # Corrigir automaticamente
```bash

---

## 📚 Referências Essenciais

| Documento | Propósito | When |
|-----------|----------|------|
| `.github/copilot-instructions.md` | Instruções do Copilot | Sempre carregado |
| `BEST_PRACTICES.md` | Boas práticas completas | Consultar antes de PR |
| `docs/SYNCHRONIZATION.md` | Rastreamento de sincronização | Ao alterar docs |
| `docs/FEATURES.md` | Status das features | Ao commitar código novo |

---

## ✅ Checklist de Indução

Quando assumindo papel de Copilot/agente:

- [ ] Ler `.github/copilot-instructions.md` completamente
- [ ] Confirmar: português será usado sempre
- [ ] Entender: matriz de dependências de docs
- [ ] Lembrar: commits com `[TAG]` e ASCII apenas
- [ ] Preparar: lint markdown antes de finalizar docs

---

## 🎯 Fluxo de Trabalho Esperado

```text
1. [PLANEJAMENTO]
   └─ Ler instrções em .github/copilot-instructions.md
      (3 regras críticas no final)

2. [EXECUÇÃO]
   └─ Implementar feature/fix:
      • Código em português
      • Testes inclusos
      • Comentários em português

3. [DOCUMENTAÇÃO]
   └─ Atualizar docs conforme matriz:
      • BEST_PRACTICES.md se aplica
      • Markdown lint antes de finalizar
      • Máx 80 caracteres por linha

4. [SINCRONIZAÇÃO]
   └─ Atualizar docs/SYNCHRONIZATION.md
      • Qual arquivo foi alterado?
      • Quais docs dependem?
      • Status de sync

5. [COMMIT]
   └─ Mensagem com [TAG] en português
      • [FEAT] Features novas
      • [FIX] Correções
      • [SYNC] Sincronização de docs
      • [TEST] Testes
      • [CHORE] Manutenção
      • ASCII only, < 72 caracteres

6. [PUSH]
   └─ Pronto para review/merge!
```text

---

## 🔄 Ciclo de Sincronização

**Regra de Ouro:** Código + Documentação sempre juntos

```text
Alterou symbols.py?
  └─ Atualizar: playbooks/, README, SYNC

Alterou playbooks/*.py?
  └─ Verificar: symbols.py, __init__.py, tests, README

Alterou README.md?
  └─ Atualizar: ROADMAP, RELEASES, FEATURES, CHANGELOG

Criou docs/ novo?
  └─ OBRIGATÓRIO: SYNCHRONIZATION.md + lint
```text

---

## 🛠️ Tools Recomendadas

### Para Lint Markdown

```bash
# Instalar (uma vez)
npm install -g markdownlint-cli

# Verificar
markdownlint *.md docs/*.md

# Corrigir automaticamente
markdownlint --fix *.md docs/*.md
```bash

### Para Git

```bash
# Verificar última mensagem
git log --oneline -1

# Ver histórico limpo
git log --oneline -10

# Commit com template
git commit -m "[FEAT] Sua descrição em português"
```bash

### Para Python

```bash
# Testes
pytest -q tests/test_seu_modulo.py

# Lint
flake8 seu_modulo.py

# Type check
mypy seu_modulo.py
```bash

---

## 💡 Dicas de Ouro

1. **Antes de commitar:**
   ```bash
   git log --oneline -1         # Verificar mensagem
   markdownlint *.md docs/*.md  # Lint docs
   pytest -q                    # Rodar testes
```bash

2. **Se quebrou uma regra:**
   - Avisar no PR qual regra foi quebrada
   - Corrigir no próximo commit
   - Atualizar `SYNCHRONIZATION.md`

3. **Quando em dúvida:**
   - Consultar `.github/copilot-instructions.md`
   - Consultar `BEST_PRACTICES.md`
   - Consultar `docs/SYNCHRONIZATION.md`

4. **Comunicação com time:**
   - SEMPRE português em diálogos
   - SEMPRE documentação sincronizada
   - SEMPRE commits com tags

---

## 🎓 Exemplo Completo: Adicionar Símbolo Novo

### Passo 1: Alterar código
```python
# config/symbols.py
SYMBOLS["NOVOUSDT"] = {
    "papel": "Novo ativo especulativo",
    "beta_estimado": 3.5,
    # ...
}
```json

### Passo 2: Criar playbook
```python
# playbooks/novo_playbook.py
class NovoPlaybook(BasePlaybook):
    """Estratégia para NOVOUSDT."""
    pass
```python

### Passo 3: Registrar
```python
# playbooks/__init__.py
from playbooks.novo_playbook import NovoPlaybook
```bash

### Passo 4: Atualizar docs
```markdown
# README.md
## Moedas Suportadas (17 Pares USDT)
...
- **NOVO (NOVOUSDT)**: Novo ativo especulativo

# docs/SYNCHRONIZATION.md
- NOVOUSDT | ✅ | 20/02 | Novo símbolo adicionado
```bash

### Passo 5: Lint docs
```bash
markdownlint README.md docs/SYNCHRONIZATION.md
markdownlint --fix README.md docs/SYNCHRONIZATION.md
```bash

### Passo 6: Commit
```bash
git commit -m "[SYNC] Adicionado símbolo NOVOUSDT e playbook"
```bash

---

## 📞 Ajuda Rápida

**P: Como assumir papel de agente?**
R: Ler este documento + ler `.github/copilot-instructions.md`

**P: Qual é a prioridade das 3 regras?**
R: Todas críticas, não há prioridade. Implementar todas.

**P: Posso quebrar lint de Markdown?**
R: Não, mas se necessário, reparar no próximo commit.

**P: Como reportar erro de sincronização?**
R: Abrir issue com tag `[SYNC]` referenciando arquivo.

---

**Versão:** 1.0 (20/02/2026)
**Mantido por:** GitHub Copilot
**Próxima revisão:** Quando novas práticas surgirem
