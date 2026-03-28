"""Phase D.5: Análise de correlação com dados REAIS.

Analisa as mesmas correlações da Fase D.4, mas utilizando dados reais
coletados pelo processo M2-016.2 em modo live/shadow.

- Correlação entre FR sentiment e label (win/loss)
- Correlação entre FR trend e reward_proxy
- Correlação entre OI sentiment e label (win/loss)
"""

from __future__ import annotations

import argparse
import importlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ImportError:
    print("Instale: pip install numpy scipy")
    sys.exit(1)

stats = importlib.import_module("scipy.stats")

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.settings import MODEL2_DB_PATH

DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "model2" / "analysis"


def _safe_json_dict(raw_value: Any) -> dict[str, Any]:
    try:
        payload = json.loads(raw_value or "{}")
    except json.JSONDecodeError:
        payload = {}
    return payload if isinstance(payload, dict) else {}


def _sentiment_to_numeric(sentiment: str) -> float:
    """Converte sentiment para valor numerico para correlacao."""
    mapping = {
        "bullish": 1.0,
        "neutral": 0.0,
        "bearish": -1.0,
        "accumulating": 1.0,  # Para OI
        "distributing": -1.0, # Para OI
    }
    return mapping.get(str(sentiment).lower(), 0.0)


def _trend_to_numeric(trend: str) -> float:
    """Converte trend para valor numerico."""
    mapping = {
        "increasing": 1.0,
        "stable": 0.0,
        "decreasing": -1.0,
    }
    return mapping.get(str(trend).lower(), 0.0)


def _label_to_numeric(label: str) -> float | None:
    """Converte label para valor numerico (win=1, loss=-1, breakeven=0)."""
    mapping = {
        "win": 1.0,
        "loss": -1.0,
        "breakeven": 0.0,
    }
    return mapping.get(str(label).lower())


def build_phase_e_metrics_bundle(
    *,
    sharpe_mlp: float,
    sharpe_lstm: float,
    win_rate_mlp: float,
    win_rate_lstm: float,
    drawdown_mlp: float,
    drawdown_lstm: float,
) -> dict[str, Any]:
    """Consolida metricas de comparativo MLP/LSTM para a Fase E."""
    return {
        "sharpe": {"mlp": sharpe_mlp, "lstm": sharpe_lstm, "delta_lstm_minus_mlp": sharpe_lstm - sharpe_mlp},
        "win_rate": {"mlp": win_rate_mlp, "lstm": win_rate_lstm, "delta_lstm_minus_mlp": win_rate_lstm - win_rate_mlp},
        "drawdown": {"mlp": drawdown_mlp, "lstm": drawdown_lstm, "delta_lstm_minus_mlp": drawdown_lstm - drawdown_mlp},
    }


