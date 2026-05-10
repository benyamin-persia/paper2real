"""Fair Value Gap detection for Paper2Real."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pandas_ta as ta

import market_structure


REPORT_CSV = Path("data/reports/fair_value_gaps.csv")
REPORT_JSON = Path("data/reports/fair_value_gaps.json")


def detect_fvgs(
    df: pd.DataFrame,
    timeframe: str = "15m",
    trend: str = "neutral",
    order_blocks: list[dict] | None = None,
) -> dict:
    candles = market_structure.clean_candles(df)
    order_blocks = order_blocks or []
    rows: list[dict] = []
    if len(candles) < 20:
        return {"timeframe": timeframe, "fvgs": rows, "active_fvgs": rows, "latest_fvg": None, "fvg_state": "none"}

    atr = ta.atr(candles["high"], candles["low"], candles["close"], length=14).fillna(0)

    for i in range(2, len(candles)):
        c1 = candles.iloc[i - 2]
        c3 = candles.iloc[i]
        fvg_type = None
        low = high = None
        if float(c1["high"]) < float(c3["low"]):
            fvg_type = "bullish"
            low = float(c1["high"])
            high = float(c3["low"])
        elif float(c1["low"]) > float(c3["high"]):
            fvg_type = "bearish"
            low = float(c3["high"])
            high = float(c1["low"])
        if not fvg_type:
            continue

        after = candles.iloc[i + 1 :]
        if fvg_type == "bullish":
            fill_rows = after[after["low"] <= low]
        else:
            fill_rows = after[after["high"] >= high]
        filled = not fill_rows.empty
        filled_at = fill_rows.iloc[0]["timestamp"].isoformat() if filled else None

        gap_size = high - low
        score = 0
        score += 25 if gap_size > float(atr.iloc[i]) * 0.5 else 0
        score += 25 if (trend == fvg_type) else 0
        score += 25 if _near_order_block(low, high, order_blocks, fvg_type) else 0
        score += 25 if not filled else 0
        rows.append(
            {
                "fvg_id": f"{timeframe}_fvg_{len(rows)+1}",
                "timeframe": timeframe,
                "type": fvg_type,
                "created_at": c3["timestamp"].isoformat(),
                "price_low": round(low, 2),
                "price_high": round(high, 2),
                "filled": bool(filled),
                "filled_at": filled_at,
                "strength_score": int(score),
                "active": not filled,
            }
        )

    active = [r for r in rows if r["active"]]
    latest = rows[-1] if rows else None
    return {
        "timeframe": timeframe,
        "fvgs": rows,
        "active_fvgs": active,
        "latest_fvg": latest,
        "fvg_state": f"{len(active)} active",
    }


def _near_order_block(low: float, high: float, order_blocks: list[dict], fvg_type: str) -> bool:
    for ob in order_blocks:
        if ob.get("type") != fvg_type or not ob.get("active"):
            continue
        if float(ob["price_low"]) <= high and float(ob["price_high"]) >= low:
            return True
    return False


def save_fvgs(results: dict[str, dict]) -> list[dict]:
    rows = []
    for result in results.values():
        rows.extend(result.get("fvgs") or [])
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(REPORT_CSV, index=False)
    REPORT_JSON.write_text(json.dumps({"fair_value_gaps": rows, "count": len(rows)}, indent=2), encoding="utf-8")
    return rows


def run(
    timeframes: dict[str, pd.DataFrame],
    structure_results: dict[str, dict] | None = None,
    order_block_results: dict[str, dict] | None = None,
    save: bool = True,
) -> dict[str, dict]:
    structure_results = structure_results or {}
    order_block_results = order_block_results or {}
    results = {}
    for tf, df in timeframes.items():
        trend = (structure_results.get(tf) or {}).get("trend", "neutral")
        obs = (order_block_results.get(tf) or {}).get("order_blocks", [])
        results[tf] = detect_fvgs(df, timeframe=tf, trend=trend, order_blocks=obs)
    if save:
        save_fvgs(results)
    return results
