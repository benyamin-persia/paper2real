"""Liquidity zone and sweep detection for Paper2Real."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import market_structure


REPORT_CSV = Path("data/reports/liquidity_zones.csv")
REPORT_JSON = Path("data/reports/liquidity_zones.json")
EQUAL_TOLERANCE_PCT = 0.2


def _pct_diff(a: float, b: float) -> float:
    base = (abs(a) + abs(b)) / 2
    return abs(a - b) / base * 100 if base else 999


def detect_liquidity(df: pd.DataFrame, timeframe: str = "15m", swing_length: int = 5) -> dict:
    candles = market_structure.clean_candles(df)
    swings = market_structure.detect_swings(candles, timeframe=timeframe, swing_length=swing_length)
    zones: list[dict] = []

    for s in swings[-80:]:
        price = float(s["price"])
        pad = price * 0.0008
        ztype = "swing_high_liquidity" if s["swing_type"] == "high" else "swing_low_liquidity"
        zones.append(
            {
                "zone_id": f"{timeframe}_liq_{len(zones)+1}",
                "timeframe": timeframe,
                "zone_type": ztype,
                "price_low": round(price - pad, 2),
                "price_high": round(price + pad, 2),
                "created_at": s["event_time"],
                "swept": False,
                "swept_at": None,
                "sweep_type": None,
                "active": True,
            }
        )

    highs = [s for s in swings if s["swing_type"] == "high"][-30:]
    lows = [s for s in swings if s["swing_type"] == "low"][-30:]
    for items, ztype in ((highs, "equal_highs"), (lows, "equal_lows")):
        for i in range(len(items) - 1):
            a, b = items[i], items[i + 1]
            pa, pb = float(a["price"]), float(b["price"])
            if _pct_diff(pa, pb) <= EQUAL_TOLERANCE_PCT:
                lo, hi = min(pa, pb), max(pa, pb)
                zones.append(
                    {
                        "zone_id": f"{timeframe}_liq_{len(zones)+1}",
                        "timeframe": timeframe,
                        "zone_type": ztype,
                        "price_low": round(lo, 2),
                        "price_high": round(hi, 2),
                        "created_at": b["event_time"],
                        "swept": False,
                        "swept_at": None,
                        "sweep_type": None,
                        "active": True,
                    }
                )

    for zone in zones:
        created = pd.to_datetime(zone["created_at"], errors="coerce")
        if pd.isna(created):
            continue
        after = candles[candles["timestamp"] > created]
        for _, row in after.iterrows():
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])
            if "low" in zone["zone_type"] and low < float(zone["price_low"]) and close > float(zone["price_low"]):
                zone.update(
                    {
                        "swept": True,
                        "swept_at": row["timestamp"].isoformat(),
                        "sweep_type": "bullish_sweep",
                        "active": False,
                    }
                )
                break
            if "high" in zone["zone_type"] and high > float(zone["price_high"]) and close < float(zone["price_high"]):
                zone.update(
                    {
                        "swept": True,
                        "swept_at": row["timestamp"].isoformat(),
                        "sweep_type": "bearish_sweep",
                        "active": False,
                    }
                )
                break

    latest_sweep = next((z for z in reversed(zones) if z["swept"]), None)
    active = [z for z in zones if z["active"]]
    return {
        "timeframe": timeframe,
        "zones": zones,
        "active_zones": active,
        "latest_sweep": latest_sweep,
        "liquidity_state": latest_sweep["sweep_type"] if latest_sweep else "no_recent_sweep",
    }


def save_zones(results: dict[str, dict]) -> list[dict]:
    rows = []
    for result in results.values():
        rows.extend(result.get("zones") or [])
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(REPORT_CSV, index=False)
    REPORT_JSON.write_text(json.dumps({"zones": rows, "count": len(rows)}, indent=2), encoding="utf-8")
    return rows


def run(timeframes: dict[str, pd.DataFrame], swing_length: int = 5, save: bool = True) -> dict[str, dict]:
    results = {tf: detect_liquidity(df, timeframe=tf, swing_length=swing_length) for tf, df in timeframes.items()}
    if save:
        save_zones(results)
    return results
