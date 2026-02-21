"""
GUIA DE USO: ORQUESTRADOR DE REUNIÕES (MAIN_ORCHESTRATOR.PY)

Este documento explica como usar o script main_orchestrator.py de forma
prática e efetiva para gerenciar reuniões de estratégia com o board de
especialistas em Crypto e ML.
"""

# ═══════════════════════════════════════════════════════════════════════════
# 1. INICIAR O ORQUESTRADOR
# ═══════════════════════════════════════════════════════════════════════════

"""
No terminal, navegue até o diretório raiz do projeto e execute:

$ python main_orchestrator.py

Output esperado:
──────────────────────────────────────────────────────────────────────────
🎯 CRYPTO FUTURES AGENT — ORQUESTRADOR DE REUNIÕES
══════════════════════════════════════════════════════════════════════════

✅ Orquestrador inicializado com sucesso
📁 Template carregado de: prompts/prompt_master.md
💾 Banco de dados: reunioes.db

======================================================================
🚀 ORQUESTRADOR DE REUNIÃO INICIADO
======================================================================

📄 CONTEXTO CARREGADO:
────────────────────────────────────────────────────────────────────────────
[Contexto da última reunião injetado aqui...]
────────────────────────────────────────────────────────────────────────────

💬 INICIANDO INTERAÇÃO
   Digite suas perguntas/observações como INVESTIDOR
   Digite 'sair' ou 'encerrar' para finalizar a reunião
   Digite 'historico' para ver todo o histórico de conversas
======================================================================

👤 Investidor >
"""

# ═══════════════════════════════════════════════════════════════════════════
# 2. DURANTE A REUNIÃO
# ═══════════════════════════════════════════════════════════════════════════

"""
Uma vez dentro do loop interativo, você pode:

A) FAZER PERGUNTAS COMO INVESTIDOR:
─────────────────────────────────────

👤 Investidor > Qual é o status do backlog?

🤖 Facilitador:
O backlog atual tem 4 itens críticos:
1. Auditar modelo de risk (HIGH) - Em progresso
2. Implementar hedge em ETH (CRITICAL) - Aberto
[...]

✅ [Sessão Persistida com Sucesso] (ID: 1)

A resposta é simulada, então será uma das respostas pré-configuradas
baseada em palavras-chave. Em produção, isso seria uma chamada real
à API (OpenAI, Anthropic, etc).

B) PALAVRAS-CHAVE SUPORTADAS (que geram snapshots automaticamente):
─────────────────────────────────────────────────────────────────

"backlog"    → Retorna status de backlog + snapshot JSON
"risco"      → Retorna análise de risco + snapshot JSON
"decisao"    → Retorna decisões tomadas + snapshot JSON

Exemplo:
👤 Investidor > Todo: qual é o status de risco atual?

[Resposta detalhada com snapshot JSON que será automaticamente capturado]

C) COMANDO: VISUALIZAR HISTÓRICO
─────────────────────────────────────────────────────────────────

👤 Investidor > historico

Output:
======================================================================
📜 HISTÓRICO DE CONVERSAS
======================================================================

[1] Investidor: Qual é o status do backlog?
[2] Facilitador: O backlog atual tem 4 itens críticos...
[3] Investidor: E qual é o nível de risco?
[4] Facilitador: O risco sistêmico está elevado...

======================================================================

D) COMANDO: ENCERRAR E PERSISTIR
─────────────────────────────────────────────────────────────────

👤 Investidor > sair

ou

👤 Investidor > encerrar

Output:
⏹️ Encerrando reunião...

🔍 GERANDO SNAPSHOT FINAL ANTES DE ENCERRAR...
════════════════════════════════════════════════════════════════

📨 [Enviando para Facilitador...]

Você é o Facilitador encerrando uma reunião de estratégia.
Por favor, forneça o SNAPSHOT FINAL...

🤖 [Simulando resposta do Facilitador]

[Resposta com snapshot JSON será exibida]

✅ [Sessão Persistida com Sucesso] (ID: 2)
✅ Reunião encerrada e dados persistidos com sucesso!

[Programa encerrado]
"""

# ═══════════════════════════════════════════════════════════════════════════
# 3. ARQUITETURA E arquivos IMPORTANTES
# ═══════════════════════════════════════════════════════════════════════════

