from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import technical_analysis


REPORT_DIR = Path("data/reports")
CSV_PATH = REPORT_DIR / "support_resistance_zones.csv"
JSON_PATH = REPORT_DIR / "support_resistance_zones.json"


def _zone(zone_id, timeframe, zone_type, price, width, strength, reason, last_touched_at=None):
    return {
        "zone_id": zone_id,
        "timeframe": timeframe,
        "zone_type": zone_type,
        "price_low": round(price - width, 2),
        "price_high": round(price + width, 2),
        "strength_score": int(max(0, min(100, strength))),
        "touch_count": 1,
        "last_touched_at": last_touched_at,
        "broken": False,
        "broken_at": None,
        "retested": False,
        "retested_at": None,
        "active": True,
        "reason": reason,
    }


def detect(timeframe: str) -> list[dict]:
    df = technical_analysis.load_timeframe(timeframe)
    if df.empty:
        return []
    df = df.tail(240).reset_index(drop=True)
    close = float(df["close"].iloc[-1])
    width = max(close * 0.0015, 25.0)
    zones = []
    highs, lows = df["high"], df["low"]
    for idx in range(3, len(df) - 3):
        ts = df["timestamp"].iloc[idx].isoformat()
        if highs.iloc[idx] == highs.iloc[idx - 3 : idx + 4].max():
            price = float(highs.iloc[idx])
            zones.append(_zone(f"{timeframe}-swing-high-{idx}", timeframe, "resistance", price, width, 35, "recent swing high", ts))
        if lows.iloc[idx] == lows.iloc[idx - 3 : idx + 4].min():
            price = float(lows.iloc[idx])
            zones.append(_zone(f"{timeframe}-swing-low-{idx}", timeframe, "support", price, width, 35, "recent swing low", ts))
    zones = sorted(zones, key=lambda z: abs(((z["price_low"] + z["price_high"]) / 2) - close))[:16]
    daily = df.set_index("timestamp").resample("1D").agg({"high": "max", "low": "min"}).dropna()
    if len(daily) >= 2:
        prev = daily.iloc[-2]
        zones.append(_zone(f"{timeframe}-previous-day-high", timeframe, "previous_day_high", float(prev["high"]), width, 55, "previous day high"))
        zones.append(_zone(f"{timeframe}-previous-day-low", timeframe, "previous_day_low", float(prev["low"]), width, 55, "previous day low"))
    weekly = df.set_index("timestamp").resample("1W").agg({"high": "max", "low": "min"}).dropna()
    if len(weekly) >= 2:
        prev = weekly.iloc[-2]
        zones.append(_zone(f"{timeframe}-previous-week-high", timeframe, "previous_week_high", float(prev["high"]), width, 70, "previous week high"))
        zones.append(_zone(f"{timeframe}-previous-week-low", timeframe, "previous_week_low", float(prev["low"]), width, 70, "previous week low"))
    round_step = 1000 if close > 50000 else 500
    for level in (round(close / round_step) * round_step, (int(close / round_step) + 1) * round_step, (int(close / round_step) - 1) * round_step):
        zones.append(_zone(f"{timeframe}-round-{int(level)}", timeframe, "round_number", float(level), width, 30, "psychological round level"))
    indicators = technical_analysis.calculate_indicators(df, timeframe)
    if not indicators.empty:
        last = indicators.iloc[-1]
        for ema in ("ema20", "ema50", "ema200"):
            price = last.get(ema)
            if price and not pd.isna(price):
                ztype = "ema_support" if close >= float(price) else "ema_resistance"
                zones.append(_zone(f"{timeframe}-{ema}", timeframe, ztype, float(price), width, 50, f"{ema.upper()} dynamic level"))
        for key, ztype in (("bb_lower", "bb_support"), ("bb_upper", "bb_resistance")):
            price = last.get(key)
            if price and not pd.isna(price):
                zones.append(_zone(f"{timeframe}-{key}", timeframe, ztype, float(price), width, 45, f"{key} band level"))
    for z in zones:
        mid = (z["price_low"] + z["price_high"]) / 2
        touches = int(((df["low"] <= z["price_high"]) & (df["high"] >= z["price_low"])).sum())
        z["touch_count"] = touches
        z["strength_score"] = int(max(z["strength_score"], min(100, z["strength_score"] + min(20, touches * 4))))
        z["broken"] = bool(close < z["price_low"] if "support" in z["zone_type"] or "low" in z["zone_type"] else close > z["price_high"])
        z["active"] = not z["broken"]
    return zones


def run(save: bool = True) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    zones = []
    for tf in ("15m", "1h", "4h"):
        zones.extend(detect(tf))
    payload = {"count": len(zones), "zones": zones}
    if save:
        pd.DataFrame(zones).to_csv(CSV_PATH, index=False)
        JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
