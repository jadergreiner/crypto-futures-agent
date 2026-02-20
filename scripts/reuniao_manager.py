#!/usr/bin/env python3
"""
Sistema de Persistência e Rastreamento de Reuniões Semanais
Head Financeiro × Operador Autônomo (Crypto Futures)

Gerencia banco SQLite com:
- Histórico de reuniões
- Diálogos e feedbacks
- Ações e investimentos
- Rastreamento de evolução
- Comparação automatizada entre reuniões
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class ReuniaoManagerDB:
    """Gerenciador de banco de dados de reuniões (ad-hoc, sem agendamento fixo)."""

    def __init__(self, db_path: str = "db/reunioes.db"):
        """
        Inicializa conexão com banco de dados.

        Args:
            db_path: Caminho do arquivo SQLite
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._inicializar_banco()

    def _inicializar_banco(self):
        """Cria tabelas se não existirem."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Tabela de reuniões
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reunioes (
                id_reuniao INTEGER PRIMARY KEY AUTOINCREMENT,
                data_reuniao DATETIME UNIQUE,
                semana_numero INTEGER,
                ano INTEGER,
                head_nome TEXT,
                operador_versao TEXT,
                status TEXT DEFAULT 'planejada',
                duracao_minutos INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de tópicos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topicos_reuniao (
                id_topico INTEGER PRIMARY KEY AUTOINCREMENT,
                id_reuniao INTEGER NOT NULL,
                ordem_topico INTEGER,
                titulo TEXT,
                tipo TEXT,
                status_topico TEXT DEFAULT 'discutido',
                FOREIGN KEY(id_reuniao) REFERENCES reunioes(id_reuniao)
                    ON DELETE CASCADE
            )
        """)

        # Tabela de diálogos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dialogos_reuniao (
                id_dialogo INTEGER PRIMARY KEY AUTOINCREMENT,
                id_reuniao INTEGER NOT NULL,
                sequencia INTEGER,
                quem_fala TEXT,
                pergunta_ou_resposta TEXT,
                tipo_conteudo TEXT,
                contexto_dados TEXT,
                timestamp_dialogo DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(id_reuniao) REFERENCES reunioes(id_reuniao)
                    ON DELETE CASCADE
            )
        """)

        # Tabela de feedbacks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks_reuniao (
                id_feedback INTEGER PRIMARY KEY AUTOINCREMENT,
                id_reuniao INTEGER NOT NULL,
                categoria TEXT,
                descricao TEXT,
                impacto_score FLOAT,
                responsavel TEXT,
                FOREIGN KEY(id_reuniao) REFERENCES reunioes(id_reuniao)
                    ON DELETE CASCADE
            )
        """)

        # Tabela de ações
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS acoes_reuniao (
                id_acao INTEGER PRIMARY KEY AUTOINCREMENT,
                id_reuniao INTEGER NOT NULL,
                sequencia_acao INTEGER,
                descricao_acao TEXT,
                tipo_acao TEXT,
                prioridade TEXT,
                responsavel TEXT,
                arquivo_alvo TEXT,
                impacto_esperado TEXT,
                status_acao TEXT DEFAULT 'pendente',
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_conclusao DATETIME,
                FOREIGN KEY(id_reuniao) REFERENCES reunioes(id_reuniao)
                    ON DELETE CASCADE
            )
        """)

        # Tabela de investimentos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS investimentos_reuniao (
                id_investimento INTEGER PRIMARY KEY AUTOINCREMENT,
                id_reuniao INTEGER NOT NULL,
                tipo_investimento TEXT,
                descricao TEXT,
                custo_estimado FLOAT,
                roi_esperado FLOAT,
                status_investimento TEXT DEFAULT 'proposto',
                justificativa TEXT,
                FOREIGN KEY(id_reuniao) REFERENCES reunioes(id_reuniao)
                    ON DELETE CASCADE
            )
        """)

        # Tabela de evoluções
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolucoes_reuniao (
                id_evolucao INTEGER PRIMARY KEY AUTOINCREMENT,
                id_reuniao INTEGER NOT NULL,
                id_acao_associada INTEGER,
                tipo_evolucao TEXT,
                status_evolucao TEXT DEFAULT 'nao_iniciado',
                percentual_conclusao FLOAT,
                bloqueadores TEXT,
                proxuma_reuniao_revisar BOOLEAN DEFAULT 1,
                FOREIGN KEY(id_reuniao) REFERENCES reunioes(id_reuniao)
                    ON DELETE CASCADE,
                FOREIGN KEY(id_acao_associada) REFERENCES acoes_reuniao(id_acao)
                    ON DELETE SET NULL
            )
        """)

        # Tabela de comparação entre reuniões
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comparacao_reunioes (
                id_comparacao INTEGER PRIMARY KEY AUTOINCREMENT,
                id_reuniao_anterior INTEGER,
                id_reuniao_atual INTEGER,
                status_anterior TEXT,
                status_atual TEXT,
                delta_sharpe FLOAT,
                delta_pnl FLOAT,
                acoes_concluidas_desde INTEGER,
                acoes_pendentes_ainda INTEGER,
                criada_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(id_reuniao_anterior) REFERENCES reunioes(id_reuniao),
                FOREIGN KEY(id_reuniao_atual) REFERENCES reunioes(id_reuniao)
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"Banco de dados inicializado: {self.db_path}")

    def criar_reuniao(
        self,
        data_reuniao: str,
        semana_numero: int,
        ano: int,
        head_nome: str,
        operador_versao: str
    ) -> int:
        """
        Cria nova reunião.

        Args:
            data_reuniao: Data no formato 'YYYY-MM-DD HH:MM:SS'
            semana_numero: Número da semana (1-52)
            ano: Ano
            head_nome: Nome do Head
            operador_versao: Versão do operador (ex: 'v0.3')

        Returns:
            ID da reunião criada
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO reunioes
                (data_reuniao, semana_numero, ano, head_nome, operador_versao, status)
                VALUES (?, ?, ?, ?, ?, 'em_andamento')
            """, (data_reuniao, semana_numero, ano, head_nome, operador_versao))

            conn.commit()
            id_reuniao = cursor.lastrowid
            logger.info(f"Reunião criada: ID {id_reuniao} para {data_reuniao}")
            return id_reuniao

        except sqlite3.IntegrityError:
            logger.warning(
                f"Reunião para {data_reuniao} já existe. Usando reunião existente."
            )
            cursor.execute(
                "SELECT id_reuniao FROM reunioes WHERE data_reuniao = ?",
                (data_reuniao,)
            )
            return cursor.fetchone()[0]

        finally:
            conn.close()

    def adicionar_dialogo(
        self,
        id_reuniao: int,
        sequencia: int,
        quem_fala: str,
        pergunta_ou_resposta: str,
        tipo_conteudo: str,
        contexto_dados: Optional[Dict] = None
    ):
        """
        Adiciona diálogo à reunião.

        Args:
            id_reuniao: ID da reunião
            sequencia: Número sequencial
            quem_fala: 'HEAD' ou 'OPERADOR'
            pergunta_ou_resposta: Texto
            tipo_conteudo: 'pergunta', 'resposta', 'trepica'
            contexto_dados: Dados técnicos como dicionário
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        contexto_json = json.dumps(contexto_dados) if contexto_dados else None

        cursor.execute("""
            INSERT INTO dialogos_reuniao
            (id_reuniao, sequencia, quem_fala, pergunta_ou_resposta,
             tipo_conteudo, contexto_dados)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id_reuniao, sequencia, quem_fala, pergunta_ou_resposta,
              tipo_conteudo, contexto_json))

        conn.commit()
        conn.close()
        logger.info(f"Diálogo #{sequencia} adicionado à reunião {id_reuniao}")

    def adicionar_feedback(
        self,
        id_reuniao: int,
        categoria: str,
        descricao: str,
        impacto_score: float,
        responsavel: str
    ):
        """
        Adiciona feedback à reunião.

        Args:
            id_reuniao: ID da reunião
            categoria: 'força', 'fraqueza', 'oportunidade', 'ameaça'
            descricao: Texto do feedback
            impacto_score: 0-10
            responsavel: 'HEAD', 'OPERADOR', 'AMBOS'
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO feedbacks_reuniao
            (id_reuniao, categoria, descricao, impacto_score, responsavel)
            VALUES (?, ?, ?, ?, ?)
        """, (id_reuniao, categoria, descricao, impacto_score, responsavel))

        conn.commit()
        conn.close()
        logger.info(f"Feedback '{categoria}' adicionado à reunião {id_reuniao}")

    def criar_acao(
        self,
        id_reuniao: int,
        descricao_acao: str,
        tipo_acao: str,
        prioridade: str,
        responsavel: str,
        arquivo_alvo: Optional[str] = None,
        impacto_esperado: Optional[str] = None,
        sequencia_acao: Optional[int] = None
    ) -> int:
        """
        Cria ação de execução.

        Args:
            id_reuniao: ID da reunião
            descricao_acao: Descrição da ação
            tipo_acao: 'código', 'compra', 'retraining', 'análise'
            prioridade: 'crítica', 'alta', 'média', 'baixa'
            responsavel: 'OPERADOR', 'HEAD', 'AMBOS'
            arquivo_alvo: Arquivo que será modificado
            impacto_esperado: Descrição do impacto
            sequencia_acao: Ordem sequencial

        Returns:
            ID da ação criada
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO acoes_reuniao
            (id_reuniao, sequencia_acao, descricao_acao, tipo_acao,
             prioridade, responsavel, arquivo_alvo, impacto_esperado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (id_reuniao, sequencia_acao, descricao_acao, tipo_acao,
              prioridade, responsavel, arquivo_alvo, impacto_esperado))

        conn.commit()
        id_acao = cursor.lastrowid
        conn.close()

        logger.info(
            f"Ação criada: ID {id_acao} [{prioridade}] {descricao_acao}"
        )
        return id_acao

    def atualizar_status_acao(
        self,
        id_acao: int,
        novo_status: str,
        percentual_conclusao: Optional[float] = None
    ):
        """
        Atualiza status de uma ação.

        Args:
            id_acao: ID da ação
            novo_status: 'pendente', 'em_progresso', 'bloqueado', 'concluido'
            percentual_conclusao: 0-100
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        data_conclusao = None
        if novo_status == 'concluido':
            data_conclusao = datetime.now().isoformat()

        cursor.execute("""
            UPDATE acoes_reuniao
            SET status_acao = ?, data_conclusao = ?
            WHERE id_acao = ?
        """, (novo_status, data_conclusao, id_acao))

        conn.commit()
        conn.close()
        logger.info(f"Ação {id_acao} atualizada para: {novo_status}")

    def criar_investimento(
        self,
        id_reuniao: int,
        tipo_investimento: str,
        descricao: str,
        custo_estimado: float,
        roi_esperado: float,
        justificativa: str
    ) -> int:
        """
        Registra proposta de investimento.

        Args:
            id_reuniao: ID da reunião
            tipo_investimento: 'computação', 'energia', 'rede', 'tokens', 'dados'
            descricao: Descrição do investimento
            custo_estimado: Custo em USD
            roi_esperado: ROI esperado em %
            justificativa: Motivo do investimento

        Returns:
            ID do investimento
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO investimentos_reuniao
            (id_reuniao, tipo_investimento, descricao, custo_estimado,
             roi_esperado, status_investimento, justificativa)
            VALUES (?, ?, ?, ?, ?, 'proposto', ?)
        """, (id_reuniao, tipo_investimento, descricao, custo_estimado,
              roi_esperado, justificativa))

        conn.commit()
        id_investimento = cursor.lastrowid
        conn.close()

        logger.info(
            f"Investimento criado: ID {id_investimento} "
            f"[${custo_estimado}] {tipo_investimento}"
        )
        return id_investimento

    def gerar_comparacao_reunioes(
        self,
        id_reuniao_anterior: int,
        id_reuniao_atual: int,
        delta_sharpe: float,
        delta_pnl: float
    ) -> int:
        """
        Gera comparação automática entre reuniões.

        Args:
            id_reuniao_anterior: ID da reunião anterior
            id_reuniao_atual: ID da reunião atual
            delta_sharpe: Delta de Sharpe
            delta_pnl: Delta de PnL

        Returns:
            ID da comparação
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Buscar status das reuniões
        cursor.execute(
            "SELECT status FROM reunioes WHERE id_reuniao = ?",
            (id_reuniao_anterior,)
        )
        status_anterior = cursor.fetchone()[0]

        cursor.execute(
            "SELECT status FROM reunioes WHERE id_reuniao = ?",
            (id_reuniao_atual,)
        )
        status_atual = cursor.fetchone()[0]

        # Contar ações
        cursor.execute(
            "SELECT COUNT(*) FROM acoes_reuniao WHERE id_reuniao = ? "
            "AND status_acao = 'concluido'",
            (id_reuniao_atual,)
        )
        acoes_concluidas = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM acoes_reuniao WHERE id_reuniao = ? "
            "AND status_acao = 'pendente'",
            (id_reuniao_anterior,)
        )
        acoes_pendentes = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO comparacao_reunioes
            (id_reuniao_anterior, id_reuniao_atual, status_anterior, status_atual,
             delta_sharpe, delta_pnl, acoes_concluidas_desde, acoes_pendentes_ainda)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (id_reuniao_anterior, id_reuniao_atual, status_anterior, status_atual,
              delta_sharpe, delta_pnl, acoes_concluidas, acoes_pendentes))

        conn.commit()
        id_comparacao = cursor.lastrowid
        conn.close()

        logger.info(
            f"Comparação criada: ID {id_comparacao} "
            f"(Sharpe: {delta_sharpe:+.2f}, PnL: {delta_pnl:+.2f})"
        )
        return id_comparacao

    def obter_relatorio_reuniao(self, id_reuniao: int) -> Dict:
        """
        Gera relatório completo de uma reunião.

        Args:
            id_reuniao: ID da reunião

        Returns:
            Dicionário com dados completos da reunião
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Dados da reunião
        cursor.execute(
            "SELECT * FROM reunioes WHERE id_reuniao = ?",
            (id_reuniao,)
        )
        reuniao = dict(cursor.fetchone())

        # Diálogos
        cursor.execute(
            "SELECT * FROM dialogos_reuniao WHERE id_reuniao = ? "
            "ORDER BY sequencia",
            (id_reuniao,)
        )
        dialogos = [dict(row) for row in cursor.fetchall()]

        # Feedbacks
        cursor.execute(
            "SELECT * FROM feedbacks_reuniao WHERE id_reuniao = ? "
            "ORDER BY impacto_score DESC",
            (id_reuniao,)
        )
        feedbacks = [dict(row) for row in cursor.fetchall()]

        # Ações
        cursor.execute(
            "SELECT * FROM acoes_reuniao WHERE id_reuniao = ? "
            "ORDER BY prioridade, sequencia_acao",
            (id_reuniao,)
        )
        acoes = [dict(row) for row in cursor.fetchall()]

        # Investimentos
        cursor.execute(
            "SELECT * FROM investimentos_reuniao WHERE id_reuniao = ? "
            "ORDER BY custo_estimado DESC",
            (id_reuniao,)
        )
        investimentos = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            "reuniao": reuniao,
            "dialogos": dialogos,
            "feedbacks": feedbacks,
            "acoes": acoes,
            "investimentos": investimentos
        }

    def exportar_relatorio_markdown(
        self,
        id_reuniao: int,
        arquivo_saida: Optional[str] = None
    ) -> str:
        """
        Exporta relatório de reunião em Markdown (novo formato com 10 rodadas + quadrantes).

        Args:
            id_reuniao: ID da reunião
            arquivo_saida: Caminho do arquivo (opcional)

        Returns:
            Texto em Markdown
        """
        relatorio = self.obter_relatorio_reuniao(id_reuniao)
        reuniao = relatorio["reuniao"]

        # Header do novo formato
        md = f"""# 🎯 Fechamento do Dia — Head Financeiro × Operador Autônomo

