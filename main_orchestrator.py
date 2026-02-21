"""
Orquestrador Principal de Reuniões — Main Orchestrator

Este módulo coordena o ciclo completo de uma reunião:
1. Lê histórico do SQLite
2. Carrega template prompt_master.md
3. Injeta variáveis de contexto
4. Implementa loop de interação Investidor ↔ Facilitador
5. Captura e persiste snapshots de decisão
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple
from database_manager import get_database_manager


class MainOrchestrator:
    """
    Orquestrador Central de Reuniões para o Board de Especialistas.

    Responsabilidades:
    - Carregar e processar prompts
    - Gerenciar interação usuário-IA
    - Extrair e validar snapshots de decisão
    - Persistir dados no banco de dados
    """

    def __init__(self, prompt_master_path: str = "prompts/prompt_master.md"):
        """
        Inicializa o orquestrador de reuniões.

        Args:
            prompt_master_path (str): Caminho para o template prompt_master.md

        Raises:
            FileNotFoundError: Se prompt_master.md não existir
        """
        self.prompt_master_path = Path(prompt_master_path)
        self.db = get_database_manager()
        self.db.initialize_db()

        # Validar existência do template
        if not self.prompt_master_path.exists():
            raise FileNotFoundError(f"Template não encontrado: {self.prompt_master_path}")

        self.prompt_template = self._load_prompt_template()
        self.historico_conversas = []
        self.snapshot_pendente = None

    def _load_prompt_template(self) -> str:
        """
        Carrega o template do prompt_master.md.

        Returns:
            str: Conteúdo do template

        Raises:
            IOError: Se não conseguir ler o arquivo
        """
        try:
            with open(self.prompt_master_path, "r", encoding="utf-8") as f:
                return f.read()
        except IOError as erro:
            raise IOError(f"Erro ao carregar template: {str(erro)}") from erro

    def _get_contexto_historico(self) -> str:
        """
        Recupera o contexto da última reunião do banco de dados.

        Returns:
            str: Contexto formatado ou string default se sem histórico

        Raises:
            sqlite3.Error: Se houver erro ao consultar banco
        """
        contexto = self.db.get_last_context()

        # Se não houver histórico, retornar mensagem padrão
        if not contexto:
            return """
═══════════════════════════════════════════════════════════════
PRIMEIRA REUNIÃO DO SISTEMA
═══════════════════════════════════════════════════════════════

Bem-vindo ao Board de Especialistas em Crypto e ML.

Este é o primeiro registro de decisão neste sistema.
Nenhuma reunião anterior foi registrada.