class RealDataCorrelationAnalyzer:
    """Analiza correlacoes em dados reais de episodios de treino."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        if self.conn:
            self.conn.close()

    def load_episodes(self, execution_mode: str) -> list[dict[str, Any]]:
        """Carrega training episodes para um dado execution_mode."""
        # Query para juntar `training_episodes` com `signal_executions`
        # para filtrar por `execution_mode`.
        rows = self.conn.execute(
            """
            SELECT 
                te.episode_key,
                te.symbol,
                te.label,
                te.reward_proxy,
                te.features_json
            FROM training_episodes te
            JOIN signal_executions se ON te.execution_id = se.id
            WHERE te.label IS NOT NULL
              AND te.label != 'context'
              AND te.features_json IS NOT NULL
              AND se.execution_mode = ?
            ORDER BY te.episode_key
            """,
            (execution_mode,),
        ).fetchall()

        episodes: list[dict[str, Any]] = []
        for row in rows:
            try:
                features = _safe_json_dict(row["features_json"])
                episodes.append({
                    "episode_key": str(row["episode_key"]),
                    "symbol": str(row["symbol"]),
                    "label": str(row["label"]),
                    "reward_proxy": float(row["reward_proxy"]) if row["reward_proxy"] is not None else None,
                    "features": features,
                })
            except Exception:
                pass

        return episodes

    def analyze_fr_sentiment_vs_label(self, episodes: list[dict[str, Any]]) -> dict[str, Any]:
        """Analiza correlacao entre funding rate sentiment e label."""
        fr_sentiments: list[float] = []
        labels_numeric: list[float] = []

        for ep in episodes:
            features = ep.get("features", {})
            fr_data = features.get("funding_rates", {})
            
            if not fr_data or "sentiment" not in fr_data:
                continue

            sentiment = _sentiment_to_numeric(fr_data["sentiment"])
            label_num = _label_to_numeric(ep["label"])
            
            if label_num is not None:
                fr_sentiments.append(sentiment)
                labels_numeric.append(label_num)

        if len(fr_sentiments) < 3:
            return {"status": "INSUFFICIENT_DATA", "n_samples": len(fr_sentiments)}

        corr_pearson, p_value_pearson = stats.pearsonr(fr_sentiments, labels_numeric)
        corr_spearman, p_value_spearman = stats.spearmanr(fr_sentiments, labels_numeric)

        sentiment_outcomes: dict[str, list[float]] = {"bullish": [], "neutral": [], "bearish": []}
        for i, sentiment in enumerate(fr_sentiments):
            if sentiment > 0.5:
                sentiment_outcomes["bullish"].append(labels_numeric[i])
            elif sentiment < -0.5:
                sentiment_outcomes["bearish"].append(labels_numeric[i])
            else:
                sentiment_outcomes["neutral"].append(labels_numeric[i])

        win_rates: dict[str, dict[str, float | int]] = {}
        for sentiment_key, outcomes in sentiment_outcomes.items():
            if outcomes:
                win_rate = sum(1 for x in outcomes if x > 0) / len(outcomes)
                win_rates[sentiment_key] = {
                    "win_rate": win_rate,
                    "n_episodes": len(outcomes),
                    "avg_reward": float(np.mean(outcomes)),
                    "std_reward": float(np.std(outcomes)) if len(outcomes) > 1 else 0.0,
                }

        return {
            "status": "OK",
            "n_samples": len(fr_sentiments),
            "pearson_correlation": float(corr_pearson),
            "pearson_p_value": float(p_value_pearson),
            "spearman_correlation": float(corr_spearman),
            "spearman_p_value": float(p_value_spearman),
            "win_rates_by_sentiment": win_rates,
            "interpretation": _interpret_correlation(corr_pearson, p_value_pearson),
        }

    def analyze_fr_trend_vs_reward(self, episodes: list[dict[str, Any]]) -> dict[str, Any]:
        """Analiza correlacao entre funding rate trend e reward."""
        fr_trends: list[float] = []
        rewards: list[float] = []

        for ep in episodes:
            features = ep.get("features", {})
            fr_data = features.get("funding_rates", {})
            
            if not fr_data or "trend" not in fr_data:
                continue

            trend = _trend_to_numeric(fr_data["trend"])
            reward = ep.get("reward_proxy")
            
            if reward is not None:
                fr_trends.append(trend)
                rewards.append(float(reward))

        if len(fr_trends) < 3:
            return {"status": "INSUFFICIENT_DATA", "n_samples": len(fr_trends)}

        corr_pearson, p_value = stats.pearsonr(fr_trends, rewards)
        corr_spearman, p_value_spearman = stats.spearmanr(fr_trends, rewards)

        trend_outcomes: dict[str, list[float]] = {"increasing": [], "stable": [], "decreasing": []}
        for i, trend in enumerate(fr_trends):
            if trend > 0.5:
                trend_outcomes["increasing"].append(rewards[i])
            elif trend < -0.5:
                trend_outcomes["decreasing"].append(rewards[i])
            else:
                trend_outcomes["stable"].append(rewards[i])

        avg_rewards: dict[str, dict[str, float | int]] = {}
        for trend_key, reward_list in trend_outcomes.items():
            if reward_list:
                avg_rewards[trend_key] = {
                    "avg_reward": float(np.mean(reward_list)),
                    "std_reward": float(np.std(reward_list)) if len(reward_list) > 1 else 0.0,
                    "min_reward": float(np.min(reward_list)),
                    "max_reward": float(np.max(reward_list)),
                    "n_episodes": len(reward_list),
                }

        return {
            "status": "OK",
            "n_samples": len(fr_trends),
            "pearson_correlation": float(corr_pearson),
            "pearson_p_value": float(p_value),
            "spearman_correlation": float(corr_spearman),
            "spearman_p_value": float(p_value_spearman),
            "avg_rewards_by_trend": avg_rewards,
            "interpretation": _interpret_correlation(corr_pearson, p_value),
        }

    def analyze_oi_sentiment_vs_label(self, episodes: list[dict[str, Any]]) -> dict[str, Any]:
        """Analiza correlacao entre OI sentiment e label."""
        oi_sentiments: list[float] = []
        labels_numeric: list[float] = []

        for ep in episodes:
            features = ep.get("features", {})
            oi_data = features.get("open_interest", {})
            
            if not oi_data or "oi_sentiment" not in oi_data:
                continue

            sentiment = _sentiment_to_numeric(oi_data["oi_sentiment"])
            label_num = _label_to_numeric(ep["label"])
            
            if label_num is not None:
                oi_sentiments.append(sentiment)
                labels_numeric.append(label_num)

        if len(oi_sentiments) < 3:
            return {"status": "INSUFFICIENT_DATA", "n_samples": len(oi_sentiments)}

        corr_pearson, p_value_pearson = stats.pearsonr(oi_sentiments, labels_numeric)
        corr_spearman, p_value_spearman = stats.spearmanr(oi_sentiments, labels_numeric)

        sentiment_outcomes: dict[str, list[float]] = {"accumulating": [], "neutral": [], "distributing": []}
        for i, sentiment in enumerate(oi_sentiments):
            # Bullish (accumulating) vs Bearish (distributing)
            if sentiment > 0.5:
                sentiment_outcomes["accumulating"].append(labels_numeric[i])
            elif sentiment < -0.5:
                sentiment_outcomes["distributing"].append(labels_numeric[i])
            else:
                sentiment_outcomes["neutral"].append(labels_numeric[i])

        win_rates: dict[str, dict[str, float | int]] = {}
        for sentiment_key, outcomes in sentiment_outcomes.items():
            if outcomes:
                win_rate = sum(1 for x in outcomes if x > 0) / len(outcomes)
                win_rates[sentiment_key] = {
                    "win_rate": win_rate,
                    "n_episodes": len(outcomes),
                    "avg_reward": float(np.mean(outcomes)),
                }

        return {
            "status": "OK",
            "n_samples": len(oi_sentiments),
            "pearson_correlation": float(corr_pearson),
            "pearson_p_value": float(p_value_pearson),
            "spearman_correlation": float(corr_spearman),
            "spearman_p_value": float(p_value_spearman),
            "win_rates_by_sentiment": win_rates,
            "interpretation": _interpret_correlation(corr_pearson, p_value_pearson),
        }

    def generate_report(self, execution_mode: str, min_episodes: int) -> dict[str, Any]:
        """Gera relatorio completo de correlacao para dados reais."""
        episodes = self.load_episodes(execution_mode)

        if len(episodes) < min_episodes:
            print(f"[ERROR] Dados insuficientes. Encontrado(s) {len(episodes)} episodio(s) para o modo '{execution_mode}', mas o minimo requerido e {min_episodes}.")
            return {"status": "FAILED", "error": f"Insufficient data: found {len(episodes)} episodes, minimum required is {min_episodes}"}

        print(f"[ANALYSIS] Analisando {len(episodes)} episodios do modo '{execution_mode}'...")

        report = {
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "analysis_type": "Phase D.5 Real Data Correlation Analysis",
            "execution_mode": execution_mode,
            "total_episodes": len(episodes),
            "fr_sentiment_vs_label": self.analyze_fr_sentiment_vs_label(episodes),
            "fr_trend_vs_reward": self.analyze_fr_trend_vs_reward(episodes),
            "oi_sentiment_vs_label": self.analyze_oi_sentiment_vs_label(episodes),
            "recommendations": self._generate_recommendations(episodes),
        }

        return report

    def _generate_recommendations(self, episodes: list[dict[str, Any]]) -> list[str]:
        """Gera recomendacoes baseadas nos dados."""
        recommendations: list[str] = []

        label_counts = {"win": 0, "loss": 0, "breakeven": 0}
        for ep in episodes:
            label = ep.get("label", "unknown")
            if label in label_counts:
                label_counts[label] += 1

        total = sum(label_counts.values())
        if total > 0:
            win_rate = label_counts["win"] / total
            if win_rate < 0.4:
                recommendations.append(
                    f"[WARNING] Win rate baixo ({win_rate:.2%}). Considere: (1) aumentar reward para winners, "
                    "(2) investigar sinais com FR bullish/OI accumulating, "
                    "(3) revisar stop loss / take profit levels"
                )
            elif win_rate > 0.6:
                recommendations.append(
                    f"[OK] Win rate alto ({win_rate:.2%}). Sistema esta funcionando bem. "
                    "Monitorar possivel overfitting ao aumentar complexidade."
                )

        rewards: list[float] = [
            float(ep["reward_proxy"])
            for ep in episodes
            if isinstance(ep.get("reward_proxy"), (int, float))
        ]
        if rewards:
            avg_reward = np.mean(rewards)
            if avg_reward < -0.1:
                recommendations.append(
                    f"[TREND] Media de reward negativa ({avg_reward:.4f}). Considere aumentar reward para winners "
                    "ou reduzir penalidade para losers."
                )

        if len(episodes) < 100:
            recommendations.append(
                f"[DATA] Amostra de {len(episodes)} episodios ainda e pequena. "
                "Correlacoes podem nao ser estatisticamente significantes. Ideal: 300+."
            )

        if not recommendations:
            recommendations.append("[OK] Dados parecem saudaveis. Continue monitorando tendencias.")

        return recommendations


def _interpret_correlation(corr: float, p_value: float) -> str:
    """Interpreta forca de correlacao."""
    if p_value > 0.05:
        return f"Nao significante (p={p_value:.4f} > 0.05)"
    
    abs_corr = abs(corr)
    if abs_corr < 0.3:
        strength = "fraca"
    elif abs_corr < 0.7:
        strength = "moderada"
    else:
        strength = "forte"
    
    direction = "positiva" if corr > 0 else "negativa"
    return f"Correlacao {strength} {direction} (r={corr:.4f}, p={p_value:.4f})"


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase D.5: Analise de Correlacao com Dados Reais")
    parser.add_argument(
        "--db",
        type=str,
        default=str(MODEL2_DB_PATH),
        help="Caminho para modelo2.db",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Diretorio de saida",
    )
    parser.add_argument(
        "--execution-mode",
        type=str,
        default="shadow",
        choices=["shadow", "live"],
        help="Modo de execucao para filtrar episodios.",
    )
    parser.add_argument(
        "--min-episodes",
        type=int,
        default=500,
        help="Numero minimo de episodios necessarios para rodar a analise.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    analyzer = RealDataCorrelationAnalyzer(db_path=args.db)
    try:
        report = analyzer.generate_report(args.execution_mode, args.min_episodes)

        if report.get("status") == "FAILED":
            print(f"\n[FAIL] Analise abortada: {report.get('error')}")
            return 1

        report_path = args.output_dir / f"phase_d5_correlation_{args.execution_mode}_{int(datetime.now(timezone.utc).timestamp())}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        print(f"\n[OK] Relatorio salvo: {report_path}")

        print("\n" + "=" * 60)
        print(f"PHASE D.5 - REAL DATA CORRELATION SUMMARY ({args.execution_mode.upper()})")
        print("=" * 60)

        print(f"\n[ANALYSIS] Total episodios analisados: {report['total_episodes']}")

        print("\n[FR SENTIMENT vs LABEL]:")
        _print_analysis_result(report.get("fr_sentiment_vs_label", {}))

        print("\n[FR TREND vs REWARD]:")
        _print_analysis_result(report.get("fr_trend_vs_reward", {}))

        print("\n[OI SENTIMENT vs LABEL]:")
        _print_analysis_result(report.get("oi_sentiment_vs_label", {}))

        print("\n[RECOMMENDATIONS]:")
        for rec in report.get("recommendations", []):
            print(f"  {rec}")

        return 0

    finally:
        analyzer.close()


def _print_analysis_result(analysis: dict[str, Any]) -> None:
    """Printa resultado da analise."""
    if not analysis or analysis.get("status") == "INSUFFICIENT_DATA":
        print(f"  [WARN] Dados insuficientes (n={analysis.get('n_samples', 0)})")
        return

    print(f"  n_samples: {analysis.get('n_samples', 'N/A')}")
    print(f"  Pearson r: {analysis.get('pearson_correlation', 'N/A'):.4f}")
    print(f"  p-value: {analysis.get('pearson_p_value', 'N/A'):.4f}")
    print(f"  Interpretacao: {analysis.get('interpretation', 'N/A')}")

    if "win_rates_by_sentiment" in analysis:
        print("\n  Por sentimento:")
        for sent, data in analysis.get("win_rates_by_sentiment", {}).items():
            if "win_rate" in data:
                print(f"    {sent}: {data['win_rate']:.2%} wins (n={data['n_episodes']})")
            else:
                print(f"    {sent}: avg_reward={data['avg_reward']:.4f} (n={data['n_episodes']})")

    if "avg_rewards_by_trend" in analysis:
        print("\n  Por trend:")
        for trend, data in analysis.get("avg_rewards_by_trend", {}).items():
            print(f"    {trend}: {data['avg_reward']:.4f} avg (n={data['n_episodes']})")


if __name__ == "__main__":
    raise SystemExit(main())
