import asyncio
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ASSETS = {
    "^GSPC": "sp500",
    "DX-Y.NYB": "dxy",
    "^VIX": "vix",
    "GC=F": "gold",
}


async def _fetch_chart(page, symbol: str) -> dict | None:
    return await page.evaluate(
        """async (symbol) => {
            const encoded = encodeURIComponent(symbol);
            const urls = [
                `https://query1.finance.yahoo.com/v8/finance/chart/${encoded}?interval=1d&range=2y`,
                `https://query2.finance.yahoo.com/v8/finance/chart/${encoded}?interval=1d&range=2y`,
            ];
            for (const url of urls) {
                try {
                    const r = await fetch(url, {credentials: 'include'});
                    if (r.ok) return await r.json();
                } catch(e) {}
            }
            return null;
        }""",
        symbol,
    )


async def _scrape() -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        print("  Loading Yahoo Finance session...")
        await page.goto(
            "https://finance.yahoo.com",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await asyncio.sleep(3)

        data = {}
        for symbol, column in ASSETS.items():
            print(f"  Fetching {column} ({symbol})...")
            data[column] = await _fetch_chart(page, symbol)

        await browser.close()

    return data


def _parse_series(raw: dict | None, column: str) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame(columns=["date", column])
    result = raw["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]
    closes = quote.get("close", [])

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(timestamps, unit="s").date,
            column: closes,
        }
    )
    df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.dropna(subset=["date", column]).drop_duplicates("date")


def scrape() -> pd.DataFrame:
    print("Scraping macro data via Yahoo Finance Playwright...")
    data = asyncio.run(_scrape())

    df = pd.DataFrame(columns=["date"])
    for column in ASSETS.values():
        series = _parse_series(data.get(column), column)
        print(f"  {column}: {len(series):,} rows")
        df = series if df.empty else pd.merge(df, series, on="date", how="outer")

    df = df.sort_values("date").reset_index(drop=True)
    df = df[["date", "sp500", "dxy", "vix", "gold"]]

    out = OUTPUT_DIR / "macro.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df):,} rows -> {out}")
    return df


if __name__ == "__main__":
    scrape()