"""
FLUXO DE DADOS:

[prompts/prompt_master.md] ← Template com placeholders
        ↓
[main_orchestrator.py] ← Carrega template
        ↓
[database_manager.py] → get_last_context() ← Recupera histórico
        ↓
[reunioes.db] ← Contexto histórico
        ↓
[Prompt Final] ← Com histórico injetado
        ↓
[Loop Interativo] ← Usuário digita perguntas
        ↓
[Parse Regex] ← Extrai JSON do snapshot
        ↓
[save_snapshot()] ← Salva no banco de dados
        ↓
[reunioes.db] ← Dados persistidos


ARQUIVOS CRIADOS/MODIFICADOS:

✅ main_orchestrator.py (670 linhas)
   - Classe MainOrchestrator
   - Funções: parse_ai_output(), salvar_snapshot(), loop_interacao()
   - Gerencia ciclo completo de reunião

✅ prompts/prompt_master.md
   - Template com {{HISTORICO_DA_ULTIMA_ATA}}
   - Template com {{ITENS_DE_BACKLOG_EM_ABERTO}}
   - Instruções para Facilitador incluir blocos de snapshot

✅ teste_orchestrator.py
   - 6 testes funcionalidades críticas
   - Todos os testes PASSAM ✅

✅ database_manager.py (criado anteriormente)
   - Persistência SQLite
   - Integridade ACID garantida
"""

# ═══════════════════════════════════════════════════════════════════════════
# 4. ENTENDENDO O PARSE DE JSON (parse_ai_output)
# ═══════════════════════════════════════════════════════════════════════════

"""
O orquestrador captura JSON automaticamente usando REGEX:

PADRÃO:
────────────────────────────────────────────────────────────────────────────
pattern = r"### SNAPSHOT_PARA_BANCO\s*\n(.*?)\n---"

FUNCIONA COM:

✅ VÁLIDO:
### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "Reunião aprovada",
  "decisions": ["D1"],
  "backlog_items": []
}
---

✅ COM ESPAÇAMENTO (funciona):
###   SNAPSHOT_PARA_BANCO

{...JSON...}

---

❌ INVÁLIDO (não funciona):
### SNAPSHOT_PARA_BANCO {...JSON...} ---
[Tudo em uma linha]

❌ INVÁLIDO (JSON malformado):
### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "teste"
  "decisions": []      ← Falta comma aqui!
}
---

SE JSON FOR DETECTADO MAS INVÁLIDO:
─────────────────────────────────────────────────────────────────────────────
❌ ERRO ao fazer parse do JSON: Expecting ',' delimiter...
JSON inválido: {...primeiros 200 caracteres...}

NESTE CASO:
- O snapshot NÃO será salvo
- A conversa continua
- Edite o JSON e tente novamente
"""

# ═══════════════════════════════════════════════════════════════════════════
# 5. SALVANDO DADOS NO BANCO (DATABASE)
# ═══════════════════════════════════════════════════════════════════════════

"""
CADA SNAPSHOT SALVO CONTÉM:

📊 Tabela: meetings
──────────────────────────────────────────────────────────────────────────────
id                  → Identificador único da reunião
date                → Timestamp da reunião (AUTO)
executive_summary   → String com resumo (ex: "Reunião aprovada")
decisions           → JSON array com decisões
created_at          → Timestamp de criação
updated_at          → Timestamp de atualização

📊 Tabela: backlog
──────────────────────────────────────────────────────────────────────────────
id                  → Identificador único do item
task                → Descrição da tarefa
owner               → Responsável (pode ser NULL)
priority            → LOW, MEDIUM, HIGH, CRITICAL
status              → OPEN, IN_PROGRESS, DONE, BLOCKED
meeting_id          → FK referenciando meetings.id
created_at          → Timestamp de criação
updated_at          → Timestamp de atualização


EXEMPLO DE SNAPSHOT CAPTURADO:
──────────────────────────────────────────────────────────────────────────────

### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "Reunião de estratégia de fevereiro concluída",
  "decisions": [
    "Aumentar alavancagem em BTC para 3x",
    "Reduzir exposição em ALT coins",
    "Auditar modelo de reward function"
  ],
  "backlog_items": [
    {
      "task": "Auditar modelo de risk management",
      "owner": "Engenheiro de Risk",
      "priority": "HIGH",
      "status": "IN_PROGRESS"
    },
    {
      "task": "Implementar hedge em ETH",
      "owner": "Risk Manager",
      "priority": "CRITICAL",
      "status": "OPEN"
    }
  ]
}
---

O QUE ACONTECE QUANDO SALVO:
✅ [Sessão Persistida com Sucesso] (ID: 1)

- ID 1 = Nova reunião registrada
- executive_summary é salvo na coluna executive_summary
- Cada item em decisions é referenciado
- Cada item em backlog_items é inserido com meeting_id = 1


PRÓXIMA REUNIÃO:
─────────────────────────────────────────────────────────────────────────────

Quando você executa main_orchestrator.py novamente:

1. database_manager.get_last_context() busca meeting_id = 1
2. Esta reunião é formatada com todo seu histórico
3. Os backlog_items daquela reunião aparecem como "pendentes"
4. O prompt é injetado no prompt_master.md

CONTINUIDADE GARANTIDA! 🎯
"""

