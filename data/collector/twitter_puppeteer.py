"""
twitter_puppeteer.py — scrape X.com using Pyppeteer (Python Puppeteer) in stealth mode.
Install:  pip install pyppeteer
Run:      python -m data.collector.twitter_puppeteer
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pyppeteer
from pyppeteer import launch

TIERS_FILE  = Path("data/raw/account_tiers.json")
OUTPUT_FILE = Path("data/raw/twitter_puppeteer.json")


def _load_tier1() -> list[str]:
    return json.loads(TIERS_FILE.read_text())["tier1_permanent"]


async def _scrape_account(browser, handle: str) -> dict:
    page = await browser.newPage()
    t0 = time.perf_counter()
    try:
        # Stealth patches
        await page.evaluateOnNewDocument("""() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3] });
            window.chrome = { runtime: {} };
        }""")
        await page.setUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        await page.setViewport({"width": 1280, "height": 900})

        await page.goto(f"https://x.com/{handle}", {"waitUntil": "domcontentloaded", "timeout": 30000})
        await asyncio.sleep(2)

        tweets = await page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('article[data-testid="tweet"]').forEach(el => {
                const text = el.querySelector('[data-testid="tweetText"]')?.innerText?.trim();
                const ts   = el.querySelector('time')?.getAttribute('datetime');
                const url  = el.querySelector('a[href*="/status/"]')?.href;
                if (text) out.push({ text, ts: ts || '', url: url || '' });
            });
            return out.slice(0, 5);
        }""")
        elapsed = round(time.perf_counter() - t0, 2)
        return {"handle": handle, "tweets": tweets or [], "elapsed_s": elapsed, "error": None}
    except Exception as e:
        return {"handle": handle, "tweets": [], "elapsed_s": round(time.perf_counter() - t0, 2), "error": str(e)}
    finally:
        await page.close()


async def run():
    accounts = _load_tier1()
    print(f"[Puppeteer] Scraping {len(accounts)} accounts on X.com...")
    total_start = time.perf_counter()

    browser = await launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )

    # Run all accounts in parallel
    results = await asyncio.gather(*[_scrape_account(browser, h) for h in accounts])
    await browser.close()

    total_elapsed = round(time.perf_counter() - total_start, 2)
    per_account   = [r["elapsed_s"] for r in results]
    tweet_count   = sum(len(r["tweets"]) for r in results)
    errors        = sum(1 for r in results if r["error"])

    print(f"\n── Puppeteer Timing ──────────────────────────────")
    print(f"  Total time (parallel):  {total_elapsed}s")
    print(f"  Avg per account:        {round(sum(per_account)/len(per_account), 2)}s")
    print(f"  Slowest account:        {max(per_account)}s")
    print(f"  Total tweets scraped:   {tweet_count}")
    print(f"  Failed accounts:        {errors}/{len(accounts)}")
    print(f"──────────────────────────────────────────────────\n")

    output = {
        "scraper":        "puppeteer",
        "last_updated":   datetime.now(timezone.utc).isoformat(),
        "total_s":        total_elapsed,
        "avg_per_acct_s": round(sum(per_account)/len(per_account), 2),
        "tweets_total":   tweet_count,
        "errors":         errors,
        "results":        results,
    }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2))
    print(f"Saved -> {OUTPUT_FILE}")
    return output


if __name__ == "__main__":
    asyncio.run(run())
