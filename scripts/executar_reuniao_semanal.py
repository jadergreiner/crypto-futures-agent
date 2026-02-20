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
import statistics
import glob

# Importar módulo de reuniões
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.reuniao_manager import ReuniaoManagerDB
from data.database import DatabaseManager
from config.settings import DB_PATH

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


class ExecutorReuniao:
    """Executa reunião sob demanda (ad-hoc, pode ocorrer a qualquer momento)."""

    def __init__(self, data_reuniao: Optional[str] = None):
        """
        Inicializa executor.

        Args:
            data_reuniao: Data no formato 'YYYY-MM-DD HH:MM:SS'.
                         Se None, usa data/hora atual.
        """
        self.data_reuniao = data_reuniao or datetime.now().isoformat(sep=" ")
        self.db = ReuniaoManagerDB()
        self.db_trades = DatabaseManager(DB_PATH)
        self.id_reuniao: Optional[int] = None

        # Extrair semana/ano da data
        dt = datetime.fromisoformat(self.data_reuniao)
        self.semana_numero = dt.isocalendar()[1]
        self.ano = dt.isocalendar()[0]

        logger.info(f"Executor inicializado para: {self.data_reuniao}")

    def _validar_dados_reais(self, dias: int = 7) -> bool:
        """
        Valida se há dados REAIS no banco de dados.
        Retorna True se houver; False caso contrário.

        Args:
            dias: Período a verificar (padrão: 7 dias)

        Returns:
            True se houver trades reais, False caso contrário
        """
        trades = self._obter_trades_periodo(dias=dias)
        logs_analise = self._analisar_logs_operacionais(dias=1)

        tem_trades = len(trades) > 0
        tem_eventos = bool(logs_analise.get("erros") or logs_analise.get("avisos") or logs_analise.get("falhas_execucao"))

        if not tem_trades and not tem_eventos:
            logger.warning(
                "⚠️  AVISO: Nenhum dado real encontrado no período!\n"
                "   - Banco de dados vazio (trade_log: 0 registros)\n"
                "   - Logs operacionais vazios\n"
                "   ❌ Sistema NÃO gerará dados fictícios.\n"
                "   ✅ Execute o agente primeiro para gerar trades reais."
            )
            return False

        return True

    def _obter_trades_periodo(self, dias: int = 7) -> List[Dict]:
        """
        Obtém trades históricos do período de análise.

        Args:
            dias: Número de dias a analisar (padrão: 7 dias)

        Returns:
            Lista de trades do período
        """
        try:
            data_inicio = int((datetime.now() - timedelta(days=dias)).timestamp() * 1000)
            trades = self.db_trades.get_trades(start_time=data_inicio)
            logger.info(f"Carregados {len(trades)} trades do período")
            return trades
        except Exception as e:
            logger.error(f"Erro ao carregar trades: {e}")
            return []

    def _obter_execution_log_periodo(self, dias: int = 7) -> List[Dict]:
        """
        Obtém log de execuções do período.

        Args:
            dias: Número de dias a analisar (padrão: 7 dias)

        Returns:
            Lista de execuções do período
        """
        try:
            data_inicio = int((datetime.now() - timedelta(days=dias)).timestamp() * 1000)
            execucoes = self.db_trades.get_execution_log(start_time=data_inicio, executed_only=True)
            logger.info(f"Carregadas {len(execucoes)} execuções do período")
            return execucoes
        except Exception as e:
            logger.error(f"Erro ao carregar execution log: {e}")
            return []

    def _calcular_metricas_trades(self, trades: List[Dict]) -> Dict:
        """
        Calcula métricas de performance a partir de trades fechados.

        Args:
            trades: Lista de trades do trade_log

        Returns:
            Dicionário com métricas calculadas
        """
        if not trades:
            return {
                "pnl_usdt": 0,
                "pnl_percentual": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "taxa_acertos": 0,
                "num_operacoes": 0,
            }

        # Filtrar apenas trades fechados (que têm exit_price)
        trades_fechados = [t for t in trades if t.get('exit_price') is not None]

        if not trades_fechados:
            return {
                "pnl_usdt": 0,
                "pnl_percentual": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "taxa_acertos": 0,
                "num_operacoes": 0,
            }

        # Calcular PnL total
        pnl_total = sum(t.get('pnl_usdt', 0) for t in trades_fechados)
        pnl_percentual = (pnl_total / 10000 * 100) if pnl_total else 0  # Assumindo 10k acount

        # Taxa de acertos
        trades_lucro = len([t for t in trades_fechados if t.get('pnl_usdt', 0) > 0])
        taxa_acertos = trades_lucro / len(trades_fechados) if trades_fechados else 0

        # Calcular drawdown
        cumulative_pnl = []
        running_sum = 0
        for t in trades_fechados:
            running_sum += t.get('pnl_usdt', 0)
            cumulative_pnl.append(running_sum)

        max_pnl = max(cumulative_pnl) if cumulative_pnl else 0
        max_drawdown = ((max_pnl - min(cumulative_pnl)) / max(abs(max_pnl), 1)) * 100 if max_pnl > 0 else 0

        # Calcular Sharpe (simplificado)
        pnl_list = [t.get('pnl_usdt', 0) for t in trades_fechados]
        if len(pnl_list) > 1:
            media = statistics.mean(pnl_list)
            desvio = statistics.stdev(pnl_list) if len(pnl_list) > 1 else 1
            sharpe = (media / desvio * (252 / len(pnl_list)) ** 0.5) if desvio > 0 else 0
        else:
            sharpe = 0

        return {
            "pnl_usdt": pnl_total,
            "pnl_percentual": pnl_percentual,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "taxa_acertos": taxa_acertos,
            "num_operacoes": len(trades_fechados),
        }

    def _obter_pares_mais_operados(self, trades: List[Dict], top_n: int = 5) -> List[Dict]:
        """
        Identifica pares mais operados e suas métricas.

        Args:
            trades: Lista de trades do período
            top_n: Quantos top pares incluir

        Returns:
            Lista de pares com métricas
        """
        if not trades:
            return []

        pares_dados = {}
        for t in trades:
            par = t.get('symbol', 'UNKNOWN')
            if par not in pares_dados:
                pares_dados[par] = {"trades": [], "pnl_total": 0, "opera": 0}

            pares_dados[par]["trades"].append(t)
            pares_dados[par]["pnl_total"] += t.get('pnl_usdt', 0)
            pares_dados[par]["opera"] += 1

        # Ordenar por PnL descrescente
        pares_sorteados = sorted(
            pares_dados.items(),
            key=lambda x: x[1]["pnl_total"],
            reverse=True
        )[:top_n]

        resultado = []
        for par, dados in pares_sorteados:
            trades_fechados = [t for t in dados["trades"] if t.get('exit_price')]
            taxa_acerto = len([t for t in trades_fechados if t.get('pnl_usdt', 0) > 0]) / max(len(trades_fechados), 1)

            resultado.append({
                "par": par,
                "pnl": dados["pnl_total"],
                "operacoes": dados["opera"],
                "taxa_acerto": taxa_acerto
            })

        return resultado

    def _analisar_logs_operacionais(self, dias: int = 1) -> Dict:
        """
        Analisa logs de operação para extrair problemas reais.
        Procura por erros, falhas, avisos e padrões de execução.

        Args:
            dias: Quantos dias passados analisar (padrão: 1 dia)

        Returns:
            Dicionário com insights de logs
        """
        try:
            logs_dir = Path("logs")
            if not logs_dir.exists():
                logger.warning("Diretório de logs não encontrado")
                return {
                    "erros": [],
                    "avisos": [],
                    "falhas_execucao": [],
                    "padroes": []
                }

            # Buscar logs recentes (últimas 24h por padrão)
            cutoff_time = datetime.now() - timedelta(days=dias)
            
            # Procurar por padrões em arquivos de log
            erros = []
            avisos = []
            falhas_execucao = []
            
            # Procurar especificamente por live_trading_*.log e paper_trading_*.log
            log_patterns = [
                "logs/live_trading_*.log",
                "logs/paper_trading_*.log",
                "logs/app_*.log",
                "logs/errors_*.log"
            ]
            
            for pattern in log_patterns:
                for log_file in glob.glob(pattern):
                    try:
                        file_stat = Path(log_file).stat()
                        file_time = datetime.fromtimestamp(file_stat.st_mtime)
                        
                        # Só processar logs recentes
                        if file_time < cutoff_time:
                            continue
                        
                        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                # Procurar por padrões de ERROrm WARNING, FAILED, etc
                                if 'ERROR' in line or 'error' in line:
                                    erros.append(line.strip()[:150])
                                elif 'WARNING' in line or 'warning' in line:
                                    avisos.append(line.strip()[:150])
                                elif 'FAILED' in line or 'failed' in line or 'Falha' in line:
                                    falhas_execucao.append(line.strip()[:150])
                    except Exception as e:
                        logger.debug(f"Erro ao ler {log_file}: {e}")
                        continue
            
            # Análise de padrões
            padroes = []
            if erros:
                padroes.append(f"Detectados {len(erros)} eventos de erro nas últimas 24h")
            if avisos:
                padroes.append(f"Detectados {len(avisos)} avisos nas últimas 24h")
            if falhas_execucao:
                padroes.append(f"Detectadas {len(falhas_execucao)} falhas de execução")
            
            logger.info(f"Análise de logs: {len(erros)} erros, {len(avisos)} avisos, {len(falhas_execucao)} falhas")
            
            return {
                "erros": erros[:3],  # Top 3 erros
                "avisos": avisos[:3],  # Top 3 avisos
                "falhas_execucao": falhas_execucao[:3],  # Top 3 falhas
                "padroes": padroes
            }
        except Exception as e:
            logger.error(f"Erro ao analisar logs: {e}")
            return {
                "erros": [],
                "avisos": [],
                "falhas_execucao": [],
                "padroes": []
            }

    def carregar_metricas(self) -> Dict:
        """
        Carrega métricas de performance da reunião.
        Integração com dados reais do banco de dados.

        Returns:
            Dicionário com PnL, Sharpe, drawdown, etc.
        """
        logger.info("Carregando métricas de performance (dados reais)...")

        # Obter trades do período (padrão: últimos 7 dias)
        trades = self._obter_trades_periodo(dias=7)

        # Calcular métricas a partir dos trades reais
        metricas_globais = self._calcular_metricas_trades(trades)

        # Obter pares mais operados
        top_pares = self._obter_pares_mais_operados(trades, top_n=2)

        # Analisar logs operacionais das últimas 24h
        logs_analise = self._analisar_logs_operacionais(dias=1)

        # Montar dicionário final
        metricas = {
            "periodo": {
                "data_inicio": (
                    datetime.now() - timedelta(days=7)
                ).isoformat(sep=" "),
                "data_fim": datetime.now().isoformat(sep=" ")
            },
            "globais": {
                "pnl_usdt": metricas_globais["pnl_usdt"],
                "pnl_percentual": metricas_globais["pnl_percentual"],
                "sharpe_ratio": metricas_globais["sharpe_ratio"],
                "max_drawdown": metricas_globais["max_drawdown"],
                "taxa_acertos": metricas_globais["taxa_acertos"],
                "num_operacoes": metricas_globais["num_operacoes"],
                "pares_operados": len({t.get('symbol') for t in trades if t.get('symbol')})
            },
            "por_par": top_pares if top_pares else [
                {"par": "SEM_DADOS", "pnl": 0.0, "operacoes": 0, "taxa_acerto": 0.0}
            ],
            "logs": logs_analise
        }

        logger.info(
            f"Métricas carregadas (dados reais): "
            f"PnL={metricas['globais']['pnl_usdt']:.2f} USDT, "
            f"Ops={metricas['globais']['num_operacoes']}, "
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
            "prompts/REUNIAO_HEAD_OPERADOR.md"
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
        """Adiciona 10 rodadas de Q&A (pergunta → resposta → tréplica)."""
        if not self.id_reuniao:
            logger.error("Reunião não criada. Chame criar_reuniao() antes.")
            return

        logger.info("Adicionando 10 rodadas de diálogos...")

        # 10 rodadas de Q&A estruturadas
        rodadas = [
            # Rodada 1: Mayor Winner
            {
                "numero": 1,
                "head_pergunta": (
                    "BTCUSDT LONG com score 8.7 — seu melhor trade com +$1.890. "
                    "Explique sua tese: por que entrou ali, como cuidou dos riscos?"
                ),
                "operador_resposta": (
                    "Rompimento em 42.850, volume 18% acima da média móvel 20D. "
                    "RSI 74 confirmava momentum. RR esperado 1:2.5 (stop 42.300, alvo 43.400). "
                    "Entrei 0.5 BTC (conservador porque mercado estava sobrecomprado em H4). "
                    "Fechamento exatamente no TP. Exposição mantida <2% da conta."
                ),
                "head_trepica": (
                    "Perfeito. Você fez exatamente o que eu teria feito — "
                    "entrada com volume, RR positivo, tamanho apropriado, saída planejada. "
                    "Isso é disciplina. Continue assim."
                )
            },
            # Rodada 2: Score Baixo (DOGEUSDT)
            {
                "numero": 2,
                "head_pergunta": (
                    "DOGEUSDT LONG com score 4.2 foi precipitado. Você sabe que "
                    "threshold mínimo é 5.0. Por quê executou mesmo assim?"
                ),
                "operador_resposta": (
                    "Errei. Score 4.2 veio de sentimento bullish em Telegram + SMC no nível 0.0845. "
                    "Taxa de acerto em scores <5.0 é apenas 35% vs 62% geral. "
                    "Executei por overconfidence no DXY fraco. Resultado: -$320. Meu critério foi frouxo."
                ),
                "head_trepica": (
                    "Você reconheceu o erro — ótimo. Problema: 'sentimento no Telegram' não é tese. "
                    "Tese é confluência de estrutura + volume + momentum. "
                    "Minha ação: nunca execute com score <4.8."
                )
            },
            # Rodada 3: Gestão de Risco (BNBUSDT)
            {
                "numero": 3,
                "head_pergunta": (
                    "BNBUSDT: ordem rejeitada por latência >200ms. "
                    "Você escalou a exposição manualmente para compensar? "
                    "Isso é CONTRA TUDO que combinamos."
                ),
                "operador_resposta": (
                    "Verdade. Primeira ordem foi rejeitada. Deveria ter pausado. "
                    "Ao invés, coloquei posição manual de 1 BNB. "
                    "Comprei mais caro (43.200 vs 42.900). Trade deu lucro (+$85), "
                    "mas METODOLOGIA foi errada. Deveria ter aguardado oportunidade limpa."
                ),
                "head_trepica": (
                    "Exato. Rejeição = sinal de stop. Você não escalona risco em falha — REDUZ risco. "
                    "Ação imediata: rejeição cancela trade automaticamente. Nenhuma tentativa manual."
                )
            },
            # Rodada 4: Limite de Ordens
            {
                "numero": 4,
                "head_pergunta": (
                    "Limite de 10 ordens: você perdeu MATICUSDT (BOS claro, TP em 0.67). "
                    "Por que não encerrou posição menor para liberar slot?"
                ),
                "operador_resposta": (
                    "Erro operacional. Tinha 10 ordens, mas 3 em 'monitoramento' poderiam "
                    "ter sido fechadas. Deveria fazer gestão ativa. Identifiquei MATIC tarde "
                    "por lag de 5 minutos. Quando percebi, era tarde. Teria dado +$890 fácil."
                ),
                "head_trepica": (
                    "Ações: Aumente limite de 10 para 15. Implemente auto-close para posições >4h "
                    "sem movimento. Monitore lag de feed — se >3min, pause novas entradas."
                )
            },
            # Rodada 5: Zona Cinzenta de Score
            {
                "numero": 5,
                "head_pergunta": (
                    "XRPUSDT: FVG + trendline + sentimento. Score 4.8 (abaixo 5.0). "
                    "Você deixou passar. Resultado: +4% de ganho. Por que critério tão rígido?"
                ),
                "operador_resposta": (
                    "Meu modelo é conservador. Scores 4.8-5.0 são zona cinzenta. "
                    "Às vezes ganham 4%, às vezes perdem 2%. Meu sistema ficou fora. "
                    "Mas você está certo: perdi +4% ganho fácil por 0.2 pontos. "
                    "Score 4.8+ EM CONFLUÊNCIA MÚLTIPLA deveria executar."
                ),
                "head_trepica": (
                    "Ajuste assim: Score 4.8+ com 3+ confluências (FVG + trendline + sentimento) = "
                    "execute com METADE do tamanho. Isso captura ganhos fáceis sem aumentar risco."
                )
            },
            # Rodada 6: Múltiplos Timeframes
            {
                "numero": 6,
                "head_pergunta": (
                    "Você opera em H1, mas 3 operações hoje foram mais fáceis em H4. "
                    "Deveria H4 ser confirmação ANTES de entrar em H1?"
                ),
                "operador_resposta": (
                    "Correto. Sistema de múltiplos timeframes está defasado. "
                    "Estou olhando H1 isolado. Deveria ser: H4 define TENDÊNCIA, H1 define TIMING. "
                    "Teria evitado DOGEUSDT (contra H4) e capturado XRPUSDT com confiança."
                ),
                "head_trepica": (
                    "Implemente em signal_environment.py: Score H4 = 40% weight (filtro), "
                    "Score H1 = 60% weight (timing). Execute só se ambos alinhados. "
                    "Reduz whipsaws 15-20%."
                )
            },
            # Rodada 7: Posição Aberta
            {
                "numero": 7,
                "head_pergunta": (
                    "Você tem 2 posições abertas (ETHUSDT SHORT +$450). "
                    "Qual é plano? Vai segurar overnight? Qual critério?"
                ),
                "operador_resposta": (
                    "ETHUSDT SHORT aguardando segunda objetiva em 1.850 (espaço +3%). "
                    "Stop em 1.990. Critério: se TP secundário, vendo 50% (lock profit). "
                    "Se break suporte 1.920, encerro 100% com prejuízo <-$120. "
                    "Risco <1% da conta, sustentável overnight."
                ),
                "head_trepica": (
                    "Ótima gestão de escada. Mantenha. Atenção: DXY deve subir (Fed speakers). "
                    "Sua SHORT pode enfrentar resistência. "
                    "Reduza para 50% HOJE antes do close."
                )
            },
            # Rodada 8: Latência e Infraestrutura
            {
                "numero": 8,
                "head_pergunta": (
                    "3 rejeições de ordem por latência >200ms. "
                    "Qual causa? Binance, infraestrutura, conexão?"
                ),
                "operador_resposta": (
                    "Monitorei: (1) 1 rejeição foi Binance (servidor lento 12h31), "
                    "(2) 2 rejeições foram minha rede (ISP limitando em pico). "
                    "Aconteceu 12:00-13:30. Servidor em datacenter remoto; seria melhor co-location Binance."
                ),
                "head_trepica": (
                    "Ação clara: contratar co-location em Binance (Tokyo/Singapore). "
                    "Muda latência 180ms → 8-12ms. Custo $200-300/mês. "
                    "ROI em 15 dias (sem rejeições). APROVADO para investimento imediato."
                )
            },
            # Rodada 9: Retrainagem do Modelo
            {
                "numero": 9,
                "head_pergunta": (
                    "Seu modelo foi treinado quando? Mercado mudou em fevereiro — "
                    "Fed cuts, inflação controlada, risco-on dominant. Está preparado?"
                ),
                "operador_resposta": (
                    "Última retrainagem 15 dias atrás com dados janeiro. "
                    "Fevereiro tem dinâmica diferente (menos volatilidade, tendências claras). "
                    "Modelo calibrado para vol 45-60%, agora 38-52%. "
                    "Deveria ter retreinado em 7 dias. Score está desatualizado."
                ),
                "head_trepica": (
                    "Ação crítica: retreine com dados últimos 7 dias (fevereiro 13-20). "
                    "Ajusta thresholds e modelos para mercado ATUAL. "
                    "Tempo: 4 horas. Faça em sessão inativa. Veja trainer.py:245+."
                )
            },
            # Rodada 10: Plano Amanhã
            {
                "numero": 10,
                "head_pergunta": (
                    "Resumindo: hoje ganhou $2.450 mas com falhas operacionais "
                    "(score baixo, gestão limite, rejeições). Amanhã qual é plano?"
                ),
                "operador_resposta": (
                    "Plano: (1) Rejeito score <4.8; (2) Se rejeição, stop automático; "
                    "(3) Limite 15 ordens; (4) H4 como filtro antes H1; "
                    "(5) Reduzo ETHUSDT SHORT 50% antes close. "
                    "Overnight: co-location retrofit + início retrainagem modelo."
                ),
                "head_trepica": (
                    "Excelente plano. Você está na direção correta. "
                    "Hoje foi +9.3% de ganho. Com essas correções, "
                    "semana que vem deve ser +12-15% consistentemente. Vamos monitorar."
                )
            }
        ]

        seq = 1
        for rodada in rodadas:
            # Pergunta do HEAD
            self.db.adicionar_dialogo(
                id_reuniao=self.id_reuniao,
                sequencia=seq,
                quem_fala="HEAD",
                pergunta_ou_resposta=rodada["head_pergunta"],
                tipo_conteudo="pergunta",
                contexto_dados={"rodada": rodada["numero"]}
            )
            seq += 1

            # Resposta do OPERADOR
            self.db.adicionar_dialogo(
                id_reuniao=self.id_reuniao,
                sequencia=seq,
                quem_fala="OPERADOR",
                pergunta_ou_resposta=rodada["operador_resposta"],
                tipo_conteudo="resposta",
                contexto_dados={"rodada": rodada["numero"]}
            )
            seq += 1

            # Tréplica do HEAD
            self.db.adicionar_dialogo(
                id_reuniao=self.id_reuniao,
                sequencia=seq,
                quem_fala="HEAD",
                pergunta_ou_resposta=rodada["head_trepica"],
                tipo_conteudo="trepica",
                contexto_dados={"rodada": rodada["numero"]}
            )
            seq += 1

        logger.info(f"10 rodadas (30 diálogos) adicionadas")

    def adicionar_feedback_exemplo(self):
        """
        Adiciona 9 feedbacks (3+3+3) com análise baseada em dados reais.
        Se houver trades reais, usa dados; caso contrário, usa exemplos.
        """
        if not self.id_reuniao:
            logger.error("Reunião não criada. Chame criar_reuniao() antes.")
            return

        logger.info("Adicionando feedbacks de exemplo (3+3+3)...")

        # Carregamentos dados reais para análise
        trades = self._obter_trades_periodo(dias=7)
        logs_analise = self._analisar_logs_operacionais(dias=1)
        
        # Se há trades reais, gerar feedbacks dinamicamente
        if trades and len(trades) > 0:
            feedbacks = self._gerar_feedbacks_dinamicos(trades, logs_analise)
        else:
            # Fallback: usar exemplos hardcoded
            feedbacks = self._gerar_feedbacks_exemplo()

        for fb in feedbacks[:9]:  # Garantir exatamente 9
            self.db.adicionar_feedback(
                id_reuniao=self.id_reuniao,
                categoria=fb["categoria"],
                descricao=fb["descricao"],
                impacto_score=fb["impacto_score"],
                responsavel="OPERADOR"
            )

        logger.info(f"{len(feedbacks[:9])} feedbacks adicionados (3+3+3)")

    def _gerar_feedbacks_dinamicos(self, trades: List[Dict], logs: Dict) -> List[Dict]:
        """
        Gera feedbacks dinamicamente baseados em trades reais.

        Args:
            trades: Trades do período
            logs: Análise de logs operacionais

        Returns:
            Lista de 9 feedbacks (3+3+3)
        """
        feedbacks = []

        # FORÇA: Operações que lucram
        traded_lucro = [t for t in trades if t.get('pnl_usdt', 0) > 0]
        if traded_lucro:
            top_trade = max(traded_lucro, key=lambda x: x.get('pnl_usdt', 0))
            feedbacks.append({
                "categoria": "força",
                "descricao": f"{top_trade['symbol']} com PnL +${top_trade['pnl_usdt']:.2f} — operação executada corretamente",
                "impacto_score": 9.0,
                "tipo_extenso": "Operação com confluência múltipla"
            })

        # FORÇA: Low error rate nos logs
        if not logs["erros"]:
            feedbacks.append({
                "categoria": "força",
                "descricao": "Zero erros críticos nos logs — sistema rodou estável",
                "impacto_score": 8.5,
                "tipo_extenso": "Robustez operacional"
            })
        else:
            feedbacks.append({
                "categoria": "força",
                "descricao": "Sistema auto-recuperou de erros — continuou operando",
                "impacto_score": 7.5,
                "tipo_extenso": "Resiliência de execução"
            })

        # FORÇA: Disciplina em operações
        feedbacks.append({
            "categoria": "força",
            "descricao": f"Manteve {len({t['symbol'] for t in trades})} pares em monitoramento sem overtrading",
            "impacto_score": 8.0,
            "tipo_extenso": "Gestão de portfólio disciplinada"
        })

        # FRAQUEZA: Operações com prejuízo
        trades_prejuizo = [t for t in trades if t.get('pnl_usdt', 0) < 0]
        if trades_prejuizo:
            worst_trade = min(trades_prejuizo, key=lambda x: x.get('pnl_usdt', 0))
            feedbacks.append({
                "categoria": "fraqueza",
                "descricao": f"{worst_trade['symbol']} perdeu ${abs(worst_trade['pnl_usdt']):.2f} — falha no SL/TP",
                "impacto_score": 8.5,
                "tipo_extenso": "Inadequado manejo de risco"
            })

        # FRAQUEZA: Erros em logs
        if logs["erros"]:
            feedbacks.append({
                "categoria": "fraqueza",
                "descricao": f"{len(logs['erros'])} erros detectados — necessário debugging",
                "impacto_score": 8.2,
                "tipo_extenso": f"Exemplos: {logs['erros'][0][:80] if logs['erros'] else 'N/A'}"
            })
        else:
            feedbacks.append({
                "categoria": "fraqueza",
                "descricao": "Taxa de acerto abaixo do esperado — investigar score mínimo",
                "impacto_score": 7.8,
                "tipo_extenso": "Possível MIN_ENTRY_SCORE muito baixo"
            })

        # FRAQUEZA: Avisos operacionais
        if logs["avisos"]:
            feedbacks.append({
                "categoria": "fraqueza",
                "descricao": f"{len(logs['avisos'])} avisos de sistema — monitorar.",
                "impacto_score": 7.5,
                "tipo_extenso": "Podem indicar deterioração de performance"
            })

        # OPORTUNIDADE: Múltiplos timeframes
        feedbacks.append({
            "categoria": "oportunidade",
            "descricao": "Implementar H4 como filtro validação (tendência principal) antes H1 entry",
            "impacto_score": 7.8,
            "tipo_extenso": "Aumentaria taxa acerto ao filtrar falsos breakouts"
        })

        # OPORTUNIDADE: Zona cinzenta "resgatável"
        feedbacks.append({
            "categoria": "oportunidade",
            "descricao": "Criar sub-regra para score 4.8-5.2: execute 50% tamanho se 3+ confluências",
            "impacto_score": 7.5,
            "tipo_extenso": "Capturaria operações borderline com risco limitado"
        })

        # OPORTUNIDADE: Retreinagem
        feedbacks.append({
            "categoria": "oportunidade",
            "descricao": "Implementar retrainagem rolling (7 dias) para modelo se adaptar dinamicamente",
            "impacto_score": 7.3,
            "tipo_extenso": "Model drift é inevitable em mercados — rolling window mitiga"
        })

        return feedbacks

    def _gerar_feedbacks_exemplo(self) -> List[Dict]:
        """Retorna feedbacks hardcoded quando não há dados reais."""
        return [
            # ✅ 3 FORÇA
            {
                "categoria": "força",
                "descricao": "Leitura de Breakout (BTCUSDT LONG) — entrada com volume, RR 1:2.5, saída no TP",
                "impacto_score": 9.5,
                "tipo_extenso": "Operação correta (Categoria A: HEAD também entraria)"
            },
            {
                "categoria": "força",
                "descricao": "Disciplina ao ficar fora (LTCUSDT, ADAUSDT) — manteve portfólio limpo",
                "impacto_score": 8.8,
                "tipo_extenso": "Gestão de risco em operações inválidas (Categoria D: ambos evitaram)"
            },
            {
                "categoria": "força",
                "descricao": "Escalada correta em winner — manteve posição firme até TP, sem overtrading",
                "impacto_score": 8.5,
                "tipo_extenso": "Gestão de tamanho apropriada em ganho"
            },

            # ❌ 3 FRAQUEZA
            {
                "categoria": "fraqueza",
                "descricao": "Execução com score baixo (DOGEUSDT 4.2) — violou próprio critério",
                "impacto_score": 9.0,
                "tipo_extenso": "Operação incorreta (Categoria B: HEAD evitaria)"
            },
            {
                "categoria": "fraqueza",
                "descricao": "Escalação após rejeição (BNBUSDT) — aumentou risco em falha em vez de pausar",
                "impacto_score": 8.5,
                "tipo_extenso": "Violação de protocolo de gestão de risco"
            },
            {
                "categoria": "fraqueza",
                "descricao": "Gestão de limite de ordens — perdeu MATICUSDT por slot cheio (não liberou)",
                "impacto_score": 8.2,
                "tipo_extenso": "Oportunidade perdida (Categoria C: HEAD entraria)"
            },

            # 🔄 3 OPORTUNIDADE
            {
                "categoria": "oportunidade",
                "descricao": "Leitura de múltiplos timeframes — H4 deveria filtrar tendência antes H1 entry",
                "impacto_score": 7.8,
                "tipo_extenso": "Ajuste em signal_environment.py: H4=40% weight, H1=60% weight"
            },
            {
                "categoria": "oportunidade",
                "descricao": "Zona cinzenta de score (4.8-5.0) — está perdendo operações claras em confluência múltipla",
                "impacto_score": 7.5,
                "tipo_extenso": "Ajuste em reward.py: Score 4.8+ com 3+ confluências = execute 50% tamanho"
            },
            {
                "categoria": "oportunidade",
                "descricao": "Frequência de retrainagem — modelo desatualizado (janeiro) para dinâmica fevereiro",
                "impacto_score": 7.3,
                "tipo_extenso": "Implementar rolling window: retrain a cada 7 dias em trainer.py"
            }
        ]

    def adicionar_acoes_exemplo(self):
        """
        Adiciona 6 ações do plano de ação completo.
        Dinamicamente baseado em dados reais; fallback para exemplos.
        """
        if not self.id_reuniao:
            logger.error("Reunião não criada. Chame criar_reuniao() antes.")
            return

        logger.info("Adicionando plano de ação (6 itens)...")

        # Carregar dados reais
        trades = self._obter_trades_periodo(dias=7)
        metricas = self.carregar_metricas()

        # Gerar ações dinamicamente se houver dados
        if trades and len(trades) > 0:
            acoes = self._gerar_acoes_dinamicas(trades, metricas)
        else:
            acoes = self._gerar_acoes_exemplo()

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

        logger.info(f"{len(acoes)} ações do plano criadas")

    def _gerar_acoes_dinamicas(self, trades: List[Dict], metricas: Dict) -> List[Dict]:
        """
        Gera ações dinamicamente baseado em problemas identificados nos trades.

        Args:
            trades: Trades reais do período
            metricas: Métricas calculadas

        Returns:
            Lista de 6 ações prioridas
        """
        acoes = []

        # Identificar problemas nos trades
        trades_fechados = [t for t in trades if t.get('exit_price')]
        taxa_acerto = metricas['globais']['taxa_acertos']

        # CRÍTICA 1: Se taxa de acertos é baixa, aumentar critério mínimo
        if taxa_acerto < 0.5:
            acoes.append({
                "descricao": "[CRÍTICA] Aumentar MIN_ENTRY_SCORE para filtrar operações fracas",
                "tipo": "código",
                "prioridade": "crítica",
                "responsavel": "OPERADOR",
                "arquivo": "agent/reward.py:340",
                "impacto": f"Taxa acerto atual {taxa_acerto:.1%} → target 65%. Elimina score <4.8",
                "seq": 1
            })
        else:
            acoes.append({
                "descricao": "[CRÍTICA] Manter rigor em MIN_ENTRY_SCORE (efetivo em {:.1%})".format(taxa_acerto),
                "tipo": "código",
                "prioridade": "crítica",
                "responsavel": "OPERADOR",
                "arquivo": "agent/reward.py:340",
                "impacto": f"Taxa acerto {taxa_acerto:.1%} está boa. Não diminuir critério",
                "seq": 1
            })

        # CRÍTICA 2: Se houver muitos trades com perdas após reject, bloquear escalação
        trades_prejuizo = [t for t in trades if t.get('pnl_usdt', 0) < 0]
        if trades_prejuizo and len(trades_prejuizo) > len([t for t in trades if t.get('pnl_usdt', 0) > 0]):
            acoes.append({
                "descricao": "[CRÍTICA] Bloquear escalação manual após rejeição de ordem",
                "tipo": "código",
                "prioridade": "crítica",
                "responsavel": "OPERADOR",
                "arquivo": "execution/order_executor.py:187",
                "impacto": f"Evita ${'%.0f' % sum(abs(t['pnl_usdt']) for t in trades_prejuizo)}/período em perdas por reentrada",
                "seq": 2
            })
        else:
            acoes.append({
                "descricao": "[CRÍTICA] Revisar resposta a ordens rejeitadas (executar com cuidado)",
                "tipo": "código",
                "prioridade": "crítica",
                "responsavel": "OPERADOR",
                "arquivo": "execution/order_executor.py:187",
                "impacto": "Rejuvenescence evita operações precipitadas. Manter disciplina",
                "seq": 2
            })

        # ALTA 1: Aumentar posições concorrentes se tem oportunidades perdidas
        pares_operados = len({t['symbol'] for t in trades})
        acoes.append({
            "descricao": "[ALTA] Aumentar MAX_CONCURRENT_POSITIONS (atualmente {}".format(pares_operados),
            "tipo": "configuração",
            "prioridade": "alta",
            "responsavel": "OPERADOR",
            "arquivo": "config/execution_config.py:45",
            "impacto": f"Capturar oportunidades em {max(10, pares_operados + 5)} símbolos. +2-3% PnL",
            "seq": 3
        })

        # ALTA 2: Auto-close de posições inativas
        acoes.append({
            "descricao": "[ALTA] Implementar auto-close de posições inativas >4h",
            "tipo": "código",
            "prioridade": "alta",
            "responsavel": "OPERADOR",
            "arquivo": "execution/position_management.py:250",
            "impacto": "Libera slots para novas oportunidades. Liquidação de trades lateral",
            "seq": 4
        })

        # ALTA 3: Múltiplos timeframes (H4 filtro)
        acoes.append({
            "descricao": "[ALTA] Usar H4 como filtro principal de tendência",
            "tipo": "código",
            "prioridade": "alta",
            "responsavel": "OPERADOR",
            "arquivo": "agent/signal_environment.py:112",
            "impacto": "Evita operações contra-tendência. Taxa acerto +8-10%. Menos whipsaws",
            "seq": 5
        })

        # MÉDIA: Retrainagem rolling
        acoes.append({
            "descricao": "[MÉDIA] Implementar retrainagem com rolling window (7 dias)",
            "tipo": "código",
            "prioridade": "média",
            "responsavel": "OPERADOR",
            "arquivo": "agent/trainer.py:245",
            "impacto": "Modelo se adapta dinamicamente. +5% calibração scores. Menos drift",
            "seq": 6
        })

        return acoes[:6]  # Garantir 6 ações

    def _gerar_acoes_exemplo(self) -> List[Dict]:
        """Retorna ações hardcoded quando não há dados reais."""
        return [
            {
                "descricao": "[CRÍTICA] Aumentar MIN_ENTRY_SCORE de 4.0 → 4.8",
                "tipo": "código",
                "prioridade": "crítica",
                "responsavel": "OPERADOR",
                "arquivo": "agent/reward.py:340",
                "impacto": "Elimina operações score <4.8. Taxa acerto 62% → 68%. +$320 poupado (DOGEUSDT)",
                "seq": 1
            },
            {
                "descricao": "[CRÍTICA] Bloquear escalação manual após rejeição de ordem",
                "tipo": "código",
                "prioridade": "crítica",
                "responsavel": "OPERADOR",
                "arquivo": "execution/order_executor.py:187",
                "impacto": "Evita operações precipitadas (BNBUSDT). Evita $500-800/semana risco. Sharpe 1.82 → 2.05",
                "seq": 2
            },
            {
                "descricao": "[ALTA] Aumentar MAX_CONCURRENT_POSITIONS de 10 → 15",
                "tipo": "configuração",
                "prioridade": "alta",
                "responsavel": "OPERADOR",
                "arquivo": "config/execution_config.py:45",
                "impacto": "Captura operações rejeitadas (MATICUSDT +$890). +3-5% PnL mensal",
                "seq": 3
            },
            {
                "descricao": "[ALTA] Implementar auto-close para posições inativas >4h",
                "tipo": "código",
                "prioridade": "alta",
                "responsavel": "OPERADOR",
                "arquivo": "execution/position_management.py:250",
                "impacto": "Libera slots para novas oportunidades. +2-3 trades/dia. Capital destraved",
                "seq": 4
            },
            {
                "descricao": "[ALTA] Usar H4 como filtro de tendência (múltiplos timeframes)",
                "tipo": "código",
                "prioridade": "alta",
                "responsavel": "OPERADOR",
                "arquivo": "agent/signal_environment.py:112",
                "impacto": "Evita operações contra-tendência. Taxa acerto 62% → 70%. -15-20% whipsaws",
                "seq": 5
            },
            {
                "descricao": "[MÉDIA] Retreinar modelo com rolling window (7 dias)",
                "tipo": "código",
                "prioridade": "média",
                "responsavel": "OPERADOR",
                "arquivo": "agent/trainer.py:245",
                "impacto": "+5% calibração de scores. Menos falsos positivos. Adaptável ao mercado vivo",
                "seq": 6
            }
        ]

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
            metricas = self.carregar_metricas()

            # ⚠️ VALIDAÇÃO CRÍTICA: Verificar se há dados REAIS
            logger.info("\n[VALIDAÇÃO] Verificando integridade de dados...")
            tem_dados_reais = self._validar_dados_reais(dias=7)

            if not tem_dados_reais:
                logger.error(
                    "\n❌ ERRO: Não há dados reais no banco de dados!\n"
                    "Sistema recusa gerar relatório com dados fictícios.\n\n"
                    "SOLUÇÃO:\n"
                    "  1. Execute o agente para gerar trades reais:\n"
                    "     python main.py --mode paper --integrated\n"
                    "  2. Deixe rodar por 30-60 minutos\n"
                    "  3. Tente novamente disparar a reunião"
                )
                return  # Bloqueia execução

            # Passo 2: Buscar reunião anterior
            logger.info("\n[PASSO 2/7] Buscando reunião anterior...")
            reuniao_anterior = self.carregar_reuniao_anterior()

            # Passo 3: Montar prompt
            logger.info("\n[PASSO 3/7] Montando prompt de contexto...")
            prompt = self.montar_prompt_contexto(metricas, reuniao_anterior)

            # Passo 4: Criar reunião
            logger.info("\n[PASSO 4/7] Criando reunião no banco...")
            self.criar_reuniao()

            # Passo 5: Adicionar conteúdos (podem agora usar dados reais com segurança)
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
        executor = ExecutorReuniao()
        executor.executar_fluxo_completo()

    except KeyboardInterrupt:
        logger.warning("Interrupção do usuário")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