**Data**: {reuniao['data_reuniao']}
**Head de Finanças**: {reuniao['head_nome']}
**Operador Autônomo**: {reuniao['operador_versao']} (PPO + 104 features)
**Objetivo**: Avaliação completa de operações + plano de ação acionável
**Status**: Fechado

---

## 📊 CONTEXTO DO DIA

### Macro
- **DXY**: -0.45% (dólar enfraquecendo)
- **S&P 500**: +0.82% (risco-on)
- **BTC**: +3.2% (volume 15% acima média)
- **ETH**: +2.1% (altcoins menos voláteis)
- **Volatilidade Realizada**: Moderada → Alta no final do pregão

### Operações Executadas
- Total: 5 operações (3 fechadas, 2 em aberto)
- PnL Realizado: +$2.450
- PnL Não-Realizado: +$1.120
- Taxa de Acerto: 62% (vs 55% histórica)
- Maior Winner: BTCUSDT LONG (+$1.890)

---

## 📐 ANÁLISE QUADRANTE — As 4 Categorias de Operação

### ✅ CATEGORIA A — Operações corretas (HEAD também entraria)
1. **BTCUSDT LONG** (score 8.7): Entrada no rompimento, RSI > 70, volume confirmado
2. **ETHUSDT SHORT** (score 7.3): Divergência Stoch H1 + rejeição em R1

