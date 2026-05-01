"""
events.py — Real-time critical event scraper (CryptoPanic via Playwright).

Runs every 15 minutes as a background task.
Writes data/raw/events.json with the latest important news and any detected alerts.

The risk engine reads market["exchange_hack_alert"] and market["stablecoin_depeg"].
This scraper is the ONLY thing that populates those values.
"""

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

OUTPUT_FILE = Path("data/raw/events.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Keywords that set exchange_hack_alert — halt trading immediately
HACK_KEYWORDS = {
    "hack", "hacked", "exploit", "exploited", "breach", "breached",
    "stolen", "drained", "attack", "attacked", "compromised", "vulnerability",
    "collapse", "collapsed", "insolvent", "insolvency", "bankrupt", "bankruptcy",
    "suspended", "halted", "shutdown", "arrested", "charged", "indicted",
    "seized", "confiscated", "scam", "rug", "rug pull", "exit scam",
    "emergency", "forced to close", "unable to process", "withdrawals paused",
    "withdrawals halted", "withdrawals suspended",
}

# Keywords that indicate regulatory action (still use exchange_hack_alert)
REGULATORY_KEYWORDS = {
    "ban", "banned", "banning", "outlawed", "prohibited",
    "sec sues", "sec charges", "cftc charges", "doj charges",
    "regulatory action", "enforcement action", "cease and desist",
    "criminal charges", "civil charges",
}

# Keywords that set stablecoin_depeg
DEPEG_KEYWORDS = {
    "depeg", "depegged", "depegging", "losing peg", "broke peg", "broken peg",
    "usdt", "usdc", "tether",  # combined below with price/peg context
}

DEPEG_CONTEXT = {"peg", "depeg", "depegged", "1.00", "$1", "lost peg", "below", "above"}

CRITICAL_EXCHANGES = {
    "binance", "coinbase", "kraken", "okx", "bybit", "bitfinex",
    "ftx", "gemini", "bitstamp", "huobi", "kucoin",
}


def _is_critical(headline: str) -> tuple[str | None, str]:
    """
    Returns (alert_type, matched_keyword) if headline is critical.
    alert_type is 'exchange_hack_alert' or 'stablecoin_depeg' or None.
    """
    text = headline.lower()
    words = set(re.split(r"[\s,.\-–—:!?/]", text))

    # Check depeg first — most specific
    has_stablecoin = bool(words & {"usdt", "usdc", "tether", "dai", "busd", "frax"})
    has_depeg_word = bool(words & {"depeg", "depegged", "depegging"})
    if has_stablecoin and has_depeg_word:
        return "stablecoin_depeg", "depeg+stablecoin"

    # Check hack/collapse
    matched = words & HACK_KEYWORDS
    if matched:
        return "exchange_hack_alert", list(matched)[0]

    # Check regulatory
    for phrase in REGULATORY_KEYWORDS:
        if phrase in text:
            return "exchange_hack_alert", phrase

    return None, ""


async def _fetch_news_via_api(page) -> list[dict]:
    """Try to call CryptoPanic's internal news API from within the browser session."""
    for endpoint in [
        "/api/v1/posts/?currencies=BTC&filter=important&public=true",
        "/api/v1/posts/?currencies=BTC&public=true",
        "/api/v1/posts/?filter=important&public=true",
    ]:
        try:
            data = await page.evaluate(
                """async (path) => {
                    try {
                        const r = await fetch(path, {
                            credentials: 'include',
                            headers: {accept: 'application/json'},
                        });
                        if (!r.ok) return null;
                        return await r.json();
                    } catch(e) { return null; }
                }""",
                endpoint,
            )
            if data and isinstance(data, dict) and data.get("results"):
                return [
                    {
                        "headline": item.get("title", ""),
                        "url":      item.get("url", ""),
                        "published_at": item.get("published_at", ""),
                        "importance": item.get("votes", {}).get("important", 0),
                        "source": "api",
                    }
                    for item in data["results"][:30]
                ]
        except Exception:
            continue
    return []


async def _fetch_news_via_html(page) -> list[dict]:
    """Fallback: parse CryptoPanic BTC news page HTML."""
    try:
        items = await page.evaluate("""() => {
            const results = [];
            const rows = document.querySelectorAll('.news-row, [class*="news_item"], article');
            rows.forEach(row => {
                const link = row.querySelector('a[href*="/news/"]');
                const timeEl = row.querySelector('time');
                if (link && link.textContent.trim()) {
                    results.push({
                        headline: link.textContent.trim(),
                        url: link.href || '',
                        published_at: timeEl ? timeEl.getAttribute('datetime') : '',
                        importance: row.classList.contains('is-important') ? 1 : 0,
                        source: 'html',
                    });
                }
            });
            return results.slice(0, 30);
        }""")
        return items if items else []
    except Exception:
        return []


async def _scrape() -> dict:
    """Main async scraper. Returns the events dict to save."""
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "last_updated":      now,
        "has_critical":      False,
        "exchange_hack_alert": None,
        "stablecoin_depeg":    None,
        "critical_alerts":   [],
        "important_news":    [],
        "scrape_error":      None,
    }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx     = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await ctx.new_page()

            await page.goto(
                "https://cryptopanic.com/news/bitcoin/",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await asyncio.sleep(3)

            news = await _fetch_news_via_api(page)
            if not news:
                news = await _fetch_news_via_html(page)

            await browser.close()

    except Exception as e:
        result["scrape_error"] = str(e)
        return result

    for item in news:
        headline = item.get("headline", "")
        if not headline:
            continue

        alert_type, keyword = _is_critical(headline)
        if alert_type:
            alert = {
                "headline":   headline,
                "url":        item.get("url", ""),
                "published_at": item.get("published_at", ""),
                "alert_type": alert_type,
                "keyword":    keyword,
            }
            result["critical_alerts"].append(alert)
            result["has_critical"] = True
            if alert_type == "exchange_hack_alert" and not result["exchange_hack_alert"]:
                result["exchange_hack_alert"] = headline[:200]
            elif alert_type == "stablecoin_depeg" and not result["stablecoin_depeg"]:
                result["stablecoin_depeg"] = headline[:200]
        else:
            result["important_news"].append({
                "headline":     headline,
                "url":          item.get("url", ""),
                "published_at": item.get("published_at", ""),
                "importance":   item.get("importance", 0),
            })

    return result


def scrape() -> dict:
    """Sync entry point — used by collect.py and manual runs."""
    print("Scraping CryptoPanic events via Playwright...")
    data = asyncio.run(_scrape())
    OUTPUT_FILE.write_text(json.dumps(data, indent=2))
    status = "CRITICAL ALERTS DETECTED" if data["has_critical"] else "no critical alerts"
    print(f"  Events saved -> {OUTPUT_FILE} ({status})")
    if data.get("scrape_error"):
        print(f"  Warning: {data['scrape_error']}")
    return data


async def async_scrape() -> dict:
    """Async entry point — used by the FastAPI background loop."""
    data = await _scrape()
    OUTPUT_FILE.write_text(json.dumps(data, indent=2))
    return data


def read_cached() -> dict | None:
    """Read the last saved events file. Returns None if file doesn't exist."""
    if not OUTPUT_FILE.exists():
        return None
    try:
        return json.loads(OUTPUT_FILE.read_text())
    except Exception:
        return None


if __name__ == "__main__":
    scrape()
