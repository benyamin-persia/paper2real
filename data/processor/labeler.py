import pandas as pd
from pathlib import Path

INPUT  = Path("data/processed/btc_15m_indicators.csv")
OUTPUT = Path("data/processed/btc_15m_labeled.csv")

TAKE_PROFIT = 0.03   # 3% profit target
STOP_LOSS   = 0.01   # 1% stop loss
CANDLES_MAX = 96     # max 24 hours to wait (96 × 15min)


def label(df: pd.DataFrame = None) -> pd.DataFrame:
    if df is None:
        df = pd.read_csv(INPUT, parse_dates=["timestamp"])

    print(f"Labeling {len(df):,} candles (this takes a minute)...")

    closes = df["close"].values
    n      = len(closes)

    future_1h  = []  # return after 4 candles  (1 hour)
    future_4h  = []  # return after 16 candles (4 hours)
    future_24h = []  # return after 96 candles (24 hours)
    signal     = []  # BUY / SELL / HOLD
    hit_tp     = []  # hit 3% profit before 1% loss?

    for i in range(n):
        entry = closes[i]

        # future returns
        r1h  = (closes[min(i+4,  n-1)] - entry) / entry * 100
        r4h  = (closes[min(i+16, n-1)] - entry) / entry * 100
        r24h = (closes[min(i+96, n-1)] - entry) / entry * 100
        future_1h.append(round(r1h, 4))
        future_4h.append(round(r4h, 4))
        future_24h.append(round(r24h, 4))

        # did price hit take profit before stop loss?
        tp_hit = False
        for j in range(i+1, min(i+CANDLES_MAX, n)):
            pct = (closes[j] - entry) / entry
            if pct >= TAKE_PROFIT:
                tp_hit = True
                break
            if pct <= -STOP_LOSS:
                break
        hit_tp.append(int(tp_hit))

        # signal label
        rsi       = df["rsi_14"].iloc[i]
        macd_bull = df["macd_bullish"].iloc[i]
        above_ema = df["above_ema200"].iloc[i]
        stoch_k   = df["stoch_k"].iloc[i]

        if rsi < 45 and above_ema and stoch_k < 30:
            signal.append("BUY")
        elif rsi > 60 and not macd_bull:
            signal.append("SELL")
        else:
            signal.append("HOLD")

    df["future_return_1h"]  = future_1h
    df["future_return_4h"]  = future_4h
    df["future_return_24h"] = future_24h
    df["hit_tp_before_sl"]  = hit_tp
    df["signal"]            = signal

    buy_count  = (df["signal"] == "BUY").sum()
    sell_count = (df["signal"] == "SELL").sum()
    win_rate   = df[df["signal"] == "BUY"]["hit_tp_before_sl"].mean() * 100

    print(f"  BUY signals:  {buy_count:,}")
    print(f"  SELL signals: {sell_count:,}")
    print(f"  Win rate on BUY signals: {win_rate:.1f}%")

    df.to_csv(OUTPUT, index=False)
    print(f"Saved labeled data → {OUTPUT}")
    return df


if __name__ == "__main__":
    label()