A partir de agora, todos os snapshots serão capturados e
poderão ser recuperados nas reuniões futuras.
═══════════════════════════════════════════════════════════════
            """

        return contexto

    def _montar_prompt_final(self) -> str:
        """
        Monta o prompt final substituindo variáveis de placeholder.

        Returns:
            str: Prompt montado e pronto para injeção
        """
        contexto = self._get_contexto_historico()
        data_sessao = datetime.now().strftime("%d de %B de %Y às %H:%M")

        # Substituir placeholders
        prompt_final = self.prompt_template.replace(
            "{{HISTORICO_DA_ULTIMA_ATA}}", contexto
        )
        prompt_final = prompt_final.replace("{{DATA_SESSAO}}", data_sessao)
        prompt_final = prompt_final.replace(
            "{{ITENS_DE_BACKLOG_EM_ABERTO}}", contexto
        )

        return prompt_final

    @staticmethod
    def parse_ai_output(response_text: str) -> Optional[Dict]:
        """
        Extrai e valida o JSON de snapshot da resposta da IA.

        Procura por um bloco estruturado entre:
        ### SNAPSHOT_PARA_BANCO
        {...JSON...}
        ---

        Args:
            response_text (str): Texto da resposta da IA

        Returns:
            Optional[Dict]: Dicionário Python do JSON, ou None se não encontrado

        Raises:
            json.JSONDecodeError: Se o JSON for inválido
        """
        # Regex para capturar o bloco SNAPSHOT_PARA_BANCO
        pattern = r"### SNAPSHOT_PARA_BANCO\s*\n(.*?)\n---"
        match = re.search(pattern, response_text, re.DOTALL)

        if not match:
            print("⚠️ Nenhum bloco SNAPSHOT_PARA_BANCO encontrado na resposta")
            return None

        json_str = match.group(1).strip()

        try:
            # Tentar fazer parse do JSON
            snapshot_dict = json.loads(json_str)

            # Validar estrutura mínima
            required_keys = ["executive_summary", "decisions", "backlog_items"]
            if not all(key in snapshot_dict for key in required_keys):
                print(f"❌ ERRO: JSON incompleto. Faltam chaves: {required_keys}")
                return None

            return snapshot_dict

        except json.JSONDecodeError as erro:
            print(f"❌ ERRO ao fazer parse do JSON: {str(erro)}")
            print(f"JSON inválido:\n{json_str[:200]}...")
            return None

    def salvar_snapshot(self, snapshot_dict: Dict) -> bool:
        """
        Salva o snapshot no banco de dados.

        Args:
            snapshot_dict (Dict): Dicionário com dados de decisão

        Returns:
            bool: True se salvou com sucesso, False caso contrário
        """
        try:
            meeting_id = self.db.save_snapshot(
                executive_summary=snapshot_dict.get(
                    "executive_summary", "Sem resumo"
                ),
                decisions=snapshot_dict.get("decisions", []),
                backlog_items=snapshot_dict.get("backlog_items", []),
            )

            if meeting_id:
                print(f"\n✅ [Sessão Persistida com Sucesso] (ID: {meeting_id})")
                self.snapshot_pendente = None
                return True
            else:
                print("\n❌ Erro ao salvar snapshot no banco de dados")
                return False

        except Exception as erro:
            print(f"\n❌ ERRO ao salvar snapshot: {str(erro)}")
            return False

    def solicitar_snapshot_final(self) -> bool:
        """
        Solicita ao "Facilitador" (simula prompt à IA) para gerar snapshot final.

        Retorna True se usuario confirmar o encerramento.

        Returns:
            bool: True se encerrou, False se voltar ao loop
        """
        print("\n" + "=" * 70)
        print("🔍 GERANDO SNAPSHOT FINAL ANTES DE ENCERRAR...")
        print("=" * 70)

        prompt_finalizacao = """
Você é o Facilitador encerando uma reunião de estratégia.

Por favor, forneça o SNAPSHOT FINAL da reunião que acabou de ocorrer.

Inclua:
1. Um resumo executivo (1-2 linhas)
2. AS decisões tomadas (liste cada uma)
3. O novo backlog atualizado com status de cada item

IMPORTANTE: Sempre inclua o bloco com as tags exatas:

### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "...",
  "decisions": [...],
  "backlog_items": [...]
}
---

Agora proceda.
        """

        print("\n📨 [Enviando para Facilitador...]")
        print(prompt_finalizacao)

        print("\n🤖 [Simulando resposta do Facilitador - Digite a resposta ou pressione Enter para usar default]:")
        resposta_facilitador = input(
            "\n> "
        )

        if not resposta_facilitador.strip():
            # Resposta default se usuário não digitar nada
            resposta_facilitador = self._gerar_resposta_default_final()

        # Tentar extrair e salvar snapshot
        snapshot = self.parse_ai_output(resposta_facilitador)
        if snapshot:
            return self.salvar_snapshot(snapshot)
        else:
            print(
                "\n⚠️ Não foi possível extrair snapshot. Deseja tentar novamente? (s/n)"
            )
            if input("> ").lower() == "s":
                return self.solicitar_snapshot_final()
            return True  # Encerrar mesmo sem salvar

    @staticmethod
    def _gerar_resposta_default_final() -> str:
        """
        Gera uma resposta simulada de encerramento com snapshot estruturado.

        Returns:
            str: Resposta simulada pronta para parse
        """
        return """
Reunião encerrada com sucesso. Segue o snapshot final:

### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "Reunião de estratégia realizada. Revisões de performance e aprovação de novos limites de risco implementados.",
  "decisions": [
    "Aumentar limite de drawdown máximo para 16%",
    "Implementar hedge adicional em ETH",
    "Auditar modelo de reward function com urgência"
  ],
  "backlog_items": [
    {
      "task": "Auditar integridade do modelo de risk management",
      "owner": "Engenheiro de Risk",
      "priority": "HIGH",
      "status": "IN_PROGRESS"
    },
    {
      "task": "Implementar proteção de hedge em ETH",
      "owner": "Risk Manager",
      "priority": "CRITICAL",
      "status": "OPEN"
    },
    {
      "task": "Testar novo modelo de reward",
      "owner": "Engenheiro de ML",
      "priority": "HIGH",
      "status": "OPEN"
    }
  ]
}
---
        """

    def loop_interacao(self):
        """
        Loop principal de interação entre Investidor e Facilitador.

        Fluxo:
        1. Exibir prompt montado
        2. Usuário digita pergunta (como Investidor)
        3. Simular resposta do Facilitador
        4. Parser regex para extrair snapshot
        5. Se snapshot detectado, salvar no banco
        6. Voltar a (2) até usuario digitar "sair" ou "encerrar"
        """
        print("\n" + "=" * 70)
        print("🚀 ORQUESTRADOR DE REUNIÃO INICIADO")
        print("=" * 70)

        prompt_final = self._montar_prompt_final()

        print("\n📄 CONTEXTO CARREGADO:")
        print("-" * 70)
        print(prompt_final[:500] + "..." if len(prompt_final) > 500 else prompt_final)
        print("-" * 70)

        print("\n💬 INICIANDO INTERAÇÃO")
        print("   Digite suas perguntas/observações como INVESTIDOR")
        print("   Digite 'sair' ou 'encerrar' para finalizar a reunião")
        print("   Digite 'historico' para ver todo o histórico de conversas")
        print("=" * 70)

        while True:
            try:
                # Input do "Investidor"
                entrada_usuario = input("\n👤 Investidor > ")

                if not entrada_usuario.strip():
                    continue

                # Verificar comandos especiais
                if entrada_usuario.lower() in ["sair", "encerrar"]:
                    print("\n⏹️ Encerrando reunião...")
                    if self.solicitar_snapshot_final():
                        print("\n✅ Reunião encerrada e dados persistidos com sucesso!")
                        break
                    else:
                        print("\n⚠️ Continuando reunião (snapshot não foi salvo)...")
                        continue

                if entrada_usuario.lower() == "historico":
                    self._exibir_historico_conversas()
                    continue

                # Adicionar entrada do usuário ao histórico
                self.historico_conversas.append(
                    {"papel": "Investidor", "mensagem": entrada_usuario}
                )

                # Simular resposta do Facilitador
                resposta_facilitador = self._simular_resposta_facilitador(
                    entrada_usuario
                )

                # Adicionar resposta do Facilitador ao histórico
                self.historico_conversas.append(
                    {"papel": "Facilitador", "mensagem": resposta_facilitador}
                )

                # Exibir resposta
                print(f"\n🤖 Facilitador:\n{resposta_facilitador}")

                # Tentar extrair snapshot
                snapshot = self.parse_ai_output(resposta_facilitador)
                if snapshot:
                    print("\n📊 Snapshot detectado na resposta!")
                    self.salvar_snapshot(snapshot)

            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupção do usuário. Deseja encerrar? (s/n)")
                if input("> ").lower() == "s":
                    print("✅ Programa encerrado.")
                    sys.exit(0)

    def _simular_resposta_facilitador(self, pergunta_usuario: str) -> str:
        """
        Simula uma resposta realista do Facilitador baseada na pergunta.

        Nota: Em produção, isso seria uma chamada real à API (OpenAI, Anthropic, etc).

        Args:
            pergunta_usuario (str): A pergunta do Investidor

        Returns:
            str: Resposta simulada do Facilitador (pode conter snapshot JSON)
        """
        # Respostas simuladas baseadas em palavras-chave
        respostas_por_palavra = {
            "backlog": """
O backlog atual tem 4 itens críticos:
1. Auditar modelo de risk (HIGH) - Em progresso
2. Implementar hedge em ETH (CRITICAL) - Aberto
3. Testar novo modelo de reward (HIGH) - Aberto
4. Documentar mudanças de alavancagem (MEDIUM) - Aberto

### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "Status do backlog revisado. 4 itens em monitoramento.",
  "decisions": [
    "Priorizar auditoria de risk",
    "Aumentar dedicação ao hedge em ETH"
  ],
  "backlog_items": [
    {
      "task": "Auditar modelo de risk",
      "owner": "Risk Eng",
      "priority": "HIGH",
      "status": "IN_PROGRESS"
    },
    {
      "task": "Implementar hedge ETH",
      "owner": "Risk Manager",
      "priority": "CRITICAL",
      "status": "OPEN"
    },
    {
      "task": "Testar novo reward model",
      "owner": "ML Engineer",
      "priority": "HIGH",
      "status": "OPEN"
    },
    {
      "task": "Documentar alavancagem",
      "owner": "Tech Lead",
      "priority": "MEDIUM",
      "status": "OPEN"
    }
  ]
}
---
            """,
            "risco": """
