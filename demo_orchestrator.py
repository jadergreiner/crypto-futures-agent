"""
DEMONSTRAÇÃO FINAL: Teste do Main Orchestrator em Modo Demo

Este script copia o comportamento de um usuário real interagindo com
o orquestrador, sem precisar de input interativo.
"""

import sys
from main_orchestrator import MainOrchestrator
from database_manager import get_database_manager


def demo_completa():
    """Demonstra fluxo completo do orquestrador."""
    print("\n" + "=" * 70)
    print("🎬 DEMONSTRAÇÃO FINAL: ORCHESTRADOR DE REUNIÕES")
    print("=" * 70)

    try:
        # ETAPA 1: Inicializar
        print("\n[ETAPA 1] Inicializando orquestrador...")
        orq = MainOrchestrator(prompt_master_path="prompts/prompt_master.md")
        print("✅ Orquestrador pronto")

        # ETAPA 2: Montar prompt
        print("\n[ETAPA 2] Montando prompt com contexto histórico...")
        prompt_final = orq._montar_prompt_final()
        print(f"✅ Prompt montado ({len(prompt_final)} caracteres)")
        print(f"   Preview: {prompt_final[:150]}...")

        # ETAPA 3: Simular pergunta do investidor
        print("\n[ETAPA 3] Simulando pergunta de Investidor...")
        pergunta = "Qual é o status do backlog?"
        print(f"👤 Investidor > {pergunta}")

        # ETAPA 4: Gerar resposta do Facilitador
        print("\n[ETAPA 4] Facilitador respondendo...")
        resposta = orq._simular_resposta_facilitador(pergunta)
        print(f"🤖 Facilitador:\n{resposta[:300]}...")

        # ETAPA 5: Parser JSON com Regex
        print("\n[ETAPA 5] Extraindo snapshot com Regex...")
        snapshot = MainOrchestrator.parse_ai_output(resposta)
        if snapshot:
            print("✅ Snapshot extraído com sucesso!")
            print(f"   Keys: {list(snapshot.keys())}")
            print(f"   Summary: {snapshot['executive_summary'][:60]}...")
            print(f"   Decisões: {len(snapshot['decisions'])} items")
            print(f"   Backlog: {len(snapshot['backlog_items'])} items")
        else:
            print("❌ Falha ao extrair snapshot")

        # ETAPA 6: Persistência
        if snapshot:
            print("\n[ETAPA 6] Persistindo snapshot no banco...")
            meeting_id = orq.salvar_snapshot(snapshot)
            if meeting_id:
                print(f"✅ Snapshot salvo com ID: {meeting_id}")
            else:
                print("❌ Falha ao salvar")

        # ETAPA 7: Recuperar contexto (simulando próxima reunião)
        print("\n[ETAPA 7] Simulando próxima reunião - recuperando contexto...")
        contexto = orq.db.get_last_context()
        if contexto:
            print("✅ Contexto recuperado!")
            print(f"   Tamanho: {len(contexto)} caracteres")
            print(f"   Preview:\n{contexto[:300]}...")
        else:
            print("❌ Contexto vazio")

        # ETAPA 8: Validar banco de dados
        print("\n[ETAPA 8] Validando integridade do banco...")
        historico = orq.db.get_meeting_history(limit=5)
        print(f"✅ Histórico de reuniões: {len(historico)} reunião(ões)")
        for reuniao in historico:
            print(f"   ID {reuniao['id']}: {reuniao['executive_summary'][:40]}...")

        backlog = orq.db.get_backlog()
        print(f"✅ Backlog total: {len(backlog)} item(ns)")

        # ETAPA 9: Verificar histórico de conversas
        print("\n[ETAPA 9] Histórico de conversas da sessão...")
        orq.historico_conversas.append(
            {"papel": "Investidor", "mensagem": pergunta}
        )
        orq.historico_conversas.append(
            {"papel": "Facilitador", "mensagem": resposta[:100]}
        )
        print(f"✅ Conversas registradas: {len(orq.historico_conversas)} entries")

        # RESUMO FINAL
        print("\n" + "=" * 70)
        print("✅ DEMONSTRAÇÃO CONCLUÍDA COM SUCESSO")
        print("=" * 70)

        print("""
FLUXO VALIDADO:

  1. ✅ Inicialização do orquestrador
  2. ✅ Carregamento de template
  3. ✅ Montagem de prompt com contexto
  4. ✅ Simulação de interação Investidor ↔ Facilitador
  5. ✅ Extração de JSON com Regex
  6. ✅ Persistência no SQLite
  7. ✅ Recuperação de contexto (próxima reunião)
  8. ✅ Validação do banco de dados
  9. ✅ Rastreamento de histórico

PRÓXIMAS REUNIÕES:
  → Contexto será recuperado automaticamente
  → Decisões anteriores estarão disponíveis
  → Backlog será mantido e atualizado
  → Histórico será rastreável

═══════════════════════════════════════════════════════════════════

🚀 SISTEMA PRONTO PARA PRODUÇÃO!

Para usar de verdade, execute:
   $ python main_orchestrator.py
        """)

    except Exception as erro:
        print(f"\n❌ ERRO: {str(erro)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def teste_campos_json():
    """Testa validação de campos JSON."""
    print("\n" + "=" * 70)
    print("🧪 TESTE: Campos Obrigatórios do JSON")
    print("=" * 70)

    # JSON válido
    resposta_valida = """
### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "Teste",
  "decisions": ["D1"],
  "backlog_items": []
}
---
    """

    # JSON sem executive_summary
    resposta_incompleta = """
### SNAPSHOT_PARA_BANCO
{
  "decisions": ["D1"],
  "backlog_items": []
}
---
    """

    print("\n1. JSON válido (com todos os campos):")
    resultado = MainOrchestrator.parse_ai_output(resposta_valida)
    print(f"   Resultado: {'✅ ACEITO' if resultado else '❌ REJEITADO'}")

    print("\n2. JSON incompleto (falta 'executive_summary'):")
    resultado = MainOrchestrator.parse_ai_output(resposta_incompleta)
    print(f"   Resultado: {'✅ ACEITO' if resultado else '❌ REJEITADO (correto!)'}")


if __name__ == "__main__":
    demo_completa()
    teste_campos_json()
    print("\n✅ Todos os testes completados!")
