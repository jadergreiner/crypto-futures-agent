import threading
import time
import logging
from datetime import datetime, timedelta
from config.symbols import ALL_SYMBOLS
from data.database import DatabaseManager

logger = logging.getLogger(__name__)

TRAIN_INTERVAL_HOURS = 24

class AgentTrainingScheduler:
    def __init__(self, db_path="db/crypto_agent.db"):
        self.db = DatabaseManager(db_path)
        self.last_train_times = {}
        self.running = False

    def _train_all_symbols(self):
        from agent.trainer import train_from_real_signals

        for symbol in ALL_SYMBOLS:
            logger.info(f"[SCHEDULER] Treinando agente para {symbol}")
            result = train_from_real_signals(symbol, self.db)
            now = datetime.utcnow()
            self.last_train_times[symbol] = now
            logger.info(f"[SCHEDULER] Treino concluído para {symbol}: {result}")

    def _check_training_times(self):
        now = datetime.utcnow()
        for symbol in ALL_SYMBOLS:
            last_train = self.last_train_times.get(symbol)
            if not last_train:
                logger.warning(f"[SECURITY] {symbol}: WARNING - nunca treinado")
            elif (now - last_train) > timedelta(hours=TRAIN_INTERVAL_HOURS):
                logger.warning(f"[SECURITY] {symbol}: WARNING - treino vencido (>24h)")
            else:
                logger.info(f"[SECURITY] {symbol}: OK")

    def start(self):
        self.running = True
        self._check_training_times()  # Emit alerts before first training cycle
        while self.running:
            self._train_all_symbols()
            self._check_training_times()
            logger.info(f"[SCHEDULER] Próximo treino em {TRAIN_INTERVAL_HOURS} horas.")
            time.sleep(TRAIN_INTERVAL_HOURS * 3600)

    def stop(self):
        self.running = False

# Para rodar em background:
def start_agent_training_scheduler():
    scheduler = AgentTrainingScheduler()
    thread = threading.Thread(target=scheduler.start, daemon=True)
    thread.start()
    return scheduler
