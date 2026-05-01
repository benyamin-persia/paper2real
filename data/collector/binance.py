import asyncio
import io
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def _scrape(days_back: int) -> pd.DataFrame:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            accept_downloads=True,
        )
        page = await context.new_page()

        try:
            print("  Trying Strategy 1: Yahoo Finance v8 JSON...")
            await page.goto(
                "https://finance.yahoo.com",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await asyncio.sleep(3)

            yahoo_data = await page.evaluate("""
                async () => {
                    const urls = [
                        'https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1d&range=2y',
                        'https://query2.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1d&range=2y',
                    ];
                    for (const url of urls) {
                        try {
                            const r = await fetch(url, {credentials: 'include'});
                            if (r.ok) return await r.json();
                        } catch(e) {}
                    }
                    return null;
                }
            """)

            if yahoo_data:
                result = yahoo_data["chart"]["result"][0]
                quote = result["indicators"]["quote"][0]
                df = pd.DataFrame(
                    {
                        "timestamp": pd.to_datetime(result["timestamp"], unit="s"),
                        "open": quote.get("open"),
                        "high": quote.get("high"),
                        "low": quote.get("low"),
                        "close": quote.get("close"),
                        "volume": quote.get("volume"),
                    }
                )
                if len(df) >= 100:
                    df.attrs["strategy"] = "Yahoo Finance v8 JSON"
                    await browser.close()
                    return df
                print(f"  Strategy 1 returned only {len(df):,} rows")
        except Exception as e:
            print(f"  Strategy 1 failed: {e}")

        try:
            print("  Trying Strategy 2: Stooq.com CSV...")
            await page.goto(
                "https://stooq.com",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await asyncio.sleep(2)

            csv_text = await page.evaluate("""
                async () => {
                    try {
                        const r = await fetch(
                            'https://stooq.com/q/d/l/?s=btc.v&i=d',
                            {credentials: 'include'}
                        );
                        if (r.ok) {
                            const t = await r.text();
                            if (t.includes('Date')) return t;
                        }
                    } catch(e) {}
                    return null;
                }
            """)

            if csv_text and "Date" in str(csv_text):
                df = pd.read_csv(io.StringIO(csv_text))
                df = df.rename(columns={"Date": "timestamp"})
                df.attrs["strategy"] = "Stooq.com CSV"
                await browser.close()
                return df
        except Exception as e:
            print(f"  Strategy 2 failed: {e}")

        try:
            print("  Trying Strategy 3: Yahoo Finance HTML table...")
            await page.goto(
                "https://finance.yahoo.com/quote/BTC-USD/history/",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await asyncio.sleep(8)

            rows = await page.evaluate("""
                () => Array.from(document.querySelectorAll('table tbody tr'))
                    .map(row => Array.from(row.querySelectorAll('td'))
                        .map(cell => cell.textContent.trim()))
                    .filter(cells => cells.length === 7)
            """)

            month_names = (
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            )
            rows = [
                row
                for row in rows
                if row and any(month in row[0] for month in month_names)
            ]
            if rows:
                df = pd.DataFrame(
                    rows,
                    columns=[
                        "timestamp",
                        "open",
                        "high",
                        "low",
                        "close",
                        "adj close",
                        "volume",
                    ],
                )
                df.attrs["strategy"] = "Yahoo Finance HTML table"
                await browser.close()
                return df
        except Exception as e:
            print(f"  Strategy 3 failed: {e}")

        await browser.close()

    return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


def scrape(days_back: int = 730) -> pd.DataFrame:
    print("Scraping BTC price data via Playwright...")
    df = asyncio.run(_scrape(days_back))
    strategy = df.attrs.get("strategy", "no strategy")

    if df.empty:
        print("  All BTC price data strategies failed - no data")
        df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        df.to_csv(OUTPUT_DIR / "btc_15m_raw.csv", index=False)
        return df

    df.columns = [c.lower().strip() for c in df.columns]
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            )

    df = df.dropna(subset=["timestamp", "close"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]

    out = OUTPUT_DIR / "btc_15m_raw.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df):,} rows to {out} using {strategy}")
    return df


if __name__ == "__main__":
    scrape(days_back=730)
