# 📚 MAPA DE NAVEGAÇÃO — Sistema de Reuniões Semanais
## Especialista em Prompts para Agentes Autônomos

---

## 🎯 O Que Você Vai Encontrar?

Este documento explica **onde ir** para entender e **como usar** o sistema de reuniões.

---

## 📍 Localização dos Arquivos

### 1. **Prompts & Templates**

#### `prompts/prompts_reuniao_head_operador_crypto_futures.md` ⭐
**O QUE LEIA se**: Quer entender a estrutura de uma reunião
**Contém**: Template completo de 2100+ linhas com:
- Papéis (HEAD + OPERADOR)
- Matriz de dados
- Análise em 4 categorias
- Formato de conversa
- Output esperado (feedback + ações + investimentos)
- Regras LLM

**Tempo de leitura**: 15 minutos

---

### 2. **Código Python**

#### `scripts/reuniao_manager.py`
**O QUE LEIA se**: Quer integrar reuniões em seu código
**Contém**: Classe `ReuniaoWeeklyDB` com métodos:
```python
db.criar_reuniao(...)                 # ← Começar aqui
db.adicionar_dialogo(...)
db.criar_acao(...)
db.criar_investimento(...)
db.exportar_relatorio_markdown(...)
```

**Tempo de leitura**: 10 minutos | **Linhas**: 550

---

#### `scripts/executar_reuniao_semanal.py`
**O QUE LEIA se**: Quer rodar reunião automática
**Contém**: Classe `ExecutorReuniaoSemanal` com:
- Fluxo 7 passos automatizado
- Carregamento de métricas
- Comparação com semana anterior
- Geração de relatório

**Como rodar**:
```bash
python scripts/executar_reuniao_semanal.py
```

**Tempo de leitura**: 5 minutos | **Linhas**: 470

---

### 3. **Documentação**

#### `docs/GUIA_REUNIOES_SEMANAIS.md` ⭐⭐⭐
**O QUE LEIA se**: Está começando e quer aprender passo-a-passo
**Contém**:
- ✅ Visão geral (5 min)
- ✅ Instalação (5 min)
- ✅ Fluxo completo com exemplos (20 min)
- ✅ Rastreamento de ações (5 min)
- ✅ Consultas SQL úteis (5 min)
- ✅ Template semanal pronto (3 min)
- ✅ Troubleshooting (5 min)

**Tempo total**: 45 minutos | **Readiness**: 100%

---

#### `docs/SISTEMA_REUNIOES_RESUMO.md`
**O QUE LEIA se**: Quer um resumo executivo
**Contém**:
- ✅ O que foi entregue (4 componentes)
- ✅ Schema do banco de dados
- ✅ Quick Start (2 opções)
- ✅ Recursos principais
- ✅ Checklist de implementação
- ✅ Próximos passos opcionais

**Tempo de leitura**: 15 minutos

---

#### `docs/reuniao_2026_09_sem9.md`
**O QUE VEJA se**: Quer ver um exemplo real de saída
**Contém**:
- ✅ Diálogos HEAD × OPERADOR
- ✅ Feedbacks (força, fraqueza, oportunidade)
- ✅ Ações (crítica, alta, média)
- ✅ Investimentos (custo, ROI, status)

**Gerading tempo**: 3 minutos para ler

---

### 4. **Banco de Dados**

#### `db/reunioes_weekly.db`
**O QUE CONTÉM**:
```
8 tabelas (reunioes, dialogos, topicos, feedbacks, acoes, 
investimentos, evolucoes, comparacoes)

- reunioes: 1 registro (exemplo)
- dialogos_reuniao: 3 registros (exemplo)
- feedbacks_reuniao: 3 registros (exemplo)
- acoes_reuniao: 2 registros (exemplo)
- investimentos_reuniao: 3 registros (exemplo)
```

**Como consultar**:
```bash
sqlite3 db/reunioes_weekly.db "SELECT * FROM acoes_reuniao"
```

---

## 🗺️ Roteiros de Navegação

### 🚀 Roteiro 1: "Quero Usar Agora (5 minutos)"

1. Abra: `docs/GUIA_REUNIOES_SEMANAIS.md` (seção "Quick Start")
2. Execute:
   ```bash
   python scripts/executar_reuniao_semanal.py
   ```
3. Veja resultado: `docs/reuniao_2026_09_sem9.md`

**Status**: Reunião automática criada, diálogos registrados, investimentos propostos ✅

---

### 📚 Roteiro 2: "Quero Entender Tudo (45 minutos)"

