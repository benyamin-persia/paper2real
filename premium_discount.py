"""Premium / discount zone calculation for Paper2Real."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import market_structure


REPORT_CSV = Path("data/reports/premium_discount_zones.csv")
REPORT_JSON = Path("data/reports/premium_discount_zones.json")


def calculate_zone(df: pd.DataFrame, structure: dict | None = None, timeframe: str = "15m") -> dict:
    candles = market_structure.clean_candles(df)
    if candles.empty:
        return {
            "timeframe": timeframe,
            "range_high": None,
            "range_low": None,
            "equilibrium": None,
            "current_zone": "unknown",
            "current_price": None,
            "created_at": None,
        }
    swings = (structure or {}).get("swings") or market_structure.detect_swings(candles, timeframe=timeframe)
    highs = [float(s["price"]) for s in swings if s["swing_type"] == "high"][-20:]
    lows = [float(s["price"]) for s in swings if s["swing_type"] == "low"][-20:]
    range_high = max(highs) if highs else float(candles["high"].tail(100).max())
    range_low = min(lows) if lows else float(candles["low"].tail(100).min())
    current_price = float(candles["close"].iloc[-1])
    equilibrium = (range_high + range_low) / 2
    if current_price < equilibrium:
        zone = "discount"
    elif current_price > equilibrium:
        zone = "premium"
    else:
        zone = "equilibrium"
    return {
        "timeframe": timeframe,
        "range_high": round(range_high, 2),
        "range_low": round(range_low, 2),
        "equilibrium": round(equilibrium, 2),
        "current_zone": zone,
        "current_price": round(current_price, 2),
        "created_at": candles["timestamp"].iloc[-1].isoformat(),
    }


def save_zones(results: dict[str, dict]) -> list[dict]:
    rows = list(results.values())
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(REPORT_CSV, index=False)
    REPORT_JSON.write_text(json.dumps({"premium_discount_zones": rows, "count": len(rows)}, indent=2), encoding="utf-8")
    return rows


def run(
    timeframes: dict[str, pd.DataFrame],
    structure_results: dict[str, dict] | None = None,
    save: bool = True,
) -> dict[str, dict]:
    structure_results = structure_results or {}
    results = {
        tf: calculate_zone(df, structure=structure_results.get(tf), timeframe=tf)
        for tf, df in timeframes.items()
    }
    if save:
        save_zones(results)
    return results
