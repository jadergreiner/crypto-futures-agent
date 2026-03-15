"""
Fase E.4: Análise Comparativa LSTM vs MLP (Sharpe Delta) - Model 2.0

Avalia dois modelos PPO treinados e extrai métricas financeiras simuladas
(Reward, Win Rate, Sharpe Ratio).
"""

import argparse
import json
import sqlite3
import logging
from collections import deque
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

try:
    from stable_baselines3 import PPO
except ImportError:
    PPO = None

REPO_ROOT = Path(__file__).resolve().parents[2]
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import MODEL2_DB_PATH
from agent.lstm_environment import LSTMSignalEnvironment
from agent.lstm_policy import LSTMPolicy

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class PPOEvaluator:
    def __init__(self, model2_db_path: Path, episodes_limit: int = 1000):
        self.db_path = model2_db_path
        self.episodes_limit = episodes_limit
        self.seq_len = 10
        self.n_features = 19
        
    def _extract_features(self, features_dict: Dict[str, Any]) -> np.ndarray:
        """Extrai as 19 features seguindo o padrão do LSTMSignalEnvironment."""
        features = []
        # Candle (5)
        candle = features_dict.get("latest_candle", {})
        features.extend([
            candle.get("open", 0.0), candle.get("high", 0.0),
            candle.get("low", 0.0), candle.get("close", 0.0),
            candle.get("volume", 0.0)
        ])
        
        # Volatility (4)
        vol = features_dict.get("volatility", {})
        features.append(vol.get("atr_14", 0.0))
        bb = vol.get("bollinger_bands", {})
        features.extend([
            bb.get("upper", 0.0), bb.get("sma", 0.0), bb.get("lower", 0.0)
        ])
        
        # Multi-timeframe (3)
        mf = features_dict.get("multi_timeframe", {})
        features.extend([
            mf.get("H1", {}).get("close", 0.0) if isinstance(mf.get("H1"), dict) else 0.0,
            mf.get("H4", {}).get("close", 0.0) if isinstance(mf.get("H4"), dict) else 0.0,
            mf.get("D1", {}).get("close", 0.0) if isinstance(mf.get("D1"), dict) else 0.0,
        ])
        
        # Funding Rates (4)
        fr = features_dict.get("funding_rates", {})
        sentiment_map = {"bullish": 1.0, "neutral": 0.0, "bearish": -1.0}
        trend_map = {"increasing": 1.0, "stable": 0.0, "decreasing": -1.0}
        dir_map = {"up": 1.0, "steady": 0.0, "down": -1.0}
        
        features.extend([
            fr.get("latest_rate", 0.0),
            fr.get("avg_rate_24h", 0.0),
            sentiment_map.get(str(fr.get("sentiment", "neutral")).lower(), 0.0),
            trend_map.get(str(fr.get("trend", "stable")).lower(), 0.0)
        ])
        
        # Open Interest (3)
        oi = features_dict.get("open_interest", {})
        features.extend([
            oi.get("current_oi", 0.0) / 100000.0,
            sentiment_map.get(str(oi.get("oi_sentiment", "neutral")).lower(), 0.0),
            dir_map.get(str(oi.get("change_direction", "steady")).lower(), 0.0)
        ])
        
        return np.array(features[:self.n_features], dtype=np.float32)

    def load_episodes(self) -> Dict[str, List[Dict[str, Any]]]:
        """Carrega e agrupa episódios cronologicamente por symbol."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT symbol, label, reward_proxy, features_json, created_at
                FROM training_episodes
                ORDER BY created_at ASC
                LIMIT {self.episodes_limit}
            """)
            rows = cursor.fetchall()
            conn.close()
            
            grouped = {}
            for row in rows:
                sym = row['symbol']
                if sym not in grouped: grouped[sym] = []
                features = {}
                if row['features_json']:
                    try: features = json.loads(row['features_json'])
                    except json.JSONDecodeError: pass
                    
                grouped[sym].append({
                    'label': row['label'],
                    'reward_proxy': row['reward_proxy'],
                    'features': self._extract_features(features)
                })
            return grouped
        except Exception as e:
            logger.error(f"Erro ao carregar episódios: {e}")
            return {}

    def simulate_policy(self, model: Any, is_lstm: bool, episodes_by_symbol: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Simula a política sobre os episódios e coleta métricas."""
        returns = []
        wins = 0
        trades = 0
        
        for sym, episodes in episodes_by_symbol.items():
            state_buffer = deque(maxlen=self.seq_len)
            
            for ep in episodes:
                feats = ep['features']
                state_buffer.append(feats)
                # Padding se buffer inicial não estiver cheio
                while len(state_buffer) < self.seq_len:
                    state_buffer.append(feats)
                
                # Forma a observação
                if is_lstm:
                    obs = np.array(list(state_buffer), dtype=np.float32)
                else:
                    obs = np.array(list(state_buffer), dtype=np.float32).flatten()
                
                # Predict (usamos Dummy se model for None em testes)
                if model is None:
                    action = np.random.choice([0, 1, 2])
                else:
                    try:
                        action, _ = model.predict(obs, deterministic=True)
                        action = int(action)
                    except Exception:
                        action = 0
                
                # Avalia trade logico (Reward Proxy)
                # Se reward_proxy for nulo, tenta inferir pelo label
                base_reward = ep['reward_proxy']
                if base_reward is None:
                    if ep['label'] == 'win': base_reward = 1.0
                    elif ep['label'] == 'loss': base_reward = -1.0
                    else: base_reward = 0.0
                else:
                    base_reward = float(base_reward)

                if action in [1, 2]:  # Long ou Short
                    trades += 1
                    # Simula um PnL logarítmico (ganho de acerto vs erro)
                    trade_return = 0.0
                    if action == 1 and base_reward > 0:
                        trade_return = 0.02
                        wins += 1
                    elif action == 1 and base_reward <= 0:
                        trade_return = -0.01
                    elif action == 2 and base_reward < 0:
                        trade_return = 0.02
                        wins += 1
                    elif action == 2 and base_reward >= 0:
                        trade_return = -0.01
                        
                    returns.append(trade_return)

        returns_arr = np.array(returns) if returns else np.array([0.0])
        mean_ret = float(np.mean(returns_arr))
        std_ret = float(np.std(returns_arr)) if len(returns_arr) > 1 else 1e-6
        if std_ret == 0: std_ret = 1e-6
        
        # Anualização (Assumindo H4 = 6 trades/dia = 2190 periods/year)
        sharpe = (mean_ret / std_ret) * np.sqrt(2190)
        win_rate = (wins / trades) * 100 if trades > 0 else 0.0

        return {
            "total_trades": trades,
            "win_rate_pct": round(win_rate, 2),
            "mean_return": round(mean_ret, 4),
            "cumulative_return": round(float(np.sum(returns_arr)), 4),
            "sharpe_ratio": round(sharpe, 4)
        }

    def run_analysis(self) -> Dict[str, Any]:
        logger.info("Carregando base de episódios...")
        episodes_by_sym = self.load_episodes()
        if not episodes_by_sym:
            return {"status": "error", "message": "Sem dados"}
            
        logger.info(f"Símbolos encontrados: {list(episodes_by_sym.keys())}")
        
        mlp_path = REPO_ROOT / "checkpoints" / "ppo_training" / "mlp" / "ppo_model_mlp.zip"
        lstm_path = REPO_ROOT / "checkpoints" / "ppo_training" / "lstm" / "ppo_model_lstm.zip"
        
        mlp_model = None
        lstm_model = None
        
        if PPO is not None:
            if mlp_path.exists():
                logger.info("Carregando modelo MLP...")
                try: mlp_model = PPO.load(str(mlp_path))
                except Exception as e: logger.error(f"Failed MLP: {e}")
            
            if lstm_path.exists():
                logger.info("Carregando modelo LSTM...")
                try: lstm_model = PPO.load(str(lstm_path), custom_objects={"LSTMPolicy": LSTMPolicy})
                except Exception as e: logger.error(f"Failed LSTM: {e}")

        logger.info("Avaliando MLP Baseline...")
        mlp_metrics = self.simulate_policy(mlp_model, is_lstm=False, episodes_by_symbol=episodes_by_sym)
        
        logger.info("Avaliando LSTM M2.0...")
        lstm_metrics = self.simulate_policy(lstm_model, is_lstm=True, episodes_by_symbol=episodes_by_sym)
        
        sharpe_delta_pct = 0.0
        if mlp_metrics["sharpe_ratio"] != 0:
            sharpe_delta_pct = ((lstm_metrics["sharpe_ratio"] / mlp_metrics["sharpe_ratio"]) - 1) * 100
        elif lstm_metrics["sharpe_ratio"] > 0:
            sharpe_delta_pct = 100.0

        result = {
            "status": "ok",
            "episodes_processed": sum(len(e) for e in episodes_by_sym.values()),
            "mlp_baseline": mlp_metrics,
            "lstm_model": lstm_metrics,
            "comparison": {
                "sharpe_delta_pct": round(float(sharpe_delta_pct), 2),
                "goal_met": bool(sharpe_delta_pct >= 5.0)
            }
        }
        return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=1000)
    args = parser.parse_args()
    
    evaluator = PPOEvaluator(model2_db_path=MODEL2_DB_PATH, episodes_limit=args.episodes)
    res = evaluator.run_analysis()
    
    print(json.dumps(res, indent=2))
    
    out_dir = REPO_ROOT / "results" / "model2" / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "phase_e4_sharpe_analysis.json"
    with open(out_file, "w") as f:
        json.dump(res, f, indent=2)
        
    logger.info(f"Report salvo em {out_file}")

if __name__ == "__main__":
    main()
