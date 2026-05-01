import asyncio
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

METRICS = {
    "hash_rate": {
        "page": "https://www.blockchain.com/explorer/charts/hash-rate",
        "api": "https://api.blockchain.info/charts/hash-rate?timespan=2years&format=json&cors=true",
    },
    "total_btc_supply": {
        "api": "https://api.blockchain.info/charts/total-bitcoins?timespan=2years&format=json&cors=true",
    },
    "tx_volume_usd": {
        "api": "https://api.blockchain.info/charts/estimated-transaction-volume-usd?timespan=2years&format=json&cors=true",
    },
}


async def _fetch_metric(page, url: str) -> dict | None:
    data = await page.evaluate(
        """async (url) => {
            try {
                const r = await fetch(url, {
                    credentials: 'include',
                    headers: {accept: 'application/json'},
                });
                if (r.ok) return await r.json();
            } catch(e) {}
            return null;
        }""",
        url,
    )
    if data:
        return data

    api_page = await page.context.new_page()
    try:
        response = await api_page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if response and response.ok:
            return await api_page.evaluate("() => JSON.parse(document.body.innerText)")
    except Exception:
        return None
    finally:
        await api_page.close()
    return None


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

        print("  Loading blockchain.com hash-rate chart...")
        await page.goto(
            METRICS["hash_rate"]["page"],
            wait_until="domcontentloaded",
            timeout=90000,
        )
        await asyncio.sleep(4)

        data = {}
        for column, cfg in METRICS.items():
            print(f"  Fetching {column}...")
            data[column] = await _fetch_metric(page, cfg["api"])

        await browser.close()

    return data


def _parse_metric(raw: dict | None, column: str) -> pd.DataFrame:
    rows = []
    for entry in (raw or {}).get("values", []):
        try:
            rows.append(
                {
                    "date": pd.to_datetime(entry["x"], unit="s").date(),
                    column: entry["y"],
                }
            )
        except Exception:
            continue
    df = pd.DataFrame(rows, columns=["date", column])
    if df.empty:
        return df
    df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.dropna(subset=["date", column]).drop_duplicates("date")


def scrape() -> pd.DataFrame:
    print("Scraping on-chain data via blockchain.com Playwright...")
    data = asyncio.run(_scrape())

    df = pd.DataFrame(columns=["date"])
    for column in METRICS:
        series = _parse_metric(data.get(column), column)
        print(f"  {column}: {len(series):,} rows")
        df = series if df.empty else pd.merge(df, series, on="date", how="outer")

    for column in ["hash_rate", "total_btc_supply", "tx_volume_usd"]:
        if column not in df.columns:
            df[column] = pd.NA

    df = df.sort_values("date").reset_index(drop=True)
    df = df[["date", "hash_rate", "total_btc_supply", "tx_volume_usd"]]

    out = OUTPUT_DIR / "onchain.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df):,} rows -> {out}")
    return df


if __name__ == "__main__":
    scrape()
