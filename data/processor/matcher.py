"""
Pattern matcher — finds the N most similar historical moments
to the current market conditions.

When Claude sees "RSI=28, above EMA200, high volume, fear=25"
we find the 20 closest matches in 2 years of history and show
Claude exactly what happened next each time.
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATASET = Path("data/processed/master_dataset.csv")

# features used for similarity matching
MATCH_FEATURES = [
    "rsi_14",
    "macd_hist",
    "bb_width",
    "volume_ratio",
    "above_ema200",
    "above_ema50",
    "ema_bullish",
    "macd_bullish",
    "stoch_k",
    "atr_14",
]

_df_cache: pd.DataFrame | None = None


def _load() -> pd.DataFrame:
    global _df_cache
    if _df_cache is None and DATASET.exists():
        _df_cache = pd.read_csv(DATASET, parse_dates=["timestamp"])
    return _df_cache


def find_similar(current: dict, n: int = 20) -> list[dict]:
    """
    Find the N most similar historical candles to current conditions.

    current: dict with keys matching MATCH_FEATURES
    Returns: list of dicts with historical context + outcomes
    """
    df = _load()
    if df is None or df.empty:
        return []

    # build feature vectors
    available = [f for f in MATCH_FEATURES if f in df.columns and f in current]
    if not available:
        return []

    hist_matrix = df[available].fillna(0).values.astype(float)
    curr_vector = np.array([float(current.get(f, 0)) for f in available])

    # normalize each feature 0-1 so RSI and volume_ratio are equally weighted
    mins  = hist_matrix.min(axis=0)
    maxes = hist_matrix.max(axis=0)
    rng   = np.where(maxes - mins == 0, 1, maxes - mins)

    hist_norm = (hist_matrix - mins) / rng
    curr_norm = (curr_vector - mins) / rng

    # euclidean distance
    distances = np.linalg.norm(hist_norm - curr_norm, axis=1)
    top_idx   = np.argsort(distances)[:n]

    results = []
    for idx in top_idx:
        row = df.iloc[idx]
        results.append({
            "timestamp":        str(row["timestamp"]),
            "price":            round(float(row["close"]), 2),
            "rsi_14":           round(float(row["rsi_14"]), 1),
            "macd_bullish":     int(row["macd_bullish"]),
            "above_ema200":     int(row["above_ema200"]),
            "volume_ratio":     round(float(row["volume_ratio"]), 2),
            "future_return_1h": round(float(row["future_return_1h"]), 2),
            "future_return_4h": round(float(row["future_return_4h"]), 2),
            "future_return_24h":round(float(row["future_return_24h"]), 2),
            "hit_tp_before_sl": int(row["hit_tp_before_sl"]),
            "signal":           str(row["signal"]),
            "similarity":       round(float(1 - distances[idx] / (distances.max() + 1e-9)), 3),
        })

    return results


def summarize_similar(similar: list[dict]) -> dict:
    """Turn raw similar matches into a statistical summary for Claude."""
    if not similar:
        return {}

    win_rate   = sum(s["hit_tp_before_sl"] for s in similar) / len(similar) * 100
    avg_1h     = sum(s["future_return_1h"]  for s in similar) / len(similar)
    avg_4h     = sum(s["future_return_4h"]  for s in similar) / len(similar)
    avg_24h    = sum(s["future_return_24h"] for s in similar) / len(similar)
    buy_count  = sum(1 for s in similar if s["signal"] == "BUY")
    sell_count = sum(1 for s in similar if s["signal"] == "SELL")

    return {
        "matches_found":    len(similar),
        "historical_win_rate_pct": round(win_rate, 1),
        "avg_return_1h":    round(avg_1h, 2),
        "avg_return_4h":    round(avg_4h, 2),
        "avg_return_24h":   round(avg_24h, 2),
        "buy_signals":      buy_count,
        "sell_signals":     sell_count,
        "hold_signals":     len(similar) - buy_count - sell_count,
        "best_case_4h":     round(max(s["future_return_4h"] for s in similar), 2),
        "worst_case_4h":    round(min(s["future_return_4h"] for s in similar), 2),
    }
