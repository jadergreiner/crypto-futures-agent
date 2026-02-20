# 📋 Rastreamento de Sincronização de Documentação

**Última Atualização:** 20 de fevereiro de 2026

## 🎯 Objetivo

Garantir que toda a documentação do projeto (README, docs/, instruções do Copilot) esteja sincronizada e consistente, refletindo mudanças reais no código e comportamento do sistema.

## 📚 Documentos Rastreados

### Documentação Principal
- ✅ [README.md](README.md) — Visão geral, versão e status do projeto
- ✅ [docs/ROADMAP.md](docs/ROADMAP.md) — Roadmap do projeto e releases
- ✅ [docs/RELEASES.md](docs/RELEASES.md) — Detalhes de cada release
- ✅ [docs/FEATURES.md](docs/FEATURES.md) — Lista de features por release
- ✅ [docs/TRACKER.md](docs/TRACKER.md) — Sprint tracker
- ✅ [docs/USER_STORIES.md](docs/USER_STORIES.md) — User stories
- ✅ [docs/LESSONS_LEARNED.md](docs/LESSONS_LEARNED.md) — Lições aprendidas
- ✅ [.github/copilot-instructions.md](.github/copilot-instructions.md) — Instruções do Copilot
- ✅ [CHANGELOG.md](CHANGELOG.md) — Keep a Changelog

### Documentação Técnica
- ✅ [docs/BINANCE_SDK_INTEGRATION.md](docs/BINANCE_SDK_INTEGRATION.md) — Integração Binance
- ✅ [docs/CROSS_MARGIN_FIXES.md](docs/CROSS_MARGIN_FIXES.md) — Correções cross margin
- ✅ [docs/LAYER_IMPLEMENTATION.md](docs/LAYER_IMPLEMENTATION.md) — Implementação de camadas

### Configuração
- ✅ [config/symbols.py](config/symbols.py) — Símbolos suportados (16 pares)
- ✅ [config/execution_config.py](config/execution_config.py) — Parâmetros de execução
- ✅ [playbooks/](playbooks/) — Playbooks específicos por moeda (16 playbooks)

## ✅ Checklist de Sincronização

### Rev. v0.2.1 (20/02/2026) — Administração de Novos Pares

**Início da Tarefa:** Adicionar 9 pares USDT em Profit Guardian Mode

#### Itens Concluídos

- ✅ **config/symbols.py**: Adicionados 4 novos símbolos
  - TWTUSDT (β=2.0, mid_cap_utility)
  - LINKUSDT (β=2.3, mid_cap_oracle_infra)
  - OGNUSDT (β=3.2, low_cap_commerce)
  - IMXUSDT (β=3.0, low_cap_l2_nft)
  - Status anterior: GTC, HYPER, 1000BONK, FIL, POLYX já existentes

