"""
Master data collector.
Run this once to build the full training dataset for Claude.

Steps:
  1. Scrape 2 years of BTC 15min candles from Binance
  2. Scrape Fear & Greed index history
  3. Scrape CoinGlass (funding rate + liquidations)
  4. Scrape CoinGecko (BTC dominance + market cap)
  5. Calculate all indicators
  6. Label every candle with outcomes (win/loss/hold)
  7. Merge everything into one master dataset
"""

from pathlib import Path

import pandas as pd

from data.collector.binance import scrape as scrape_binance
from data.collector.fear_greed import scrape as scrape_fear_greed
from data.collector.coinglass import scrape as scrape_coinglass
from data.collector.coingecko import scrape as scrape_coingecko
from data.collector.macro import scrape as scrape_macro
from data.collector.onchain import scrape as scrape_onchain
from data.collector.events import scrape as scrape_events
from data.processor.indicators import calculate
from data.processor.labeler import label

OUTPUT = Path("data/processed/master_dataset.csv")


def merge_daily_data(df_15m: pd.DataFrame, *daily_dfs) -> pd.DataFrame:
    """Merge daily scraped data onto 15-minute candles by date."""
    df_15m["date"] = pd.to_datetime(df_15m["timestamp"]).dt.date

    for daily_df in daily_dfs:
        if daily_df is None or daily_df.empty:
            continue
        daily_df["date"] = pd.to_datetime(daily_df["date"]).dt.date
        df_15m = pd.merge(df_15m, daily_df, on="date", how="left")

    df_15m = df_15m.drop(columns=["date"])
    return df_15m


def run():
    print("=" * 60)
    print("  Paper2Real - Data Collection Pipeline")
    print("=" * 60)

    print("\n[1/6] Scraping Binance price data...")
    df_price = scrape_binance(days_back=730)
    if len(df_price) == 0:
        print("  ⚠️  WARNING: BTC price data is empty. All downstream steps will be skipped.")
        print("  Fix data/collector/binance.py before continuing.")
        return df_price

    print("\n[2/6] Scraping Fear & Greed index...")
    df_fg = scrape_fear_greed()

    print("\n[3/6] Scraping CoinGlass...")
    df_cg = scrape_coinglass()

    print("\n[4/6] Scraping CoinGecko...")
    df_gecko = scrape_coingecko()

    print("\n[4b] Scraping macro data (S&P500, DXY, VIX, Gold)...")
    df_macro = scrape_macro()

    print("\n[4c] Scraping on-chain data (hash rate, tx volume)...")
    df_onchain = scrape_onchain()

    print("\n[4d] Scraping CryptoPanic critical events...")
    scrape_events()   # saves data/raw/events.json — not merged into dataset

    print("\n[5/6] Calculating indicators...")
    df_ind = calculate(df_price)

    print("\n[6/6] Labeling outcomes...")
    df_labeled = label(df_ind)

    print("\nMerging all data sources...")
    df_master = merge_daily_data(df_labeled, df_fg, df_cg, df_gecko, df_macro, df_onchain)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df_master.to_csv(OUTPUT, index=False)

    print("\n" + "=" * 60)
    print(f"  DONE. Master dataset saved -> {OUTPUT}")
    print(f"  Rows:    {len(df_master):,} candles")
    print(f"  Columns: {len(df_master.columns)}")
    if len(df_master) > 0:
        print(f"  Period:  {df_master['timestamp'].iloc[0]} → {df_master['timestamp'].iloc[-1]}")
    else:
        print("  Period:  No data collected — BTC price scraper needs fixing")
    print("=" * 60)

    return df_master


if __name__ == "__main__":
    run()
