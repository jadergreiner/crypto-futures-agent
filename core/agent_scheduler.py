import threading
import time
import logging
from datetime import datetime, timedelta
from config.symbols import ALL_SYMBOLS
from data.database import DatabaseManager

logger = logging.getLogger(__name__)

DEFAULT_TRAIN_INTERVAL_HOURS = 24

class AgentTrainingScheduler:
    def __init__(self, db_path="db/crypto_agent.db", interval_hours=DEFAULT_TRAIN_INTERVAL_HOURS):
        self.db = DatabaseManager(db_path)
        self.interval_hours = interval_hours
        self.last_train_times = {}
        self.running = False

    def _train_all_symbols(self):
        from agent.trainer import train_from_real_signals

        logger.info(f"[TRAINING CYCLE] Iniciando treinamento de {len(ALL_SYMBOLS)} símbolos...")
        successful = 0
        failed = 0
        
        for symbol in ALL_SYMBOLS:
            try:
                logger.info(f"[TRAINING] {symbol}...")
                result = train_from_real_signals(symbol, self.db)
                now = datetime.utcnow()
                self.last_train_times[symbol] = now
                logger.info(f"[TRAINING OK] {symbol}: {result}")
                successful += 1
            except Exception as e:
                logger.error(f"[TRAINING FAILED] {symbol}: {e}")
                failed += 1
        
        logger.info(f"[TRAINING CYCLE COMPLETE] {successful} OK, {failed} FAILED")

    def _check_training_times(self):
        now = datetime.utcnow()
        for symbol in ALL_SYMBOLS:
            last_train = self.last_train_times.get(symbol)
            if not last_train:
                logger.warning(f"[SECURITY] {symbol}: WARNING - nunca treinado")
            elif (now - last_train) > timedelta(hours=self.interval_hours * 2):
                logger.warning(f"[SECURITY] {symbol}: WARNING - treino vencido (>{self.interval_hours * 2}h)")
            else:
                logger.info(f"[SECURITY] {symbol}: OK")

    def start(self):
        self.running = True
        self._check_training_times()  # Validação inicial
        
        while self.running:
            try:
                self._train_all_symbols()
                self._check_training_times()
                logger.info(f"[SCHEDULER] Próximo ciclo de treino em {self.interval_hours} hora(s).")
                time.sleep(self.interval_hours * 3600)
            except Exception as e:
                logger.error(f"[SCHEDULER ERROR] {e}")
                time.sleep(300)  # Retry após 5 min se erro

    def stop(self):
        self.running = False
        logger.info("[SCHEDULER] Treinamento em background foi interrompido")

# Para rodar em background:
def start_agent_training_scheduler(interval_hours=DEFAULT_TRAIN_INTERVAL_HOURS):
    """
    Inicia scheduler de treinamento em thread background.
    
    Args:
        interval_hours: Intervalo entre ciclos de treinamento (default 24 horas)
    
    Returns:
        AgentTrainingScheduler instance (pode chamar .stop() para parar)
    """
    scheduler = AgentTrainingScheduler(interval_hours=interval_hours)
    thread = threading.Thread(target=scheduler.start, daemon=True, name='agent-training-scheduler')
    thread.start()
    return scheduler