- ✅ **playbooks/**: Criados 4 novos playbooks
  - twt_playbook.py (TWT — Wallet ecosystem)
  - link_playbook.py (LINK — Oracle infrastructure)
  - ogn_playbook.py (OGN — Commerce protocol, CONSERVADOR)
  - imx_playbook.py (IMX — Layer 2 NFT/Gaming)

- ✅ **playbooks/__init__.py**: Registrados imports para novos playbooks

- ✅ **config/execution_config.py**: Auto-sincronizado via ALL_SYMBOLS

- ✅ **README.md**: Atualizado com 16 pares categorizados

- ✅ **test_admin_9pares.py**: Script de validação criado e testado
  - Status: 36/36 validações OK

#### Sincronização de Documentação Relacionada

- ⏳ [docs/ROADMAP.md](docs/ROADMAP.md) — Aguarda revisão de status atual
- ⏳ [docs/RELEASES.md](docs/RELEASES.md) — Aguarda atualização de v0.2.1
- ⏳ [docs/FEATURES.md](docs/FEATURES.md) — Aguarda atualização de features completadas
- ⏳ [docs/TRACKER.md](docs/TRACKER.md) — Aguarda atualização de task completion
- ⏳ [CHANGELOG.md](CHANGELOG.md) — Aguarda entry para v0.2.1

## 🔄 Protocolo de Sincronização Obrigatória

Toda vez que um documento for alterado, o fluxo abaixo `DEVE` ser executado:

### 1. Identificar Mudança

**Quando:** Arquivo alterado em:
- `config/symbols.py` ou `config/execution_config.py`
- `playbooks/**/*.py`
- `README.md`
- Qualquer arquivo em `docs/`

### 2. Propagar Mudança

Se alterou `symbols.py` → verificar:
- [ ] Playbook correspondente existe?
- [ ] Registrado em `playbooks/__init__.py`?
- [ ] README reflete a nova moeda?
- [ ] FEATURES.md atualizado?
- [ ] TRACKER.md atualizado?

Se alterou `playbooks/*.py` → verificar:
- [ ] Symbol configurado em `symbols.py`?
- [ ] Registrado em `playbooks/__init__.py`?
- [ ] Teste de validação passa?
- [ ] README reflete a configuração?

Se alterou `README.md` → verificar:
- [ ] Seção de moedas sincronizada?
- [ ] Roadmap está atualizado?
- [ ] Versão está correta?
- [ ] Links internos apontam para arquivos corretos?

### 3. Atualizar Rastreamento

- [ ] Adicionar entrada neste arquivo (SYNCHRONIZATION.md)
- [ ] Indicar qraise de sincronização: ✅ Completo / ⏳ Pendente / ⚠️ Parcial
- [ ] Listar todos os documentos impactados
- [ ] Incluir timestamp

### 4. Documentar Automaticamente

Adicione comentário ao commit:

```
[SYNC] Documento: X foi alterado
Documentos impactados:
- symbol.py (✅ sincronizado)
- playbooks/__init__.py (✅ sincronizado)
- README.md (✅ sincronizado)
- SYNCHRONIZATION.md (✅ rastreado)

Status geral: ✅ Sincronização completa
```

## 📊 Matriz de Interdependências

```
config/symbols.py
    ├── Depende de: Nada (fonte de verdade)
    └── Impacta:
        ├── playbooks/*.py (cada símbolo precisa de playbook)
        ├── playbooks/__init__.py (registro de imports)
        ├── config/execution_config.py (auto-sync via ALL_SYMBOLS)
        ├── README.md (listagem de moedas)
        └── test_admin_*.py (validação)

playbooks/*.py
    ├── Depende de: config/symbols.py (símbolo deve existir)
    └── Impacta:
        ├── playbooks/__init__.py (deve estar registrado)
        ├── agent/environment.py (carrega playbook)
        ├── test_admin_*.py (validação)
        └── README.md (listagem de estratégias)

README.md
    ├── Depende de: Todos os acima (reflete estado)
    └── Impacta:
        ├── Documentação externa/GitHub
        └── Expectativas de usuário

docs/*
    ├── Depende de: README.md, config/, playbooks/
    └── Impacta:
        ├── Compreensão técnica
        ├── Onboarding
        └── Governance
```

## 🚨 Regras Críticas de Sincronização

### ❌ NÃO Faça

1. **Não adicione símbolo sem playbook**
   - Se `XYZUSDT` foi adicionado em `symbols.py`, DEVE ter `xyz_playbook.py`

2. **Não crie playbook sem símbolo**
   - Se `abc_playbook.py` foi criado, DEVE estar em `symbols.py`

3. **Não deixe playbooks não registrados**
   - Se novo playbook foi criado, DEVE estar em `playbooks/__init__.py`

4. **Não atualize README sem sincronizar docs/**
   - Se versão mudou em README, TODAS as docs devem refletir

5. **Não faça alterações sem rastrear aqui**
   - Este arquivo DEVE ser atualizado em CADA ciclo de mudança

### ✅ SEMPRE Faça

1. Quando adicionar símbolo:
   ```
   1. Adicionar em config/symbols.py
   2. Criar playbook correspondente
   3. Registrar em playbooks/__init__.py
   4. Criar teste de validação
   5. Atualizar README
   6. Atualizar este arquivo (SYNCHRONIZATION.md)
   ```

2. Quando alterar funcionalidade crítica:
   ```
   1. Atualizar código
   2. Atualizar tests/
   3. Atualizar docs/ relevante
   4. Atualizar README se impactar usuário
   5. Atualizar CHANGELOG.md
   6. Atualizar este arquivo
   ```

3. Antes de fazer commit:
   ```
   1. Rodar pytest
   2. Validar sincronização (checklist acima)
   3. Revisar documentação impactada
   4. Adicionar [SYNC] tag ao commit message
   ```

## 📈 Histórico de Sincronizações

### Rev. v0.3 (20/02/2026 — IN PROGRESS)

**Mudança Principal:** Feature F-08 — Pipeline de dados para treinamento

| Artefato | Status | Data | Notas |
|----------|--------|------|-------|
| data/data_loader.py | ✅ | 20/02 | Implementado (Engenheiro Senior) |
| validate_training_data.py | ✅ | 20/02 | Validações ML (Especialista ML) |
| tests/test_data_loader.py | ✅ | 20/02 | 8 testes unitários |
| docs/FEATURES.md | ✅ | 20/02 | F-08 marcado como IN PROGRESS |
| requirements.txt | ✅ | 20/02 | Adicionados sklearn, scipy |
| README.md | ⏳ | — | Pendente: seção v0.3 |
| docs/ROADMAP.md | ⏳ | — | Pendente: timeline v0.3 |
| docs/RELEASES.md | ⏳ | — | Pendente: descrição v0.3 |
| CHANGELOG.md | ⏳ | — | Pendente: entry v0.3 |

**Transparência Operacional:**
- ✅ F-08 isolado (zero imports em main.py)
- ✅ Módulo core validado (main.py syntax OK)
- ✅ Dependências de F-08 em requirements.txt
- ✅ iniciar.bat não impactado
- ✅ Operação automática funciona sem mudanças

### Rev. v0.2.1 (20/02/2026 — CONCLUÍDO)

**Mudança Principal:** Administração de 9 pares USDT em Profit Guardian Mode

| Artefato | Status | Data | Notas |
|----------|--------|------|-------|
| config/symbols.py (TWT, LINK, OGN, IMX) | ✅ | 20/02 | 4 novos símbolos |
| playbooks/*.py (4 novos) | ✅ | 20/02 | Todos criados |
| playbooks/__init__.py | ✅ | 20/02 | Imports registrados |
| README.md | ✅ | 20/02 | 16 pares listados |
| test_admin_9pares.py | ✅ | 20/02 | Validação 36/36 OK |
| docs/ROADMAP.md | ⏳ | — | Pendente revisão |
| docs/RELEASES.md | ⏳ | — | Pendente atualização |
| docs/FEATURES.md | ⏳ | — | Pendente atualização |
| CHANGELOG.md | ⏳ | — | Pendente entry |

## 🔔 Notificações Obrigatórias

Quando qualquer item acima mover de ⏳ para ✅, notificar:
1. Commit message deve conter `[SYNC] Complete: <documento>`
2. Atualizar esta tabela
3. Revisar documentação relacionada

## 📞 Contato & Escalação

Se encontrar inconsistência:
1. Abra issue com tag `[SYNC]`
2. Descreva qual documento está fora de sincronia
3. Sugira a mudança necessária
4. Reference este arquivo (SYNCHRONIZATION.md)

---

**Mantido pelo:** GitHub Copilot + Agente Autônomo
**Frequência de Revisão:** A cada mudança documentada
**Próxima Revisão Esperada:** 25/02/2026 (fim da Rev. v0.2.1)
