"""Utilitário para iniciar a fase 2 do treinamento do BTCUSDT."""
import logging

from agent.trainer import Trainer
from agent.data_loader import DataLoader
from config.settings import DB_PATH
from data.database import DatabaseManager


logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("run_phase2")


def main():
    logger.info("Iniciando fase 2 de refinamento para BTCUSDT")
    db = DatabaseManager(DB_PATH)
    loader = DataLoader(db=db)
    train_data = loader.load_training_data(symbol="BTCUSDT", train_ratio=0.8, min_length=1000)
    trainer = Trainer()
    trainer.train_phase2_refinement(train_data, total_timesteps=1_000_000, load_phase1=True)


if __name__ == "__main__":
    main()