1. **Leia (5 min)**: `docs/SISTEMA_REUNIOES_RESUMO.md` (Overview)
2. **Leia (20 min)**: `docs/GUIA_REUNIOES_SEMANAIS.md` (Completo)
3. **Explore (10 min)**: Template `prompts/prompts_reuniao_head_operador_crypto_futures.md`
4. **Veja (5 min)**: Código `scripts/reuniao_manager.py` (classe principal)
5. **Teste (5 min)**: Execute `python scripts/executar_reuniao_semanal.py`

**Status**: Você domina o sistema ✅

---

### 💻 Roteiro 3: "Quero Integrar no Meu Código (30 minutos)"

1. **Leia (5 min)**: `docs/SISTEMA_REUNIOES_RESUMO.md` (Seção "Como Usar")
2. **Copie (5 min)**: Código exemplo de `docs/GUIA_REUNIOES_SEMANAIS.md`
3. **Estude (10 min)**: `scripts/reuniao_manager.py` (API)
4. **Implemente (10 min)**: Seu próprio código usando `ReuniaoWeeklyDB`

**Template de Início**:
```python
from scripts.reuniao_manager import ReuniaoWeeklyDB

db = ReuniaoWeeklyDB()
id_reuniao = db.criar_reuniao(
    data_reuniao="2026-02-20 17:00:00",
    semana_numero=8,
    ano=2026,
    head_nome="[Seu Nome]",
    operador_versao="v0.3"
)

# Adicione diálogos, feedback, ações...
# Exporte relatório
```

---

### 🎯 Roteiro 4: "Quero Criar Meu Próprio Template (60 minutos)"

1. **Leia (15 min)**: Template completo `prompts/prompts_reuniao_head_operador_crypto_futures.md`
2. **Compreenda (20 min)**: Estrutura, papeisponto, matriz de análise
3. **Customize (15 min)**: Edite seções que você quer mudar
4. **Valide (10 min)**: Teste com `ExecutorReuniaoSemanal`

---

## 🔍 Índice Rápido (Por Necessidade)

| Necessidade | Vá Para | Tempo |
|-------------|---------|-------|
| Rodar reunião agora | `Quick Start` em GUIA | 5 min |
| Entender arquitetura | `SISTEMA_REUNIOES_RESUMO.md` | 15 min |
| Ver exemplo de saída | `docs/reuniao_2026_09_sem9.md` | 3 min |
| Aprender API Python | `docs/GUIA_REUNIOES_SEMANAIS.md` (Usar) | 20 min |
| Estrutura do banco | `SISTEMA_REUNIOES_RESUMO.md` (Schema) | 5 min |
| Customizar prompt | `prompts/prompts_reuniao_*.md` | 30 min |
| Troubleshoot erro | `docs/GUIA_REUNIOES_SEMANAIS.md` (Troubleshooting) | 10 min |
| Integrar em projeto | `docs/GUIA_REUNIOES_SEMANAIS.md` (Programático) | 30 min |

---

## 📊 Árvore de Dependências

```
prompts/prompts_reuniao_head_operador_crypto_futures.md
    ↓ (define estrutura)
    
scripts/reuniao_manager.py (ReuniaoWeeklyDB)
    ├─ Cria: db/reunioes_weekly.db
    ├─ Lê/escreve 8 tabelas
    └─ Exporta: Markdown
        
scripts/executar_reuniao_semanal.py (ExecutorReuniaoSemanal)
    ├─ Usa: ReuniaoWeeklyDB
    ├─ Carrega: Métricas (simuladas)
    ├─ Gera: docs/reuniao_YYYY_NN_semNN.md
    └─ Imprime: Resumo ejecutivo
        
docs/
    ├─ GUIA_REUNIOES_SEMANAIS.md (Learn)
    ├─ SISTEMA_REUNIOES_RESUMO.md (Summary)
    ├─ reuniao_2026_09_sem9.md (Example output)
    └─ MAPA_NAVEGACAO.md (← You are here)
```

---

## ⚡ Atalhos Úteis

### Executar Reunião
```bash
python scripts/executar_reuniao_semanal.py
```

### Ver Última Reunião
```bash
cat docs/reuniao_*.md | tail -50
```

### Listar Todas as Reuniões
```bash
sqlite3 db/reunioes_weekly.db "SELECT data_reuniao, id_reuniao FROM reunioes ORDER BY data_reuniao DESC"
```