O risco sistêmico está elevado neste momento.
Sharpe Ratio: 0.06 (abaixo do alvo 1.0)
Max Drawdown: 17.24% (acima do limite 15%)

Recomendação: Reduzir posições alavancadas e ativar hedges.

### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "Risco sistêmico elevado. Medidas de proteção ativadas.",
  "decisions": [
    "Reduzir alavancagem geral de 3x para 2x",
    "Ativar proteção de drawdown máximo 15%",
    "Aumentar hedge em BTC"
  ],
  "backlog_items": [
    {
      "task": "Validar limite de drawdown em backtest",
      "owner": "QA Manager",
      "priority": "CRITICAL",
      "status": "OPEN"
    }
  ]
}
---
            """,
            "decisao": """
Ótima questão. Como Facilitador, registro as seguintes decisões:

1. Aprovar alavancagem máxima de 3x em BTC
2. Implementar stop-loss em 15% de drawdown
3. Auditar modelo completo até amanhã

Esta decisão deve ser refletida no backlog e no histórico.

### SNAPSHOT_PARA_BANCO
{
  "executive_summary": "Decisões de alavancagem e stop-loss aprovadas.",
  "decisions": [
    "Alavancagem máxima de 3x em BTC aprovada",
    "Stop-loss de 15% drawdown ativado",
    "Auditoria de modelo agendada"
  ],
  "backlog_items": [
    {
      "task": "Implementar stop-loss de 15%",
      "owner": "Engenheiro de Risk",
      "priority": "CRITICAL",
      "status": "OPEN"
    },
    {
      "task": "Auditar modelo completo",
      "owner": "ML Engineer",
      "priority": "HIGH",
      "status": "OPEN"
    }
  ]
}
---
            """,
        }

        # Procurar palavra-chave na pergunta
        pergunta_lower = pergunta_usuario.lower()
        for palavra, resposta in respostas_por_palavra.items():
            if palavra in pergunta_lower:
                return resposta

        # Resposta genérica padrão
        return f"""
Entendi sua questão: "{pergunta_usuario}"

Como Facilitador, procuro manter o foco em:
1. Performance e métricas do sistema
2. Decisões estratégicas que impactam risco
3. Itens críticos do backlog

Pode detalhar mais sua pergunta ou deseja revisar o backlog atual?
        """

    def _exibir_historico_conversas(self):
        """Exibe o histórico completo de conversas da sessão."""
        print("\n" + "=" * 70)
        print("📜 HISTÓRICO DE CONVERSAS")
        print("=" * 70)

        if not self.historico_conversas:
            print("(Nenhuma conversa registrada)")
            return

        for i, conversa in enumerate(self.historico_conversas, 1):
            papel = conversa["papel"]
            mensagem = conversa["mensagem"][:100] + "..." if len(
                conversa["mensagem"]
            ) > 100 else conversa["mensagem"]
            print(f"\n[{i}] {papel}: {mensagem}")

        print("\n" + "=" * 70)


def main():
    """
    Ponto de entrada principal do Orquestrador de Reuniões.

    Fluxo:
    1. Inicializar orquestrador
    2. Montar prompt com contexto histórico
    3. Iniciar loop de interação
    """
    try:
        print("\n" + "=" * 70)
        print("🎯 CRYPTO FUTURES AGENT — ORQUESTRADOR DE REUNIÕES")
        print("=" * 70)

        # Inicializar orquestrador
        orq = MainOrchestrator(prompt_master_path="prompts/prompt_master.md")

        print("\n✅ Orquestrador inicializado com sucesso")
        print(f"📁 Template carregado de: {orq.prompt_master_path}")
        print(f"💾 Banco de dados: reunioes.db")

        # Iniciar loop de interação
        orq.loop_interacao()

    except FileNotFoundError as erro:
        print(f"\n❌ ERRO: {str(erro)}")
        print("Verifique se o arquivo prompt_master.md existe em prompts/")
        sys.exit(1)

    except Exception as erro:
        print(f"\n❌ ERRO FATAL: {str(erro)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
