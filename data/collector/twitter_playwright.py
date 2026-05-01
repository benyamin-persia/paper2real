"""
Fast X/Twitter crawler using Playwright.

Default run scrapes all accounts from data/raw/account_tiers.json and writes CSV
files that Excel can open.

Examples:
  python -m data.collector.twitter_playwright
  python -m data.collector.twitter_playwright --workers 4 --max-tweets 4
  python -m data.collector.twitter_playwright --account saylor --max-tweets 4
  python -m data.collector.twitter_playwright --tier tier1 --workers 3

Outputs:
  data/raw/twitter_tweets.csv
  data/raw/twitter_timing.csv
  data/raw/twitter_playwright.json
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

TIERS_FILE = Path("data/raw/account_tiers.json")
JSON_OUTPUT = Path("data/raw/twitter_playwright.json")
TWEETS_CSV = Path("data/raw/twitter_tweets.csv")
TIMING_CSV = Path("data/raw/twitter_timing.csv")

DEFAULT_WORKERS = 4
DEFAULT_MAX_TWEETS = 4
DEFAULT_MAX_SCROLLS = 5


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_accounts(args: argparse.Namespace) -> list[str]:
    tiers = json.loads(TIERS_FILE.read_text(encoding="utf-8"))
    if args.account:
        return [args.account.lstrip("@")]
    if args.tier == "tier1":
        return tiers.get("tier1_permanent", [])
    if args.tier == "tier2":
        return tiers.get("tier2_roles", [])
    if args.tier == "tier3":
        return tiers.get("tier3_dynamic", [])

    accounts: list[str] = []
    for key in ("tier1_permanent", "tier2_roles", "tier3_dynamic"):
        accounts.extend(tiers.get(key, []))
    return list(dict.fromkeys(accounts))


async def _block_heavy_assets(route) -> None:
    if route.request.resource_type in {"image", "font", "media"}:
        await route.abort()
    else:
        await route.continue_()


EXTRACT_JS = """
({ maxTweets, includePinned }) => {
  const parseCompact = (value) => {
    if (!value) return 0;
    const raw = String(value).replace(/,/g, '').trim();
    const match = raw.match(/([0-9]+(?:\\.[0-9]+)?)([KMB])?/i);
    if (!match) return 0;
    const n = parseFloat(match[1]);
    const suffix = (match[2] || '').toUpperCase();
    const mult = suffix === 'K' ? 1e3 : suffix === 'M' ? 1e6 : suffix === 'B' ? 1e9 : 1;
    return Math.round(n * mult);
  };

  const firstNumber = (text) => parseCompact(text || '');

  const metricsFromLabel = (article) => {
    const metrics = { replies: 0, reposts: 0, likes: 0, views: 0, bookmarks: 0, quotes: 0 };
    const labels = [
      ...Array.from(article.querySelectorAll('[role="group"][aria-label]')).map(x => x.getAttribute('aria-label') || ''),
      ...Array.from(article.querySelectorAll('[aria-label]')).map(x => x.getAttribute('aria-label') || '')
    ].join(' | ');
    const patterns = [
      ['replies', /([0-9.,]+\\s*[KMB]?)\\s+(?:Reply|Replies)/i],
      ['reposts', /([0-9.,]+\\s*[KMB]?)\\s+(?:repost|reposts|retweet|retweets)/i],
      ['likes', /([0-9.,]+\\s*[KMB]?)\\s+(?:Like|Likes)/i],
      ['views', /([0-9.,]+\\s*[KMB]?)\\s+(?:view|views)/i],
      ['bookmarks', /([0-9.,]+\\s*[KMB]?)\\s+(?:bookmark|bookmarks)/i],
      ['quotes', /([0-9.,]+\\s*[KMB]?)\\s+(?:quote|quotes)/i],
    ];
    for (const [key, re] of patterns) {
      const m = labels.match(re);
      if (m) metrics[key] = parseCompact(m[1]);
    }
    return metrics;
  };

  const metricsFromButtons = (article, metrics) => {
    const reply = article.querySelector('[data-testid="reply"]')?.getAttribute('aria-label');
    const repost = article.querySelector('[data-testid="retweet"]')?.getAttribute('aria-label');
    const like = article.querySelector('[data-testid="like"], [data-testid="unlike"]')?.getAttribute('aria-label');
    const bookmark = article.querySelector('[data-testid="bookmark"]')?.getAttribute('aria-label');
    const views = article.querySelector('a[href$="/analytics"]')?.getAttribute('aria-label')
      || article.querySelector('a[href*="/analytics"]')?.innerText;
    if (reply && !metrics.replies) metrics.replies = firstNumber(reply);
    if (repost && !metrics.reposts) metrics.reposts = firstNumber(repost);
    if (like && !metrics.likes) metrics.likes = firstNumber(like);
    if (bookmark && !metrics.bookmarks) metrics.bookmarks = firstNumber(bookmark);
    if (views && !metrics.views) metrics.views = firstNumber(views);
    return metrics;
  };

  const out = [];
  const seen = new Set();
  for (const article of document.querySelectorAll('article[data-testid="tweet"]')) {
    const full = article.innerText || '';
    const isPinned = /\\bPinned\\b/i.test(full.split('\\n').slice(0, 3).join(' '));
    if (isPinned && !includePinned) continue;

    const text = article.querySelector('[data-testid="tweetText"]')?.innerText?.trim() || '';
    const timestamp = article.querySelector('time')?.getAttribute('datetime') || '';
    const url = article.querySelector('a[href*="/status/"]')?.href || '';
    const tweetId = (url.match(/status\\/(\\d+)/) || [])[1] || '';
    if (!tweetId || seen.has(tweetId)) continue;
    seen.add(tweetId);

    let metrics = metricsFromLabel(article);
    metrics = metricsFromButtons(article, metrics);
    out.push({
      tweet_id: tweetId,
      timestamp,
      text,
      url,
      is_pinned: isPinned ? 1 : 0,
      replies: metrics.replies || 0,
      comments: metrics.replies || 0,
      reposts: metrics.reposts || 0,
      retweets: metrics.reposts || 0,
      quotes: metrics.quotes || 0,
      likes: metrics.likes || 0,
      views: metrics.views || 0,
      bookmarks: metrics.bookmarks || 0,
    });
    if (out.length >= maxTweets) break;
  }
  return out;
}
"""


async def _extract_until_ready(page, max_tweets: int, max_scrolls: int, include_pinned: bool) -> list[dict]:
    tweets: list[dict] = []
    try:
        await page.wait_for_selector('article[data-testid="tweet"]', timeout=12000)
    except PlaywrightTimeoutError:
        return tweets

    for _ in range(max_scrolls + 1):
        tweets = await page.evaluate(
            EXTRACT_JS,
            {"maxTweets": max_tweets, "includePinned": include_pinned},
        )
        if len(tweets) >= max_tweets:
            return tweets
        await page.mouse.wheel(0, 900)
        await page.wait_for_timeout(900)
    return tweets


async def _scrape_account(ctx, handle: str, args: argparse.Namespace) -> dict:
    page = await ctx.new_page()
    t0 = time.perf_counter()
    try:
        await page.route("**/*", _block_heavy_assets)
        await page.goto(
            f"https://x.com/{handle}",
            wait_until="domcontentloaded",
            timeout=args.timeout_ms,
        )
        tweets = await _extract_until_ready(
            page=page,
            max_tweets=args.max_tweets,
            max_scrolls=args.max_scrolls,
            include_pinned=not args.skip_pinned,
        )
        elapsed = round(time.perf_counter() - t0, 2)
        print(f"  @{handle:<20} {elapsed:>6.2f}s  ({len(tweets)} tweets)")
        return {"handle": handle, "tweets": tweets, "elapsed_s": elapsed, "error": ""}
    except Exception as e:
        elapsed = round(time.perf_counter() - t0, 2)
        print(f"  @{handle:<20} {elapsed:>6.2f}s  ERROR: {e}")
        return {"handle": handle, "tweets": [], "elapsed_s": elapsed, "error": str(e)}
    finally:
        await page.close()


def _flatten_rows(results: list[dict], scraped_at: str) -> list[dict]:
    rows: list[dict] = []
    for account in results:
        for rank, tweet in enumerate(account["tweets"], start=1):
            rows.append(
                {
                    "scraped_at": scraped_at,
                    "handle": account["handle"],
                    "rank": rank,
                    "tweet_id": tweet.get("tweet_id", ""),
                    "timestamp": tweet.get("timestamp", ""),
                    "text": tweet.get("text", ""),
                    "url": tweet.get("url", ""),
                    "is_pinned": tweet.get("is_pinned", 0),
                    "comments": tweet.get("comments", tweet.get("replies", 0)),
                    "replies": tweet.get("replies", 0),
                    "retweets": tweet.get("retweets", tweet.get("reposts", 0)),
                    "reposts": tweet.get("reposts", 0),
                    "quotes": tweet.get("quotes", 0),
                    "likes": tweet.get("likes", 0),
                    "views": tweet.get("views", 0),
                    "bookmarks": tweet.get("bookmarks", 0),
                    "account_elapsed_s": account.get("elapsed_s", 0),
                    "account_error": account.get("error", ""),
                }
            )
    return rows


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


async def run(args: argparse.Namespace | None = None) -> dict:
    args = args or parse_args()
    accounts = _load_accounts(args)
    started_at = _utc_now()
    total_start = time.perf_counter()

    print(f"\n[Fast Playwright] Scraping {len(accounts)} X account(s)")
    print(f"  Tweets/account: {args.max_tweets}")
    print(f"  Workers:        {args.workers}")
    print(f"  Include pinned: {not args.skip_pinned}\n")

    results: list[dict] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not args.headed,
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
        await ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3] });
            window.chrome = { runtime: {} };
        """)

        for i in range(0, len(accounts), args.workers):
            batch = accounts[i : i + args.workers]
            batch_start = time.perf_counter()
            batch_results = await asyncio.gather(*[_scrape_account(ctx, h, args) for h in batch])
            results.extend(batch_results)
            print(f"  Batch {i // args.workers + 1} done in {time.perf_counter() - batch_start:.2f}s\n")

        if not args.no_retry_missing:
            missing = [r["handle"] for r in results if not r["tweets"] and not r["error"]]
            if missing:
                print(f"  Retrying {len(missing)} zero-tweet account(s) one by one...\n")
                retry_by_handle = {}
                for handle in missing:
                    retry_by_handle[handle] = await _scrape_account(ctx, handle, args)
                results = [retry_by_handle.get(r["handle"], r) for r in results]

        await browser.close()

    finished_at = _utc_now()
    total_s = round(time.perf_counter() - total_start, 2)
    per_account = [r["elapsed_s"] for r in results]
    tweets_total = sum(len(r["tweets"]) for r in results)
    errors = sum(1 for r in results if r["error"])
    accounts_with_tweets = sum(1 for r in results if r["tweets"])

    tweet_rows = _flatten_rows(results, finished_at)
    timing_rows = [
        {
            "scraped_at": finished_at,
            "handle": r["handle"],
            "elapsed_s": r["elapsed_s"],
            "tweets_found": len(r["tweets"]),
            "error": r["error"],
        }
        for r in results
    ]

    tweet_fields = [
        "scraped_at",
        "handle",
        "rank",
        "tweet_id",
        "timestamp",
        "text",
        "url",
        "is_pinned",
        "comments",
        "replies",
        "retweets",
        "reposts",
        "quotes",
        "likes",
        "views",
        "bookmarks",
        "account_elapsed_s",
        "account_error",
    ]
    timing_fields = ["scraped_at", "handle", "elapsed_s", "tweets_found", "error"]

    _write_csv(TWEETS_CSV, tweet_rows, tweet_fields)
    _write_csv(TIMING_CSV, timing_rows, timing_fields)

    output = {
        "scraper": "fast_playwright_csv",
        "started_at": started_at,
        "finished_at": finished_at,
        "accounts_total": len(accounts),
        "accounts_with_tweets": accounts_with_tweets,
        "tweets_per_account_requested": args.max_tweets,
        "tweets_total": tweets_total,
        "errors": errors,
        "workers": args.workers,
        "total_s": total_s,
        "avg_per_account_s": round(mean(per_account), 2) if per_account else 0,
        "slowest_account_s": round(max(per_account), 2) if per_account else 0,
        "tweets_csv": str(TWEETS_CSV),
        "timing_csv": str(TIMING_CSV),
        "results": results,
    }
    JSON_OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("-- Timing ------------------------------------------------")
    print(f"  Accounts:             {len(accounts)}")
    print(f"  Accounts with tweets: {accounts_with_tweets}")
    print(f"  Tweets scraped:       {tweets_total}")
    print(f"  Workers:              {args.workers}")
    print(f"  Total time:           {total_s}s")
    print(f"  Avg/account:          {output['avg_per_account_s']}s")
    print(f"  Slowest account:      {output['slowest_account_s']}s")
    print(f"  Errors:               {errors}/{len(accounts)}")
    print(f"  Tweets CSV:           {TWEETS_CSV}")
    print(f"  Timing CSV:           {TIMING_CSV}")
    print("---------------------------------------------------------\n")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fast X/Twitter crawler writing CSV files.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--account", help="Single account handle, for example saylor")
    group.add_argument("--tier", choices=["tier1", "tier2", "tier3"], help="Scrape one tier")
    parser.add_argument("--max-tweets", type=int, default=DEFAULT_MAX_TWEETS)
    parser.add_argument("--workers", "--concurrency", dest="workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--max-scrolls", type=int, default=DEFAULT_MAX_SCROLLS)
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--no-retry-missing", action="store_true", help="Do not retry accounts that return zero tweets")
    parser.add_argument("--skip-pinned", action="store_true", help="Skip tweets marked as pinned")
    parser.add_argument("--headed", action="store_true", help="Show Chromium window for debugging")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run())
