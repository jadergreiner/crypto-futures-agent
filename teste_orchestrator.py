"""
Script de Teste: Validar Main Orchestrator

Testa o orquestrador de reuniões sem interação interativa,
validando todas as funções críticas.
"""

import json
from main_orchestrator import MainOrchestrator
from database_manager import get_database_manager


def teste_parse_json():
    """Testar extração de JSON com regex."""
    print("\n" + "=" * 70)
    print("TESTE 1: Parse de JSON com Regex")
    print("=" * 70)

    resposta_exemplo = """
Aqui está um resumo da reunião:

### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "Reunião de estratégia aprovada",
  "decisions": [
    "Aumentar alavancagem em BTC",
    "Reduzir riscos em ALT coins"
  ],
  "backlog_items": [
    {
      "task": "Auditar modelo",
      "owner": "ML Eng",
      "priority": "HIGH",
      "status": "IN_PROGRESS"
    }
  ]
}
---

Fim da reunião.
    """

    resultado = MainOrchestrator.parse_ai_output(resposta_exemplo)

    if resultado:
        print("✅ SUCESSO: JSON extraído com sucesso!")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
    else:
        print("❌ FALHA: Não conseguiu extrair JSON")


def teste_carregamento_template():
    """Testar carregamento do template prompt_master.md."""
    print("\n" + "=" * 70)
    print("TESTE 2: Carregamento de Template")
    print("=" * 70)

    try:
        orq = MainOrchestrator(prompt_master_path="prompts/prompt_master.md")
        print("✅ SUCESSO: Template carregado!")
        print(f"   Tamanho: {len(orq.prompt_template)} caracteres")
        print(f"   Contém {{{{HISTORICO_DA_ULTIMA_ATA}}}}: {'Sim' if '{{' in orq.prompt_template else 'Não'}")
    except Exception as erro:
        print(f"❌ FALHA: {str(erro)}")


def teste_montagem_prompt():
    """Testar substituição de variáveis no prompt."""
    print("\n" + "=" * 70)
    print("TESTE 3: Montagem de Prompt com Variáveis")
    print("=" * 70)

    try:
        orq = MainOrchestrator(prompt_master_path="prompts/prompt_master.md")
        prompt_final = orq._montar_prompt_final()

        print("✅ SUCESSO: Prompt montado!")
        print(f"   Tamanho: {len(prompt_final)} caracteres")
        print(f"   Contém data: {'Sim' if '2026' in prompt_final else 'Não'}")

        # Validar que placeholders foram substituídos
        if "{{" not in prompt_final:
            print("✅ Todos os placeholders foram substituídos")
        else:
            print("⚠️ AVISO: Ainda há placeholders no prompt")

    except Exception as erro:
        print(f"❌ FALHA: {str(erro)}")


def teste_banco_dados():
    """Testar integração com banco de dados."""
    print("\n" + "=" * 70)
    print("TESTE 4: Integração com Banco de Dados")
    print("=" * 70)

    try:
        db = get_database_manager("test_reunioes.db")
        db.initialize_db()

        print("✅ Banco inicializado")

        # Salvar snapshot de teste
        meeting_id = db.save_snapshot(
            executive_summary="Reunião de teste",
            decisions=["Decisão 1", "Decisão 2"],
            backlog_items=[
                {"task": "Teste 1", "owner": "Eng", "priority": "HIGH"}
            ],
        )

        if meeting_id:
            print(f"✅ Snapshot salvo (ID: {meeting_id})")

            # Recuperar contexto
            contexto = db.get_last_context()
            if contexto and "Reunião de teste" in contexto:
                print("✅ Contexto recuperado com sucesso")
            else:
                print("❌ Contexto não recuperado")
        else:
            print("❌ Erro ao salvar snapshot")

    except Exception as erro:
        print(f"❌ FALHA: {str(erro)}")


def teste_simulacao_conversas():
    """Testar simulação de resposta do Facilitador."""
    print("\n" + "=" * 70)
    print("TESTE 5: Simulação de Resposta do Facilitador")
    print("=" * 70)

    try:
        orq = MainOrchestrator(prompt_master_path="prompts/prompt_master.md")

        # Testar com pergunta que contém palavra-chave
        resposta = orq._simular_resposta_facilitador("Qual é o status do backlog?")

        if resposta:
            print("✅ Resposta gerada com sucesso")
            print(f"   Tamanho: {len(resposta)} caracteres")

            # Verificar se contém snapshot
            if "### SNAPSHOT_PARA_BANCO" in resposta:
                print("✅ Resposta contém estrutura de snapshot")
                snapshot = MainOrchestrator.parse_ai_output(resposta)
                if snapshot:
                    print("✅ Snapshot extraído corretamente da resposta simulada")
                else:
                    print("❌ Falha ao extrair snapshot da resposta simulada")
            else:
                print("⚠️ Resposta não contém snapshot (esperado para algumas perguntas)")
        else:
            print("❌ Falha ao gerar resposta")

    except Exception as erro:
        print(f"❌ FALHA: {str(erro)}")


def teste_json_valido_vs_invalido():
    """Testar parse com JSON válido e inválido."""
    print("\n" + "=" * 70)
    print("TESTE 6: Validação de JSON (Válido vs Inválido)")
    print("=" * 70)

    # JSON válido
    resposta_valida = """
### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "teste",
  "decisions": ["d1"],
  "backlog_items": []
}
---
    """

    # JSON inválido (falta comma)
    resposta_invalida = """
### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "teste"
  "decisions": ["d1"],
  "backlog_items": []
}
---
    """

    print("\n1. Testando JSON válido...")
    resultado_valido = MainOrchestrator.parse_ai_output(resposta_valida)
    if resultado_valido:
        print("   ✅ JSON válido foi extraído corretamente")
    else:
        print("   ❌ Falha ao extrair JSON válido")

    print("\n2. Testando JSON inválido...")
    resultado_invalido = MainOrchestrator.parse_ai_output(resposta_invalida)
    if resultado_invalido is None:
        print("   ✅ JSON inválido foi rejeitado corretamente")
    else:
        print("   ❌ JSON inválido não foi rejeitado")


def main():
    """Executar todos os testes."""
    print("\n" + "=" * 70)
    print("🧪 SUITE DE TESTES: MAIN ORCHESTRATOR")
    print("=" * 70)

    teste_parse_json()
    teste_carregamento_template()
    teste_montagem_prompt()
    teste_banco_dados()
    teste_simulacao_conversas()
    teste_json_valido_vs_invalido()

    print("\n" + "=" * 70)
    print("✅ SUITE DE TESTES CONCLUÍDA")
    print("=" * 70)
    print(
        "\nPróximo passo: Execute 'python main_orchestrator.py' para interação real"
    )


if __name__ == "__main__":
    main()