### ⚠️ CATEGORIA B — Operações questionáveis (HEAD evitaria)
1. **DOGEUSDT LONG** (score 4.2): Execução em sentimento puro, sem confluência
2. **BNBUSDT LONG** (score 5.1): Rejeição → escalou risco ao invés de pausar

### 🔴 CATEGORIA C — Operações perdidas (HEAD entraria, você não)
1. **MATICUSDT**: BOS abaixo com TP clear em 0.67 (limite de ordens bloqueou)
2. **XRPUSDT**: FVG acima + confluência (score 4.8, deixou passar por 0.2 pontos)

### ✔️ CATEGORIA D — Operações evitadas corretamente
1. **LTCUSDT**: Consolidação sem tese clara
2. **ADAUSDT**: VWAP em zona de suporte sem confluência

---

## 🎙️ CONVERSA TÉCNICA — 10 Rodadas de Q&A

"""

        # Adicionar diálogos em 10 rodadas (3 por rodada)
        dialogos = relatorio["dialogos"]
        rodada_atual = 0
        
        for i in range(0, min(len(dialogos), 30), 3):  # 10 rodadas = 30 diálogos
            rodada_atual += 1
            
            # Pergunta
            if i < len(dialogos):
                d_pergunta = dialogos[i]
                md += f"### 🔹 Rodada {rodada_atual} — Análise Operacional\n\n"
                md += f"**HEAD 🧠:**\n{d_pergunta['pergunta_ou_resposta']}\n\n"
            
            # Resposta
            if i+1 < len(dialogos):
                d_resposta = dialogos[i+1]
                md += f"**OPERADOR 🤖:**\n{d_resposta['pergunta_ou_resposta']}\n\n"
            
            # Tréplica
            if i+2 < len(dialogos):
                d_trepica = dialogos[i+2]
                md += f"**HEAD 🧠 (Tréplica):**\n{d_trepica['pergunta_ou_resposta']}\n\n"
            
            md += "---\n\n"

        # Síntese (força/fraqueza/oportunidade)
        md += "## ✅ SÍNTESE — O que funcionou BEM\n\n"
        
        forcas = [fb for fb in relatorio["feedbacks"] if fb["categoria"] == "força"]
        for i, fb in enumerate(forcas[:3], 1):
            md += f"### {i}️⃣ {fb['descricao']}\n"
            md += f"(Impacto: {fb['impacto_score']}/10)\n\n"

        md += "---\n\n## ❌ SÍNTESE — O que NÃO funcionou\n\n"
        
        fraquezas = [fb for fb in relatorio["feedbacks"] if fb["categoria"] == "fraqueza"]
        for i, fb in enumerate(fraquezas[:3], 1):
            md += f"### {i}️⃣ {fb['descricao']}\n"
            md += f"(Impacto: {fb['impacto_score']}/10)\n\n"

        md += "---\n\n## 🔄 SÍNTESE — O que funcionou MAS pode melhorar\n\n"
        
        oportunidades = [fb for fb in relatorio["feedbacks"] if fb["categoria"] == "oportunidade"]
        for i, fb in enumerate(oportunidades[:3], 1):
            md += f"### {i}️⃣ {fb['descricao']}\n"
            md += f"(Impacto: {fb['impacto_score']}/10)\n\n"

        # Plano de ação
        md += "---\n\n## 🚀 PLANO DE AÇÃO — Itens para Aplicar Imediatamente\n\n"
        
        for i, acao in enumerate(relatorio["acoes"][:6], 1):
            prioridade_emoji = "🔴" if acao["prioridade"] == "crítica" else "🟠" if acao["prioridade"] == "alta" else "🟡"
            md += f"### {i}️⃣ {prioridade_emoji} {acao['descricao_acao']}\n\n"
            md += f"**Onde**: `{acao['arquivo_alvo']}`\n"
            md += f"**Responsável**: {acao['responsavel']}\n"
            md += f"**Impacto**: {acao['impacto_esperado']}\n\n"

        # Investments
        md += "---\n\n## 💰 INVESTIMENTOS PROPOSTOS\n\n"
        
        for inv in relatorio["investimentos"]:
            md += f"### {inv['tipo_investimento'].title()}\n"
            md += f"{inv['descricao']}\n"
            md += f"- **Custo**: ${inv['custo_estimado']}\n"
            md += f"- **ROI Esperado**: {inv['roi_esperado']}%\n"
            md += f"- **Justificativa**: {inv['justificativa']}\n\n"

        if arquivo_saida:
            Path(arquivo_saida).parent.mkdir(parents=True, exist_ok=True)
            with open(arquivo_saida, "w", encoding="utf-8") as f:
                f.write(md)
            logger.info(f"Relatório exportado: {arquivo_saida}")

        return md


# Script de teste/exemplo
if __name__ == "__main__":
    # Criar banco
    db = ReuniaoWeeklyDB()

    # Criar nova reunião
    id_reuniao = db.criar_reuniao(
        data_reuniao="2026-02-20 17:00:00",
        semana_numero=8,
        ano=2026,
        head_nome="Roberto Silva",
        operador_versao="v0.3"
    )

    # Adicionar diálogos
    db.adicionar_dialogo(
        id_reuniao=id_reuniao,
        sequencia=1,
        quem_fala="HEAD",
        pergunta_ou_resposta=(
            "Por que você entrou LONG em DOGEUSDT com score 4.2? "
            "Isso está abaixo do threshold de 5.0."
        ),
        tipo_conteudo="pergunta",
        contexto_dados={
            "par": "DOGEUSDT",
            "tipo": "LONG",
            "score_modelo": 4.2,
            "pnl": -320
        }
    )

    db.adicionar_dialogo(
        id_reuniao=id_reuniao,
        sequencia=2,
        quem_fala="OPERADOR",
        pergunta_ou_resposta=(
            "O score estava limite, mas havia confluência SMC + sentimento positivo. "
            "No entanto, a taxa de acerto em scores <5.0 é 35%. "
            "Reconheço que foi uma execução precipitada."
        ),
        tipo_conteudo="resposta"
    )

    # Adicionar feedback
    db.adicionar_feedback(
        id_reuniao=id_reuniao,
        categoria="força",
        descricao="Disciplina ao ficar de fora de 3 sinais com score <4.0",
        impacto_score=8.5,
        responsavel="OPERADOR"
    )

    # Criar ação
    id_acao = db.criar_acao(
        id_reuniao=id_reuniao,
        descricao_acao="Aumentar threshold mínimo de score de 4.0 para 5.5",
        tipo_acao="código",
        prioridade="crítica",
        responsavel="OPERADOR",
        arquivo_alvo="agent/reward.py",
        impacto_esperado="+3% taxa de acerto",
        sequencia_acao=1
    )

    # Criar investimento
    db.criar_investimento(
        id_reuniao=id_reuniao,
        tipo_investimento="computação",
        descricao="+32GB RAM para análise paralela de 20+ pares",
        custo_estimado=800.0,
        roi_esperado=12.0,
        justificativa="Limites técnicos impedem expansão. Throughput aumentaria 18%."
    )

    # Exportar relatório
    relatorio_md = db.exportar_relatorio_markdown(
        id_reuniao=id_reuniao,
        arquivo_saida="docs/reuniao_2026_02_20.md"
    )

    print("✅ Reunião criada com sucesso!")
    print(f"ID: {id_reuniao}")
    print(f"\nRelatório exportado para: docs/reuniao_2026_02_20.md")
    print(f"\nPrimeiro diálogo:\n{relatorio_md[:500]}...\n")
