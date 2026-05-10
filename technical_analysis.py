from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pandas_ta as ta


REPORT_DIR = Path("data/reports")
RAW_DIR = Path("data/raw")
INDICATORS_CSV = REPORT_DIR / "technical_indicators.csv"
INDICATORS_JSON = REPORT_DIR / "technical_indicators.json"


def _safe_float(value, digits: int = 6):
    try:
        if pd.isna(value):
            return None
        return round(float(value), digits)
    except Exception:
        return None


def _load_15m() -> pd.DataFrame:
    path = RAW_DIR / "live_btc_15m.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    return normalize_candles(df)


def normalize_candles(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp")
    out = out.drop_duplicates(subset=["timestamp"], keep="last")
    return out.reset_index(drop=True)


def resample_candles(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    df = normalize_candles(df)
    if df.empty or timeframe == "15m":
        return df
    rule = {"1h": "1H", "4h": "4H"}.get(timeframe)
    if not rule:
        return pd.DataFrame()
    indexed = df.set_index("timestamp")
    out = indexed.resample(rule, label="right", closed="right").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return out.dropna(subset=["open", "high", "low", "close"]).reset_index()


def load_timeframe(timeframe: str) -> pd.DataFrame:
    direct = RAW_DIR / f"live_btc_{timeframe}.csv"
    if direct.exists():
        df = normalize_candles(pd.read_csv(direct))
        if not df.empty:
            return df
    return resample_candles(_load_15m(), timeframe)


def _state(row: pd.Series) -> tuple[str, str, str]:
    close = float(row.get("close") or 0)
    ema20 = row.get("ema20")
    ema50 = row.get("ema50")
    ema200 = row.get("ema200")
    rsi = row.get("rsi14")
    macd_hist = row.get("macd_histogram")
    bb_width = row.get("bb_width")
    bb_squeeze = bool(row.get("bb_squeeze"))
    if close and ema20 and ema50 and ema200 and close > ema20 > ema50 > ema200:
        trend = "bullish"
    elif close and ema20 and ema50 and ema200 and close < ema20 < ema50 < ema200:
        trend = "bearish"
    else:
        trend = "neutral"
    if rsi is not None and rsi >= 70:
        momentum = "overbought"
    elif rsi is not None and rsi <= 30:
        momentum = "oversold"
    elif macd_hist is not None and macd_hist > 0 and rsi is not None and rsi >= 50:
        momentum = "bullish"
    elif macd_hist is not None and macd_hist < 0 and rsi is not None and rsi <= 50:
        momentum = "bearish"
    elif macd_hist is not None and macd_hist > 0:
        momentum = "recovering"
    elif macd_hist is not None and macd_hist < 0:
        momentum = "weakening"
    else:
        momentum = "neutral"
    volatility = "squeeze" if bb_squeeze else "high" if bb_width and bb_width > 0.08 else "normal"
    return trend, momentum, volatility


def calculate_indicators(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    df = normalize_candles(df)
    if df.empty:
        return pd.DataFrame()
    close, high, low, volume = df["close"], df["high"], df["low"], df["volume"].fillna(0)
    out = df.copy()
    for length in (20, 50, 200):
        out[f"ema{length}"] = ta.ema(close, length=length)
        out[f"sma{length}"] = ta.sma(close, length=length)
    out["rsi14"] = ta.rsi(close, length=14)
    macd = ta.macd(close, fast=12, slow=26, signal=9)
    if macd is not None and not macd.empty:
        out["macd"] = macd["MACD_12_26_9"]
        out["macd_signal"] = macd["MACDs_12_26_9"]
        out["macd_histogram"] = macd["MACDh_12_26_9"]
    else:
        out["macd"] = 0.0
        out["macd_signal"] = 0.0
        out["macd_histogram"] = 0.0
    bb = ta.bbands(close, length=20, std=2)
    if bb is not None and not bb.empty:
        out["bb_upper"] = bb[[c for c in bb.columns if c.startswith("BBU")][0]]
        out["bb_middle"] = bb[[c for c in bb.columns if c.startswith("BBM")][0]]
        out["bb_lower"] = bb[[c for c in bb.columns if c.startswith("BBL")][0]]
    else:
        out["bb_upper"] = close
        out["bb_middle"] = close
        out["bb_lower"] = close
    out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / out["bb_middle"]
    width_q20 = out["bb_width"].rolling(120, min_periods=20).quantile(0.2)
    out["bb_squeeze"] = out["bb_width"] <= width_q20
    out["atr14"] = ta.atr(high, low, close, length=14)
    out["volume_ma"] = ta.sma(volume, length=20)
    out["volume_ratio"] = volume / out["volume_ma"]
    zero_ratio = float((volume.tail(50) <= 0).mean()) if len(volume) else 1.0
    out["volume_quality"] = "unreliable" if zero_ratio > 0.2 else "reliable"
    out["volume_spike"] = out["volume_ratio"] >= 1.8
    out["distance_ema20"] = (close - out["ema20"]) / close * 100
    out["distance_ema50"] = (close - out["ema50"]) / close * 100
    out["distance_ema200"] = (close - out["ema200"]) / close * 100
    out["atr_percent"] = out["atr14"] / close * 100
    rows = []
    for _, row in out.iterrows():
        trend, momentum, volatility = _state(row)
        aligned = sum(
            1
            for ema in ("ema20", "ema50", "ema200")
            if row.get(ema) is not None and not pd.isna(row.get(ema)) and row["close"] > row[ema]
        )
        strength = 50 + (aligned - 1.5) * 20
        if trend == "bullish":
            strength += 10
        if trend == "bearish":
            strength -= 10
        rows.append(
            {
                "timeframe": timeframe,
                "timestamp": row["timestamp"].isoformat(),
                "close": _safe_float(row["close"], 2),
                "ema20": _safe_float(row.get("ema20"), 2),
                "ema50": _safe_float(row.get("ema50"), 2),
                "ema200": _safe_float(row.get("ema200"), 2),
                "sma20": _safe_float(row.get("sma20"), 2),
                "sma50": _safe_float(row.get("sma50"), 2),
                "sma200": _safe_float(row.get("sma200"), 2),
                "rsi14": _safe_float(row.get("rsi14"), 2),
                "macd": _safe_float(row.get("macd"), 4),
                "macd_signal": _safe_float(row.get("macd_signal"), 4),
                "macd_histogram": _safe_float(row.get("macd_histogram"), 4),
                "bb_upper": _safe_float(row.get("bb_upper"), 2),
                "bb_middle": _safe_float(row.get("bb_middle"), 2),
                "bb_lower": _safe_float(row.get("bb_lower"), 2),
                "bb_width": _safe_float(row.get("bb_width"), 6),
                "bb_squeeze": bool(row.get("bb_squeeze")),
                "atr14": _safe_float(row.get("atr14"), 2),
                "volume_ratio": _safe_float(row.get("volume_ratio"), 4),
                "volume_quality": row.get("volume_quality"),
                "trend_state": trend,
                "momentum_state": momentum,
                "volatility_state": volatility,
                "trend_strength_score": max(0, min(100, round(strength, 2))),
            }
        )
    return pd.DataFrame(rows)


def run(save: bool = True) -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for timeframe in ("15m", "1h", "4h"):
        frame = calculate_indicators(load_timeframe(timeframe), timeframe)
        if not frame.empty:
            frames.append(frame.tail(240))
    all_rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    records = json.loads(all_rows.to_json(orient="records")) if not all_rows.empty else []
    latest = {}
    for tf in ("15m", "1h", "4h"):
        tf_rows = [r for r in records if r.get("timeframe") == tf]
        latest[tf] = tf_rows[-1] if tf_rows else {}
    payload = {"count": len(records), "latest": latest, "rows": records}
    if save:
        all_rows.to_csv(INDICATORS_CSV, index=False)
        INDICATORS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
