"""
Scheduler - Orquestrador das camadas com execução condicional.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import schedule
import time
from zoneinfo import ZoneInfo

from config.settings import H4_EXECUTION_HOURS, FUNDING_RATE_HOURS
from .layer_manager import LayerManager

logger = logging.getLogger(__name__)
BRASILIA_TZ = ZoneInfo("America/Sao_Paulo")


class Scheduler:
    """
    Orquestra todas as camadas do sistema com execução condicional.
    
    LAYER 1 (Heartbeat): 1 min - Health check
    LAYER 2 (Risk): 5 min - Gestão de risco (APENAS se posições abertas)
    LAYER 3 (H1): 1 hora - Timing de entrada (APENAS se signal pendente ou posição)
    LAYER 4 (H4): 4 horas - Decisão principal (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)
    LAYER 5 (D1): 00:00 UTC - Tendência e macro (ANTES da Layer 4)
    LAYER 6 (Weekly/Monthly): Performance review e retrain
    """
    
    def __init__(self, layer_manager: LayerManager):
        """
        Inicializa scheduler.
        
        Args:
            layer_manager: Gerenciador de camadas
        """
        self.layer_manager = layer_manager
        self.running = False
        logger.info("Scheduler initialized")
    
    def setup_schedules(self) -> None:
        """Configura todos os schedules."""
        # Layer 1: Heartbeat (1 min)
        schedule.every(1).minutes.do(self._run_layer1_heartbeat)
        
        # Layer 2: Risk (5 min)
        schedule.every(5).minutes.do(self._run_layer2_risk)
        
        # Layer 3: H1 (1 hora)
        schedule.every().hour.at(":00").do(self._run_layer3_h1)
        
        # Layer 4: H4 (nas horas específicas)
        for hour in H4_EXECUTION_HOURS:
            schedule.every().day.at(f"{hour:02d}:00").do(self._run_layer4_h4)
        
        # Layer 5: D1 (00:00 UTC, ANTES da Layer 4)
        schedule.every().day.at("23:59").do(self._run_layer5_d1)  # 1 min antes
        
        # Layer 6: Weekly (Segunda 00:00)
        schedule.every().monday.at("00:00").do(self._run_layer6_weekly)
        
        # Layer 6: Monthly (Dia 1 00:00)
        schedule.every().day.at("00:00").do(self._check_monthly)
        
        logger.info("All schedules configured")
    
    def start(self) -> None:
        """Inicia o scheduler."""
        self.running = True
        self.setup_schedules()

        # Bootstrap operacional: executa uma varredura inicial imediata.
        # Evita ficar "parado" até o próximo horário fixo da Layer 4.
        try:
            logger.info("Bootstrap: executando varredura inicial de oportunidades (Layer 4)")
            self.layer_manager.h4_main_decision()
        except Exception as e:
            logger.error(f"Bootstrap da Layer 4 falhou: {e}", exc_info=True)
        
        logger.info("="*60)
        logger.info("SCHEDULER STARTED")
        logger.info("="*60)
        
        # Loop principal
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                self.stop()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                time.sleep(5)  # Esperar antes de continuar
    
    def stop(self) -> None:
        """Para o scheduler."""
        self.running = False
        schedule.clear()
        logger.info("Scheduler stopped")
    
    def _run_layer1_heartbeat(self) -> None:
        """Layer 1: Heartbeat - Health check."""
        try:
            pending_signals = len(self.layer_manager.pending_signals)
            open_positions = len(self.layer_manager.open_positions)
            now_brt = datetime.now(BRASILIA_TZ)

            h1_runs = [
                job.next_run
                for job in schedule.jobs
                if job.job_func.__name__ == "_run_layer3_h1" and job.next_run is not None
            ]
            h4_runs = [
                job.next_run
                for job in schedule.jobs
                if job.job_func.__name__ == "_run_layer4_h4" and job.next_run is not None
            ]

            h1_next = min(h1_runs) if h1_runs else None
            h4_next = min(h4_runs) if h4_runs else None

            h1_next_str = self._format_brasilia_time(h1_next)
            h4_next_str = self._format_brasilia_time(h4_next)

            logger.info(
                f"Heartbeat (BRT {now_brt.strftime('%Y-%m-%d %H:%M:%S')}) | open_positions={open_positions} | "
                f"pending_signals={pending_signals} | next_h1={h1_next_str} | next_h4={h4_next_str}"
            )
            self.layer_manager.heartbeat_check()
        except Exception as e:
            logger.error(f"Layer 1 error: {e}", exc_info=True)

    def _format_brasilia_time(self, dt_obj: Optional[datetime]) -> str:
        """Converte datetime para horário de Brasília para logs consistentes."""
        if dt_obj is None:
            return "N/A"

        if dt_obj.tzinfo is None:
            local_tz = datetime.now().astimezone().tzinfo
            dt_obj = dt_obj.replace(tzinfo=local_tz)

        return dt_obj.astimezone(BRASILIA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    
    def _run_layer2_risk(self) -> None:
        """Layer 2: Risk - Apenas se há posições abertas."""
        try:
            if self.layer_manager.has_open_positions():
                logger.info("Layer 2: Risk management")
                self.layer_manager.risk_management()
            else:
                logger.debug("Layer 2: Skipped (no positions)")
        except Exception as e:
            logger.error(f"Layer 2 error: {e}", exc_info=True)
    
    def _run_layer3_h1(self) -> None:
        """Layer 3: H1 - Apenas se signal pendente ou posição."""
        try:
            if self.layer_manager.should_execute_h1():
                logger.info("Layer 3: H1 timing")
                self.layer_manager.h1_timing()
            else:
                logger.debug("Layer 3: Skipped (no signal/position)")
        except Exception as e:
            logger.error(f"Layer 3 error: {e}", exc_info=True)
    
    def _run_layer4_h4(self) -> None:
        """Layer 4: H4 - Decisão principal."""
        try:
            logger.info("="*60)
            logger.info(f"Layer 4: H4 MAIN DECISION - {datetime.utcnow()}")
            logger.info("="*60)
            self.layer_manager.h4_main_decision()
        except Exception as e:
            logger.error(f"Layer 4 error: {e}", exc_info=True)
    
    def _run_layer5_d1(self) -> None:
        """Layer 5: D1 - Tendência e macro."""
        try:
            logger.info("="*60)
            logger.info(f"Layer 5: D1 TREND & MACRO - {datetime.utcnow()}")
            logger.info("="*60)
            self.layer_manager.d1_trend_macro()
        except Exception as e:
            logger.error(f"Layer 5 error: {e}", exc_info=True)
    
    def _run_layer6_weekly(self) -> None:
        """Layer 6: Weekly - Performance review."""
        try:
            logger.info("="*60)
            logger.info(f"Layer 6: WEEKLY REVIEW - {datetime.utcnow()}")
            logger.info("="*60)
            self.layer_manager.weekly_review()
        except Exception as e:
            logger.error(f"Layer 6 error: {e}", exc_info=True)
    
    def _check_monthly(self) -> None:
        """Verifica se é dia 1 do mês para executar mensal."""
        if datetime.utcnow().day == 1:
            self._run_layer6_monthly()
    
    def _run_layer6_monthly(self) -> None:
        """Layer 6: Monthly - Retrain."""
        try:
            logger.info("="*60)
            logger.info(f"Layer 6: MONTHLY RETRAIN - {datetime.utcnow()}")
            logger.info("="*60)
            self.layer_manager.monthly_retrain()
        except Exception as e:
            logger.error(f"Layer 6 monthly error: {e}", exc_info=True)
