from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import technical_analysis


REPORT_DIR = Path("data/reports")
CSV_PATH = REPORT_DIR / "chart_patterns.csv"
JSON_PATH = REPORT_DIR / "chart_patterns.json"


def _pattern(pid, timeframe, ptype, direction, row, confidence, reason):
    return {
        "pattern_id": pid,
        "timeframe": timeframe,
        "pattern_type": ptype,
        "direction": direction,
        "detected_at": row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"]),
        "price": round(float(row["close"]), 2),
        "confidence": int(max(0, min(100, confidence))),
        "invalidated": False,
        "invalidated_at": None,
        "reason": reason,
    }


def detect(timeframe: str) -> list[dict]:
    df = technical_analysis.load_timeframe(timeframe).tail(120).reset_index(drop=True)
    if len(df) < 30:
        return []
    indicators = technical_analysis.calculate_indicators(df, timeframe)
    out = []
    last = df.iloc[-1]
    prev = df.iloc[-2]
    body = abs(last.close - last.open)
    candle_range = max(last.high - last.low, 1e-9)
    upper = last.high - max(last.close, last.open)
    lower = min(last.close, last.open) - last.low
    if last.close > last.open and last.open <= prev.close and last.close >= prev.open:
        out.append(_pattern(f"{timeframe}-bull-engulf-{len(df)}", timeframe, "bullish engulfing", "bullish", last, 65, "current candle engulfs prior body"))
    if last.close < last.open and last.open >= prev.close and last.close <= prev.open:
        out.append(_pattern(f"{timeframe}-bear-engulf-{len(df)}", timeframe, "bearish engulfing", "bearish", last, 65, "current candle engulfs prior body"))
    if lower > body * 2 and upper < body * 1.2:
        out.append(_pattern(f"{timeframe}-hammer-{len(df)}", timeframe, "hammer", "bullish", last, 55, "long lower wick"))
    if upper > body * 2 and lower < body * 1.2:
        out.append(_pattern(f"{timeframe}-shooting-star-{len(df)}", timeframe, "shooting star", "bearish", last, 55, "long upper wick"))
    if body / candle_range < 0.12:
        out.append(_pattern(f"{timeframe}-doji-{len(df)}", timeframe, "doji", "neutral", last, 50, "small body relative to range"))
    if body / candle_range > 0.65 and last.close > last.open:
        out.append(_pattern(f"{timeframe}-strong-bull-{len(df)}", timeframe, "strong bullish candle", "bullish", last, 60, "large bullish body"))
    if body / candle_range > 0.65 and last.close < last.open:
        out.append(_pattern(f"{timeframe}-strong-bear-{len(df)}", timeframe, "strong bearish candle", "bearish", last, 60, "large bearish body"))
    recent_high = df["high"].tail(30).iloc[:-1].max()
    recent_low = df["low"].tail(30).iloc[:-1].min()
    if last.close > recent_high:
        out.append(_pattern(f"{timeframe}-breakout-{len(df)}", timeframe, "breakout", "bullish", last, 70, "close above recent resistance"))
    if last.close < recent_low:
        out.append(_pattern(f"{timeframe}-breakdown-{len(df)}", timeframe, "breakdown", "bearish", last, 70, "close below recent support"))
    swing_lows = df["low"].rolling(5, center=True).min()
    swing_highs = df["high"].rolling(5, center=True).max()
    lows = df[df["low"].eq(swing_lows)].tail(3)
    highs = df[df["high"].eq(swing_highs)].tail(3)
    if len(lows) >= 2 and lows["low"].iloc[-1] > lows["low"].iloc[-2]:
        out.append(_pattern(f"{timeframe}-higher-low-{len(df)}", timeframe, "higher low setup", "bullish", last, 58, "latest swing low is higher"))
    if len(highs) >= 2 and highs["high"].iloc[-1] < highs["high"].iloc[-2]:
        out.append(_pattern(f"{timeframe}-lower-high-{len(df)}", timeframe, "lower high setup", "bearish", last, 58, "latest swing high is lower"))
    if len(highs) >= 2 and abs(highs["high"].iloc[-1] / highs["high"].iloc[-2] - 1) < 0.004:
        out.append(_pattern(f"{timeframe}-double-top-{len(df)}", timeframe, "double top", "bearish", last, 55, "two nearby swing highs"))
    if len(lows) >= 2 and abs(lows["low"].iloc[-1] / lows["low"].iloc[-2] - 1) < 0.004:
        out.append(_pattern(f"{timeframe}-double-bottom-{len(df)}", timeframe, "double bottom", "bullish", last, 55, "two nearby swing lows"))
    if not indicators.empty and len(indicators) > 8:
        a, b = indicators.iloc[-8], indicators.iloc[-1]
        if b["close"] < a["close"] and b.get("rsi14", 50) > a.get("rsi14", 50):
            out.append(_pattern(f"{timeframe}-rsi-bull-div-{len(df)}", timeframe, "bullish RSI divergence", "bullish", last, 62, "price lower while RSI improves"))
        if b["close"] > a["close"] and b.get("rsi14", 50) < a.get("rsi14", 50):
            out.append(_pattern(f"{timeframe}-rsi-bear-div-{len(df)}", timeframe, "bearish RSI divergence", "bearish", last, 62, "price higher while RSI weakens"))
        if b["close"] < a["close"] and b.get("macd_histogram", 0) > a.get("macd_histogram", 0):
            out.append(_pattern(f"{timeframe}-macd-bull-div-{len(df)}", timeframe, "bullish MACD divergence", "bullish", last, 60, "price lower while MACD histogram improves"))
        if b["close"] > a["close"] and b.get("macd_histogram", 0) < a.get("macd_histogram", 0):
            out.append(_pattern(f"{timeframe}-macd-bear-div-{len(df)}", timeframe, "bearish MACD divergence", "bearish", last, 60, "price higher while MACD histogram weakens"))
    return out[-30:]


def run(save: bool = True) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    patterns = []
    for tf in ("15m", "1h", "4h"):
        patterns.extend(detect(tf))
    payload = {"count": len(patterns), "patterns": patterns}
    if save:
        pd.DataFrame(patterns).to_csv(CSV_PATH, index=False)
        JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