# ═══════════════════════════════════════════════════════════════════════════
# 6. PERSONALIZANDO RESPOSTAS DO FACILITADOR
# ═══════════════════════════════════════════════════════════════════════════

"""
LOCALIZANDO O CÓDIGO (main_orchestrator.py, linha ~580):
───────────────────────────────────────────────────────────────

def _simular_resposta_facilitador(self, pergunta_usuario: str) -> str:
    # ... código ...
    respostas_por_palavra = {
        "backlog": "← RESPOSTA PARA BACKLOG",
        "risco": "← RESPOSTA PARA RISCO",
        "decisao": "← RESPOSTA PARA DECISÃO",
    }


PARA ADICIONAR NOVA PALAVRA-CHAVE:
──────────────────────────────────────────────────────────────────────

Abra main_orchestrator.py e encontre respostas_por_palavra.

Adicione uma nova entrada:

respostas_por_palavra = {
    "backlog": "...",
    "risco": "...",
    "performance": """
Relatório de Performance:

Data: 2026-02-21
Retorno: +12.5% no mês
Sharpe: 0.06
Drawdown: 17.24%

...

### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "Performance revisada",
  "decisions": [...],
  "backlog_items": [...]
}
---
    """,  ← ADICIONE VÍRGULA AQUI
}


EM PRODUÇÃO (com API Real):
──────────────────────────────────────────────────────────────────────

Substitua toda a função _simular_resposta_facilitador():

async def _simular_resposta_facilitador(self, pergunta_usuario: str):
    '''Chamada real à OpenAI/Anthropic/etc'''
    
    resposta = await openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": self.prompt_template},
            {"role": "user", "content": pergunta_usuario}
        ]
    )
    
    return resposta.choices[0].message['content']
"""

# ═══════════════════════════════════════════════════════════════════════════
# 7. INTEGRANDO COM COPILOT/IA REAL (Dicas)
# ═══════════════════════════════════════════════════════════════════════════

"""
OPÇÃO 1: OpenAI GPT-4 (RECOMENDADO)
──────────────────────────────────────────────────────────────────────

pip install openai

import openai

async def _simular_resposta_facilitador(self, pergunta_usuario: str):
    response = await openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": self.prompt_template},
            {"role": "user", "content": pergunta_usuario}
        ],
        temperature=0.7
    )
    return response.choices[0].message['content']


OPÇÃO 2: Anthropic Claude
──────────────────────────────────────────────────────────────────────

pip install anthropic

from anthropic import Anthropic

client = Anthropic()

def _simular_resposta_facilitador(self, pergunta_usuario: str):
    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        system_prompt=self.prompt_template,
        messages=[
            {"role": "user", "content": pergunta_usuario}
        ]
    )
    return message.content[0].text


OPÇÃO 3: Ollama Local (Gratuito, Privacy)
──────────────────────────────────────────────────────────────────────

pip install ollama

from ollama import Client

client = Client(host='http://localhost:11434')

def _simular_resposta_facilitador(self, pergunta_usuario: str):
    response = client.generate(
        model='mistral',
        prompt=f"{self.prompt_template}\n\nInvestidor: {pergunta_usuario}",
        stream=False
    )
    return response['response']
"""

