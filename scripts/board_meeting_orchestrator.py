#!/usr/bin/env python3
"""
Orquestrador de Reuniões de Board com 16 Membros da Equipe

Sistema de Decisão Estruturado onde cada membro opina de sua perspectiva/especialidade:

EQUIPE CORE (14 internos):
  1. Angel (Investidor)
  2. Elo (Facilitador)
  3. Audit/Docs (Doc Advocate)
  4. Planner (Gerente Projetos)
  5. Dr. Risk (Head Finanças & Risco)
  6. Flux (Arquiteto Dados)
  7. The Brain (Engenheiro ML)
  8. Guardian (Risk Manager)
  9. Audit/QA (QA Manager)
 10. The Blueprint (Tech Lead)
 11. Dev (The Implementer)
 12. Vision (Product Manager)
 13. Arch (Tech Lead AI Architect)
 14. Alpha (Senior Crypto Trader)

EXTERNOS (2 consultivos):
 E1. Board Member (Conselheiro Estratégico)
 E2. Compliance (Auditor Independente)

FLUXO:
1. Apresentação do Tópico/Decisão
2. Ciclo de Opiniões: cada membro opina de sua especialidade
3. Síntese: Facilitador resume posições
4. Votação: Angel toma decisão final
5. Registro: JSON persistido em banco
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/board_meetings.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TipoOpiniao(Enum):
    """Tipo de opinião esperada por especialidade"""
    EXECUTIVA = "executiva"  # Angel (custo, ROI, decisão)
    GOVERNANCA = "governança"  # Elo (processo, alinhamento)
    DOCUMENTACAO = "documentação"  # Audit/Docs (registro, compliance)
    OPERACIONAL = "operacional"  # Planner (timeline, burndown)
    FINANCEIRA = "financeira"  # Dr. Risk (risco, capital)
    DADOS = "dados"  # Flux (integridade, performance)
    ML = "machine_learning"  # The Brain (modelo, validação)
    RISCO = "risco"  # Guardian (drawdown, liquidação)
    QUALIDADE = "qualidade"  # Audit/QA (testes, edge cases)
    ARQUITETURA = "arquitetura"  # The Blueprint (sistema, escalabilidade)
    IMPLEMENTACAO = "implementação"  # Dev (código, performance)
    PRODUTO = "produto"  # Vision (roadmap, mercado)
    INFRAESTRUTURA_ML = "infraestrutura_ml"  # Arch (training, PPO)
    TRADING = "trading"  # Alpha (price action, execution)
    ESTRATEGIA = "estratégia"  # Board Member (visão longa)
    COMPLIANCE = "compliance"  # Compliance (regulatória)


class Membro:
    """Representação de membro com especialidades"""

    def __init__(
        self,
        id_membro: int,
        nome: str,
        persona: str,
        tipo_opiniao: TipoOpiniao,
        eh_interno: bool = True,
        é_decision_maker: bool = False
    ):
        self.id = id_membro
        self.nome = nome
        self.persona = persona
        self.tipo_opiniao = tipo_opiniao
        self.eh_interno = eh_interno
        self.é_decision_maker = é_decision_maker  # Angel é o único ao final


class BoardMeetingOrchestrator:
    """Orquestrador de reuniões de board com 16 membros"""

    # Definição da equipe fixa
    EQUIPE_FIXA = [
        Membro(1, "Angel", "Investidor", TipoOpiniao.EXECUTIVA, eh_interno=True, é_decision_maker=True),
        Membro(2, "Elo", "Facilitador", TipoOpiniao.GOVERNANCA, eh_interno=True),
        Membro(3, "Audit", "Doc Advocate", TipoOpiniao.DOCUMENTACAO, eh_interno=True),
        Membro(4, "Planner", "Gerente Projetos", TipoOpiniao.OPERACIONAL, eh_interno=True),
        Membro(5, "Dr. Risk", "Head Finanças & Risco", TipoOpiniao.FINANCEIRA, eh_interno=True),
        Membro(6, "Flux", "Arquiteto Dados", TipoOpiniao.DADOS, eh_interno=True),
        Membro(7, "The Brain", "Engenheiro ML", TipoOpiniao.ML, eh_interno=True),
        Membro(8, "Guardian", "Risk Manager", TipoOpiniao.RISCO, eh_interno=True),
        Membro(9, "Audit (QA)", "QA Manager", TipoOpiniao.QUALIDADE, eh_interno=True),
        Membro(10, "The Blueprint", "Tech Lead", TipoOpiniao.ARQUITETURA, eh_interno=True),
        Membro(11, "Dev", "The Implementer", TipoOpiniao.IMPLEMENTACAO, eh_interno=True),
        Membro(12, "Vision", "Product Manager", TipoOpiniao.PRODUTO, eh_interno=True),
        Membro(13, "Arch", "Tech Lead & AI Architect", TipoOpiniao.INFRAESTRUTURA_ML, eh_interno=True),
        Membro(14, "Alpha", "Senior Crypto Trader", TipoOpiniao.TRADING, eh_interno=True),
        Membro(15, "Board Member", "Conselheiro Estratégico", TipoOpiniao.ESTRATEGIA, eh_interno=False),
        Membro(16, "Compliance", "Auditor Independente", TipoOpiniao.COMPLIANCE, eh_interno=False),
    ]

    def __init__(self, db_path: str = "db/board_meetings.db"):
        """Inicializa orquestrador de board meetings"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._inicializar_banco()
        logger.info(f"BoardMeetingOrchestrator inicializado ({self.db_path})")

    def _inicializar_banco(self):
        """Cria tabelas necessárias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabela de reuniões
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS board_meetings (
                id_reuniao INTEGER PRIMARY KEY AUTOINCREMENT,
                data_reuniao DATETIME UNIQUE,
                titulo_decisao TEXT,
                descricao TEXT,
                status TEXT DEFAULT 'aberta',
                decision_maker_id INTEGER,
                decisao_final TEXT,
                data_decisao DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de opiniões por membro
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opinoes_board (
                id_opiniao INTEGER PRIMARY KEY AUTOINCREMENT,
                id_reuniao INTEGER NOT NULL,
                membro_id INTEGER NOT NULL,
                nome_membro TEXT,
                persona TEXT,
                tipo_opiniao TEXT,
                opcoes_consideradas TEXT,
                parecer_texto TEXT,
                posicao_final TEXT,
                argumentos_json TEXT,
                prioridade TEXT,
                risco_apontado TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(id_reuniao) REFERENCES board_meetings(id_reuniao)
            )
        """)

        # Tabela de síntese de decisão
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sintese_decisoes (
                id_sintese INTEGER PRIMARY KEY AUTOINCREMENT,
                id_reuniao INTEGER NOT NULL,
                consenso TEXT,
                dissenso JSON,
                impacto_financeiro TEXT,
                impacto_timeline TEXT,
                impacto_risco TEXT,
                proximas_acoes JSON,
                proprietario_implementacao TEXT,
                data_alvo TEXT,
                FOREIGN KEY(id_reuniao) REFERENCES board_meetings(id_reuniao)
            )
        """)

        conn.commit()
        conn.close()

    def criar_reuniao(
        self,
        titulo_decisao: str,
        descricao: str,
        data_reuniao: Optional[str] = None
    ) -> int:
        """
        Cria nova reunião de board

        Args:
            titulo_decisao: Título da decisão (ex: "ML Training Strategy - Decision #2")
            descricao: Descrição da decisão
            data_reuniao: Data ISO, padrão=agora

        Returns:
            ID da reunião criada
        """
        data_reuniao = data_reuniao or datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO board_meetings (data_reuniao, titulo_decisao, descricao, status)
            VALUES (?, ?, ?, 'aberta')
        """, (data_reuniao, titulo_decisao, descricao))
        conn.commit()
        id_reuniao = cursor.lastrowid
        conn.close()

        logger.info(f"Reunião criada: ID={id_reuniao}, Título={titulo_decisao}")
        return id_reuniao

    def registrar_opiniao(
        self,
        id_reuniao: int,
        membro: Membro,
        opcoes_consideradas: List[str],
        parecer_texto: str,
        posicao_final: str,
        argumentos: Dict,
        prioridade: str = "MÉDIA",
        risco_apontado: str = ""
    ):
        """
        Registra opinião de um membro sobre a decisão

        Args:
            id_reuniao: ID da reunião
            membro: Objeto Membro
            opcoes_consideradas: ["Opção A", "Opção B", "Opção C"]
            parecer_texto: Texto da opinião (500-1000 caracteres)
            posicao_final: "FAVORÁVEL", "CONTRÁRIO", "NEUTRO", "CONDICIONAL"
            argumentos: {"argumento_1": "...", "argumento_2": "..."}
            prioridade: "CRÍTICA", "ALTA", "MÉDIA", "BAIXA"
            risco_apontado: Descrição de riscos identificados
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO opinoes_board (
                id_reuniao, membro_id, nome_membro, persona, tipo_opiniao,
                opcoes_consideradas, parecer_texto, posicao_final, argumentos_json,
                prioridade, risco_apontado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            id_reuniao,
            membro.id,
            membro.nome,
            membro.persona,
            membro.tipo_opiniao.value,
            json.dumps(opcoes_consideradas),
            parecer_texto,
            posicao_final,
            json.dumps(argumentos),
            prioridade,
            risco_apontado
        ))
        conn.commit()
        conn.close()

        logger.info(f"Opinião registrada: {membro.nome} - {posicao_final}")

    def obter_opinoes_reuniao(self, id_reuniao: int) -> List[Dict]:
        """Recupera todas as opiniões de uma reunião"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM opinoes_board
            WHERE id_reuniao = ?
            ORDER BY tipo_opiniao, nome_membro
        """, (id_reuniao,))

        opinoes = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return opinoes

    def gerar_relatorio_opinoes(self, id_reuniao: int) -> str:
        """Gera relatório Markdown com todas as opiniões"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Buscar reunião
        cursor.execute("SELECT * FROM board_meetings WHERE id_reuniao = ?", (id_reuniao,))
        reuniao = dict(cursor.fetchone())

        # Buscar opiniões
        opinoes = self.obter_opinoes_reuniao(id_reuniao)
        conn.close()

        # Gerar markdown
        md = []
        md.append(f"# 🎯 BOARD MEETING — {reuniao['titulo_decisao']}")
        md.append(f"\n**Data:** {reuniao['data_reuniao']}")
        md.append(f"**Status:** {reuniao['status'].upper()}")
        md.append(f"\n{reuniao['descricao']}\n")

        md.append("---\n")
        md.append("## 📋 CICLO DE OPINIÕES (16 MEMBROS)\n")

        # Agrupar por tipo de opinião
        por_tipo = {}
        for opiniao in opinoes:
            tipo = opiniao['tipo_opiniao']
            if tipo not in por_tipo:
                por_tipo[tipo] = []
            por_tipo[tipo].append(opiniao)

        # Renderizar por grupo
        ordem_tipos = [
            "executiva", "governança", "produto", "financeira",
            "machine_learning", "infraestrutura_ml", "trading", "arquitetura",
            "dados", "implementação", "qualidade", "risco",
            "documentação", "operacional", "estratégia", "compliance"
        ]

        for tipo in ordem_tipos:
            if tipo not in por_tipo:
                continue

            # Título do grupo
            emojis = {
                "executiva": "👑", "governança": "🎯", "produto": "📈",
                "financeira": "💰", "machine_learning": "🤖", "infraestrutura_ml": "⚙️",
                "trading": "📉", "arquitetura": "🏗️", "dados": "🏪",
                "implementação": "💻", "qualidade": "✅", "risco": "⚠️",
                "documentação": "📖", "operacional": "📊", "estratégia": "🔮",
                "compliance": "⚖️"
            }
            emoji = emojis.get(tipo, "•")
            md.append(f"\n### {emoji} {tipo.upper()}\n")

            # Opiniões neste grupo
            for op in por_tipo[tipo]:
                md.append(f"#### {op['nome_membro']} ({op['persona']})")
                md.append(f"\n**Posição:** `{op['posicao_final']}` | **Prioridade:** `{op['prioridade']}`\n")
                md.append(f"**Parecer:**\n> {op['parecer_texto']}\n")

                if op['risco_apontado']:
                    md.append(f"**⚠️ Risco apontado:** {op['risco_apontado']}\n")

                if op['argumentos_json']:
                    args = json.loads(op['argumentos_json'])
                    md.append("**Argumentos:**\n")
                    for i, (chave, valor) in enumerate(args.items(), 1):
                        md.append(f"  {i}. {chave}: {valor}\n")
                md.append("\n")

        return "".join(md)

    def processar_ciclo_opinoes(
        self,
        id_reuniao: int,
        opinioes_json: str  # JSON com opinião de cada membro
    ):
        """
        Processa um ciclo completo de opiniões (16 membros)

        Args:
            id_reuniao: ID da reunião
            opinioes_json: JSON estruturado com opinião de cada membro
        """
        opinioes_dados = json.loads(opinioes_json)

        for membro_id, dados in opinioes_dados.items():
            membro = next((m for m in self.EQUIPE_FIXA if m.id == int(membro_id)), None)
            if not membro:
                continue

            self.registrar_opiniao(
                id_reuniao=id_reuniao,
                membro=membro,
                opcoes_consideradas=dados.get("opcoes", []),
                parecer_texto=dados.get("parecer", ""),
                posicao_final=dados.get("posicao", "NEUTRO"),
                argumentos=dados.get("argumentos", {}),
                prioridade=dados.get("prioridade", "MÉDIA"),
                risco_apontado=dados.get("risco", "")
            )

    def fechar_reuniao(
        self,
        id_reuniao: int,
        decisao_final: str,
        proprietario: str,
        data_alvo: str
    ):
        """Fecha reunião registrando decisão final"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        data_decisao = datetime.now().isoformat()
        cursor.execute("""
            UPDATE board_meetings
            SET status = 'fechada', decisao_final = ?, data_decisao = ?
            WHERE id_reuniao = ?
        """, (decisao_final, data_decisao, id_reuniao))

        conn.commit()
        conn.close()

        logger.info(f"Reunião fechada: ID={id_reuniao}, Decisão={decisao_final}")


def exemplo_uso():
    """Exemplo de uso do orquestrador"""
    orchestrator = BoardMeetingOrchestrator()

    # Criar reunião
    id_reuniao = orchestrator.criar_reuniao(
        titulo_decisao="Decision #2 — ML Training Strategy",
        descricao="Votação sobre estratégia de treinamento PPO: Opção A (heurísticas), B (full training), ou C (híbrido)",
        data_reuniao=None
    )

    # Exemplo: opinião do The Brain (ML)
    the_brain = next(m for m in orchestrator.EQUIPE_FIXA if m.nome == "The Brain")
    orchestrator.registrar_opiniao(
        id_reuniao=id_reuniao,
        membro=the_brain,
        opcoes_consideradas=["Heurísticas (A)", "PPO Full (B)", "Híbrido (C)"],
        parecer_texto="""
        Opção B (PPO Full Training) é a única com rigor científico garantido.
        Opção A sacrifica generalização; Opção C é um compromisso arriscado.
        Recomendo B, tempo 7 dias. Sistema será robusto em produção.
        """,
        posicao_final="FAVORÁVEL",
        argumentos={
            "Walk-Forward Validation": "Apenas em B temos OOT >80%",
            "Generalização": "Modelo B generaliza em novo regime",
            "Confiança Live": "Sharpe produção esperado >0.5 em B"
        },
        prioridade="CRÍTICA",
        risco_apontado="Opção A falhará em regime diferente"
    )

    # Gerar relatório
    relatorio = orchestrator.gerar_relatorio_opinoes(id_reuniao)
    print(relatorio)

    # Salvar relatório
    Path("reports").mkdir(exist_ok=True)
    with open(f"reports/board_meeting_{id_reuniao}.md", "w") as f:
        f.write(relatorio)

    logger.info("Relatório salvo em reports/")


if __name__ == "__main__":
    exemplo_uso()
