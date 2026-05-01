"""
twitter.py — Tier 1 Twitter/X scraper for paper2real.

Strategy (fastest to slowest, tried in order):
  1. Nitter RSS  — pure httpx, no browser, ~0.5s/account, parallel async
  2. Nitter HTML — Playwright, simple HTML, ~1-2s/account
  3. Twitter.com — Playwright + stealth patches, ~8-15s/account (last resort)

Only scrapes Tier 1 accounts (24 accounts from account_tiers.json).
Only cares about the last 24 hours of tweets.
Saves to data/raw/twitter_alerts.json with timing stats.
"""

import asyncio
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx

OUTPUT_FILE = Path("data/raw/twitter_alerts.json")
TIERS_FILE  = Path("data/raw/account_tiers.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Public Nitter instances — tried in order, first that responds wins
NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks",
    "https://nitter.unixfox.eu",
]

MAX_TWEET_AGE_HOURS = 24     # ignore tweets older than this
MAX_TWEETS_PER_ACCOUNT = 10  # latest N tweets to check per account

# Keywords that make a tweet worth flagging for the risk engine
CRITICAL_KEYWORDS = {
    "hack", "hacked", "exploit", "breach", "stolen", "drained",
    "ban", "banned", "ban crypto", "outlaw", "shutdown", "suspended",
    "sec sues", "sec charges", "cftc", "doj charges", "enforcement",
    "arrested", "indicted", "seized", "emergency",
    "depeg", "insolvent", "bankrupt", "collapse", "failed",
    "btc", "bitcoin", "crypto", "exchange",
}

ALERT_KEYWORDS = {
    "ban", "banned", "hack", "hacked", "exploit", "breach", "seized",
    "insolvent", "bankrupt", "collapse", "depeg", "emergency", "shutdown",
    "arrested", "indicted", "enforcement action", "cease and desist",
}


def _load_tier1_accounts() -> list[str]:
    data = json.loads(TIERS_FILE.read_text())
    return data.get("tier1_permanent", [])


