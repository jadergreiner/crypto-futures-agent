#!/usr/bin/env python3
"""
Executor de Reunião Semanal Completa
Head Financeiro × Operador Autônomo (Crypto Futures)

Funciones:
1. Carrega dados de performance da semana
2. Busca reunião anterior para comparação
3. Prepara prompt com contexto
4. Executa conversa simulada (HEAD × OPERADOR)
5. Registra diálogos, feedbacks, ações, investimentos
6. Exporta relatório markdown
7. Sincroniza em git com tag [SYNC]
"""

import json
import os
import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Importar módulo de reuniões
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.reuniao_manager import ReuniaoWeeklyDB

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/reuniao_execucao.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ExecutorReuniaoSemanal:
    """Executa reunião semanal completa."""

    def __init__(self, data_reuniao: Optional[str] = None):
        """
        Inicializa executor.

        Args:
            data_reuniao: Data no formato 'YYYY-MM-DD HH:MM:SS'.
                         Se None, usa próxima sexta-feira às 17:00.
        """
        self.data_reuniao = data_reuniao or self._calcular_proxima_sexta()
        self.db = ReuniaoWeeklyDB()
        self.id_reuniao: Optional[int] = None

        # Extrair semana/ano da data
        dt = datetime.fromisoformat(self.data_reuniao)
        self.semana_numero = dt.isocalendar()[1]
        self.ano = dt.isocalendar()[0]

        logger.info(f"Executor inicializado para: {self.data_reuniao}")

    def _calcular_proxima_sexta(self) -> str:
        """Calcula próxima sexta-feira às 17:00 BRT."""
        agora = datetime.now()
        dias_para_sexta = (4 - agora.weekday()) % 7
        if dias_para_sexta == 0 and agora.hour >= 17:
            dias_para_sexta = 7

        proxima_sexta = agora + timedelta(days=dias_para_sexta)
        proxima_sexta = proxima_sexta.replace(hour=17, minute=0, second=0)
        return proxima_sexta.isoformat(sep=" ")

    def carregar_metricas_semana(self) -> Dict:
        """
        Carrega métricas de performance da semana.

        Returns:
            Dicionário com PnL, Sharpe, drawdown, etc.
        """
        logger.info("Carregando métricas de performance da semana...")

        # PLACEHOLDER: Em produção, buscar dados reais do banco
        # Por enquanto, simular dados
        metricas = {
            "periodo": {
                "data_inicio": (
                    datetime.now() - timedelta(days=7)
                ).isoformat(sep=" "),
                "data_fim": datetime.now().isoformat(sep=" ")
            },
            "globais": {
                "pnl_usdt": 12450.75,
                "pnl_percentual": 2.15,
                "sharpe_ratio": 1.82,
                "max_drawdown": 3.2,
                "taxa_acertos": 0.62,
                "num_operacoes": 45,
                "pares_operados": 12
            },
            "por_par": [
                {
                    "par": "BTCUSDT",
                    "pnl": 5200.00,
                    "operacoes": 8,
                    "taxa_acerto": 0.75
                },
                {
                    "par": "ETHUSDT",
                    "pnl": 3100.00,
                    "operacoes": 6,
                    "taxa_acerto": 0.67
                }
            ]
        }

        logger.info(
            f"Métricas carregadas: "
            f"PnL={metricas['globais']['pnl_usdt']:.2f} USDT, "
            f"Sharpe={metricas['globais']['sharpe_ratio']:.2f}"
        )
        return metricas

    def carregar_reuniao_anterior(self) -> Optional[Dict]:
        """
        Busca reunião anterior para comparação.

        Returns:
            Dados da reunião anterior ou None
        """
        logger.info("Buscando reunião anterior...")

        conn = sqlite3.connect("db/reunioes_weekly.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Buscar reunião anterior (até 2 semanas atrás)
        cursor.execute("""
            SELECT id_reuniao, data_reuniao, semana_numero
            FROM reunioes
            ORDER BY data_reuniao DESC
            LIMIT 1
        """)

        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            logger.info(f"Reunião anterior encontrada: {resultado['data_reuniao']}")
            return dict(resultado)

        logger.warning("Nenhuma reunião anterior encontrada (primeira semana?)")
        return None

    def montar_prompt_contexto(
        self,
        metricas: Dict,
        reuniao_anterior: Optional[Dict]
    ) -> str:
        """
        Monta prompt com contexto completo.

        Args:
            metricas: Dados de performance
            reuniao_anterior: Dados da reunião anterior

        Returns:
            Prompt pronto para ser enviado ao LLM
        """
        logger.info("Montando prompt de contexto...")

        # Ler template base
        template_path = Path(
            "prompts/prompts_reuniao_head_operador_crypto_futures.md"
        )
        if not template_path.exists():
            logger.error(f"Template não encontrado: {template_path}")
            return ""

        with open(template_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        # Interpolação segura (sem format() que quebra com placeholders complexos)
        prompt = prompt.replace("{DATA_REUNIAO}", self.data_reuniao)
        prompt = prompt.replace("{SEMANA_NUMERO}", str(self.semana_numero))
        prompt = prompt.replace("{ANO}", str(self.ano))
        prompt = prompt.replace(
            "{PNL_SEMANA}",
            f"{metricas['globais']['pnl_usdt']:.2f}"
        )
        prompt = prompt.replace(
            "{PNL_PCT}",
            f"{metricas['globais']['pnl_percentual']:.2f}"
        )
        prompt = prompt.replace(
            "{SHARPE}",
            f"{metricas['globais']['sharpe_ratio']:.2f}"
        )
        prompt = prompt.replace(
            "{MAX_DRAWDOWN}",
            f"{metricas['globais']['max_drawdown']:.2f}"
        )

        logger.info("Prompt montado com sucesso")
        return prompt

    def criar_reuniao(
        self,
        head_nome: str = "Roberto Silva",
        operador_versao: str = "v0.3"
    ) -> int:
        """
        Cria nova reunião no banco.

        Args:
            head_nome: Nome do Head Financeiro
            operador_versao: Versão do operador

        Returns:
            ID da reunião criada
        """
        logger.info(f"Criando reunião {self.semana_numero}/{self.ano}...")

        self.id_reuniao = self.db.criar_reuniao(
            data_reuniao=self.data_reuniao,
            semana_numero=self.semana_numero,
            ano=self.ano,
            head_nome=head_nome,
            operador_versao=operador_versao
        )

        return self.id_reuniao

    def adicionar_dialogo_exemplo(self):
        """Adiciona dialogos de exemplo para teste."""
        if not self.id_reuniao:
            logger.error("Reunião não criada. Chame criar_reuniao() antes.")
            return

        logger.info("Adicionando diálogos de exemplo...")

        # Pergunta 1: Sobre operações com score baixo
        self.db.adicionar_dialogo(
            id_reuniao=self.id_reuniao,
            sequencia=1,
            quem_fala="HEAD",
            pergunta_ou_resposta=(
                "Vi que você executou DOGEUSDT LONG com score 4.2. "
                "Isso está abaixo do threshold de 5.0. Por quê?"
            ),
            tipo_conteudo="pergunta",
            contexto_dados={
                "par": "DOGEUSDT",
                "tipo": "LONG",
                "score": 4.2,
                "pnl": -320,
                "threshold_esperado": 5.0
            }
        )

        # Resposta 1
        self.db.adicionar_dialogo(
            id_reuniao=self.id_reuniao,
            sequencia=2,
            quem_fala="OPERADOR",
            pergunta_ou_resposta=(
                "O modelo apontou confluência SMC (liquidity sweep) + "
                "sentimento bullish no Telegram. No entanto, reconheço que "
                "a taxa de acerto em scores <5.0 foi apenas 35% (vs 62% geral). "
                "Operação precipitada. Peço que aumentemos o threshold."
            ),
            tipo_conteudo="resposta",
            contexto_dados={
                "taxa_acerto_lowscore": 0.35,
                "taxa_acerto_geral": 0.62,
                "razao": "Confluência fraca, execução por sentimento"
            }
        )

        # Tréplica
        self.db.adicionar_dialogo(
            id_reuniao=self.id_reuniao,
            sequencia=3,
            quem_fala="HEAD",
            pergunta_ou_resposta=(
                "Concordo. Score abaixo de 5.0 não têm edge estatístico. "
                "Ação: elevar MIN_ENTRY_SCORE de 4.0 para 5.5 em reward.py. "
                "Vamos reduzir volume mas aumentar taxa de acerto."
            ),
            tipo_conteudo="trepica"
        )

        logger.info("3 diálogos adicionados")

    def adicionar_feedback_exemplo(self):
        """Adiciona feedbacks de exemplo."""
        if not self.id_reuniao:
            logger.error("Reunião não criada. Chame criar_reuniao() antes.")
            return

        logger.info("Adicionando feedbacks de exemplo...")

        feedbacks = [
            {
                "categoria": "força",
                "descricao": "BTCUSDT LONG com score 8.7 — entrada perfeita, TP atingido",
                "impacto_score": 9.5,
                "responsavel": "OPERADOR"
            },
            {
                "categoria": "fraqueza",
                "descricao": "3 operações com score <5.0 — taxa de acerto 35%",
                "impacto_score": 8.0,
                "responsavel": "OPERADOR"
            },
            {
                "categoria": "oportunidade",
                "descricao": "0GUSDT teve BOS confirmado. Limite de 10 ordens impediu execução.",
                "impacto_score": 7.5,
                "responsavel": "OPERADOR"
            }
        ]

        for fb in feedbacks:
            self.db.adicionar_feedback(
                id_reuniao=self.id_reuniao,
                categoria=fb["categoria"],
                descricao=fb["descricao"],
                impacto_score=fb["impacto_score"],
                responsavel=fb["responsavel"]
            )

        logger.info(f"{len(feedbacks)} feedbacks adicionados")

    def adicionar_acoes_exemplo(self):
        """Adiciona ações de exemplo."""
        if not self.id_reuniao:
            logger.error("Reunião não criada. Chame criar_reuniao() antes.")
            return

        logger.info("Adicionando ações de exemplo...")

        acoes = [
            {
                "descricao": "Aumentar MIN_ENTRY_SCORE de 4.0 para 5.5",
                "tipo": "código",
                "prioridade": "crítica",
                "responsavel": "OPERADOR",
                "arquivo": "agent/reward.py",
                "impacto": "+3% taxa acerto, -5% volume",
                "seq": 1
            },
            {
                "descricao": "Investigar causa de latência em 3 rejeições de ordem",
                "tipo": "análise",
                "prioridade": "alta",
                "responsavel": "OPERADOR",
                "arquivo": "monitoring/critical_monitor_opção_c.py",
                "impacto": "Identificar gargalo de rede/API",
                "seq": 2
            }
        ]

        for acao in acoes:
            self.db.criar_acao(
                id_reuniao=self.id_reuniao,
                descricao_acao=acao["descricao"],
                tipo_acao=acao["tipo"],
                prioridade=acao["prioridade"],
                responsavel=acao["responsavel"],
                arquivo_alvo=acao["arquivo"],
                impacto_esperado=acao["impacto"],
                sequencia_acao=acao["seq"]
            )

        logger.info(f"{len(acoes)} ações criadas")

    def adicionar_investimentos_exemplo(self):
        """Adiciona investimentos de exemplo."""
        if not self.id_reuniao:
            logger.error("Reunião não criada. Chame criar_reuniao() antes.")
            return

        logger.info("Adicionando investimentos de exemplo...")

        investimentos = [
            {
                "tipo": "computação",
                "descricao": "+32GB RAM para análise paralela de 20+ pares",
                "custo": 800.0,
                "roi": 12.0,
                "justificativa": "Limite de 12 pares em paralelo. ROI: +18% throughput, +2.1% Sharpe"
            },
            {
                "tipo": "infraestrutura",
                "descricao": "Nobreak 1500W + gerador 5kW",
                "custo": 1200.0,
                "roi": -5.0,
                "justificativa": "Uptime 99.95% requer redundância. Queda = stop loss automático."
            },
            {
                "tipo": "rede",
                "descricao": "Conexão dedicada co-location Binance (IP fixo)",
                "custo": 200.0,
                "roi": 1.5,
                "justificativa": "Latência 19-21ms → 0.5ms. Less slippage em futuros."
            }
        ]

        for inv in investimentos:
            self.db.criar_investimento(
                id_reuniao=self.id_reuniao,
                tipo_investimento=inv["tipo"],
                descricao=inv["descricao"],
                custo_estimado=inv["custo"],
                roi_esperado=inv["roi"],
                justificativa=inv["justificativa"]
            )

        logger.info(f"{len(investimentos)} investimentos propostos")

    def exportar_relatorio(self, arquivo_saida: Optional[str] = None) -> str:
        """
        Exporta relatório completo em Markdown.

        Args:
            arquivo_saida: Caminho do arquivo. Se None, cria automático.

        Returns:
            Caminho do arquivo exportado
        """
        if not self.id_reuniao:
            logger.error("Reunião não criada. Chame criar_reuniao() antes.")
            return ""

        if not arquivo_saida:
            arquivo_saida = (
                f"docs/reuniao_{self.ano}_{self.semana_numero:02d}"
                f"_sem{self.semana_numero}.md"
            )

        logger.info(f"Exportando relatório: {arquivo_saida}...")

        md = self.db.exportar_relatorio_markdown(
            id_reuniao=self.id_reuniao,
            arquivo_saida=arquivo_saida
        )

        logger.info(f"Relatório exportado com sucesso")
        return arquivo_saida

    def executar_fluxo_completo(self):
        """Executa fluxo completo de reunião."""
        logger.info("=" * 80)
        logger.info("INICIANDO FLUXO COMPLETO DE REUNIÃO SEMANAL")
        logger.info("=" * 80)

        try:
            # Passo 1: Carregar dados
            logger.info("\n[PASSO 1/7] Carregando métricas...")
            metricas = self.carregar_metricas_semana()

            # Passo 2: Buscar reunião anterior
            logger.info("\n[PASSO 2/7] Buscando reunião anterior...")
            reuniao_anterior = self.carregar_reuniao_anterior()

            # Passo 3: Montar prompt
            logger.info("\n[PASSO 3/7] Montando prompt de contexto...")
            prompt = self.montar_prompt_contexto(metricas, reuniao_anterior)

            # Passo 4: Criar reunião
            logger.info("\n[PASSO 4/7] Criando reunião no banco...")
            self.criar_reuniao()

            # Passo 5: Adicionar conteúdos
            logger.info("\n[PASSO 5/7] Adicionando diálogos, feedbacks, ações...")
            self.adicionar_dialogo_exemplo()
            self.adicionar_feedback_exemplo()
            self.adicionar_acoes_exemplo()
            self.adicionar_investimentos_exemplo()

            # Passo 6: Exportar relatório
            logger.info("\n[PASSO 6/7] Exportando relatório markdown...")
            arquivo_relatorio = self.exportar_relatorio()

            # Passo 7: Resumo final
            logger.info("\n[PASSO 7/7] Resumo final...")
            self._imprimir_resumo(arquivo_relatorio)

            logger.info("\n" + "=" * 80)
            logger.info("✅ FLUXO COMPLETO DE REUNIÃO CONCLUÍDO COM SUCESSO")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"❌ Erro durante execução: {e}", exc_info=True)
            raise

    def _imprimir_resumo(self, arquivo_relatorio: str):
        """Imprime resumo da reunião."""
        relatorio = self.db.obter_relatorio_reuniao(self.id_reuniao)

        print("\n" + "=" * 80)
        print("📋 RESUMO DE REUNIÃO")
        print("=" * 80)
        print(f"\nData: {self.data_reuniao}")
        print(f"Semana: {self.semana_numero}/{self.ano}")
        print(f"Reunião ID: {self.id_reuniao}")
        print(f"\n📊 Estrutura:")
        print(f"   - Diálogos: {len(relatorio['dialogos'])}")
        print(f"   - Feedbacks: {len(relatorio['feedbacks'])}")
        print(f"   - Ações: {len(relatorio['acoes'])}")
        print(f"   - Investimentos: {len(relatorio['investimentos'])}")
        print(f"\n📄 Arquivo exportado: {arquivo_relatorio}")
        print("\n" + "=" * 80 + "\n")


def main():
    """Função principal."""
    try:
        executor = ExecutorReuniaoSemanal()
        executor.executar_fluxo_completo()

    except KeyboardInterrupt:
        logger.warning("Interrupção do usuário")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
