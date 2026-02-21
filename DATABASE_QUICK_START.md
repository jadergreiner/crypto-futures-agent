"""
GUIA RÁPIDO: Importar e usar database_manager.py em outros arquivos

Este documento mostra como integrar o gerenciador de banco de dados
em módulos de orquestração de reuniões ou agentes autônomos.
"""

# ════════════════════════════════════════════════════════════════
# PADRÃO 1: USO SIMPLES (Singleton)
# ════════════════════════════════════════════════════════════════

from database_manager import get_database_manager

def minha_funcao_de_reuniao():
    """Exemplo de função que usa o banco de dados."""

    # Obter instância (singleton)
    db = get_database_manager()

    # Inicializar se necessário
    db.initialize_db()

    # Recuperar contexto anterior
    contexto = db.get_last_context()
    print(contexto)


# ════════════════════════════════════════════════════════════════
# PADRÃO 2: SALVAR SNAPSHOT APÓS REUNIÃO
# ════════════════════════════════════════════════════════════════

from database_manager import get_database_manager

def salvar_decisoes_reuniao(resumo: str, decisoes: dict, backlog: list):
    """Salva resultado de reunião no banco de dados."""

    db = get_database_manager()
    db.initialize_db()

    meeting_id = db.save_snapshot(
        executive_summary=resumo,
        decisions=decisoes,
        backlog_items=backlog
    )

    if meeting_id:
        print(f"Reunião salva com ID: {meeting_id}")
    else:
        print("Erro ao salvar reunião")


# ════════════════════════════════════════════════════════════════
# PADRÃO 3: RECUPERAR E INJETAR EM PROMPT
# ════════════════════════════════════════════════════════════════

from database_manager import get_database_manager

def gerar_prompt_com_contexto() -> str:
    """Gera prompt para IA com contexto histórico injetado."""

    db = get_database_manager()
    db.initialize_db()

    # Recuperar contexto automaticamente formatado
    contexto_historico = db.get_last_context()

    # Montar prompt
    prompt = f"""
Você é um especialista em trading e ML.

{contexto_historico}

Baseado no histórico acima, qual é sua recomendação para a reunião de hoje?
    """

    return prompt


# ════════════════════════════════════════════════════════════════
# PADRÃO 4: GERENCIAR BACKLOG
# ════════════════════════════════════════════════════════════════

from database_manager import get_database_manager

def gerenciar_backlog():
    """Exemplos de operações com backlog."""

    db = get_database_manager()
    db.initialize_db()

    # 1. Recuperar apenas itens abertos
    itens_abertos = db.get_backlog(status_filter="OPEN")
    print(f"Itens abertos: {len(itens_abertos)}")

    # 2. Atualizar status de um item
    db.update_backlog_status(item_id=1, novo_status="IN_PROGRESS")

    # 3. Recuperar todos os itens
    todos_itens = db.get_backlog()
    for item in todos_itens:
        print(f"  {item['task']} - {item['status']}")


# ════════════════════════════════════════════════════════════════
# PADRÃO 5: EM CLASSE (Integração com Agent)
# ════════════════════════════════════════════════════════════════

from database_manager import get_database_manager

class OrquestradorDeReunioes:
    """Orquestrador que usa memória de longo prazo."""

    def __init__(self):
        self.db = get_database_manager()
        self.db.initialize_db()

    def dar_inicio_a_reuniao(self):
        """Inicia reunião com contexto do histórico."""

        # Recuperar contexto
        contexto = self.db.get_last_context()
        print(f"Iniciando reunião com contexto histórico...")
        print(contexto)

    def finalizando_reuniao(self, resumo: str, decisoes: dict, backlog: list):
        """Finaliza reunião salvando decisões."""

        meeting_id = self.db.save_snapshot(
            executive_summary=resumo,
            decisions=decisoes,
            backlog_items=backlog
        )
        print(f"Reunião finalizada e salva (ID: {meeting_id})")


# ════════════════════════════════════════════════════════════════
# EXEMPLO DE INTEGRAÇÃO COMPLETA
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # Criar orquestrador
    orquestrador = OrquestradorDeReunioes()

    # PASSO 1: Iniciar reunião (usa contexto anterior)
    print("=" * 70)
    print("INICIANDO REUNIÃO COM CONTEXTO HISTÓRICO")
    print("=" * 70)
    orquestrador.dar_inicio_a_reuniao()

    # PASSO 2: Simular discussão e decisões
    print("\n" + "=" * 70)
    print("REUNIÃO EM ANDAMENTO...")
    print("=" * 70)

    # Aqui aconteceria a lógica de IA/agentes
    resumo = "Reunião de estratégia: Análise de Q1 2026"
    decisoes = {
        "Ação 1": "Implementar novo modelo de risk",
        "Ação 2": "Auditar hedge strategies"
    }
    backlog_novo = [
        {
            "task": "Treinar modelo PPO",
            "owner": "ML Engineer",
            "priority": "HIGH",
            "status": "OPEN"
        }
    ]

    # PASSO 3: Finalizar reunião (salva snapshot)
    print("\nFINALIZANDO REUNIÃO...")
    orquestrador.finalizando_reuniao(resumo, decisoes, backlog_novo)

    print("\n✅ Integração completa funcionando!")


# ════════════════════════════════════════════════════════════════
# ESTRUTURA DO BANCO DE DADOS (Gerado automaticamente)
# ════════════════════════════════════════════════════════════════

"""
TABELA: meetings
─────────────────────────────────────────────────────
  id (INT PRIMARY KEY AUTO_INCREMENT)
  date (TIMESTAMP)                    — Quando a reunião ocorreu
  executive_summary (TEXT)            — Resumo em linguagem natural
  decisions (JSON)                    — Decisões em formato JSON
  created_at (TIMESTAMP)              — Quando foi registrado
  updated_at (TIMESTAMP)              — Última atualização

TABELA: backlog
─────────────────────────────────────────────────────
  id (INT PRIMARY KEY AUTO_INCREMENT)
  task (TEXT)                         — Descrição da tarefa
  owner (TEXT)                        — Responsável (opcional)
  priority (TEXT)                     — LOW, MEDIUM, HIGH, CRITICAL
  status (TEXT)                       — OPEN, IN_PROGRESS, DONE, BLOCKED
  meeting_id (INT FOREIGN KEY)        — Referência para meetings
  created_at (TIMESTAMP)              — Quando foi criado
  updated_at (TIMESTAMP)              — Última atualização

ÍNDICES (para otimizar queries):
  idx_meetings_date                   — Busca rápida por data
  idx_backlog_meeting_id              — Busca rápida por reunião
  idx_backlog_status                  — Busca rápida por status
"""

# ════════════════════════════════════════════════════════════════
# ARQUIVOS CRIADOS NESTA ENTREGA
# ════════════════════════════════════════════════════════════════

"""
✅ database_manager.py
   - Classe DatabaseManager com todas as funcionalidades
   - Factory get_database_manager() para Singleton
   - Suporte completo a ACID (com context managers)
   - Tratamento robusto de erros

✅ exemplo_database.py
   - Exemplos funcionais de uso
   - Demonstración de injeção em prompts
   - Código pronto para copiar-colar

✅ DATABASE_QUICK_START.md (este arquivo)
   - Padrões de integração
   - Exemplos de cada função
   - Estrutura do banco de dados
"""