### Ver Ações Pendentes
```bash
sqlite3 db/reunioes_weekly.db "SELECT descricao_acao, prioridade FROM acoes_reuniao WHERE status_acao = 'pendente'"
```

### Gerar Novo Relatório
```python
from scripts.reuniao_manager import ReuniaoWeeklyDB
db = ReuniaoWeeklyDB()
db.exportar_relatorio_markdown(id_reuniao=1, arquivo_saida="docs/nova_reuniao.md")
```

---

## 🎓 Estrutura de Aprendizado Recomendada

### Nível 1: Iniciante (15 minutos)
- ✅ Leia: `SISTEMA_REUNIOES_RESUMO.md` (Overview seção)
- ✅ Execute: `python scripts/executar_reuniao_semanal.py`
- ✅ Veja: `docs/reuniao_2026_09_sem9.md`

### Nível 2: Intermediário (45 minutos)
- ✅ Leia: `GUIA_REUNIOES_SEMANAIS.md` completo
- ✅ Estude: `scripts/reuniao_manager.py` (classe e métodos)
- ✅ Teste: Código de exemplo em Python

### Nível 3: Avançado (2 horas)
- ✅ Customize: Template de prompt
- ✅ Estenda: Adicione novas tabelas/fields ao SQLite
- ✅ Integre: Dados reais do seu agente
- ✅ Automatize: Pipeline CI/CD

---

## 📝 Checklist de Primeiros Passos

- [ ] Abri este arquivo (você está aqui ✅)
- [ ] Li `SISTEMA_REUNIOES_RESUMO.md` (15 min)
- [ ] Executei `python scripts/executar_reuniao_semanal.py` (2 seg)
- [ ] Vi `docs/reuniao_2026_09_sem9.md` (3 min)
- [ ] Li `GUIA_REUNIOES_SEMANAIS.md` parte "Quick Start" (5 min)

**Total**: 25 minutos → **Pronto para usar!**

---

## 🆘 Precisa de Ajuda?

### "Dá erro ao rodar o script"
→ Vá para: `GUIA_REUNIOES_SEMANAIS.md` seção "Troubleshooting"

### "Não entendo a estrutura do banco"
→ Vá para: `SISTEMA_REUNIOES_RESUMO.md` seção "Banco de Dados"

### "Como customizar o template?"
→ Vá para: `prompts/prompts_reuniao_head_operador_crypto_futures.md` (base)

### "Como integrar dados reais?"
→ Vá para: `GUIA_REUNIOES_SEMANAIS.md` seção "Uso Programático"

### "Posso apagar reuniões antigas?"
→ Vá para: `GUIA_REUNIOES_SEMANAIS.md` seção "Troubleshooting" (Database corrompido)

---

## 🔗 Links Rápidos

| Arquivo | Propósito | Link |
|---------|-----------|------|
| Template de Prompt | Estrutura de reunião | [`prompts_reuniao_*.md`](../prompts/prompts_reuniao_head_operador_crypto_futures.md) |
| Biblioteca Python | API de persistência | [`reuniao_manager.py`](../scripts/reuniao_manager.py) |
| Executor | Automatização | [`executar_reuniao_semanal.py`](../scripts/executar_reuniao_semanal.py) |
| Guia Completo | Learn everything | [`GUIA_REUNIOES_SEMANAIS.md`](GUIA_REUNIOES_SEMANAIS.md) |
| Resumo | 5-min overview | [`SISTEMA_REUNIOES_RESUMO.md`](SISTEMA_REUNIOES_RESUMO.md) |
| Exemplo Real | Ver output | [`reuniao_2026_09_sem9.md`](reuniao_2026_09_sem9.md) |
| Este Arquivo | You are here | [`MAPA_NAVEGACAO.md`](MAPA_NAVEGACAO.md) |

---

## ✅ Validação de Entrega

- [x] 4 Componentes principais
- [x] Banco SQLite funcional
- [x] Testes executados com sucesso
- [x] Relatório de exemplo gerado
- [x] 100% documentação em português
- [x] Zero dependências externas
- [x] Compatível com Python 3.8+
- [x] Commit com `[SYNC]` tag
- [x] Mapa de navegação (este arquivo)

**Status**: ✅ **COMPLETO E PRONTO PARA USO** ✅

---

**Última atualização**: 20 de fevereiro de 2026
**Versão**: 1.0
**Autor**: Especialista em Prompts para Agentes Autônomos

---

**Comece aqui**: [Quick Start em 5 minutos](GUIA_REUNIOES_SEMANAIS.md#-como-usar-quick-start)

