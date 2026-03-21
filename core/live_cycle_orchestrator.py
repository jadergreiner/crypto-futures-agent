#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Módulo Orquestrador do Ciclo de Vida do Agente (Live Cycle Orchestrator)

Este módulo centraliza a execução sequencial das tarefas que compõem o ciclo 
operacional do agente, conforme definido pelos requisitos do PRD. 
Ele substitui a orquestração baseada em scripts externos (como .bat) 
por um fluxo de controle robusto e unificado dentro da aplicação Python.
"""

import logging
import subprocess
import sys
from config.settings import M2_EXECUTION_MODE, M2_LIVE_SYMBOLS

# Configuração do logger para este módulo
logger = logging.getLogger(__name__)

class LiveCycleOrchestrator:
    """
    Orquestra o ciclo de vida model-driven do agente, executando as etapas
    de pipeline, ciclo live, healthcheck e status em uma sequência controlada.
    """

    def __init__(self, execution_mode: str, symbols: list[str]):
        """
        Inicializa o orquestrador.

        Args:
            execution_mode (str): O modo de execução ('shadow' or 'live').
            symbols (list[str]): A lista de símbolos a serem processados.
        """
        self.execution_mode = execution_mode
        self.symbols = symbols
        self.pipeline_symbol_args = []
        self.live_symbol_args = []

        if not self.symbols:
            raise ValueError("A lista de símbolos não pode ser vazia.")

        # Monta os argumentos para os scripts a serem chamados
        for symbol in self.symbols:
            self.pipeline_symbol_args.extend(["--symbol", symbol])
            self.live_symbol_args.extend(["--live-symbol", symbol])
        
        logger.info(f"Orquestrador inicializado em modo '{self.execution_mode}' para os símbolos: {self.symbols}")

    def _run_script(self, script_path: str, args: list[str]) -> bool:
        """
        Executa um script Python como um subprocesso e loga a saída.

        Args:
            script_path (str): O caminho para o script Python.
            args (list[str]): Uma lista de argumentos para o script.

        Returns:
            bool: True se o script foi executado com sucesso, False caso contrário.
        """
        command = [sys.executable, script_path] + args
        script_name = script_path.split("/")[-1]
        logger.info(f"Executando etapa: {script_name} com args: {' '.join(args)}")
        
        try:
            # Redirecionar stdout e stderr para o logger
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
            
            for line in process.stdout:
                logger.info(f"[{script_name}] {line.strip()}")
            
            process.wait()
            
            if process.returncode == 0:
                logger.info(f"Etapa {script_name} concluída com sucesso.")
                return True
            else:
                logger.error(f"Erro na etapa {script_name}. Código de saída: {process.returncode}")
                return False
        except Exception as e:
            logger.critical(f"Falha crítica ao executar {script_name}: {e}", exc_info=True)
            return False

    def run_cycle(self) -> None:
        """
        Executa um ciclo completo de orquestração.
        """
        logger.info("="*80)
        logger.info(f"INICIANDO NOVO CICLO DE ORQUESTRAÇÃO (Modo: {self.execution_mode})")
        logger.info("="*80)

        # Etapa 1: Daily Pipeline
        if not self._run_script("scripts/model2/daily_pipeline.py", ["--timeframe", "H4", "--continue-on-error"] + self.pipeline_symbol_args):
            logger.error("Ciclo interrompido devido a erro no daily_pipeline.")
            return

        # Etapa 2: Live Cycle
        if not self._run_script("scripts/model2/live_cycle.py", ["--execution-mode", self.execution_mode] + self.live_symbol_args):
            logger.error("Ciclo interrompido devido a erro no live_cycle.")
            return

        # Etapa 3: Health Check
        if not self._run_script("scripts/model2/healthcheck_live_execution.py", ["--runtime-dir", "results/model2/runtime"]):
            logger.warning("A etapa de healthcheck falhou, mas o ciclo continuará.")

        # Etapa 4: Status por Símbolo
        symbols_csv = ",".join(self.symbols)
        if not self._run_script("scripts/model2/operator_cycle_status.py", ["--runtime-dir", "results/model2/runtime", "--max-age-minutes", "20", "--symbols-csv", symbols_csv]):
            logger.warning("A etapa de status falhou.")

        logger.info("="*80)
        logger.info("CICLO DE ORQUESTRAÇÃO CONCLUÍDO.")
        logger.info("="*80)

if __name__ == '__main__':
    # Exemplo de como usar o orquestrador
    # Este bloco é para teste e não será executado quando importado
    
    # Configurar um logger básico para teste
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    logger.info("Executando LiveCycleOrchestrator em modo de teste.")
    
    # Usar configurações do settings.py como padrão
    try:
        orchestrator = LiveCycleOrchestrator(
            execution_mode=M2_EXECUTION_MODE,
            symbols=M2_LIVE_SYMBOLS
        )
        orchestrator.run_cycle()
    except Exception as e:
        logger.critical(f"Erro ao instanciar ou executar o orquestrador: {e}")

