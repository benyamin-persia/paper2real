import asyncio
import json
import pandas as pd
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def _scrape() -> list:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        print("  Loading Fear & Greed page...")
        await page.goto(
            "https://alternative.me/crypto/fear-and-greed-index/",
            wait_until="domcontentloaded",
            timeout=90000,
        )
        await asyncio.sleep(6)

        # use fetch() from inside the browser — bypasses Python-level blocks
        print("  Fetching data via browser fetch()...")
        data = await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('https://api.alternative.me/fng/?limit=0&format=json');
                    return await r.json();
                } catch(e) {
                    return null;
                }
            }
        """)

        await browser.close()
        return data.get("data", []) if data else []


def scrape() -> pd.DataFrame:
    print("Scraping Fear & Greed index via Playwright browser fetch...")
    items = asyncio.run(_scrape())

    rows = []
    for item in items:
        try:
            rows.append({
                "date":             pd.to_datetime(int(item["timestamp"]), unit="s").date(),
                "fear_greed_index": int(item["value"]),
                "fear_greed_label": item["value_classification"],
            })
        except Exception:
            continue

    df = pd.DataFrame(rows).drop_duplicates("date") if rows else pd.DataFrame(
        columns=["date", "fear_greed_index", "fear_greed_label"]
    )
    df = df.sort_values("date").reset_index(drop=True)
    out = OUTPUT_DIR / "fear_greed.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df):,} days → {out}")
    return df


if __name__ == "__main__":
    scrape()
