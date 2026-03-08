"""
Exemplo de Uso: Recuperar Contexto de Reuniões Anteriores

Este script demonstra como usar o DatabaseManager para:
1. Inicializar o banco de dados
2. Salvar um snapshot de reunião com decisões
3. Recuperar o contexto formatado para injeção em prompt
"""

from database_manager import get_database_manager


def exemplo_basico():
    """Demonstra uso básico do gerenciador de banco de dados."""

    # 1. Obter instância do gerenciador
    db = get_database_manager(db_path="reunioes.db")

    # 2. Inicializar banco de dados
    sucesso = db.initialize_db()
    if not sucesso:
        print("Erro ao inicializar banco de dados")
        return

    print("✅ Banco de dados inicializado com sucesso\n")

    # 3. Salvar snapshot de reunião com decisões e backlog
    novo_snapshot = db.save_snapshot(
        executive_summary="""
Reunião P&L e Estratégia: Análise de performance de fevereiro
- Performance geral: +12.5% no mês
- Volatilidade BTC: Aumentou 18%
- Impacto de liquidação: 3 itens liquidados no periodo
        """,
        decisions={
            "Decisão 1": "Aumentar alavancagem em BTC para 3x",
            "Decisão 2": "Reduzir exposição em ALT coins",
            "Decisão 3": "Implementar proteção de drawdown máximo 15%",
            "Decisão 4": "Auditar modelo de reward function"
        },
        backlog_items=[
            {
                "task": "Auditar integridade do modelo de risk management",
                "owner": "Engenheiro de Risk",
                "priority": "HIGH",
                "status": "IN_PROGRESS"
            },
            {
                "task": "Realizar backtest com novos parâmetros de alavancagem",
                "owner": "Engenheiro de ML",
                "priority": "HIGH",
                "status": "OPEN"
            },
            {
                "task": "Investigar causas das 3 liquidações de fevereiro",
                "owner": "Analista de Dados",
                "priority": "CRITICAL",
                "status": "OPEN"
            },
            {
                "task": "Documentar mudanças na tolerance de drawdown",
                "owner": "Engenheiro Sênior",
                "priority": "MEDIUM",
                "status": "OPEN"
            },
        ]
    )

    if novo_snapshot:
        print(f"✅ Snapshot salvo com sucesso (ID: {novo_snapshot})\n")
    else:
        print("❌ Erro ao salvar snapshot\n")

    # 4. Recuperar contexto da última reunião para injeção em prompt
    contexto = db.get_last_context()
    print("📥 CONTEXTO RECUPERADO PARA INJEÇÃO EM PROMPT:")
    print(contexto)

    # 5. Recuperar backlog filtrado
    backlog_aberto = db.get_backlog(status_filter="OPEN")
    print(f"\n📌 ITENS ABERTOS NO BACKLOG: {len(backlog_aberto)} item(ns)")
    for item in backlog_aberto:
        print(f"  • [{item['id']}] {item['task']} ({item['priority']})")

    # 6. Recuperar histórico de reuniões
    historico = db.get_meeting_history(limit=5)
    print(f"\n📜 HISTÓRICO DE REUNIÕES: {len(historico)} reunião(ões)")
    for reuniao in historico:
        print(f"  • ID: {reuniao['id']} | Data: {reuniao['date']}")


def exemplo_injecao_em_prompt():
    """
    Exemplo prático: como usar get_last_context() para injetar em um prompt de IA.

    Este padrão é útil para que o orquestrador de reuniões tenha memória
    do contexto anterior e possa tomar decisões mais informadas.
    """
    db = get_database_manager(db_path="reunioes.db")
    db.initialize_db()

    # Simular uma reunião anterior
    db.save_snapshot(
        executive_summary="Reunião anterior: Análise de drawdown crítico",
        decisions=["Reduzir risco", "Auditar modelo"],
        backlog_items=[{"task": "Implementar hedge", "priority": "CRITICAL"}]
    )

    # Recuperar contexto
    contexto_anterior = db.get_last_context()

    # Montar prompt completo com injeção de contexto
    prompt_reuniao = f"""
Você é um Especialista em Finanças e ML assessorando um board de decisão.

{contexto_anterior}

Com base no contexto anterior, responda:
1. Qual é o estado atual de cada decisão?
2. Que ações você recomenda para hoje?
3. Qual item do backlog é mais urgente?

Seja conciso e direto.
    """

    print("=" * 70)
    print("PROMPT PARA INJEÇÃO EM IA (com contexto histórico):")
    print("=" * 70)
    print(prompt_reuniao)


if __name__ == "__main__":
    print("🚀 EXECUTANDO EXEMPLO BÁSICO\n")
    exemplo_basico()

    print("\n" + "=" * 70 + "\n")

    print("🚀 EXECUTANDO EXEMPLO DE INJEÇÃO EM PROMPT\n")
    exemplo_injecao_em_prompt()
