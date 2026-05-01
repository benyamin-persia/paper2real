"""
Debug script — runs each scraper one at a time and shows all network activity.
Run this to find which URLs are returning 404.
"""
import asyncio
from playwright.async_api import async_playwright


async def debug_site(name: str, url: str):
    print(f"\n{'='*60}")
    print(f"  Debugging: {name}")
    print(f"  URL: {url}")
    print(f"{'='*60}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        async def handle_response(response):
            ct = response.headers.get("content-type", "")
            if "json" in ct or response.status >= 400:
                status = response.status
                emoji = "✅" if status == 200 else "❌"
                print(f"  {emoji} [{status}] {response.url[:100]}")

        page.on("response", handle_response)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(8)
        except Exception as e:
            print(f"  ERROR: {e}")

        await browser.close()


async def main():
    sites = [
        ("Yahoo Finance BTC",   "https://finance.yahoo.com/quote/BTC-USD/history/"),
        ("Fear & Greed",        "https://alternative.me/crypto/fear-and-greed-index/"),
        ("CoinGlass",           "https://www.coinglass.com/BitcoinFundingRate"),
        ("CoinGecko",           "https://www.coingecko.com/en/coins/bitcoin"),
    ]

    for name, url in sites:
        await debug_site(name, url)
        input(f"\n  Press ENTER to continue to next site...")


asyncio.run(main())
