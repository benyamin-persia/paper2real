"""Closed-candle market structure detection for Paper2Real.

Detects swings, HH/HL/LH/LL, BOS, and CHoCH. This module is deterministic
and never executes trades.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


REPORT_CSV = Path("data/reports/market_structure_events.csv")
REPORT_JSON = Path("data/reports/market_structure_events.json")


def clean_candles(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in out.columns:
            out[col] = 0
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"])
    return out.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)


def detect_swings(df: pd.DataFrame, timeframe: str = "15m", swing_length: int = 5) -> list[dict]:
    candles = clean_candles(df)
    swings: list[dict] = []
    if len(candles) < swing_length * 2 + 3:
        return swings

    prev_high = None
    prev_low = None
    for i in range(swing_length, len(candles) - swing_length):
        row = candles.iloc[i]
        before = candles.iloc[i - swing_length : i]
        after = candles.iloc[i + 1 : i + swing_length + 1]
        high = float(row["high"])
        low = float(row["low"])
        ts = row["timestamp"].isoformat()

        if high > float(before["high"].max()) and high > float(after["high"].max()):
            label = "HH" if prev_high is not None and high > prev_high else "LH" if prev_high is not None else "H"
            swings.append(
                {
                    "swing_id": f"{timeframe}_H_{i}",
                    "timeframe": timeframe,
                    "index": i,
                    "event_time": ts,
                    "swing_type": "high",
                    "price": high,
                    "structure_label": label,
                    "confirmed_by_closed_candle": True,
                }
            )
            prev_high = high

        if low < float(before["low"].min()) and low < float(after["low"].min()):
            label = "HL" if prev_low is not None and low > prev_low else "LL" if prev_low is not None else "L"
            swings.append(
                {
                    "swing_id": f"{timeframe}_L_{i}",
                    "timeframe": timeframe,
                    "index": i,
                    "event_time": ts,
                    "swing_type": "low",
                    "price": low,
                    "structure_label": label,
                    "confirmed_by_closed_candle": True,
                }
            )
            prev_low = low

    return sorted(swings, key=lambda x: x["index"])


def detect_structure(df: pd.DataFrame, timeframe: str = "15m", swing_length: int = 5) -> dict:
    candles = clean_candles(df)
    swings = detect_swings(candles, timeframe=timeframe, swing_length=swing_length)
    events: list[dict] = []
    if len(candles) < 20 or not swings:
        return {
            "timeframe": timeframe,
            "trend": "neutral",
            "structure_state": "neutral",
            "latest_event": None,
            "swings": swings,
            "events": events,
        }

    swing_highs = [s for s in swings if s["swing_type"] == "high"]
    swing_lows = [s for s in swings if s["swing_type"] == "low"]
    broken_highs: set[str] = set()
    broken_lows: set[str] = set()
    trend = "neutral"

    for i, row in candles.iterrows():
        close = float(row["close"])
        ts = row["timestamp"].isoformat()
        prev_highs = [s for s in swing_highs if s["index"] < i and s["swing_id"] not in broken_highs]
        prev_lows = [s for s in swing_lows if s["index"] < i and s["swing_id"] not in broken_lows]

        if prev_highs:
            level = prev_highs[-1]
            if close > float(level["price"]):
                previous = trend
                event_type = "bullish_BOS" if trend in {"bullish", "neutral"} else "bullish_CHoCH"
                trend = "bullish"
                broken_highs.add(level["swing_id"])
                events.append(
                    {
                        "event_id": f"{timeframe}_structure_{len(events)+1}",
                        "timeframe": timeframe,
                        "event_time": ts,
                        "event_type": event_type,
                        "price": close,
                        "broken_level": float(level["price"]),
                        "previous_structure": previous,
                        "new_structure": trend,
                        "confidence": 70 if "BOS" in event_type else 75,
                        "confirmed_by_closed_candle": True,
                    }
                )

        if prev_lows:
            level = prev_lows[-1]
            if close < float(level["price"]):
                previous = trend
                event_type = "bearish_BOS" if trend in {"bearish", "neutral"} else "bearish_CHoCH"
                trend = "bearish"
                broken_lows.add(level["swing_id"])
                events.append(
                    {
                        "event_id": f"{timeframe}_structure_{len(events)+1}",
                        "timeframe": timeframe,
                        "event_time": ts,
                        "event_type": event_type,
                        "price": close,
                        "broken_level": float(level["price"]),
                        "previous_structure": previous,
                        "new_structure": trend,
                        "confidence": 70 if "BOS" in event_type else 75,
                        "confirmed_by_closed_candle": True,
                    }
                )

    latest_event = events[-1] if events else None
    labels = [s["structure_label"] for s in swings[-4:]]
    structure_state = f"{trend}: {'/'.join(labels)}" if labels else trend
    return {
        "timeframe": timeframe,
        "trend": trend,
        "structure_state": structure_state,
        "latest_event": latest_event,
        "swings": swings,
        "events": events,
    }


def save_events(results: dict[str, dict]) -> list[dict]:
    rows = []
    for result in results.values():
        rows.extend(result.get("events") or [])
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(REPORT_CSV, index=False)
    REPORT_JSON.write_text(json.dumps({"events": rows, "count": len(rows)}, indent=2), encoding="utf-8")
    return rows


def run(timeframes: dict[str, pd.DataFrame], swing_length: int = 5, save: bool = True) -> dict[str, dict]:
    results = {
        tf: detect_structure(df, timeframe=tf, swing_length=swing_length)
        for tf, df in timeframes.items()
    }
    if save:
        save_events(results)
    return results