# ═══════════════════════════════════════════════════════════════════════════
# 8. TROUBLESHOOTING
# ═══════════════════════════════════════════════════════════════════════════

"""
PROBLEMA 1: "FileNotFoundError: Template não encontrado"
────────────────────────────────────────────────────────────────────────────
SOLUÇÃO:
- Certifique-se que prompts/prompt_master.md existe
- Verifique caminho: ls prompts/prompt_master.md
- Se não existe: crie usando o exemplo fornecido


PROBLEMA 2: "Banco de dados locked"
────────────────────────────────────────────────────────────────────────────
SOLUÇÃO:
- Feche outras instâncias do programa
- Remova arquivo .db-journal se existir: rm reunioes.db-journal
- Tente novamente


PROBLEMA 3: "JSON não está sendo extraído"
────────────────────────────────────────────────────────────────────────────
VERIFICAR:
- A resposta contém exatamente: ### SNAPSHOT_PARA_BANCO
- JSON está bem formatado (use jsonlint.com para validar)
- Bloco termina com: ---
- Sem caracteres especiais ou encoding errado


PROBLEMA 4: Snapshot está sendo salvo mas não aparece em próxima reunião
────────────────────────────────────────────────────────────────────────────
SOLUÇÃO:
- Abra reunioes.db com sqlite3: sqlite3 reunioes.db
- Query: SELECT * FROM meetings;
- Verifique se dados estão lá
- Se vazio: cheque se salvar_snapshot() retornou True


PROBLEMA 5: Placeholders {{}} ainda aparecem no prompt
────────────────────────────────────────────────────────────────────────────
SOLUÇÃO:
- Certifique-se que placeholder é exatamente: {{HISTORICO_DA_ULTIMA_ATA}}
- Sem espaços extras
- Verifique encoding UTF-8 do arquivo
"""

# ═══════════════════════════════════════════════════════════════════════════
# 9. EXEMPLOS DE USO COMPLETO
# ═══════════════════════════════════════════════════════════════════════════

"""
CENÁRIO: Primeira Reunião

$ python main_orchestrator.py

[Orquestrador inicializado]

👤 Investidor > Quais são nossas estratégias para BTC nesta semana?

🤖 Facilitador: [Resposta simulada genérica]

👤 Investidor > Qual o status do backlog?

🤖 Facilitador: O backlog tem 4 itens...

✅ [Sessão Persistida com Sucesso] (ID: 1)

👤 Investidor > encerrar

🔍 GERANDO SNAPSHOT FINAL...
[Snapshot final capturado e salvo]

✅ Reunião encerrada e dados persistidos com sucesso!


CENÁRIO: Segunda Reunião (24h depois)

$ python main_orchestrator.py

[Orquestrador carrega contexto...]

📄 CONTEXTO CARREGADO:
Data: 21 de Fevereiro de 2026
Resumo: "Reunião de estratégia BTC aprovada"
Backlog Pendente:
  - Auditar modelo (HIGH) - IN_PROGRESS
  - Implementar hedge (CRITICAL) - OPEN
  ...

👤 Investidor > Como está o progresso da auditoria?

🤖 Facilitador: Com base no histórico anterior, a auditoria...

[Conta com contexto da reunião anterior!]
"""

# ═══════════════════════════════════════════════════════════════════════════
# 10. PRÓXIMOS PASSOS RECOMENDADOS
# ═══════════════════════════════════════════════════════════════════════════

"""
✅ IMEDIATO (hoje):
1. Executar: python main_orchestrator.py
2. Testar com perguntas: "backlog", "risco", "decisao"
3. Encerrar e verificar se dados foram salvos

✅ CURTO PRAZO (semana):
1. Integrar com OpenAI/Anthropic (substituir _simular_resposta_facilitador)
2. Testar com dados reais de reuniões
3. Ajustar respostas para seu contexto específico

✅ MÉDIO PRAZO:
1. Adicionar logging detalhado de decisões
2. Implementar webhooks para notificação de decisões críticas
3. Dashboard para visualizar histórico de reuniões

✅ LONGO PRAZO:
1. Migrar banco SQLite para PostgreSQL
2. Implementar controle de acesso (permissões por usuário)
3. Integrar com Slack/Teams para notificações em tempo real
"""