def _is_recent(date_str: str) -> bool:
    """Return True if the tweet date string is within MAX_TWEET_AGE_HOURS."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_TWEET_AGE_HOURS)
        # Nitter RSS uses RFC 2822 format: "Mon, 01 Jan 2026 12:00:00 GMT"
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt >= cutoff
    except Exception:
        return True  # if we can't parse, include it


def _score_tweet(text: str) -> tuple[bool, list[str]]:
    """Returns (is_alert, matched_keywords) for a tweet text."""
    lower = text.lower()
    matched = [kw for kw in ALERT_KEYWORDS if kw in lower]
    return bool(matched), matched


# ── Strategy 1: Nitter RSS (fastest — pure httpx, no browser) ────────────────

async def _fetch_rss(client: httpx.AsyncClient, base: str, handle: str) -> list[dict]:
    """Fetch latest tweets for one account via Nitter RSS."""
    url = f"{base}/{handle}/rss"
    try:
        r = await client.get(url, timeout=8, follow_redirects=True)
        if r.status_code != 200:
            return []
        return _parse_rss(r.text, handle)
    except Exception:
        return []


def _parse_rss(xml: str, handle: str) -> list[dict]:
    """Extract tweets from Nitter RSS XML without an XML parser (faster)."""
    tweets = []
    items = xml.split("<item>")[1:]
    for item in items[:MAX_TWEETS_PER_ACCOUNT]:
        try:
            title = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item, re.DOTALL)
            pub   = re.search(r"<pubDate>(.*?)</pubDate>", item)
            link  = re.search(r"<link>(.*?)</link>", item)
            if not title:
                continue
            text     = title.group(1).strip()
            date_str = pub.group(1).strip() if pub else ""
            url      = link.group(1).strip() if link else ""
            if date_str and not _is_recent(date_str):
                continue
            is_alert, keywords = _score_tweet(text)
            tweets.append({
                "handle":     handle,
                "text":       text[:500],
                "url":        url,
                "date":       date_str,
                "is_alert":   is_alert,
                "keywords":   keywords,
                "source":     "nitter_rss",
            })
        except Exception:
            continue
    return tweets


async def _find_working_nitter(client: httpx.AsyncClient) -> str | None:
    """Ping each Nitter instance, return first that responds."""
    for base in NITTER_INSTANCES:
        try:
            r = await client.get(f"{base}/x", timeout=5, follow_redirects=True)
            if r.status_code < 500:
                return base
        except Exception:
            continue
    return None


async def scrape_via_rss(accounts: list[str]) -> tuple[list[dict], float]:
    """
    Fetch all Tier 1 accounts in parallel via Nitter RSS.
    Returns (tweets, elapsed_seconds).
    """
    start = time.perf_counter()
    tweets = []

    async with httpx.AsyncClient(
        headers={"user-agent": "Mozilla/5.0 (compatible; RSS reader)"},
        timeout=10,
    ) as client:
        nitter_base = await _find_working_nitter(client)
        if not nitter_base:
            print("  No Nitter instance available — RSS strategy failed")
            return [], time.perf_counter() - start

        print(f"  Using Nitter: {nitter_base}")
        tasks = [_fetch_rss(client, nitter_base, h) for h in accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, list):
            tweets.extend(r)

    return tweets, time.perf_counter() - start


# ── Strategy 2: Nitter HTML via Playwright (fallback) ────────────────────────

async def scrape_via_playwright_nitter(
    accounts: list[str],
    nitter_base: str,
) -> tuple[list[dict], float]:
    """
    Scrape Nitter HTML pages via Playwright for accounts that returned 0 tweets via RSS.
    Returns (tweets, elapsed_seconds).
    """
    from playwright.async_api import async_playwright

    start  = time.perf_counter()
    tweets = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx     = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        async def _fetch_page(handle: str) -> list[dict]:
            page = await ctx.new_page()
            try:
                await page.goto(
                    f"{nitter_base}/{handle}",
                    wait_until="domcontentloaded",
                    timeout=20000,
                )
                items = await page.evaluate("""() => {
                    const tweets = [];
                    document.querySelectorAll('.timeline-item').forEach(el => {
                        const text = el.querySelector('.tweet-content')?.innerText?.trim();
                        const date = el.querySelector('.tweet-date a')?.title?.trim();
                        const link = el.querySelector('.tweet-link')?.href;
                        if (text) tweets.push({ text, date: date || '', url: link || '' });
                    });
                    return tweets.slice(0, 10);
                }""")
                result = []
                for item in (items or []):
                    is_alert, keywords = _score_tweet(item.get("text", ""))
                    result.append({
                        "handle":   handle,
                        "text":     item.get("text", "")[:500],
                        "url":      item.get("url", ""),
                        "date":     item.get("date", ""),
                        "is_alert": is_alert,
                        "keywords": keywords,
                        "source":   "nitter_html",
                    })
                return result
            except Exception:
                return []
            finally:
                await page.close()

        tasks   = [_fetch_page(h) for h in accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        await browser.close()

    for r in results:
        if isinstance(r, list):
            tweets.extend(r)

    return tweets, time.perf_counter() - start


# ── Strategy 3: Direct Twitter.com with stealth (last resort) ────────────────

async def scrape_via_playwright_twitter(
    accounts: list[str],
) -> tuple[list[dict], float]:
    """
    Scrape Twitter.com directly using Playwright with anti-detection patches.
    Slowest (8-15s/account) but works when Nitter is down.
    Runs accounts sequentially — parallel on Twitter.com triggers rate limits fast.
    """
    from playwright.async_api import async_playwright

    start  = time.perf_counter()
    tweets = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            timezone_id="America/New_York",
        )
        # Patch navigator.webdriver before any page loads
        await ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            window.chrome = { runtime: {} };
        """)

        for handle in accounts:
            page = await ctx.new_page()
            try:
                await page.goto(
                    f"https://x.com/{handle}",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                await asyncio.sleep(2)  # let React render

                items = await page.evaluate("""() => {
                    const tweets = [];
                    document.querySelectorAll('article[data-testid="tweet"]').forEach(el => {
                        const text = el.querySelector('[data-testid="tweetText"]')?.innerText?.trim();
                        const time = el.querySelector('time')?.getAttribute('datetime');
                        const link = el.querySelector('a[href*="/status/"]')?.href;
                        if (text) tweets.push({ text, date: time || '', url: link || '' });
                    });
                    return tweets.slice(0, 10);
                }""")

                for item in (items or []):
                    is_alert, keywords = _score_tweet(item.get("text", ""))
                    tweets.append({
                        "handle":   handle,
                        "text":     item.get("text", "")[:500],
                        "url":      item.get("url", ""),
                        "date":     item.get("date", ""),
                        "is_alert": is_alert,
                        "keywords": keywords,
                        "source":   "twitter_direct",
                    })

            except Exception as e:
                print(f"  Twitter.com failed for @{handle}: {e}")
            finally:
                await page.close()

        await browser.close()

    return tweets, time.perf_counter() - start


# ── Main scrape function ──────────────────────────────────────────────────────

async def _scrape_with_timing() -> dict:
    accounts = _load_tier1_accounts()
    print(f"  Scraping {len(accounts)} Tier 1 accounts...")

    timing: dict = {}
    all_tweets:  list[dict] = []
    strategy_used = "none"

    # Strategy 1: Nitter RSS (fastest)
    print("\n  [1/3] Trying Nitter RSS (fastest)...")
    rss_tweets, rss_time = await scrape_via_rss(accounts)
    timing["nitter_rss_seconds"] = round(rss_time, 2)
    print(f"       {len(rss_tweets)} tweets in {rss_time:.2f}s")

    if rss_tweets:
        all_tweets   = rss_tweets
        strategy_used = "nitter_rss"
    else:
        # Strategy 2: Nitter HTML
        print("\n  [2/3] RSS failed — trying Nitter HTML (Playwright)...")
        async with httpx.AsyncClient(timeout=5) as c:
            nitter_base = await _find_working_nitter(c)

        if nitter_base:
            html_tweets, html_time = await scrape_via_playwright_nitter(
                accounts, nitter_base
            )
            timing["nitter_html_seconds"] = round(html_time, 2)
            print(f"       {len(html_tweets)} tweets in {html_time:.2f}s")

            if html_tweets:
                all_tweets    = html_tweets
                strategy_used = "nitter_html"

        if not all_tweets:
            # Strategy 3: Direct Twitter.com (last resort)
            print("\n  [3/3] Nitter unavailable — trying Twitter.com direct (slow)...")
            tw_tweets, tw_time = await scrape_via_playwright_twitter(accounts)
            timing["twitter_direct_seconds"] = round(tw_time, 2)
            print(f"       {len(tw_tweets)} tweets in {tw_time:.2f}s")
            all_tweets    = tw_tweets
            strategy_used = "twitter_direct"

    # Separate alerts from context tweets
    alerts  = [t for t in all_tweets if t["is_alert"]]
    context = [t for t in all_tweets if not t["is_alert"]]

    result = {
        "last_updated":     datetime.now(timezone.utc).isoformat(),
        "strategy_used":    strategy_used,
        "accounts_scraped": len(accounts),
        "tweets_found":     len(all_tweets),
        "alerts_found":     len(alerts),
        "timing":           timing,
        "alerts":           alerts,
        "recent_tweets":    context[:50],
    }

    # Print timing summary
    print(f"\n  ── Timing Summary ──────────────────────────────")
    for k, v in timing.items():
        accounts_per_second = round(len(accounts) / v, 1) if v > 0 else 0
        print(f"  {k:35s} {v:6.2f}s  ({accounts_per_second} accounts/s)")
    print(f"  Strategy used: {strategy_used}")
    print(f"  Total tweets:  {len(all_tweets)}")
    print(f"  Alerts:        {len(alerts)}")
    if alerts:
        print(f"\n  ALERTS:")
        for a in alerts:
            print(f"    @{a['handle']}: {a['text'][:100]}")
    print(f"  ────────────────────────────────────────────────")

    return result


def scrape() -> dict:
    """Sync entry point — for collect.py and manual runs."""
    print("Scraping Tier 1 Twitter accounts...")
    data = asyncio.run(_scrape_with_timing())
    OUTPUT_FILE.write_text(json.dumps(data, indent=2))
    print(f"  Saved -> {OUTPUT_FILE}")
    return data


async def async_scrape() -> dict:
    """Async entry point — for FastAPI background loop."""
    data = await _scrape_with_timing()
    OUTPUT_FILE.write_text(json.dumps(data, indent=2))
    return data


def read_cached() -> dict | None:
    if not OUTPUT_FILE.exists():
        return None
    try:
        return json.loads(OUTPUT_FILE.read_text())
    except Exception:
        return None


if __name__ == "__main__":
    scrape()
