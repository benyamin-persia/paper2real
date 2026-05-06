"""Mechanical order block detection for Paper2Real."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import market_structure


REPORT_CSV = Path("data/reports/order_blocks.csv")
REPORT_JSON = Path("data/reports/order_blocks.json")


def detect_order_blocks(
    df: pd.DataFrame,
    structure: dict,
    timeframe: str = "15m",
    higher_trend: str = "neutral",
) -> dict:
    candles = market_structure.clean_candles(df)
    events = [e for e in (structure.get("events") or []) if "BOS" in str(e.get("event_type", ""))]
    blocks: list[dict] = []
    if candles.empty:
        return {"timeframe": timeframe, "order_blocks": blocks, "active_order_blocks": blocks, "order_block_state": "none"}

    candles = candles.reset_index(drop=True)
    body = (candles["close"] - candles["open"]).abs()
    avg_body = float(body.rolling(20).mean().fillna(body.mean()).iloc[-1] or 0)
    avg_volume = float(candles["volume"].rolling(20).mean().fillna(candles["volume"].mean()).iloc[-1] or 0)

    for event in events[-40:]:
        event_ts = pd.to_datetime(event["event_time"], errors="coerce")
        if pd.isna(event_ts):
            continue
        idxs = candles.index[candles["timestamp"] <= event_ts].tolist()
        if not idxs:
            continue
        idx = idxs[-1]
        bullish = str(event["event_type"]).startswith("bullish")
        lookback = candles.iloc[max(0, idx - 12) : idx]
        if bullish:
            candidates = lookback[lookback["close"] < lookback["open"]]
            ob_type = "bullish"
        else:
            candidates = lookback[lookback["close"] > lookback["open"]]
            ob_type = "bearish"
        if candidates.empty:
            continue
        ob = candidates.iloc[-1]
        price_low = float(min(ob["open"], ob["close"], ob["low"]))
        price_high = float(max(ob["open"], ob["close"], ob["high"]))
        after = candles[candles["timestamp"] > event_ts]
        mitigated_rows = after[(after["low"] <= price_high) & (after["high"] >= price_low)]
        mitigated = not mitigated_rows.empty
        strength = 0
        strength += 20
        strength += 20 if abs(float(ob["close"]) - float(ob["open"])) > avg_body else 0
        strength += 20 if float(ob.get("volume", 0)) > avg_volume else 0
        strength += 20 if not mitigated else 0
        strength += 20 if higher_trend in {ob_type, "neutral"} else 0
        blocks.append(
            {
                "order_block_id": f"{timeframe}_ob_{len(blocks)+1}",
                "timeframe": timeframe,
                "type": ob_type,
                "created_at": ob["timestamp"].isoformat(),
                "price_low": round(price_low, 2),
                "price_high": round(price_high, 2),
                "bos_event_id": event.get("event_id"),
                "mitigated": bool(mitigated),
                "mitigated_at": mitigated_rows.iloc[0]["timestamp"].isoformat() if mitigated else None,
                "strength_score": int(strength),
                "active": not mitigated and strength >= 40,
            }
        )

    active = [b for b in blocks if b["active"]]
    return {
        "timeframe": timeframe,
        "order_blocks": blocks,
        "active_order_blocks": active,
        "latest_order_block": blocks[-1] if blocks else None,
        "order_block_state": f"{len(active)} active",
    }


def save_order_blocks(results: dict[str, dict]) -> list[dict]:
    rows = []
    for result in results.values():
        rows.extend(result.get("order_blocks") or [])
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(REPORT_CSV, index=False)
    REPORT_JSON.write_text(json.dumps({"order_blocks": rows, "count": len(rows)}, indent=2), encoding="utf-8")
    return rows


def run(
    timeframes: dict[str, pd.DataFrame],
    structure_results: dict[str, dict],
    save: bool = True,
) -> dict[str, dict]:
    higher_trend = (structure_results.get("4h") or structure_results.get("1h") or {}).get("trend", "neutral")
    results = {
        tf: detect_order_blocks(
            df,
            structure_results.get(tf) or {},
            timeframe=tf,
            higher_trend=higher_trend,
        )
        for tf, df in timeframes.items()
    }
    if save:
        save_order_blocks(results)
    return results
