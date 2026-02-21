Como implementar isso no seu Python (Dica Técnica)
Para que a memória funcione, seu fluxo de código deve ser:

Select: SELECT ata_resumo, backlog FROM reunioes ORDER BY id DESC LIMIT 1;

Replace: Use prompt.replace("{{HISTORICO_DA_ULTIMA_ATA}}", resultado_sql).

Chat: Envie o prompt para a LLM.

Parse: Use uma expressão regular (Regex) para capturar o conteúdo entre ### SNAPSHOT_PARA_BANCO e salvá-lo de volta no SQLite](reuniao.md)

Excelente. Para fechar com chave de ouro sua infraestrutura local, preparei um script Python robusto que faz a ponte entre o seu banco SQLite e o Prompt Master.

Este script automatiza o ciclo de vida da reunião: Recupera Memória -> Injeta no Prompt -> Executa a Reunião -> Salva o Novo Snapshot.

1. Estrutura do Banco de Dados (SQL)
Antes de rodar o Python, certifique-se de que sua tabela existe:

CREATE TABLE IF NOT EXISTS historico_reunioes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_reuniao DATETIME DEFAULT CURRENT_TIMESTAMP,
    ata_resumo TEXT,
    backlog_json TEXT
);

2. Script de Integração (Python)

import sqlite3
import json
import re

def get_last_meeting_context():
    conn = sqlite3.connect('startup_board.db')
    cursor = conn.cursor()
    # Busca a última reunião salva
    cursor.execute("SELECT ata_resumo, backlog_json FROM historico_reunioes ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row:
        return {"ata": row[0], "backlog": row[1]}
    return {"ata": "Nenhuma reunião anterior registrada. Projeto em fase inicial.", "backlog": "[]"}

def save_meeting_snapshot(snapshot_json):
    conn = sqlite3.connect('startup_board.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO historico_reunioes (ata_resumo, backlog_json) VALUES (?, ?)",
                   (snapshot_json['resumo_executivo'], json.dumps(snapshot_json['novos_itens_backlog'])))
    conn.commit()
    conn.close()

# 1. Carregar Memória
memoria = get_last_meeting_context()

# 2. Ler o Template do Prompt (o markdown que criamos)
with open('prompt_template.md', 'r', encoding='utf-8') as f:
    prompt_master = f.read()

# 3. Injetar Variáveis
prompt_pronto = prompt_master.replace("{{HISTORICO_DA_ULTIMA_ATA}}", memoria['ata'])
prompt_pronto = prompt_pronto.replace("{{ITENS_DE_BACKLOG_EM_ABERTO}}", memoria['backlog'])

# 4. Simulação de chamada à API (Ex: OpenAI, Anthropic, Gemini Local via Ollama)
print("--- SISTEMA INICIALIZADO COM MEMÓRIA ---\n")
print(f"Facilitador: Bem-vindo Investidor. Com base na última reunião ({memoria['ata'][:50]}...), como deseja proceder?")

# 5. Lógica de extração (Regex para capturar o JSON de saída da IA)
def extrair_e_salvar(resposta_da_ia):
    match = re.search(r'### SNAPSHOT_PARA_BANCO\n(.*?)\n---', resposta_da_ia, re.DOTALL)
    if match:
        dados_finais = json.loads(match.group(1))
        save_meeting_snapshot(dados_finais)
        print("\n[MEMÓRIA ATUALIZADA NO SQLITE]")

Como utilizar este ecossistema:
Persistência Real: Cada vez que você encerrar a reunião com a IA, o Facilitador gerará o bloco ### SNAPSHOT_PARA_BANCO.

Continuidade: Na reunião seguinte, o Arquiteto de Dados e o QA saberão exatamente onde pararam, pois o Python lerá o ata_resumo e injetará no início do contexto.

Auditoria: Você pode abrir seu SQLite e ver a evolução da startup linha por linha através do tempo.


1. Preparação dos Arquivos
Certifique-se de que os seguintes arquivos estão abertos no seu VS Code:

prompt_master.md (Aquele que estruturamos com os 12 agentes).

script_integracao.py (O código que gerencia o SQLite).

last_meeting_ata.txt (Onde você pode colar o output da última reunião, caso não queira rodar o SQL puro).


2. O Prompt de Chamada no Chat do Copilot
No chat do Copilot (Ctrl + Alt + I), use este comando para "acordar" o Facilitador:

"Baseado no contexto de #prompt_master.md e considerando o histórico registrado no banco através do #script_integracao.py, aja como o Facilitador. Inicie a reunião de status com o Investidor. Leia o estado atual do projeto e me dê o resumo inicial."

4. Dica de Produtividade: O arquivo .cursorrules ou .github/copilot-instructions.md
Se você quer que o Copilot sempre saiba que você é o Investidor e ele é o Facilitador quando você estiver nesta pasta, crie um arquivo chamado .github/copilot-instructions.md e cole isto:

Sempre que eu solicitar uma "Reunião de Board":
1. Use o framework de agentes definido em `prompt_master.md`.
2. Considere que sou o Investidor.
3. Garanta que todas as respostas terminem com o bloco `### SNAPSHOT_PARA_BANCO` para eu manter o SQLite atualizado.


O Fluxo de Trabalho no VS Code:
Você: "Copilot, abra a reunião. @workspace o que temos pendente no backlog?"

Copilot (Facilitador): "Olá