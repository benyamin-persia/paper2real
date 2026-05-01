import pandas as pd
import pandas_ta as ta
from pathlib import Path

INPUT  = Path("data/raw/btc_15m_raw.csv")
OUTPUT = Path("data/processed/btc_15m_indicators.csv")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)


def calculate(df: pd.DataFrame = None) -> pd.DataFrame:
    if df is None:
        df = pd.read_csv(INPUT, parse_dates=["timestamp"])

    if len(df) < 30:
        print(f"  Not enough data ({len(df)} rows) — skipping indicators")
        return df

    print(f"Calculating indicators on {len(df):,} rows...")

    # trend
    df["ema_20"]  = ta.ema(df["close"], length=20)
    df["ema_50"]  = ta.ema(df["close"], length=50)
    df["ema_200"] = ta.ema(df["close"], length=200)

    # momentum
    df["rsi_14"] = ta.rsi(df["close"], length=14)

    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd is not None:
        df["macd"]        = macd["MACD_12_26_9"]
        df["macd_signal"] = macd["MACDs_12_26_9"]
        df["macd_hist"]   = macd["MACDh_12_26_9"]
    else:
        df["macd"] = df["macd_signal"] = df["macd_hist"] = float("nan")

    stoch = ta.stoch(df["high"], df["low"], df["close"], k=14, d=3)
    if stoch is not None:
        df["stoch_k"] = stoch["STOCHk_14_3_3"]
        df["stoch_d"] = stoch["STOCHd_14_3_3"]
    else:
        df["stoch_k"] = df["stoch_d"] = float("nan")

    # volatility
    bb = ta.bbands(df["close"], length=20, std=2)
    if bb is not None:
        bb_upper_col = [c for c in bb.columns if c.startswith("BBU")][0]
        bb_lower_col = [c for c in bb.columns if c.startswith("BBL")][0]
        bb_mid_col   = [c for c in bb.columns if c.startswith("BBM")][0]
        df["bb_upper"] = bb[bb_upper_col]
        df["bb_lower"] = bb[bb_lower_col]
        df["bb_mid"]   = bb[bb_mid_col]
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
    else:
        df["bb_upper"] = df["bb_lower"] = df["bb_mid"] = df["bb_width"] = float("nan")

    df["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    # volume
    df["volume_sma_20"] = ta.sma(df["volume"], length=20)
    df["volume_ratio"]  = df["volume"] / df["volume_sma_20"]

    # trend context flags
    df["above_ema200"]   = (df["close"] > df["ema_200"]).astype(int)
    df["above_ema50"]    = (df["close"] > df["ema_50"]).astype(int)
    df["ema_bullish"]    = (df["ema_20"] > df["ema_50"]).astype(int)
    df["macd_bullish"]   = (df["macd"] > df["macd_signal"]).astype(int)
    df["rsi_oversold"]   = (df["rsi_14"] < 30).astype(int)
    df["rsi_overbought"] = (df["rsi_14"] > 70).astype(int)
    df["high_volume"]    = (df["volume_ratio"] > 1.5).astype(int)

    df = df.dropna().reset_index(drop=True)
    df.to_csv(OUTPUT, index=False)
    print(f"Saved {len(df):,} rows with indicators → {OUTPUT}")
    return df


if __name__ == "__main__":
    calculate()
